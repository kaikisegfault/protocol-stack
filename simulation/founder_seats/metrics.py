"""Derived reporting views. No invariant depends on a metric."""

from __future__ import annotations

from typing import Any

from . import contract as c
from ..common.canonical import format_atomic
from .domain import State


def build_metrics(state: State) -> dict[str, Any]:
    next_index = c.block_index(state.seats_sold) if state.seats_sold < c.FOUNDER_SEAT_CAPACITY else None
    current_index = c.block_index(state.seats_sold - 1) if state.seats_sold else None
    counts = state.principal_seat_counts.values()
    return {
        "founder_seat_capacity": c.FOUNDER_SEAT_CAPACITY,
        "maximum_seats_per_person": c.MAXIMUM_SEATS_PER_PERSON,
        "seats_sold": state.seats_sold,
        "seats_remaining": state.seats_remaining,
        "proceeds_usd_cents": format_atomic(state.proceeds_usd_cents),
        "full_sale_proceeds_usd_cents": format_atomic(c.FULL_SALE_PROCEEDS_CENTS),
        "current_block_index": current_index,
        "current_block_price_usd_cents": (
            None if current_index is None
            else format_atomic(c.block_price_cents(current_index))
        ),
        "next_block_index": next_index,
        "next_block_price_usd_cents": (
            None if next_index is None
            else format_atomic(c.block_price_cents(next_index))
        ),
        "distinct_principal_count": len(state.principal_seat_counts),
        "largest_principal_holding": format_atomic(max(counts) if counts else 0),
    }
