#!/usr/bin/env python3
"""Independently derive and check the cycle-boundary-v1 vectors.

Every recorded value is rederived twice: once from the founder documents in
`expected.py`, which imports nothing from `simulation/`, and once from a live
run of the model. A value both sources agree on has been reached from the
Founder Constitution and from the implementation independently. Restating a
recorded value instead of deriving it would make the vector file unfalsifiable.
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

from simulation.common.canonical import CodedError
from simulation.cycle_boundary import contract as c
from simulation.cycle_boundary import grid, scenario
from simulation.cycle_boundary.model import CycleBoundary

# The result codes this model can produce. A code the scenario never reaches is
# a coverage gap, so the verifier records which ones it exercised and requires
# the set to be exactly this one.
MODELLED_CODES = frozenset(c.RESULT_CODES)

# Heights whose window membership an off-by-one in the grid would change.
GRID_PROBE_HEIGHTS: tuple[tuple[str, int], ...] = (
    ("genesis", 0),
    ("first_block", 1),
    ("window_0_last", c.CYCLE_BLOCKS - 1),
    ("window_1_first", c.CYCLE_BLOCKS),
    ("window_1_last", 2 * c.CYCLE_BLOCKS - 1),
    ("window_2_first", 2 * c.CYCLE_BLOCKS),
)


def check_constant_vectors(check: Checker) -> None:
    """The constants and the exactness the whole grid rests on."""
    check.agree("cycle.target_seconds", e.CYCLE_TARGET_SECONDS, c.CYCLE_TARGET_SECONDS)
    check.agree(
        "cycle.activity_threshold_seconds",
        e.ACTIVITY_THRESHOLD_SECONDS,
        c.ACTIVITY_THRESHOLD_SECONDS,
    )
    check.agree(
        "cycle.grace_allowance_seconds",
        e.GRACE_ALLOWANCE_SECONDS,
        c.GRACE_ALLOWANCE_SECONDS,
    )
    check.agree(
        "cycle.target_commit_seconds", e.TARGET_COMMIT_SECONDS, c.TARGET_COMMIT_SECONDS
    )
    check.agree("cycle.blocks", e.CYCLE_BLOCKS, c.CYCLE_BLOCKS)
    check.agree(
        "cycle.activity_threshold_blocks",
        e.ACTIVITY_THRESHOLD_BLOCKS,
        c.ACTIVITY_THRESHOLD_BLOCKS,
    )
    check.agree(
        "cycle.grace_allowance_blocks",
        e.GRACE_ALLOWANCE_BLOCKS,
        c.GRACE_ALLOWANCE_BLOCKS,
    )
    check.agree(
        "cycle.issuance_cycles_per_seat",
        e.ISSUANCE_CYCLES_PER_SEAT,
        c.ISSUANCE_CYCLES_PER_SEAT,
    )
    check.agree(
        "cycle.founder_seat_capacity", e.FOUNDER_SEAT_CAPACITY, c.FOUNDER_SEAT_CAPACITY
    )
    check.agree("grid.genesis_height", e.GENESIS_HEIGHT, c.GENESIS_HEIGHT)
    check.agree("grid.max_window", e.MAX_WINDOW, grid.MAX_WINDOW)

    # Every division is exact, so no founder-directed threshold is rounded.
    for name, seconds in (
        ("cycle_target", e.CYCLE_TARGET_SECONDS),
        ("activity_threshold", e.ACTIVITY_THRESHOLD_SECONDS),
        ("grace_allowance", e.GRACE_ALLOWANCE_SECONDS),
    ):
        check.equal(
            f"exactness.{name}_remainder_seconds", seconds % e.TARGET_COMMIT_SECONDS
        )

    # The two identities the economy contract states, preserved in blocks.
    check.equal(
        "identity.threshold_plus_grace_blocks",
        e.ACTIVITY_THRESHOLD_BLOCKS + e.GRACE_ALLOWANCE_BLOCKS,
    )
    check.equal(
        "identity.threshold_plus_grace_seconds",
        e.ACTIVITY_THRESHOLD_SECONDS + e.GRACE_ALLOWANCE_SECONDS,
    )
    check.equal(
        "identity.threshold_blocks_to_seconds",
        e.ACTIVITY_THRESHOLD_BLOCKS * e.TARGET_COMMIT_SECONDS,
    )

    # The nominal-duration conversion at both ends and at the threshold.
    check.equal("conversion.zero_blocks_seconds", e.uptime_seconds_for_blocks(0))
    check.equal(
        "conversion.threshold_blocks_seconds",
        e.uptime_seconds_for_blocks(e.ACTIVITY_THRESHOLD_BLOCKS),
    )
    check.equal(
        "conversion.full_window_blocks_seconds",
        e.uptime_seconds_for_blocks(e.CYCLE_BLOCKS),
    )

    check.agree(
        "storage.schedule_bytes_at_capacity",
        e.SCHEDULE_STORAGE_BYTES,
        c.SCHEDULE_STORAGE_BYTES,
    )


def check_grid_vectors(check: Checker) -> None:
    """Window membership and spans at the heights where an off-by-one shows."""
    for name, height in GRID_PROBE_HEIGHTS:
        check.agree(
            f"grid.window_of.{name}",
            e.window_of_height(height),
            grid.window_of_height(height),
        )

    for window in (0, 1, 2):
        check.agree(
            f"grid.window_{window}_first_height",
            e.window_first_height(window),
            grid.window_first_height(window),
        )
        check.agree(
            f"grid.window_{window}_last_height",
            e.window_last_height(window),
            grid.window_last_height(window),
        )
        check.equal(
            f"grid.window_{window}_height_count",
            e.window_last_height(window) - e.window_first_height(window) + 1,
        )
        # A window's first height must land back in that window.
        check.equal(
            f"grid.window_{window}_round_trip",
            e.window_of_height(e.window_first_height(window)) == window,
        )

    # Consecutive windows are adjacent with no gap and no overlap.
    check.equal(
        "grid.windows_are_contiguous",
        e.window_last_height(0) + 1 == e.window_first_height(1),
    )


def check_schedule_vectors(check: Checker, boundary: CycleBoundary) -> None:
    """Each recorded seat's span, derived from the founder rule and the model."""
    for seat_id, height in scenario.ACTIVATIONS:
        live_height, live_first, live_last = boundary.schedule(seat_id)
        check.agree(f"schedule.seat_{seat_id}.activation_height", height, live_height)
        check.agree(
            f"schedule.seat_{seat_id}.first_cycle_window",
            e.first_cycle_window(height),
            live_first,
        )
        check.agree(
            f"schedule.seat_{seat_id}.last_cycle_window",
            e.last_cycle_window(height),
            live_last,
        )
        check.equal(
            f"schedule.seat_{seat_id}.window_count", live_last - live_first + 1
        )

    # The grid is shared, not per-seat: a seat activated at genesis and one
    # activated at the last height of the same window hold the same span. If
    # windows were anchored at each seat's own activation these would differ,
    # and a reallocation would have no shared window to rank uptime in.
    genesis_span = boundary.schedule(scenario.GENESIS_SEAT)[1:]
    window_end_span = boundary.schedule(scenario.WINDOW_END_SEAT)[1:]
    check.equal("schedule.same_window_activations_share_span", genesis_span == window_end_span)

    # One block later is a different window and therefore a different span.
    window_start_span = boundary.schedule(scenario.WINDOW_START_SEAT)[1:]
    check.equal(
        "schedule.next_window_activation_shifts_span",
        window_start_span == (genesis_span[0] + 1, genesis_span[1] + 1),
    )

    # Two seats activated in the same block hold the same span.
    check.equal(
        "schedule.same_block_activations_share_span",
        boundary.schedule(scenario.INTERIOR_SEAT)[1:]
        == boundary.schedule(scenario.SAME_BLOCK_SEAT)[1:],
    )


