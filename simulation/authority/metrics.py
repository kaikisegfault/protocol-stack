"""Exact integer authority metrics."""

from __future__ import annotations

from typing import Any

from .domain import Manifest, State


def build_metrics(
    state: State,
    manifest: Manifest,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    accepted_by_kind: dict[str, int] = {}
    rejected_by_result: dict[str, int] = {}
    for record in records:
        target = accepted_by_kind if record["accepted"] else rejected_by_result
        key = record["kind"] if record["accepted"] else record["result"]
        target[key] = target.get(key, 0) + 1

    by_capability: dict[str, int] = {}
    surpluses: list[int] = []
    for result in state.authorization_results.values():
        key = f"{result.module}/{result.capability}"
        by_capability[key] = by_capability.get(key, 0) + 1
        binding = state.capabilities[(result.module, result.capability)]
        version = next(
            item for item in binding.versions if item.version == result.set_version
        )
        surpluses.append(len(result.approvals) - version.threshold)

    versions = [
        version
        for capability in state.capabilities.values()
        for version in capability.versions
    ]
    return {
        "inventory": {
            "capabilities": len(state.capabilities),
            "paused_capabilities": sum(
                capability.paused for capability in state.capabilities.values()
            ),
            "retained_versions": len(versions),
            "active_members": sum(
                len(capability.versions[-1].members)
                for capability in state.capabilities.values()
            ),
            "active_thresholds": sum(
                capability.versions[-1].threshold
                for capability in state.capabilities.values()
            ),
        },
        "accepted_events": dict(sorted(accepted_by_kind.items())),
        "rejected_results": dict(sorted(rejected_by_result.items())),
        "authorization_results": dict(sorted(by_capability.items())),
        "accepted_approvals": len(state.accepted_proof_ids),
        "unique_member_proofs": len(state.accepted_proof_ids),
        "rotations_scheduled": accepted_by_kind.get("schedule_rotation", 0),
        "rotations_activated": accepted_by_kind.get("activate_rotation", 0),
        "pauses": accepted_by_kind.get("pause_capability", 0),
        "member_revocations": accepted_by_kind.get("revoke_member", 0),
        "recoveries": accepted_by_kind.get("recover_capability", 0),
        "approval_surplus": {
            "minimum": min(surpluses) if surpluses else 0,
            "maximum": max(surpluses) if surpluses else 0,
        },
        "epoch_length": manifest.parameters.epoch_length,
    }
