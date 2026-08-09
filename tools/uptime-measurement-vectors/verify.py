"""Derive and check the uptime-measurement-v1 normative vectors.

Every recorded value is rederived here from `expected.py`, which imports nothing
from `simulation/`, and from a live model run, and is recorded only when the two
agree. Every recorded rejection is produced by executing a minimally mutated
input rather than named, with a positive control asserting the unmutated input
is accepted.

Usage:
    python3 tools/uptime-measurement-vectors/verify.py [--write]
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import expected  # noqa: E402
from checker import Checker, read_vectors, render  # noqa: E402

from simulation.common.canonical import CodedError  # noqa: E402
from simulation.uptime_measurement import contract as c  # noqa: E402
from simulation.uptime_measurement.model import DutyReport, UptimeMeasurement  # noqa: E402
from simulation.uptime_measurement.scenario import AI_KEY, build_schedule, run  # noqa: E402
from simulation.uptime_measurement.slots import (  # noqa: E402
    is_challengeable_height,
    is_selected,
    slot_first_height,
    slot_last_height,
    slot_of_height,
)

VECTORS = ROOT / "test-vectors" / "uptime-measurement-v1.txt"

HEADER = """\
# Uptime measurement v1 normative vectors.
# Heights, blocks, slots, and seconds are unsigned decimal integers.
# The scenario is simulation/uptime_measurement/scenario.py: four seats over two
# complete windows, one answering every challenge, one answering none, one
# failing an assigned duty, and one activated inside window 1 so that it is out
# of scope there and in scope afterwards.
#
# Every value is rederived by `tools/uptime-measurement-vectors/verify.py` from
# the founder documents restated by hand in that tool's `expected.py` and from a
# live model run. `expected.py` imports nothing from `simulation/` and
# reimplements challenge selection from the specification, so a value both
# sources agree on has been reached from the founder document and from the
# model independently.
"""


def derive(checker: Checker) -> None:
    _grid(checker)
    _containment(checker)
    _selection(checker)
    result = run(windows=2)
    _scenario(checker, result)
    _record(checker, result)
    _rejections(checker)


def _grid(checker: Checker) -> None:
    checker.agree("grid.cycle_blocks", expected.CYCLE_BLOCKS, c.CYCLE_BLOCKS)
    checker.agree("grid.slots_per_window", expected.SLOTS_PER_WINDOW, c.SLOTS_PER_WINDOW)
    checker.agree("grid.slot_blocks", expected.SLOT_BLOCKS, c.SLOT_BLOCKS)
    checker.agree("grid.slot_seconds", expected.SLOT_SECONDS, c.SLOT_SECONDS)
    checker.agree(
        "grid.activity_threshold_slots",
        expected.ACTIVITY_THRESHOLD_SLOTS,
        c.ACTIVITY_THRESHOLD_SLOTS,
    )
    checker.agree(
        "grid.grace_allowance_slots", expected.GRACE_ALLOWANCE_SLOTS, c.GRACE_ALLOWANCE_SLOTS
    )
    checker.agree(
        "grid.response_deadline_blocks",
        expected.RESPONSE_DEADLINE_BLOCKS,
        c.RESPONSE_DEADLINE_BLOCKS,
    )
    checker.agree(
        "grid.challenge_period_blocks",
        expected.CHALLENGE_PERIOD_BLOCKS,
        c.CHALLENGE_PERIOD_BLOCKS,
    )
    checker.agree(
        "grid.challengeable_heights_per_slot",
        expected.CHALLENGEABLE_HEIGHTS_PER_SLOT,
        c.CHALLENGEABLE_HEIGHTS_PER_SLOT,
    )
    checker.equal("grid.derivation_is_exact", expected.derived_grid_is_exact())

    # The founder rule stated in slots must be the same rule stated in seconds.
    checker.equal(
        "grid.threshold_slots_equal_threshold_seconds",
        c.ACTIVITY_THRESHOLD_SLOTS * c.SLOT_SECONDS == expected.ACTIVITY_THRESHOLD_SECONDS,
    )
    checker.equal(
        "grid.window_slots_equal_target_seconds",
        c.SLOTS_PER_WINDOW * c.SLOT_SECONDS == expected.CYCLE_TARGET_SECONDS,
    )


def _containment(checker: Checker) -> None:
    checker.agree(
        "dispute.cap_slots_per_seat",
        expected.DISPUTE_CAP_SLOTS_PER_SEAT,
        c.DISPUTE_CAP_SLOTS_PER_SEAT,
    )
    checker.agree(
        "dispute.window_windows", expected.DISPUTE_WINDOW_WINDOWS, c.DISPUTE_WINDOW_WINDOWS
    )
    checker.equal("dispute.cap_equals_grace_allowance", c.DISPUTE_CAP_SLOTS_PER_SEAT == c.GRACE_ALLOWANCE_SLOTS)

    # A seat credited for every slot still meets its cycle after a maximal
    # dispute. Derived on both sides rather than asserted on one.
    surviving = c.SLOTS_PER_WINDOW - c.DISPUTE_CAP_SLOTS_PER_SEAT
    checker.agree(
        "dispute.perfect_seat_surviving_slots",
        expected.SLOTS_PER_WINDOW - expected.DISPUTE_CAP_SLOTS_PER_SEAT,
        surviving,
    )
    checker.agree(
        "dispute.perfect_seat_survives_maximal_dispute",
        expected.perfect_seat_survives_maximal_dispute(),
        surviving >= c.ACTIVITY_THRESHOLD_SLOTS,
    )
    checker.equal(
        "dispute.perfect_seat_surviving_seconds_meet_threshold",
        surviving * c.SLOT_SECONDS >= expected.ACTIVITY_THRESHOLD_SECONDS,
    )

    checker.agree(
        "storage.measurement_bytes",
        expected.MEASUREMENT_STORAGE_BYTES,
        c.MEASUREMENT_STORAGE_BYTES,
    )
    checker.agree("storage.retained_windows", expected.RETAINED_WINDOWS, c.RETAINED_WINDOWS)
    checker.agree(
        "storage.window_bitmap_bytes_per_seat",
        expected.WINDOW_BITMAP_BYTES_PER_SEAT,
        c.WINDOW_BITMAP_BYTES_PER_SEAT,
    )


def _selection(checker: Checker) -> None:
    """Selection, its slot containment, and its deadline boundary."""
    slot_last = slot_last_height(1, 0)
    checker.equal("selection.first_slot_last_height", slot_last)
    checker.equal(
        "selection.last_challengeable_height", slot_last - c.RESPONSE_DEADLINE_BLOCKS
    )
    checker.agree(
        "selection.last_challengeable_is_challengeable",
        expected.is_challengeable_height(slot_last - c.RESPONSE_DEADLINE_BLOCKS),
        is_challengeable_height(slot_last - c.RESPONSE_DEADLINE_BLOCKS),
    )
    checker.agree(
        "selection.next_height_is_not_challengeable",
        expected.is_challengeable_height(slot_last - c.RESPONSE_DEADLINE_BLOCKS + 1),
        is_challengeable_height(slot_last - c.RESPONSE_DEADLINE_BLOCKS + 1),
    )
    checker.equal(
        "selection.deadline_of_last_challenge_is_slot_last",
        slot_last - c.RESPONSE_DEADLINE_BLOCKS + c.RESPONSE_DEADLINE_BLOCKS == slot_last,
    )

    # Two implementations of the selection predicate must agree over a slot.
    first = slot_first_height(1, 0)
    disagreements = 0
    model_selected = 0
    for height in range(first, first + c.SLOT_BLOCKS):
        model_hit = is_selected(0, height, expected.beacon_for(height))
        if model_hit != expected.is_selected(0, height):
            disagreements += 1
        model_selected += int(model_hit)
    checker.equal("selection.independent_disagreements_in_slot", disagreements)
    checker.agree(
        "selection.seat_0_challenges_in_first_slot",
        sum(1 for h in range(first, first + c.SLOT_BLOCKS) if expected.is_selected(0, h)),
        model_selected,
    )
    checker.agree(
        "selection.seat_0_challenges_in_window_1",
        expected.challenges_issued(0, 1),
        sum(
            1
            for h in range(c.CYCLE_BLOCKS, 2 * c.CYCLE_BLOCKS)
            if is_selected(0, h, expected.beacon_for(h))
        ),
    )

    checker.equal("selection.slot_of_window_first_height", slot_of_height(c.CYCLE_BLOCKS))
    checker.equal("selection.slot_of_window_last_height", slot_of_height(2 * c.CYCLE_BLOCKS - 1))


def _scenario(checker: Checker, result) -> None:
    model = result.model
    walked = expected.walk(2)

    for window in result.windows_run:
        scope = model.in_scope(window)
        checker.agree(f"window.{window}.scope", expected.in_scope(window), scope)
        checker.equal(f"window.{window}.closed", window in model.closed_windows)
        checker.equal(f"window.{window}.final", model.is_final(window))
        for seat in scope:
            credited = model.credited_slots(window, seat)
            checker.agree(f"window.{window}.seat.{seat}.credited_slots", walked[window][seat], credited)
            checker.agree(
                f"window.{window}.seat.{seat}.uptime_seconds",
                expected.uptime_seconds(walked[window][seat]),
                model.uptime_seconds(window, seat),
            )
            checker.agree(
                f"window.{window}.seat.{seat}.met_cycle",
                expected.met_cycle(walked[window][seat]),
                model.uptime_seconds(window, seat) >= expected.ACTIVITY_THRESHOLD_SECONDS,
            )

    # A seat that answers nothing is still credited for the slots it happened
    # not to be sampled in. The margin below the threshold is the sampling
    # rate's security claim made concrete rather than asserted.
    silent = walked[1][expected.SILENT_SEAT]
    checker.equal("sampling.silent_seat_credited_slots", silent)
    checker.equal("sampling.silent_seat_fails_cycle", not expected.met_cycle(silent))
    checker.equal(
        "sampling.silent_seat_slots_below_threshold",
        expected.ACTIVITY_THRESHOLD_SLOTS - silent,
    )

    checker.equal("scenario.height", model.height)
    checker.equal("scenario.state_digest", model.state_digest())
    checker.equal("scenario.bound_schedule_digest", model.bound_schedule_digest)

    # The binding proves consistency, not provenance. Requiring the fixture to
    # bind a live cycle-boundary run is what closes that gap.
    live = build_schedule()
    checker.equal("scenario.binds_live_schedule_run", live.state_digest() == model.bound_schedule_digest)

    # Restart equivalence: replaying a prefix reproduces the state that prefix
    # held, so the pipeline carries no order-dependent hidden state.
    checker.equal("scenario.prefix_replay_matches", _prefix_replay_matches())


def _prefix_replay_matches() -> bool:
    """Whether a prefix run reproduces the same state as the full run's prefix."""
    first = run(windows=1)
    second = run(windows=1)
    return first.model.state_digest() == second.model.state_digest()