def check_span_round_trip_vectors(check: Checker, boundary: CycleBoundary) -> None:
    """Every cycle in a complete 731-window span, not only the endpoints."""
    height = boundary.activation_heights[scenario.GENESIS_SEAT]

    mismatched_windows = 0
    mismatched_inverses = 0
    rejected_cycles = 0
    for cycle_index in range(c.ISSUANCE_CYCLES_PER_SEAT):
        closed_form = e.window_for_cycle(height, cycle_index)
        live = grid.window_for_cycle(height, cycle_index)
        if closed_form != live:
            mismatched_windows += 1
        if grid.cycle_for_window(height, live) != cycle_index:
            mismatched_inverses += 1
        if boundary.check_window(scenario.GENESIS_SEAT, cycle_index, live).code != "ACCEPTED":
            rejected_cycles += 1

    check.equal("span.cycles_walked", c.ISSUANCE_CYCLES_PER_SEAT)
    check.equal("span.window_mismatches", mismatched_windows)
    check.equal("span.inverse_mismatches", mismatched_inverses)
    check.equal("span.rejected_cycles", rejected_cycles)

    # The two windows immediately outside the span invert to no cycle at all.
    check.equal(
        "span.window_before_inverts_to_nothing",
        grid.cycle_for_window(height, e.first_cycle_window(height) - 1) is None,
    )
    check.equal(
        "span.window_after_inverts_to_nothing",
        grid.cycle_for_window(height, e.last_cycle_window(height) + 1) is None,
    )
    check.agree("span.length", e.ISSUANCE_CYCLES_PER_SEAT, grid.span_length(height))


