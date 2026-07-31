#!/usr/bin/env python3
"""Strict validation, precedence, boundaries, and atomic failure tests."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from simulation.authority import simulate
from simulation.authority.domain import MAX_U64
from simulation.authority.validation import InputError, load_json, parse_events
from tests.simulation.authority_common import authority_events, authority_manifest


class AuthorityErrorsTest(unittest.TestCase):
    def test_manifest_validation_rejects_invalid_shapes_and_bounds(self) -> None:
        cases = []
        value = authority_manifest()
        value["research_only"] = False
        cases.append(value)
        value = authority_manifest()
        value["parameters"]["epoch_length"] = True
        cases.append(value)
        value = authority_manifest()
        value["parameters"]["min_rotation_delay_epochs"] = 5
        value["parameters"]["max_rotation_delay_epochs"] = 4
        cases.append(value)
        value = authority_manifest()
        value["control_sets"]["containment"]["members"].reverse()
        cases.append(value)
        value = authority_manifest()
        value["control_sets"]["containment"]["threshold"] = 4
        cases.append(value)
        value = authority_manifest()
        value["control_sets"]["recovery"]["set_id"] = "containment_set"
        cases.append(value)
        value = authority_manifest()
        value["capabilities"]["authority"] = value["capabilities"].pop(
            "native_economy"
        )
        cases.append(value)
        value = authority_manifest()
        value["unexpected"] = 1
        cases.append(value)
        for manifest in cases:
            with self.subTest(manifest=manifest):
                with self.assertRaises(InputError):
                    simulate(manifest, [])

    def test_duplicate_json_keys_and_numeric_forms_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text('{"schema":1,"schema":2}', encoding="utf-8")
            with self.assertRaisesRegex(InputError, "duplicate JSON key"):
                load_json(path)
            path.write_text('{"value":1.0}', encoding="utf-8")
            with self.assertRaisesRegex(InputError, "floating-point"):
                load_json(path)
            path.write_text('{"value":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(InputError, "non-finite"):
                load_json(path)

    def test_event_decoder_rejects_unknown_or_malformed_fields(self) -> None:
        event = copy.deepcopy(authority_events()[0])
        cases = []
        value = copy.deepcopy(event)
        value["unknown"] = 1
        cases.append(value)
        value = copy.deepcopy(event)
        value["height"] = False
        cases.append(value)
        value = copy.deepcopy(event)
        value["action_digest"] = "A" * 64
        cases.append(value)
        value = copy.deepcopy(event)
        value["capability"] = "bad//scope"
        cases.append(value)
        rotation = next(
            item
            for item in authority_events()
            if item["kind"] == "schedule_rotation" and len(item["approvals"]) == 4
        )
        value = copy.deepcopy(rotation)
        value["next_members"].reverse()
        cases.append(value)
        for candidate in cases:
            with self.subTest(candidate=candidate):
                with self.assertRaises(InputError):
                    parse_events([candidate])

    def test_ordinary_failure_precedence_and_boundaries(self) -> None:
        manifest = authority_manifest()
        base = copy.deepcopy(authority_events()[0])
        base["approvals"] = []
        self.assertEqual(simulate(manifest, [base])["records"][0]["result"], "LIMIT")

        base = copy.deepcopy(authority_events()[0])
        base["valid_from_epoch"] = 2
        base["deadline_epoch"] = 1
        self.assertEqual(
            simulate(manifest, [base])["records"][0]["result"],
            "INVALID_TARGET",
        )

        base = copy.deepcopy(authority_events()[0])
        base["height"] = 1
        self.assertEqual(
            simulate(manifest, [base])["records"][0]["result"],
            "WRONG_HEIGHT",
        )

        clock = {
            "id": "clock_event",
            "height": 0,
            "kind": "advance_height",
            "actor": "outsider",
            "to_height": 1,
        }
        self.assertEqual(
            simulate(manifest, [clock])["records"][0]["result"],
            "UNAUTHORIZED",
        )

        overflow_manifest = authority_manifest()
        overflow_manifest["genesis"]["height"] = MAX_U64
        overflow = {
            "id": "clock_event",
            "height": MAX_U64,
            "kind": "advance_height",
            "actor": "clock",
            "to_height": MAX_U64,
        }
        self.assertEqual(
            simulate(overflow_manifest, [overflow])["records"][0]["result"],
            "OVERFLOW",
        )

    def test_proof_replay_precedes_duplicate_member_and_threshold(self) -> None:
        event = copy.deepcopy(authority_events()[0])
        first = copy.deepcopy(event["approvals"][0])
        event["approvals"] = [
            first,
            {
                "member": "issuer_b",
                "proof_id": first["proof_id"],
                "evidence_digest": "b" * 64,
            },
        ]
        record = simulate(authority_manifest(), [event])["records"][0]
        self.assertEqual(record["result"], "PROOF_REPLAY")
        self.assertEqual(record["state_digest_before"], record["state_digest_after"])

    def test_version_and_member_limits_fail_before_digest_use(self) -> None:
        rotation = next(
            copy.deepcopy(item)
            for item in authority_events()
            if item["kind"] == "schedule_rotation" and len(item["approvals"]) == 4
        )
        manifest = authority_manifest()
        manifest["parameters"]["max_versions_per_capability"] = 1
        self.assertEqual(
            simulate(manifest, [rotation])["records"][0]["result"],
            "LIMIT",
        )
        rotation["next_threshold"] = 0
        manifest["parameters"]["max_versions_per_capability"] = 8
        self.assertEqual(
            simulate(manifest, [rotation])["records"][0]["result"],
            "INVALID_TARGET",
        )

    def test_every_rejected_scenario_event_is_failure_atomic(self) -> None:
        result = simulate(authority_manifest(), authority_events())
        rejected = [record for record in result["records"] if not record["accepted"]]
        self.assertGreater(len(rejected), 10)
        for record in rejected:
            self.assertEqual(
                record["state_digest_before"],
                record["state_digest_after"],
                msg=json.dumps(record, sort_keys=True),
            )
            self.assertIsNone(record["accepted_result_id"])
            self.assertIsNone(record["accepted_action_id"])
            self.assertEqual(record["accepted_proof_ids"], [])


if __name__ == "__main__":
    unittest.main()
