"""Shared Founder Seat sale test inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from simulation.founder_seats import contract as c

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "simulation" / "founder_seats" / "fixtures"
VECTORS_PATH = ROOT / "test-vectors" / "founder-seat-schedule-v1.txt"


def research_events() -> list[dict[str, Any]]:
    return json.loads((FIXTURES / "research-events-v1.json").read_text(encoding="utf-8"))


def vectors() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in VECTORS_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            key, _, value = stripped.partition("=")
            values[key] = value
    return values


def purchase(
    seat_id: int,
    principal_id: str = "principal-alpha",
    *,
    referrer: int | None = None,
    settled: bool = True,
    purchase_id: str | None = None,
    event_id: str | None = None,
    payment: dict[str, Any] | None = ...,  # type: ignore[assignment]
    binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a purchase whose payment fixture is bound to the expected seat."""
    identifier = purchase_id or f"purchase-{seat_id:05d}"
    price = c.seat_price_cents(seat_id)
    if payment is ...:
        payment = {
            "purchase_id": identifier,
            "principal_id": principal_id,
            "seat_id": seat_id,
            "price_usd_cents": str(price if price is not None else 0),
            "settled": settled,
        }
        payment.update(binding or {})
    return {
        "id": event_id or identifier,
        "kind": "purchase_seat",
        "purchase_id": identifier,
        "principal_id": principal_id,
        "referrer_seat_id": referrer,
        "payment_result": payment,
    }


def sale(count: int, *, principal_block: int = c.MAXIMUM_SEATS_PER_PERSON) -> list[dict]:
    """Build `count` sequential purchases spread across principals."""
    return [
        purchase(seat_id, f"principal-{seat_id // principal_block:04d}")
        for seat_id in range(count)
    ]
