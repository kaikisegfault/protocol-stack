"""Derived reporting views. No invariant depends on a metric."""

from __future__ import annotations

from typing import Any

from . import contract as c
from ..common.canonical import format_atomic
from .domain import State


def build_metrics(state: State) -> dict[str, Any]:
    commercial = state.founder_commercial_balances.values()
    fees = state.founder_fee_balances.values()
    credited_seats = set(state.founder_commercial_balances) | set(
        state.founder_fee_balances
    )
    return {
        "share_denominator": c.SHARE_DENOMINATOR,
        "founder_share_numerator": c.FOUNDER_SHARE_NUMERATOR,
        "creator_share_numerator": c.CREATOR_SHARE_NUMERATOR,
        "system_creator_share_numerator": c.SYSTEM_CREATOR_SHARE_NUMERATOR,
        "creator_split_parts": c.CREATOR_SPLIT_PARTS,
        "maximum_remainder_single_creator": c.MAXIMUM_REMAINDER_SINGLE_CREATOR,
        "maximum_remainder_two_creators": c.MAXIMUM_REMAINDER_TWO_CREATORS,
        "cycles_closed": state.current_cycle,
        "commercial_routed_total": format_atomic(state.commercial_routed_total),
        "fee_routed_total": format_atomic(state.fee_routed_total),
        "commercial_pool": format_atomic(state.commercial_pool),
        "fee_pool": format_atomic(state.fee_pool),
        "commercial_carry": format_atomic(state.commercial_carry),
        "fee_carry": format_atomic(state.fee_carry),
        "system_creator_balance": format_atomic(state.system_creator_balance),
        "creator_count": len(state.creator_balances),
        "credited_seat_count": len(credited_seats),
        "largest_creator_balance": format_atomic(
            max(state.creator_balances.values(), default=0)
        ),
        "largest_seat_commercial_balance": format_atomic(max(commercial, default=0)),
        "largest_seat_fee_balance": format_atomic(max(fees, default=0)),
    }
