#!/usr/bin/env python3
"""Version ten's contract half: the declarations, the entries, and the rules.

The recorded vectors fix one value per construction. These cover what a fixed
vector cannot: that every refusal a decoder owes is reachable, that the
lifetime rule governs exactly the kinds the specification names and no others,
and that the carried surface is version nine's own.
"""

from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v6.envelope import MalformedTransaction
from simulation.economy_transition_v9 import contract as v9c
from simulation.economy_transition_v10 import contract as c
from simulation.economy_transition_v10 import envelope, genesis, messages, state

CHAIN = bytes([0x0C]) * 32
KEY = bytes([0x22]) * 32
SIGNATURE = bytes([0x5A]) * 64
NO_SIGNATURE = bytes(64)


def fixture_genesis(**changes) -> genesis.Genesis:
    fields = dict(
        network_id=10,
        genesis_timestamp=1_768_435_200_000,
        supply_limit=5_699_395_010_000_000_000,
        fixed_transfer_fee=1_000,
        manifest_digest=bytes.fromhex(c.MANIFEST_DIGEST_HEX),
        launch_key=bytes([0x55]) * 32,
        dispute_authority_key=bytes([0xD8]) * 32,
        build_authority_key=bytes([0xB4]) * 32,
    )
    return genesis.Genesis(**(fields | changes))


def transaction(kind: int, body: dict, valid_until: int = 1_200) -> envelope.Transaction:
    return envelope.Transaction(
        kind=kind,
        scheme=c.KIND_SCHEME[kind],
        chain_id=CHAIN,
        authority_public_key=KEY,
        nonce=0 if kind == c.HUB_REGISTER else 1,
        body=body,
        fee_limit=0 if kind in (c.HUB_REGISTER, c.CHALLENGE_RESPONSE) else 1_000,
        valid_until_height=valid_until,
    )


class DeclarationTest(unittest.TestCase):
    def test_the_classification_partitions_version_nines_surface(self) -> None:
        surface = {n for n in dir(v9c) if n.isupper() and not n.startswith("_")}
        classified = (
            set(c.CARRIED_FROM_V9)
            | set(c.REVISED_IN_V10)
            | set(c.WITHDRAWN_IN_V10)
            | set(c.REPLACED_DECLARATIONS)
        )
        self.assertEqual(classified, surface)

    def test_every_version_ten_name_is_declared(self) -> None:
        names = {n for n in dir(c) if n.isupper() and not n.startswith("_")}
        declared = (
            set(c.CARRIED_FROM_V9)
            | set(c.REVISED_IN_V10)
            | set(c.ADDED_IN_V10)
            | set(c.DECLARATIONS)
        )
        self.assertEqual(names, declared)

    def test_carried_constants_are_version_nines_objects(self) -> None:
        for name in c.CARRIED_FROM_V9:
            self.assertIs(getattr(c, name), getattr(v9c, name), name)

    def test_the_account_bound_moves_by_one(self) -> None:
        self.assertEqual(c.MAX_GENESIS_ACCOUNTS, v9c.MAX_GENESIS_ACCOUNTS - 1)
        self.assertLessEqual(
            c.GENESIS_PREFIX_BYTES + c.MAX_GENESIS_ACCOUNTS * c.ACCOUNT_ENTRY_BYTES,
            c.MAX_OBJECT_BYTES,
        )

    def test_the_founder_figures_are_the_adr_s(self) -> None:
        self.assertEqual(c.LAUNCH_RETIREMENT_ACTIVE_MACHINES, 100)
        self.assertEqual(c.MACHINE_REGISTRATIONS_PER_WINDOW, 1_000)
        self.assertEqual(c.APPROVAL_LIFETIME_BLOCKS, c.SLOT_BLOCKS)


class GenesisTest(unittest.TestCase):
    def test_a_build_key_of_the_wrong_width_is_refused(self) -> None:
        with self.assertRaises(MalformedTransaction):
            genesis.encode(fixture_genesis(build_authority_key=bytes(31)))

    def test_version_nine_refusals_still_apply(self) -> None:
        with self.assertRaises(MalformedTransaction):
            genesis.encode(fixture_genesis(genesis_timestamp=-1))

    def test_each_key_moves_the_chain_id(self) -> None:
        base = genesis.chain_id(fixture_genesis())
        for name in ("launch_key", "dispute_authority_key", "build_authority_key"):
            moved = fixture_genesis(**{name: bytes([0x01]) * 32})
            self.assertNotEqual(genesis.chain_id(moved), base, name)


