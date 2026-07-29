"""Value types, canonical serialization, and invariants."""

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
    supply_limit: int
    epoch_length: int
    unbonding_epochs: int
    fee_split_denominator: int
    fee_reward_parts: int


@dataclass(frozen=True)
class Authorities:
    clock: str
    issuance: str
    fee_allocation: str
    treasury: str
    escrow: str
    reward: str
    penalty: str


@dataclass(frozen=True)
class Participants:
    validators: dict[str, str]
    nodes: dict[str, str]


@dataclass(frozen=True)
class Genesis:
    height: int
    issued_supply: int
    accounts: dict[str, int]
    fee_pool: int
    treasury: int
    reward_pool: int
    penalty_pool: int


@dataclass(frozen=True)
class Manifest:
    parameters: Parameters
    authorities: Authorities
    participants: Participants
    genesis: Genesis
    source: dict[str, Any]


@dataclass
class Escrow:
    escrow_kind: str
    beneficiary: str
    amount: int
    unlock_epoch: int


@dataclass
class Bond:
    owner: str
    validator: str
    amount: int


@dataclass
class Unbonding:
    owner: str
    validator: str
    amount: int
    release_epoch: int


@dataclass
class State:
    height: int
    issued_supply: int
    accounts: dict[str, int]
    fee_pool: int
    treasury: int
    escrows: dict[str, Escrow] = field(default_factory=dict)
    bonds: dict[str, Bond] = field(default_factory=dict)
    unbondings: dict[str, Unbonding] = field(default_factory=dict)
    reward_pool: int = 0
    validator_claims: dict[str, int] = field(default_factory=dict)
    node_claims: dict[str, int] = field(default_factory=dict)
    penalty_pool: int = 0
    accepted_event_ids: set[str] = field(default_factory=set)

    def clone(self) -> State:
        return copy.deepcopy(self)


def initial_state(manifest: Manifest) -> State:
    genesis = manifest.genesis
    state = State(
        height=genesis.height,
        issued_supply=genesis.issued_supply,
        accounts=dict(genesis.accounts),
        fee_pool=genesis.fee_pool,
        treasury=genesis.treasury,
        reward_pool=genesis.reward_pool,
        penalty_pool=genesis.penalty_pool,
    )
    assert_invariants(state, manifest)
    return state


def checked_add(left: int, right: int) -> int | None:
    if left > MAX_U64 - right:
        return None
    return left + right


def checked_mul(left: int, right: int) -> int | None:
    if left != 0 and right > MAX_U64 // left:
        return None
    return left * right


def _checked_total(values: list[int]) -> int:
    total = 0
    for value in values:
        result = checked_add(total, value)
        if result is None:
            raise InvariantError("custodied value exceeds u64")
        total = result
    return total


def current_epoch(state: State, manifest: Manifest) -> int:
    return state.height // manifest.parameters.epoch_length


def state_value(state: State) -> dict[str, Any]:
    return {
        "height": state.height,
        "issued_supply": state.issued_supply,
        "accounts": dict(sorted(state.accounts.items())),
        "fee_pool": state.fee_pool,
        "treasury": state.treasury,
        "escrows": {
            key: {
                "escrow_kind": value.escrow_kind,
                "beneficiary": value.beneficiary,
                "amount": value.amount,
                "unlock_epoch": value.unlock_epoch,
            }
            for key, value in sorted(state.escrows.items())
        },
        "bonds": {
            key: {
                "owner": value.owner,
                "validator": value.validator,
                "amount": value.amount,
            }
            for key, value in sorted(state.bonds.items())
        },
        "unbondings": {
            key: {
                "owner": value.owner,
                "validator": value.validator,
                "amount": value.amount,
                "release_epoch": value.release_epoch,
            }
            for key, value in sorted(state.unbondings.items())
        },
        "reward_pool": state.reward_pool,
        "validator_claims": dict(sorted(state.validator_claims.items())),
        "node_claims": dict(sorted(state.node_claims.items())),
        "penalty_pool": state.penalty_pool,
        "accepted_event_ids": sorted(state.accepted_event_ids),
    }


def canonical_json(value: Any) -> bytes:
    text = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return text.encode("utf-8")


def domain_digest(domain: str, value: Any) -> str:
    payload = domain.encode("ascii") + b"\0" + canonical_json(value)
    return hashlib.sha256(payload).hexdigest()


def state_digest(state: State) -> str:
    return domain_digest(
        "protocol-stack:native-economy:state-v1",
        state_value(state),
    )


def assert_invariants(state: State, manifest: Manifest) -> None:
    scalars = [
        state.height,
        state.issued_supply,
        state.fee_pool,
        state.treasury,
        state.reward_pool,
        state.penalty_pool,
    ]
    if any(type(value) is not int or not 0 <= value <= MAX_U64 for value in scalars):
        raise InvariantError("state scalar is outside u64")

    values = list(state.accounts.values())
    values.extend([state.fee_pool, state.treasury])
    values.extend(record.amount for record in state.escrows.values())
    values.extend(record.amount for record in state.bonds.values())
    values.extend(record.amount for record in state.unbondings.values())
    values.append(state.reward_pool)
    values.extend(state.validator_claims.values())
    values.extend(state.node_claims.values())
    values.append(state.penalty_pool)
    if any(type(value) is not int or not 0 <= value <= MAX_U64 for value in values):
        raise InvariantError("bucket value is outside u64")

    if any(record.amount == 0 for record in state.escrows.values()):
        raise InvariantError("zero escrow exists")
    if any(record.amount == 0 for record in state.bonds.values()):
        raise InvariantError("zero bond exists")
    if any(record.amount == 0 for record in state.unbondings.values()):
        raise InvariantError("zero unbonding exists")
    if any(value == 0 for value in state.validator_claims.values()):
        raise InvariantError("zero validator claim exists")
    if any(value == 0 for value in state.node_claims.values()):
        raise InvariantError("zero node claim exists")

    if any(
        record.validator not in manifest.participants.validators
        for record in list(state.bonds.values()) + list(state.unbondings.values())
    ):
        raise InvariantError("position references an unknown validator")
    if not set(state.validator_claims) <= set(manifest.participants.validators):
        raise InvariantError("unknown validator claim")
    if not set(state.node_claims) <= set(manifest.participants.nodes):
        raise InvariantError("unknown node claim")

    custodied = _checked_total(values)
    if custodied != state.issued_supply:
        raise InvariantError("custodied value does not equal issued supply")
    if not 0 < state.issued_supply <= manifest.parameters.supply_limit:
        raise InvariantError("issued supply violates the manifest limit")
