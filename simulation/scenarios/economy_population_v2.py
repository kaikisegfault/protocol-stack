"""A complete 731-cycle run over a staggered Founder Seat population, v2.

The Founder Constitution gives each seat 731 eligible cycles beginning at its
own first activation, so seats activated on different dates hold different
windows. The model has no global clock, so the stagger is expressed as event
order: at tick `t` the seat activated at tick `k * STAGGER` evaluates its own
cycle `t - k * STAGGER`. Every seat therefore completes exactly 731 cycles
while three windows overlap in different phases throughout the run.

Version two differs from `economy_population` in shape, not only in parameters.
Inactivity and the performance recipient are no longer supplied research inputs:
this generator emits a cycle uptime record carrying measurements only, and the
model derives the activity verdict and the winner set from it. The referral is
no longer a permission, so a cycle emits one unconditional accrual instead of an
evaluation and a second exercise.

The tick is the shared `cycle_window`. That is the whole reason a window is a
separate field from a seat's `cycle_index`: seats staggered 61 ticks apart are
at different cycle indices in the same window, and reallocation to "the highest
uptime in that same cycle" is only meaningful against a shared one.
"""

from __future__ import annotations

from typing import Any

from ..founder_economy_v2 import contract as c

SEATS = 3
# Seat 0 refers both other seats, so one referrer accumulates the referral
# benefit of two seats across the whole multi-year window. Seat 0 is itself
# unreferred, so its own accruals reach the unreferred performance pool and the
# run exercises both destinations of the channel.
REFERRERS: dict[int, int | None] = {0: None, 1: 0, 2: 0}

# Activated but never evaluated, so a boundary probe has an unevaluated
# (seat, cycle) key to reach the uptime rejections with. Every population seat's
# 731 cycles are consumed by the run itself.
PROBE_SEAT = 3

# Ticks between consecutive activations. Prime, and far below the 731-cycle
# window, so every pair of windows overlaps for most of the run.
STAGGER = 61

# A seat is inactive when `(cycle + INACTIVE_PHASE * seat) % INACTIVE_PERIOD`
# is zero. The phase shift keeps the three seats' inactive cycles disjoint in
# every window, which `failing_seat` asserts rather than assumes.
INACTIVE_PERIOD = 73
INACTIVE_PHASE = 7

# Uptime in whole seconds. A failed cycle is far below the threshold; the
# intended winner is at the full cycle target; every other seat sits exactly on
# the 64,800-second threshold, so the boundary is exercised in every window that
# reallocates rather than only in a dedicated test.
FAILED_UPTIME = 3_600
WINNER_UPTIME = c.CYCLE_TARGET_SECONDS
THRESHOLD_UPTIME = c.ACTIVITY_THRESHOLD_SECONDS

LAST_CYCLE = c.ISSUANCE_CYCLES_PER_SEAT - 1
LAST_TICK = LAST_CYCLE + (SEATS - 1) * STAGGER


def cycle_at(seat_id: int, tick: int) -> int | None:
    """The seat's own cycle index at this tick, or None when out of window."""
    cycle_index = tick - seat_id * STAGGER
    if 0 <= cycle_index < c.ISSUANCE_CYCLES_PER_SEAT:
        return cycle_index
    return None


def is_inactive(seat_id: int, cycle_index: int) -> bool:
    return (cycle_index + INACTIVE_PHASE * seat_id) % INACTIVE_PERIOD == 0


def inactive_cycles(seat_id: int) -> list[int]:
    return [
        cycle
        for cycle in range(c.ISSUANCE_CYCLES_PER_SEAT)
        if is_inactive(seat_id, cycle)
    ]


def failing_seat(tick: int) -> int | None:
    """The one seat whose evaluated cycle fails in this window, if any.

    The phase shift makes the three seats' inactive cycles disjoint in every
    window. That is asserted here rather than assumed, because two failures in
    one window would make the winner set depend on evaluation order and would
    quietly change what the recorded totals mean.
    """
    failing = [
        seat_id
        for seat_id in range(SEATS)
        if (cycle := cycle_at(seat_id, tick)) is not None
        and is_inactive(seat_id, cycle)
    ]
    if len(failing) > 1:
        raise AssertionError(f"tick {tick}: {len(failing)} seats fail in one window")
    return failing[0] if failing else None


def performance_winner(seat_id: int) -> int:
    """The deterministic recipient of a failed seat's 342-unit leg.

    Version one supplied this as an allocation list. Here it is only an
    intention: the generator gives this seat the highest uptime in the window
    and the model derives the winner set independently.
    """
    return (seat_id + 1) % SEATS


