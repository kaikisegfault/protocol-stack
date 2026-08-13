#!/usr/bin/env python3
"""The performance reallocation commitment and its agreement with the economy model."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition import contract as c
from simulation.economy_transition import scenario, winners
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
        derived = scenario.window_winners()
        self.assertEqual(derived, (0, 4))
        self.assertNotIn(7, derived, "a failed seat never rewards another failed seat")
        self.assertNotIn(c.MAX_SEAT_ID, derived, "only the maximum uptime wins")

    def test_the_rule_agrees_with_the_accepted_economy_model(self) -> None:
        """The encoding must not hold a second opinion about who wins.

        The two implementations reach the set from different inputs: this one
        from a window's met bitmap and uptimes, the accepted model from a
        supplied record. A value they both reach has been derived twice.
        """
        self.assertEqual(
            scenario.window_winners(),
            uptime.winner_seats(as_record(scenario.WINDOW_UPTIME)),
        )

    def test_the_fixtures_met_flags_are_the_accepted_threshold(self) -> None:
        for seat, seconds in scenario.WINDOW_UPTIME.items():
            with self.subTest(seat):
                self.assertEqual(
                    scenario.WINDOW_MET[seat], uptime.met_cycle(seconds)
                )

    def test_restricting_before_the_maximum_is_what_makes_the_rule_right(self) -> None:
        """Taking the maximum first would return an empty set here."""
        uptimes = {0: 86_400, 1: 64_800}
        met = {0: False, 1: True}
        self.assertEqual(winners.derive_winner_set(uptimes, met), (1,))

    def test_a_window_no_seat_met_has_an_empty_winner_set(self) -> None:
        uptimes = {0: 3_600, 1: 7_200}
        met = {0: False, 1: False}
        self.assertEqual(winners.derive_winner_set(uptimes, met), ())


class CommitmentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.derived = scenario.window_winners()
        self.root = winners.winner_root(self.derived)
        self.count = len(self.derived)

    def test_the_derived_set_reproduces_its_commitment(self) -> None:
        self.assertTrue(
            winners.matches_commitment(self.derived, self.root, self.count)
        )

    def test_a_reordered_short_long_or_substituted_list_is_refused(self) -> None:
        candidates = {
            "reordered": tuple(reversed(self.derived)),
            "short_by_one": self.derived[:-1],
            "long_by_one": tuple(sorted(self.derived + (c.MAX_SEAT_ID,))),
            "substituted": tuple(sorted(self.derived[:-1] + (self.derived[-1] + 1,))),
            "empty": (),
        }
        for name, candidate in candidates.items():
            with self.subTest(name):
                self.assertFalse(
                    winners.matches_commitment(candidate, self.root, self.count)
                )

    def test_a_list_correct_for_another_window_is_refused(self) -> None:
        other = winners.derive_winner_set({0: 86_400, 9: 86_400}, {0: True, 9: True})
        self.assertNotEqual(other, self.derived)
        self.assertFalse(winners.matches_commitment(other, self.root, self.count))

    def test_the_empty_set_has_its_own_committed_root(self) -> None:
        empty_root = winners.winner_root(())
        self.assertNotEqual(empty_root, self.root)
        self.assertTrue(winners.matches_commitment((), empty_root, 0))

    def test_an_uncanonical_list_is_refused_rather_than_normalised(self) -> None:
        for candidate in ((4, 0), (0, 0), (c.FOUNDER_SEAT_CAPACITY,)):
            with self.subTest(candidate):
                with self.assertRaises(winners.InvalidWinnerSet):
                    winners.winner_root(candidate)

    def test_a_list_at_the_seat_capacity_is_committed(self) -> None:
        """The fully tied window the constitution expects to be ordinary."""
        full = tuple(range(c.FOUNDER_SEAT_CAPACITY))
        root = winners.winner_root(full)
        self.assertEqual(len(root), 32)
        self.assertTrue(winners.matches_commitment(full, root, len(full)))


class SplitTest(unittest.TestCase):
    def test_an_exact_split_carries_no_remainder(self) -> None:
        self.assertEqual(winners.equal_split(34_200_000_000, 2), (17_100_000_000, 0))

    def test_an_inexact_split_carries_the_integer_remainder(self) -> None:
        share, remainder = winners.equal_split(34_200_000_000, 7)
        self.assertEqual((share, remainder), (4_885_714_285, 5))
        self.assertEqual(share * 7 + remainder, 34_200_000_000)

    def test_an_empty_winner_set_carries_the_whole_portion(self) -> None:
        self.assertEqual(
            winners.equal_split(economy.FOUNDER_OPERATOR_LEG, 0),
            (0, economy.FOUNDER_OPERATOR_LEG),
        )

    def test_the_split_conserves_the_portion_for_every_winner_count(self) -> None:
        portion = economy.FOUNDER_OPERATOR_LEG
        for count in range(1, 64):
            with self.subTest(count):
                share, remainder = winners.equal_split(portion, count)
                self.assertEqual(share * count + remainder, portion)
                self.assertLess(remainder, count)

    def test_the_portion_is_the_founder_directed_operator_leg(self) -> None:
        self.assertEqual(economy.FOUNDER_OPERATOR_LEG, 34_200_000_000)


if __name__ == "__main__":
    unittest.main()
