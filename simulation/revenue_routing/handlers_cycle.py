"""The accounting-cycle close transition.

Both pools are divided over the same supplied active-seat snapshot, but they are
divided independently: each keeps its own residue as the next cycle's carry, so
nothing is burned and an empty or undersized population delays a distribution
rather than destroying it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..common.canonical import checked_add
from .domain import State, seat_key
from .operations import (
    DECREASE,
    INCREASE,
    CloseEffect,
    JournalEntry,
    Outcome,
    entry,
    failure,
)


@dataclass(frozen=True)
class Distribution:
    """One side of a cycle close: what leaves the pool and where it lands."""

    pool_in: int
    per_seat: int
    carry: int
    credits: tuple[tuple[int, int], ...]


def close_cycle(state: State, event: dict[str, Any]) -> Outcome:
    if event["cycle_index"] != state.current_cycle:
        return failure("CYCLE_MISMATCH")

    snapshot = event["active_seats_result"]
    if snapshot is None:
        return failure("MISSING_RESEARCH_INPUT")
    if snapshot["cycle_index"] != state.current_cycle:
        return failure("INVALID_RESEARCH_INPUT")

    seats = snapshot["seat_ids"]
    if checked_add(state.current_cycle, 1) is None:
        return failure("ARITHMETIC_OVERFLOW")

    commercial = _distribute(
        state.commercial_pool,
        state.commercial_carry,
        seats,
        state.founder_commercial_balances,
    )
    fees = _distribute(
        state.fee_pool, state.fee_carry, seats, state.founder_fee_balances
    )
    if commercial is None or fees is None:
        return failure("ARITHMETIC_OVERFLOW")

    return Outcome(
        code="OK",
        effect=CloseEffect(
            commercial_carry=commercial.carry,
            fee_carry=fees.carry,
            commercial_credits=commercial.credits,
            fee_credits=fees.credits,
        ),
        journal=_side_journal(commercial, "commercial") + _side_journal(fees, "fee"),
    )


def _distribute(
    pool: int,
    carry: int,
    seats: list[int],
    balances: dict[int, int],
) -> Distribution | None:
    pool_in = checked_add(pool, carry)
    if pool_in is None:
        return None
    if not seats:
        return Distribution(pool_in=pool_in, per_seat=0, carry=pool_in, credits=())

    per_seat, residue = divmod(pool_in, len(seats))
    credits: list[tuple[int, int]] = []
    if per_seat != 0:
        for seat_id in seats:
            updated = checked_add(balances.get(seat_id, 0), per_seat)
            if updated is None:
                return None
            credits.append((seat_id, updated))
    return Distribution(
        pool_in=pool_in, per_seat=per_seat, carry=residue, credits=tuple(credits)
    )


def _side_journal(distribution: Distribution, side: str) -> list[JournalEntry]:
    """An untouched side emits nothing, so a quiet cycle has an empty journal."""
    if distribution.pool_in == 0:
        return []
    journal = [entry(f"{side}_distribution", DECREASE, distribution.pool_in)]
    journal.extend(
        entry(f"seat:{seat_key(seat_id)}:{side}", INCREASE, distribution.per_seat)
        for seat_id, _ in distribution.credits
    )
    if distribution.carry != 0:
        journal.append(entry(f"{side}_carry", INCREASE, distribution.carry))
    return journal
