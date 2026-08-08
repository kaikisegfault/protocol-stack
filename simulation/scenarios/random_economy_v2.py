"""Seeded random event sequences for `founder-economy-simulator-v2`.

This generator produces varied, hostile, mostly-legal traffic; it does not
predict outcomes. It deliberately emits replays, malformed uptime records,
contradictory records for one window, referral issuance through the wrong
channel, and out-of-range seats and cycles alongside legal events. Nothing here
asserts anything: the properties are the model's conservation equations, and the
caller checks them against the recorded final state.

Every sequence is a pure function of its seed, so a failing property names a
reproducible input.

One boundary needs care. An out-of-range count is an input-shape error that
aborts the whole run, while an over-target `uptime_seconds` is a modelled
rejection that must produce a trace record. Hostile uptimes are therefore drawn
above the cycle target but well inside the parser's bounds, so this generator
exercises `INVALID_UPTIME_RECORD` rather than killing the run.
"""

from __future__ import annotations

import random
from typing import Any

from ..founder_economy_v2 import contract as economy_contract

ECONOMY_SEATS = 4
ECONOMY_CYCLES = 8
ECONOMY_WINDOWS = 6
RECORD_SUPPLIED_PROBABILITY = 0.85
ELIGIBILITY_SUPPLIED_PROBABILITY = 0.85
WELL_FORMED_RECORD_PROBABILITY = 0.75
MET_CYCLE_PROBABILITY = 0.75

# Above the 86,400-second cycle target, so the record is rejected by the model,
# and far below the parser's count bound, so the run continues.
OVER_TARGET_UPTIME = economy_contract.CYCLE_TARGET_SECONDS + 1


def economy_events(seed: int, count: int) -> list[dict[str, Any]]:
    """Activations, base evaluations, exercises, accruals, and direct issuance."""
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
            events.append(_random_accrual(index, seat_id, cycle_index))
        elif choice == 3:
            events.append(_random_exercise(index, seat_id, cycle_index))
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


def _random_record(
    source: random.Random,
    seat_id: int,
) -> dict[str, Any] | None:
    """A cycle uptime record carrying measurements only.

    Windows are drawn from a small set so that different records collide on one
    window often, which is what exercises the digest binding and
    `INCONSISTENT_UPTIME_RECORD`. Malformed variants omit the evaluated seat,
    repeat a seat, or report more uptime than a cycle contains.
    """
    if source.random() >= RECORD_SUPPLIED_PROBABILITY:
        return None

    window = source.randrange(ECONOMY_WINDOWS)
    listed = list(range(ECONOMY_SEATS))
    if source.random() >= WELL_FORMED_RECORD_PROBABILITY:
        flaw = source.randrange(3)
        if flaw == 0:
            listed = [other for other in listed if other != seat_id]
        elif flaw == 1:
            listed = listed + [listed[0]]
        else:
            return {
                "cycle_window": window,
                "entries": [
                    {"seat_id": other, "uptime_seconds": OVER_TARGET_UPTIME}
                    for other in listed
                ],
            }

    entries = [
        {
            "seat_id": other,
            "uptime_seconds": (
                economy_contract.CYCLE_TARGET_SECONDS
                if source.random() < MET_CYCLE_PROBABILITY
                else source.randrange(economy_contract.ACTIVITY_THRESHOLD_SECONDS)
            ),
        }
        for other in listed
    ]
    return {"cycle_window": window, "entries": entries}


def _random_base(
    source: random.Random,
    index: int,
    seat_id: int,
    cycle_index: int,
) -> dict[str, Any]:
    return {
        "id": f"e{index:05d}",
        "kind": "evaluate_base_permission",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
        "cycle_uptime_record": _random_record(source, seat_id),
    }


def _random_accrual(index: int, seat_id: int, cycle_index: int) -> dict[str, Any]:
    """The accrual is unconditional, so it carries no research input at all."""
    return {
        "id": f"e{index:05d}",
        "kind": "accrue_referral",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
    }


def _random_exercise(index: int, seat_id: int, cycle_index: int) -> dict[str, Any]:
    """Version two has no permission kind, because the referral is not one."""
    return {
        "id": f"e{index:05d}",
        "kind": "exercise_permission",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
    }


def _random_direct(
    source: random.Random,
    index: int,
    channels: list[str],
) -> dict[str, Any]:
    """`channels` includes `founder_referral`, which the model must refuse.

    Leaving it in the draw is deliberate hostile traffic: the containment that
    keeps referral units inside the per-seat-cycle accounting is exercised by
    the property runs rather than only by a named probe.
    """
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
