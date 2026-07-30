#!/usr/bin/env python3
"""Fixed participation lifecycle, entitlement, and funding tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.native_economy import simulate as simulate_economy
from simulation.participation import build_funding_events, simulate
from simulation.participation.domain import canonical_json
from tests.simulation.participation_common import economy_manifest, fixture


class ParticipationModelTest(unittest.TestCase):
    def test_fixed_fixture_covers_lifecycle_and_entitlements(self) -> None:
        manifest, events = fixture()
        result = simulate(manifest, events)
        self.assertEqual(len(result["records"]), 34)
        self.assertTrue(all(record["accepted"] for record in result["records"]))
        state = result["final_state"]
        self.assertEqual(state["height"], 6)
        self.assertEqual(
            {
                key: value["phase"]
                for key, value in state["participants"].items()
            },
            {
                "node_a": "active",
                "node_b": "removed",
                "validator_a": "active",
                "validator_b": "exited",
            },
        )
        self.assertEqual(
            state["participants"]["validator_b"]["unbond_ready_epoch"],
            3,
        )
        self.assertEqual(
            [(item["role"], item["participant"], item["amount"])
             for item in state["entitlements"]],
            [
                ("node", "node_a", 3),
                ("node", "node_b", 1),
                ("validator", "validator_a", 7),
                ("validator", "validator_b", 2),
            ],
        )
        self.assertEqual(
            [(item["role"], item["allocated"], item["remainder"])
             for item in state["budgets"]],
            [("node", 4, 1), ("validator", 9, 1)],
        )
        self.assertEqual(result["metrics"]["accepted_events"]["jail"], 1)
        self.assertEqual(result["metrics"]["accepted_events"]["recover"], 1)
        self.assertEqual(result["metrics"]["accepted_events"]["remove"], 1)

    def test_repeated_replay_is_byte_identical(self) -> None:
        manifest, events = fixture()
        first = simulate(manifest, events)
        second = simulate(manifest, events)
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertEqual(
            first["trace_digest"],
            "22c2b495457a13d7a83837ceeb98893b6df148b9ab99761763744dcbbb07b7e3",
        )

    def test_finalized_entitlements_fund_and_pull_exact_claims(self) -> None:
        manifest, events = fixture()
        participation = simulate(manifest, events)
        economy = economy_manifest()
        funding = []
        for role in ("validator", "node"):
            funding.extend(
                build_funding_events(
                    participation,
                    manifest,
                    economy,
                    epoch=1,
                    role=role,
                    height=0,
                )
            )
        self.assertEqual(
            [(item["role"], item["participant"], item["amount"]) for item in funding],
            [
                ("validator", "validator_a", 7),
                ("validator", "validator_b", 2),
                ("node", "node_a", 3),
                ("node", "node_b", 1),
            ],
        )
        claims = [
            {
                "id": f"claim_{item['participant']}",
                "height": 0,
                "kind": "claim_reward",
                "actor": economy["participants"][f"{item['role']}s"][
                    item["participant"]
                ],
                "role": item["role"],
                "participant": item["participant"],
                "amount": item["amount"],
            }
            for item in funding
        ]
        result = simulate_economy(economy, funding + claims)
        self.assertTrue(all(record["accepted"] for record in result["records"]))
        self.assertEqual(
            result["final_state"]["accounts"],
            {"alice": 7, "bob": 2, "carol": 3, "dave": 1},
        )
        self.assertEqual(result["final_state"]["reward_pool"], 2)
        self.assertEqual(result["final_state"]["validator_claims"], {})
        self.assertEqual(result["final_state"]["node_claims"], {})


if __name__ == "__main__":
    unittest.main()
