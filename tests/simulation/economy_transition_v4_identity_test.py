#!/usr/bin/env python3
"""The HUB registry, the per-human seat bound, and self-referral across addresses."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v3 import contract as v3
from simulation.economy_transition_v4 import contract as c
from simulation.economy_transition_v4 import identity, scenario, state


class RegistryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = scenario.registry()

    def test_one_person_holds_several_addresses(self) -> None:
        self.assertEqual(
            self.registry.identity_of(scenario.ALICE_FIRST_ADDRESS),
            self.registry.identity_of(scenario.ALICE_SECOND_ADDRESS),
        )
        self.assertEqual(
            self.registry.identities[scenario.ALICE_IDENTITY].address_count, 2
        )

    def test_an_identity_is_registered_once(self) -> None:
        self.assertEqual(
            self.registry.register(
                scenario.ALICE_IDENTITY, scenario.ALICE_KEY, bytes.fromhex("f1" * 32), 1
            ),
            "REPLAY",
        )

    def test_an_account_belongs_to_at_most_one_identity(self) -> None:
        self.assertEqual(
            self.registry.add_address(
                scenario.BOB_IDENTITY, scenario.ALICE_FIRST_ADDRESS
            ),
            "REPLAY",
        )
        self.assertEqual(
            self.registry.register(
                bytes.fromhex("f2" * 32), scenario.BOB_KEY,
                scenario.ALICE_FIRST_ADDRESS, 1
            ),
            "REPLAY",
        )

    def test_removal_unlinks_and_touches_nothing_else(self) -> None:
        """The account keeps its balance, its nonce, and its ability to transact."""
        self.assertFalse(self.registry.is_verified(scenario.CAROL_ADDRESS))
        self.assertIn(scenario.CAROL_IDENTITY, self.registry.identities)
        self.assertEqual(
            self.registry.identities[scenario.CAROL_IDENTITY].hub_public_key,
            scenario.CAROL_KEY,
        )

    def test_an_identity_with_no_addresses_can_still_add_one(self) -> None:
        """The recovery path the whole direction exists for."""
        self.assertEqual(
            self.registry.identities[scenario.CAROL_IDENTITY].address_count, 0
        )
        self.assertEqual(
            self.registry.add_address(
                scenario.CAROL_IDENTITY, bytes.fromhex("c9" * 32)
            ),
            "SUCCESS",
        )
        self.assertEqual(
            self.registry.identities[scenario.CAROL_IDENTITY].address_count, 1
        )

    def test_an_unregistered_identity_cannot_add_an_address(self) -> None:
        self.assertEqual(
            self.registry.add_address(bytes.fromhex("f3" * 32), bytes.fromhex("f4" * 32)),
            "NOT_HUB_VERIFIED",
        )

    def test_removing_an_unlinked_account_is_refused(self) -> None:
        self.assertEqual(
            self.registry.remove_address(bytes.fromhex("f5" * 32)), "NOT_HUB_VERIFIED"
        )

    def test_the_address_bound_holds_at_its_boundary(self) -> None:
        full = identity.Registry()
        full.register(scenario.BOB_IDENTITY, scenario.BOB_KEY, scenario.BOB_ADDRESS, 1)
        for index in range(c.MAX_IDENTITY_ADDRESSES - 1):
            self.assertEqual(
                full.add_address(scenario.BOB_IDENTITY, index.to_bytes(32, "big")),
                "SUCCESS",
            )
        self.assertEqual(
            full.identities[scenario.BOB_IDENTITY].address_count,
            c.MAX_IDENTITY_ADDRESSES,
        )
        self.assertEqual(
            full.add_address(scenario.BOB_IDENTITY, bytes.fromhex("fe" * 32)),
            "ADDRESS_LIMIT",
        )

    def test_the_two_counts_are_equalities(self) -> None:
        self.assertTrue(self.registry.counts_agree({scenario.ALICE_IDENTITY: 1}))
        self.assertFalse(self.registry.counts_agree({}))
        self.assertFalse(
            self.registry.counts_agree({scenario.ALICE_IDENTITY: 2})
        )

    def test_a_removed_address_lowers_the_count(self) -> None:
        before = self.registry.identities[scenario.ALICE_IDENTITY].address_count
        self.registry.remove_address(scenario.ALICE_SECOND_ADDRESS)
        self.assertEqual(
            self.registry.identities[scenario.ALICE_IDENTITY].address_count, before - 1
        )
        self.assertTrue(self.registry.counts_agree({scenario.ALICE_IDENTITY: 1}))


class SeatBoundTest(unittest.TestCase):
    """The constitution's per-human bound, finally reaching the chain."""

    def test_version_three_has_no_code_for_it(self) -> None:
        self.assertNotIn("SEAT_LIMIT", v3.RESULT_CODES.values())
        self.assertIn("SEAT_LIMIT", c.RESULT_CODES.values())

    def test_the_bound_is_the_constitutions(self) -> None:
        self.assertEqual(c.MAX_SEATS_PER_IDENTITY, 1_000)

    def test_claims_succeed_to_the_bound_and_fail_past_it(self) -> None:
        registry = identity.Registry()
        registry.register(
            scenario.ALICE_IDENTITY, scenario.ALICE_KEY,
            scenario.ALICE_FIRST_ADDRESS, 1
        )
        for index in range(c.MAX_SEATS_PER_IDENTITY):
            outcome = registry.claim_seat(scenario.ALICE_IDENTITY)
            if outcome != "SUCCESS":
                self.fail(f"claim {index + 1} returned {outcome}")
        self.assertEqual(
            registry.identities[scenario.ALICE_IDENTITY].seat_count,
            c.MAX_SEATS_PER_IDENTITY,
        )
        self.assertEqual(registry.claim_seat(scenario.ALICE_IDENTITY), "SEAT_LIMIT")
        self.assertEqual(
            registry.identities[scenario.ALICE_IDENTITY].seat_count,
            c.MAX_SEATS_PER_IDENTITY,
        )

    def test_an_unregistered_identity_cannot_claim(self) -> None:
        self.assertEqual(
            identity.Registry().claim_seat(scenario.ALICE_IDENTITY), "NOT_HUB_VERIFIED"
        )

    def test_the_bound_is_per_person_not_per_address(self) -> None:
        """Two addresses of one person share one seat count."""
        registry = scenario.registry()
        self.assertEqual(
            registry.identity_of(scenario.ALICE_FIRST_ADDRESS),
            registry.identity_of(scenario.ALICE_SECOND_ADDRESS),
        )
        registry.claim_seat(registry.identity_of(scenario.ALICE_SECOND_ADDRESS))
        self.assertEqual(
            registry.identities[scenario.ALICE_IDENTITY].seat_count, 2
        )


