"""Scenario builder, deterministic stream, and fixed research manifest."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import MAX_U64, action_digest, control_digest, domain_digest
from .validation import MANIFEST_SCHEMA, parse_manifest

_GOLDEN_GAMMA = 0x9E3779B97F4A7C15
_MIX_1 = 0xBF58476D1CE4E5B9
_MIX_2 = 0x94D049BB133111EB


@dataclass
class SplitMix64:
    state: int

    def __post_init__(self) -> None:
        if type(self.state) is not int or not 0 <= self.state <= MAX_U64:
            raise ValueError("seed must be a u64")

    def next(self) -> int:
        self.state = (self.state + _GOLDEN_GAMMA) & MAX_U64
        value = self.state
        value = ((value ^ (value >> 30)) * _MIX_1) & MAX_U64
        value = ((value ^ (value >> 27)) * _MIX_2) & MAX_U64
        return value ^ (value >> 31)

    def bounded(self, upper: int) -> int:
        if upper <= 0:
            raise ValueError("upper bound must be positive")
        return self.next() % upper


class Builder:
    def __init__(self, seed: int):
        self.seed = seed
        self.stream = SplitMix64(seed)
        self.manifest_value = _manifest()
        self.manifest = parse_manifest(self.manifest_value)
        self.events: list[dict[str, Any]] = []
        self.targets: dict[str, dict[str, Any]] = {}
        self.height = 0
        self.sequence = 0
        self.proof_sequence = 0

    def append(self, kind: str, **fields: Any) -> dict[str, Any]:
        self.sequence += 1
        event = {
            "id": f"event_{self.sequence:04d}",
            "height": self.height,
            "kind": kind,
            **fields,
        }
        self.events.append(event)
        return event

    def approval(self, member: str) -> dict[str, str]:
        self.proof_sequence += 1
        proof_id = f"proof_{self.proof_sequence:04d}"
        return {
            "member": member,
            "proof_id": proof_id,
            "evidence_digest": domain_digest(
                "protocol-stack:authority:scenario-evidence-v1",
                {"seed": self.seed, "proof_id": proof_id, "member": member},
            ),
        }

    def common(
        self,
        set_id: str,
        version: int,
        approvals: list[dict[str, str]],
        *,
        result_id: str | None = None,
        action_id: str | None = None,
        valid_from: int = 0,
        deadline: int = 2,
        chain_id: str = "research_chain",
    ) -> dict[str, Any]:
        suffix = self.sequence + 1
        return {
            "chain_id": chain_id,
            "set_id": set_id,
            "set_version": version,
            "result_id": result_id or f"result_{suffix:04d}",
            "action_id": action_id or f"action_{suffix:04d}",
            "valid_from_epoch": valid_from,
            "deadline_epoch": deadline,
            "action_digest": "0" * 64,
            "approvals": approvals,
        }

    def authorize(
        self,
        target: dict[str, Any],
        module: str,
        capability: str,
        set_id: str,
        version: int,
        approvals: list[dict[str, str]],
        **common_overrides: Any,
    ) -> dict[str, Any]:
        common = self.common(set_id, version, approvals, **common_overrides)
        common["action_digest"] = action_digest(
            chain_id=common["chain_id"],
            module=module,
            capability=capability,
            set_id=set_id,
            set_version=version,
            result_id=common["result_id"],
            action_id=common["action_id"],
            valid_from_epoch=common["valid_from_epoch"],
            deadline_epoch=common["deadline_epoch"],
            action=target,
        )
        event = self.append(
            "authorize_action",
            module=module,
            capability=capability,
            **common,
        )
        self.targets[common["result_id"]] = target
        return event

    def control(
        self,
        kind: str,
        control_capability: str,
        action: dict[str, Any],
        set_id: str,
        version: int,
        approvals: list[dict[str, str]],
        *,
        valid_from: int = 0,
        deadline: int = 2,
        **fields: Any,
    ) -> dict[str, Any]:
        common = self.common(
            set_id,
            version,
            approvals,
            valid_from=valid_from,
            deadline=deadline,
        )
        event = {
            "id": f"event_{self.sequence + 1:04d}",
            "height": self.height,
            "kind": kind,
            **common,
            **fields,
        }
        event["action_digest"] = control_digest(
            self.manifest,
            event,
            control_capability,
            action,
        )
        outer = {"id", "height", "kind"}
        return self.append(
            kind,
            **{key: value for key, value in event.items() if key not in outer},
        )

    def advance_to(self, height: int) -> None:
        while self.height < height:
            self.append(
                "advance_height",
                actor="clock",
                to_height=self.height + 1,
            )
            self.height += 1


def _manifest() -> dict[str, Any]:
    def authority_set(set_id: str, prefix: str) -> dict[str, Any]:
        return {
            "set_id": set_id,
            "version": 1,
            "members": [f"{prefix}_a", f"{prefix}_b", f"{prefix}_c"],
            "threshold": 2,
        }

    return {
        "schema": MANIFEST_SCHEMA,
        "research_only": True,
        "chain_id": "research_chain",
        "parameters": {
            "epoch_length": 10,
            "min_rotation_delay_epochs": 1,
            "max_rotation_delay_epochs": 4,
            "recovery_delay_epochs": 2,
            "max_action_lifetime_epochs": 2,
            "max_capabilities": 8,
            "max_members_per_set": 8,
            "max_approvals_per_result": 16,
            "max_versions_per_capability": 8,
        },
        "clock": "clock",
        "control_sets": {
            "containment": authority_set("containment_set", "contain"),
            "recovery": authority_set("recovery_set", "recover"),
        },
        "capabilities": {
            "native_economy": {
                "issuance": authority_set("issuance_set", "issuer"),
                "reward": authority_set("reward_set", "rewarder"),
            },
            "participation": {
                "registration": authority_set(
                    "registration_set", "registrar"
                ),
                "contribution/validator/vote": authority_set(
                    "vote_set", "vote"
                ),
            },
        },
        "genesis": {"height": 0},
    }