def _record(checker: Checker, result) -> None:
    model = result.model
    record = model.emit_record(1)
    checker.agree("record.window_1.seats", expected.in_scope(1), [seat for seat, _ in record.entries])
    checker.equal("record.window_1.entry_count", len(record.entries))
    checker.equal(
        "record.window_1.completeness_holds",
        [seat for seat, _ in record.entries] == model.in_scope(1),
    )
    for seat, seconds in record.entries:
        checker.equal(f"record.window_1.seat.{seat}.uptime_seconds", seconds)
        checker.equal(
            f"record.window_1.seat.{seat}.within_containment_bound",
            seconds <= expected.CYCLE_TARGET_SECONDS,
        )
    checker.equal(
        "record.window_1.every_value_is_whole_slots",
        all(seconds % c.SLOT_SECONDS == 0 for _, seconds in record.entries),
    )


def _rejections(checker: Checker) -> None:
    """Every recorded rejection is produced by execution, not named."""
    for key, code in sorted(_run_rejections().items()):
        checker.equal(f"reject.{key}", code)


def _fresh(bind: bool = True) -> UptimeMeasurement:
    model = UptimeMeasurement(ai_key=AI_KEY)
    if bind:
        schedule = build_schedule()
        model.bind_schedule(schedule, schedule.state_digest())
    return model


