"""Synthetic research manifests for one stress configuration."""

from __future__ import annotations

from typing import Any

from .design import Configuration

CAPABILITY_SETS = {
    ("participation", "clock"): "p_clock_set",
    ("participation", "registration"): "p_registration_set",
    ("participation", "stake"): "p_stake_set",
    ("participation", "lifecycle"): "p_lifecycle_set",
    ("participation", "enforcement"): "p_enforcement_set",
    ("participation", "reward"): "p_reward_set",
    ("participation", "contribution/validator/proposal"): "p_proposal_set",
    ("participation", "contribution/validator/vote"): "p_vote_set",
    ("participation", "contribution/node/compute"): "p_compute_set",
    ("participation", "contribution/node/storage"): "p_storage_set",
    ("native_economy", "clock"): "e_clock_set",
    ("native_economy", "issuance"): "e_issuance_set",
    ("native_economy", "fee_allocation"): "e_fee_set",
    ("native_economy", "treasury"): "e_treasury_set",
    ("native_economy", "reward"): "e_reward_set",
    ("native_economy", "penalty"): "e_penalty_set",
}


def participation_manifest(config: Configuration) -> dict[str, Any]:
    values = config.values
    return {
        "schema": "protocol-stack/participation-simulation-manifest/v1",
        "research_only": True,
        "parameters": {
            "epoch_length": 1,
            "activation_delay_epochs": values["activation_delay_epochs"],
            "exit_delay_epochs": values["exit_unbond_delay_epochs"],
            "removal_hold_epochs": values["exit_unbond_delay_epochs"],
            "max_jail_epochs": 4,
            "max_participants": 8,
            "validator_minimum_bond": values["validator_minimum_bond"],
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
                "proposal": {
                    "verifier": "vote_verifier",
                    "weight": values["validator_weight"],
                },
                "vote": {
                    "verifier": "vote_verifier",
                    "weight": 1,
                },
            },
            "nodes": {
                "compute": {
                    "verifier": "storage_verifier",
                    "weight": values["node_weight"],
                },
                "storage": {
                    "verifier": "storage_verifier",
                    "weight": 1,
                },
            },
        },
        "genesis": {"height": 0},
    }


def economy_manifest(config: Configuration) -> dict[str, Any]:
    return {
        "schema": "protocol-stack/native-economy-simulation-manifest/v1",
        "research_only": True,
        "parameters": {
            "supply_limit": 13_000,
            "epoch_length": 1,
            "unbonding_epochs": config.values["exit_unbond_delay_epochs"],
            "fee_split_denominator": 10,
            "fee_reward_parts": config.values["fee_reward_parts"],
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
            "validators": {"validator_a": "alice", "validator_b": "bob"},
            "nodes": {"node_a": "carol", "node_b": "dave"},
        },
        "genesis": {
            "height": 0,
            "issued_supply": 8_500,
            "accounts": {
                "alice": 2_000,
                "bob": 2_000,
                "carol": 2_000,
                "dave": 2_000,
            },
            "fee_pool": 0,
            "treasury": 500,
            "reward_pool": 0,
            "penalty_pool": 0,
        },
    }


def authority_manifest(config: Configuration) -> dict[str, Any]:
    threshold = config.values["authority_threshold"]
    delay = config.values["authority_delay_epochs"]

    def authority_set(set_id: str, members: list[str]) -> dict[str, Any]:
        return {
            "set_id": set_id,
            "version": 1,
            "members": members,
            "threshold": threshold,
        }

    capabilities: dict[str, dict[str, Any]] = {}
    for (module, capability), set_id in CAPABILITY_SETS.items():
        capabilities.setdefault(module, {})[capability] = authority_set(
            set_id,
            ["operator_a", "operator_b", "operator_c"],
        )
    return {
        "schema": "protocol-stack/authority-simulation-manifest/v1",
        "research_only": True,
        "chain_id": "stress_chain",
        "parameters": {
            "epoch_length": 1,
            "min_rotation_delay_epochs": delay,
            "max_rotation_delay_epochs": delay,
            "recovery_delay_epochs": delay,
            "max_action_lifetime_epochs": 64,
            "max_capabilities": 16,
            "max_members_per_set": 3,
            "max_approvals_per_result": 8,
            "max_versions_per_capability": 4,
        },
        "clock": "authority_clock",
        "control_sets": {
            "containment": authority_set(
                "containment_set",
                ["contain_a", "contain_b", "contain_c"],
            ),
            "recovery": authority_set(
                "recovery_set",
                ["recover_a", "recover_b", "recover_c"],
            ),
        },
        "capabilities": capabilities,
        "genesis": {"height": 0},
    }
