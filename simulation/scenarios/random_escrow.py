"""Seeded random event sequences for `escrow-payout-v1`.

This generator produces varied, hostile, mostly-legal traffic; it does not
predict outcomes. It deliberately emits replays, withheld approvals, approvals
bound to another payout, and amounts above every bound alongside legal events.
Nothing here asserts anything: the properties are the model's conservation
equations, and the caller checks them against the recorded final state.

Every sequence is a pure function of its seed, so a failing property names a
reproducible input.
"""

from __future__ import annotations

import random
from typing import Any

from ..common.canonical import digest
from ..escrow_payout import contract as escrow_contract

CAPABILITIES_PER_ESCROW = 2
ESCROW_RECIPIENTS = 5
SYNTHETIC_CUSTODY = 1_000_000_000_000
APPROVAL_SUPPLIED_PROBABILITY = 0.9

# Most payouts name the escrow their capability actually holds, so they reach
# the bound and custody checks instead of stopping at an escrow mismatch. The
# remainder deliberately name another escrow, which must be refused.
MATCHED_ESCROW_PROBABILITY = 0.85


def _capability(source: random.Random) -> tuple[str, str]:
    """Pick a capability identifier and the escrow it is bound to."""
    index = source.randrange(len(escrow_contract.ESCROW_IDS))
    slot = source.randrange(CAPABILITIES_PER_ESCROW)
    return f"cap-{index}-{slot}", escrow_contract.ESCROW_IDS[index]


def escrow_events(seed: int, count: int) -> list[dict[str, Any]]:
    """A bind of a synthetic economy state followed by capability traffic."""
    source = random.Random(seed)
    events: list[dict[str, Any]] = [_synthetic_bind()]
    cycle = 0
    for index in range(count):
        capability_id, held = _capability(source)
        named = (
            held
            if source.random() < MATCHED_ESCROW_PROBABILITY
            else source.choice(escrow_contract.ESCROW_IDS)
        )
        # Weighted so payouts dominate and revocation, which is permanent,
        # does not silence most capabilities early in a sequence.
        choice = source.randrange(10)
        if choice < 2:
            events.append(
                _random_grant(source, index, capability_id, held, cycle)
            )
        elif choice == 2:
            events.append(
                {
                    "id": f"e{index:05d}",
                    "kind": "revoke_capability",
                    "capability_id": capability_id,
                }
            )
        elif choice == 3:
            events.append(
                {
                    "id": f"e{index:05d}",
                    "kind": "advance_cycle",
                    "cycle_index": cycle,
                }
            )
            cycle += 1
        else:
            events.append(
                _random_payout(source, index, capability_id, named)
            )
    return events


def _synthetic_bind() -> dict[str, Any]:
    """A minimal economy-shaped state opening every escrow with the same amount."""
    state_value = {
        "seats": {},
        "channels": {},
        "pending_permissions": {},
        "evaluated_permission_keys": [],
        "accepted_direct_decision_ids": [],
        "typed_custody": {
            escrow_contract.custody_key(escrow_id): str(SYNTHETIC_CUSTODY)
            for escrow_id in escrow_contract.ESCROW_IDS
        },
    }
    return {
        "id": "bind-synthetic",
        "kind": "bind_opening_custody",
        "economy_state_result": {
            "state_digest": digest(
                escrow_contract.ECONOMY_STATE_LABEL, state_value
            ),
            "state_value": state_value,
        },
    }


def _random_grant(
    source: random.Random,
    index: int,
    capability_id: str,
    escrow_id: str,
    cycle: int,
) -> dict[str, Any]:
    envelope = source.randrange(1, SYNTHETIC_CUSTODY)
    return {
        "id": f"e{index:05d}",
        "kind": "grant_capability",
        "capability_id": capability_id,
        "escrow_id": escrow_id,
        "per_payout_maximum": str(source.randrange(1, envelope + 1)),
        "envelope_total": str(envelope),
        "expiry_cycle": cycle + source.randrange(4),
    }


def _random_payout(
    source: random.Random,
    index: int,
    capability_id: str,
    escrow_id: str,
) -> dict[str, Any]:
    payout_id = f"out-{source.randrange(64):03d}"
    approval = None
    if source.random() < APPROVAL_SUPPLIED_PROBABILITY:
        approval = {
            # Occasionally bound to another payout, which must be refused.
            "payout_id": payout_id if source.random() < 0.95 else "out-999",
            "decision": (
                escrow_contract.APPROVED
                if source.random() < 0.8
                else escrow_contract.REJECTED
            ),
            "evaluation_reference": "ai-evaluation-0001",
        }
    return {
        "id": f"e{index:05d}",
        "kind": "execute_payout",
        "payout_id": payout_id,
        "capability_id": capability_id,
        "escrow_id": escrow_id,
        "recipient_id": f"recipient-{source.randrange(ESCROW_RECIPIENTS)}",
        "amount_atomic": str(source.randrange(0, SYNTHETIC_CUSTODY // 2)),
        "approval_result": approval,
    }
