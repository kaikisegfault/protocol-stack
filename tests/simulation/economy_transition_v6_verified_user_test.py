#!/usr/bin/env python3
"""Channel 8: the derived rate, the entry airdrop, and what the cap forfeits.

The rate is the strongest thing in this contract that nobody chose: ADR 0042
supplied a population and a period, the accepted manifest supplied a cap, and
those three determine the fourth to the atomic unit. This module tests that the
derivation is a derivation rather than a constant with a comment, and that
forfeiture is permanent rather than deferred.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v6 import contract as c
from simulation.economy_transition_v6 import scenario, verified_user
from simulation.economy_transition_v6.identity import Registry
from simulation.founder_economy_v2 import contract as manifest


class RateTest(unittest.TestCase):
    def test_the_rate_is_derived_from_three_founder_supplied_figures(self) -> None:
        self.assertEqual(verified_user.derived_daily_atomic(), 171_000_000)

    def test_the_three_figures_reproduce_the_accepted_cap_exactly(self) -> None:
        self.assertEqual(
            c.VERIFIED_USER_POPULATION
            * c.VERIFIED_USER_CYCLES
            * verified_user.derived_daily_atomic(),
            manifest.CHANNEL_CAPS["hub_verified_user_incentives"],
        )

    def test_the_cap_comes_from_the_accepted_manifest(self) -> None:
        """Not a second copy of a founder-directed figure."""
        self.assertEqual(
            c.VERIFIED_USER_CHANNEL_CAP,
            manifest.CHANNEL_CAPS["hub_verified_user_incentives"],
        )

    def test_a_730_cycle_period_would_leave_a_remainder(self) -> None:
        """Which is what fixes the period at 731 rather than making it a choice."""
        cap = c.VERIFIED_USER_CHANNEL_CAP
        self.assertNotEqual(cap % (c.VERIFIED_USER_POPULATION * 730), 0)
        self.assertEqual(cap % (c.VERIFIED_USER_POPULATION * 731), 0)

    def test_the_period_matches_a_seats_issuance_period(self) -> None:
        self.assertEqual(c.VERIFIED_USER_CYCLES, c.ISSUANCE_CYCLES_PER_SEAT)


class EntryAirdropTest(unittest.TestCase):
    def test_registration_credits_the_first_day(self) -> None:
        registry = Registry()
        escrow = registry.register(
            scenario.ALICE_IDENTITY, scenario.ALICE_KEY, scenario.ALICE_SIGNER_KEY, 1
        )
        balance, nonce = registry.accounts[escrow]
        self.assertEqual(balance, c.VERIFIED_USER_DAILY_ATOMIC)
        self.assertEqual(nonce, 0)

    def test_the_airdrop_is_paid_once_per_identity(self) -> None:
        registry = Registry()
        registry.register(
            scenario.ALICE_IDENTITY, scenario.ALICE_KEY, scenario.ALICE_SIGNER_KEY, 1
        )
        enrollment = registry.enrollments[scenario.ALICE_IDENTITY]
        self.assertEqual(enrollment.issued_atomic, c.VERIFIED_USER_DAILY_ATOMIC)
        self.assertEqual(registry.enrolled_count, 1)

    def test_a_registration_past_the_population_pays_nothing(self) -> None:
        """After the first million the entry problem does not recur, and the
        registration must still succeed — which is why it is fee-exempt rather
        than credit-before-fee."""
        registry = Registry()
        registry.enrolled_count = c.VERIFIED_USER_POPULATION
        escrow = registry.register(
            scenario.BOB_IDENTITY, scenario.BOB_KEY, scenario.BOB_SIGNER_KEY, 1
        )
        balance, _nonce = registry.accounts[escrow]
        self.assertEqual(balance, 0)
        self.assertNotIn(scenario.BOB_IDENTITY, registry.enrollments)
        self.assertEqual(registry.enrolled_count, c.VERIFIED_USER_POPULATION)


class CollectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.height = 5 * c.CYCLE_BLOCKS
        self.enrollment = verified_user.enroll(self.height)

    def _at(self, window: int) -> verified_user.Collection:
        return verified_user.collect(self.enrollment, window * c.CYCLE_BLOCKS)

    def test_nothing_is_collectable_in_the_enrollment_window(self) -> None:
        self.assertEqual(self._at(5).count, 0)
        self.assertEqual(self._at(6).count, 0)

    def test_one_completed_window_is_collectable(self) -> None:
        collection = self._at(7)
        self.assertEqual(collection.count, 1)
        self.assertEqual(collection.amount_atomic, c.VERIFIED_USER_DAILY_ATOMIC)

    def test_the_cap_bounds_a_collection_at_thirty_windows(self) -> None:
        collection = self._at(5 + 200)
        self.assertEqual(collection.count, c.MINT_ACCUMULATION_CAP)

    def test_forfeiture_is_permanent_rather_than_deferred(self) -> None:
        """The mark advances to the collectable end rather than to the walk's
        end, which is what makes the older windows unreachable afterwards."""
        collection = self._at(5 + 41)
        self.assertEqual(collection.forfeited_windows, 10)
        applied = verified_user.applied(self.enrollment, collection)
        self.assertEqual(applied.minted_through_window, collection.collectable_end)
        again = verified_user.collect(applied, (5 + 41) * c.CYCLE_BLOCKS)
        self.assertEqual(again.count, 0)

    def test_a_complete_period_issues_the_whole_allocation_and_no_more(self) -> None:
        walking = self.enrollment
        for window in range(6, 5 + c.VERIFIED_USER_CYCLES + 2):
            walking = verified_user.applied(
                walking, verified_user.collect(walking, window * c.CYCLE_BLOCKS)
            )
        self.assertEqual(
            walking.issued_atomic, verified_user.maximum_issuance_per_identity()
        )
        beyond = verified_user.collect(walking, (5 + 900) * c.CYCLE_BLOCKS)
        self.assertEqual(beyond.count, 0)

    def test_a_neglectful_person_ends_below_the_maximum(self) -> None:
        """Which is the founder answer: the value is never issued, and total
        supply ends below the cap by exactly what was not collected."""
        walking = self.enrollment
        for window in range(6, 5 + c.VERIFIED_USER_CYCLES + 2, 40):
            walking = verified_user.applied(
                walking, verified_user.collect(walking, window * c.CYCLE_BLOCKS)
            )
        self.assertLess(
            walking.issued_atomic, verified_user.maximum_issuance_per_identity()
        )

    def test_the_walk_is_arithmetic_rather_than_iteration(self) -> None:
        """Every window in the period pays the same amount unconditionally, so a
        collection after any gap costs the same."""
        collection = self._at(5 + 10_000)
        self.assertEqual(
            collection.amount_atomic,
            collection.count * c.VERIFIED_USER_DAILY_ATOMIC,
        )

    def test_the_period_ends_at_seven_hundred_and_thirty_windows_after_entry(self) -> None:
        self.assertEqual(verified_user.last_window(self.enrollment), 5 + 730)


class ChannelIndependenceTest(unittest.TestCase):
    def test_the_channel_binds_no_settlement_module(self) -> None:
        """The channel is independent of uptime measurement and of the dispute
        lag, because eligibility is being verified rather than being active.

        Checked against the module's bound names rather than its source text: a
        docstring that explains the difference mentions assignment, and a text
        search cannot tell an explanation from a dependency.
        """
        bound = {
            getattr(value, "__module__", None) or getattr(value, "__name__", "")
            for value in vars(verified_user).values()
        }
        for name in bound:
            if not name:
                continue
            self.assertNotIn("settlement", name)
            self.assertNotIn("uptime_measurement", name)
            self.assertNotIn("founder_economy", name)

    def test_a_collection_depends_only_on_the_enrollment_and_the_height(self) -> None:
        """Two chains that disagree about every seat agree about this mint."""
        import inspect

        signature = inspect.signature(verified_user.collect)
        self.assertEqual(list(signature.parameters), ["enrollment", "height"])

    def test_channel_eight_left_the_reserved_direct_issue_set(self) -> None:
        self.assertNotIn(c.VERIFIED_USER_CHANNEL, c.DIRECT_ISSUE_CHANNELS)
        self.assertEqual(c.DIRECT_ISSUE_CHANNELS, (5, 6, 9))


if __name__ == "__main__":
    unittest.main()
