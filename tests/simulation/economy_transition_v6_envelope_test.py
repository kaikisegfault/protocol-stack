#!/usr/bin/env python3
"""The version-six envelope: two schemes, fourteen kinds, five retired.

The claims this module exists to hold are the ones a byte-level vector file
cannot state on its own: that the kind-1 bytes survive a fifth version while
their execution does not, that a kind fixes its scheme so no transaction is
ambiguous about what authorized it, and that every retired identifier is refused
rather than quietly unknown.
"""

from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v6 import contract as c
from simulation.economy_transition_v6 import envelope, scenario
from simulation.economy_transition_v6.envelope import MalformedTransaction

ACCEPTED = Path(__file__).resolve().parents[2] / "test-vectors"


def _accepted_primitives() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (ACCEPTED / "protocol-primitives-v1.txt").read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, _, value = stripped.partition("=")
            values[key] = value
    return values


class KindOneIdentityTest(unittest.TestCase):
    """The compatibility claim, checked against the accepted M1 file."""

    def setUp(self) -> None:
        self.recorded = _accepted_primitives()
        self.transfer = scenario.accepted_transfer()

    def test_the_unsigned_transfer_is_the_accepted_bytes(self) -> None:
        unsigned = envelope.unsigned_bytes(self.transfer)
        self.assertEqual(unsigned.hex(), self.recorded["unsigned_tx"])
        self.assertEqual(len(unsigned), 136)

    def test_the_signed_transfer_is_the_accepted_bytes(self) -> None:
        signed = envelope.signed_bytes(self.transfer, scenario.TRANSFER_SIGNATURE)
        self.assertEqual(signed.hex(), self.recorded["signed_tx"])
        self.assertEqual(len(signed), 200)

    def test_the_transaction_id_is_the_accepted_id(self) -> None:
        signed = envelope.signed_bytes(self.transfer, scenario.TRANSFER_SIGNATURE)
        self.assertEqual(
            envelope.transaction_id(signed), self.recorded["tx.item2"]
        )

    def test_the_bytes_survive_and_the_execution_does_not(self) -> None:
        """Version one creates the recipient; version six refuses it.

        The bytes are identical and the outcome is not, which is the one claim
        no earlier version had to make.
        """
        registry = scenario.registry()
        self.assertNotIn(
            self.transfer.body["recipient_escrow_id"], registry.escrows
        )
        self.assertIn(scenario.BOB_ESCROW, registry.escrows)
        self.assertEqual(c.RESULT_CODES[27], "RECIPIENT_NOT_REGISTERED")


class SchemeTest(unittest.TestCase):
    def test_every_kind_fixes_exactly_one_scheme(self) -> None:
        self.assertEqual(set(c.KIND_SCHEME), set(c.TRANSACTION_KINDS))
        for kind, scheme in c.KIND_SCHEME.items():
            self.assertIn(scheme, c.SIGNATURE_SCHEMES, f"kind {kind}")

    def test_the_administrative_kinds_are_identity_authorized(self) -> None:
        """Scheme 2 is what lets a person holding no key act at all."""
        administrative = {
            c.HUB_REGISTER,
            c.ESCROW_CREATE,
            c.ESCROW_DELETE,
            c.SIGNER_ADD,
            c.SIGNER_REVOKE,
        }
        for kind in administrative:
            self.assertEqual(c.KIND_SCHEME[kind], c.SCHEME_IDENTITY, f"kind {kind}")
        for kind in set(c.TRANSACTION_KINDS) - administrative:
            self.assertEqual(c.KIND_SCHEME[kind], c.SCHEME_SIGNER, f"kind {kind}")

    def test_a_kind_refuses_a_scheme_it_does_not_permit(self) -> None:
        transfer = scenario.accepted_transfer()
        with self.assertRaises(MalformedTransaction):
            envelope.unsigned_bytes(replace(transfer, scheme=c.SCHEME_IDENTITY))

    def test_the_posture_change_is_signer_authorized(self) -> None:
        """The asymmetry lives inside kind 17 rather than in its scheme.

        Tightening must work with a signer signature alone, so the kind cannot
        be scheme 2; the HUB signature it carries for a relaxation is a body
        field.
        """
        self.assertEqual(c.KIND_SCHEME[c.SET_SECURITY_POSTURE], c.SCHEME_SIGNER)


