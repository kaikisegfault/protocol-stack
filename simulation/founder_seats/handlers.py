"""The Founder Seat purchase transition.

The handler is pure: it inspects state and returns either a rejection or a
complete description of the writes. It never holds a mutable reference it can
partially write, so a rejected purchase cannot change state by construction
rather than by a compensating copy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import contract as c
from ..common.canonical import checked_add, format_atomic
from .domain import Seat, State

INCREASE = "increase"
DECREASE = "decrease"


@dataclass(frozen=True)
class Effect:
    """The complete write set of one accepted purchase."""

    seat_id: int
    seat: Seat
    purchase_id: str
    proceeds_usd_cents: int
    principal_count: int


@dataclass
class Outcome:
    code: str
    effect: Effect | None = None
    journal: list[dict[str, Any]] = field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return self.code == "OK"


def failure(code: str) -> Outcome:
    return Outcome(code=code)


def entry(bucket: str, direction: str, amount: int) -> dict[str, Any]:
    return {
        "bucket": bucket,
        "direction": direction,
        "amount_usd_cents": format_atomic(amount),
    }


def journal_delta(item: dict[str, Any]) -> int:
    amount = int(item["amount_usd_cents"])
    return amount if item["direction"] == INCREASE else -amount


def purchase_seat(state: State, event: dict[str, Any]) -> Outcome:
    purchase_id = event["purchase_id"]
    principal_id = event["principal_id"]

    if purchase_id in state.accepted_purchase_ids:
        return failure("REPLAY")
    if state.seats_sold >= c.FOUNDER_SEAT_CAPACITY:
        return failure("CAPACITY_EXHAUSTED")

    referrer = event["referrer_seat_id"]
    if referrer is not None and referrer not in state.seats:
        return failure("INVALID_REFERRER")

    held = state.principal_seat_counts.get(principal_id, 0)
    if held >= c.MAXIMUM_SEATS_PER_PERSON:
        return failure("PRINCIPAL_SEAT_LIMIT")

    seat_id = state.seats_sold
    price = c.seat_price_cents(seat_id)
    if price is None:
        return failure("ARITHMETIC_OVERFLOW")

    payment = event["payment_result"]
    if payment is None:
        return failure("MISSING_RESEARCH_INPUT")
    if not _bound(payment, purchase_id, principal_id, seat_id, price):
        return failure("INVALID_RESEARCH_INPUT")
    if not payment["settled"]:
        return failure("PAYMENT_NOT_SETTLED")

    proceeds = checked_add(state.proceeds_usd_cents, price)
    count = checked_add(held, 1)
    if proceeds is None or count is None or checked_add(state.seats_sold, 1) is None:
        return failure("ARITHMETIC_OVERFLOW")

    return Outcome(
        code="OK",
        effect=Effect(
            seat_id=seat_id,
            seat=Seat(
                principal_id=principal_id,
                price_usd_cents=price,
                referrer_seat_id=referrer,
            ),
            purchase_id=purchase_id,
            proceeds_usd_cents=proceeds,
            principal_count=count,
        ),
        journal=[
            entry("remaining_seats", DECREASE, 1),
            entry("seats_sold", INCREASE, 1),
            entry(f"principal:{principal_id}", INCREASE, 1),
            entry("proceeds", INCREASE, price),
        ],
    )


def apply_effect(state: State, effect: Effect) -> None:
    """Commit a validated write set. Every check already passed."""
    state.seats[effect.seat_id] = effect.seat
    state.seats_sold = effect.seat_id + 1
    state.proceeds_usd_cents = effect.proceeds_usd_cents
    state.principal_seat_counts[effect.seat.principal_id] = effect.principal_count
    state.accepted_purchase_ids.add(effect.purchase_id)


def _bound(
    payment: dict[str, Any],
    purchase_id: str,
    principal_id: str,
    seat_id: int,
    price: int,
) -> bool:
    """The fixture must match the purchase the state itself determines."""
    return (
        payment["purchase_id"] == purchase_id
        and payment["principal_id"] == principal_id
        and payment["seat_id"] == seat_id
        and int(payment["price_usd_cents"]) == price
    )


HANDLERS = {"purchase_seat": purchase_seat}
