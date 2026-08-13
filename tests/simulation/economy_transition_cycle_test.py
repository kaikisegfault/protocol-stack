#!/usr/bin/env python3
"""The per-cycle assignment: the winner rule, the split, and the two bitmaps."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition import contract as c
from simulation.economy_transition import scenario, state, winners
from simulation.founder_economy_v3 import contract as economy
from simulation.founder_economy_v3 import uptime


def as_record(uptime_by_seat: dict[int, int]) -> dict:
    """The fixture expressed as the accepted model's record shape."""
    return {
        "entries": [
            {"seat_id": seat, "uptime_seconds": uptime_by_seat[seat]}
            for seat in sorted(uptime_by_seat)
        ]
    }


class WinnerRuleTest(unittest.TestCase):
    def test_the_winner_set_excludes_failed_and_lower_uptime_seats(self) -> None:
        derived = scenario.cycle_winners()
        self.assertEqual(derived, (0, 4))
        self.assertNotIn(7, derived, "a failed seat never rewards another failed seat")
        self.assertNotIn(c.MAX_SEAT_ID, derived, "only the maximum uptime wins")

    def test_the_rule_agrees_with_the_accepted_economy_model(self) -> None:
        """The encoding must not hold a second opinion about who wins."""
        self.assertEqual(
            scenario.cycle_winners(),
            uptime.winner_seats(as_record(scenario.CYCLE_UPTIME)),
        )

    def test_the_fixtures_met_flags_are_the_accepted_threshold(self) -> None:
        for seat, seconds in scenario.CYCLE_UPTIME.items():
            with self.subTest(seat):
                self.assertEqual(scenario.CYCLE_MET[seat], uptime.met_cycle(seconds))

    def test_restricting_before_the_maximum_is_what_makes_the_rule_right(self) -> None:
        """Taking the maximum first would return an empty set here."""
        self.assertEqual(
            winners.derive_winner_set({0: 86_400, 1: 64_800}, {0: False, 1: True}),
            (1,),
        )

    def test_a_cycle_no_seat_met_has_an_empty_winner_set(self) -> None:
        self.assertEqual(
            winners.derive_winner_set({0: 3_600, 1: 7_200}, {0: False, 1: False}), ()
        )


class SplitTest(unittest.TestCase):
    """Every leg is divided, not only the operator leg.

    A failed cycle's whole permission moves to that cycle's winners, so the
    escrows and the System Creator are paid at the winner's mint and each of
    their legs can leave a remainder.
    """

    def test_every_leg_is_divided_and_the_split_conserves(self) -> None:
        for count in (1, 2, 3, 7, 13, 100, 99_999):
            with self.subTest(count):
                shares, carries = winners.split_permission(count)
                self.assertEqual(sorted(shares), sorted(carries))
                for channel, amount in c.BASE_PERMISSION_LEGS:
                    self.assertEqual(
                        shares[channel] * count + carries[channel], amount
                    )
                    self.assertLess(carries[channel], count)

    def test_an_exact_split_carries_no_remainder(self) -> None:
        shares, carries = winners.split_permission(2)
        self.assertEqual(shares[c.FOUNDER_OPERATOR_CHANNEL], 17_100_000_000)
        self.assertEqual(set(carries.values()), {0})

    def test_an_inexact_split_carries_the_integer_remainder(self) -> None:
        shares, carries = winners.split_permission(7)
        self.assertEqual(shares[c.FOUNDER_OPERATOR_CHANNEL], 4_885_714_285)
        self.assertEqual(carries[c.FOUNDER_OPERATOR_CHANNEL], 5)

    def test_an_empty_winner_set_carries_the_whole_permission(self) -> None:
        shares, carries = winners.split_permission(0)
        self.assertEqual(set(shares.values()), {0})
        self.assertEqual(sum(carries.values()), c.BASE_PERMISSION_TOTAL)

    def test_the_legs_are_the_founder_directed_ones(self) -> None:
        self.assertEqual(c.BASE_PERMISSION_TOTAL, 57_430_000_000)
        self.assertEqual(
            dict(c.BASE_PERMISSION_LEGS)[c.FOUNDER_OPERATOR_CHANNEL],
            economy.FOUNDER_OPERATOR_LEG,
        )


class BitmapTest(unittest.TestCase):
    """Met and won are separate facts, so they are separate bitmaps."""

    def setUp(self) -> None:
        self.derived = scenario.cycle_winners()
        self.met = state.bitmap(
            [scenario.CYCLE_MET[seat] for seat in scenario.IN_SCOPE_SEATS]
        )
        self.won = state.bitmap(
            [seat in self.derived for seat in scenario.IN_SCOPE_SEATS]
        )

    def test_the_two_bitmaps_differ(self) -> None:
        self.assertNotEqual(self.met, self.won)

    def test_a_seat_may_meet_a_cycle_without_winning_it(self) -> None:
        index = scenario.IN_SCOPE_SEATS.index(c.MAX_SEAT_ID)
        self.assertTrue(state.bit_is_set(self.met, index))
        self.assertFalse(state.bit_is_set(self.won, index))

    def test_every_winner_also_met_the_cycle(self) -> None:
        for index in range(len(scenario.IN_SCOPE_SEATS)):
            if state.bit_is_set(self.won, index):
                with self.subTest(index):
                    self.assertTrue(state.bit_is_set(self.met, index))

    def test_the_failed_seat_is_set_in_neither(self) -> None:
        index = scenario.IN_SCOPE_SEATS.index(7)
        self.assertFalse(state.bit_is_set(self.met, index))
        self.assertFalse(state.bit_is_set(self.won, index))

    def test_the_assignment_entry_has_its_derived_width(self) -> None:
        key, value = scenario.cycle_assignment_entry()
        self.assertEqual(len(key), c.ENTRY_KEY_BYTES[c.CYCLE_ASSIGNMENT_ENTRY])
        self.assertEqual(
            len(value),
            c.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES + len(self.met) + len(self.won),
        )

    def test_one_record_replaces_a_write_per_winner(self) -> None:
        """At capacity, 25,033 bytes once instead of 100,000 credits per cycle."""
        at_capacity = (
            c.ENTRY_KEY_BYTES[c.CYCLE_ASSIGNMENT_ENTRY]
            + c.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES
            + 2 * (c.FOUNDER_SEAT_CAPACITY // 8)
        )
        self.assertEqual(at_capacity, 25_033)


class CanonicalWinnerListTest(unittest.TestCase):
    def test_an_uncanonical_list_is_refused_rather_than_normalised(self) -> None:
        for candidate in ((4, 0), (0, 0), (c.FOUNDER_SEAT_CAPACITY,)):
            with self.subTest(candidate):
                with self.assertRaises(winners.InvalidWinnerSet):
                    winners.require_canonical(candidate)

    def test_the_derived_set_is_canonical(self) -> None:
        winners.require_canonical(scenario.cycle_winners())

    def test_a_full_population_tie_is_canonical(self) -> None:
        """The constitution expects a perfect cycle to tie nearly everyone."""
        winners.require_canonical(tuple(range(c.FOUNDER_SEAT_CAPACITY)))


if __name__ == "__main__":
    unittest.main()
