"""An escrow run that exhausts every envelope and drains every escrow.

The opening custody is bound to a supplied `founder-economy-simulator-v1`
canonical state. Passing the state of the multi-year population run joins the
two models over a complete 731-cycle window: the escrows are drained of exactly
what three seats issued into them across their whole issuance period.

Exhausting delegated authority and exhausting the escrow are different
operational events, so each escrow proves both separately. The draining
capability's envelope equals its escrow's opening custody, so one further
payout on it reports `ENVELOPE_EXCEEDED`; a freshly granted capability with
authority to spare then reports `INSUFFICIENT_CUSTODY`, which is a statement
about the escrow rather than about the delegation.
"""

from __future__ import annotations

from typing import Any

from ..common.canonical import digest
from ..escrow_payout import contract as c

# Not a divisor of any of the three opening amounts, so the final payout of
# each escrow is a remainder rather than another full per-payout maximum.
PAYOUTS_PER_ESCROW = 7
RECIPIENTS_PER_ESCROW = 3
EXPIRY_CYCLE = 1_000
PROBE_AMOUNT = 1
FRESH_ENVELOPE = 1_000
EVALUATION_REFERENCE = "ai-evaluation-0001"


def opening_custody(state_value: dict[str, Any]) -> dict[str, int]:
    """Read the three singleton escrow custody keys from an economy state."""
    custody = state_value["typed_custody"]
    return {
        escrow_id: int(custody.get(c.custody_key(escrow_id), "0"))
        for escrow_id in c.ESCROW_IDS
    }


def payout_amounts(custody: int) -> list[int]:
    """Split one escrow's custody into payouts that drain it exactly."""
    if custody == 0:
        return []
    maximum = -(-custody // PAYOUTS_PER_ESCROW)
    amounts = []
    remaining = custody
    while remaining > 0:
        amount = min(maximum, remaining)
        amounts.append(amount)
        remaining -= amount
    return amounts


def _bind(state_value: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "bind-population-run",
        "kind": "bind_opening_custody",
        "economy_state_result": {
            "state_digest": digest(c.ECONOMY_STATE_LABEL, state_value),
            "state_value": state_value,
        },
    }


def _grant(
    capability_id: str,
    escrow_id: str,
    per_payout: int,
    envelope: int,
) -> dict[str, Any]:
    return {
        "id": f"grant-{capability_id}",
        "kind": "grant_capability",
        "capability_id": capability_id,
        "escrow_id": escrow_id,
        "per_payout_maximum": str(per_payout),
        "envelope_total": str(envelope),
        "expiry_cycle": EXPIRY_CYCLE,
    }


def _payout(
    payout_id: str,
    capability_id: str,
    escrow_id: str,
    recipient_id: str,
    amount: int,
) -> dict[str, Any]:
    return {
        "id": payout_id,
        "kind": "execute_payout",
        "payout_id": payout_id,
        "capability_id": capability_id,
        "escrow_id": escrow_id,
        "recipient_id": recipient_id,
        "amount_atomic": str(amount),
        "approval_result": {
            "payout_id": payout_id,
            "decision": c.APPROVED,
            "evaluation_reference": EVALUATION_REFERENCE,
        },
    }


def _escrow_events(
    index: int,
    escrow_id: str,
    custody: int,
) -> list[dict[str, Any]]:
    amounts = payout_amounts(custody)
    draining = f"cap-drain-{index}"
    generated = [_grant(draining, escrow_id, max(amounts), custody)]
    for position, amount in enumerate(amounts):
        recipient = f"recipient-{index}-{position % RECIPIENTS_PER_ESCROW}"
        generated.append(
            _payout(
                f"payout-{index}-{position:02d}",
                draining,
                escrow_id,
                recipient,
                amount,
            )
        )

    generated.append(
        _payout(
            f"probe-{index}-envelope",
            draining,
            escrow_id,
            f"recipient-{index}-0",
            PROBE_AMOUNT,
        )
    )
    fresh = f"cap-fresh-{index}"
    generated.append(_grant(fresh, escrow_id, PROBE_AMOUNT, FRESH_ENVELOPE))
    generated.append(
        _payout(
            f"probe-{index}-custody",
            fresh,
            escrow_id,
            f"recipient-{index}-0",
            PROBE_AMOUNT,
        )
    )
    return generated


def events(state_value: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the drain of every escrow opened by the supplied economy state."""
    custody = opening_custody(state_value)
    generated = [_bind(state_value)]
    for index, escrow_id in enumerate(c.ESCROW_IDS):
        generated.extend(_escrow_events(index, escrow_id, custody[escrow_id]))
    return generated
