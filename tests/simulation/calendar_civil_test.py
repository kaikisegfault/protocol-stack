#!/usr/bin/env python3
"""The calendar-v1 derivation: constants, the leap rule, months, and bounds."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.calendar import contract as c
from simulation.calendar import civil, months
from simulation.common.canonical import MAX_U64, InvariantError


class ConstantTest(unittest.TestCase):
    def test_the_derivation_is_exact(self) -> None:
        c.assert_exact_derivation()
        self.assertEqual(c.TIMESTAMP_TOLERANCE_MILLIS, 60_000)
        self.assertEqual(c.MAX_BOUNDARY_SHIFT_BLOCKS, 20)
        self.assertEqual(c.MAX_MONTH_INDEX, 96_359)

    def test_the_range_matches_the_calendar(self) -> None:
        c.assert_range_matches_the_calendar()
        self.assertEqual(c.MAX_TIMESTAMP_MILLIS, 253_402_300_799_999)
        self.assertLessEqual(c.MAX_TIMESTAMP_MILLIS, MAX_U64)

    def test_the_commit_interval_agrees_with_the_accepted_grid(self) -> None:
        c.assert_agrees_with_cycle_boundary()

    def test_the_tolerance_is_small_relative_to_a_month(self) -> None:
        # The ceiling ADR 0050 sets: a proposer can move a month boundary by
        # exactly the tolerance, so the tolerance must be small beside a month.
        self.assertLess(
            c.TIMESTAMP_TOLERANCE_SECONDS * 1_000, c.SECONDS_PER_MONTH_MINIMUM
        )

    def test_the_calendar_stores_nothing(self) -> None:
        self.assertEqual(c.CALENDAR_STATE_BYTES, 0)


class LeapRuleTest(unittest.TestCase):
    def test_the_rule_is_the_full_gregorian_one(self) -> None:
        self.assertTrue(civil.is_leap_year(2024))
        self.assertFalse(civil.is_leap_year(2026))
        # The two the abbreviated "divisible by four" rule gets wrong.
        self.assertTrue(civil.is_leap_year(2000))
        self.assertFalse(civil.is_leap_year(2100))

    def test_february_is_the_only_month_whose_length_moves(self) -> None:
        for month in range(1, 13):
            if month == 2:
                continue
            self.assertEqual(
                civil.days_in_month(2024, month), civil.days_in_month(2026, month)
            )
        self.assertEqual(civil.days_in_month(2024, 2), 29)
        self.assertEqual(civil.days_in_month(2026, 2), 28)

    def test_a_month_outside_one_to_twelve_is_refused(self) -> None:
        for month in (0, 13, -1):
            with self.assertRaises(InvariantError):
                civil.days_in_month(2026, month)

    def test_four_centuries_hold_the_gregorian_cycle_length(self) -> None:
        self.assertEqual(
            civil.days_from_civil(2370, 1, 1) - civil.days_from_civil(1970, 1, 1),
            civil.DAYS_PER_ERA,
        )


class CivilRoundTripTest(unittest.TestCase):
    def test_the_two_directions_invert_each_other_across_every_month_start(self) -> None:
        for index in range(c.MAX_MONTH_INDEX + 1):
            year = months.year_of_index(index)
            month = months.month_of_index(index)
            day = civil.days_from_civil(year, month, 1)
            self.assertEqual(civil.civil_from_days(day), (year, month, 1))

    def test_the_last_day_of_every_month_inverts(self) -> None:
        for index in range(c.MAX_MONTH_INDEX + 1):
            year = months.year_of_index(index)
            month = months.month_of_index(index)
            last = civil.days_in_month(year, month)
            day = civil.days_from_civil(year, month, last)
            self.assertEqual(civil.civil_from_days(day), (year, month, last))

    def test_a_day_outside_the_month_is_refused(self) -> None:
        with self.assertRaises(InvariantError):
            civil.days_from_civil(2026, 2, 29)
        civil.days_from_civil(2024, 2, 29)


class MonthTest(unittest.TestCase):
    def test_the_epoch_is_month_index_zero(self) -> None:
        self.assertEqual(months.month_index(0), 0)
        self.assertEqual(months.month_start_millis(0), 0)
        self.assertEqual(months.year_month_of(0), (1970, 1))

    def test_a_month_contains_exactly_its_own_milliseconds(self) -> None:
        for index in (0, 1, 361, 672, 673, c.MAX_MONTH_INDEX):
            start = months.month_start_millis(index)
            end = months.month_end_millis(index)
            self.assertEqual(months.month_index(start), index)
            self.assertEqual(months.month_index(end), index)
            if index > 0:
                self.assertEqual(months.month_index(start - 1), index - 1)

    def test_the_last_month_ends_at_the_range_bound(self) -> None:
        self.assertEqual(
            months.month_end_millis(c.MAX_MONTH_INDEX), c.MAX_TIMESTAMP_MILLIS
        )

    def test_month_start_accepts_one_past_the_end_and_nothing_further(self) -> None:
        # The single value the derivation computes outside the accepted range,
        # and the reason the range ends where it does.
        self.assertEqual(
            months.month_start_millis(c.MAX_MONTH_INDEX + 1), c.MAX_TIMESTAMP_MILLIS + 1
        )
        with self.assertRaises(InvariantError):
            months.month_start_millis(c.MAX_MONTH_INDEX + 2)
        with self.assertRaises(InvariantError):
            months.month_end_millis(c.MAX_MONTH_INDEX + 1)

    def test_a_timestamp_outside_the_range_is_refused_before_any_derivation(self) -> None:
        for timestamp in (-1, c.MAX_TIMESTAMP_MILLIS + 1):
            self.assertFalse(months.in_range(timestamp))
            with self.assertRaises(InvariantError):
                months.month_index(timestamp)

    def test_the_month_index_is_non_decreasing_in_the_timestamp(self) -> None:
        previous = 0
        probe = 0
        while probe <= c.MAX_TIMESTAMP_MILLIS:
            index = months.month_index(probe)
            self.assertGreaterEqual(index, previous)
            previous = index
            probe += 400 * 24 * 3_600_000

    def test_a_span_of_one_day_touches_one_month(self) -> None:
        self.assertEqual(months.months_spanned(0, 1), 1)
        with self.assertRaises(InvariantError):
            months.months_spanned(0, 0)

    def test_a_seat_span_touches_at_most_twenty_five_months(self) -> None:
        # Walked over a four-century window in the verifier; sampled here at
        # the shape that produces the maximum, which is a span beginning on the
        # last day of a month.
        start = civil.days_from_civil(2026, 1, 31)
        self.assertEqual(months.months_spanned(start, 731), 25)


if __name__ == "__main__":
    unittest.main()
