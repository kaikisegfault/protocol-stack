#!/usr/bin/env python3
"""The result-code space, its total mapping from the economy model, and receipts."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition import contract as c
from simulation.economy_transition import receipt
from simulation.founder_economy_v3 import contract as model


class ResultCodeSpaceTest(unittest.TestCase):
    def test_the_space_is_flat_and_contiguous(self) -> None:
        """One code means one thing regardless of the kind that produced it."""
        self.assertEqual(sorted(c.RESULT_CODES), list(range(len(c.RESULT_CODES))))
        self.assertEqual(len(set(c.RESULT_CODES.values())), len(c.RESULT_CODES))

    def test_the_version_one_codes_keep_their_numbers_and_meanings(self) -> None:
        version_one = {
            0: "SUCCESS",
            1: "ZERO_AMOUNT",
            2: "FEE_LIMIT_TOO_LOW",
            3: "EXPIRED",
            4: "SENDER_NOT_FOUND",
            5: "NONCE_EXHAUSTED",
            6: "NONCE_MISMATCH",
            7: "DEBIT_OVERFLOW",
            8: "INSUFFICIENT_BALANCE",
        }
        for number, name in version_one.items():
            self.assertEqual(c.RESULT_CODES[number], name)
        self.assertEqual(c.INHERITED_RESULT_CODES, tuple(version_one))

    def test_the_added_codes_extend_contiguously_from_nine(self) -> None:
        self.assertEqual(c.ADDED_RESULT_CODES[0], 9)
        self.assertEqual(
            len(c.INHERITED_RESULT_CODES) + len(c.ADDED_RESULT_CODES),
            len(c.RESULT_CODES),
        )


class ModelMappingTest(unittest.TestCase):
    """The mapping is checked against the model's own declared set, not a copy."""

    def setUp(self) -> None:
        self.declared = set(model.RESULT_CODES)
        self.carried = set(c.CARRIED_MODEL_CODES)
        self.guards = set(c.GUARD_MODEL_CODES)
        self.unrepresentable = set(c.UNREPRESENTABLE_MODEL_CODES)

    def test_the_three_dispositions_partition_the_models_codes(self) -> None:
        self.assertEqual(
            self.carried | self.guards | self.unrepresentable, self.declared
        )
        self.assertEqual(self.carried & self.guards, set())
        self.assertEqual(self.carried & self.unrepresentable, set())
        self.assertEqual(self.guards & self.unrepresentable, set())

    def test_the_partition_sizes_are_the_recorded_ones(self) -> None:
        self.assertEqual(len(self.declared), 24)
        self.assertEqual(len(self.carried), 11)
        self.assertEqual(len(self.guards), 2)
        self.assertEqual(len(self.unrepresentable), 11)

    def test_every_carried_code_has_a_numbered_target(self) -> None:
        for source, target in c.CARRIED_MODEL_CODES.items():
            with self.subTest(source):
                self.assertIn(target, c.CODE_NUMBER)

    def test_the_guards_are_the_models_own_guards(self) -> None:
        self.assertEqual(set(c.GUARD_MODEL_CODES), set(model.GUARD_RESULT_CODES))

    def test_a_guard_never_becomes_a_receipt_code(self) -> None:
        """`ledger-transition-v1` already makes these invalidate the block."""
        for name in c.GUARD_MODEL_CODES:
            self.assertNotIn(name, c.CODE_NUMBER)

    def test_every_unrepresentable_code_records_why(self) -> None:
        for name, reason in c.UNREPRESENTABLE_MODEL_CODES.items():
            with self.subTest(name):
                self.assertTrue(reason.strip())
                self.assertNotIn(name, c.CODE_NUMBER)

    def test_each_removed_code_is_removed_for_a_stated_structural_reason(self) -> None:
        """Eleven codes, in four groups, each with its input gone for one reason."""
        record_conditions = {
            "MISSING_UPTIME_RECORD",
            "INVALID_UPTIME_RECORD",
            "INCONSISTENT_UPTIME_RECORD",
            "SEAT_NOT_IN_SCOPE",
            "INCOMPLETE_UPTIME_RECORD",
        }
        window_conditions = {
            "WINDOW_BEFORE_ISSUANCE",
            "WINDOW_AFTER_ISSUANCE",
            "WINDOW_NOT_FOR_CYCLE",
        }
        height_conditions = {"HEIGHT_RANGE", "HEIGHT_NOT_MONOTONIC"}
        mint_conditions = {"PERMISSION_NOT_FOUND"}
        self.assertEqual(
            self.unrepresentable,
            record_conditions | window_conditions | height_conditions | mint_conditions,
        )
        self.assertEqual(
            [len(record_conditions), len(window_conditions), len(height_conditions), len(mint_conditions)],
            [5, 3, 2, 1],
        )

    def test_the_new_codes_are_conditions_the_model_cannot_have(self) -> None:
        """A model with no signer, no purchase, and no take-everything mint."""
        new = {
            name
            for number, name in c.RESULT_CODES.items()
            if number >= 9 and name not in c.CARRIED_MODEL_CODES.values()
        }
        self.assertEqual(new, {"UNAUTHORIZED", "SEAT_NOT_PURCHASED", "NOTHING_TO_MINT"})
        for name in new:
            with self.subTest(name):
                self.assertNotIn(name, model.RESULT_CODES)

    def test_every_code_the_model_added_in_version_three_is_accounted_for(self) -> None:
        for name in model.ADDED_RESULT_CODES:
            with self.subTest(name):
                self.assertIn(
                    name, self.carried | self.guards | self.unrepresentable
                )


class ReceiptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.accepted = receipt.Receipt(
            transaction_id=bytes.fromhex("ab" * 32),
            kind=c.MINT_NODE,
            result_code=c.CODE_NUMBER["SUCCESS"],
            fee_charged=1_000,
            issued_atomic=57_430_000_000,
        )

    def test_the_layout_is_fifty_six_bytes_and_round_trips(self) -> None:
        encoded = receipt.encode(self.accepted)
        self.assertEqual(len(encoded), 56)
        self.assertEqual(receipt.decode(encoded), self.accepted)

    def test_the_version_is_two_rather_than_a_widened_version_one(self) -> None:
        encoded = receipt.encode(self.accepted)
        self.assertEqual(encoded[0:4], b"PSRC")
        self.assertEqual(int.from_bytes(encoded[4:6], "big"), 2)
        self.assertNotEqual(len(encoded), 47)

    def test_a_failed_receipt_charges_no_fee_and_issues_nothing(self) -> None:
        failed = c.CODE_NUMBER["CHANNEL_CAP"]
        for fee, issued in ((1_000, 0), (0, 1)):
            with self.subTest(fee=fee, issued=issued):
                with self.assertRaises(receipt.InvalidReceipt):
                    receipt.encode(
                        receipt.Receipt(
                            self.accepted.transaction_id,
                            c.MINT_NODE,
                            failed,
                            fee,
                            issued,
                        )
                    )

    def test_a_non_issuing_kind_cannot_report_issuance(self) -> None:
        for kind in receipt.NON_ISSUING_KINDS:
            with self.subTest(kind):
                with self.assertRaises(receipt.InvalidReceipt):
                    receipt.encode(
                        receipt.Receipt(
                            self.accepted.transaction_id, kind, 0, 1_000, 1
                        )
                    )

    def test_the_issuing_kinds_are_the_two_mints_and_direct_issue(self) -> None:
        """Until a permission is minted its units do not exist."""
        issuing = set(c.TRANSACTION_KINDS) - receipt.NON_ISSUING_KINDS
        self.assertEqual(issuing, {c.MINT_NODE, c.MINT_REFERRAL, c.DIRECT_ISSUE})

    def test_an_unknown_kind_or_code_is_refused(self) -> None:
        with self.assertRaises(receipt.InvalidReceipt):
            receipt.encode(
                receipt.Receipt(self.accepted.transaction_id, 7, 0, 1_000, 0)
            )
        with self.assertRaises(receipt.InvalidReceipt):
            receipt.encode(
                receipt.Receipt(self.accepted.transaction_id, 1, 200, 0, 0)
            )

    def test_a_truncated_or_mislabelled_receipt_is_refused(self) -> None:
        encoded = receipt.encode(self.accepted)
        with self.assertRaises(receipt.InvalidReceipt):
            receipt.decode(encoded[:-1])
        with self.assertRaises(receipt.InvalidReceipt):
            receipt.decode(b"XSRC" + encoded[4:])
        with self.assertRaises(receipt.InvalidReceipt):
            receipt.decode(encoded[:4] + b"\x00\x01" + encoded[6:])


if __name__ == "__main__":
    unittest.main()
