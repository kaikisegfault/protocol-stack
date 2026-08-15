#!/usr/bin/env python3
"""The account architecture: identities, escrows, signers, and recovery.

The vectors fix the derivations and the fixture's recorded shape. What is tested
here is what the derivations mean: that a deleted escrow's identifier is never
reissued, that one signer key belongs to exactly one escrow, that recovery is the
ordinary signer-add rather than a transaction of its own, and that the four
structural invariants hold as equalities.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v6 import contract as c
from simulation.economy_transition_v6 import scenario
from simulation.economy_transition_v6.identity import (
    Posture,
    Registry,
    RegistryError,
    escrow_id,
    relaxes,
    requires_confirmation,
    signer_id,
    slot_of,
)

ACCEPTED = Path(__file__).resolve().parents[2] / "test-vectors"


class DerivationTest(unittest.TestCase):
    def test_the_signer_derivation_is_the_accepted_account_derivation(self) -> None:
        """Checked against the accepted file, not against a second restatement."""
        recorded = {}
        for line in (ACCEPTED / "protocol-primitives-v1.txt").read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, value = line.strip().partition("=")
                recorded[key] = value
        self.assertEqual(
            signer_id(scenario.SENDER_PUBLIC_KEY).hex(), recorded["account_id"]
        )

    def test_an_escrow_identifier_depends_on_both_terms(self) -> None:
        alice, bob = scenario.ALICE_IDENTITY, scenario.BOB_IDENTITY
        derived = {
            escrow_id(alice, 0),
            escrow_id(alice, 1),
            escrow_id(bob, 0),
            escrow_id(bob, 1),
        }
        self.assertEqual(len(derived), 4)

    def test_an_escrow_identifier_is_computable_without_the_chain(self) -> None:
        """A wallet derives its own identifiers before the chain writes them."""
        built = Registry()
        expected = escrow_id(scenario.ALICE_IDENTITY, 0)
        actual = built.register(
            scenario.ALICE_IDENTITY, scenario.ALICE_KEY, scenario.ALICE_SIGNER_KEY, 1
        )
        self.assertEqual(actual, expected)


class EscrowLifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = Registry()
        self.registry.register(
            scenario.ALICE_IDENTITY, scenario.ALICE_KEY, scenario.ALICE_SIGNER_KEY, 1
        )

    def test_a_deleted_index_is_never_reissued(self) -> None:
        first = self.registry.create_escrow(scenario.ALICE_IDENTITY)
        self.registry.delete_escrow(scenario.ALICE_IDENTITY, first)
        second = self.registry.create_escrow(scenario.ALICE_IDENTITY)
        self.assertNotEqual(first, second)
        identity = self.registry.identities[scenario.ALICE_IDENTITY]
        self.assertEqual(identity.next_escrow_index, 3)
        self.assertEqual(identity.escrow_count, 2)

    def test_deleting_an_escrow_that_holds_value_is_refused(self) -> None:
        escrow = self.registry.create_escrow(scenario.ALICE_IDENTITY)
        self.registry.accounts[escrow] = (1, 0)
        with self.assertRaises(RegistryError) as raised:
            self.registry.delete_escrow(scenario.ALICE_IDENTITY, escrow)
        self.assertEqual(raised.exception.code, "ESCROW_NOT_EMPTY")

    def test_deleting_an_escrow_removes_its_signers_and_its_account(self) -> None:
        escrow = self.registry.create_escrow(scenario.ALICE_IDENTITY)
        self.registry.add_signer(escrow, scenario.ALICE_SECOND_SIGNER_KEY)
        self.registry.delete_escrow(scenario.ALICE_IDENTITY, escrow)
        self.assertNotIn(escrow, self.registry.accounts)
        self.assertNotIn(
            signer_id(scenario.ALICE_SECOND_SIGNER_KEY), self.registry.signers
        )

    def test_an_escrow_may_hold_no_signer(self) -> None:
        escrow = self.registry.create_escrow(scenario.ALICE_IDENTITY)
        self.assertEqual(self.registry.escrows[escrow].signer_count, 0)
        self.assertEqual(self.registry.structural_failures(), [])

    def test_escrows_per_identity_are_not_bounded_by_rule(self) -> None:
        """The founder direction is as many as the person wants."""
        for _ in range(64):
            self.registry.create_escrow(scenario.ALICE_IDENTITY)
        self.assertEqual(
            self.registry.identities[scenario.ALICE_IDENTITY].escrow_count, 65
        )
        self.assertEqual(self.registry.structural_failures(), [])


class SignerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = Registry()
        self.escrow = self.registry.register(
            scenario.ALICE_IDENTITY, scenario.ALICE_KEY, scenario.ALICE_SIGNER_KEY, 1
        )
        self.second = self.registry.create_escrow(scenario.ALICE_IDENTITY)

    def test_a_signer_key_belongs_to_exactly_one_escrow(self) -> None:
        with self.assertRaises(RegistryError) as raised:
            self.registry.add_signer(self.second, scenario.ALICE_SIGNER_KEY)
        self.assertEqual(raised.exception.code, "REPLAY")

    def test_the_chain_resolves_the_escrow_from_the_signer_alone(self) -> None:
        self.assertEqual(
            self.registry.escrow_of_signer(scenario.ALICE_SIGNER_KEY), self.escrow
        )

    def test_an_unknown_key_authorizes_nothing(self) -> None:
        with self.assertRaises(RegistryError) as raised:
            self.registry.escrow_of_signer(bytes.fromhex("fe" * 32))
        self.assertEqual(raised.exception.code, "SIGNER_NOT_FOUND")

    def test_revocation_is_immediate_and_total(self) -> None:
        self.registry.revoke_signer(self.escrow, signer_id(scenario.ALICE_SIGNER_KEY))
        with self.assertRaises(RegistryError):
            self.registry.escrow_of_signer(scenario.ALICE_SIGNER_KEY)

    def test_a_signer_cannot_be_revoked_from_another_escrow(self) -> None:
        with self.assertRaises(RegistryError) as raised:
            self.registry.revoke_signer(
                self.second, signer_id(scenario.ALICE_SIGNER_KEY)
            )
        self.assertEqual(raised.exception.code, "UNAUTHORIZED")

    def test_the_signer_bound_is_sixteen(self) -> None:
        for index in range(c.MAX_SIGNERS_PER_ESCROW - 1):
            self.registry.add_signer(self.escrow, bytes([index + 1]) * 32)
        with self.assertRaises(RegistryError) as raised:
            self.registry.add_signer(self.escrow, bytes([0xF0]) * 32)
        self.assertEqual(raised.exception.code, "SIGNER_LIMIT")


class RecoveryTest(unittest.TestCase):
    """The path the whole pivot exists to make work.

    A person who has lost every signer proves their identity, assigns a fresh
    one to an escrow that already holds value, and revokes the lost one. Nothing
    about it is a special transaction, which is the point.
    """

    def setUp(self) -> None:
        self.registry = Registry()
        self.escrow = self.registry.register(
            scenario.MARIA_IDENTITY,
            scenario.MARIA_KEY,
            scenario.MARIA_LOST_SIGNER_KEY,
            1,
        )

    def test_the_escrow_already_holds_value(self) -> None:
        """The entry airdrop is what makes recovery need no external funding."""
        balance, _nonce = self.registry.accounts[self.escrow]
        self.assertEqual(balance, c.VERIFIED_USER_DAILY_ATOMIC)

    def test_a_new_signer_is_assigned_with_no_key_at_all(self) -> None:
        identity = self.registry.require_identity(
            scenario.MARIA_IDENTITY, scenario.MARIA_KEY
        )
        self.assertEqual(identity.hub_public_key, scenario.MARIA_KEY)
        self.registry.add_signer(self.escrow, scenario.MARIA_NEW_SIGNER_KEY)
        self.assertEqual(
            self.registry.escrow_of_signer(scenario.MARIA_NEW_SIGNER_KEY), self.escrow
        )

    def test_the_lost_signer_is_revoked_afterwards(self) -> None:
        self.registry.add_signer(self.escrow, scenario.MARIA_NEW_SIGNER_KEY)
        self.registry.revoke_signer(
            self.escrow, signer_id(scenario.MARIA_LOST_SIGNER_KEY)
        )
        self.assertEqual(self.registry.escrows[self.escrow].signer_count, 1)
        self.assertEqual(self.registry.structural_failures(), [])

    def test_a_wrong_header_key_cannot_act_for_the_identity(self) -> None:
        with self.assertRaises(RegistryError) as raised:
            self.registry.require_identity(
                scenario.MARIA_IDENTITY, bytes.fromhex("00" * 32)
            )
        self.assertEqual(raised.exception.code, "UNAUTHORIZED")

    def test_recovery_is_not_a_re_registration(self) -> None:
        with self.assertRaises(RegistryError) as raised:
            self.registry.register(
                scenario.MARIA_IDENTITY,
                scenario.MARIA_KEY,
                bytes.fromhex("ab" * 32),
                2,
            )
        self.assertEqual(raised.exception.code, "REPLAY")


class PostureTest(unittest.TestCase):
    def test_a_new_escrow_is_strict_by_default(self) -> None:
        registry = Registry()
        escrow = registry.register(
            scenario.ALICE_IDENTITY, scenario.ALICE_KEY, scenario.ALICE_SIGNER_KEY, 1
        )
        posture = registry.escrows[escrow].posture
        self.assertTrue(posture.requires_confirmation)
        self.assertEqual(posture.min_amount_atomic, 0)
        self.assertEqual(posture.exempt_slot_mask, 0)
        self.assertTrue(requires_confirmation(posture, 0, 0))

    def test_each_disjunct_alone_is_a_relaxation(self) -> None:
        strict = Posture()
        for proposed in (
            Posture(requires_confirmation=False),
            Posture(min_amount_atomic=1),
            Posture(exempt_slot_mask=0b1),
        ):
            with self.subTest(proposed):
                self.assertTrue(relaxes(strict, proposed))

    def test_a_mixed_change_that_weakens_anything_is_a_relaxation(self) -> None:
        """Rounding in this direction is deliberate: the failure that matters is
        a stolen key weakening a protection."""
        current = Posture(min_amount_atomic=10, exempt_slot_mask=0b10)
        proposed = Posture(min_amount_atomic=5, exempt_slot_mask=0b11)
        self.assertTrue(relaxes(current, proposed))

    def test_tightening_every_field_is_not_a_relaxation(self) -> None:
        current = Posture(
            requires_confirmation=False, min_amount_atomic=10, exempt_slot_mask=0b11
        )
        proposed = Posture(
            requires_confirmation=True, min_amount_atomic=5, exempt_slot_mask=0b1
        )
        self.assertFalse(relaxes(current, proposed))

    def test_a_time_window_is_a_height_and_never_a_clock(self) -> None:
        self.assertEqual(slot_of(0), 0)
        self.assertEqual(slot_of(c.SLOT_BLOCKS), 1)
        self.assertEqual(slot_of(c.CYCLE_BLOCKS - 1), c.SLOTS_PER_WINDOW - 1)
        self.assertEqual(slot_of(c.CYCLE_BLOCKS), 0)

    def test_an_unchanged_posture_is_refused(self) -> None:
        registry = Registry()
        escrow = registry.register(
            scenario.ALICE_IDENTITY, scenario.ALICE_KEY, scenario.ALICE_SIGNER_KEY, 1
        )
        with self.assertRaises(RegistryError) as raised:
            registry.set_posture(escrow, Posture())
        self.assertEqual(raised.exception.code, "REPLAY")


class StructuralInvariantTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = scenario.registry()

    def test_the_fixture_satisfies_every_invariant(self) -> None:
        self.assertEqual(self.registry.structural_failures(), [])

    def test_every_account_is_an_escrow(self) -> None:
        self.assertEqual(set(self.registry.accounts), set(self.registry.escrows))

    def test_an_account_with_no_escrow_is_a_failure(self) -> None:
        """The invariant this version exists for, checked by breaking it."""
        self.registry.accounts[bytes.fromhex("99" * 32)] = (1, 0)
        self.assertIn(
            "the account map and the escrow set have different keys",
            self.registry.structural_failures(),
        )

    def test_a_lost_escrow_count_is_a_failure(self) -> None:
        from dataclasses import replace

        identity = self.registry.identities[scenario.ALICE_IDENTITY]
        self.registry.identities[scenario.ALICE_IDENTITY] = replace(
            identity, escrow_count=identity.escrow_count + 1
        )
        self.assertIn(
            "an identity's escrow count is not its escrow entries",
            self.registry.structural_failures(),
        )

    def test_a_lost_signer_count_is_a_failure(self) -> None:
        from dataclasses import replace

        entry = self.registry.escrows[scenario.ALICE_FIRST_ESCROW]
        self.registry.escrows[scenario.ALICE_FIRST_ESCROW] = replace(
            entry, signer_count=entry.signer_count + 1
        )
        self.assertIn(
            "an escrow's signer count is not its signer entries",
            self.registry.structural_failures(),
        )


if __name__ == "__main__":
    unittest.main()
