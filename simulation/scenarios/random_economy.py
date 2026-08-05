"""Seeded random event sequences for `founder-economy-simulator-v1`.

This generator produces varied, hostile, mostly-legal traffic; it does not
predict outcomes. It deliberately emits replays, unbound research fixtures,
and out-of-range seats and cycles alongside legal events.
Nothing here asserts anything: the properties are the model's conservation
equations, and the caller checks them against the recorded final state.

Every sequence is a pure function of its seed, so a failing property names a
reproducible input.
"""

from __future__ import annotations

import random
from typing import Any

from ..founder_economy import contract as economy_contract

ECONOMY_SEATS = 4
ECONOMY_CYCLES = 8
ACTIVE_PROBABILITY = 0.75
ELIGIBILITY_SUPPLIED_PROBABILITY = 0.85


def economy_events(seed: int, count: int) -> list[dict[str, Any]]:
    """Activations, permission evaluations, exercises, and direct issuance."""
    source = random.Random(seed)
    channels = sorted(economy_contract.DIRECT_CHANNEL_IDS)
    events: list[dict[str, Any]] = []
    for index in range(count):
        seat_id = source.randrange(ECONOMY_SEATS)
        cycle_index = source.randrange(ECONOMY_CYCLES)
        choice = source.randrange(5)
        if choice == 0:
            events.append(_random_activation(source, index, seat_id))
        elif choice == 1:
            events.append(_random_base(source, index, seat_id, cycle_index))
        elif choice == 2:
            events.append(_random_referral(source, index, seat_id, cycle_index))
        elif choice == 3:
            events.append(_random_exercise(source, index, seat_id, cycle_index))
        else:
            events.append(_random_direct(source, index, channels))
    return events


def _random_activation(
    source: random.Random,
    index: int,
    seat_id: int,
) -> dict[str, Any]:
    referrer = None if source.random() < 0.5 else source.randrange(ECONOMY_SEATS)
    return {
        "id": f"e{index:05d}",
        "kind": "activate_seat",
        "seat_id": seat_id,
        "referrer_seat_id": referrer,
    }


def _activity(seat_id: int, cycle_index: int, active: bool) -> dict[str, Any]:
    return {"seat_id": seat_id, "cycle_index": cycle_index, "active": active}


def _random_base(
    source: random.Random,
    index: int,
    seat_id: int,
    cycle_index: int,
) -> dict[str, Any]:
    active = source.random() < ACTIVE_PROBABILITY
    allocation = None
    if not active:
        allocation = {
            "seat_id": seat_id,
            "cycle_index": cycle_index,
            "allocations": [
                {
                    "seat_id": source.randrange(ECONOMY_SEATS),
                    "amount_atomic": str(economy_contract.FOUNDER_OPERATOR_LEG),
                }
            ],
        }
    return {
        "id": f"e{index:05d}",
        "kind": "evaluate_base_permission",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
        "activity_result": _activity(seat_id, cycle_index, active),
        "performance_allocation": allocation,
    }


def _random_referral(
    source: random.Random,
    index: int,
    seat_id: int,
    cycle_index: int,
) -> dict[str, Any]:
    active = source.random() < ACTIVE_PROBABILITY
    inactive_result = None
    if not active:
        inactive_result = {
            "seat_id": seat_id,
            "cycle_index": cycle_index,
            "create": source.random() < 0.5,
        }
    return {
        "id": f"e{index:05d}",
        "kind": "evaluate_referral_permission",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
        "activity_result": _activity(seat_id, cycle_index, active),
        "inactive_referral_result": inactive_result,
    }


def _random_exercise(
    source: random.Random,
    index: int,
    seat_id: int,
    cycle_index: int,
) -> dict[str, Any]:
    return {
        "id": f"e{index:05d}",
        "kind": "exercise_permission",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
        "permission_kind": source.choice(["base", "referral"]),
    }


def _random_direct(
    source: random.Random,
    index: int,
    channels: list[str],
) -> dict[str, Any]:
    channel = source.choice(channels)
    decision_id = f"decision-{source.randrange(16):02d}"
    beneficiary_id = f"beneficiary-{source.randrange(4)}"
    amount = str(source.randrange(1, 10**12))
    eligibility = None
    if source.random() < ELIGIBILITY_SUPPLIED_PROBABILITY:
        eligibility = {
            "channel": channel,
            "decision_id": decision_id,
            "beneficiary_id": beneficiary_id,
            "amount_atomic": amount,
            "eligible": source.random() < 0.8,
        }
    return {
        "id": f"e{index:05d}",
        "kind": "direct_issue",
        "channel": channel,
        "decision_id": decision_id,
        "beneficiary_id": beneficiary_id,
        "amount_atomic": amount,
        "eligibility_result": eligibility,
    }
