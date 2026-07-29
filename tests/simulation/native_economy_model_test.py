#!/usr/bin/env python3
"""Fixed native-economy flow and metric tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.native_economy import simulate
from simulation.native_economy.domain import canonical_json
from tests.simulation.common import fixture


class NativeEconomyModelTest(unittest.TestCase):
    def test_fixed_fixture_covers_every_bucket(self) -> None:
        manifest, events = fixture()
        result = simulate(manifest, events)

        self.assertEqual(len(result["records"]), 23)
        self.assertTrue(all(record["accepted"] for record in result["records"]))
        for record in result["records"]:
            self.assertEqual(
                sum(entry["delta"] for entry in record["journal"]),
                0,
            )

        state = result["final_state"]
        self.assertEqual(state["height"], 2)
        self.assertEqual(state["issued_supply"], 1050)
        self.assertEqual(
            state["accounts"],
            {"alice": 314, "bob": 390, "carol": 55},
        )
        self.assertEqual(state["treasury"], 211)
        self.assertEqual(state["reward_pool"], 30)
        self.assertEqual(
            state["bonds"],
            {
                "bond_1": {
                    "owner": "alice",
                    "validator": "validator_a",
                    "amount": 50,
                }
            },
        )
        self.assertEqual(state["escrows"], {})
        self.assertEqual(state["unbondings"], {})
        self.assertEqual(state["validator_claims"], {})
        self.assertEqual(state["node_claims"], {})
        self.assertEqual(state["penalty_pool"], 0)

        inventory = result["metrics"]["inventory"]
        self.assertEqual(sum(inventory[key] for key in (
            "accounts",
            "fee_pool",
            "treasury",
            "escrows",
            "bonded",
            "unbonding",
            "reward_pool",
            "validator_claims",
            "node_claims",
            "penalty_pool",
        )), inventory["issued_supply"])
        self.assertEqual(inventory["issuance_capacity"], 8950)

        flows = result["metrics"]["flows"]
        self.assertEqual(flows["issuance"], 50)
        self.assertEqual(flows["fees_charged"], 11)
        self.assertEqual(flows["fees_allocated"], 11)
        self.assertEqual(flows["fee_to_rewards"], 3)
        self.assertEqual(flows["fee_to_treasury"], 8)
        self.assertEqual(flows["treasury_grants"], 25)
        self.assertEqual(flows["reward_funding"], 97)
        self.assertEqual(flows["escrow_opened"], 70)
        self.assertEqual(flows["escrow_released"], 70)
        self.assertEqual(flows["stake_bonded"], 100)
        self.assertEqual(flows["unbonding_begun"], 40)
        self.assertEqual(flows["unbonding_completed"], 35)
        self.assertEqual(flows["validator_rewards_allocated"], 40)
        self.assertEqual(flows["node_rewards_allocated"], 30)
        self.assertEqual(flows["validator_rewards_claimed"], 40)
        self.assertEqual(flows["node_rewards_claimed"], 30)
        self.assertEqual(flows["penalties_assessed"], 15)
        self.assertEqual(flows["penalties_routed"], 15)

    def test_repeated_replay_is_byte_identical(self) -> None:
        manifest, events = fixture()
        first = simulate(manifest, events)
        second = simulate(manifest, events)
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertEqual(
            first["trace_digest"],
            "41e956350c63970fa40378703c1b497801d28d095b756338efac1a1b558a1098",
        )


if __name__ == "__main__":
    unittest.main()
