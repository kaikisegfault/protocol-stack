"""Authority-result construction and exact target release for stress runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from simulation.authority.adapter import build_authorized_events
from simulation.authority.domain import action_digest, control_digest, domain_digest
from simulation.authority.validation import parse_manifest

from .design import Configuration
from .manifests import CAPABILITY_SETS


@dataclass(frozen=True)
class AuthorizedTarget:
    module: str
    capability: str
    result_id: str
    event: dict[str, Any]
    legitimate: bool


class AuthorityBuilder:
    def __init__(
        self,
        config: Configuration,
        seed: int,
        manifest_value: dict[str, Any],
    ) -> None:
        self.config = config
        self.seed = seed
        self.manifest_value = manifest_value
        self.manifest = parse_manifest(manifest_value)
        self.events: list[dict[str, Any]] = []
        self.targets: list[AuthorizedTarget] = []
        self.height = 0
        self.event_sequence = 0
        self.result_sequence = 0
        self.proof_sequence = 0

    def add_operational(
        self,
        module: str,
        capability: str,
        event: dict[str, Any],
        *,
        legitimate: bool = True,
    ) -> AuthorizedTarget:
        self.result_sequence += 1
        result_id = f"result_{self.result_sequence:04d}"
        action_id = f"action_{self.result_sequence:04d}"
        set_id = CAPABILITY_SETS[(module, capability)]
        members = self.honest("operator") if legitimate else self._compromised()
        common = self._common(result_id, action_id, set_id, 1, members)
        common["action_digest"] = action_digest(
            chain_id="stress_chain",
            module=module,
            capability=capability,
            set_id=set_id,
            set_version=1,
            result_id=result_id,
            action_id=action_id,
            valid_from_epoch=0,
            deadline_epoch=64,
            action=event,
        )
        self.append(
            "authorize_action",
            module=module,
            capability=capability,
            **common,
        )
        target = AuthorizedTarget(
            module=module,
            capability=capability,
            result_id=result_id,
            event=dict(event),
            legitimate=legitimate,
        )
        self.targets.append(target)
        return target

    def add_control(
        self,
        kind: str,
        control_capability: str,
        set_id: str,
        set_version: int,
        members: list[str],
        action: dict[str, Any],
        **fields: Any,
    ) -> str:
        self.result_sequence += 1
        result_id = f"result_{self.result_sequence:04d}"
        action_id = f"action_{self.result_sequence:04d}"
        common = self._common(
            result_id,
            action_id,
            set_id,
            set_version,
            members,
        )
        event = {
            "id": f"authority_event_{self.event_sequence + 1:04d}",
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
        )["id"]

    def _common(
        self,
        result_id: str,
        action_id: str,
        set_id: str,
        set_version: int,
        members: list[str],
    ) -> dict[str, Any]:
        return {
            "chain_id": "stress_chain",
            "set_id": set_id,
            "set_version": set_version,
            "result_id": result_id,
            "action_id": action_id,
            "valid_from_epoch": 0,
            "deadline_epoch": 64,
            "action_digest": "0" * 64,
            "approvals": [self._approval(member) for member in members],
        }

    def _approval(self, member: str) -> dict[str, str]:
        self.proof_sequence += 1
        proof_id = f"authority_proof_{self.proof_sequence:04d}"
        return {
            "member": member,
            "proof_id": proof_id,
            "evidence_digest": domain_digest(
                "protocol-stack:economic-stress:evidence-v1",
                {
                    "case_id": self.config.case_id,
                    "seed": self.seed,
                    "proof_id": proof_id,
                    "member": member,
                },
            ),
        }

    def honest(self, prefix: str) -> list[str]:
        return [
            f"{prefix}_{suffix}"
            for suffix in ("a", "b", "c")[: self.config.honest_available]
        ]

    def _compromised(self) -> list[str]:
        members = ("operator_a", "operator_b", "operator_c")
        count = self.config.compromised_available
        return list(members[len(members) - count :]) if count else []

    def advance(self, count: int) -> None:
        target = self.height + count
        while self.height < target:
            self.append(
                "advance_height",
                actor="authority_clock",
                to_height=self.height + 1,
            )
            self.height += 1

    def append(self, kind: str, **fields: Any) -> dict[str, Any]:
        self.event_sequence += 1
        event = {
            "id": f"authority_event_{self.event_sequence:04d}",
            "height": self.height,
            "kind": kind,
            **fields,
        }
        self.events.append(event)
        return event


def release_targets(
    authority_result: dict[str, Any],
    authority_manifest: dict[str, Any],
    target_manifest: dict[str, Any],
    module: str,
    targets: list[AuthorizedTarget],
) -> list[dict[str, Any]]:
    accepted = {
        result["result_id"]
        for result in authority_result["final_state"]["authorization_results"]
    }
    pairs = [
        (target.result_id, target.event)
        for target in targets
        if target.module == module and target.result_id in accepted
    ]
    if not pairs:
        return []
    return build_authorized_events(
        authority_result,
        authority_manifest,
        target_manifest,
        module=module,
        pairs=pairs,
    )
