#!/usr/bin/env python3
"""Fixed authority trace, canonical result, and downstream adapter tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from simulation.authority import build_authorized_events, simulate
from simulation.native_economy import simulate as simulate_economy
from simulation.participation import simulate as simulate_participation
from tests.simulation.authority_common import (
    authority_events,
    authority_manifest,
    economy_manifest,
    find_capability,
    fixture,
    participation_manifest,
    targets,
)


class AuthorityModelTest(unittest.TestCase):
    def test_fixed_adversarial_trace(self) -> None:
        manifest = fixture("research-manifest-v1.json")
        events = fixture("research-events-v1.json")
        self.assertEqual(manifest, authority_manifest())
        self.assertEqual(events, authority_events())
        result = simulate(manifest, events)
        self.assertEqual(
            result["trace_digest"],
            "26f96d2fccdcb7b9acdcad0b83f81a564aa99196eb4042285ddcf38dba6588a1",
        )
        self.assertEqual(len(result["records"]), 69)
        self.assertEqual(sum(record["accepted"] for record in result["records"]), 50)
        self.assertEqual(len(result["final_state"]["accepted_proof_ids"]), 26)
        self.assertEqual(len(result["final_state"]["authorization_results"]), 3)
        self.assertEqual(
            set(result["metrics"]["rejected_results"]),
            {
                "ACTION_REPLAY",
                "DIGEST_MISMATCH",
                "DOMAIN_MISMATCH",
                "DUPLICATE_MEMBER",
                "EXPIRED",
                "NOT_FOUND",
                "PAUSED",
                "PROOF_REPLAY",
                "REPLAY",
                "RESULT_REPLAY",
                "THRESHOLD",
                "TOO_EARLY",
                "UNAUTHORIZED_MEMBER",
                "WRONG_SET",
            },
        )
        issuance = find_capability(result, "native_economy", "issuance")
        registration = find_capability(result, "participation", "registration")
        self.assertEqual(issuance["active_version"], 3)
        self.assertEqual(issuance["versions"][1]["revoked_members"], ["issuer_d"])
        self.assertEqual(registration["active_version"], 2)
        self.assertFalse(issuance["paused"])
        self.assertFalse(registration["paused"])

    def test_replay_is_byte_deterministic(self) -> None:
        first = simulate(authority_manifest(7), authority_events(7))
        second = simulate(authority_manifest(7), authority_events(7))
        self.assertEqual(first, second)
        self.assertNotEqual(
            first["trace_digest"],
            simulate(authority_manifest(8), authority_events(8))["trace_digest"],
        )

    def test_native_and_participation_adapters_execute_exact_events(self) -> None:
        manifest = authority_manifest()
        result = simulate(manifest, authority_events())
        target_values = targets()
        economy_events = build_authorized_events(
            result,
            manifest,
            economy_manifest(),
            module="native_economy",
            pairs=[("result_issue", target_values["result_issue"])],
        )
        participation_events = build_authorized_events(
            result,
            manifest,
            participation_manifest(),
            module="participation",
            pairs=[("result_register", target_values["result_register"])],
        )
        self.assertEqual(economy_events, [target_values["result_issue"]])
        self.assertEqual(
            participation_events,
            [target_values["result_register"]],
        )
        economy = simulate_economy(economy_manifest(), economy_events)
        participation = simulate_participation(
            participation_manifest(),
            participation_events,
        )
        self.assertTrue(economy["records"][0]["accepted"])
        self.assertTrue(participation["records"][0]["accepted"])
        self.assertGreater(economy["final_state"]["treasury"], 1)
        self.assertIn("node_a", participation["final_state"]["participants"])

    def test_results_sort_approvals_and_bind_independent_identities(self) -> None:
        result = simulate(authority_manifest(), authority_events())
        issue = next(
            item
            for item in result["final_state"]["authorization_results"]
            if item["result_id"] == "result_issue"
        )
        self.assertEqual(issue["action_id"], "action_issue")
        self.assertEqual(
            [item["member"] for item in issue["approvals"]],
            ["issuer_a", "issuer_b"],
        )
        self.assertNotEqual(issue["result_id"], issue["action_id"])
        self.assertEqual(issue["authorized_epoch"], 0)


if __name__ == "__main__":
    unittest.main()
