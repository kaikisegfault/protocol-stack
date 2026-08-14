#!/usr/bin/env python3
"""The version-three result-code space, the receipt, and the model mapping."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition import contract as v2
from simulation.economy_transition_v3 import contract as c
from simulation.economy_transition_v3 import receipt
from simulation.founder_economy_v3 import contract as economy


class ResultCodeSpaceTest(unittest.TestCase):
    def test_the_space_is_contiguous_from_zero(self) -> None:
        self.assertEqual(sorted(c.RESULT_CODES), list(range(len(c.RESULT_CODES))))
        self.assertEqual(len(c.RESULT_CODES), 24)

    def test_every_version_two_code_keeps_its_number_and_meaning(self) -> None:
        """A version-three chain is a different chain, so nothing forces this.

        It is kept because a code that names the same condition should not have
        to be relearned by a reader, a wallet, or an operator's runbook.
        """
        for number, name in v2.RESULT_CODES.items():
            with self.subTest(number):
                self.assertEqual(c.RESULT_CODES[number], name)

    def test_exactly_three_codes_are_new(self) -> None:
        added = set(c.RESULT_CODES) - set(v2.RESULT_CODES)
        self.assertEqual(added, {21, 22, 23})
        self.assertEqual(
            [c.RESULT_CODES[number] for number in sorted(added)],
            ["NOT_HUB_VERIFIED", "BIOMETRIC_REQUIRED", "MANAGER_LIMIT"],
        )

    def test_the_admission_codes_are_version_ones(self) -> None:
        self.assertEqual(c.ADMISSION_CODES, v2.ADMISSION_CODES)

    def test_each_new_code_names_a_condition_version_two_could_not_have(self) -> None:
        self.assertNotIn("NOT_HUB_VERIFIED", v2.RESULT_CODES.values())
        self.assertNotIn(c.HUB_REGISTRATION_ENTRY, v2.ENTRY_KINDS)
        self.assertNotIn(c.SEAT_MANAGER_ENTRY, v2.ENTRY_KINDS)
        self.assertNotIn(c.MINT_NODE_VERIFIED, v2.TRANSACTION_KINDS)


class ModelMappingTest(unittest.TestCase):
    """The mapping onto the economy model's codes is total and unchanged."""

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

    def test_the_partition_is_version_twos(self) -> None:
        """The model is unchanged between transition versions two and three."""
        self.assertEqual(c.CARRIED_MODEL_CODES, v2.CARRIED_MODEL_CODES)
        self.assertEqual(c.GUARD_MODEL_CODES, v2.GUARD_MODEL_CODES)
        self.assertEqual(
            set(c.UNREPRESENTABLE_MODEL_CODES), set(v2.UNREPRESENTABLE_MODEL_CODES)
        )

    def test_every_carried_target_exists(self) -> None:
        for target in c.CARRIED_MODEL_CODES.values():
            with self.subTest(target):
                self.assertIn(target, c.CODE_NUMBER)

    def test_a_guard_never_acquires_a_receipt_code(self) -> None:
        """A checked-arithmetic violation invalidates the block, not the transaction."""
        self.assertEqual(self.guards & set(c.CODE_NUMBER), set())

    def test_every_unrepresentable_code_states_why(self) -> None:
        for name in self.unrepresentable:
            with self.subTest(name):
                self.assertTrue(c.UNREPRESENTABLE_MODEL_CODES[name].strip())

    def test_six_codes_have_no_model_counterpart(self) -> None:
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
        self.assertEqual(c.RECEIPT_VERSION, 3)
        self.assertNotEqual(c.RECEIPT_VERSION, v2.RECEIPT_VERSION)

    def test_the_receipt_round_trips(self) -> None:
        encoded = receipt.encode(self.accepted)
        self.assertEqual(len(encoded), 56)
        self.assertEqual(receipt.decode(encoded), self.accepted)

    def test_a_version_two_receipt_is_refused(self) -> None:
        """A reader must be able to tell an unknown contract from an invalid one."""
        encoded = bytearray(receipt.encode(self.accepted))
        encoded[4:6] = (2).to_bytes(2, "big")
        with self.assertRaises(receipt.InvalidReceipt):
            receipt.decode(bytes(encoded))

    def test_the_impossible_combinations_are_refused(self) -> None:
        failed = c.CODE_NUMBER["CHANNEL_CAP"]
        cases = {
            "unknown_kind": receipt.Receipt(self.accepted.transaction_id, 11, 0, 0, 0),
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

    def test_the_non_issuing_kinds_are_the_six_that_write_no_value(self) -> None:
        self.assertEqual(
            receipt.NON_ISSUING_KINDS,
            frozenset(
                {
                    c.TRANSFER,
                    c.PURCHASE_SEAT,
                    c.ACTIVATE_SEAT,
                    c.SET_MINT_BIOMETRIC,
                    c.ADD_MANAGER,
                    c.HUB_VERIFY,
                }
            ),
        )
        for kind in receipt.NON_ISSUING_KINDS:
            with self.subTest(kind):
                with self.assertRaises(receipt.InvalidReceipt):
                    receipt.encode(
                        receipt.Receipt(self.accepted.transaction_id, kind, 0, 0, 1)
                    )

    def test_the_issuing_kinds_may_report_issuance(self) -> None:
        for kind in (c.MINT_NODE, c.MINT_NODE_VERIFIED, c.MINT_REFERRAL, c.DIRECT_ISSUE):
            with self.subTest(kind):
                receipt.encode(
                    receipt.Receipt(self.accepted.transaction_id, kind, 0, 0, 1)
                )


class VersionTwoIsUntouchedTest(unittest.TestCase):
    """Version two is accepted evidence and version three must not disturb it."""

    def test_the_version_two_contract_still_has_six_kinds(self) -> None:
        self.assertEqual(len(v2.TRANSACTION_KINDS), 6)
        self.assertEqual(len(v2.ENTRY_KINDS), 8)
        self.assertEqual(len(v2.RESULT_CODES), 21)

    def test_the_version_two_labels_are_unchanged(self) -> None:
        self.assertEqual(v2.CHAIN_ID_LABEL, "protocol-stack:v2:chain-id")
        self.assertEqual(v2.STATE_ROOT_LABEL, "protocol-stack:v2:state-root")
        self.assertEqual(v2.ECONOMY_TREE_PREFIX, "protocol-stack:v2:economy")

    def test_the_two_versions_agree_on_what_they_share(self) -> None:
        self.assertEqual(c.HEADER_BYTES, v2.HEADER_BYTES)
        self.assertEqual(c.TRAILER_BYTES, v2.TRAILER_BYTES)
        self.assertEqual(c.SIGN_LABEL, v2.SIGN_LABEL)
        self.assertEqual(c.TX_ID_LABEL, v2.TX_ID_LABEL)
        self.assertEqual(c.MANIFEST_DIGEST_HEX, v2.MANIFEST_DIGEST_HEX)
        self.assertEqual(c.BASE_PERMISSION_LEGS, v2.BASE_PERMISSION_LEGS)
        self.assertEqual(c.REFERRAL_LEG_ATOMIC, v2.REFERRAL_LEG_ATOMIC)

    def test_the_two_versions_differ_where_the_founder_directed(self) -> None:
        self.assertNotEqual(c.CHAIN_ID_LABEL, v2.CHAIN_ID_LABEL)
        self.assertNotEqual(c.STATE_ROOT_LABEL, v2.STATE_ROOT_LABEL)
        self.assertNotEqual(c.ECONOMY_TREE_PREFIX, v2.ECONOMY_TREE_PREFIX)
        self.assertNotEqual(
            c.ENTRY_VALUE_BYTES[c.SEAT_ENTRY], v2.ENTRY_VALUE_BYTES[v2.SEAT_ENTRY]
        )
        self.assertNotEqual(c.ENROLLMENT_LABEL, v2.ENROLLMENT_LABEL)


if __name__ == "__main__":
    unittest.main()
