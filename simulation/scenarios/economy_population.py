"""A complete 731-cycle run over a staggered Founder Seat population.

The Founder Constitution gives each seat 731 eligible cycles beginning at its
own first activation, so seats activated on different dates hold different
windows. The model has no global clock, so the stagger is expressed as event
order: at tick `t` the seat activated at tick `k * STAGGER` evaluates its own
cycle `t - k * STAGGER`. Every seat therefore completes exactly 731 cycles
while three windows overlap in different phases throughout the run.

Inactivity, the performance recipient, and the inactive-cycle referral decision
are unresolved founder choices. They are supplied here as explicit, deterministic
research inputs bound to the exact seat and cycle they authorize, never derived.
"""

from __future__ import annotations

from typing import Any

from ..founder_economy import contract as c

SEATS = 3
# Seat 0 refers both other seats, so one referrer accumulates the referral
# benefit of two seats across the whole multi-year window.
REFERRERS: dict[int, int | None] = {0: None, 1: 0, 2: 0}

# Ticks between consecutive activations. Prime, and far below the 731-cycle
# window, so every pair of windows overlaps for most of the run.
STAGGER = 61

# A seat is inactive when `(cycle + INACTIVE_PHASE * seat) % INACTIVE_PERIOD`
# is zero. The phase shift keeps the three seats' inactive cycles disjoint, so
# a performance recipient is always itself active in that cycle.
INACTIVE_PERIOD = 73
INACTIVE_PHASE = 7

LAST_CYCLE = c.ISSUANCE_CYCLES_PER_SEAT - 1
LAST_TICK = LAST_CYCLE + (SEATS - 1) * STAGGER


def is_inactive(seat_id: int, cycle_index: int) -> bool:
    return (cycle_index + INACTIVE_PHASE * seat_id) % INACTIVE_PERIOD == 0


def performance_winner(seat_id: int) -> int:
    """The deterministic recipient of an inactive seat's 342-unit leg."""
    return (seat_id + 1) % SEATS


def creates_referral(cycle_index: int) -> bool:
    """The supplied inactive-cycle referral decision, exercised both ways."""
    return cycle_index % 2 == 0


def inactive_cycles(seat_id: int) -> list[int]:
    return [
        cycle
        for cycle in range(c.ISSUANCE_CYCLES_PER_SEAT)
        if is_inactive(seat_id, cycle)
    ]


def referral_permissions_created() -> int:
    """The closed-form count of referral permissions this scenario creates."""
    total = 0
    for seat_id, referrer in REFERRERS.items():
        if referrer is None:
            continue
        withheld = sum(
            1 for cycle in inactive_cycles(seat_id) if not creates_referral(cycle)
        )
        total += c.ISSUANCE_CYCLES_PER_SEAT - withheld
    return total


def _activate(seat_id: int, referrer: int | None) -> dict[str, Any]:
    return {
        "id": f"activate-{seat_id:05d}",
        "kind": "activate_seat",
        "seat_id": seat_id,
        "referrer_seat_id": referrer,
    }


def _activity(seat_id: int, cycle_index: int, active: bool) -> dict[str, Any]:
    return {"seat_id": seat_id, "cycle_index": cycle_index, "active": active}


def _base(seat_id: int, cycle_index: int, active: bool) -> dict[str, Any]:
    allocation = None
    if not active:
        allocation = {
            "seat_id": seat_id,
            "cycle_index": cycle_index,
            "allocations": [
                {
                    "seat_id": performance_winner(seat_id),
                    "amount_atomic": str(c.FOUNDER_OPERATOR_LEG),
                }
            ],
        }
    return {
        "id": f"base-{seat_id:05d}-{cycle_index:03d}",
        "kind": "evaluate_base_permission",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
        "activity_result": _activity(seat_id, cycle_index, active),
        "performance_allocation": allocation,
    }


def _referral(seat_id: int, cycle_index: int, active: bool) -> dict[str, Any]:
    inactive_result = None
    if not active:
        inactive_result = {
            "seat_id": seat_id,
            "cycle_index": cycle_index,
            "create": creates_referral(cycle_index),
        }
    return {
        "id": f"referral-{seat_id:05d}-{cycle_index:03d}",
        "kind": "evaluate_referral_permission",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
        "activity_result": _activity(seat_id, cycle_index, active),
        "inactive_referral_result": inactive_result,
    }


def _exercise(seat_id: int, cycle_index: int, kind: str) -> dict[str, Any]:
    return {
        "id": f"exercise-{seat_id:05d}-{cycle_index:03d}-{kind}",
        "kind": "exercise_permission",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
        "permission_kind": kind,
    }


def _cycle_events(seat_id: int, cycle_index: int) -> list[dict[str, Any]]:
    active = not is_inactive(seat_id, cycle_index)
    events = [
        _base(seat_id, cycle_index, active),
        _exercise(seat_id, cycle_index, "base"),
    ]
    if REFERRERS[seat_id] is None:
        return events
    events.append(_referral(seat_id, cycle_index, active))
    if active or creates_referral(cycle_index):
        events.append(_exercise(seat_id, cycle_index, "referral"))
    return events


def boundary_probes() -> list[dict[str, Any]]:
    """Adversarial events appended once every window is complete.

    Each one must be rejected: the issuance period ends exactly at the 731st
    cycle, an evaluated cycle cannot be evaluated again, an exercised
    permission is gone, an activated seat cannot be activated again, and an
    unreferred seat has no referral permission to create. Every probe carries
    its own event identifier, because a repeated identifier is an input-shape
    error that would abort the run instead of producing a trace record.
    """
    probes = [
        ("probe-cycle-beyond-window", _base(0, c.ISSUANCE_CYCLES_PER_SEAT, True)),
        ("probe-base-replay", _base(0, LAST_CYCLE, True)),
        ("probe-exercise-replay", _exercise(0, LAST_CYCLE, "base")),
        ("probe-activation-replay", _activate(0, None)),
        ("probe-unreferred-referral", _referral(0, 0, True)),
    ]
    return [{**event, "id": event_id} for event_id, event in probes]


def events() -> list[dict[str, Any]]:
    """Build the complete staggered population run and its boundary probes."""
    generated = [_activate(seat_id, REFERRERS[seat_id]) for seat_id in range(SEATS)]
    for tick in range(LAST_TICK + 1):
        for seat_id in range(SEATS):
            cycle_index = tick - seat_id * STAGGER
            if 0 <= cycle_index < c.ISSUANCE_CYCLES_PER_SEAT:
                generated.extend(_cycle_events(seat_id, cycle_index))
    generated.extend(boundary_probes())
    return generated
