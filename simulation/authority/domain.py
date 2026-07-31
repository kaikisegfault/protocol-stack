"""Authority simulation value types and canonical digest helpers."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

MAX_U64 = (1 << 64) - 1


class InvariantError(RuntimeError):
    """The simulator constructed an invalid state."""


@dataclass(frozen=True)
class Parameters:
    epoch_length: int
    min_rotation_delay_epochs: int
    max_rotation_delay_epochs: int
    recovery_delay_epochs: int
    max_action_lifetime_epochs: int
    max_capabilities: int
    max_members_per_set: int
    max_approvals_per_result: int
    max_versions_per_capability: int


@dataclass(frozen=True)
class AuthoritySet:
    set_id: str
    version: int
    members: tuple[str, ...]
    threshold: int


@dataclass(frozen=True)
class Manifest:
    chain_id: str
    parameters: Parameters
    clock: str
    containment: AuthoritySet
    recovery: AuthoritySet
    capabilities: dict[tuple[str, str], AuthoritySet]
    genesis_height: int
    source: dict[str, Any]


@dataclass
class Version:
    version: int
    members: list[str]
    threshold: int
    activated_epoch: int
    retired_epoch: int | None
    source: str
    revoked_members: list[str] = field(default_factory=list)


@dataclass
class PendingRotation:
    version: int
    members: list[str]
    threshold: int
    activation_epoch: int
    result_id: str
    action_id: str
    action_digest: str


@dataclass
class Capability:
    module: str
    capability: str
    set_id: str
    active_version: int
    versions: list[Version]
    paused: bool = False
    paused_epoch: int | None = None
    pause_reason_digest: str | None = None
    pending_rotation: PendingRotation | None = None


@dataclass
class AuthorizationResult:
    result_id: str
    action_id: str
    chain_id: str
    module: str
    capability: str
    set_id: str
    set_version: int
    valid_from_epoch: int
    deadline_epoch: int
    action_digest: str
    authorized_height: int
    authorized_epoch: int
    approvals: list[dict[str, str]]


@dataclass
class State:
    height: int
    capabilities: dict[tuple[str, str], Capability]
    accepted_event_ids: set[str] = field(default_factory=set)
    accepted_result_ids: set[str] = field(default_factory=set)
    accepted_action_ids: set[str] = field(default_factory=set)
    accepted_proof_ids: set[str] = field(default_factory=set)
    authorization_results: dict[str, AuthorizationResult] = field(
        default_factory=dict
    )

    def clone(self) -> State:
        return copy.deepcopy(self)


def initial_state(manifest: Manifest) -> State:
    capabilities: dict[tuple[str, str], Capability] = {}
    for key, authority_set in manifest.capabilities.items():
        capabilities[key] = Capability(
            module=key[0],
            capability=key[1],
            set_id=authority_set.set_id,
            active_version=1,
            versions=[
                Version(
                    version=1,
                    members=list(authority_set.members),
                    threshold=authority_set.threshold,
                    activated_epoch=manifest.genesis_height
                    // manifest.parameters.epoch_length,
                    retired_epoch=None,
                    source="genesis",
                )
            ],
        )
    return State(height=manifest.genesis_height, capabilities=capabilities)


def current_epoch(state: State, manifest: Manifest) -> int:
    return state.height // manifest.parameters.epoch_length


def checked_add(left: int, right: int) -> int | None:
    if left > MAX_U64 - right:
        return None
    return left + right


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def domain_digest(domain: str, value: Any) -> str:
    return hashlib.sha256(
        domain.encode("ascii") + b"\0" + canonical_json(value)
    ).hexdigest()


def action_digest(
    *,
    chain_id: str,
    module: str,
    capability: str,
    set_id: str,
    set_version: int,
    result_id: str,
    action_id: str,
    valid_from_epoch: int,
    deadline_epoch: int,
    action: dict[str, Any],
) -> str:
    return domain_digest(
        "protocol-stack:authority:action-v1",
        {
            "schema": "protocol-stack/authority-action/v1",
            "chain_id": chain_id,
            "module": module,
            "capability": capability,
            "set_id": set_id,
            "set_version": set_version,
            "result_id": result_id,
            "action_id": action_id,
            "valid_from_epoch": valid_from_epoch,
            "deadline_epoch": deadline_epoch,
            "action": action,
        },
    )


def control_digest(
    manifest: Manifest,
    event: dict[str, Any],
    capability: str,
    action: dict[str, Any],
) -> str:
    return action_digest(
        chain_id=manifest.chain_id,
        module="authority",
        capability=capability,
        set_id=event["set_id"],
        set_version=event["set_version"],
        result_id=event["result_id"],
        action_id=event["action_id"],
        valid_from_epoch=event["valid_from_epoch"],
        deadline_epoch=event["deadline_epoch"],
        action=action,
    )


def active_version(capability: Capability) -> Version:
    version = capability.versions[-1]
    if version.version != capability.active_version:
        raise InvariantError("active version is not final")
    return version
