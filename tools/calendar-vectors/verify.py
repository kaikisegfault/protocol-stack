#!/usr/bin/env python3
"""Independently derive and check the calendar-v1 vectors.

Every recorded value is rederived twice: once from the accepted documents in
`expected.py`, which imports nothing from `simulation/` and builds the calendar
by accumulating month lengths from 1970, and once from a live run of the model,
which uses the closed-form era arithmetic. A value both sources agree on has
been reached by two different algorithms; a value only the model reproduces
would be a restatement of the model rather than evidence about it.

`--emit` rewrites the vector file from the same derivations through the same
agreement gate, so a recorded value is never transcribed by hand.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import expected as e
from checker import Checker, read_vectors

from simulation.calendar import contract as c
from simulation.calendar import civil, months, scenario
from simulation.calendar.chain import Calendar

MODELLED_CODES = frozenset(c.RESULT_CODES)


def check_constants(check: Checker) -> None:
    check.section("The unit, the range, and the tolerance.")
    check.agree("constants.millis_per_second", e.MILLIS_PER_SECOND, c.MILLIS_PER_SECOND)
    check.agree("constants.millis_per_day", e.MILLIS_PER_DAY, c.MILLIS_PER_DAY)
    check.agree(
        "constants.min_timestamp_millis", e.MIN_TIMESTAMP_MILLIS, c.MIN_TIMESTAMP_MILLIS
    )
    check.agree(
        "constants.max_timestamp_millis", e.MAX_TIMESTAMP_MILLIS, c.MAX_TIMESTAMP_MILLIS
    )
    check.agree("constants.min_calendar_year", e.MIN_CALENDAR_YEAR, c.MIN_CALENDAR_YEAR)
    check.agree("constants.max_calendar_year", e.MAX_CALENDAR_YEAR, c.MAX_CALENDAR_YEAR)
    check.agree("constants.months_per_year", e.MONTHS_PER_YEAR, c.MONTHS_PER_YEAR)
    check.agree("constants.max_month_index", e.MAX_MONTH_INDEX, c.MAX_MONTH_INDEX)
    check.agree(
        "constants.tolerance_seconds",
        e.TIMESTAMP_TOLERANCE_SECONDS,
        c.TIMESTAMP_TOLERANCE_SECONDS,
    )
    check.agree(
        "constants.tolerance_millis",
        e.TIMESTAMP_TOLERANCE_MILLIS,
        c.TIMESTAMP_TOLERANCE_MILLIS,
    )
    check.agree(
        "constants.target_commit_seconds",
        e.TARGET_COMMIT_SECONDS,
        c.TARGET_COMMIT_SECONDS,
    )
    check.agree(
        "constants.max_boundary_shift_blocks",
        e.MAX_BOUNDARY_SHIFT_BLOCKS,
        c.MAX_BOUNDARY_SHIFT_BLOCKS,
    )
    check.agree(
        "constants.seconds_per_month_minimum",
        e.SECONDS_PER_MONTH_MINIMUM,
        c.SECONDS_PER_MONTH_MINIMUM,
    )
    # The calendar stores nothing: a height's month is a pure function of a
    # field the header already carries.
    check.equal("constants.state_bytes", c.CALENDAR_STATE_BYTES)


def check_exactness(check: Checker) -> None:
    check.section(
        "The tolerance divides the commit interval exactly, and it is small "
        "relative to the shortest month, which is the ceiling ADR 0050 sets."
    )
    check.equal(
        "exactness.tolerance_remainder_seconds",
        e.TIMESTAMP_TOLERANCE_SECONDS % e.TARGET_COMMIT_SECONDS,
    )
    check.equal(
        "exactness.boundary_shift_converts_back_to_seconds",
        e.MAX_BOUNDARY_SHIFT_BLOCKS * e.TARGET_COMMIT_SECONDS,
    )
    check.equal(
        "exactness.tolerance_parts_per_million_of_shortest_month",
        e.TIMESTAMP_TOLERANCE_SECONDS * 1_000_000 // e.SECONDS_PER_MONTH_MINIMUM,
    )
    check.equal(
        "exactness.blocks_in_shortest_month",
        e.SECONDS_PER_MONTH_MINIMUM // e.TARGET_COMMIT_SECONDS,
    )
    # The one literal a reader could not check by inspection, derived from the
    # month table on both sides rather than trusted.
    check.equal(
        "exactness.range_ends_at_the_last_milli_of_december_9999",
        e.month_end_millis(e.MAX_MONTH_INDEX) == c.MAX_TIMESTAMP_MILLIS,
    )
    check.equal("exactness.epoch_is_month_index_zero", months.month_index(0) == 0)
    check.equal("exactness.day_count_in_range", e.DAY_COUNT)


def check_leap_rule(check: Checker) -> None:
    check.section(
        "The Gregorian leap rule in full. 2000 and 2100 are the pair the "
        "abbreviated rule gets wrong, in opposite directions."
    )
    check.agree("leap.year_2024_is_a_leap_year", e.is_leap_year(2024), civil.is_leap_year(2024))
    check.agree("leap.year_2000_is_a_leap_year", e.is_leap_year(2000), civil.is_leap_year(2000))
    for year in (1970, 2000, 2024, 2026, 2100):
        check.agree(
            f"leap.february_days_{year}",
            e.month_length_days(year, 2),
            civil.days_in_month(year, 2),
        )
    check.equal("leap.days_in_400_years", e.MONTH_START_DAYS[400 * 12] - e.MONTH_START_DAYS[0])


def check_derivation_probes(check: Checker) -> None:
    check.section(
        "Instants whose month an off-by-one anywhere in the derivation would "
        "change: month edges, year edges, February in four kinds of year, and "
        "both ends of the accepted range."
    )
    for label, instant in scenario.DERIVATION_PROBES:
        timestamp = scenario.millis_of(instant)
        check.agree(
            f"derivation.{label}.timestamp", e.millis_of(instant), timestamp
        )
        check.agree(
            f"derivation.{label}.month_index",
            e.month_index(timestamp),
            months.month_index(timestamp),
        )
        year, month = months.year_month_of(timestamp)
        expected_year, expected_month = e.year_month_of(timestamp)
        check.agree(f"derivation.{label}.year", expected_year, year)
        check.agree(f"derivation.{label}.month", expected_month, month)


def check_round_trips(check: Checker) -> None:
    """Every day and every month in the accepted range, not sampled points."""
    check.section(
        "The whole accepted range walked day by day and month by month, "
        "reported as mismatch counts rather than as a claim."
    )
    day_mismatches = 0
    cross_algorithm_mismatches = 0
    for day in range(e.DAY_COUNT):
        year, month, day_of_month = civil.civil_from_days(day)
        if civil.days_from_civil(year, month, day_of_month) != day:
            day_mismatches += 1
        if e.civil_from_days(day) != (year, month, day_of_month):
            cross_algorithm_mismatches += 1
    check.equal("roundtrip.days_walked", e.DAY_COUNT)
    check.equal("roundtrip.day_inverse_mismatches", day_mismatches)
    check.equal("roundtrip.day_cross_algorithm_mismatches", cross_algorithm_mismatches)

    index_mismatches = 0
    start_off_day_boundary = 0
    end_mismatches = 0
    length_total = 0
    shortest = None
    longest = 0
    for index in range(c.MAX_MONTH_INDEX + 1):
        start = months.month_start_millis(index)
        end = months.month_end_millis(index)
        if e.month_start_millis(index) != start or e.month_end_millis(index) != end:
            cross_algorithm_mismatches += 1
        if months.month_index(start) != index:
            index_mismatches += 1
        if months.month_index(end) != index:
            end_mismatches += 1
        if start % c.MILLIS_PER_DAY != 0:
            start_off_day_boundary += 1
        length = end - start + 1
        length_total += length
        shortest = length if shortest is None else min(shortest, length)
        longest = max(longest, length)

    check.equal("roundtrip.months_walked", c.MAX_MONTH_INDEX + 1)
    check.equal("roundtrip.month_start_index_mismatches", index_mismatches)
    check.equal("roundtrip.month_end_index_mismatches", end_mismatches)
    check.equal("roundtrip.month_starts_off_a_day_boundary", start_off_day_boundary)
    check.equal("roundtrip.month_cross_algorithm_mismatches", cross_algorithm_mismatches)
    # Every month's length summed is the whole range: no millisecond belongs to
    # two months and none belongs to none.
    check.equal("roundtrip.month_length_total_millis", length_total)
    check.equal(
        "roundtrip.month_lengths_tile_the_range",
        length_total == c.MAX_TIMESTAMP_MILLIS + 1,
    )
    check.equal("roundtrip.shortest_month_millis", shortest)
    check.equal("roundtrip.longest_month_millis", longest)


def check_chain(check: Checker, chain: Calendar) -> None:
    check.section(
        "The recorded chain: a first block that closes nothing, a repeated "
        "timestamp, both milliseconds of a month boundary, and a halt long "
        "enough to leave two months with no height at all."
    )
    check.agree(
        "chain.genesis_timestamp",
        e.millis_of(scenario.GENESIS_INSTANT),
        chain.genesis_timestamp,
    )
    check.equal("chain.block_count", len(chain.blocks))

    previous: int | None = None
    opening_heights: list[int] = []
    for offset, (label, instant, _clock) in enumerate(scenario.CHAIN):
        height = c.FIRST_BLOCK_HEIGHT + offset
        timestamp = chain.timestamp_of(height)
        check.agree(
            f"chain.{label}.height", c.FIRST_BLOCK_HEIGHT + offset, chain.blocks[offset].height
        )
        check.agree(f"chain.{label}.timestamp", e.millis_of(instant), timestamp)
        check.agree(
            f"chain.{label}.month_index",
            e.month_index(timestamp),
            chain.month_of_height(height),
        )
        opens = chain.opens_a_month(height)
        if opens != e.opens_a_month(previous, timestamp):
            check.failures.append(f"chain.{label}: the two derivations disagree on opening")
        if opens:
            opening_heights.append(height)
        check.agree(
            f"chain.{label}.months_closed",
            ",".join(str(index) for index in e.months_closed_by(previous, timestamp))
            or "none",
            ",".join(str(index) for index in chain.months_closed_by(height)) or "none",
        )
        previous = timestamp

    check.equal(
        "chain.month_indices", ",".join(str(index) for index in chain.month_indices())
    )
    check.equal("chain.opening_heights", ",".join(str(h) for h in opening_heights))
    check.equal(
        "chain.empty_months", ",".join(str(index) for index in chain.empty_months())
    )
    # A repeated timestamp is accepted: C2 is non-decreasing, not strict.
    check.equal(
        "chain.a_repeated_timestamp_is_accepted",
        chain.timestamp_of(1) == chain.timestamp_of(2),
    )

    for index in sorted(set(chain.month_indices())):
        span = chain.month_height_span(index)
        assert span is not None
        check.equal(f"chain.month_{index}_first_height", span[0])
        check.equal(f"chain.month_{index}_last_height", span[1])

    check.equal("chain.head_timestamp", chain.head_timestamp)
    check.equal("chain.state_digest", chain.state_digest())


def check_tolerance_edges(check: Checker, chain: Calendar) -> None:
    check.section(
        "The tolerance is inclusive on both sides. Two of the accepted blocks "
        "were observed at exactly the edge, one on each side."
    )
    # Derived from the fixture rather than asserted: the clock offsets are the
    # scenario's, and these vectors say what they were.
    ahead = next(
        offset for label, _instant, offset in scenario.CHAIN if label == "january_last_milli"
    )
    behind = next(
        offset for label, _instant, offset in scenario.CHAIN if label == "repeated_timestamp"
    )
    check.agree("tolerance.ahead_edge_offset_millis", -e.TIMESTAMP_TOLERANCE_MILLIS, ahead)
    check.agree("tolerance.behind_edge_offset_millis", e.TIMESTAMP_TOLERANCE_MILLIS, behind)
    check.equal(
        "tolerance.both_edges_were_accepted",
        chain.head_height == len(scenario.CHAIN),
    )


def check_rejections(check: Checker, chain: Calendar) -> None:
    check.section(
        "Every rejection, produced by a live run and by the independently "
        "restated order. The three `order.` cases violate two conditions at "
        "once, so the stated order is normative rather than decorative."
    )
    head_timestamp = chain.head_timestamp
    next_height = chain.next_height
    probes = scenario.rejections(chain)
    live = scenario.rejection_codes(chain)

    for label, height_offset, timestamp, clock in probes:
        closed_form = e.acceptance_code(
            next_height,
            head_timestamp,
            next_height + height_offset,
            timestamp,
            clock,
        )
        check.agree(f"rejection.{label}", closed_form, live[label])

    genesis = scenario.genesis_boundary_codes()
    genesis_timestamp = e.millis_of(scenario.GENESIS_INSTANT)
    check.agree(
        "genesis.first_block_equal_to_genesis",
        e.acceptance_code(
            e.FIRST_BLOCK_HEIGHT,
            genesis_timestamp,
            e.FIRST_BLOCK_HEIGHT,
            genesis_timestamp,
            genesis_timestamp,
        ),
        genesis["first_block_equal_to_genesis"],
    )
    check.agree(
        "genesis.first_block_below_genesis",
        e.acceptance_code(
            e.FIRST_BLOCK_HEIGHT,
            genesis_timestamp,
            e.FIRST_BLOCK_HEIGHT,
            genesis_timestamp - 1,
            genesis_timestamp - 1,
        ),
        genesis["first_block_below_genesis"],
    )

    reached = set(live.values()) | {"ACCEPTED"}
    check.equal("coverage.codes_modelled", len(MODELLED_CODES))
    check.equal("coverage.codes_reached", len(reached))
    check.equal(
        "coverage.unreached_codes", ",".join(sorted(MODELLED_CODES - reached)) or "none"
    )
    check.equal("coverage.deterministic_codes", len(c.DETERMINISTIC_CODES))
    check.equal("coverage.admission_only_codes", len(c.ADMISSION_ONLY_CODES))
    check.equal(
        "coverage.rejection_order",
        ",".join(c.REJECTION_ORDER),
    )


def check_containment(check: Checker, chain: Calendar, digest_before: str) -> None:
    check.section(
        "A refusal writes nothing, and a replay with no clock at all reaches "
        "the chain the tolerance admitted."
    )
    check.equal(
        "containment.rejections_leave_the_chain_unchanged",
        chain.state_digest() == digest_before,
    )

    replayed = scenario.replay(chain)
    check.equal(
        "containment.replay_reaches_the_same_digest",
        replayed.state_digest() == chain.state_digest(),
    )
    check.equal(
        "containment.replay_reaches_the_same_months",
        replayed.month_indices() == chain.month_indices(),
    )
    check.equal(
        "containment.every_code_is_deterministic_or_admission_only",
        c.DETERMINISTIC_CODES | c.ADMISSION_ONLY_CODES
        == set(c.RESULT_CODES) - {"ACCEPTED"},
    )

    # The difference between the two paths, made falsifiable rather than
    # described: one stamp ten days out is offered to both.
    replay_code, admission_code = scenario.replay_ignores_the_tolerance(chain)
    check.equal(
        "containment.replay_admits_a_stamp_the_tolerance_refuses",
        replay_code == "ACCEPTED",
    )
    check.agree(
        "containment.admission_refuses_that_stamp",
        e.acceptance_code(
            chain.next_height,
            chain.head_timestamp,
            chain.next_height,
            chain.head_timestamp + scenario.REPLAY_PROBE_OFFSET_MILLIS,
            chain.head_timestamp,
        ),
        admission_code,
    )


def check_bounds(check: Checker) -> None:
    check.section(
        "The bounds a later slice needs: how far a proposer can move a "
        "boundary, and how many months a seat's span can touch."
    )
    check.agree(
        "bounds.max_boundary_shift_blocks",
        e.MAX_BOUNDARY_SHIFT_BLOCKS,
        c.MAX_BOUNDARY_SHIFT_BLOCKS,
    )
    check.agree(
        "bounds.longest_seat_span_months",
        e.longest_seat_span_months(),
        max(
            months.months_spanned(first_day, e.ISSUANCE_CYCLES_PER_SEAT)
            for first_day in range(400 * 366)
        ),
    )
    check.equal("bounds.issuance_cycles_per_seat", e.ISSUANCE_CYCLES_PER_SEAT)
    check.equal("bounds.max_day_index", e.DAY_COUNT - 1)


def check_state(check: Checker, chain: Calendar) -> None:
    check.section("The model's own state label and schema.")
    check.equal("state.schema", c.STATE_SCHEMA)
    check.equal("state.label", c.STATE_LABEL)
    check.equal("state.block_count", len(chain.blocks))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vectors",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "test-vectors" / "calendar-v1.txt",
    )
    parser.add_argument(
        "--emit",
        action="store_true",
        help="rewrite the vector file from the derivations instead of checking it",
    )
    arguments = parser.parse_args()

    # The model's own consistency guards run before anything is derived, so a
    # range that did not end where the calendar says fails here rather than
    # producing vectors nobody would question.
    c.assert_exact_derivation()
    c.assert_range_matches_the_calendar()
    c.assert_agrees_with_cycle_boundary()

    chain = scenario.build()
    if scenario.build().state_digest() != chain.state_digest():
        sys.stderr.write("the model is not deterministic across repeated runs\n")
        return 1
    digest_before_rejections = chain.state_digest()

    check = Checker(read_vectors(arguments.vectors), emit=arguments.emit)
    check_constants(check)
    check_exactness(check)
    check_leap_rule(check)
    check_derivation_probes(check)
    check_round_trips(check)
    check_chain(check, chain)
    check_tolerance_edges(check, chain)
    check_rejections(check, chain)
    check_containment(check, chain, digest_before_rejections)
    check_bounds(check)
    check_state(check, chain)
    check.require_full_coverage()

    for failure in check.failures:
        sys.stderr.write(f"vector mismatch: {failure}\n")
    if check.failures:
        return 1

    if arguments.emit:
        written = check.write(arguments.vectors)
        sys.stdout.write(f"emitted {written} calendar-v1 vectors\n")
        return 0

    sys.stdout.write(f"derived and matched {check.checked} calendar-v1 vectors\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
