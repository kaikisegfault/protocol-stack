#!/usr/bin/env python3
"""The slot grid, its exactness, challenge selection, and the storage bound."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import InvariantError
from simulation.uptime_measurement import contract as c
from simulation.uptime_measurement import slots


class ConstantTest(unittest.TestCase):
    def test_the_derivation_is_exact(self) -> None:
        c.assert_exact_derivation()
        self.assertEqual(c.SLOTS_PER_WINDOW, 24)
        self.assertEqual(c.SLOT_BLOCKS, 1_200)
        self.assertEqual(c.ACTIVITY_THRESHOLD_SLOTS, 18)
        self.assertEqual(c.GRACE_ALLOWANCE_SLOTS, 6)
        self.assertEqual(c.SLOT_SECONDS, 3_600)

    def test_it_defers_to_the_cycle_boundary_contract(self) -> None:
        c.assert_agrees_with_boundary()

    def test_no_founder_figure_leaves_a_remainder(self) -> None:
        for blocks in (
            c.CYCLE_BLOCKS,
            c.ACTIVITY_THRESHOLD_BLOCKS,
            c.GRACE_ALLOWANCE_BLOCKS,
        ):
            self.assertEqual(blocks % c.SLOT_BLOCKS, 0, blocks)

    def test_the_threshold_and_allowance_sum_to_a_window(self) -> None:
        self.assertEqual(
            c.ACTIVITY_THRESHOLD_SLOTS + c.GRACE_ALLOWANCE_SLOTS, c.SLOTS_PER_WINDOW
        )

    def test_a_slot_is_one_hour_of_the_founder_target(self) -> None:
        self.assertEqual(c.SLOT_SECONDS * c.SLOTS_PER_WINDOW, 86_400)
        self.assertEqual(c.ACTIVITY_THRESHOLD_SLOTS * c.SLOT_SECONDS, 64_800)
        self.assertEqual(c.GRACE_ALLOWANCE_SLOTS * c.SLOT_SECONDS, 21_600)

    def test_the_dispute_cap_cannot_fail_a_perfect_seat(self) -> None:
        surviving = c.SLOTS_PER_WINDOW - c.DISPUTE_CAP_SLOTS_PER_SEAT
        self.assertGreaterEqual(surviving, c.ACTIVITY_THRESHOLD_SLOTS)
        self.assertEqual(c.DISPUTE_CAP_SLOTS_PER_SEAT, c.GRACE_ALLOWANCE_SLOTS)

    def test_the_storage_bound_is_exact(self) -> None:
        self.assertEqual(c.WINDOW_BITMAP_BYTES_PER_SEAT, 3)
        self.assertEqual(c.RETAINED_WINDOWS, 2)
        self.assertEqual(c.MEASUREMENT_STORAGE_BYTES, 800_000)

    def test_every_result_code_is_unique(self) -> None:
        self.assertEqual(len(c.RESULT_CODES), len(set(c.RESULT_CODES)))


class GridTest(unittest.TestCase):
    def test_the_slots_tile_a_window_exactly(self) -> None:
        slots.assert_slots_tile_window()

    def test_a_window_first_height_is_slot_zero(self) -> None:
        self.assertEqual(slots.slot_of_height(c.CYCLE_BLOCKS), 0)

    def test_a_window_last_height_is_the_final_slot(self) -> None:
        self.assertEqual(slots.slot_of_height(2 * c.CYCLE_BLOCKS - 1), c.MAX_SLOT_INDEX)

    def test_every_slot_boundary_is_where_the_grid_says(self) -> None:
        for slot in range(c.SLOTS_PER_WINDOW):
            first = slots.slot_first_height(3, slot)
            last = slots.slot_last_height(3, slot)
            self.assertEqual(last - first + 1, c.SLOT_BLOCKS)
            self.assertEqual(slots.slot_of_height(first), slot)
            self.assertEqual(slots.slot_of_height(last), slot)

    def test_a_slot_index_outside_the_window_is_refused(self) -> None:
        with self.assertRaises(InvariantError):
            slots.slot_first_height(0, c.SLOTS_PER_WINDOW)


class ChallengeableHeightTest(unittest.TestCase):
    """A challenge and its deadline must lie inside one slot.

    That containment is what lets the per-slot counters be discarded at the slot
    boundary, which is one of the three properties the storage bound rests on.
    """

    def test_the_last_challengeable_height_deadline_is_the_slot_last_height(self) -> None:
        last = slots.slot_last_height(1, 0)
        latest = last - c.RESPONSE_DEADLINE_BLOCKS
        self.assertTrue(slots.is_challengeable_height(latest))
        self.assertEqual(latest + c.RESPONSE_DEADLINE_BLOCKS, last)

    def test_the_next_height_is_excluded(self) -> None:
        last = slots.slot_last_height(1, 0)
        self.assertFalse(slots.is_challengeable_height(last - c.RESPONSE_DEADLINE_BLOCKS + 1))

    def test_the_final_heights_of_every_slot_are_excluded(self) -> None:
        for slot in range(c.SLOTS_PER_WINDOW):
            last = slots.slot_last_height(1, slot)
            for offset in range(c.RESPONSE_DEADLINE_BLOCKS):
                self.assertFalse(slots.is_challengeable_height(last - offset))

    def test_the_challengeable_count_per_slot_is_exact(self) -> None:
        first = slots.slot_first_height(1, 0)
        challengeable = sum(
            1 for height in range(first, first + c.SLOT_BLOCKS)
            if slots.is_challengeable_height(height)
        )
        self.assertEqual(challengeable, c.CHALLENGEABLE_HEIGHTS_PER_SLOT)


class SelectionTest(unittest.TestCase):
    @staticmethod
    def beacon(height: int) -> str:
        return f"{height:064x}"

    def test_selection_is_deterministic(self) -> None:
        for height in range(c.CYCLE_BLOCKS, c.CYCLE_BLOCKS + 200):
            first = slots.is_selected(7, height, self.beacon(height))
            self.assertEqual(first, slots.is_selected(7, height, self.beacon(height)))

    def test_a_different_beacon_changes_the_selection(self) -> None:
        """A seat cannot predict its audit from the height alone."""
        height = c.CYCLE_BLOCKS + 5
        under_one = [
            slots.is_selected(seat, height, self.beacon(height)) for seat in range(400)
        ]
        under_two = [
            slots.is_selected(seat, height, "ff" * 32) for seat in range(400)
        ]
        self.assertNotEqual(under_one, under_two)

    def test_no_seat_is_selected_in_an_excluded_height(self) -> None:
        last = slots.slot_last_height(1, 0)
        for seat in range(500):
            self.assertFalse(slots.is_selected(seat, last, self.beacon(last)))

    def test_a_seat_expects_about_one_challenge_per_slot(self) -> None:
        """The sampling rate is one probe per credited unit.

        The count is a random variable, so this bounds it rather than fixing it.
        A rate far from one would mean the period no longer equals the slot.
        """
        first = slots.slot_first_height(1, 0)
        counts = []
        for seat in range(40):
            counts.append(
                sum(
                    1
                    for height in range(first, first + c.SLOT_BLOCKS)
                    if slots.is_selected(seat, height, self.beacon(height))
                )
            )
        self.assertGreaterEqual(sum(counts), 20)
        self.assertLessEqual(sum(counts), 70)


if __name__ == "__main__":
    unittest.main()