class RetiredKindTest(unittest.TestCase):
    def test_no_retired_identifier_is_assigned(self) -> None:
        self.assertFalse(set(c.RETIRED_KINDS) & set(c.TRANSACTION_KINDS))

    def test_a_retired_identifier_is_refused_at_admission(self) -> None:
        valid = bytearray(
            envelope.signed_bytes(
                scenario.accepted_transfer(), scenario.TRANSFER_SIGNATURE
            )
        )
        for kind in c.RETIRED_KINDS:
            mutated = bytearray(valid)
            mutated[6] = kind
            with self.subTest(kind=kind), self.assertRaises(MalformedTransaction):
                envelope.decode_signed(bytes(mutated))


class BodyLayoutTest(unittest.TestCase):
    def test_every_kind_round_trips_through_its_body(self) -> None:
        for name, transaction in scenario.transactions().items():
            with self.subTest(name):
                signed = envelope.signed_bytes(transaction, bytes(64))
                decoded, signature = envelope.decode_signed(signed)
                self.assertEqual(signature, bytes(64))
                self.assertEqual(decoded.kind, transaction.kind)
                self.assertEqual(decoded.scheme, transaction.scheme)
                self.assertEqual(decoded.body, transaction.body)

    def test_every_kind_is_fixed_length(self) -> None:
        for kind in c.TRANSACTION_KINDS:
            transaction = _first_of_kind(kind)
            body = envelope.body_bytes(transaction.kind, transaction.body)
            self.assertEqual(len(body), c.BODY_BYTES[kind], f"kind {kind}")

    def test_five_kinds_share_a_body_length(self) -> None:
        """A decoder dispatches on the kind byte, which is why this is safe."""
        ninety_six = {
            kind for kind, width in c.BODY_BYTES.items() if width == 96
        }
        self.assertEqual(
            ninety_six,
            {
                c.MINT_REFERRAL,
                c.ESCROW_DELETE,
                c.SIGNER_ADD,
                c.SIGNER_REVOKE,
                c.MINT_VERIFIED_USER,
            },
        )

    def test_the_largest_transaction_is_the_registration(self) -> None:
        largest = max(
            (envelope.expected_signed_length(kind), kind)
            for kind in c.TRANSACTION_KINDS
        )
        self.assertEqual(largest, (288, c.HUB_REGISTER))


class RegistrationEnvelopeTest(unittest.TestCase):
    """Registration has no escrow yet, so both its variable fields are fixed."""

    def setUp(self) -> None:
        self.registration = scenario.transactions()["hub_register"]

    def test_it_carries_a_zero_nonce_and_a_zero_fee_limit(self) -> None:
        self.assertEqual(self.registration.nonce, 0)
        self.assertEqual(self.registration.fee_limit, 0)

    def test_a_nonzero_nonce_is_refused(self) -> None:
        raw = envelope.signed_bytes(replace(self.registration, nonce=1), bytes(64))
        with self.assertRaises(MalformedTransaction):
            envelope.decode_signed(raw)

    def test_a_nonzero_fee_limit_is_refused(self) -> None:
        raw = envelope.signed_bytes(
            replace(self.registration, fee_limit=1), bytes(64)
        )
        with self.assertRaises(MalformedTransaction):
            envelope.decode_signed(raw)


def _first_of_kind(kind: int):
    for transaction in scenario.transactions().values():
        if transaction.kind == kind:
            return transaction
    raise AssertionError(f"the fixture holds no kind {kind}")


if __name__ == "__main__":
    unittest.main()
