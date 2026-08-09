#!/usr/bin/env python3
"""The cycle-boundary grid: constants, window spans, and a seat's issuance span."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import MAX_U64, InvariantError
from simulation.cycle_boundary import contract as c
from simulation.cycle_boundary import grid


class ConstantTest(unittest.TestCase):
    def test_the_derivation_is_exact(self) -> None:
        c.assert_exact_derivation()
        self.assertEqual(c.CYCLE_BLOCKS, 28_800)
        self.assertEqual(c.ACTIVITY_THRESHOLD_BLOCKS, 21_600)
        self.assertEqual(c.GRACE_ALLOWANCE_BLOCKS, 7_200)

    def test_no_founder_duration_leaves_a_remainder(self) -> None:
        for seconds in (
            c.CYCLE_TARGET_SECONDS,
            c.ACTIVITY_THRESHOLD_SECONDS,
            c.GRACE_ALLOWANCE_SECONDS,
        ):
            self.assertEqual(seconds % c.TARGET_COMMIT_SECONDS, 0, seconds)

    def test_block_counts_convert_back_to_the_stated_seconds(self) -> None:
        for blocks, seconds in (
            (c.CYCLE_BLOCKS, c.CYCLE_TARGET_SECONDS),
            (c.ACTIVITY_THRESHOLD_BLOCKS, c.ACTIVITY_THRESHOLD_SECONDS),
            (c.GRACE_ALLOWANCE_BLOCKS, c.GRACE_ALLOWANCE_SECONDS),
        ):
            self.assertEqual(blocks * c.TARGET_COMMIT_SECONDS, seconds)

    def test_threshold_and_allowance_sum_to_a_window_in_both_units(self) -> None:
        self.assertEqual(
            c.ACTIVITY_THRESHOLD_BLOCKS + c.GRACE_ALLOWANCE_BLOCKS, c.CYCLE_BLOCKS
        )
        self.assertEqual(
            c.ACTIVITY_THRESHOLD_SECONDS + c.GRACE_ALLOWANCE_SECONDS,
            c.CYCLE_TARGET_SECONDS,
        )

    def test_the_shared_figures_agree_with_the_accepted_economy_contract(self) -> None:
        c.assert_agrees_with_economy()

    def test_a_grid_that_could_not_represent_a_threshold_raises(self) -> None:
        """The guard is what stops a founder threshold from being rounded."""
        original = c.TARGET_COMMIT_SECONDS
        try:
            c.TARGET_COMMIT_SECONDS = 7
            with self.assertRaises(InvariantError):
                c.assert_exact_derivation()
        finally:
            c.TARGET_COMMIT_SECONDS = original
        c.assert_exact_derivation()


class WindowTest(unittest.TestCase):
    def test_genesis_is_in_window_zero(self) -> None:
        self.assertEqual(grid.window_of_height(c.GENESIS_HEIGHT), 0)

    def test_a_window_holds_exactly_cycle_blocks_heights(self) -> None:
        for window in (0, 1, 2, 1_000):
            first = grid.window_first_height(window)
            last = grid.window_last_height(window)
            self.assertEqual(last - first + 1, c.CYCLE_BLOCKS)

    def test_window_boundaries_are_off_by_one_safe(self) -> None:
        self.assertEqual(grid.window_of_height(c.CYCLE_BLOCKS - 1), 0)
        self.assertEqual(grid.window_of_height(c.CYCLE_BLOCKS), 1)
        self.assertEqual(grid.window_of_height(2 * c.CYCLE_BLOCKS - 1), 1)
        self.assertEqual(grid.window_of_height(2 * c.CYCLE_BLOCKS), 2)

    def test_windows_are_contiguous_with_no_gap_or_overlap(self) -> None:
        for window in range(5):
            self.assertEqual(
                grid.window_last_height(window) + 1,
                grid.window_first_height(window + 1),
            )

    def test_every_first_height_lands_back_in_its_own_window(self) -> None:
        for window in (0, 1, 7, 731, 1_000_000):
            self.assertEqual(
                grid.window_of_height(grid.window_first_height(window)), window
            )
            self.assertEqual(
                grid.window_of_height(grid.window_last_height(window)), window
            )

    def test_a_negative_or_oversized_height_is_a_shape_error(self) -> None:
        for height in (-1, MAX_U64 + 1):
            with self.assertRaises(InvariantError):
                grid.window_of_height(height)

    def test_a_boolean_is_not_a_height(self) -> None:
        with self.assertRaises(InvariantError):
            grid.window_of_height(True)


class SpanTest(unittest.TestCase):
    def test_a_seat_begins_at_the_next_full_window(self) -> None:
        self.assertEqual(grid.first_cycle_window(0), 1)
        self.assertEqual(grid.first_cycle_window(c.CYCLE_BLOCKS - 1), 1)
        self.assertEqual(grid.first_cycle_window(c.CYCLE_BLOCKS), 2)

    def test_every_span_holds_the_founder_directed_731_windows(self) -> None:
        for height in (0, 1, c.CYCLE_BLOCKS - 1, c.CYCLE_BLOCKS, 100_000, 10**12):
            self.assertEqual(grid.span_length(height), c.ISSUANCE_CYCLES_PER_SEAT)
            self.assertEqual(
                grid.last_cycle_window(height) - grid.first_cycle_window(height) + 1,
                c.ISSUANCE_CYCLES_PER_SEAT,
            )

    def test_activations_in_one_window_share_a_span(self) -> None:
        """The property that makes performance reallocation possible at all."""
        first = grid.first_cycle_window(0)
        for height in (0, 1, c.CYCLE_BLOCKS // 2, c.CYCLE_BLOCKS - 1):
            self.assertEqual(grid.first_cycle_window(height), first)

    def test_the_next_window_shifts_the_span_by_exactly_one(self) -> None:
        self.assertEqual(
            grid.first_cycle_window(c.CYCLE_BLOCKS),
            grid.first_cycle_window(c.CYCLE_BLOCKS - 1) + 1,
        )

    def test_cycle_to_window_and_back_over_a_complete_span(self) -> None:
        height = 100_000
        for cycle_index in range(c.ISSUANCE_CYCLES_PER_SEAT):
            window = grid.window_for_cycle(height, cycle_index)
            self.assertEqual(grid.cycle_for_window(height, window), cycle_index)

    def test_windows_outside_a_span_invert_to_nothing(self) -> None:
        height = 100_000
        self.assertIsNone(
            grid.cycle_for_window(height, grid.first_cycle_window(height) - 1)
        )
        self.assertIsNone(
            grid.cycle_for_window(height, grid.last_cycle_window(height) + 1)
        )

    def test_a_cycle_index_outside_the_span_is_a_shape_error(self) -> None:
        for cycle_index in (-1, c.ISSUANCE_CYCLES_PER_SEAT):
            with self.assertRaises(InvariantError):
                grid.window_for_cycle(0, cycle_index)


class OverflowTest(unittest.TestCase):
    """Guards proved present rather than reached at any plausible height."""

    def test_the_u64_maximum_height_has_no_representable_span(self) -> None:
        self.assertFalse(grid.span_is_representable(c.MAX_HEIGHT))

    def test_the_highest_usable_activation_height_is_representable(self) -> None:
        highest = (grid.MAX_WINDOW - c.MAX_CYCLE_INDEX - 1) * c.CYCLE_BLOCKS
        self.assertTrue(grid.span_is_representable(highest))
        self.assertEqual(grid.span_length(highest), c.ISSUANCE_CYCLES_PER_SEAT)
        self.assertLessEqual(grid.last_cycle_window(highest), grid.MAX_WINDOW)

    def test_one_window_above_the_highest_usable_height_is_not(self) -> None:
        highest = (grid.MAX_WINDOW - c.MAX_CYCLE_INDEX - 1) * c.CYCLE_BLOCKS
        self.assertFalse(grid.span_is_representable(highest + c.CYCLE_BLOCKS))

    def test_a_window_above_the_bound_cannot_be_addressed(self) -> None:
        with self.assertRaises(InvariantError):
            grid.window_first_height(grid.MAX_WINDOW + 1)


if __name__ == "__main__":
    unittest.main()