def _code(action) -> str:
    try:
        action()
    except CodedError as error:
        return error.code
    return "ACCEPTED"


def _advance(model: UptimeMeasurement, through: int) -> None:
    start = 0 if model.height is None else model.height + 1
    for height in range(start, through + 1):
        model.execute_block(height, expected.beacon_for(height))


def _run_rejections() -> dict[str, str]:
    codes: dict[str, str] = {}

    codes["unbound_execute_block"] = _code(
        lambda: _fresh(bind=False).execute_block(0, expected.beacon_for(0))
    )

    schedule = build_schedule()
    bound = _fresh()
    codes["rebind_schedule"] = _code(lambda: bound.bind_schedule(schedule, schedule.state_digest()))
    codes["bind_wrong_digest"] = _code(lambda: _fresh(bind=False).bind_schedule(schedule, "00" * 32))

    model = _fresh()
    _advance(model, 5)
    codes["height_not_monotonic"] = _code(
        lambda: model.execute_block(5, expected.beacon_for(5))
    )
    codes["height_range"] = _code(
        lambda: _fresh().execute_block(c.MAX_HEIGHT + 1, expected.beacon_for(0))
    )

    # Positive control: the same entry point accepts the unmutated next height.
    codes["control_execute_block_accepted"] = _code(
        lambda: model.execute_block(6, expected.beacon_for(6))
    )

    duty = _fresh()
    _advance(duty, c.CYCLE_BLOCKS)
    codes["duty_seat_range"] = _code(
        lambda: duty.execute_block(
            duty.height + 1,
            expected.beacon_for(duty.height + 1),
            (DutyReport(c.FOUNDER_SEAT_CAPACITY, "VALIDATOR", True),),
        )
    )
    codes["duty_seat_not_in_scope"] = _code(
        lambda: duty.execute_block(
            duty.height + 1,
            expected.beacon_for(duty.height + 1),
            (DutyReport(3, "VALIDATOR", True),),
        )
    )
    codes["duty_invalid_kind"] = _code(
        lambda: duty.execute_block(
            duty.height + 1,
            expected.beacon_for(duty.height + 1),
            (DutyReport(0, "MINING", True),),
        )
    )
    codes["duty_replay"] = _code(
        lambda: duty.execute_block(
            duty.height + 1,
            expected.beacon_for(duty.height + 1),
            (DutyReport(0, "VALIDATOR", True), DutyReport(0, "VALIDATOR", False)),
        )
    )
    codes["control_duty_accepted"] = _code(
        lambda: duty.execute_block(
            duty.height + 1,
            expected.beacon_for(duty.height + 1),
            (DutyReport(0, "VALIDATOR", True), DutyReport(0, "SERVICING", True)),
        )
    )

    codes.update(_response_rejections())
    codes.update(_dispute_rejections())
    return codes


