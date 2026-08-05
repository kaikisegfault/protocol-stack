"""The maximally concentrated complete Founder Seat sale.

The Founder Constitution fixes exactly 100,000 seats and no more than 1,000
seats per human. The two bounds meet at exactly 100 principals, which is the
smallest population that can absorb the entire capacity. This scenario runs
that sale end to end, and after each principal reaches its bound it attempts
one further purchase, so a saturated principal is proved not to consume a seat
over the full sale rather than only in a short fixture.

The per-principal bound is not yet a per-human bound: nothing here shows that
two principal identifiers are two people. That gap belongs to the biometric
enrollment milestone and is recorded, not modelled.
"""

from __future__ import annotations

from typing import Any

from ..founder_seats import contract as c

PRINCIPAL_BLOCK = c.MAXIMUM_SEATS_PER_PERSON
MINIMUM_PRINCIPALS = c.FOUNDER_SEAT_CAPACITY // PRINCIPAL_BLOCK


def principal_of(seat_id: int) -> str:
    return f"principal-{seat_id // PRINCIPAL_BLOCK:04d}"


def _purchase(
    seat_id: int,
    principal_id: str,
    *,
    purchase_id: str | None = None,
    event_id: str | None = None,
    settled: bool = True,
) -> dict[str, Any]:
    """Build a purchase whose payment fixture is bound to the expected seat.

    The price is the one the constitutional schedule assigns to `seat_id`; a
    purchase that will be rejected still carries the price of the seat it aimed
    at, so the rejection is decided by state rather than by a malformed fixture.
    """
    identifier = purchase_id or f"purchase-{seat_id:05d}"
    price = c.seat_price_cents(seat_id)
    return {
        "id": event_id or identifier,
        "kind": "purchase_seat",
        "purchase_id": identifier,
        "principal_id": principal_id,
        "referrer_seat_id": None,
        "payment_result": {
            "purchase_id": identifier,
            "principal_id": principal_id,
            "seat_id": seat_id,
            "price_usd_cents": str(price if price is not None else 0),
            "settled": settled,
        },
    }


def over_limit_attempts() -> int:
    """One attempt per principal that reaches its bound before the sale ends."""
    return MINIMUM_PRINCIPALS - 1


def events() -> list[dict[str, Any]]:
    """Build the complete concentrated sale and its two exhaustion probes."""
    generated: list[dict[str, Any]] = []
    for seat_id in range(c.FOUNDER_SEAT_CAPACITY):
        if seat_id != 0 and seat_id % PRINCIPAL_BLOCK == 0:
            saturated = f"principal-{seat_id // PRINCIPAL_BLOCK - 1:04d}"
            generated.append(
                _purchase(seat_id, saturated, purchase_id=f"over-{seat_id:05d}")
            )
        generated.append(_purchase(seat_id, principal_of(seat_id)))

    # The capacity is gone, so a fresh principal with a settled payment is
    # still refused. Capacity is checked before the per-principal bound.
    generated.append(
        _purchase(
            c.FOUNDER_SEAT_CAPACITY,
            f"principal-{MINIMUM_PRINCIPALS:04d}",
            purchase_id="beyond-capacity",
        )
    )
    # A replayed purchase identifier is refused ahead of the capacity check,
    # so an exhausted sale is still not a place where replay stops mattering.
    generated.append(
        _purchase(
            0,
            "principal-0000",
            purchase_id="purchase-00000",
            event_id="probe-purchase-replay",
        )
    )
    return generated
