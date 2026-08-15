#!/usr/bin/env python3
"""Kind 11's transition: recovery, and the squatting the correction closes.

The registry is version four's and is exercised by that version's own tests.
What is tested here is the entry point version five adds — the one with no
parameter through which an account other than the sender's could be named — and
the two end-to-end consequences it has.
"""

from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v5 import contract as c
from simulation.economy_transition_v5 import envelope, identity, scenario


class AddAddressTransitionTest(unittest.TestCase):
    def test_the_linked_account_is_always_the_sender(self) -> None:
        for transaction in (
            scenario.recovery_transaction(),
            scenario.attacker_transaction(),
        ):
            with self.subTest(transaction.sender_public_key[:4].hex()):
                self.assertEqual(
                    identity.linked_account(transaction),
                    envelope.sender_account_id(transaction),
                )

    def test_the_transition_takes_no_account_argument(self) -> None:
        """Squatting is unrepresentable because there is nothing to name it with."""
        parameters = list(
            inspect.signature(identity.apply_add_address).parameters
        )
        self.assertEqual(parameters, ["registry", "transaction"])

    def test_another_kind_is_refused(self) -> None:
        for name in ("hub_remove_address", "hub_register"):
            with self.subTest(name):
                with self.assertRaises(envelope.MalformedTransaction):
                    identity.apply_add_address(
                        scenario.registry(), scenario.transactions()[name]
                    )

    def test_the_rejection_order_is_the_specified_one(self) -> None:
        self.assertEqual(
            c.ADD_ADDRESS_REJECTION_ORDER,
            ("NOT_HUB_VERIFIED", "REPLAY", "ADDRESS_LIMIT", "UNAUTHORIZED"),
        )

    def test_an_unregistered_identity_is_refused_first(self) -> None:
        registry = scenario.registry()
        transaction = scenario.add_address_transaction(
            bytes.fromhex("9a" * 32), scenario.RECOVERY_PUBLIC_KEY
        )
        self.assertEqual(
            identity.apply_add_address(registry, transaction), "NOT_HUB_VERIFIED"
        )

    def test_a_linked_sender_is_a_replay(self) -> None:
        registry = scenario.registry()
        first = scenario.recovery_transaction()
        self.assertEqual(identity.apply_add_address(registry, first), "SUCCESS")
        self.assertEqual(identity.apply_add_address(registry, first), "REPLAY")

    def test_the_address_bound_is_reached_through_the_transition(self) -> None:
        registry = scenario.registry()
        for index in range(c.MAX_IDENTITY_ADDRESSES):
            transaction = scenario.add_address_transaction(
                scenario.CAROL_IDENTITY, index.to_bytes(32, "big")
            )
            outcome = identity.apply_add_address(registry, transaction)
            if outcome != "SUCCESS":
                self.fail(f"addition {index + 1} returned {outcome}")
        overflow = scenario.add_address_transaction(
            scenario.CAROL_IDENTITY, bytes.fromhex("fe" * 32)
        )
        self.assertEqual(
            identity.apply_add_address(registry, overflow), "ADDRESS_LIMIT"
        )


class RecoveryTest(unittest.TestCase):
    """A person with an identity, no linked addresses, and a fresh account."""

    def setUp(self) -> None:
        self.registry = scenario.registry()
        self.transaction = scenario.recovery_transaction()
        self.account = scenario.recovery_account_id()

    def test_the_person_starts_with_nothing_they_can_sign_from(self) -> None:
        self.assertEqual(
            self.registry.identities[scenario.CAROL_IDENTITY].address_count, 0
        )
        self.assertIsNone(self.registry.identity_of(self.account))

    def test_the_addition_succeeds_and_the_counts_stay_equal(self) -> None:
        self.assertEqual(
            identity.apply_add_address(self.registry, self.transaction), "SUCCESS"
        )
        self.assertEqual(
            self.registry.identity_of(self.account), scenario.CAROL_IDENTITY
        )
        self.assertEqual(
            self.registry.identities[scenario.CAROL_IDENTITY].address_count, 1
        )
        self.assertTrue(self.registry.counts_agree({scenario.ALICE_IDENTITY: 1}))

    def test_version_four_could_not_have_named_the_identity(self) -> None:
        """The defect: kind 11's body carried an account where the identity had to be."""
        from simulation.economy_transition_v4 import scenario as v4_scenario

        four = v4_scenario.transactions()["hub_add_address"]
        self.assertEqual(sorted(four.body), ["account_id", "hub_signature"])
        self.assertEqual(
            sorted(self.transaction.body), ["hub_identity_hash", "hub_signature"]
        )


class SquattingTest(unittest.TestCase):
    """The second hole the chosen repair closes, run under both readings."""

    def setUp(self) -> None:
        self.victim = scenario.victim_account_id()

    def test_version_four_permits_linking_a_strangers_account(self) -> None:
        registry = scenario.squatting_registry()
        self.assertEqual(
            identity.version_four_add_address(
                registry, scenario.ATTACKER_IDENTITY, self.victim
            ),
            "SUCCESS",
        )
        self.assertEqual(
            registry.identity_of(self.victim), scenario.ATTACKER_IDENTITY
        )

    def test_version_four_then_locks_the_victim_out_permanently(self) -> None:
        registry = scenario.squatting_registry()
        identity.version_four_add_address(
            registry, scenario.ATTACKER_IDENTITY, self.victim
        )
        self.assertEqual(
            registry.register(
                scenario.VICTIM_IDENTITY,
                scenario.VICTIM_HUB_KEY,
                self.victim,
                scenario.REGISTRATION_HEIGHT,
            ),
            "REPLAY",
        )

    def test_version_five_links_only_the_attackers_own_account(self) -> None:
        registry = scenario.squatting_registry()
        transaction = scenario.attacker_transaction()
        self.assertEqual(
            identity.apply_add_address(registry, transaction), "SUCCESS"
        )
        self.assertEqual(
            registry.identity_of(scenario.attacker_account_id()),
            scenario.ATTACKER_IDENTITY,
        )
        self.assertIsNone(registry.identity_of(self.victim))

    def test_the_victim_can_still_register(self) -> None:
        registry = scenario.squatting_registry()
        identity.apply_add_address(registry, scenario.attacker_transaction())
        self.assertEqual(
            registry.register(
                scenario.VICTIM_IDENTITY,
                scenario.VICTIM_HUB_KEY,
                self.victim,
                scenario.REGISTRATION_HEIGHT,
            ),
            "SUCCESS",
        )
        self.assertEqual(
            registry.identity_of(self.victim), scenario.VICTIM_IDENTITY
        )


if __name__ == "__main__":
    unittest.main()
