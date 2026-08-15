#!/usr/bin/env python3
"""The version-five envelope, kind 11's corrected reading, and the eight messages."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import label_prefix
from simulation.economy_transition_v4 import messages as v4_messages
from simulation.economy_transition_v5 import contract as c
from simulation.economy_transition_v5 import envelope, messages, receipt, scenario

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def accepted(name: str) -> dict[str, str]:
    values: dict[str, str] = {}
    path = REPOSITORY_ROOT / "test-vectors" / name
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            key, _, value = stripped.partition("=")
            values[key] = value
    return values


class EnvelopeTest(unittest.TestCase):
    def test_every_kind_round_trips(self) -> None:
        for name, transaction in sorted(scenario.transactions().items()):
            with self.subTest(name):
                raw = envelope.signed_bytes(transaction, scenario.TRANSFER_SIGNATURE)
                self.assertEqual(
                    len(raw), envelope.expected_signed_length(transaction.kind)
                )
                decoded, signature = envelope.decode_signed(raw)
                self.assertEqual(decoded, transaction)
                self.assertEqual(signature, scenario.TRANSFER_SIGNATURE)

    def test_the_kind_one_identity_survives_a_fourth_revision(self) -> None:
        primitives = accepted("protocol-primitives-v1.txt")
        transfer = scenario.accepted_transfer()
        unsigned = envelope.unsigned_bytes(transfer)
        signed = envelope.signed_bytes(transfer, scenario.TRANSFER_SIGNATURE)
        self.assertEqual(unsigned.hex(), primitives["unsigned_tx"])
        self.assertEqual(signed.hex(), primitives["signed_tx"])
        self.assertEqual(envelope.transaction_id(signed), primitives["tx_id"])

    def test_a_relabelled_kind_changes_the_signing_message(self) -> None:
        original = scenario.transactions()["hub_add_address"]
        raw = bytearray(envelope.signed_bytes(original, scenario.TRANSFER_SIGNATURE))
        raw[6] = c.HUB_REMOVE_ADDRESS
        decoded, _ = envelope.decode_signed(bytes(raw))
        self.assertEqual(decoded.kind, c.HUB_REMOVE_ADDRESS)
        self.assertNotEqual(
            envelope.signing_message(envelope.unsigned_bytes(decoded)),
            envelope.signing_message(envelope.unsigned_bytes(original)),
        )

    def test_the_two_kinds_still_share_a_body_length(self) -> None:
        self.assertEqual(
            c.BODY_BYTES[c.HUB_ADD_ADDRESS], c.BODY_BYTES[c.HUB_REMOVE_ADDRESS]
        )


class AddAddressBodyTest(unittest.TestCase):
    """The one field whose meaning moved."""

    def setUp(self) -> None:
        self.transaction = scenario.recovery_transaction()

    def test_the_body_is_still_ninety_six_octets(self) -> None:
        body = envelope.body_bytes(c.HUB_ADD_ADDRESS, self.transaction.body)
        self.assertEqual(len(body), 96)
        self.assertEqual(len(body), c.BODY_BYTES[c.HUB_ADD_ADDRESS])

    def test_the_thirty_two_byte_field_is_the_identity(self) -> None:
        body = envelope.body_bytes(c.HUB_ADD_ADDRESS, self.transaction.body)
        self.assertEqual(body[0:32], self.transaction.body["hub_identity_hash"])
        self.assertEqual(body[32:96], self.transaction.body["hub_signature"])

    def test_decoding_names_the_identity(self) -> None:
        raw = envelope.signed_bytes(self.transaction, scenario.TRANSFER_SIGNATURE)
        decoded, _ = envelope.decode_signed(raw)
        self.assertIn("hub_identity_hash", decoded.body)
        self.assertNotIn("account_id", decoded.body)

    def test_a_body_of_the_wrong_shape_is_refused(self) -> None:
        for body in (
            {"hub_identity_hash": bytes(31), "hub_signature": bytes(64)},
            {"hub_identity_hash": bytes(32), "hub_signature": bytes(63)},
        ):
            with self.subTest(body):
                with self.assertRaises(envelope.MalformedTransaction):
                    envelope.body_bytes(c.HUB_ADD_ADDRESS, body)


class SenderDerivationTest(unittest.TestCase):
    """Version five is the first contract that must know who sent a transaction."""

    def test_the_account_is_the_accepted_version_one_derivation(self) -> None:
        import hashlib

        transaction = scenario.recovery_transaction()
        expected = hashlib.sha256(
            label_prefix("protocol-stack:v1:account")
            + b"\x01"
            + transaction.sender_public_key
        ).digest()
        self.assertEqual(envelope.sender_account_id(transaction), expected)

    def test_a_different_key_gives_a_different_account(self) -> None:
        self.assertNotEqual(
            envelope.sender_account_id(scenario.recovery_transaction()),
            envelope.sender_account_id(scenario.attacker_transaction()),
        )

    def test_a_public_key_of_the_wrong_width_is_refused(self) -> None:
        from dataclasses import replace

        transaction = replace(
            scenario.recovery_transaction(), sender_public_key=bytes(31)
        )
        with self.assertRaises(envelope.MalformedTransaction):
            envelope.sender_account_id(transaction)


class MessageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.chain = scenario.CHAIN_ID
        self.who = scenario.ALICE_IDENTITY
        self.expiry = scenario.VALID_UNTIL_HEIGHT

    def test_all_eight_labels_are_version_five(self) -> None:
        self.assertEqual(len(c.HUB_MESSAGE_LABELS), 8)
        for label in c.HUB_MESSAGE_LABELS:
            with self.subTest(label):
                self.assertTrue(label.startswith("protocol-stack:v5:"))

    def test_the_verifier_signs_exactly_one_message(self) -> None:
        self.assertEqual(c.VERIFIER_SIGNED_LABELS, (c.REGISTRATION_LABEL,))

    def test_every_message_binds_the_identity(self) -> None:
        built = (
            messages.activation_message(self.chain, self.who, 0, self.expiry),
            messages.mint_message(self.chain, self.who, 0, self.expiry),
            messages.mint_biometric_disable_message(
                self.chain, self.who, 0, self.expiry
            ),
            messages.address_add_message(
                self.chain, self.who, scenario.ALICE_SECOND_ADDRESS, self.expiry
            ),
        )
        for message in built:
            with self.subTest(message[:40].hex()):
                self.assertIn(self.who, message)
        self.assertEqual(len(set(built)), len(built))

    def test_the_fields_are_version_fours_and_only_the_label_moves(self) -> None:
        five = messages.mint_message(self.chain, self.who, 0, self.expiry)
        four = v4_messages.mint_message(self.chain, self.who, 0, self.expiry)
        self.assertNotEqual(five, four)
        self.assertEqual(
            five[len(label_prefix(c.MINT_LABEL)) :],
            four[len(label_prefix("protocol-stack:v4:seat-mint")) :],
        )

    def test_the_address_add_message_is_built_from_the_transaction(self) -> None:
        """The correction: no argument can name an identity the bytes do not carry."""
        transaction = scenario.recovery_transaction()
        derived = messages.address_add_message_for(transaction)
        self.assertEqual(
            derived,
            messages.address_add_message(
                transaction.chain_id,
                transaction.body["hub_identity_hash"],
                envelope.sender_account_id(transaction),
                transaction.valid_until_height,
            ),
        )

    def test_only_kind_eleven_carries_an_address_add_message(self) -> None:
        for name in ("hub_remove_address", "hub_register", "transfer"):
            with self.subTest(name):
                with self.assertRaises(envelope.MalformedTransaction):
                    messages.address_add_message_for(
                        scenario.transactions()[name]
                    )

    def test_every_message_has_a_reachable_identity_source(self) -> None:
        self.assertEqual(set(c.MESSAGE_IDENTITY_SOURCE), set(_message_names()))
        self.assertNotIn(c.NO_SOURCE, set(c.MESSAGE_IDENTITY_SOURCE.values()))
        self.assertEqual(c.VERSION_FOUR_ADDRESS_ADD_IDENTITY_SOURCE, c.NO_SOURCE)


def _message_names() -> tuple[str, ...]:
    return (
        "registration",
        "address_add",
        "address_remove",
        "purchase",
        "activation",
        "mint",
        "mint_biometric_disable",
        "manager",
    )


class ReceiptTest(unittest.TestCase):
    def test_the_version_field_is_five_and_the_layout_is_not(self) -> None:
        record = receipt.Receipt(
            transaction_id=bytes.fromhex("ab" * 32),
            kind=c.MINT_NODE,
            result_code=c.CODE_NUMBER["SUCCESS"],
            fee_charged=1_000,
            issued_atomic=1,
        )
        encoded = receipt.encode(record)
        self.assertEqual(len(encoded), 56)
        self.assertEqual(int.from_bytes(encoded[4:6], "big"), 5)
        self.assertEqual(receipt.decode(encoded), record)

    def test_a_version_four_receipt_is_refused(self) -> None:
        from simulation.economy_transition_v4 import receipt as v4_receipt

        record = v4_receipt.Receipt(
            transaction_id=bytes.fromhex("ab" * 32),
            kind=c.MINT_NODE,
            result_code=0,
            fee_charged=1_000,
            issued_atomic=1,
        )
        with self.assertRaises(receipt.InvalidReceipt):
            receipt.decode(v4_receipt.encode(record))


if __name__ == "__main__":
    unittest.main()
