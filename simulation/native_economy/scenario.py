"""Versioned deterministic multi-actor research scenario generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .types import MAX_U64
from .validation import MANIFEST_SCHEMA

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


def generate_scenario(seed: int, rounds: int = 8) -> tuple[dict, list[dict]]:
    if type(rounds) is not int or not 1 <= rounds <= 64:
        raise ValueError("rounds must be in 1..64")
    stream = SplitMix64(seed)
    actors = ["alice", "bob", "carol", "dave"]
    validators = ["validator_a", "validator_b"]
    nodes = ["node_a", "node_b"]
    manifest = _manifest()
    events: list[dict[str, Any]] = []
    height = 0
    sequence = 0

    def append(kind: str, actor: str, **fields: Any) -> None:
        nonlocal sequence
        sequence += 1
        events.append(
            {
                "id": f"event_{sequence:04d}",
                "height": height,
                "kind": kind,
                "actor": actor,
                **fields,
            }
        )

    for round_index in range(rounds):
        owner = actors[stream.bounded(len(actors))]
        destination = actors[(actors.index(owner) + 1 + stream.bounded(3)) % 4]
        validator = validators[stream.bounded(len(validators))]
        node = nodes[stream.bounded(len(nodes))]
        issue_amount = 20 + stream.bounded(31)
        transfer_amount = 30 + stream.bounded(71)
        fee_amount = 11 + stream.bounded(90)
        reward_funding = 100 + stream.bounded(101)
        validator_reward = 25 + stream.bounded(26)
        node_reward = 20 + stream.bounded(21)
        escrow_amount = 50 + stream.bounded(51)
        bond_amount = 120 + stream.bounded(81)
        bond_penalty = 5 + stream.bounded(11)
        unbond_amount = 40 + stream.bounded(31)
        unbond_penalty = 3 + stream.bounded(8)

        append("issue", "issuer", amount=issue_amount)
        append(
            "transfer",
            owner,
            source=owner,
            destination=destination,
            amount=transfer_amount,
        )
        append("charge_fee", owner, account=owner, amount=fee_amount)
        append("allocate_fees", "fee_allocator", amount=fee_amount)
        append("fund_rewards", "treasury", amount=reward_funding)
        append(
            "allocate_reward",
            "reward",
            role="validator",
            participant=validator,
            amount=validator_reward,
        )
        append(
            "allocate_reward",
            "reward",
            role="node",
            participant=node,
            amount=node_reward,
        )
        append(
            "claim_reward",
            manifest["participants"]["validators"][validator],
            role="validator",
            participant=validator,
            amount=validator_reward,
        )
        append(
            "claim_reward",
            manifest["participants"]["nodes"][node],
            role="node",
            participant=node,
            amount=node_reward,
        )
        escrow_id = f"escrow_{round_index:02d}"
        append(
            "open_escrow",
            owner,
            escrow_id=escrow_id,
            escrow_kind="general" if round_index % 2 == 0 else "venture",
            source_kind="account",
            source=owner,
            beneficiary=destination,
            unlock_epoch=(height // 5) + 1,
            amount=escrow_amount,
        )
        bond_id = f"bond_{round_index:02d}"
        append(
            "bond",
            owner,
            bond_id=bond_id,
            owner=owner,
            validator=validator,
            amount=bond_amount,
        )
        append(
            "penalize",
            "penalty",
            source_kind="bond",
            position_id=bond_id,
            amount=bond_penalty,
        )
        unbonding_id = f"unbonding_{round_index:02d}"
        append(
            "begin_unbond",
            owner,
            bond_id=bond_id,
            unbonding_id=unbonding_id,
            amount=unbond_amount,
        )
        append(
            "penalize",
            "penalty",
            source_kind="unbonding",
            position_id=unbonding_id,
            amount=unbond_penalty,
        )

        target = height + 5
        while height < target:
            append("advance_height", "clock", to_height=height + 1)
            height += 1

        append("release_escrow", "escrow", escrow_id=escrow_id)
        append("complete_unbond", owner, unbonding_id=unbonding_id)
        append(
            "route_penalty",
            "penalty",
            amount=bond_penalty + unbond_penalty,
        )

    return manifest, events


def _manifest() -> dict:
    return {
        "schema": MANIFEST_SCHEMA,
        "research_only": True,
        "parameters": {
            "supply_limit": 1_000_000,
            "epoch_length": 5,
            "unbonding_epochs": 1,
            "fee_split_denominator": 10,
            "fee_reward_parts": 3,
        },
        "authorities": {
            "clock": "clock",
            "issuance": "issuer",
            "fee_allocation": "fee_allocator",
            "treasury": "treasury",
            "escrow": "escrow",
            "reward": "reward",
            "penalty": "penalty",
        },
        "participants": {
            "validators": {
                "validator_a": "alice",
                "validator_b": "bob",
            },
            "nodes": {
                "node_a": "carol",
                "node_b": "dave",
            },
        },
        "genesis": {
            "height": 0,
            "issued_supply": 500_000,
            "accounts": {
                "alice": 100_000,
                "bob": 100_000,
                "carol": 100_000,
                "dave": 100_000,
            },
            "fee_pool": 0,
            "treasury": 100_000,
            "reward_pool": 0,
            "penalty_pool": 0,
        },
    }
