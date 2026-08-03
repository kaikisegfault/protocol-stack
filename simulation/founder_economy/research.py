"""Binding checks for the four unresolved research placeholders.

Each object must be bound to the exact action it authorizes. A stand-in that
could authorize a different seat, cycle, channel, or amount would let a fixture
silently become policy, so binding is total rather than partial.
"""

from __future__ import annotations

from typing import Any

from . import contract as c
from .canonical import MAX_U64, checked_add
from .domain import Leg, State, founder_custody_key

FOUNDER_CHANNEL = "founder_operator"


def bound_to_cycle(result: dict[str, Any], seat_id: int, cycle_index: int) -> bool:
    return result["seat_id"] == seat_id and result["cycle_index"] == cycle_index


def bound_to_direct(result: dict[str, Any], event: dict[str, Any]) -> bool:
    return all(
        result[name] == event[name]
        for name in ("channel", "decision_id", "beneficiary_id", "amount_atomic")
    )


def resolve_performance_allocation(
    state: State,
    source_seat_id: int,
    allocation: dict[str, Any],
) -> tuple[str | None, tuple[Leg, ...]]:
    """Resolve the inactive-cycle Founder leg into concrete recipient legs.

    The recipients must be distinct activated seats other than the inactive
    source seat, and their checked sum must equal the Founder leg exactly.
    Proving that each recipient was active in the same cycle requires the
    unresolved performance policy and is an M3 obligation.
    """
    entries = allocation["allocations"]
    if not entries:
        return "INVALID_PERFORMANCE_ALLOCATION", ()

    seen: set[int] = set()
    total = 0
    legs: list[Leg] = []
    for item in entries:
        seat_id = item["seat_id"]
        amount = int(item["amount_atomic"])
        if seat_id in seen or seat_id == source_seat_id:
            return "INVALID_PERFORMANCE_ALLOCATION", ()
        if not 0 <= seat_id < c.FOUNDER_SEAT_CAPACITY or seat_id not in state.seats:
            return "INVALID_PERFORMANCE_ALLOCATION", ()
        if not 0 < amount <= MAX_U64:
            return "INVALID_PERFORMANCE_ALLOCATION", ()
        checked = checked_add(total, amount)
        if checked is None:
            return "INVALID_PERFORMANCE_ALLOCATION", ()
        seen.add(seat_id)
        total = checked
        legs.append(
            Leg(
                channel=FOUNDER_CHANNEL,
                custody_key=founder_custody_key(seat_id),
                amount_atomic=amount,
            )
        )

    if total != c.FOUNDER_OPERATOR_LEG:
        return "INVALID_PERFORMANCE_ALLOCATION", ()
    return None, tuple(legs)


def fixed_base_legs() -> tuple[Leg, ...]:
    """Return the four base legs whose beneficiaries never change."""
    return tuple(
        Leg(
            channel=channel,
            custody_key=f"{beneficiary_kind}:{c.SINGLETON_BENEFICIARY_ID}",
            amount_atomic=amount,
        )
        for channel, beneficiary_kind, amount in c.BASE_LEGS
        if beneficiary_kind in c.SINGLETON_BENEFICIARY_KINDS
    )
