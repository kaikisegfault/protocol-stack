#!/usr/bin/env python3
"""Rotation, containment, recovery, and adapter-negative tests."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from simulation.authority import AdapterError, build_authorized_events, simulate
from simulation.authority.domain import domain_digest
from tests.simulation.authority_common import (
    authority_events,
    authority_manifest,
    economy_manifest,
    find_capability,
    participation_manifest,
    targets,
)


class AuthorityLifecycleTest(unittest.TestCase):
    def test_rotation_requires_old_and_new_thresholds_then_explicit_activation(
        self,
    ) -> None:
        events = authority_events()
        rotations = [
            index
            for index, event in enumerate(events)
            if event["kind"] == "schedule_rotation"
            and event["target_module"] == "native_economy"
        ]
        first = simulate(authority_manifest(), events[: rotations[0] + 1])
        second = simulate(authority_manifest(), events[: rotations[1] + 1])
        self.assertEqual(first["records"][-1]["result"], "THRESHOLD")
        self.assertTrue(second["records"][-1]["accepted"])
        issuance = find_capability(second, "native_economy", "issuance")
        self.assertEqual(issuance["active_version"], 1)
        self.assertEqual(issuance["pending_rotation"]["version"], 2)

        too_early_index = next(
            index
            for index, event in enumerate(events)
            if event["kind"] == "activate_rotation"
            and event["target_module"] == "native_economy"
        )
        too_early = simulate(authority_manifest(), events[: too_early_index + 1])
        self.assertEqual(too_early["records"][-1]["result"], "TOO_EARLY")

        complete = simulate(authority_manifest(), events)
        issuance = find_capability(complete, "native_economy", "issuance")
        self.assertEqual(
            [version["source"] for version in issuance["versions"]],
            ["genesis", "rotation", "recovery"],
        )
        self.assertEqual(issuance["versions"][0]["retired_epoch"], 2)
        self.assertEqual(issuance["versions"][1]["retired_epoch"], 4)

    def test_containment_cancels_pending_rotation_and_recovery_replaces_set(
        self,
    ) -> None:
        events = authority_events()
        pause_index = next(
            index
            for index, event in enumerate(events)
            if event["kind"] == "pause_capability"
            and event["action_digest"] != "f" * 64
        )
        paused = simulate(authority_manifest(), events[: pause_index + 1])
        registration = find_capability(paused, "participation", "registration")
        self.assertTrue(registration["paused"])
        self.assertIsNone(registration["pending_rotation"])
        self.assertEqual(registration["active_version"], 1)

        complete = simulate(authority_manifest(), events)
        registration = find_capability(complete, "participation", "registration")
        self.assertFalse(registration["paused"])
        self.assertEqual(registration["active_version"], 2)
        self.assertEqual(registration["versions"][1]["source"], "recovery")
        self.assertEqual(complete["metrics"]["recoveries"], 2)

    def test_revocation_never_lowers_threshold_and_pauses_until_recovery(self) -> None:
        result = simulate(authority_manifest(), authority_events())
        issuance = find_capability(result, "native_economy", "issuance")
        revoked = issuance["versions"][1]
        replacement = issuance["versions"][2]
        self.assertEqual(revoked["threshold"], 2)
        self.assertEqual(revoked["members"], ["issuer_d", "issuer_e", "issuer_f"])
        self.assertEqual(revoked["revoked_members"], ["issuer_d"])
        self.assertEqual(replacement["threshold"], 2)
        self.assertEqual(replacement["members"], ["issuer_g", "issuer_h", "issuer_i"])

    def test_adapter_rejects_mutation_wrong_actor_and_owner_events(self) -> None:
        manifest = authority_manifest()
        result = simulate(manifest, authority_events())
        target_values = targets()

        mutated = copy.deepcopy(target_values["result_issue"])
        mutated["amount"] += 1
        self._assert_adapter_code(
            "ACTION_DIGEST_MISMATCH",
            result,
            manifest,
            economy_manifest(),
            "native_economy",
            [("result_issue", mutated)],
        )
        wrong_actor = copy.deepcopy(target_values["result_issue"])
        wrong_actor["actor"] = "outsider"
        self._assert_adapter_code(
            "ACTOR_MISMATCH",
            result,
            manifest,
            economy_manifest(),
            "native_economy",
            [("result_issue", wrong_actor)],
        )
        owner_event = {
            "id": "owner_transfer",
            "height": 0,
            "kind": "transfer",
            "actor": "alice",
            "source": "alice",
            "destination": "bob",
            "amount": 1,
        }
        self._assert_adapter_code(
            "TARGET_INVALID",
            result,
            manifest,
            economy_manifest(),
            "native_economy",
            [("result_issue", owner_event)],
        )

    def test_adapter_is_all_or_nothing_and_validates_complete_result(self) -> None:
        manifest = authority_manifest()
        result = simulate(manifest, authority_events())
        target = targets()["result_issue"]
        self._assert_adapter_code(
            "RESULT_NOT_FOUND",
            result,
            manifest,
            economy_manifest(),
            "native_economy",
            [("result_issue", target), ("result_issue", target)],
        )
        self._assert_adapter_code(
            "TARGET_INVALID",
            result,
            manifest,
            economy_manifest(),
            "native_economy",
            [
                ("result_issue", target),
                ("result_rotated_issue", target),
            ],
        )
        tampered = copy.deepcopy(result)
        tampered["trace_digest"] = "0" * 64
        self._assert_adapter_code(
            "MANIFEST_MISMATCH",
            tampered,
            manifest,
            economy_manifest(),
            "native_economy",
            [("result_issue", target)],
        )
        wrong_manifest = authority_manifest()
        wrong_manifest["chain_id"] = "other_chain"
        self._assert_adapter_code(
            "MANIFEST_MISMATCH",
            result,
            wrong_manifest,
            economy_manifest(),
            "native_economy",
            [("result_issue", target)],
        )

    def test_adapter_reports_capability_and_set_mismatch(self) -> None:
        manifest = authority_manifest()
        result = simulate(manifest, authority_events())
        target = targets()["result_issue"]

        capability = copy.deepcopy(result)
        item = next(
            value
            for value in capability["final_state"]["authorization_results"]
            if value["result_id"] == "result_issue"
        )
        item["capability"] = "reward"
        item["set_id"] = "reward_set"
        self._reseal(capability)
        self._assert_adapter_code(
            "CAPABILITY_MISMATCH",
            capability,
            manifest,
            economy_manifest(),
            "native_economy",
            [("result_issue", target)],
        )

        wrong_set = copy.deepcopy(result)
        item = next(
            value
            for value in wrong_set["final_state"]["authorization_results"]
            if value["result_id"] == "result_issue"
        )
        item["set_id"] = "reward_set"
        self._reseal(wrong_set)
        self._assert_adapter_code(
            "SET_MISMATCH",
            wrong_set,
            manifest,
            economy_manifest(),
            "native_economy",
            [("result_issue", target)],
        )

    def _assert_adapter_code(
        self,
        code: str,
        result: dict,
        manifest: dict,
        target_manifest: dict,
        module: str,
        pairs: list,
    ) -> None:
        with self.assertRaises(AdapterError) as caught:
            build_authorized_events(
                result,
                manifest,
                target_manifest,
                module=module,
                pairs=pairs,
            )
        self.assertEqual(caught.exception.code, code)

    def _reseal(self, result: dict) -> None:
        state_digest = domain_digest(
            "protocol-stack:authority:state-v1",
            result["final_state"],
        )
        result["records"][-1]["state_digest_after"] = state_digest
        result["trace_digest"] = domain_digest(
            "protocol-stack:authority:trace-v1",
            result["records"],
        )


if __name__ == "__main__":
    unittest.main()