class StateTest(unittest.TestCase):
    def entry(self, **changes) -> state.MachineKey:
        return replace(state.MachineKey(KEY, bytes([0x33]) * 32, 3, 5, 6, 7), **changes)

    def test_every_machine_key_refusal_is_reachable(self) -> None:
        for bad in (
            self.entry(machine_public_key=bytes(31)),
            self.entry(build_digest=bytes(33)),
            self.entry(registered_at_height=0),
            self.entry(registrations_in_window=1_001),
            self.entry(last_met_window=-1),
        ):
            with self.assertRaises(state.InvalidStateEntry):
                state.machine_key_value(bad)
        with self.assertRaises(state.InvalidStateEntry):
            state.decode_machine_key_value(bytes(91))

    def test_owner_and_retirement_refusals(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.launch_retirement_value(0)
        with self.assertRaises(state.InvalidStateEntry):
            state.decode_launch_retirement_value(bytes(7))
        with self.assertRaises(state.InvalidStateEntry):
            state.decode_machine_key_owner_value(bytes(5))
        with self.assertRaises(state.InvalidStateEntry):
            state.machine_key_owner_key(bytes(31))
        with self.assertRaises(state.InvalidStateEntry):
            state.machine_key_parts(state.launch_retirement_key())

    def test_entry_shape_delegates_carried_kinds_to_version_nine(self) -> None:
        entries = genesis.initial_economy_entries(fixture_genesis())
        self.assertEqual(len(state.ordered_entries(entries)), 16)
        with self.assertRaises(state.InvalidStateEntry):
            state.require_entry_shape(bytes([99]), b"")


class EnvelopeTest(unittest.TestCase):
    def test_a_registration_needs_a_zero_nonce(self) -> None:
        body = {
            "hub_identity_hash": KEY,
            "first_signer_public_key": KEY,
            "attesting_seat_id": c.LAUNCH_ATTESTER,
            "attestation_signature": SIGNATURE,
        }
        raw = envelope.signed_bytes(replace(transaction(10, body), nonce=1), SIGNATURE)
        with self.assertRaises(MalformedTransaction):
            envelope.decode_signed(raw)

    def test_kind_23_under_the_identity_scheme_is_refused(self) -> None:
        body = {
            "seat_id": 0,
            "machine_public_key": KEY,
            "build_digest": KEY,
            "attestation_signature": SIGNATURE,
            "hub_signature": SIGNATURE,
        }
        with self.assertRaises(MalformedTransaction):
            envelope.unsigned_bytes(replace(transaction(23, body), scheme=2))


class ApprovalTest(unittest.TestCase):
    def test_only_body_carried_kinds_have_approved_bytes(self) -> None:
        transfer = transaction(1, {"recipient_escrow_id": KEY, "amount_atomic": 1})
        with self.assertRaises(MalformedTransaction):
            messages.approved_bytes(transfer)

    def test_the_lifetime_governs_exactly_the_proven_transactions(self) -> None:
        far = 10_000_000_000
        governed = transaction(
            19,
            {"recipient_escrow_id": KEY, "amount_atomic": 1, "hub_signature": SIGNATURE},
            far,
        )
        self.assertTrue(messages.approval_lifetime_exceeded(governed, 0))
        absent = replace(governed, body=governed.body | {"hub_signature": NO_SIGNATURE})
        self.assertFalse(messages.approval_lifetime_exceeded(absent, 0))
        tighten = transaction(
            17,
            {
                "requires_confirmation": True,
                "min_amount_atomic": 0,
                "exempt_slot_mask": 0,
                "hub_signature": NO_SIGNATURE,
            },
            far,
        )
        self.assertFalse(messages.approval_lifetime_exceeded(tighten, 0))
        transfer = transaction(1, {"recipient_escrow_id": KEY, "amount_atomic": 1}, far)
        self.assertFalse(messages.approval_lifetime_exceeded(transfer, 0))
        for kind in (13, 14, 15, 16):
            self.assertIn(kind, c.ALWAYS_PROVEN_KINDS)
        self.assertEqual(c.APPROVAL_KINDS & {1, 6, 10, 13, 14, 15, 16, 20, 21}, set())


if __name__ == "__main__":
    unittest.main()
