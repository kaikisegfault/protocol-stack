#!/usr/bin/env python3
"""The enforced schedule: activation heights, windows, and the in-scope set."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import MAX_U64
from simulation.cycle_boundary.grid import (
    first_cycle_window,
    last_cycle_window,
    window_for_cycle,
)
from simulation.cycle_boundary.model import CycleBoundary
from simulation.founder_economy_v3 import contract as c
from simulation.founder_economy_v3.domain import Seat, State
from simulation.founder_economy_v3.schedule import check_window, in_scope_seats

from tests.simulation.founder_economy_v3_common import (
    CYCLE_BLOCKS,
    activate,
    codes,
    evaluate_scoped,
    run,
    scoped_record,
    evaluate,
)


class ActivationHeightTest(unittest.TestCase):
    def test_a_seat_records_the_height_and_its_derived_span(self) -> None:
        state = run([activate(0, height=CYCLE_BLOCKS)])["final_state"]
        seat = state["seats"]["00000"]
        self.assertEqual(seat["activation_height"], str(CYCLE_BLOCKS))
        self.assertEqual(seat["first_cycle_window"], 2)
        self.assertEqual(seat["last_cycle_window"], 2 + c.MAX_CYCLE_INDEX)
        self.assertEqual(state["last_activation_height"], str(CYCLE_BLOCKS))

    def test_a_height_is_a_string_and_a_window_is_a_number(self) -> None:
        """The rendering rule the record's unchanged shape depends on."""
        state = run([activate(0, height=CYCLE_BLOCKS)])["final_state"]
        seat = state["seats"]["00000"]
        self.assertIsInstance(seat["activation_height"], str)
        self.assertIsInstance(seat["first_cycle_window"], int)
        self.assertIsInstance(state["last_activation_height"], str)

    def test_the_last_height_of_a_window_and_the_first_of_the_next_differ_by_one(
        self,
    ) -> None:
        result = run(
            [
                activate(0, height=CYCLE_BLOCKS - 1),
                activate(1, height=CYCLE_BLOCKS),
            ]
        )
        seats = result["final_state"]["seats"]
        self.assertEqual(seats["00000"]["first_cycle_window"], 1)
        self.assertEqual(seats["00001"]["first_cycle_window"], 2)

    def test_a_span_that_would_wrap_is_refused(self) -> None:
        """A wrapped window would silently alias another seat's schedule."""
        self.assertEqual(codes(run([activate(0, height=MAX_U64)])), ["HEIGHT_RANGE"])

    def test_the_largest_representable_height_is_accepted(self) -> None:
        highest_window = MAX_U64 // CYCLE_BLOCKS - c.MAX_CYCLE_INDEX - 1
        height = highest_window * CYCLE_BLOCKS
        result = run([activate(0, height=height)])
        self.assertEqual(codes(result), ["OK"])
        self.assertEqual(
            result["final_state"]["seats"]["00000"]["last_cycle_window"],
            MAX_U64 // CYCLE_BLOCKS,
        )

    def test_heights_may_repeat_but_may_not_decrease(self) -> None:
        """One block may activate several seats; none may land in the past."""
        result = run(
            [
                activate(0, height=CYCLE_BLOCKS),
                activate(1, height=CYCLE_BLOCKS),
                activate(2, height=CYCLE_BLOCKS - 1),
            ]
        )
        self.assertEqual(codes(result), ["OK", "OK", "HEIGHT_NOT_MONOTONIC"])

    def test_a_rejected_activation_writes_nothing(self) -> None:
        result = run([activate(0, height=CYCLE_BLOCKS), activate(1, height=0)])
        self.assertEqual(codes(result), ["OK", "HEIGHT_NOT_MONOTONIC"])
        self.assertNotIn("00001", result["final_state"]["seats"])
        self.assertEqual(result["final_state"]["last_activation_height"], str(CYCLE_BLOCKS))


