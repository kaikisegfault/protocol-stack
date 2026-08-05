"""Seeded random event sequences for `founder-seat-schedule-v1`.

This generator produces varied, hostile, mostly-legal traffic; it does not
predict outcomes. It deliberately emits replays, unsettled payments, and
fixtures bound to the wrong seat alongside legal events.
Nothing here asserts anything: the properties are the model's conservation
equations, and the caller checks them against the recorded final state.

Every sequence is a pure function of its seed, so a failing property names a
reproducible input.
"""

from __future__ import annotations

import random
from typing import Any

from ..founder_seats import contract as seat_contract

SEAT_PRINCIPALS = 6
SETTLED_PROBABILITY = 0.85
REPLAY_PROBABILITY = 0.1
BOUND_SEAT_PROBABILITY = 0.9


def seat_events(seed: int, count: int) -> list[dict[str, Any]]:
    """Purchases whose payment fixture is bound to a predicted next seat.

    The prediction only keeps the sequence interesting: it applies the same
    admission rules the model does, so most purchases reach a state check
    rather than stopping at an unbound fixture. A wrong prediction is rejected
    as an unbound fixture, which is itself a case worth generating, and no
    property depends on the prediction being right.
    """
    source = random.Random(seed)
    events: list[dict[str, Any]] = []
    expected_seat = 0
    for index in range(count):
        principal_id = f"principal-{source.randrange(SEAT_PRINCIPALS):04d}"
        settled = source.random() < SETTLED_PROBABILITY
        replay = bool(events) and source.random() < REPLAY_PROBABILITY
        identifier = (
            source.choice(events)["purchase_id"] if replay else f"p{index:05d}"
        )
        bound = source.random() < BOUND_SEAT_PROBABILITY
        seat_id = expected_seat if bound else expected_seat + 1
        events.append(
            _purchase(index, identifier, principal_id, seat_id, settled)
        )
        if settled and not replay and bound:
            expected_seat += 1
    return events


def _purchase(
    index: int,
    identifier: str,
    principal_id: str,
    seat_id: int,
    settled: bool,
) -> dict[str, Any]:
    price = seat_contract.seat_price_cents(seat_id)
    return {
        "id": f"e{index:05d}",
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
