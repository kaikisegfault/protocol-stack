"""Versioned deterministic adverse-participation scenario generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import MAX_U64
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


def generate_scenario(seed: int, rounds: int = 4) -> tuple[dict, list[dict]]:
    if type(rounds) is not int or not 1 <= rounds <= 32:
        raise ValueError("rounds must be in 1..32")
    stream = SplitMix64(seed)
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

    def proof_fields() -> dict[str, str]:
        return {
            "proof_id": f"proof_{sequence + 1:04d}",
            "evidence_digest": f"{sequence + 1:064x}",
        }

    participants = [
        ("validator_a", "validator", "alice"),
        ("validator_b", "validator", "bob"),
        ("node_a", "node", "carol"),
        ("node_b", "node", "dave"),
    ]
    for participant, role, owner in participants:
        fields = {
            "participant": participant,
            "owner": owner,
            "payout_account": owner,
            **proof_fields(),
        }
        if role == "validator":
            fields["bond_id"] = f"bond_{participant[-1]}"
        append(f"register_{role}", "registrar", **fields)
    for participant, _, _ in participants[:2]:
        append(
            "confirm_bond",
            "stake_verifier",
            participant=participant,
            bond_id=f"bond_{participant[-1]}",
            amount=100 + stream.bounded(101),
            **proof_fields(),
        )
    while height < manifest["parameters"]["epoch_length"]:
        append("advance_height", "clock", to_height=height + 1)
        height += 1
    for participant, _, _ in participants:
        append("activate", "lifecycle", participant=participant)

    for round_index in range(rounds):
        epoch = height // manifest["parameters"]["epoch_length"]
        for participant, role, _ in participants:
            plural = "validators" if role == "validator" else "nodes"
            kinds = sorted(manifest["contributions"][plural])
            contribution_kind = kinds[stream.bounded(len(kinds))]
            units = 1 + stream.bounded(20)
            verifier = manifest["contributions"][plural][contribution_kind]["verifier"]
            append(
                "attest_contribution",
                verifier,
                participant=participant,
                role=role,
                contribution_kind=contribution_kind,
                epoch=epoch,
                units=units,
                **proof_fields(),
            )

        jailed_index = stream.bounded(len(participants))
        jailed_participant, _, jailed_owner = participants[jailed_index]
        append(
            "jail",
            "enforcement",
            participant=jailed_participant,
            until_epoch=epoch + 1,
            **proof_fields(),
        )
        target_height = height + manifest["parameters"]["epoch_length"]
        while height < target_height:
            append("advance_height", "clock", to_height=height + 1)
            height += 1
        append(
            "request_recovery",
            jailed_owner,
            participant=jailed_participant,
        )
        append("recover", "lifecycle", participant=jailed_participant)

        for role in ("validator", "node"):
            budget = 25 + stream.bounded(76)
            append(
                "set_reward_budget",
                "reward",
                epoch=epoch,
                role=role,
                amount=budget,
            )
            for participant, participant_role, _ in participants:
                if participant_role == role:
                    append(
                        "settle_entitlement",
                        "reward",
                        epoch=epoch,
                        role=role,
                        participant=participant,
                    )
            append("finalize_budget", "reward", epoch=epoch, role=role)

    append("request_exit", "bob", participant="validator_b")
    append(
        "remove",
        "enforcement",
        participant="node_b",
        reason="study_terminal",
        **proof_fields(),
    )
    target_height = height + manifest["parameters"]["epoch_length"]
    while height < target_height:
        append("advance_height", "clock", to_height=height + 1)
        height += 1
    append("complete_exit", "bob", participant="validator_b")
    return manifest, events


def _manifest() -> dict:
    return {
        "schema": MANIFEST_SCHEMA,
        "research_only": True,
        "parameters": {
            "epoch_length": 3,
            "activation_delay_epochs": 1,
            "exit_delay_epochs": 1,
            "removal_hold_epochs": 2,
            "max_jail_epochs": 3,
            "max_participants": 8,
            "validator_minimum_bond": 100,
            "max_units_per_proof": 20,
            "max_units_per_participant_epoch": 40,
        },
        "authorities": {
            "clock": "clock",
            "registration": "registrar",
            "stake": "stake_verifier",
            "lifecycle": "lifecycle",
            "enforcement": "enforcement",
            "reward": "reward",
        },
        "contributions": {
            "validators": {
                "proposal": {"verifier": "consensus_verifier", "weight": 7},
                "vote": {"verifier": "consensus_verifier", "weight": 3},
            },
            "nodes": {
                "compute": {"verifier": "compute_verifier", "weight": 5},
                "storage": {"verifier": "storage_verifier", "weight": 2},
            },
        },
        "genesis": {"height": 0},
    }
