"""Seeded random event sequences for `revenue-routing-v1`.

This generator produces varied, hostile, mostly-legal traffic; it does not
predict outcomes. It deliberately emits replays, out-of-order cycles, and empty
active-seat snapshots alongside legal events.
Nothing here asserts anything: the properties are the model's conservation
equations, and the caller checks them against the recorded final state.

Every sequence is a pure function of its seed, so a failing property names a
reproducible input.
"""

from __future__ import annotations

import random
from typing import Any

ROUTING_SEAT_POOL = 12
ROUTING_CREATORS = 3
CURRENT_CYCLE_PROBABILITY = 0.9
MAXIMUM_PAYMENT = 10**10
MAXIMUM_FEE = 10**8


def routing_events(seed: int, count: int) -> list[dict[str, Any]]:
    """Commercial payments, transaction fees, and accounting-cycle closes."""
    source = random.Random(seed)
    events: list[dict[str, Any]] = []
    cycle = 0
    for index in range(count):
        choice = source.randrange(3)
        if choice == 0:
            events.append(_random_payment(source, index, count))
        elif choice == 1:
            events.append(
                {
                    "id": f"e{index:05d}",
                    "kind": "route_transaction_fee",
                    "fee_id": f"fee-{source.randrange(count):05d}",
                    "amount_atomic": str(source.randrange(1, MAXIMUM_FEE)),
                }
            )
        else:
            closed = (
                cycle
                if source.random() < CURRENT_CYCLE_PROBABILITY
                else cycle + 1
            )
            events.append(_close(source, index, closed))
            if closed == cycle:
                cycle += 1
    return events


def _random_payment(
    source: random.Random,
    index: int,
    count: int,
) -> dict[str, Any]:
    product = (
        None
        if source.random() < 0.5
        else f"creator-{source.randrange(ROUTING_CREATORS)}"
    )
    return {
        "id": f"e{index:05d}",
        "kind": "route_commercial_payment",
        "payment_id": f"pay-{source.randrange(count):05d}",
        "amount_atomic": str(source.randrange(1, MAXIMUM_PAYMENT)),
        "project_creator_id": f"creator-{source.randrange(ROUTING_CREATORS)}",
        "product_creator_id": product,
    }


def _close(source: random.Random, index: int, cycle_index: int) -> dict[str, Any]:
    seats = sorted(
        {
            source.randrange(ROUTING_SEAT_POOL)
            for _ in range(source.randrange(ROUTING_SEAT_POOL))
        }
    )
    return {
        "id": f"e{index:05d}",
        "kind": "close_cycle",
        "cycle_index": cycle_index,
        "active_seats_result": {
            "cycle_index": cycle_index,
            "seat_ids": seats,
        },
    }
