#!/usr/bin/env python3
"""The version-four envelope, its twelve bodies, admission, and HUB messages."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v4 import contract as c
from simulation.economy_transition_v4 import envelope, messages, scenario

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ACCEPTED_PRIMITIVES = REPOSITORY_ROOT / "test-vectors" / "protocol-primitives-v1.txt"


def accepted_value(key: str) -> str:
    for line in ACCEPTED_PRIMITIVES.read_text(encoding="ascii").splitlines():
        name, separator, value = line.partition("=")
        if separator and name == key:
            return value
    raise AssertionError(f"{key} is not recorded in the accepted vectors")


class VersionOneIdentityTest(unittest.TestCase):
    """Three contract revisions have now left the kind-1 bytes untouched."""

    def setUp(self) -> None:
        self.transfer = scenario.accepted_transfer()

    def test_the_unsigned_kind_one_bytes_are_the_accepted_transfer(self) -> None:
        derived = envelope.unsigned_bytes(self.transfer)
        self.assertEqual(len(derived), 136)
        self.assertEqual(derived.hex(), accepted_value("unsigned_tx"))

    def test_the_signed_kind_one_bytes_are_the_accepted_transfer(self) -> None:
        derived = envelope.signed_bytes(self.transfer, scenario.TRANSFER_SIGNATURE)
        self.assertEqual(len(derived), 200)
        self.assertEqual(derived.hex(), accepted_value("signed_tx"))

    def test_the_transaction_id_is_the_accepted_one(self) -> None:
        signed = envelope.signed_bytes(self.transfer, scenario.TRANSFER_SIGNATURE)
        self.assertEqual(envelope.transaction_id(signed), accepted_value("tx_id"))

    def test_every_earlier_encoder_agrees_on_the_kind_one_bytes(self) -> None:
        """Four accepted contracts must encode one accepted transfer identically."""
        from simulation.economy_transition import envelope as v2e
        from simulation.economy_transition import scenario as v2s
        from simulation.economy_transition_v3 import envelope as v3e
        from simulation.economy_transition_v3 import scenario as v3s

        derived = envelope.unsigned_bytes(self.transfer)
        self.assertEqual(derived, v2e.unsigned_bytes(v2s.accepted_transfer()))
        self.assertEqual(derived, v3e.unsigned_bytes(v3s.accepted_transfer()))

    def test_the_labels_are_not_re_versioned(self) -> None:
        self.assertEqual(c.ENVELOPE_SCHEMA_VERSION, 1)
        self.assertEqual(c.SIGN_LABEL, "protocol-stack:v1:tx-sign")
        self.assertEqual(c.TX_ID_LABEL, "protocol-stack:v1:tx-id")


class KindTableTest(unittest.TestCase):
    def test_every_kind_is_fixed_length(self) -> None:
        for kind in c.TRANSACTION_KINDS:
            with self.subTest(kind):
                self.assertEqual(
                    envelope.expected_signed_length(kind),
                    c.HEADER_BYTES
                    + c.BODY_BYTES[kind]
                    + c.TRAILER_BYTES
                    + c.SIGNATURE_BYTES,
                )

    def test_two_pairs_share_a_body_length(self) -> None:
        self.assertEqual(
            c.BODY_BYTES[c.ACTIVATE_SEAT], c.BODY_BYTES[c.MINT_NODE_VERIFIED]
        )
        self.assertEqual(
            c.BODY_BYTES[c.HUB_ADD_ADDRESS], c.BODY_BYTES[c.HUB_REMOVE_ADDRESS]
        )

    def test_the_largest_transaction_shrank_from_version_three(self) -> None:
        """Purchase no longer carries an enrollment signature."""
        largest = max(
            envelope.expected_signed_length(kind) for kind in c.TRANSACTION_KINDS
        )
        self.assertEqual(largest, 293)
        self.assertLess(largest, 325)

    def test_every_kind_round_trips(self) -> None:
        for name, transaction in scenario.transactions().items():
            with self.subTest(name):
                raw = envelope.signed_bytes(transaction, scenario.TRANSFER_SIGNATURE)
                decoded, signature = envelope.decode_signed(raw)
                self.assertEqual(decoded, transaction)
                self.assertEqual(signature, scenario.TRANSFER_SIGNATURE)

    def test_every_kind_has_a_fixture(self) -> None:
        covered = {t.kind for t in scenario.transactions().values()}
        self.assertEqual(covered, set(c.TRANSACTION_KINDS))


class AdmissionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.accepted = bytearray(
            envelope.signed_bytes(
                scenario.accepted_transfer(), scenario.TRANSFER_SIGNATURE
            )
        )

    def refuses(self, raw: bytes) -> None:
        with self.assertRaises(envelope.MalformedTransaction):
            envelope.decode_signed(raw)

    def test_the_positive_control_is_accepted(self) -> None:
        envelope.decode_signed(bytes(self.accepted))

    def test_shape_failures_are_refused(self) -> None:
        cases = {
            "wrong_magic": b"XSTX" + self.accepted[4:],
            "wrong_schema": self.accepted[:4] + b"\x00\x02" + self.accepted[6:],
            "unknown_scheme": self.accepted[:39] + b"\x02" + self.accepted[40:],
            "trailing": bytes(self.accepted) + b"\x00",
            "truncated": bytes(self.accepted[:-1]),
        }
        for name, raw in cases.items():
            with self.subTest(name):
                self.refuses(bytes(raw))

    def test_an_unknown_kind_is_refused(self) -> None:
        for kind in (0, 13, 255):
            with self.subTest(kind):
                mutated = bytearray(self.accepted)
                mutated[6] = kind
                self.refuses(bytes(mutated))

    def test_a_non_minimal_absent_referrer_is_refused(self) -> None:
        purchase = scenario.transactions()["purchase_unreferred_last_seat"]
        raw = bytearray(envelope.signed_bytes(purchase, scenario.TRANSFER_SIGNATURE))
        raw[80 + 37] = 1
        self.refuses(bytes(raw))

    def test_enabling_protection_must_carry_no_signature(self) -> None:
        enable = scenario.transactions()["enable_mint_biometric"]
        raw = bytearray(envelope.signed_bytes(enable, scenario.TRANSFER_SIGNATURE))
        raw[80 + 5] = 1
        self.refuses(bytes(raw))

    def test_a_relabelled_kind_of_another_length_is_refused(self) -> None:
        mint = scenario.transactions()["mint_node"]
        raw = bytearray(envelope.signed_bytes(mint, scenario.TRANSFER_SIGNATURE))
        raw[6] = c.MINT_REFERRAL
        self.refuses(bytes(raw))

    def test_both_same_length_relabellings_change_the_signing_message(self) -> None:
        """The two cases a length check cannot catch."""
        for source, target in (
            ("activate_seat", c.MINT_NODE_VERIFIED),
            ("hub_add_address", c.HUB_REMOVE_ADDRESS),
        ):
            with self.subTest(source):
                original = scenario.transactions()[source]
                raw = bytearray(
                    envelope.signed_bytes(original, scenario.TRANSFER_SIGNATURE)
                )
                raw[6] = target
                decoded, _ = envelope.decode_signed(bytes(raw))
                self.assertEqual(decoded.kind, target)
                self.assertNotEqual(
                    envelope.signing_message(envelope.unsigned_bytes(decoded)),
                    envelope.signing_message(envelope.unsigned_bytes(original)),
                )


class HubMessageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.chain = scenario.CHAIN_ID
        self.who = scenario.ALICE_IDENTITY
        self.expiry = scenario.VALID_UNTIL_HEIGHT
        self.built = {
            "registration": messages.registration_message(
                self.chain, self.who, scenario.ALICE_KEY,
                scenario.ALICE_FIRST_ADDRESS, self.expiry
            ),
            "address_add": messages.address_add_message(
                self.chain, self.who, scenario.ALICE_SECOND_ADDRESS, self.expiry
            ),
            "address_remove": messages.address_remove_message(
                self.chain, self.who, scenario.ALICE_SECOND_ADDRESS, self.expiry
            ),
            "purchase": messages.purchase_message(
                self.chain, self.who, 0, scenario.ALICE_FIRST_ADDRESS, self.expiry
            ),
            "activation": messages.activation_message(
                self.chain, self.who, 0, self.expiry
            ),
            "mint": messages.mint_message(self.chain, self.who, 0, self.expiry),
            "disable": messages.mint_biometric_disable_message(
                self.chain, self.who, 0, self.expiry
            ),
            "manager": messages.manager_message(
                self.chain, self.who, 0, scenario.MANAGER_ACCOUNT_ID, self.expiry
            ),
        }

    def test_all_eight_are_distinct(self) -> None:
        self.assertEqual(len(set(self.built.values())), 8)

    def test_the_verifier_signs_exactly_one(self) -> None:
        """The whole architecture: an unavailable verifier stops only new people."""
        self.assertEqual(c.VERIFIER_SIGNED_LABELS, (c.REGISTRATION_LABEL,))
        self.assertEqual(len(c.HUB_MESSAGE_LABELS), 8)

    def test_every_message_names_the_identity(self) -> None:
        for name, message in self.built.items():
            with self.subTest(name):
                self.assertIn(self.who, message)

    def test_rebinding_the_identity_changes_every_message(self) -> None:
        other = messages.mint_message(self.chain, scenario.BOB_IDENTITY, 0, self.expiry)
        self.assertNotEqual(other, self.built["mint"])

    def test_three_messages_differ_only_by_their_label(self) -> None:
        from simulation.common.canonical import label_prefix

        bodies = {
            name: self.built[name][len(label_prefix(label)) :]
            for name, label in (
                ("activation", c.ACTIVATION_LABEL),
                ("mint", c.MINT_LABEL),
                ("disable", c.MINT_BIOMETRIC_DISABLE_LABEL),
            )
        }
        self.assertEqual(len(set(bodies.values())), 1)
        self.assertEqual(
            len({self.built[n] for n in ("activation", "mint", "disable")}), 3
        )

    def test_every_label_is_version_four(self) -> None:
        for label in c.HUB_MESSAGE_LABELS:
            with self.subTest(label):
                self.assertTrue(label.startswith("protocol-stack:v4:"))

    def test_a_field_of_the_wrong_width_is_refused(self) -> None:
        with self.assertRaises(envelope.MalformedTransaction):
            messages.mint_message(bytes(31), self.who, 0, self.expiry)
        with self.assertRaises(envelope.MalformedTransaction):
            messages.registration_message(
                self.chain, self.who, bytes(31), scenario.ALICE_FIRST_ADDRESS,
                self.expiry
            )


if __name__ == "__main__":
    unittest.main()
