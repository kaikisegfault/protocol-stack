"""The version-three rejection set, its order, and the input-shape boundary.

A modelled rejection produces a deterministic trace record; an input-shape error
aborts the run. The two are kept apart deliberately, so this module asserts on
both sides of that line.
"""

from __future__ import annotations

import unittest

from simulation.common.canonical import MAX_U64
from simulation.founder_economy_v3.validation import InputError, parse_events

from .founder_economy_v3_common import (
    CYCLE_BLOCKS,
    FULL_WINDOW,
    activate,
    codes,
    evaluate,
    evaluate_scoped,
    record,
    run,
    scoped_record,
    window_of,
)

HEIGHTS = {0: 0, 1: CYCLE_BLOCKS}
OPENED = [activate(0, height=0), activate(1, referrer=0, height=CYCLE_BLOCKS)]


def last(*events: dict) -> str:
    return codes(run([*OPENED, *events]))[-1]


class ActivationRejectionTest(unittest.TestCase):
    def test_each_condition_is_reachable(self) -> None:
        cases = (
            ("CYCLE_RANGE", activate(100_000, height=CYCLE_BLOCKS)),
            ("HEIGHT_RANGE", activate(5, height=MAX_U64)),
            ("INVALID_REFERRER", activate(5, referrer=5, height=CYCLE_BLOCKS)),
            ("REPLAY", activate(0, height=CYCLE_BLOCKS)),
            ("SEAT_NOT_ACTIVATED", activate(5, referrer=60, height=CYCLE_BLOCKS)),
            ("HEIGHT_NOT_MONOTONIC", activate(5, height=0)),
        )
        for expected, event in cases:
            with self.subTest(expected=expected):
                self.assertEqual(last(event), expected)

    def test_the_order_is_fixed_where_two_defects_meet(self) -> None:
        """Each event carries two defects, so only one order explains it."""
        pairs = (
            ("CYCLE_RANGE", activate(100_000, height=MAX_U64)),
            ("HEIGHT_RANGE", activate(5, referrer=5, height=MAX_U64)),
            ("REPLAY", activate(0, height=0)),
            ("SEAT_NOT_ACTIVATED", activate(5, referrer=60, height=0)),
        )
        for expected, event in pairs:
            with self.subTest(expected=expected):
                self.assertEqual(last(event), expected)


class EvaluationRejectionTest(unittest.TestCase):
    def test_each_condition_is_reachable(self) -> None:
        window = window_of(HEIGHTS[0], 0)
        cases = (
            ("CYCLE_RANGE", evaluate(0, 731, scoped_record(HEIGHTS, window, {}))),
            ("SEAT_NOT_ACTIVATED", evaluate(50, 0, record(window, {50: FULL_WINDOW}))),
            ("MISSING_UPTIME_RECORD", evaluate(0, 0, None)),
            ("INVALID_UPTIME_RECORD", evaluate(0, 0, record(window, {}))),
            (
                "WINDOW_BEFORE_ISSUANCE",
                evaluate(0, 0, record(window - 1, {0: FULL_WINDOW})),
            ),
            (
                "WINDOW_AFTER_ISSUANCE",
                evaluate(0, 730, record(window + 731, {0: FULL_WINDOW})),
            ),
            ("WINDOW_NOT_FOR_CYCLE", evaluate(0, 0, record(window + 1, {0: FULL_WINDOW}))),
        )
        for expected, event in cases:
            with self.subTest(expected=expected):
                self.assertEqual(last(event), expected)

    def test_a_replayed_key_is_reported_before_the_record_is_read(self) -> None:
        first = evaluate_scoped(HEIGHTS, 0, 1)
        self.assertEqual(last(first, evaluate(0, 1, None)), "REPLAY")

    def test_an_inconsistent_record_needs_a_correct_window_first(self) -> None:
        """The intrinsic checks precede the run-history check."""
        window = window_of(HEIGHTS[0], 1)
        disagreeing = scoped_record(HEIGHTS, window, {1: 3_600})
        self.assertEqual(
            last(evaluate_scoped(HEIGHTS, 0, 1), evaluate(1, 0, disagreeing)),
            "INCONSISTENT_UPTIME_RECORD",
        )

    def test_a_wrong_window_is_reported_before_an_inconsistency(self) -> None:
        window = window_of(HEIGHTS[0], 1)
        disagreeing = scoped_record(HEIGHTS, window, {1: 3_600})
        # Seat 1's cycle 0 is this window; presenting it for cycle 1 is both the
        # wrong window and a record that disagrees with the bound one.
        wrong = evaluate(1, 1, disagreeing)
        self.assertEqual(
            last(evaluate_scoped(HEIGHTS, 0, 1), wrong), "WINDOW_NOT_FOR_CYCLE"
        )

    def test_a_rejected_evaluation_binds_no_window(self) -> None:
        """A defective record must not occupy a window a correct one then fails."""
        window = window_of(HEIGHTS[0], 1)
        defective = scoped_record(HEIGHTS, window, {1: 3_600})
        defective["entries"] = [
            entry for entry in defective["entries"] if entry["seat_id"] != 1
        ]
        results = codes(
            run([*OPENED, evaluate(0, 1, defective), evaluate_scoped(HEIGHTS, 0, 1)])
        )
        self.assertEqual(results[-2:], ["INCOMPLETE_UPTIME_RECORD", "OK"])


class InputShapeTest(unittest.TestCase):
    def _activation(self, **changes: object) -> dict:
        event = {
            "id": "a1",
            "kind": "activate_seat",
            "seat_id": 0,
            "referrer_seat_id": None,
            "activation_height": "0",
        }
        event.update(changes)
        return event

    def test_a_height_given_as_a_json_number_is_refused(self) -> None:
        """A u64 height could not be canonicalized as a number."""
        with self.assertRaises(InputError):
            parse_events([self._activation(activation_height=0)])

    def test_a_height_above_u64_is_an_input_error_not_a_rejection(self) -> None:
        """HEIGHT_RANGE is reserved for a representable height with no span."""
        with self.assertRaises(InputError):
            parse_events([self._activation(activation_height=str(MAX_U64 + 1))])

    def test_a_missing_height_is_refused(self) -> None:
        event = self._activation()
        del event["activation_height"]
        with self.assertRaises(InputError):
            parse_events([event])

    def test_a_non_canonical_height_is_refused(self) -> None:
        with self.assertRaises(InputError):
            parse_events([self._activation(activation_height="007")])

    def test_the_record_still_cannot_express_a_verdict(self) -> None:
        """The record's shape is version two's, so a supplied answer is unparsable."""
        event = {
            "id": "e1",
            "kind": "evaluate_base_permission",
            "seat_id": 0,
            "cycle_index": 0,
            "cycle_uptime_record": {
                "cycle_window": 1,
                "entries": [{"seat_id": 0, "uptime_seconds": FULL_WINDOW, "active": True}],
            },
        }
        with self.assertRaises(InputError):
            parse_events([event])

    def test_a_window_is_still_a_json_number(self) -> None:
        event = {
            "id": "e1",
            "kind": "evaluate_base_permission",
            "seat_id": 0,
            "cycle_index": 0,
            "cycle_uptime_record": {"cycle_window": "1", "entries": []},
        }
        with self.assertRaises(InputError):
            parse_events([event])


if __name__ == "__main__":
    unittest.main()