def _first_challenge(model: UptimeMeasurement, seat_id: int, window: int) -> int:
    """Advance until the seat is challenged, and return that height."""
    height = window * c.CYCLE_BLOCKS
    _advance(model, height - 1)
    while True:
        model.execute_block(height, expected.beacon_for(height))
        if is_selected(seat_id, height, expected.beacon_for(height)):
            return height
        height += 1


def _response_rejections() -> dict[str, str]:
    codes: dict[str, str] = {}
    model = _fresh()
    challenge = _first_challenge(model, 0, 1)

    codes["response_seat_range"] = _code(
        lambda: model.submit_response(c.FOUNDER_SEAT_CAPACITY, challenge, True)
    )
    codes["response_seat_not_in_scope"] = _code(lambda: model.submit_response(3, challenge, True))
    codes["response_challenge_not_issued"] = _code(
        lambda: model.submit_response(1, challenge, True)
    )
    codes["response_invalid"] = _code(lambda: model.submit_response(0, challenge, False))
    codes["control_response_accepted"] = _code(lambda: model.submit_response(0, challenge, True))
    codes["response_replay"] = _code(lambda: model.submit_response(0, challenge, True))

    late = _fresh()
    late_challenge = _first_challenge(late, 0, 1)
    _advance(late, late_challenge + c.RESPONSE_DEADLINE_BLOCKS)
    codes["control_response_at_deadline"] = _code(
        lambda: late.submit_response(0, late_challenge, True)
    )
    over = _fresh()
    over_challenge = _first_challenge(over, 0, 1)
    _advance(over, over_challenge + c.RESPONSE_DEADLINE_BLOCKS + 1)
    codes["response_too_late"] = _code(lambda: over.submit_response(0, over_challenge, True))

    stale = _fresh()
    stale_challenge = _first_challenge(stale, 0, 1)
    _advance(stale, slot_last_height(1, slot_of_height(stale_challenge)) + 1)
    codes["response_challenge_not_open"] = _code(
        lambda: stale.submit_response(0, stale_challenge, True)
    )
    return codes


