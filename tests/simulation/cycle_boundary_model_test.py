#!/usr/bin/env python3
"""Cycle-boundary transitions: activation, the window check, and containment."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import CodedError, InvariantError
from simulation.cycle_boundary import contract as c
from simulation.cycle_boundary import scenario
from simulation.cycle_boundary.model import CycleBoundary


def code(callable_object, *arguments) -> str:
    try:
        callable_object(*arguments)
    except CodedError as error:
        return error.code
    return "ACCEPTED"


class ActivationTest(unittest.TestCase):
    def test_an_activation_records_a_height(self) -> None:
        boundary = CycleBoundary()
        boundary.record_activation(0, 100_000)
        self.assertEqual(boundary.activation_heights[0], 100_000)
        self.assertEqual(boundary.last_activation_height, 100_000)

    def test_an_activation_issues_nothing(self) -> None:
        """The model holds a schedule; there is no balance to credit."""
        boundary = CycleBoundary()
        boundary.record_activation(0, 0)
        self.assertEqual(set(boundary.canonical_state()), {
            "schema",
            "cycle_blocks",
            "seats",
            "last_activation_height",
        })

    def test_a_seat_above_capacity_is_rejected(self) -> None:
        boundary = CycleBoundary()
        self.assertEqual(
            code(boundary.record_activation, c.FOUNDER_SEAT_CAPACITY, 0), "SEAT_RANGE"
        )

    def test_the_last_seat_identifier_is_accepted(self) -> None:
        boundary = CycleBoundary()
        boundary.record_activation(c.MAX_SEAT_ID, 0)
        self.assertIn(c.MAX_SEAT_ID, boundary.activation_heights)

    def test_a_height_with_no_representable_span_is_rejected(self) -> None:
        boundary = CycleBoundary()
        self.assertEqual(
            code(boundary.record_activation, 0, c.MAX_HEIGHT), "HEIGHT_RANGE"
        )

    def test_a_repeated_seat_is_a_replay(self) -> None:
        boundary = CycleBoundary()
        boundary.record_activation(3, 100_000)
        self.assertEqual(code(boundary.record_activation, 3, 200_000), "REPLAY")

    def test_a_replay_does_not_move_a_recorded_height(self) -> None:
        boundary = CycleBoundary()
        boundary.record_activation(3, 100_000)
        code(boundary.record_activation, 3, 200_000)
        self.assertEqual(boundary.activation_heights[3], 100_000)
        self.assertEqual(boundary.last_activation_height, 100_000)

    def test_a_height_below_the_last_recorded_one_is_rejected(self) -> None:
        boundary = CycleBoundary()
        boundary.record_activation(0, 100_000)
        self.assertEqual(
            code(boundary.record_activation, 1, 99_999), "HEIGHT_NOT_MONOTONIC"
        )

    def test_an_equal_height_is_accepted_because_one_block_may_activate_many(self) -> None:
        boundary = CycleBoundary()
        boundary.record_activation(0, 100_000)
        boundary.record_activation(1, 100_000)
        self.assertEqual(boundary.schedule(0)[1:], boundary.schedule(1)[1:])

    def test_the_seat_bound_is_reported_before_the_height_bound(self) -> None:
        boundary = CycleBoundary()
        self.assertEqual(
            code(boundary.record_activation, c.FOUNDER_SEAT_CAPACITY, c.MAX_HEIGHT),
            "SEAT_RANGE",
        )

    def test_a_replay_is_reported_before_a_stale_height(self) -> None:
        boundary = CycleBoundary()
        boundary.record_activation(3, 100_000)
        self.assertEqual(code(boundary.record_activation, 3, 0), "REPLAY")

    def test_a_negative_or_non_integer_input_is_a_shape_error(self) -> None:
        boundary = CycleBoundary()
        for seat_id, height in ((-1, 0), (0, -1), (True, 0), (0, "7")):
            with self.assertRaises(InvariantError):
                boundary.record_activation(seat_id, height)


class CheckWindowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.boundary = scenario.build()
        self.height = self.boundary.activation_heights[scenario.GENESIS_SEAT]
        self.first = self.boundary.schedule(scenario.GENESIS_SEAT)[1]
        self.last = self.boundary.schedule(scenario.GENESIS_SEAT)[2]

    def check(self, seat_id: int, cycle_index: int, window: int) -> str:
        return self.boundary.check_window(seat_id, cycle_index, window).code

    def test_the_first_and_last_cycle_of_a_span_are_accepted(self) -> None:
        self.assertEqual(self.check(scenario.GENESIS_SEAT, 0, self.first), "ACCEPTED")
        self.assertEqual(
            self.check(scenario.GENESIS_SEAT, c.MAX_CYCLE_INDEX, self.last), "ACCEPTED"
        )

    def test_an_accepted_check_returns_the_derived_cycle(self) -> None:
        result = self.boundary.check_window(scenario.GENESIS_SEAT, 5, self.first + 5)
        self.assertEqual(result.code, "ACCEPTED")
        self.assertEqual(result.cycle_index, 5)

    def test_a_window_before_the_span_is_distinguished(self) -> None:
        self.assertEqual(
            self.check(scenario.GENESIS_SEAT, 0, self.first - 1),
            "WINDOW_BEFORE_ISSUANCE",
        )

    def test_a_window_after_the_span_is_distinguished(self) -> None:
        self.assertEqual(
            self.check(scenario.GENESIS_SEAT, c.MAX_CYCLE_INDEX, self.last + 1),
            "WINDOW_AFTER_ISSUANCE",
        )

    def test_a_window_inside_the_span_but_for_another_cycle_is_distinguished(self) -> None:
        """The code that indicates a caller defect rather than a bad request."""
        self.assertEqual(
            self.check(scenario.GENESIS_SEAT, 5, self.first), "WINDOW_NOT_FOR_CYCLE"
        )
        self.assertEqual(
            self.check(scenario.GENESIS_SEAT, 0, self.first + 5), "WINDOW_NOT_FOR_CYCLE"
        )

    def test_an_unactivated_seat_has_no_schedule(self) -> None:
        self.assertEqual(
            self.check(scenario.UNACTIVATED_SEAT, 0, self.first), "SEAT_NOT_ACTIVATED"
        )

    def test_a_cycle_above_the_span_is_rejected(self) -> None:
        self.assertEqual(
            self.check(scenario.GENESIS_SEAT, c.ISSUANCE_CYCLES_PER_SEAT, self.first),
            "CYCLE_RANGE",
        )

    def test_the_seat_bound_is_reported_before_the_cycle_bound(self) -> None:
        self.assertEqual(
            self.check(
                c.FOUNDER_SEAT_CAPACITY, c.ISSUANCE_CYCLES_PER_SEAT, self.first
            ),
            "SEAT_RANGE",
        )

    def test_the_cycle_bound_is_reported_before_activation(self) -> None:
        self.assertEqual(
            self.check(
                scenario.UNACTIVATED_SEAT, c.ISSUANCE_CYCLES_PER_SEAT, self.first
            ),
            "CYCLE_RANGE",
        )

    def test_every_cycle_of_a_complete_span_is_accepted(self) -> None:
        for cycle_index in range(c.ISSUANCE_CYCLES_PER_SEAT):
            self.assertEqual(
                self.check(scenario.GENESIS_SEAT, cycle_index, self.first + cycle_index),
                "ACCEPTED",
                cycle_index,
            )

    def test_a_check_writes_nothing(self) -> None:
        before = self.boundary.state_digest()
        for cycle_index in range(0, c.ISSUANCE_CYCLES_PER_SEAT, 37):
            self.check(scenario.GENESIS_SEAT, cycle_index, self.first)
        self.assertEqual(self.boundary.state_digest(), before)

    def test_two_seats_in_the_same_window_accept_the_same_window(self) -> None:
        """Reallocation ranks uptime across seats, so their windows must coincide."""
        for cycle_index in (0, 365, c.MAX_CYCLE_INDEX):
            window = self.first + cycle_index
            self.assertEqual(
                self.check(scenario.GENESIS_SEAT, cycle_index, window), "ACCEPTED"
            )
            self.assertEqual(
                self.check(scenario.WINDOW_END_SEAT, cycle_index, window), "ACCEPTED"
            )


class StateTest(unittest.TestCase):
    def test_the_scenario_digest_is_stable_across_repeated_runs(self) -> None:
        self.assertEqual(scenario.build().state_digest(), scenario.build().state_digest())

    def test_the_digest_covers_the_schedule_not_the_arrival_order(self) -> None:
        ascending = CycleBoundary()
        for seat_id, height in sorted(scenario.ACTIVATIONS, key=lambda pair: pair[1]):
            ascending.record_activation(seat_id, height)

        by_seat = CycleBoundary()
        for seat_id, height in sorted(scenario.ACTIVATIONS):
            by_seat.record_activation(seat_id, height)

        self.assertEqual(ascending.state_digest(), by_seat.state_digest())

    def test_a_different_activation_height_changes_the_digest(self) -> None:
        moved = CycleBoundary()
        for seat_id, height in scenario.ACTIVATIONS:
            moved.record_activation(seat_id, height + c.CYCLE_BLOCKS)
        self.assertNotEqual(moved.state_digest(), scenario.build().state_digest())

    def test_an_empty_model_has_no_last_activation_height(self) -> None:
        self.assertIsNone(CycleBoundary().canonical_state()["last_activation_height"])

    def test_a_rejected_activation_leaves_the_digest_unchanged(self) -> None:
        boundary = scenario.build()
        before = boundary.state_digest()
        for _, seat_id, height in scenario.ACTIVATION_REJECTIONS:
            code(boundary.record_activation, seat_id, height)
        self.assertEqual(boundary.state_digest(), before)

    def test_the_recorded_scenario_reaches_every_modelled_code(self) -> None:
        reached = set(scenario.activation_rejection_codes().values()) | set(
            scenario.check_codes().values()
        )
        self.assertEqual(reached, set(c.RESULT_CODES))

    def test_the_state_label_carries_its_version(self) -> None:
        self.assertTrue(c.STATE_LABEL.endswith("-v1"), c.STATE_LABEL)
        self.assertTrue(c.STATE_SCHEMA.endswith("/v1"), c.STATE_SCHEMA)

    def test_the_storage_bound_is_one_height_per_seat(self) -> None:
        self.assertEqual(
            c.SCHEDULE_STORAGE_BYTES,
            c.FOUNDER_SEAT_CAPACITY * c.ACTIVATION_HEIGHT_BYTES,
        )

    def test_an_unactivated_seat_has_no_schedule_to_read(self) -> None:
        self.assertEqual(
            code(scenario.build().schedule, scenario.UNACTIVATED_SEAT),
            "SEAT_NOT_ACTIVATED",
        )


if __name__ == "__main__":
    unittest.main()
