"""The commercial payment and transaction-fee transitions.

The two paths share no state term. A commercial payment never reads or writes a
fee bucket and a fee never reads or writes a commercial one, which is what makes
"fees are not deducted from commercial revenue" a structural property.
"""

from __future__ import annotations

from typing import Any

from . import contract as c
from ..common.canonical import checked_add
from .domain import State
from .operations import (
    DECREASE,
    INCREASE,
    FeeEffect,
    JournalEntry,
    Outcome,
    PaymentEffect,
    entry,
    failure,
)


def route_commercial_payment(state: State, event: dict[str, Any]) -> Outcome:
    payment_id = event["payment_id"]
    project_id = event["project_creator_id"]
    product_id = event["product_creator_id"]
    amount = int(event["amount_atomic"])

    if payment_id in state.accepted_payment_ids:
        return failure("REPLAY")
    if amount == 0:
        return failure("ZERO_AMOUNT")
    if product_id is not None and product_id == project_id:
        return failure("DUPLICATE_CREATOR")

    parts = c.split(amount, product_creator=product_id is not None)
    if parts is None:
        return failure("ARITHMETIC_OVERFLOW")
    founder_credit, project_amount, product_amount, system_share = parts

    pool = checked_add(state.commercial_pool, founder_credit)
    system = checked_add(state.system_creator_balance, system_share)
    routed = checked_add(state.commercial_routed_total, amount)
    if pool is None or system is None or routed is None:
        return failure("ARITHMETIC_OVERFLOW")

    legs = [(project_id, project_amount)]
    if product_id is not None:
        legs.append((product_id, product_amount))
    credits: list[tuple[str, int]] = []
    for creator_id, leg in legs:
        if leg == 0:
            continue
        updated = checked_add(state.creator_balances.get(creator_id, 0), leg)
        if updated is None:
            return failure("ARITHMETIC_OVERFLOW")
        credits.append((creator_id, updated))

    return Outcome(
        code="OK",
        effect=PaymentEffect(
            payment_id=payment_id,
            commercial_pool=pool,
            system_creator_balance=system,
            commercial_routed_total=routed,
            creator_balances=tuple(credits),
        ),
        journal=_payment_journal(amount, founder_credit, legs, system_share),
    )


def _payment_journal(
    amount: int,
    founder_credit: int,
    legs: list[tuple[str, int]],
    system_share: int,
) -> list[JournalEntry]:
    """A bucket that receives nothing does not appear, so no entry is zero."""
    journal = [
        entry("payment", DECREASE, amount),
        entry("commercial_pool", INCREASE, founder_credit),
    ]
    journal.extend(
        entry(f"creator:{creator_id}", INCREASE, leg)
        for creator_id, leg in legs
        if leg != 0
    )
    if system_share != 0:
        journal.append(entry("system_creator", INCREASE, system_share))
    return journal


def route_transaction_fee(state: State, event: dict[str, Any]) -> Outcome:
    fee_id = event["fee_id"]
    amount = int(event["amount_atomic"])

    if fee_id in state.accepted_fee_ids:
        return failure("REPLAY")
    if amount == 0:
        return failure("ZERO_AMOUNT")

    pool = checked_add(state.fee_pool, amount)
    routed = checked_add(state.fee_routed_total, amount)
    if pool is None or routed is None:
        return failure("ARITHMETIC_OVERFLOW")

    return Outcome(
        code="OK",
        effect=FeeEffect(fee_id=fee_id, fee_pool=pool, fee_routed_total=routed),
        journal=[entry("fee", DECREASE, amount), entry("fee_pool", INCREASE, amount)],
    )
