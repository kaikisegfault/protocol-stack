#!/usr/bin/env python3
"""Validation, boundary, precedence, and atomic-failure tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.native_economy import simulate
from simulation.native_economy.domain import MAX_U64
from simulation.native_economy.validation import InputError, load_json, parse_events
from tests.simulation.common import base_manifest, changed, event


class NativeEconomyErrorTest(unittest.TestCase):
    def assert_failure(self, events: list[dict], expected: str, index: int = -1) -> dict:
        result = simulate(base_manifest(), events)
        record = result["records"][index]
        self.assertFalse(record["accepted"])
        self.assertEqual(record["result"], expected)
        self.assertEqual(record["journal"], [])
        self.assertEqual(
            record["state_digest_before"],
            record["state_digest_after"],
        )
        self.assertEqual(record["height_before"], record["height_after"])
        return result

    def test_common_and_value_flow_failures(self) -> None:
        cases = [
            (
                [event("issue", "issuer", height=1, amount=1)],
                "WRONG_HEIGHT",
            ),
            (
                [event("issue", "alice", amount=1)],
                "UNAUTHORIZED",
            ),
            (
                [event("issue", "issuer", amount=0)],
                "ZERO_AMOUNT",
            ),
            (
                [
                    event(
                        "transfer",
                        "carol",
                        source="carol",
                        destination="alice",
                        amount=1,
                    )
                ],
                "NOT_FOUND",
            ),
            (
                [
                    event(
                        "transfer",
                        "alice",
                        source="alice",
                        destination="alice",
                        amount=1,
                    )
                ],
                "INVALID_TARGET",
            ),
            (
                [
                    event(
                        "transfer",
                        "alice",
                        source="alice",
                        destination="bob",
                        amount=401,
                    )
                ],
                "INSUFFICIENT_FUNDS",
            ),
            (
                [event("issue", "issuer", amount=9001)],
                "SUPPLY_LIMIT",
            ),
        ]
        for events, expected in cases:
            with self.subTest(expected=expected):
                self.assert_failure(events, expected)

    def test_replay_and_failed_identifier_reuse(self) -> None:
        first = event("issue", "issuer", id="shared_id", amount=1)
        replay = event("issue", "issuer", id="shared_id", amount=2)
        result = self.assert_failure([first, replay], "REPLAY")
        self.assertEqual(result["final_state"]["issued_supply"], 1001)

        denied = event("issue", "alice", id="retry_id", amount=2)
        retry = event("issue", "issuer", id="retry_id", amount=2)
        result = simulate(base_manifest(), [denied, retry])
        self.assertEqual(
            [record["result"] for record in result["records"]],
            ["UNAUTHORIZED", "OK"],
        )
        self.assertEqual(result["final_state"]["issued_supply"], 1002)

    def test_existing_and_time_locked_records(self) -> None:
        opening = event(
            "open_escrow",
            "alice",
            id="open_1",
            escrow_id="escrow_1",
            escrow_kind="general",
            source_kind="account",
            source="alice",
            beneficiary="bob",
            unlock_epoch=1,
            amount=10,
        )
        duplicate = event(
            "open_escrow",
            "alice",
            id="open_2",
            escrow_id="escrow_1",
            escrow_kind="general",
            source_kind="account",
            source="alice",
            beneficiary="bob",
            unlock_epoch=1,
            amount=10,
        )
        self.assert_failure([opening, duplicate], "ALREADY_EXISTS")
        early = event(
            "release_escrow",
            "escrow",
            id="release_1",
            escrow_id="escrow_1",
        )
        self.assert_failure([opening, early], "TOO_EARLY")

    def test_checked_epoch_and_height_overflow(self) -> None:
        manifest = base_manifest()
        manifest["parameters"]["supply_limit"] = MAX_U64
        manifest["parameters"]["epoch_length"] = 1
        manifest["genesis"] = {
            "height": MAX_U64,
            "issued_supply": 10,
            "accounts": {"alice": 10},
            "fee_pool": 0,
            "treasury": 0,
            "reward_pool": 0,
            "penalty_pool": 0,
        }
        bond = event(
            "bond",
            "alice",
            id="bond_1",
            height=MAX_U64,
            bond_id="bond_1",
            owner="alice",
            validator="validator_a",
            amount=5,
        )
        unbond = event(
            "begin_unbond",
            "alice",
            id="unbond_1",
            height=MAX_U64,
            bond_id="bond_1",
            unbonding_id="unbonding_1",
            amount=5,
        )
        result = simulate(manifest, [bond, unbond])
        self.assertEqual(result["records"][1]["result"], "OVERFLOW")
        self.assertEqual(
            result["records"][1]["state_digest_before"],
            result["records"][1]["state_digest_after"],
        )

        advance = event(
            "advance_height",
            "clock",
            height=MAX_U64,
            to_height=MAX_U64,
        )
        result = simulate(manifest, [advance])
        self.assertEqual(result["records"][0]["result"], "OVERFLOW")

    def test_checked_fee_share_intermediate(self) -> None:
        manifest = base_manifest()
        denominator = 1 << 63
        amount = denominator - 1
        manifest["parameters"] = {
            **manifest["parameters"],
            "supply_limit": MAX_U64,
            "fee_split_denominator": denominator,
            "fee_reward_parts": denominator,
        }
        manifest["genesis"] = {
            "height": 0,
            "issued_supply": MAX_U64,
            "accounts": {},
            "fee_pool": amount,
            "treasury": MAX_U64 - amount,
            "reward_pool": 0,
            "penalty_pool": 0,
        }
        allocation = event(
            "allocate_fees",
            "fee_allocator",
            amount=amount,
        )
        result = simulate(manifest, [allocation])
        self.assertEqual(result["records"][0]["result"], "OVERFLOW")

    def test_event_shape_and_number_validation(self) -> None:
        valid = event("issue", "issuer", amount=1)
        malformed = [
            {**valid, "amount": True},
            {**valid, "amount": 1.5},
            {**valid, "unknown": 1},
            {**valid, "kind": "unknown"},
            {**valid, "id": "UPPER"},
        ]
        for value in malformed:
            with self.subTest(value=value):
                with self.assertRaises(InputError):
                    parse_events([value])

    def test_manifest_validation(self) -> None:
        manifest = base_manifest()
        cases = []
        value = changed(manifest)
        value["research_only"] = False
        cases.append(value)
        value = changed(manifest)
        value["genesis"]["issued_supply"] += 1
        cases.append(value)
        value = changed(manifest)
        value["participants"]["nodes"]["validator_a"] = "bob"
        cases.append(value)
        value = changed(manifest)
        value["parameters"]["fee_reward_parts"] = 11
        cases.append(value)
        value = changed(manifest)
        value["parameters"]["epoch_length"] = 0
        cases.append(value)
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(InputError):
                    simulate(value, [])

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"amount": 1, "amount": 2}', encoding="utf-8")
            with self.assertRaisesRegex(InputError, "duplicate JSON key"):
                load_json(path)

    def test_result_precedence_checks_height_before_replay(self) -> None:
        accepted = event("issue", "issuer", id="same", amount=1)
        wrong_height = event(
            "issue",
            "issuer",
            id="same",
            height=1,
            amount=1,
        )
        result = simulate(base_manifest(), [accepted, wrong_height])
        self.assertEqual(result["records"][1]["result"], "WRONG_HEIGHT")

    def test_result_contains_no_floating_point(self) -> None:
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
