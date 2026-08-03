"""Founder Seat sale state, canonical values, and invariants."""

from __future__ import annotations

import copy
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
    """Zero-padded so the seat map sorts numerically and lexicographically."""
    return f"{seat_id:05d}"


@dataclass(frozen=True)
class Seat:
    principal_id: str
    price_usd_cents: int
    referrer_seat_id: int | None


@dataclass
class State:
    seats_sold: int = 0
    proceeds_usd_cents: int = 0
    seats: dict[int, Seat] = field(default_factory=dict)
    principal_seat_counts: dict[str, int] = field(default_factory=dict)
    accepted_purchase_ids: set[str] = field(default_factory=set)

    def clone(self) -> State:
        return copy.deepcopy(self)

    @property
    def seats_remaining(self) -> int:
        return c.FOUNDER_SEAT_CAPACITY - self.seats_sold

    def summary(self) -> tuple[int, int, int, int, int]:
        """A constant-time fingerprint used to cross-check no-write rejection.

        The primary guarantee is that handlers are pure and never receive a
        reference they partially write. This is a cheap defence in depth; the
        tests additionally compare full state digests across rejections on
        bounded scenarios.
        """
        return (
            self.seats_sold,
            self.proceeds_usd_cents,
            len(self.seats),
            len(self.principal_seat_counts),
            len(self.accepted_purchase_ids),
        )


def initial_state() -> State:
    """No pre-sale, founder grant, or reserved allocation exists."""
    return State()


def state_value(state: State) -> dict[str, Any]:
    return {
        "seats_sold": state.seats_sold,
        "proceeds_usd_cents": format_atomic(state.proceeds_usd_cents),
        "seats": {
            seat_key(seat_id): {
                "principal_id": seat.principal_id,
                "price_usd_cents": format_atomic(seat.price_usd_cents),
                "referrer_seat_id": (
                    None if seat.referrer_seat_id is None
                    else seat_key(seat.referrer_seat_id)
                ),
            }
            for seat_id, seat in sorted(state.seats.items())
        },
        "principal_seat_counts": {
            principal: format_atomic(count)
            for principal, count in sorted(state.principal_seat_counts.items())
        },
        "accepted_purchase_ids": sorted(state.accepted_purchase_ids),
    }


def state_digest(state: State) -> str:
    return digest(c.STATE_LABEL, state_value(state))


def assert_invariants(state: State) -> None:
    _assert_capacity(state)
    _assert_ownership(state)
    _assert_pricing(state)
    _assert_referrers(state)


def _assert_capacity(state: State) -> None:
    if type(state.seats_sold) is not int or not 0 <= state.seats_sold <= MAX_U64:
        raise InvariantError("seats_sold is outside u64")
    if state.seats_sold > c.FOUNDER_SEAT_CAPACITY:
        raise InvariantError("seats_sold exceeds the founder seat capacity")
    if len(state.seats) != state.seats_sold:
        raise InvariantError("the seat record count does not equal seats_sold")
    if any(not 0 <= seat_id < state.seats_sold for seat_id in state.seats):
        raise InvariantError("a seat identifier is outside the sold range")


def _assert_ownership(state: State) -> None:
    counts = list(state.principal_seat_counts.values())
    if any(type(count) is not int or count <= 0 for count in counts):
        raise InvariantError("a principal seat count is not positive")
    if any(count > c.MAXIMUM_SEATS_PER_PERSON for count in counts):
        raise InvariantError("a principal exceeds the maximum seats per person")
    if required_sum(counts, "principal seat counts") != state.seats_sold:
        raise InvariantError("principal seat counts do not sum to seats_sold")

    observed: dict[str, int] = {}
    for seat in state.seats.values():
        observed[seat.principal_id] = observed.get(seat.principal_id, 0) + 1
    if observed != state.principal_seat_counts:
        raise InvariantError("principal seat counts disagree with the seat records")


def _assert_pricing(state: State) -> None:
    if (
        type(state.proceeds_usd_cents) is not int
        or not 0 <= state.proceeds_usd_cents <= MAX_U64
    ):
        raise InvariantError("proceeds_usd_cents is outside u64")
    if state.proceeds_usd_cents > c.FULL_SALE_PROCEEDS_CENTS:
        raise InvariantError("proceeds exceed the full-sale total")

    for seat_id, seat in state.seats.items():
        expected = c.seat_price_cents(seat_id)
        if expected is None or seat.price_usd_cents != expected:
            raise InvariantError("a seat price does not match its block price")
    total = required_sum(
        [seat.price_usd_cents for seat in state.seats.values()],
        "seat prices",
    )
    if total != state.proceeds_usd_cents:
        raise InvariantError("seat prices do not sum to recorded proceeds")


def _assert_referrers(state: State) -> None:
    for seat_id, seat in state.seats.items():
        referrer = seat.referrer_seat_id
        if referrer is None:
            continue
        if referrer == seat_id:
            raise InvariantError("a seat refers to itself")
        if referrer not in state.seats:
            raise InvariantError("a seat refers to an unsold seat")
        if referrer >= seat_id:
            raise InvariantError("a seat refers to a later seat")
