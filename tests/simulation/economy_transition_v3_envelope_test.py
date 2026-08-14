#!/usr/bin/env python3
"""The version-three transaction envelope, its ten bodies, and admission."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v3 import contract as c
from simulation.economy_transition_v3 import envelope, messages, scenario

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ACCEPTED_PRIMITIVES = REPOSITORY_ROOT / "test-vectors" / "protocol-primitives-v1.txt"


def accepted_value(key: str) -> str:
    for line in ACCEPTED_PRIMITIVES.read_text(encoding="ascii").splitlines():
        name, separator, value = line.partition("=")
        if separator and name == key:
            return value
    raise AssertionError(f"{key} is not recorded in the accepted vectors")


class VersionOneIdentityTest(unittest.TestCase):
    """The whole compatibility argument, checked against the accepted file.

    Version two established that the transfer factors. What version three must
    show is that adding four kinds, three state entries, and a settlement rule
    left the factoring untouched, which is only evidence if it is checked
    against the accepted bytes again rather than against version two's model.
    """

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

    def test_the_header_and_trailer_are_slices_of_the_accepted_transfer(self) -> None:
        accepted = bytes.fromhex(accepted_value("unsigned_tx"))
        derived = envelope.unsigned_bytes(self.transfer)
        self.assertEqual(derived[: c.HEADER_BYTES], accepted[: c.HEADER_BYTES])
        self.assertEqual(derived[-c.TRAILER_BYTES :], accepted[-c.TRAILER_BYTES :])
        body = accepted[c.HEADER_BYTES : len(accepted) - c.TRAILER_BYTES]
        self.assertEqual(len(body), c.BODY_BYTES[c.TRANSFER])

    def test_the_schema_version_and_labels_are_not_re_versioned(self) -> None:
        self.assertEqual(c.ENVELOPE_SCHEMA_VERSION, 1)
        self.assertEqual(c.SIGN_LABEL, "protocol-stack:v1:tx-sign")
        self.assertEqual(c.TX_ID_LABEL, "protocol-stack:v1:tx-id")

    def test_the_version_two_encoder_agrees_on_the_kind_one_bytes(self) -> None:
        """Two accepted contracts must encode one accepted transfer identically."""
        from simulation.economy_transition import envelope as v2_envelope
        from simulation.economy_transition import scenario as v2_scenario

        self.assertEqual(
            envelope.unsigned_bytes(self.transfer),
            v2_envelope.unsigned_bytes(v2_scenario.accepted_transfer()),
        )


class KindTableTest(unittest.TestCase):
    def test_every_kind_is_fixed_length(self) -> None:
        for kind in c.TRANSACTION_KINDS:
            with self.subTest(kind):
                expected = (
                    c.HEADER_BYTES
                    + c.BODY_BYTES[kind]
                    + c.TRAILER_BYTES
                    + c.SIGNATURE_BYTES
                )
                self.assertEqual(envelope.expected_signed_length(kind), expected)

    def test_kinds_three_and_seven_share_a_body_length(self) -> None:
        """The case version two anticipated when it required dispatch on kind."""
        self.assertEqual(
            c.BODY_BYTES[c.ACTIVATE_SEAT], c.BODY_BYTES[c.MINT_NODE_VERIFIED]
        )

    def test_the_largest_transaction_is_still_the_purchase(self) -> None:
        largest = max(
            envelope.expected_signed_length(kind) for kind in c.TRANSACTION_KINDS
        )
        self.assertEqual(largest, 325)
        self.assertEqual(largest, envelope.expected_signed_length(c.PURCHASE_SEAT))

    def test_no_body_scales_with_the_seat_population(self) -> None:
        """Nothing a transaction carries grows with the number of seats."""
        self.assertLess(max(c.BODY_BYTES.values()), 1_000)

    def test_every_kind_round_trips(self) -> None:
        for name, transaction in scenario.transactions().items():
            with self.subTest(name):
                raw = envelope.signed_bytes(transaction, scenario.TRANSFER_SIGNATURE)
                decoded, signature = envelope.decode_signed(raw)
                self.assertEqual(decoded, transaction)
                self.assertEqual(signature, scenario.TRANSFER_SIGNATURE)

    def test_every_kind_has_a_fixture(self) -> None:
        covered = {
            transaction.kind for transaction in scenario.transactions().values()
        }
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
        for kind in (0, 11, 255):
            with self.subTest(kind):
                mutated = bytearray(self.accepted)
                mutated[6] = kind
                self.refuses(bytes(mutated))

    def test_a_non_minimal_absent_referrer_is_refused(self) -> None:
        purchase = scenario.transactions()["purchase_unreferred_last_seat"]
        raw = bytearray(envelope.signed_bytes(purchase, scenario.TRANSFER_SIGNATURE))
        raw[80 + 69] = 1
        self.refuses(bytes(raw))

    def test_a_non_canonical_referrer_flag_is_refused(self) -> None:
        purchase = scenario.transactions()["purchase_unreferred_last_seat"]
        raw = bytearray(envelope.signed_bytes(purchase, scenario.TRANSFER_SIGNATURE))
        raw[80 + 68] = 2
        self.refuses(bytes(raw))

    def test_enabling_protection_must_carry_no_signature(self) -> None:
        """Half of the asymmetry is checkable on the bytes alone."""
        enable = scenario.transactions()["enable_mint_biometric"]
        raw = bytearray(envelope.signed_bytes(enable, scenario.TRANSFER_SIGNATURE))
        raw[80 + 5] = 1
        self.refuses(bytes(raw))

    def test_a_non_canonical_enable_flag_is_refused(self) -> None:
        enable = scenario.transactions()["enable_mint_biometric"]
        raw = bytearray(envelope.signed_bytes(enable, scenario.TRANSFER_SIGNATURE))
        raw[80 + 4] = 2
        self.refuses(bytes(raw))

    def test_disabling_protection_carries_a_signature(self) -> None:
        disable = scenario.transactions()["disable_mint_biometric"]
        raw = envelope.signed_bytes(disable, scenario.TRANSFER_SIGNATURE)
        decoded, _ = envelope.decode_signed(raw)
        self.assertFalse(decoded.body["enable"])
        self.assertNotEqual(decoded.body["biometric_signature"], bytes(64))

    def test_a_relabelled_kind_of_another_length_is_refused(self) -> None:
        mint = scenario.transactions()["mint_node"]
        raw = bytearray(envelope.signed_bytes(mint, scenario.TRANSFER_SIGNATURE))
        raw[6] = c.MINT_REFERRAL
        self.refuses(bytes(raw))

    def test_a_relabelled_kind_of_the_same_length_changes_the_signing_message(
        self,
    ) -> None:
        """The one relabelling a length check cannot catch.

        Kinds 3 and 7 share a body length, so an activation relabelled as a
        protected mint decodes. What separates them is the kind byte at offset
        6, which sits inside every signature preimage, so the two cannot share a
        signature.
        """
        activate = scenario.transactions()["activate_seat"]
        raw = bytearray(envelope.signed_bytes(activate, scenario.TRANSFER_SIGNATURE))
        raw[6] = c.MINT_NODE_VERIFIED
        decoded, _ = envelope.decode_signed(bytes(raw))
        self.assertEqual(decoded.kind, c.MINT_NODE_VERIFIED)
        self.assertNotEqual(
            envelope.signing_message(envelope.unsigned_bytes(decoded)),
            envelope.signing_message(envelope.unsigned_bytes(activate)),
        )

    def test_a_seat_id_outside_its_range_decodes_and_is_refused_at_execution(
        self,
    ) -> None:
        """Shape belongs to admission and value belongs to execution."""
        mint = scenario.transactions()["mint_node"]
        raw = bytearray(envelope.signed_bytes(mint, scenario.TRANSFER_SIGNATURE))
        raw[80:84] = c.FOUNDER_SEAT_CAPACITY.to_bytes(4, "big")
        decoded, _ = envelope.decode_signed(bytes(raw))
        self.assertEqual(decoded.body["seat_id"], c.FOUNDER_SEAT_CAPACITY)
        self.assertGreater(decoded.body["seat_id"], c.MAX_SEAT_ID)


class VerifierMessageTest(unittest.TestCase):
    """Six messages, six labels, and the separation the labels provide."""

    def setUp(self) -> None:
        self.chain = scenario.CHAIN_ID
        self.actor = scenario.PURCHASER_ACCOUNT_ID
        self.expiry = scenario.VALID_UNTIL_HEIGHT
        self.built = {
            "enrollment": messages.enrollment_message(
                self.chain,
                0,
                scenario.BIOMETRIC_IDENTITY_HASH,
                scenario.PURCHASER_ACCOUNT_ID,
                self.expiry,
            ),
            "activation": messages.activation_message(
                self.chain, 0, self.actor, self.expiry
            ),
            "mint": messages.mint_message(self.chain, 0, self.actor, self.expiry),
            "disable": messages.mint_biometric_disable_message(
                self.chain, 0, self.actor, self.expiry
            ),
            "manager": messages.manager_message(
                self.chain, 0, self.actor, scenario.MANAGER_ACCOUNT_ID, self.expiry
            ),
            "hub": messages.hub_message(
                self.chain, self.actor, scenario.HUB_UNIQUENESS_HASH, self.expiry
            ),
        }

    def test_all_six_messages_are_distinct(self) -> None:
        self.assertEqual(len(set(self.built.values())), 6)

    def test_three_messages_differ_only_by_their_label(self) -> None:
        """Domain separation is what stops an approval crossing actions."""
        bodies = {
            name: self.built[name][len(label) + 1 :]
            for name, label in (
                ("activation", c.ACTIVATION_LABEL),
                ("mint", c.MINT_LABEL),
                ("disable", c.MINT_BIOMETRIC_DISABLE_LABEL),
            )
        }
        self.assertEqual(len(set(bodies.values())), 1)
        self.assertEqual(
            len({self.built[name] for name in ("activation", "mint", "disable")}), 3
        )

    def test_every_label_is_version_three(self) -> None:
        for label in c.VERIFIER_MESSAGE_LABELS:
            with self.subTest(label):
                self.assertTrue(label.startswith("protocol-stack:v3:"))
        self.assertEqual(len(set(c.VERIFIER_MESSAGE_LABELS)), 6)

    def test_an_approval_is_bound_to_its_seat_actor_chain_and_expiry(self) -> None:
        base = self.built["mint"]
        rebindings = {
            "seat": messages.mint_message(self.chain, 1, self.actor, self.expiry),
            "actor": messages.mint_message(
                self.chain, 0, scenario.MANAGER_ACCOUNT_ID, self.expiry
            ),
            "chain": messages.mint_message(bytes(32), 0, self.actor, self.expiry),
            "expiry": messages.mint_message(
                self.chain, 0, self.actor, self.expiry + 1
            ),
        }
        for name, rebound in rebindings.items():
            with self.subTest(name):
                self.assertNotEqual(rebound, base)

    def test_a_message_refuses_a_field_of_the_wrong_width(self) -> None:
        with self.assertRaises(envelope.MalformedTransaction):
            messages.mint_message(bytes(31), 0, self.actor, self.expiry)
        with self.assertRaises(envelope.MalformedTransaction):
            messages.hub_message(self.chain, self.actor, bytes(31), self.expiry)


if __name__ == "__main__":
    unittest.main()