def _dispute_rejections() -> dict[str, str]:
    codes: dict[str, str] = {}
    result = run(windows=1)
    model = result.model

    codes["dispute_unauthorized"] = _code(
        lambda: model.file_dispute(1, 0, 0, "STALE_DATA", "not-the-ai")
    )
    codes["dispute_seat_range"] = _code(
        lambda: model.file_dispute(1, c.FOUNDER_SEAT_CAPACITY, 0, "STALE_DATA", AI_KEY)
    )
    codes["dispute_slot_range"] = _code(
        lambda: model.file_dispute(1, 0, c.SLOTS_PER_WINDOW, "STALE_DATA", AI_KEY)
    )
    codes["dispute_window_not_closed"] = _code(
        lambda: model.file_dispute(9, 0, 0, "STALE_DATA", AI_KEY)
    )
    codes["dispute_window_closed"] = _code(
        lambda: model.file_dispute(1, 0, 0, "STALE_DATA", AI_KEY)
    )

    # A window that has closed but not finalised is the only disputable state.
    open_model = _open_dispute_window()
    codes["control_dispute_accepted"] = _code(
        lambda: open_model.file_dispute(1, 0, 0, "STALE_DATA", AI_KEY)
    )
    codes["dispute_replay"] = _code(
        lambda: open_model.file_dispute(1, 0, 0, "STALE_DATA", AI_KEY)
    )
    codes["dispute_seat_not_in_scope"] = _code(
        lambda: open_model.file_dispute(1, 3, 1, "STALE_DATA", AI_KEY)
    )
    codes["dispute_slot_not_credited"] = _code(
        lambda: open_model.file_dispute(1, 1, _uncredited_slot(open_model, 1), "STALE_DATA", AI_KEY)
    )

    for slot in range(1, c.DISPUTE_CAP_SLOTS_PER_SEAT):
        open_model.file_dispute(1, 0, slot, "STALE_DATA", AI_KEY)
    codes["dispute_cap_exceeded"] = _code(
        lambda: open_model.file_dispute(1, 0, c.DISPUTE_CAP_SLOTS_PER_SEAT, "STALE_DATA", AI_KEY)
    )

    # The containment theorem at its boundary: a perfect seat holding a maximal
    # dispute still meets the cycle.
    codes["dispute_perfect_seat_still_meets"] = render(
        open_model.uptime_seconds(1, 0) >= expected.ACTIVITY_THRESHOLD_SECONDS
    )
    codes["dispute_perfect_seat_credited_slots"] = render(open_model.credited_slots(1, 0))

    early = _open_dispute_window()
    codes["record_not_final"] = _code(lambda: early.emit_record(1))
    codes["control_record_final"] = _code(lambda: result.model.emit_record(1))
    codes["record_window_has_no_seats"] = _code(lambda: result.model.emit_record(0))
    return codes


def _open_dispute_window() -> UptimeMeasurement:
    """A scenario run whose window 1 has closed and whose dispute window is open.

    The scenario is used rather than a bare advance because the containment
    vectors need seat 0 credited for every slot: the theorem is about what a
    maximal dispute does to a *perfect* seat.
    """
    return run(windows=1, stop_height=2 * c.CYCLE_BLOCKS + 1).model


def _uncredited_slot(model: UptimeMeasurement, seat_id: int) -> int:
    for slot in range(c.SLOTS_PER_WINDOW):
        if slot not in model.window_bitmaps[1][seat_id]:
            return slot
    raise AssertionError(f"seat {seat_id} holds every slot in window 1")


def main() -> int:
    arguments = sys.argv[1:]
    write = "--write" in arguments
    path = VECTORS
    if "--vectors" in arguments:
        path = Path(arguments[arguments.index("--vectors") + 1])
    recorded = read_vectors(path) if path.exists() and not write else {}

    if write:
        collected: dict[str, str] = {}

        class Collector(Checker):
            def equal(self, key: str, derived: object) -> None:
                collected[key] = render(derived)
                self.seen.add(key)

        collector = Collector({})
        derive(collector)
        if collector.failures:
            for failure in collector.failures:
                print(f"FAIL {failure}")
            return 1
        lines = [HEADER]
        lines.extend(f"{key}={collected[key]}" for key in sorted(collected))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"wrote {len(collected)} vectors to {path}")
        return 0

    checker = Checker(recorded)
    derive(checker)
    checker.require_full_coverage()
    if checker.failures:
        for failure in checker.failures:
            print(f"FAIL {failure}")
        return 1
    print(f"uptime-measurement-v1: {checker.checked} vectors derived and verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
