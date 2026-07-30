"""Shared participation-v1 simulator test inputs."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from simulation.participation import simulate
from simulation.participation.validation import load_json

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "simulation" / "participation" / "fixtures"


def fixture() -> tuple[dict, list[dict]]:
    return (
        load_json(FIXTURES / "research-manifest-v1.json"),
        load_json(FIXTURES / "research-events-v1.json"),
    )


def base_manifest() -> dict:
    manifest, _ = fixture()
    return manifest


def active_setup() -> list[dict]:
    _, events = fixture()
    return events[:12]


def event(kind: str, actor: str, **fields) -> dict:
    return {
        "id": fields.pop("id", "test_event"),
        "height": fields.pop("height", 0),
        "kind": kind,
        "actor": actor,
        **fields,
    }


def proof(number: int) -> dict[str, str]:
    return {
        "proof_id": f"test_proof_{number}",
        "evidence_digest": f"{number:064x}",
    }


def changed(value):
    return copy.deepcopy(value)


class ParticipationTestCase(unittest.TestCase):
    def assert_failure(
        self,
        events: list[dict],
        expected: str,
        *,
        manifest: dict | None = None,
        index: int = -1,
    ) -> dict:
        result = simulate(base_manifest() if manifest is None else manifest, events)
        record = result["records"][index]
        self.assertFalse(record["accepted"])
        self.assertEqual(record["result"], expected)
        self.assertIsNone(record["accepted_proof_id"])
        self.assertEqual(record["state_digest_before"], record["state_digest_after"])
        self.assertEqual(record["height_before"], record["height_after"])
        return result


def economy_manifest(reward_pool: int = 15) -> dict:
    return {
        "schema": "protocol-stack/native-economy-simulation-manifest/v1",
        "research_only": True,
        "parameters": {
            "supply_limit": reward_pool,
            "epoch_length": 1,
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
        "participants": {
            "validators": {"validator_a": "alice", "validator_b": "bob"},
            "nodes": {"node_a": "carol", "node_b": "dave"},
        },
        "genesis": {
            "height": 0,
            "issued_supply": reward_pool,
            "accounts": {"alice": 0, "bob": 0, "carol": 0, "dave": 0},
            "fee_pool": 0,
            "treasury": 0,
            "reward_pool": reward_pool,
            "penalty_pool": 0,
        },
    }
