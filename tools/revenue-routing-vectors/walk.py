"""An independent replay of revenue-routing-v1, sharing no model code.

The vector file was produced from the model, so restating the model's own
arithmetic would prove nothing. This module re-implements the specification
directly: it parses the events with the standard JSON decoder, computes each
share with the naive `numerator * amount / 100` form that Python's arbitrary
precision integers make safe, and accumulates plain dictionaries.

The contract module instead computes shares from the amount's quotient and
remainder so the arithmetic stays inside `u64`. Requiring the two forms to agree
on an exhaustive residue scan is what makes the overflow-free decomposition an
audited claim rather than an assumption.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DENOMINATOR = 100
FOUNDER_NUMERATOR = 45
CREATOR_NUMERATOR = 45
SYSTEM_NUMERATOR = 10
CREATOR_PARTS = 2


def direct_share(amount: int, numerator: int) -> int:
    """The naive form the specification is written in."""
    return (numerator * amount) // DENOMINATOR


def direct_split(amount: int, *, product_creator: bool) -> tuple[int, int, int, int]:
    """Return (founder credit including remainder, project, product, system)."""
    founder = direct_share(amount, FOUNDER_NUMERATOR)
    creator = direct_share(amount, CREATOR_NUMERATOR)
    system = direct_share(amount, SYSTEM_NUMERATOR)
    if product_creator:
        project = product = creator // CREATOR_PARTS
    else:
        project, product = creator, 0
    remainder = amount - (founder + project + product + system)
    return founder + remainder, project, product, system


def direct_remainder(amount: int, *, product_creator: bool) -> int:
    founder_credit = direct_split(amount, product_creator=product_creator)[0]
    return founder_credit - direct_share(amount, FOUNDER_NUMERATOR)


@dataclass
class Close:
    """What one cycle close distributed, recorded for the vector file."""

    active_seat_count: int
    commercial_pool_in: int
    commercial_per_seat: int
    commercial_carry: int
    fee_pool_in: int
    fee_per_seat: int
    fee_carry: int


@dataclass
class Walk:
    current_cycle: int = 0
    commercial_pool: int = 0
    fee_pool: int = 0
    commercial_carry: int = 0
    fee_carry: int = 0
    commercial_routed_total: int = 0
    fee_routed_total: int = 0
    system_creator_balance: int = 0
    creator_balances: dict[str, int] = field(default_factory=dict)
    commercial_seats: dict[int, int] = field(default_factory=dict)
    fee_seats: dict[int, int] = field(default_factory=dict)
    payments: set[str] = field(default_factory=set)
    fees: set[str] = field(default_factory=set)
    closes: list[Close] = field(default_factory=list)
    accepted: int = 0
    rejected: int = 0


def load_events(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def replay(events: list[dict[str, Any]]) -> Walk:
    """Apply the specification's transitions to plain dictionaries."""
    walk = Walk()
    for event in events:
        handler = {
            "route_commercial_payment": _payment,
            "route_transaction_fee": _fee,
            "close_cycle": _close,
        }[event["kind"]]
        if handler(walk, event):
            walk.accepted += 1
        else:
            walk.rejected += 1
    return walk


def _payment(walk: Walk, event: dict[str, Any]) -> bool:
    payment_id = event["payment_id"]
    amount = int(event["amount_atomic"])
    project_id = event["project_creator_id"]
    product_id = event["product_creator_id"]
    if payment_id in walk.payments or amount == 0 or product_id == project_id:
        return False

    founder, project, product, system = direct_split(
        amount, product_creator=product_id is not None
    )
    walk.commercial_pool += founder
    walk.system_creator_balance += system
    walk.commercial_routed_total += amount
    _credit(walk.creator_balances, project_id, project)
    if product_id is not None:
        _credit(walk.creator_balances, product_id, product)
    walk.payments.add(payment_id)
    return True


def _fee(walk: Walk, event: dict[str, Any]) -> bool:
    fee_id = event["fee_id"]
    amount = int(event["amount_atomic"])
    if fee_id in walk.fees or amount == 0:
        return False
    walk.fee_pool += amount
    walk.fee_routed_total += amount
    walk.fees.add(fee_id)
    return True


def _close(walk: Walk, event: dict[str, Any]) -> bool:
    snapshot = event["active_seats_result"]
    if event["cycle_index"] != walk.current_cycle or snapshot is None:
        return False
    if snapshot["cycle_index"] != walk.current_cycle:
        return False

    seats = snapshot["seat_ids"]
    commercial = _side(walk.commercial_pool, walk.commercial_carry, seats)
    fees = _side(walk.fee_pool, walk.fee_carry, seats)
    for seat_id in seats:
        _credit(walk.commercial_seats, seat_id, commercial[0])
        _credit(walk.fee_seats, seat_id, fees[0])

    walk.commercial_pool = walk.fee_pool = 0
    walk.commercial_carry, walk.fee_carry = commercial[1], fees[1]
    walk.current_cycle += 1
    walk.closes.append(
        Close(
            active_seat_count=len(seats),
            commercial_pool_in=commercial[2],
            commercial_per_seat=commercial[0],
            commercial_carry=commercial[1],
            fee_pool_in=fees[2],
            fee_per_seat=fees[0],
            fee_carry=fees[1],
        )
    )
    return True


def _side(pool: int, carry: int, seats: list[int]) -> tuple[int, int, int]:
    """Return (per seat, new carry, pool consumed) for one side of a close."""
    pool_in = pool + carry
    if not seats:
        return 0, pool_in, pool_in
    per_seat, residue = divmod(pool_in, len(seats))
    return per_seat, residue, pool_in


def _credit(balances: dict[Any, int], key: Any, amount: int) -> None:
    if amount:
        balances[key] = balances.get(key, 0) + amount