class WindowCheckTest(unittest.TestCase):
    HEIGHTS = {0: CYCLE_BLOCKS}

    def _evaluate(self, cycle_index: int, window: int) -> str:
        events = [
            activate(0, height=self.HEIGHTS[0]),
            evaluate_scoped(self.HEIGHTS, 0, cycle_index, window=window),
        ]
        return codes(run(events))[1]

    def _evaluate_alone(self, cycle_index: int, window: int) -> str:
        """Evaluate against a record naming only the evaluated seat.

        A window before the seat's own span has no in-scope seats at all, so a
        complete record for it would be empty and version two's validity
        condition would reject it before the window check ran.
        """
        events = [
            activate(0, height=self.HEIGHTS[0]),
            evaluate(0, cycle_index, {"cycle_window": window,
                                      "entries": [{"seat_id": 0, "uptime_seconds": 86_400}]}),
        ]
        return codes(run(events))[1]

    def test_the_correct_window_is_accepted(self) -> None:
        self.assertEqual(self._evaluate(0, window_for_cycle(CYCLE_BLOCKS, 0)), "OK")

    def test_a_window_before_the_span_is_distinguished(self) -> None:
        self.assertEqual(
            self._evaluate_alone(0, first_cycle_window(CYCLE_BLOCKS) - 1),
            "WINDOW_BEFORE_ISSUANCE",
        )

    def test_a_window_with_no_in_scope_seats_cannot_carry_a_complete_record(self) -> None:
        """An empty record is invalid, so the window check is never reached."""
        self.assertEqual(
            self._evaluate(0, first_cycle_window(CYCLE_BLOCKS) - 1),
            "INVALID_UPTIME_RECORD",
        )

    def test_a_window_after_the_span_is_distinguished(self) -> None:
        self.assertEqual(
            self._evaluate(730, last_cycle_window(CYCLE_BLOCKS) + 1),
            "WINDOW_AFTER_ISSUANCE",
        )

    def test_a_window_inside_the_span_but_one_cycle_away_is_distinguished(self) -> None:
        self.assertEqual(
            self._evaluate(0, window_for_cycle(CYCLE_BLOCKS, 1)), "WINDOW_NOT_FOR_CYCLE"
        )

    def test_both_span_endpoints_are_reachable(self) -> None:
        self.assertEqual(self._evaluate(0, window_for_cycle(CYCLE_BLOCKS, 0)), "OK")
        self.assertEqual(self._evaluate(730, window_for_cycle(CYCLE_BLOCKS, 730)), "OK")

    def test_the_accepted_cycle_boundary_model_gives_the_same_answers(self) -> None:
        """The two models must agree, because neither binds the other's state."""
        boundary = CycleBoundary()
        boundary.record_activation(0, CYCLE_BLOCKS)
        seat = Seat(referrer_seat_id=None, activation_height=CYCLE_BLOCKS)
        first = first_cycle_window(CYCLE_BLOCKS)
        last = last_cycle_window(CYCLE_BLOCKS)
        for cycle_index, window in (
            (0, first),
            (0, first - 1),
            (0, first + 1),
            (730, last),
            (730, last + 1),
            (365, first + 365),
        ):
            with self.subTest(cycle_index=cycle_index, window=window):
                here = check_window(seat, cycle_index, window) or "ACCEPTED"
                there = boundary.check_window(0, cycle_index, window).code
                self.assertEqual(here, there)


