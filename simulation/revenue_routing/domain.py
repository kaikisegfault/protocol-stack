"""Routing state, canonical values, and conservation invariants."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import contract as c
from ..common.canonical import (
    MAX_U64,
    InvariantError,
    digest,
    format_atomic,
    required_sum,
)


def seat_key(seat_id: int) -> str:
    """Zero-padded so the seat maps sort numerically and lexicographically."""
    return f"{seat_id:05d}"


@dataclass
class State:
    current_cycle: int = 0
    commercial_pool: int = 0
    fee_pool: int = 0
    commercial_carry: int = 0
    fee_carry: int = 0
    commercial_routed_total: int = 0
    fee_routed_total: int = 0
    system_creator_balance: int = 0
    creator_balances: dict[str, int] = field(default_factory=dict)
    founder_commercial_balances: dict[int, int] = field(default_factory=dict)
    founder_fee_balances: dict[int, int] = field(default_factory=dict)
    accepted_payment_ids: set[str] = field(default_factory=set)
    accepted_fee_ids: set[str] = field(default_factory=set)

    def summary(self) -> tuple[int, ...]:
        """A constant-time fingerprint used to cross-check no-write rejection.

        The primary guarantee is that handlers are pure and never receive a
        reference they partially write. This is a cheap defence in depth; the
        tests additionally compare full state digests across rejections.
        """
        return (
            self.current_cycle,
            self.commercial_pool,
            self.fee_pool,
            self.commercial_carry,
            self.fee_carry,
            self.commercial_routed_total,
            self.fee_routed_total,
            self.system_creator_balance,
            len(self.creator_balances),
            len(self.founder_commercial_balances),
            len(self.founder_fee_balances),
            len(self.accepted_payment_ids),
            len(self.accepted_fee_ids),
        )


def initial_state() -> State:
    """No opening balance, float, or reserve exists."""
    return State()


def state_value(state: State) -> dict[str, Any]:
    return {
        "current_cycle": state.current_cycle,
        "commercial_pool": format_atomic(state.commercial_pool),
        "fee_pool": format_atomic(state.fee_pool),
        "commercial_carry": format_atomic(state.commercial_carry),
        "fee_carry": format_atomic(state.fee_carry),
        "commercial_routed_total": format_atomic(state.commercial_routed_total),
        "fee_routed_total": format_atomic(state.fee_routed_total),
        "system_creator_balance": format_atomic(state.system_creator_balance),
        "creator_balances": {
            creator: format_atomic(amount)
            for creator, amount in sorted(state.creator_balances.items())
        },
        "founder_commercial_balances": _seat_map(state.founder_commercial_balances),
        "founder_fee_balances": _seat_map(state.founder_fee_balances),
        "accepted_payment_ids": sorted(state.accepted_payment_ids),
        "accepted_fee_ids": sorted(state.accepted_fee_ids),
    }


def _seat_map(balances: dict[int, int]) -> dict[str, str]:
    return {
        seat_key(seat_id): format_atomic(amount)
        for seat_id, amount in sorted(balances.items())
    }


def state_digest(state: State) -> str:
    return digest(c.STATE_LABEL, state_value(state))


def assert_invariants(state: State) -> None:
    _assert_scalars(state)
    _assert_balances(state)
    _assert_commercial_conservation(state)
    _assert_fee_conservation(state)


def _assert_scalars(state: State) -> None:
    scalars = (
        state.current_cycle,
        state.commercial_pool,
        state.fee_pool,
        state.commercial_carry,
        state.fee_carry,
        state.commercial_routed_total,
        state.fee_routed_total,
        state.system_creator_balance,
    )
    for value in scalars:
        if type(value) is not int or not 0 <= value <= MAX_U64:
            raise InvariantError("a routing scalar is outside u64")


def _assert_balances(state: State) -> None:
    for balances in (state.founder_commercial_balances, state.founder_fee_balances):
        for seat_id in balances:
            if not 0 <= seat_id < c.FOUNDER_SEAT_CAPACITY:
                raise InvariantError("a credited seat is outside the seat capacity")
    maps: tuple[dict[Any, int], ...] = (
        state.creator_balances,
        state.founder_commercial_balances,
        state.founder_fee_balances,
    )
    for balances in maps:
        for amount in balances.values():
            if type(amount) is not int or not 0 < amount <= MAX_U64:
                raise InvariantError("a stored balance is zero or outside u64")


def _assert_commercial_conservation(state: State) -> None:
    credited = required_sum(
        [
            state.system_creator_balance,
            required_sum(list(state.creator_balances.values()), "creator balances"),
            required_sum(
                list(state.founder_commercial_balances.values()),
                "founder commercial balances",
            ),
            state.commercial_pool,
            state.commercial_carry,
        ],
        "commercial conservation",
    )
    if credited != state.commercial_routed_total:
        raise InvariantError("commercial value is neither credited nor pooled")


def _assert_fee_conservation(state: State) -> None:
    credited = required_sum(
        [
            required_sum(
                list(state.founder_fee_balances.values()), "founder fee balances"
            ),
            state.fee_pool,
            state.fee_carry,
        ],
        "fee conservation",
    )
    if credited != state.fee_routed_total:
        raise InvariantError("fee value is neither credited nor pooled")
