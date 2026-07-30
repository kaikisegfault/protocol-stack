"""Participation value types and checked numeric helpers."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

MAX_U64 = (1 << 64) - 1


@dataclass(frozen=True)
class Parameters:
    epoch_length: int
    activation_delay_epochs: int
    exit_delay_epochs: int
    removal_hold_epochs: int
    max_jail_epochs: int
    max_participants: int
    validator_minimum_bond: int
    max_units_per_proof: int
    max_units_per_participant_epoch: int


@dataclass(frozen=True)
class Authorities:
    clock: str
    registration: str
    stake: str
    lifecycle: str
    enforcement: str
    reward: str


@dataclass(frozen=True)
class ContributionPolicy:
    verifier: str
    weight: int


@dataclass(frozen=True)
class Manifest:
    parameters: Parameters
    authorities: Authorities
    contributions: dict[str, dict[str, ContributionPolicy]]
    genesis_height: int
    source: dict[str, Any]


@dataclass
class Participant:
    participant: str
    role: str
    owner: str
    payout_account: str
    phase: str
    registered_epoch: int
    activation_epoch: int
    activated_epoch: int | None
    exit_epoch: int | None
    unbond_ready_epoch: int | None
    jailed_until_epoch: int | None
    recovery_requested: bool
    bond_id: str | None
    confirmed_bond: int | None
    terminal_reason: str | None
    removed_epoch: int | None


@dataclass
class Contribution:
    units: int
    weighted_units: int


@dataclass
class ParticipantTotal:
    raw_units: int
    weighted_units: int


@dataclass
class RoleTotal:
    weighted_units: int
    participant_count: int


@dataclass
class Budget:
    amount: int
    total_weight: int
    participant_count: int
    settled_count: int = 0
    allocated: int = 0
    finalized: bool = False
    remainder: int | None = None


@dataclass
class Entitlement:
    participant_weight: int
    amount: int


@dataclass
class State:
    height: int
    participants: dict[str, Participant] = field(default_factory=dict)
    accepted_event_ids: set[str] = field(default_factory=set)
    accepted_proof_ids: set[str] = field(default_factory=set)
    contributions: dict[tuple[int, str, str, str], Contribution] = field(
        default_factory=dict
    )
    participant_totals: dict[tuple[int, str, str], ParticipantTotal] = field(
        default_factory=dict
    )
    role_totals: dict[tuple[int, str], RoleTotal] = field(default_factory=dict)
    budgets: dict[tuple[int, str], Budget] = field(default_factory=dict)
    entitlements: dict[tuple[int, str, str], Entitlement] = field(
        default_factory=dict
    )

    def clone(self) -> State:
        return copy.deepcopy(self)


def initial_state(manifest: Manifest) -> State:
    return State(height=manifest.genesis_height)


def checked_add(left: int, right: int) -> int | None:
    if left > MAX_U64 - right:
        return None
    return left + right


def checked_mul(left: int, right: int) -> int | None:
    if left != 0 and right > MAX_U64 // left:
        return None
    return left * right


def current_epoch(state: State, manifest: Manifest) -> int:
    return state.height // manifest.parameters.epoch_length


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def domain_digest(domain: str, value: Any) -> str:
    payload = domain.encode("ascii") + b"\0" + canonical_json(value)
    return hashlib.sha256(payload).hexdigest()