class InScopeTest(unittest.TestCase):
    HEIGHTS = {0: 0, 1: CYCLE_BLOCKS, 2: 2 * CYCLE_BLOCKS}

    def _state(self) -> State:
        return State(
            seats={
                seat_id: Seat(referrer_seat_id=None, activation_height=height)
                for seat_id, height in self.HEIGHTS.items()
            }
        )

    def test_the_set_grows_as_seats_open(self) -> None:
        state = self._state()
        self.assertEqual(in_scope_seats(state, 0), ())
        self.assertEqual(in_scope_seats(state, 1), (0,))
        self.assertEqual(in_scope_seats(state, 2), (0, 1))
        self.assertEqual(in_scope_seats(state, 3), (0, 1, 2))

    def test_a_seat_activated_inside_a_window_is_not_in_scope_for_it(self) -> None:
        """It cannot have evidence for a window that had already begun."""
        state = self._state()
        self.assertNotIn(1, in_scope_seats(state, 1))
        self.assertIn(1, in_scope_seats(state, 2))

    def test_a_seat_past_its_issuance_span_stays_in_scope(self) -> None:
        """The founder rule ranks the window, not the seats still issuing."""
        state = self._state()
        beyond = last_cycle_window(self.HEIGHTS[0]) + 1
        self.assertIn(0, in_scope_seats(state, beyond))

    def test_monotonicity_refuses_a_later_activation_that_would_be_in_scope(self) -> None:
        """The bound on what completeness cannot see.

        The set is derived from the seat table as it stands, and the model has no
        current height for an evaluation. Once an activation lands at or above a
        window's first height, though, no later one can join that window's
        in-scope set, because a lower height is refused outright.
        """
        first_height = CYCLE_BLOCKS  # window 1 begins here
        result = run(
            [
                activate(0, height=first_height),
                activate(1, height=first_height - 1),
            ]
        )
        self.assertEqual(codes(result), ["OK", "HEIGHT_NOT_MONOTONIC"])
        state = State(
            seats={0: Seat(referrer_seat_id=None, activation_height=first_height)}
        )
        self.assertEqual(in_scope_seats(state, 1), ())


class CompletenessTest(unittest.TestCase):
    HEIGHTS = {0: 0, 1: 0, 2: CYCLE_BLOCKS}

    def _events(self) -> list[dict]:
        return [
            activate(0, height=self.HEIGHTS[0]),
            activate(1, height=self.HEIGHTS[1]),
            activate(2, height=self.HEIGHTS[2]),
        ]

    def test_a_complete_record_is_accepted(self) -> None:
        events = self._events() + [evaluate_scoped(self.HEIGHTS, 0, 1)]
        self.assertEqual(codes(run(events))[-1], "OK")

    def test_an_omitted_in_scope_seat_is_rejected(self) -> None:
        window = window_for_cycle(self.HEIGHTS[0], 1)
        partial = scoped_record(self.HEIGHTS, window, {})
        partial["entries"] = [
            entry for entry in partial["entries"] if entry["seat_id"] != 2
        ]
        events = self._events() + [evaluate(0, 1, partial)]
        self.assertEqual(codes(run(events))[-1], "INCOMPLETE_UPTIME_RECORD")

    def test_an_out_of_scope_seat_is_rejected(self) -> None:
        window = window_for_cycle(self.HEIGHTS[0], 0)
        extra = scoped_record(self.HEIGHTS, window, {})
        extra["entries"].append({"seat_id": 2, "uptime_seconds": 86_400})
        events = self._events() + [evaluate(0, 0, extra)]
        self.assertEqual(codes(run(events))[-1], "SEAT_NOT_IN_SCOPE")

    def test_an_out_of_scope_seat_is_reported_before_an_omission(self) -> None:
        """Two defects at once must have one defined result."""
        window = window_for_cycle(self.HEIGHTS[0], 0)
        pair = scoped_record(self.HEIGHTS, window, {})
        # Drop in-scope seat 1 and add seat 2, which has not opened yet.
        pair["entries"] = [entry for entry in pair["entries"] if entry["seat_id"] != 1]
        pair["entries"].append({"seat_id": 2, "uptime_seconds": 86_400})
        events = self._events() + [evaluate(0, 0, pair)]
        self.assertEqual(codes(run(events))[-1], "SEAT_NOT_IN_SCOPE")


if __name__ == "__main__":
    unittest.main()
