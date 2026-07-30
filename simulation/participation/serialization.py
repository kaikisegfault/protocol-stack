"""Canonical participation state projection and digest."""

from __future__ import annotations

from typing import Any

from .domain import Participant, State, domain_digest


def state_digest(state: State) -> str:
    return domain_digest("protocol-stack:participation:state-v1", state_value(state))


def state_value(state: State) -> dict[str, Any]:
    return {
        "height": state.height,
        "participants": {
            key: _participant_value(value)
            for key, value in sorted(state.participants.items())
        },
        "accepted_event_ids": sorted(state.accepted_event_ids),
        "accepted_proof_ids": sorted(state.accepted_proof_ids),
        "contributions": [
            {
                "epoch": key[0],
                "role": key[1],
                "participant": key[2],
                "kind": key[3],
                "units": value.units,
                "weighted_units": value.weighted_units,
            }
            for key, value in sorted(state.contributions.items())
        ],
        "participant_totals": [
            {
                "epoch": key[0],
                "role": key[1],
                "participant": key[2],
                "raw_units": value.raw_units,
                "weighted_units": value.weighted_units,
            }
            for key, value in sorted(state.participant_totals.items())
        ],
        "role_totals": [
            {
                "epoch": key[0],
                "role": key[1],
                "weighted_units": value.weighted_units,
                "participant_count": value.participant_count,
            }
            for key, value in sorted(state.role_totals.items())
        ],
        "budgets": [
            {
                "epoch": key[0],
                "role": key[1],
                "amount": value.amount,
                "total_weight": value.total_weight,
                "participant_count": value.participant_count,
                "settled_count": value.settled_count,
                "allocated": value.allocated,
                "finalized": value.finalized,
                "remainder": value.remainder,
            }
            for key, value in sorted(state.budgets.items())
        ],
        "entitlements": [
            {
                "epoch": key[0],
                "role": key[1],
                "participant": key[2],
                "participant_weight": value.participant_weight,
                "amount": value.amount,
            }
            for key, value in sorted(state.entitlements.items())
        ],
    }


def _participant_value(value: Participant) -> dict[str, Any]:
    return {
        "participant": value.participant,
        "role": value.role,
        "owner": value.owner,
        "payout_account": value.payout_account,
        "phase": value.phase,
        "registered_epoch": value.registered_epoch,
        "activation_epoch": value.activation_epoch,
        "activated_epoch": value.activated_epoch,
        "exit_epoch": value.exit_epoch,
        "unbond_ready_epoch": value.unbond_ready_epoch,
        "jailed_until_epoch": value.jailed_until_epoch,
        "recovery_requested": value.recovery_requested,
        "bond_id": value.bond_id,
        "confirmed_bond": value.confirmed_bond,
        "terminal_reason": value.terminal_reason,
        "removed_epoch": value.removed_epoch,
    }
