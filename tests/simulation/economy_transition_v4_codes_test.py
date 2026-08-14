#!/usr/bin/env python3
"""The version-four result-code space, the receipt, and the model mapping."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v3 import contract as v3
from simulation.economy_transition_v4 import contract as c
from simulation.economy_transition_v4 import receipt
from simulation.founder_economy_v3 import contract as economy


class ResultCodeSpaceTest(unittest.TestCase):
    def test_the_space_is_contiguous_from_zero(self) -> None:
        self.assertEqual(sorted(c.RESULT_CODES), list(range(len(c.RESULT_CODES))))
        self.assertEqual(len(c.RESULT_CODES), 26)

    def test_every_version_three_code_keeps_its_number_and_meaning(self) -> None:
        for number, name in v3.RESULT_CODES.items():
            with self.subTest(number):
                self.assertEqual(c.RESULT_CODES[number], name)

    def test_exactly_two_codes_are_new(self) -> None:
        added = set(c.RESULT_CODES) - set(v3.RESULT_CODES)
        self.assertEqual(added, {24, 25})
        self.assertEqual(
            [c.RESULT_CODES[n] for n in sorted(added)], ["SEAT_LIMIT", "ADDRESS_LIMIT"]
        )

    def test_the_admission_codes_are_version_ones(self) -> None:
        self.assertEqual(c.ADMISSION_CODES, v3.ADMISSION_CODES)

    def test_each_new_code_names_a_condition_version_three_could_not_have(self) -> None:
        """`SEAT_LIMIT` needs one identity per person; `ADDRESS_LIMIT` needs a set.

        Version three has a HUB registry, but it is an attestation keyed by
        account with no public key, no address set, and no seat count, so
        neither condition is expressible in it.
        """
        self.assertNotIn("hub_identity", v3.ENTRY_KINDS.values())
        self.assertNotIn("hub_address", v3.ENTRY_KINDS.values())
        self.assertIn("hub_identity", c.ENTRY_KINDS.values())
        self.assertIn("hub_address", c.ENTRY_KINDS.values())
        self.assertNotIn("hub_add_address", v3.TRANSACTION_KINDS.values())
        self.assertNotIn("hub_remove_address", v3.TRANSACTION_KINDS.values())


class ModelMappingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.declared = set(economy.RESULT_CODES)
        self.carried = set(c.CARRIED_MODEL_CODES)
        self.guards = set(c.GUARD_MODEL_CODES)
        self.unrepresentable = set(c.UNREPRESENTABLE_MODEL_CODES)

    def test_the_three_sets_partition_the_models_declared_set(self) -> None:
        self.assertEqual(
            self.carried | self.guards | self.unrepresentable, self.declared
        )
        self.assertEqual(self.carried & self.guards, set())
        self.assertEqual(self.carried & self.unrepresentable, set())
        self.assertEqual(self.guards & self.unrepresentable, set())

    def test_the_partition_is_version_threes(self) -> None:
        """The model is unchanged, so the disposition is unchanged with it."""
        self.assertEqual(c.CARRIED_MODEL_CODES, v3.CARRIED_MODEL_CODES)
        self.assertEqual(c.GUARD_MODEL_CODES, v3.GUARD_MODEL_CODES)
        self.assertEqual(
            set(c.UNREPRESENTABLE_MODEL_CODES), set(v3.UNREPRESENTABLE_MODEL_CODES)
        )

    def test_a_guard_never_acquires_a_receipt_code(self) -> None:
        self.assertEqual(self.guards & set(c.CODE_NUMBER), set())

    def test_eight_codes_have_no_model_counterpart(self) -> None:
        beyond = {
            name
            for number, name in c.RESULT_CODES.items()
            if number >= 9 and name not in c.CARRIED_MODEL_CODES.values()
        }
        self.assertEqual(
            beyond,
            {
                "UNAUTHORIZED",
                "SEAT_NOT_PURCHASED",
                "NOTHING_TO_MINT",
                "NOT_HUB_VERIFIED",
                "BIOMETRIC_REQUIRED",
                "MANAGER_LIMIT",
                "SEAT_LIMIT",
                "ADDRESS_LIMIT",
            },
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

    def test_the_layout_is_version_twos_and_the_version_is_not(self) -> None:
        self.assertEqual(receipt.RECEIPT_BYTES, 56)
        self.assertEqual(c.RECEIPT_VERSION, 4)
        self.assertNotEqual(c.RECEIPT_VERSION, v3.RECEIPT_VERSION)

    def test_the_receipt_round_trips(self) -> None:
        encoded = receipt.encode(self.accepted)
        self.assertEqual(len(encoded), 56)
        self.assertEqual(receipt.decode(encoded), self.accepted)

    def test_a_version_three_receipt_is_refused(self) -> None:
        encoded = bytearray(receipt.encode(self.accepted))
        encoded[4:6] = (3).to_bytes(2, "big")
        with self.assertRaises(receipt.InvalidReceipt):
            receipt.decode(bytes(encoded))

    def test_the_impossible_combinations_are_refused(self) -> None:
        failed = c.CODE_NUMBER["CHANNEL_CAP"]
        cases = {
            "unknown_kind": receipt.Receipt(self.accepted.transaction_id, 13, 0, 0, 0),
            "unknown_code": receipt.Receipt(self.accepted.transaction_id, 1, 200, 0, 0),
            "failed_with_fee": receipt.Receipt(
                self.accepted.transaction_id, 1, failed, 1_000, 0
            ),
            "failed_with_issuance": receipt.Receipt(
                self.accepted.transaction_id, 4, failed, 0, 1
            ),
        }
        for name, candidate in cases.items():
            with self.subTest(name):
                with self.assertRaises(receipt.InvalidReceipt):
                    receipt.encode(candidate)

    def test_no_hub_transaction_issues_value(self) -> None:
        for kind in (c.HUB_REGISTER, c.HUB_ADD_ADDRESS, c.HUB_REMOVE_ADDRESS):
            with self.subTest(kind):
                self.assertIn(kind, receipt.NON_ISSUING_KINDS)
                with self.assertRaises(receipt.InvalidReceipt):
                    receipt.encode(
                        receipt.Receipt(self.accepted.transaction_id, kind, 0, 0, 1)
                    )

    def test_the_issuing_kinds_may_report_issuance(self) -> None:
        for kind in (c.MINT_NODE, c.MINT_NODE_VERIFIED, c.MINT_REFERRAL, c.DIRECT_ISSUE):
            with self.subTest(kind):
                receipt.encode(receipt.Receipt(self.accepted.transaction_id, kind, 0, 0, 1))


class VersionThreeIsUntouchedTest(unittest.TestCase):
    def test_the_version_three_contract_still_has_ten_kinds(self) -> None:
        self.assertEqual(len(v3.TRANSACTION_KINDS), 10)
        self.assertEqual(len(v3.ENTRY_KINDS), 11)
        self.assertEqual(len(v3.RESULT_CODES), 24)

    def test_the_version_three_labels_are_unchanged(self) -> None:
        self.assertEqual(v3.CHAIN_ID_LABEL, "protocol-stack:v3:chain-id")
        self.assertEqual(v3.STATE_ROOT_LABEL, "protocol-stack:v3:state-root")
        self.assertEqual(v3.ECONOMY_TREE_PREFIX, "protocol-stack:v3:economy")

    def test_the_two_versions_agree_on_what_they_share(self) -> None:
        self.assertEqual(c.HEADER_BYTES, v3.HEADER_BYTES)
        self.assertEqual(c.TRAILER_BYTES, v3.TRAILER_BYTES)
        self.assertEqual(c.SIGN_LABEL, v3.SIGN_LABEL)
        self.assertEqual(c.TX_ID_LABEL, v3.TX_ID_LABEL)
        self.assertEqual(c.MANIFEST_DIGEST_HEX, v3.MANIFEST_DIGEST_HEX)
        self.assertEqual(c.BASE_PERMISSION_LEGS, v3.BASE_PERMISSION_LEGS)
        self.assertEqual(c.MINT_ACCUMULATION_CAP, v3.MINT_ACCUMULATION_CAP)
        self.assertEqual(c.MAX_SEAT_MANAGERS, v3.MAX_SEAT_MANAGERS)

    def test_the_two_versions_differ_where_the_founder_directed(self) -> None:
        self.assertNotEqual(c.CHAIN_ID_LABEL, v3.CHAIN_ID_LABEL)
        self.assertNotEqual(c.STATE_ROOT_LABEL, v3.STATE_ROOT_LABEL)
        self.assertNotEqual(c.ECONOMY_TREE_PREFIX, v3.ECONOMY_TREE_PREFIX)
        self.assertLess(
            c.BODY_BYTES[c.PURCHASE_SEAT], v3.BODY_BYTES[v3.PURCHASE_SEAT]
        )
        self.assertNotIn("protocol-stack:v3:seat-enrollment", c.HUB_MESSAGE_LABELS)

    def test_the_verifier_reach_narrowed(self) -> None:
        """Version three gates five actions; version four gates one."""
        self.assertEqual(len(c.VERIFIER_SIGNED_LABELS), 1)
        self.assertEqual(len(v3.VERIFIER_MESSAGE_LABELS), 6)


if __name__ == "__main__":
    unittest.main()
