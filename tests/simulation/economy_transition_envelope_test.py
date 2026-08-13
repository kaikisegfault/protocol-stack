#!/usr/bin/env python3
"""The version-two transaction envelope, its six bodies, and admission."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition import contract as c
from simulation.economy_transition import envelope, scenario

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ACCEPTED_PRIMITIVES = REPOSITORY_ROOT / "test-vectors" / "protocol-primitives-v1.txt"


def accepted_value(key: str) -> str:
    for line in ACCEPTED_PRIMITIVES.read_text(encoding="ascii").splitlines():
        name, separator, value = line.partition("=")
        if separator and name == key:
            return value
    raise AssertionError(f"{key} is not recorded in the accepted vectors")


class VersionOneIdentityTest(unittest.TestCase):
    """The whole compatibility argument, checked against the accepted file."""

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
        """The factoring must be a partition of the accepted bytes, not a rewrite."""
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


class EncodingTest(unittest.TestCase):
    def test_every_kind_round_trips(self) -> None:
        for name, transaction in scenario.transactions().items():
            with self.subTest(name):
                raw = envelope.signed_bytes(transaction, scenario.TRANSFER_SIGNATURE)
                decoded, signature = envelope.decode_signed(raw)
                self.assertEqual(decoded, transaction)
                self.assertEqual(signature, scenario.TRANSFER_SIGNATURE)

    def test_every_kind_has_the_length_its_table_requires(self) -> None:
        for name, transaction in scenario.transactions().items():
            with self.subTest(name):
                raw = envelope.signed_bytes(transaction, scenario.TRANSFER_SIGNATURE)
                self.assertEqual(
                    len(raw), envelope.expected_signed_length(transaction.kind)
                )

    def test_no_kind_is_variable_length(self) -> None:
        """Nothing a transaction carries scales with the seat population."""
        for kind in c.TRANSACTION_KINDS:
            with self.subTest(kind):
                self.assertEqual(
                    envelope.expected_signed_length(kind),
                    c.HEADER_BYTES
                    + c.BODY_BYTES[kind]
                    + c.TRAILER_BYTES
                    + c.SIGNATURE_BYTES,
                )

    def test_no_two_kinds_share_a_body_length(self) -> None:
        lengths = list(c.BODY_BYTES.values())
        self.assertEqual(len(set(lengths)), len(lengths))

    def test_the_largest_transaction_is_far_below_the_object_bound(self) -> None:
        largest = max(
            envelope.expected_signed_length(kind) for kind in c.TRANSACTION_KINDS
        )
        self.assertEqual(largest, 325)
        self.assertLess(largest, c.MAX_OBJECT_BYTES)


class AdmissionTest(unittest.TestCase):
    """Shape only. A bounded value outside its range decodes and is refused later."""

    def setUp(self) -> None:
        self.accepted = bytearray(
            envelope.signed_bytes(
                scenario.accepted_transfer(), scenario.TRANSFER_SIGNATURE
            )
        )

    def refuses(self, raw: bytes) -> None:
        with self.assertRaises(envelope.MalformedTransaction):
            envelope.decode_signed(raw)

    def test_the_unmutated_encoding_is_accepted(self) -> None:
        envelope.decode_signed(bytes(self.accepted))

    def test_a_wrong_magic_or_schema_version_is_malformed(self) -> None:
        self.refuses(b"XSTX" + bytes(self.accepted[4:]))
        self.refuses(bytes(self.accepted[:4]) + b"\x00\x02" + bytes(self.accepted[6:]))

    def test_an_unknown_kind_is_malformed(self) -> None:
        for kind in (0, 7, 255):
            mutated = bytearray(self.accepted)
            mutated[6] = kind
            self.refuses(bytes(mutated))

    def test_trailing_and_truncated_bytes_are_malformed(self) -> None:
        self.refuses(bytes(self.accepted) + b"\x00")
        self.refuses(bytes(self.accepted[:-1]))

    def purchase(self) -> bytearray:
        return bytearray(
            envelope.signed_bytes(
                scenario.transactions()["purchase_unreferred_last_seat"],
                scenario.TRANSFER_SIGNATURE,
            )
        )

    def test_an_absent_referrer_must_encode_as_thirty_two_zero_octets(self) -> None:
        """A second encoding of one fact is the non-minimal representation."""
        raw = self.purchase()
        envelope.decode_signed(bytes(raw))
        raw[80 + 69] = 1
        self.refuses(bytes(raw))

    def test_a_non_canonical_bool_is_malformed(self) -> None:
        raw = self.purchase()
        raw[80 + 68] = 2
        self.refuses(bytes(raw))

    def test_a_relabelled_body_fails_on_length(self) -> None:
        """No two kinds share a length, so re-labelling is caught before signing."""
        raw = bytearray(
            envelope.signed_bytes(
                scenario.transactions()["mint_node"], scenario.TRANSFER_SIGNATURE
            )
        )
        raw[6] = c.MINT_REFERRAL
        self.refuses(bytes(raw))

    def test_a_bounded_value_outside_its_range_still_decodes(self) -> None:
        """It is an execution result, so it keeps its receipt and root entry."""
        raw = bytearray(
            envelope.signed_bytes(
                scenario.transactions()["mint_node"], scenario.TRANSFER_SIGNATURE
            )
        )
        raw[80:84] = c.FOUNDER_SEAT_CAPACITY.to_bytes(4, "big")
        decoded, _ = envelope.decode_signed(bytes(raw))
        self.assertEqual(decoded.body["seat_id"], c.FOUNDER_SEAT_CAPACITY)
        self.assertGreater(decoded.body["seat_id"], c.MAX_SEAT_ID)

    def test_the_biometric_signature_is_carried_but_not_verified_here(self) -> None:
        """It verifies against ledger state, which admission is defined not to read."""
        raw = self.purchase()
        raw[80 + 101] ^= 0xFF
        decoded, _ = envelope.decode_signed(bytes(raw))
        self.assertNotEqual(
            decoded.body["biometric_signature"], scenario.BIOMETRIC_SIGNATURE
        )


class CrossKindSeparationTest(unittest.TestCase):
    """The kind byte is inside every preimage, so a signature cannot cross kinds."""

    def test_flipping_the_kind_byte_changes_the_signing_message(self) -> None:
        """The byte a re-labelling attack would change is inside the preimage."""
        for name, transaction in scenario.transactions().items():
            with self.subTest(name):
                unsigned = bytearray(envelope.unsigned_bytes(transaction))
                original = envelope.signing_message(bytes(unsigned))
                for other in c.TRANSACTION_KINDS:
                    if other == transaction.kind:
                        continue
                    unsigned[6] = other
                    self.assertNotEqual(
                        original, envelope.signing_message(bytes(unsigned))
                    )
                unsigned[6] = transaction.kind
                self.assertEqual(original, envelope.signing_message(bytes(unsigned)))

    def test_every_kinds_encoding_is_distinct(self) -> None:
        encodings = {
            name: envelope.signed_bytes(tx, scenario.TRANSFER_SIGNATURE)
            for name, tx in scenario.transactions().items()
        }
        self.assertEqual(len(set(encodings.values())), len(encodings))

    def test_the_chain_id_and_kind_are_both_inside_the_signing_message(self) -> None:
        transfer = scenario.accepted_transfer()
        message = envelope.signing_message(envelope.unsigned_bytes(transfer))
        self.assertIn(scenario.CHAIN_ID, message)
        self.assertIn(bytes([transfer.kind]), message)


if __name__ == "__main__":
    unittest.main()
