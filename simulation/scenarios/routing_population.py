"""A routing run whose active Founder population changes every cycle.

The Founder Constitution divides both the commercial and the fee pool among the
seats that are online and meet the active requirements for the applicable
accounting cycle, and states that offline seats do not dilute active ones. The
hard case is a cycle with no active seat at all: nothing may be burned, so the
whole pool must survive as carry and be distributed by a later cycle.

The active-seat snapshot is an unresolved founder choice — no activity metric,
grace allowance, or liveness proof exists yet — so it is supplied here as an
explicit research input bound to the cycle it describes.
"""

from __future__ import annotations

from typing import Any

# The active population size cycles through every residue modulo this period,
# so the run contains empty, singleton, and multi-seat cycles in a fixed order.
ACTIVE_PERIOD = 5
ACTIVE_STEP = 7
SEAT_STEP = 13
SEAT_MODULUS = 97

# Ends one cycle after an empty cycle, so the final state shows a pool that an
# empty cycle carried and a later cycle distributed.
CYCLES = 122

# Chosen coprime to the 200-residue routing period, so successive payments walk
# the remainder classes instead of repeating one.
PAYMENT_BASE = 1_000_000_007
PAYMENT_STEP = 999_983
FEE_BASE = 500_003
FEE_STEP = 97

PROJECT_CREATOR = "creator-alpha"
PRODUCT_CREATOR = "creator-beta"
PRODUCT_CYCLE_PERIOD = 3


def active_seats(cycle_index: int) -> list[int]:
    """The supplied active-seat snapshot for one cycle, strictly ascending."""
    size = (cycle_index * ACTIVE_STEP) % ACTIVE_PERIOD
    return sorted(
        {
            (cycle_index * SEAT_STEP + offset) % SEAT_MODULUS
            for offset in range(size)
        }
    )


def payment_amount(cycle_index: int) -> int:
    return PAYMENT_BASE + cycle_index * PAYMENT_STEP


def fee_amount(cycle_index: int) -> int:
    return FEE_BASE + cycle_index * FEE_STEP


def has_product_creator(cycle_index: int) -> bool:
    return cycle_index % PRODUCT_CYCLE_PERIOD == 0


def empty_cycles() -> list[int]:
    return [cycle for cycle in range(CYCLES) if not active_seats(cycle)]


def _payment(cycle_index: int) -> dict[str, Any]:
    identifier = f"payment-{cycle_index:04d}"
    return {
        "id": identifier,
        "kind": "route_commercial_payment",
        "payment_id": identifier,
        "amount_atomic": str(payment_amount(cycle_index)),
        "project_creator_id": PROJECT_CREATOR,
        "product_creator_id": (
            PRODUCT_CREATOR if has_product_creator(cycle_index) else None
        ),
    }


def _fee(cycle_index: int) -> dict[str, Any]:
    identifier = f"fee-{cycle_index:04d}"
    return {
        "id": identifier,
        "kind": "route_transaction_fee",
        "fee_id": identifier,
        "amount_atomic": str(fee_amount(cycle_index)),
    }


def _close(
    cycle_index: int,
    *,
    event_id: str | None = None,
    snapshot_cycle: int | None = None,
) -> dict[str, Any]:
    return {
        "id": event_id or f"close-{cycle_index:04d}",
        "kind": "close_cycle",
        "cycle_index": cycle_index,
        "active_seats_result": {
            "cycle_index": cycle_index if snapshot_cycle is None else snapshot_cycle,
            "seat_ids": active_seats(cycle_index),
        },
    }


def boundary_probes() -> list[dict[str, Any]]:
    """Adversarial events appended once the population run is complete.

    Each one must be rejected: a routed payment identifier cannot be reused, a
    cycle that is not the current one cannot be closed, and a snapshot
    describing another cycle cannot decide this one's distribution.
    """
    replayed = _payment(0)
    return [
        {**replayed, "id": "probe-payment-replay"},
        _close(CYCLES + 1, event_id="probe-close-wrong-cycle"),
        _close(
            CYCLES,
            event_id="probe-close-stale-snapshot",
            snapshot_cycle=CYCLES - 1,
        ),
    ]


def events() -> list[dict[str, Any]]:
    """Build the changing-population run and its boundary probes."""
    generated: list[dict[str, Any]] = []
    for cycle_index in range(CYCLES):
        generated.append(_payment(cycle_index))
        generated.append(_fee(cycle_index))
        generated.append(_close(cycle_index))
    generated.extend(boundary_probes())
    return generated
