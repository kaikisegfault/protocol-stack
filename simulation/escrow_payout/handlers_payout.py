"""The escrow payout transition.

Conditions are evaluated in one fixed order so a payout violating several of
them has one deterministic result code. Every authority condition precedes both
bound checks, which precede the custody check, so a capability bound to the
wrong escrow can never be used to probe that escrow's balance.
"""

from __future__ import annotations

from typing import Any

from . import contract as c
from ..common.canonical import checked_add, checked_sub
from .domain import Capability, State
from .operations import (
    DECREASE,
    INCREASE,
    Outcome,
    PayoutEffect,
    entry,
    failure,
)


def execute_payout(state: State, event: dict[str, Any]) -> Outcome:
    if event["payout_id"] in state.accepted_payout_ids:
        return failure("REPLAY")

    capability = state.capabilities.get(event["capability_id"])
    if capability is None:
        # Also covers every payout attempted before a bind, because no
        # capability can exist until the state is bound.
        return failure("UNKNOWN_CAPABILITY")
    if capability.escrow_id != event["escrow_id"]:
        return failure("ESCROW_MISMATCH")
    if capability.revoked:
        return failure("CAPABILITY_REVOKED")
    if state.current_cycle > capability.expiry_cycle:
        return failure("CAPABILITY_EXPIRED")

    amount = int(event["amount_atomic"])
    if amount == 0:
        return failure("ZERO_AMOUNT")

    withheld = _approval_failure(event)
    if withheld is not None:
        return failure(withheld)

    return _release(state, event, capability, amount)


def _approval_failure(event: dict[str, Any]) -> str | None:
    """The AI evaluation is supplied, never derived. It decides only whether."""
    approval = event["approval_result"]
    if approval is None:
        return "MISSING_RESEARCH_INPUT"
    if approval["payout_id"] != event["payout_id"]:
        return "INVALID_RESEARCH_INPUT"
    if approval["decision"] != c.APPROVED:
        return "APPROVAL_WITHHELD"
    return None


def _release(
    state: State,
    event: dict[str, Any],
    capability: Capability,
    amount: int,
) -> Outcome:
    if amount > capability.per_payout_maximum:
        return failure("PAYOUT_LIMIT_EXCEEDED")

    spent = checked_add(capability.spent, amount)
    if spent is None or spent > capability.envelope_total:
        return failure("ENVELOPE_EXCEEDED")

    escrow_id = capability.escrow_id
    available = checked_sub(state.available_custody[escrow_id], amount)
    if available is None:
        return failure("INSUFFICIENT_CUSTODY")

    recipient_id = event["recipient_id"]
    paid_out = checked_add(state.paid_out_total[escrow_id], amount)
    balance = checked_add(
        state.recipient_balances[escrow_id].get(recipient_id, 0), amount
    )
    if paid_out is None or balance is None:
        return failure("ARITHMETIC_OVERFLOW")

    return Outcome(
        code="OK",
        effect=PayoutEffect(
            payout_id=event["payout_id"],
            capability_id=event["capability_id"],
            escrow_id=escrow_id,
            recipient_id=recipient_id,
            available_custody=available,
            paid_out_total=paid_out,
            recipient_balance=balance,
            spent=spent,
        ),
        journal=[
            entry(f"custody:{escrow_id}", DECREASE, amount),
            entry(f"recipient:{escrow_id}:{recipient_id}", INCREASE, amount),
        ],
    )