def uptime_record(tick: int) -> dict[str, Any]:
    """The window's measurements, identical for every seat evaluating in it.

    A record is bound by digest on first reference, so every seat evaluating in
    this window must present exactly this value. Building it as a pure function
    of the tick is what guarantees that.

    Every population seat is listed whether or not it is inside its own
    issuance window, because uptime is a measurement of a running node and the
    issuance window is a separate accounting concept.
    """
    failing = failing_seat(tick)
    winner = None if failing is None else performance_winner(failing)
    entries = []
    for seat_id in range(SEATS):
        if seat_id == failing:
            uptime = FAILED_UPTIME
        elif failing is None or seat_id == winner:
            uptime = WINNER_UPTIME
        else:
            uptime = THRESHOLD_UPTIME
        entries.append({"seat_id": seat_id, "uptime_seconds": uptime})
    return {"cycle_window": tick, "entries": entries}


def _activate(seat_id: int, referrer: int | None) -> dict[str, Any]:
    return {
        "id": f"activate-{seat_id:05d}",
        "kind": "activate_seat",
        "seat_id": seat_id,
        "referrer_seat_id": referrer,
    }


def _base(seat_id: int, cycle_index: int, record: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "id": f"base-{seat_id:05d}-{cycle_index:03d}",
        "kind": "evaluate_base_permission",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
        "cycle_uptime_record": record,
    }


def _exercise(seat_id: int, cycle_index: int) -> dict[str, Any]:
    return {
        "id": f"exercise-{seat_id:05d}-{cycle_index:03d}",
        "kind": "exercise_permission",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
    }


def _accrue(seat_id: int, cycle_index: int) -> dict[str, Any]:
    return {
        "id": f"accrue-{seat_id:05d}-{cycle_index:03d}",
        "kind": "accrue_referral",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
    }


def _cycle_events(seat_id: int, cycle_index: int, tick: int) -> list[dict[str, Any]]:
    """One seat's cycle: evaluate, exercise, and accrue its referral benefit.

    The accrual is unconditional and direct-mint, so it needs no evaluation and
    no exercise. An unreferred seat's accrual is accepted and reaches the
    unreferred performance pool, which is what consumes the channel exactly.
    """
    return [
        _base(seat_id, cycle_index, uptime_record(tick)),
        _exercise(seat_id, cycle_index),
        _accrue(seat_id, cycle_index),
    ]


def boundary_probes() -> list[dict[str, Any]]:
    """Adversarial events appended once every window is complete.

    Each one must be rejected. The three uptime probes share one unevaluated
    key on `PROBE_SEAT` and are ordered so that each reaches a later condition
    than the last: a missing record, then a record that omits the evaluated
    seat, then a well-formed record contradicting one already bound to window
    zero. Every probe carries its own event identifier, because a repeated
    identifier is an input-shape error that would abort the run instead of
    producing a trace record.
    """
    foreign = {
        "cycle_window": 0,
        "entries": [{"seat_id": PROBE_SEAT, "uptime_seconds": WINNER_UPTIME}],
    }
    probes = [
        ("probe-cycle-beyond-window", _base(0, c.ISSUANCE_CYCLES_PER_SEAT, uptime_record(0))),
        ("probe-base-replay", _base(0, LAST_CYCLE, uptime_record(0))),
        ("probe-exercise-replay", _exercise(0, LAST_CYCLE)),
        ("probe-activation-replay", _activate(0, None)),
        ("probe-missing-uptime-record", _base(PROBE_SEAT, 0, None)),
        ("probe-invalid-uptime-record", _base(PROBE_SEAT, 0, uptime_record(0))),
        ("probe-inconsistent-uptime-record", _base(PROBE_SEAT, 0, foreign)),
        ("probe-accrual-replay", _accrue(0, 0)),
        ("probe-direct-referral", _direct_referral()),
    ]
    return [{**event, "id": event_id} for event_id, event in probes]


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


def events() -> list[dict[str, Any]]:
    """Build the complete staggered population run and its boundary probes."""
    generated = [_activate(seat_id, REFERRERS[seat_id]) for seat_id in range(SEATS)]
    generated.append(_activate(PROBE_SEAT, None))
    for tick in range(LAST_TICK + 1):
        for seat_id in range(SEATS):
            cycle_index = cycle_at(seat_id, tick)
            if cycle_index is not None:
                generated.extend(_cycle_events(seat_id, cycle_index, tick))
    generated.extend(boundary_probes())
    return generated