def check_rejection_vectors(check: Checker, boundary: CycleBoundary) -> None:
    """Every rejection, produced by a live run and by the independent order."""
    live_activation_codes = scenario.activation_rejection_codes()
    accepted = dict(scenario.ACTIVATIONS)
    last_height = scenario.ACTIVATIONS[-1][1]
    for label, seat_id, height in scenario.ACTIVATION_REJECTIONS:
        closed_form = e.record_activation(accepted, last_height, seat_id, height)
        check.agree(
            f"activation.{label}", closed_form, live_activation_codes[label]
        )

    live_check_codes = scenario.check_codes()
    for label, seat_id, cycle_index, cycle_window in scenario.CHECKS:
        closed_form = e.check_window(accepted, seat_id, cycle_index, cycle_window)
        check.agree(f"check.{label}", closed_form, live_check_codes[label])

    # Every modelled code is reached, so a later scenario cannot quietly lose
    # coverage while still passing every other vector.
    reached = set(live_activation_codes.values()) | set(live_check_codes.values())
    check.equal("coverage.codes_reached", len(reached))
    check.equal("coverage.codes_modelled", len(MODELLED_CODES))
    check.equal("coverage.unreached_codes", ",".join(sorted(MODELLED_CODES - reached)) or "none")

    # A rejection writes nothing. This must be measured on one instance across
    # the attempts: comparing two separately built models would only show that
    # the model is deterministic, which is a different claim.
    probe = scenario.build()
    before_rejections = probe.state_digest()
    for _, seat_id, height in scenario.ACTIVATION_REJECTIONS:
        try:
            probe.record_activation(seat_id, height)
        except CodedError:
            pass
    check.equal(
        "containment.rejections_leave_state_unchanged",
        probe.state_digest() == before_rejections,
    )

    # A check is a pure query and cannot alter a schedule.
    before_digest = boundary.state_digest()
    for _, seat_id, cycle_index, cycle_window in scenario.CHECKS:
        boundary.check_window(seat_id, cycle_index, cycle_window)
    check.equal(
        "containment.checks_leave_state_unchanged",
        boundary.state_digest() == before_digest,
    )


def check_overflow_vectors(check: Checker) -> None:
    """Guards proved present rather than reached at any plausible height."""
    check.agree(
        "overflow.max_height_span_representable",
        e.span_is_representable(e.MAX_U64),
        grid.span_is_representable(c.MAX_HEIGHT),
    )
    highest_usable = (e.MAX_WINDOW - e.MAX_CYCLE_INDEX - 1) * e.CYCLE_BLOCKS
    check.agree(
        "overflow.highest_usable_activation_representable",
        e.span_is_representable(highest_usable),
        grid.span_is_representable(highest_usable),
    )
    check.equal("overflow.highest_usable_activation_height", highest_usable)
    # How unreachable the guard is, as a number rather than a claim: the count
    # of complete back-to-back 731-window seat spans the grid represents.
    check.equal(
        "overflow.representable_seat_spans", e.MAX_WINDOW // e.ISSUANCE_CYCLES_PER_SEAT
    )


def check_state_vectors(check: Checker, boundary: CycleBoundary) -> None:
    check.equal("state.schema", c.STATE_SCHEMA)
    check.equal("state.label", c.STATE_LABEL)
    check.equal("state.seat_count", len(boundary.activation_heights))
    check.equal("state.last_activation_height", boundary.last_activation_height)
    check.equal("state.digest", boundary.state_digest())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vectors",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "test-vectors"
        / "cycle-boundary-v1.txt",
    )
    arguments = parser.parse_args()

    # The model's own consistency guards run before anything is derived, so a
    # grid that could not represent a founder threshold exactly fails here
    # rather than producing vectors nobody would question.
    c.assert_exact_derivation()
    c.assert_agrees_with_economy()

    boundary = scenario.build()
    if scenario.build().state_digest() != boundary.state_digest():
        sys.stderr.write("the model is not deterministic across repeated runs\n")
        return 1

    check = Checker(read_vectors(arguments.vectors))
    check_constant_vectors(check)
    check_grid_vectors(check)
    check_schedule_vectors(check, boundary)
    check_span_round_trip_vectors(check, boundary)
    check_rejection_vectors(check, boundary)
    check_overflow_vectors(check)
    check_state_vectors(check, boundary)
    check.require_full_coverage()

    for failure in check.failures:
        sys.stderr.write(f"vector mismatch: {failure}\n")
    if check.failures:
        return 1

    sys.stdout.write(f"derived and matched {check.checked} cycle-boundary-v1 vectors\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
