"""Derived reporting views. No invariant depends on a metric."""

from __future__ import annotations

from typing import Any

from . import contract as c
from ..common.canonical import format_atomic
from .domain import State


def build_metrics(state: State) -> dict[str, Any]:
    capabilities = state.capabilities.values()
    return {
        "escrow_count": len(c.ESCROW_IDS),
        "bound_state_digest": state.bound_state_digest,
        "current_cycle": state.current_cycle,
        "capability_count": len(state.capabilities),
        "revoked_capability_count": sum(1 for item in capabilities if item.revoked),
        "exhausted_envelope_count": sum(
            1 for item in capabilities if item.spent == item.envelope_total
        ),
        "accepted_payout_count": len(state.accepted_payout_ids),
        "escrows": {
            escrow_id: _escrow_metrics(state, escrow_id)
            for escrow_id in sorted(c.ESCROW_IDS)
        },
    }


def _escrow_metrics(state: State, escrow_id: str) -> dict[str, Any]:
    balances = state.recipient_balances[escrow_id]
    return {
        "cap_atomic": format_atomic(c.ESCROW_CAPS[escrow_id]),
        "opening_custody": format_atomic(state.opening_custody[escrow_id]),
        "available_custody": format_atomic(state.available_custody[escrow_id]),
        "paid_out_total": format_atomic(state.paid_out_total[escrow_id]),
        "recipient_count": len(balances),
        "largest_recipient_balance": format_atomic(max(balances.values(), default=0)),
        "capability_count": sum(
            1
            for capability in state.capabilities.values()
            if capability.escrow_id == escrow_id
        ),
    }
