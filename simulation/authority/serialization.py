"""Canonical authority state projection and digest."""

from __future__ import annotations

from typing import Any

from .domain import (
    AuthorizationResult,
    Capability,
    PendingRotation,
    State,
    Version,
    domain_digest,
)


def state_digest(state: State) -> str:
    return domain_digest("protocol-stack:authority:state-v1", state_value(state))


def state_value(state: State) -> dict[str, Any]:
    return {
        "height": state.height,
        "capabilities": [
            _capability_value(value)
            for _, value in sorted(state.capabilities.items())
        ],
        "accepted_event_ids": sorted(state.accepted_event_ids),
        "accepted_result_ids": sorted(state.accepted_result_ids),
        "accepted_action_ids": sorted(state.accepted_action_ids),
        "accepted_proof_ids": sorted(state.accepted_proof_ids),
        "authorization_results": [
            _result_value(value)
            for _, value in sorted(state.authorization_results.items())
        ],
    }


def _capability_value(value: Capability) -> dict[str, Any]:
    return {
        "module": value.module,
        "capability": value.capability,
        "set_id": value.set_id,
        "active_version": value.active_version,
        "paused": value.paused,
        "paused_epoch": value.paused_epoch,
        "pause_reason_digest": value.pause_reason_digest,
        "versions": [_version_value(item) for item in value.versions],
        "pending_rotation": (
            None
            if value.pending_rotation is None
            else _pending_value(value.pending_rotation)
        ),
    }


def _version_value(value: Version) -> dict[str, Any]:
    return {
        "version": value.version,
        "members": sorted(value.members),
        "threshold": value.threshold,
        "activated_epoch": value.activated_epoch,
        "retired_epoch": value.retired_epoch,
        "source": value.source,
        "revoked_members": sorted(value.revoked_members),
    }


def _pending_value(value: PendingRotation) -> dict[str, Any]:
    return {
        "version": value.version,
        "members": sorted(value.members),
        "threshold": value.threshold,
        "activation_epoch": value.activation_epoch,
        "result_id": value.result_id,
        "action_id": value.action_id,
        "action_digest": value.action_digest,
    }


def _result_value(value: AuthorizationResult) -> dict[str, Any]:
    return {
        "schema": "protocol-stack/authority-result/v1",
        "result_id": value.result_id,
        "action_id": value.action_id,
        "chain_id": value.chain_id,
        "module": value.module,
        "capability": value.capability,
        "set_id": value.set_id,
        "set_version": value.set_version,
        "valid_from_epoch": value.valid_from_epoch,
        "deadline_epoch": value.deadline_epoch,
        "action_digest": value.action_digest,
        "authorized_height": value.authorized_height,
        "authorized_epoch": value.authorized_epoch,
        "approvals": [
            dict(item)
            for item in sorted(
                value.approvals,
                key=lambda item: (item["member"], item["proof_id"]),
            )
        ],
    }
