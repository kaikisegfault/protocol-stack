"""Shared threshold-authority simulator test inputs."""

from __future__ import annotations

import copy
from typing import Any
from pathlib import Path

from simulation.authority.scenario import generate_scenario, scenario_targets
from simulation.authority.validation import load_json

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "simulation" / "authority" / "fixtures"


def authority_manifest(seed: int = 0) -> dict[str, Any]:
    manifest, _ = generate_scenario(seed)
    return copy.deepcopy(manifest)


def authority_events(seed: int = 0) -> list[dict[str, Any]]:
    _, events = generate_scenario(seed)
    return copy.deepcopy(events)


def fixture(name: str) -> Any:
    return load_json(FIXTURES / name)


def targets(seed: int = 0) -> dict[str, dict[str, Any]]:
    return copy.deepcopy(scenario_targets(seed))


def economy_manifest() -> dict[str, Any]:
    return {
        "schema": "protocol-stack/native-economy-simulation-manifest/v1",
        "research_only": True,
        "parameters": {
            "supply_limit": 1000,
            "epoch_length": 10,
            "unbonding_epochs": 1,
            "fee_split_denominator": 1,
            "fee_reward_parts": 0,
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
        "participants": {"validators": {}, "nodes": {"node_a": "alice"}},
        "genesis": {
            "height": 0,
            "issued_supply": 1,
            "accounts": {"alice": 0},
            "fee_pool": 0,
            "treasury": 1,
            "reward_pool": 0,
            "penalty_pool": 0,
        },
    }


def participation_manifest() -> dict[str, Any]:
    return {
        "schema": "protocol-stack/participation-simulation-manifest/v1",
        "research_only": True,
        "parameters": {
            "epoch_length": 10,
            "activation_delay_epochs": 1,
            "exit_delay_epochs": 1,
            "removal_hold_epochs": 1,
            "max_jail_epochs": 2,
            "max_participants": 8,
            "validator_minimum_bond": 1,
            "max_units_per_proof": 10,
            "max_units_per_participant_epoch": 20,
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
                "vote": {"verifier": "vote_verifier", "weight": 1}
            },
            "nodes": {
                "storage": {"verifier": "storage_verifier", "weight": 1}
            },
        },
        "genesis": {"height": 0},
    }


def find_record(result: dict[str, Any], code: str) -> dict[str, Any]:
    return next(record for record in result["records"] if record["result"] == code)


def find_capability(
    result: dict[str, Any],
    module: str,
    capability: str,
) -> dict[str, Any]:
    return next(
        item
        for item in result["final_state"]["capabilities"]
        if item["module"] == module and item["capability"] == capability
    )
