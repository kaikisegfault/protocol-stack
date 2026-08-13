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
        self.assertEqual(len(body), c.FIXED_BODY_BYTES[c.TRANSFER])

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
                winners = len(transaction.body.get("winners", ()))
                raw = envelope.signed_bytes(transaction, scenario.TRANSFER_SIGNATURE)
                self.assertEqual(
                    len(raw), envelope.expected_signed_length(transaction.kind, winners)
                )

    def test_the_exercise_is_the_only_variable_length_kind(self) -> None:
        for kind in c.TRANSACTION_KINDS:
            fixed = envelope.expected_signed_length(kind)
            widened = envelope.expected_signed_length(kind, 1)
            if kind in c.VARIABLE_LENGTH_KINDS:
                self.assertEqual(widened - fixed, 4)
            else:
                self.assertEqual(widened, fixed)

    def test_a_fully_tied_exercise_fits_the_canonical_object_bound(self) -> None:
        at_capacity = envelope.expected_signed_length(
            c.EXERCISE_PERMISSION, c.FOUNDER_SEAT_CAPACITY
        )
        self.assertEqual(at_capacity, 400_170)
        self.assertLessEqual(at_capacity, c.MAX_OBJECT_BYTES)


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

    def test_an_absent_referrer_must_encode_as_zero(self) -> None:
        """A second encoding of one fact is the non-minimal representation."""
        raw = bytearray(
            envelope.signed_bytes(
                scenario.transactions()["activate_first_seat"],
                scenario.TRANSFER_SIGNATURE,
            )
        )
        envelope.decode_signed(bytes(raw))
        raw[85:89] = (1).to_bytes(4, "big")
        self.refuses(bytes(raw))

    def test_a_non_canonical_bool_is_malformed(self) -> None:
        raw = bytearray(
            envelope.signed_bytes(
                scenario.transactions()["activate_first_seat"],
                scenario.TRANSFER_SIGNATURE,
            )
        )
        raw[84] = 2
        self.refuses(bytes(raw))

    def test_a_winner_list_must_be_strictly_increasing_and_bounded(self) -> None:
        raw = bytearray(
            envelope.signed_bytes(
                scenario.transactions()["exercise_failed_cycle"],
                scenario.TRANSFER_SIGNATURE,
            )
        )
        envelope.decode_signed(bytes(raw))
        unordered = bytearray(raw)
        unordered[90:94], unordered[94:98] = unordered[94:98], unordered[90:94]
        self.refuses(bytes(unordered))

        duplicated = bytearray(raw)
        duplicated[94:98] = duplicated[90:94]
        self.refuses(bytes(duplicated))

        over = bytearray(raw)
        over[86:90] = (c.FOUNDER_SEAT_CAPACITY + 1).to_bytes(4, "big")
        self.refuses(bytes(over))

    def test_a_bounded_value_outside_its_range_still_decodes(self) -> None:
        """It is an execution result, so it keeps its receipt and root entry."""
        raw = bytearray(
            envelope.signed_bytes(
                scenario.transactions()["activate_first_seat"],
                scenario.TRANSFER_SIGNATURE,
            )
        )
        raw[80:84] = c.FOUNDER_SEAT_CAPACITY.to_bytes(4, "big")
        decoded, _ = envelope.decode_signed(bytes(raw))
        self.assertEqual(decoded.body["seat_id"], c.FOUNDER_SEAT_CAPACITY)
        self.assertGreater(decoded.body["seat_id"], c.MAX_SEAT_ID)


class CrossKindSeparationTest(unittest.TestCase):
    """Two kinds share a body width, so the signed kind byte must separate them."""

    def test_a_shared_width_body_reinterprets_but_changes_the_preimage(self) -> None:
        evaluation = scenario.transactions()["evaluate_first_cycle"]
        accrual = scenario.transactions()["accrue_referral"]
        self.assertEqual(
            c.FIXED_BODY_BYTES[evaluation.kind], c.FIXED_BODY_BYTES[accrual.kind]
        )

        raw = bytearray(envelope.signed_bytes(evaluation, scenario.TRANSFER_SIGNATURE))
        raw[6] = c.ACCRUE_REFERRAL
        reinterpreted, _ = envelope.decode_signed(bytes(raw))
        self.assertEqual(reinterpreted.kind, c.ACCRUE_REFERRAL)

        # The bytes decode; what fails is the signature, because the kind byte
        # is inside the preimage that was signed.
        self.assertNotEqual(
            envelope.signing_message(envelope.unsigned_bytes(evaluation)),
            envelope.signing_message(envelope.unsigned_bytes(reinterpreted)),
        )

    def test_the_chain_id_and_kind_are_both_inside_the_signing_message(self) -> None:
        transfer = scenario.accepted_transfer()
        message = envelope.signing_message(envelope.unsigned_bytes(transfer))
        self.assertIn(scenario.CHAIN_ID, message)
        self.assertIn(bytes([transfer.kind]), message)


if __name__ == "__main__":
    unittest.main()
