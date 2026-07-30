#!/usr/bin/env python3
"""Participation validation, boundary, precedence, and atomic-failure tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.native_economy import simulate as simulate_economy
from simulation.participation import AdapterError, build_funding_events, simulate
from simulation.participation.domain import MAX_U64
from simulation.participation.validation import InputError, load_json, parse_events
from tests.simulation.participation_common import (
    ParticipationTestCase,
    active_setup,
    base_manifest,
    changed,
    economy_manifest,
    event,
    fixture,
    proof,
)


class ParticipationErrorTest(ParticipationTestCase):

    def test_contribution_authority_caps_and_overflow(self) -> None:
        wrong = event(
            "attest_contribution",
            "alice",
            id="wrong_verifier",
            height=2,
            participant="validator_a",
            role="validator",
            contribution_kind="vote",
            epoch=1,
            units=1,
            **proof(40),
        )
        self.assert_failure([*active_setup(), wrong], "UNAUTHORIZED")
        too_large = {**wrong, "id": "too_large", "actor": "consensus_verifier",
                     "units": 11, **proof(41)}
        self.assert_failure([*active_setup(), too_large], "LIMIT")
        accepted_one = {**too_large, "id": "accepted_1", "units": 10, **proof(42)}
        accepted_two = {**too_large, "id": "accepted_2", "units": 10, **proof(43)}
        over_total = {**too_large, "id": "over_total", "units": 1, **proof(44)}
        self.assert_failure(
            [*active_setup(), accepted_one, accepted_two, over_total],
            "LIMIT",
        )

        manifest = base_manifest()
        manifest["contributions"]["validators"]["vote"]["weight"] = MAX_U64
        manifest["parameters"]["max_units_per_proof"] = 2
        overflow = {**wrong, "id": "overflow", "actor": "consensus_verifier",
                    "units": 2, **proof(45)}
        self.assert_failure(
            [*active_setup(), overflow],
            "OVERFLOW",
            manifest=manifest,
        )

    def test_budget_finalization_and_settlement_order(self) -> None:
        manifest, events = fixture()
        reordered = changed(events)
        reordered[23], reordered[24] = reordered[24], reordered[23]
        first = simulate(manifest, events)
        second = simulate(manifest, reordered)
        self.assertEqual(first["final_state"], second["final_state"])

        partial = events[:24]
        finalize = event(
            "finalize_budget",
            "reward",
            id="early_finalize",
            height=4,
            epoch=1,
            role="validator",
        )
        self.assert_failure([*partial, finalize], "TOO_EARLY")

    def test_zero_entitlements_are_finalized_without_funding_events(self) -> None:
        _, fixture_events = fixture()
        events = fixture_events[:16]
        events.extend(fixture_events[17:19])
        events.extend(
            [
                event(
                    "set_reward_budget",
                    "reward",
                    id="tiny_budget",
                    height=4,
                    epoch=1,
                    role="validator",
                    amount=1,
                ),
                event(
                    "settle_entitlement",
                    "reward",
                    id="tiny_a",
                    height=4,
                    epoch=1,
                    role="validator",
                    participant="validator_a",
                ),
                event(
                    "settle_entitlement",
                    "reward",
                    id="tiny_b",
                    height=4,
                    epoch=1,
                    role="validator",
                    participant="validator_b",
                ),
                event(
                    "finalize_budget",
                    "reward",
                    id="tiny_final",
                    height=4,
                    epoch=1,
                    role="validator",
                ),
            ]
        )
        result = simulate(base_manifest(), events)
        self.assertEqual(
            [item["amount"] for item in result["final_state"]["entitlements"]],
            [0, 0],
        )
        self.assertEqual(result["final_state"]["budgets"][0]["remainder"], 1)
        self.assertEqual(
            build_funding_events(
                result,
                base_manifest(),
                economy_manifest(1),
                epoch=1,
                role="validator",
                height=0,
            ),
            [],
        )

    def test_adapter_rejects_mismatch_and_economy_can_refuse_funding(self) -> None:
        manifest, events = fixture()
        result = simulate(manifest, events)
        mismatch = economy_manifest()
        mismatch["participants"]["validators"]["validator_a"] = "mallory"
        with self.assertRaisesRegex(AdapterError, "MANIFEST_MISMATCH"):
            build_funding_events(
                result,
                manifest,
                mismatch,
                epoch=1,
                role="validator",
                height=0,
            )

        underfunded = economy_manifest(8)
        funding = build_funding_events(
            result,
            manifest,
            underfunded,
            epoch=1,
            role="validator",
            height=0,
        )
        economic_result = simulate_economy(underfunded, funding)
        self.assertEqual(
            [record["result"] for record in economic_result["records"]],
            ["OK", "INSUFFICIENT_FUNDS"],
        )

    def test_event_and_manifest_validation(self) -> None:
        malformed_event = event(
            "register_node",
            "registrar",
            participant="node_x",
            owner="alice",
            payout_account="alice",
            **proof(50),
        )
        cases = [
            {**malformed_event, "height": True},
            {**malformed_event, "height": 1.5},
            {**malformed_event, "unknown": 1},
            {**malformed_event, "id": "UPPER"},
            {**malformed_event, "evidence_digest": "0" * 63},
        ]
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(InputError):
                    parse_events([value])
        manifest = base_manifest()
        invalid_manifests = []
        value = changed(manifest)
        value["research_only"] = False
        invalid_manifests.append(value)
        value = changed(manifest)
        value["parameters"]["epoch_length"] = 0
        invalid_manifests.append(value)
        value = changed(manifest)
        value["parameters"]["max_units_per_proof"] = 21
        invalid_manifests.append(value)
        value = changed(manifest)
        value["contributions"]["nodes"] = {}
        invalid_manifests.append(value)
        for value in invalid_manifests:
            with self.subTest(value=value):
                with self.assertRaises(InputError):
                    simulate(value, [])

    def test_duplicate_json_key_and_floating_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"height": 1, "height": 2}', encoding="utf-8")
            with self.assertRaisesRegex(InputError, "duplicate JSON key"):
                load_json(path)
        result = simulate(base_manifest(), [])

        def walk(value) -> None:
            self.assertIsNot(type(value), float)
            if isinstance(value, dict):
                for item in value.values():
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(result)
        json.dumps(result, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
