"""Adversarial events appended once every population window is complete.

Every event named `probe-` must be rejected, and each reaches a different
condition. The seven conditions version three added are reached here rather than
only in the model's own research scenario, because a defect in the enforced
schedule is most likely to appear after a complete multi-year run rather than in
a short fixture.

Three events are named `peer-` and are accepted. They exist because version
three checks a window before it checks the binding: a contradictory record can
now only be presented inside a window the evaluating seat genuinely holds, so
some other seat must first have bound one there. `PEER_SEAT` shares
`PROBE_SEAT`'s activation height for exactly that reason.
"""

from __future__ import annotations

from typing import Any

from ..cycle_boundary.grid import last_cycle_window
from ..founder_economy_v3 import contract as c
from .economy_schedule_v3 import (
    FAILED_UPTIME,
    LAST_CYCLE,
    LAST_TICK,
    LATE_HEIGHT,
    LATE_SEAT,
    PEER_SEAT,
    PROBE_HEIGHT,
    PROBE_SEAT,
    PROBE_WINDOW,
    THRESHOLD_UPTIME,
    UNKNOWN_SEAT,
    WINNER_UPTIME,
    accrue,
    activate,
    base,
    exercise,
    in_scope_at_window,
    record_over,
    uptime_record,
)

# The probe seats' first window is their cycle 0, so every window probe below is
# a statement about one cycle rather than about a schedule position.
PROBE_CYCLE = 0


def probe_scope() -> tuple[int, ...]:
    """The seat set a record at the probe window must cover exactly."""
    return in_scope_at_window(PROBE_WINDOW)


def complete_record() -> dict[str, Any]:
    """The record `PEER_SEAT` binds: exactly the in-scope set, and complete.

    `PROBE_SEAT` is recorded as having failed its cycle. That is what makes the
    contradictory probe below adversarial rather than merely different: the seat
    whose window already records a failed cycle is the one that later presents a
    record claiming a full one.
    """
    uptimes = {seat_id: THRESHOLD_UPTIME for seat_id in probe_scope()}
    uptimes[PROBE_SEAT] = FAILED_UPTIME
    return record_over(PROBE_WINDOW, uptimes)


def disagreeing_record() -> dict[str, Any]:
    """The same window and the same complete seat set, one measurement raised.

    A seat cannot improve its own recorded uptime by presenting a better record
    for a window that has already been measured.
    """
    uptimes = {seat_id: THRESHOLD_UPTIME for seat_id in probe_scope()}
    uptimes[PROBE_SEAT] = WINNER_UPTIME
    return record_over(PROBE_WINDOW, uptimes)


def _only_probe_seat(window: int) -> dict[str, Any]:
    """A well-formed record naming one seat, used to isolate a window code."""
    return record_over(window, {PROBE_SEAT: THRESHOLD_UPTIME})


def _without_probe_seat() -> dict[str, Any]:
    uptimes = {
        seat_id: THRESHOLD_UPTIME
        for seat_id in probe_scope()
        if seat_id != PROBE_SEAT
    }
    return record_over(PROBE_WINDOW, uptimes)


def _with_late_seat() -> dict[str, Any]:
    """The complete set plus a seat whose own schedule has not opened yet."""
    uptimes = {seat_id: THRESHOLD_UPTIME for seat_id in probe_scope()}
    uptimes[LATE_SEAT] = THRESHOLD_UPTIME
    return record_over(PROBE_WINDOW, uptimes)


def _direct_referral() -> dict[str, Any]:
    """`founder_referral` is a direct-mint channel `direct_issue` must refuse.

    Admitting it would let a supplied eligibility fixture mint referral units
    outside the per-seat-cycle accounting, so the containment is exercised here
    rather than only stated in ADR 0025.
    """
    return {
        "id": "probe-direct-referral",
        "kind": "direct_issue",
        "channel": c.REFERRAL_CHANNEL,
        "decision_id": "probe-referral-decision",
        "beneficiary_id": "probe-beneficiary",
        "amount_atomic": str(c.REFERRAL_AMOUNT),
        "eligibility_result": {
            "channel": c.REFERRAL_CHANNEL,
            "decision_id": "probe-referral-decision",
            "beneficiary_id": "probe-beneficiary",
            "amount_atomic": str(c.REFERRAL_AMOUNT),
            "eligible": True,
        },
    }


def boundary_probes() -> list[dict[str, Any]]:
    """The ordered probe block.

    The four window and completeness probes precede the peer's binding, so each
    reaches an intrinsic property of the record and the schedule while nothing is
    bound at the probe window. The contradiction probe follows it, because that
    condition is a property of what an earlier event bound. A rejected event
    binds nothing, so the six refused records leave the window free.

    Every probe carries its own event identifier, because a repeated identifier
    is an input-shape error that would abort the run instead of producing a
    trace record.
    """
    probes = [
        (
            "probe-cycle-beyond-window",
            base(0, c.ISSUANCE_CYCLES_PER_SEAT, uptime_record(LAST_TICK)),
        ),
        ("probe-base-replay", base(0, LAST_CYCLE, uptime_record(LAST_CYCLE))),
        ("probe-exercise-replay", exercise(0, LAST_CYCLE)),
        # A monotonic-valid height, so a replayed activation is refused for
        # being a replay rather than for the schedule it carries.
        ("probe-activation-replay", activate(0, None, LATE_HEIGHT)),
        ("probe-height-range", activate(UNKNOWN_SEAT, None, c.MAX_HEIGHT)),
        ("probe-height-not-monotonic", activate(UNKNOWN_SEAT, None, 0)),
        ("probe-missing-uptime-record", base(PROBE_SEAT, PROBE_CYCLE, None)),
        (
            "probe-invalid-uptime-record",
            base(PROBE_SEAT, PROBE_CYCLE, _without_probe_seat()),
        ),
        (
            "probe-window-before-issuance",
            base(PROBE_SEAT, PROBE_CYCLE, _only_probe_seat(PROBE_WINDOW - 1)),
        ),
        (
            "probe-window-after-issuance",
            base(
                PROBE_SEAT,
                PROBE_CYCLE,
                _only_probe_seat(last_cycle_window(PROBE_HEIGHT) + 1),
            ),
        ),
        (
            "probe-window-not-for-cycle",
            base(PROBE_SEAT, PROBE_CYCLE, _only_probe_seat(PROBE_WINDOW + 1)),
        ),
        ("probe-seat-not-in-scope", base(PROBE_SEAT, PROBE_CYCLE, _with_late_seat())),
        (
            "probe-incomplete-uptime-record",
            base(PROBE_SEAT, PROBE_CYCLE, _only_probe_seat(PROBE_WINDOW)),
        ),
        ("peer-base-probe-window", base(PEER_SEAT, PROBE_CYCLE, complete_record())),
        ("peer-exercise-probe-window", exercise(PEER_SEAT, PROBE_CYCLE)),
        ("peer-accrue-probe-window", accrue(PEER_SEAT, PROBE_CYCLE)),
        (
            "probe-inconsistent-uptime-record",
            base(PROBE_SEAT, PROBE_CYCLE, disagreeing_record()),
        ),
        ("probe-accrual-replay", accrue(0, 0)),
        ("probe-direct-referral", _direct_referral()),
    ]
    return [{**event, "id": event_id} for event_id, event in probes]