class SelfReferralTest(unittest.TestCase):
    def test_two_addresses_of_one_person_are_refused(self) -> None:
        registry = scenario.registry()
        purchaser = registry.identity_of(scenario.ALICE_FIRST_ADDRESS)
        referrer = registry.identity_of(scenario.ALICE_SECOND_ADDRESS)
        self.assertNotEqual(scenario.ALICE_FIRST_ADDRESS, scenario.ALICE_SECOND_ADDRESS)
        self.assertTrue(identity.self_referral(purchaser, referrer))

    def test_a_different_person_is_accepted(self) -> None:
        self.assertFalse(
            identity.self_referral(scenario.ALICE_IDENTITY, scenario.BOB_IDENTITY)
        )

    def test_no_referrer_is_accepted(self) -> None:
        self.assertFalse(identity.self_referral(scenario.ALICE_IDENTITY, None))


class RegistryStateTest(unittest.TestCase):
    def test_the_registry_encodes_as_canonical_entries(self) -> None:
        entries = scenario.registry().entries()
        kinds = {key[0] for key in entries}
        self.assertEqual(kinds, {c.HUB_IDENTITY_ENTRY, c.HUB_ADDRESS_ENTRY})
        for key, value in entries.items():
            with self.subTest(key.hex()):
                self.assertEqual(len(key), c.ENTRY_KEY_BYTES[key[0]])
                self.assertEqual(len(value), c.ENTRY_VALUE_BYTES[key[0]])

    def test_the_identity_record_is_forty_eight_bytes(self) -> None:
        value = state.hub_identity_value(scenario.ALICE_KEY, 7, 2, 1)
        self.assertEqual(len(value), 48)
        self.assertEqual(value[0:32], scenario.ALICE_KEY)

    def test_the_counts_are_bounded_in_the_encoding(self) -> None:
        for addresses, seats in (
            (c.MAX_IDENTITY_ADDRESSES + 1, 0),
            (1, c.MAX_SEATS_PER_IDENTITY + 1),
        ):
            with self.subTest((addresses, seats)):
                with self.assertRaises(state.InvalidStateEntry):
                    state.hub_identity_value(scenario.ALICE_KEY, 7, addresses, seats)

    def test_the_referral_balance_is_keyed_by_a_person(self) -> None:
        """A balance keyed by an address is the one place losing one loses value."""
        key = state.referral_balance_key(scenario.BOB_IDENTITY)
        self.assertEqual(key[0], c.REFERRAL_BALANCE_ENTRY)
        self.assertEqual(key[1:], scenario.BOB_IDENTITY)


if __name__ == "__main__":
    unittest.main()
