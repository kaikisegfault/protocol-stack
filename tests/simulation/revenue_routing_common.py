"""Shared revenue routing test inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "simulation" / "revenue_routing" / "fixtures"
VECTORS_PATH = ROOT / "test-vectors" / "revenue-routing-v1.txt"


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


def payment(
    amount: int,
    *,
    payment_id: str = "payment-0001",
    event_id: str | None = None,
    project: str = "creator-alpha",
    product: str | None = None,
) -> dict[str, Any]:
    return {
        "id": event_id or payment_id,
        "kind": "route_commercial_payment",
        "payment_id": payment_id,
        "amount_atomic": str(amount),
        "project_creator_id": project,
        "product_creator_id": product,
    }


def fee(
    amount: int,
    *,
    fee_id: str = "fee-0001",
    event_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": event_id or fee_id,
        "kind": "route_transaction_fee",
        "fee_id": fee_id,
        "amount_atomic": str(amount),
    }


def close(
    cycle: int,
    seats: list[int],
    *,
    event_id: str | None = None,
    snapshot_cycle: int | None = None,
    snapshot: dict[str, Any] | None = ...,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Build a close whose snapshot is bound to the cycle it closes."""
    if snapshot is ...:
        snapshot = {
            "cycle_index": cycle if snapshot_cycle is None else snapshot_cycle,
            "seat_ids": seats,
        }
    return {
        "id": event_id or f"close-{cycle:04d}",
        "kind": "close_cycle",
        "cycle_index": cycle,
        "active_seats_result": snapshot,
    }
