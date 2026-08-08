#!/usr/bin/env python3
"""Founder Economy v2 transition rejections, atomicity, and input-shape errors."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.founder_economy_v2 import contract as c
from simulation.founder_economy_v2.engine import simulate
from simulation.founder_economy_v2.validation import InputError, parse_events
from tests.simulation.founder_economy_v2_common import (
    FAILED_BOUNDARY,
    FULL_WINDOW,
    accrue,
    activate,
    codes,
    direct,
    evaluate,
    evaluate_alone,
    exercise,
    manifest,
    record,
)

MAX_SEAT = c.FOUNDER_SEAT_CAPACITY - 1
MAX_CYCLE = c.ISSUANCE_CYCLES_PER_SEAT - 1


def run(events: list[dict]) -> dict:
    return simulate(manifest(), events)


def last(events: list[dict]) -> str:
    return codes(run(events))[-1]


class SeatActivationTest(unittest.TestCase):
    def test_seat_bounds(self) -> None:
        self.assertEqual(last([activate(c.FOUNDER_SEAT_CAPACITY)]), "CYCLE_RANGE")
        self.assertEqual(last([activate(MAX_SEAT)]), "OK")

    def test_self_referral_is_rejected(self) -> None:
        self.assertEqual(last([activate(5, 5)]), "INVALID_REFERRER")

    def test_out_of_range_referrer_is_rejected(self) -> None:
        self.assertEqual(
            last([activate(5, c.FOUNDER_SEAT_CAPACITY)]), "INVALID_REFERRER"
        )

    def test_unactivated_referrer_is_rejected(self) -> None:
        self.assertEqual(last([activate(5, 6)]), "SEAT_NOT_ACTIVATED")

    def test_replay_is_rejected(self) -> None:
        self.assertEqual(last([activate(0), activate(0)]), "REPLAY")


class BaseEvaluationTest(unittest.TestCase):
    def test_cycle_bounds(self) -> None:
        self.assertEqual(
            last([activate(0), evaluate_alone(0, c.ISSUANCE_CYCLES_PER_SEAT)]),
            "CYCLE_RANGE",
        )
        self.assertEqual(last([activate(0), evaluate_alone(0, MAX_CYCLE)]), "OK")

    def test_unactivated_seat_is_rejected_before_the_record(self) -> None:
        self.assertEqual(last([evaluate_alone(0, 0)]), "SEAT_NOT_ACTIVATED")

    def test_replay_is_rejected(self) -> None:
        self.assertEqual(
            last([activate(0), evaluate_alone(0, 0), evaluate_alone(0, 0)]), "REPLAY"
        )

    def test_a_missing_record_is_distinct_from_a_missing_placeholder(self) -> None:
        self.assertEqual(last([activate(0), evaluate(0, 0, None)]),
                         "MISSING_UPTIME_RECORD")

    def test_an_empty_record_is_rejected(self) -> None:
        self.assertEqual(
            last([activate(0), evaluate(0, 0, record(1, {}))]), "INVALID_UPTIME_RECORD"
        )

    def test_a_record_omitting_the_evaluated_seat_is_rejected(self) -> None:
        self.assertEqual(
            last([activate(0), activate(1), evaluate(0, 0, record(1, {1: FULL_WINDOW}))]),
            "INVALID_UPTIME_RECORD",
        )

    def test_a_duplicate_seat_is_rejected(self) -> None:
        duplicate = {
            "cycle_window": 1,
            "entries": [
                {"seat_id": 0, "uptime_seconds": 100},
                {"seat_id": 0, "uptime_seconds": 200},
            ],
        }
        self.assertEqual(
            last([activate(0), evaluate(0, 0, duplicate)]), "INVALID_UPTIME_RECORD"
        )

    def test_an_unactivated_listed_seat_is_rejected(self) -> None:
        self.assertEqual(
            last([activate(0), evaluate(0, 0, record(1, {0: FULL_WINDOW, 9: 100}))]),
            "INVALID_UPTIME_RECORD",
        )

    def test_an_out_of_range_listed_seat_is_rejected(self) -> None:
        self.assertEqual(
            last(
                [
                    activate(0),
                    evaluate(0, 0, record(1, {0: FULL_WINDOW,
                                              c.FOUNDER_SEAT_CAPACITY: 100})),
                ]
            ),
            "INVALID_UPTIME_RECORD",
        )

    def test_uptime_above_the_cycle_target_is_rejected(self) -> None:
        self.assertEqual(
            last([activate(0), evaluate(0, 0, record(1, {0: c.CYCLE_TARGET_SECONDS + 1}))]),
            "INVALID_UPTIME_RECORD",
        )
        self.assertEqual(
            last([activate(0), evaluate(0, 0, record(1, {0: c.CYCLE_TARGET_SECONDS}))]),
            "OK",
        )


class ReferralAccrualErrorTest(unittest.TestCase):
    def test_bounds(self) -> None:
        self.assertEqual(last([accrue(c.FOUNDER_SEAT_CAPACITY, 0)]), "CYCLE_RANGE")
        self.assertEqual(
            last([activate(0), accrue(0, c.ISSUANCE_CYCLES_PER_SEAT)]), "CYCLE_RANGE"
        )

    def test_unactivated_seat_is_rejected(self) -> None:
        self.assertEqual(last([accrue(0, 0)]), "SEAT_NOT_ACTIVATED")

    def test_replay_is_rejected(self) -> None:
        self.assertEqual(last([activate(0), accrue(0, 0), accrue(0, 0)]), "REPLAY")

    def test_an_unreferred_seat_is_never_rejected_for_lacking_a_referrer(self) -> None:
        """Version one answered this with SEAT_NOT_REFERRED; version two pays the pool."""
        result = run([activate(0), accrue(0, 0)])
        self.assertNotIn("SEAT_NOT_REFERRED", codes(result))
        self.assertEqual(codes(result), ["OK", "OK"])


class ExerciseTest(unittest.TestCase):
    def test_bounds(self) -> None:
        self.assertEqual(last([exercise(c.FOUNDER_SEAT_CAPACITY, 0)]), "CYCLE_RANGE")
        self.assertEqual(
            last([exercise(0, c.ISSUANCE_CYCLES_PER_SEAT)]), "CYCLE_RANGE"
        )

    def test_an_absent_permission_is_rejected(self) -> None:
        self.assertEqual(last([activate(0), exercise(0, 0)]), "PERMISSION_NOT_FOUND")

    def test_a_second_exercise_cannot_issue_again(self) -> None:
        events = [activate(0), evaluate_alone(0, 0), exercise(0, 0), exercise(0, 0)]
        result = run(events)
        self.assertEqual(codes(result), ["OK", "OK", "OK", "PERMISSION_NOT_FOUND"])
        self.assertEqual(
            int(result["metrics"]["issued_supply_atomic"]), c.BASE_PERMISSION_TOTAL
        )

    def test_the_evaluated_key_survives_exercise(self) -> None:
        events = [activate(0), evaluate_alone(0, 0), exercise(0, 0), evaluate_alone(0, 0)]
        self.assertEqual(codes(run(events))[-1], "REPLAY")


class DirectIssuanceErrorTest(unittest.TestCase):
    def test_unknown_channel(self) -> None:
        self.assertEqual(last([direct(channel="not_a_channel")]), "INVALID_CHANNEL")

    def test_zero_amount(self) -> None:
        self.assertEqual(last([direct(amount="0")]), "ZERO_AMOUNT")

    def test_replayed_decision(self) -> None:
        self.assertEqual(
            last([direct(decision="d1"), direct(decision="d1")]), "REPLAY"
        )

    def test_missing_placeholder(self) -> None:
        event = direct()
        event["eligibility_result"] = None
        self.assertEqual(last([event]), "MISSING_RESEARCH_INPUT")

    def test_unbound_placeholder(self) -> None:
        self.assertEqual(
            last([direct(amount="500", bound_amount="600")]), "INVALID_RESEARCH_INPUT"
        )

    def test_ineligible_result_consumes_no_decision(self) -> None:
        result = run(
            [direct(decision="d1", eligible=False), direct(decision="d1", eligible=True)]
        )
        self.assertEqual(codes(result), ["NOT_ELIGIBLE", "OK"])


class AtomicityTest(unittest.TestCase):
    """A rejected transition emits no journal and changes no state digest."""

    def test_every_rejection_is_a_complete_no_write(self) -> None:
        events = [
            activate(0),
            activate(1),
            evaluate_alone(0, 0),
            activate(0),
            evaluate_alone(0, 0),
            evaluate(1, 0, None),
            evaluate(1, 0, record(9, {})),
            accrue(9, 0),
            exercise(1, 0),
            direct(amount="0"),
            direct(channel=c.REFERRAL_CHANNEL),
        ]
        result = run(events)
        rejected = [item for item in result["records"] if not item["accepted"]]
        self.assertEqual(len(rejected), 8)
        for item in rejected:
            self.assertEqual(item["journal"], [])
            self.assertEqual(item["state_digest_before"], item["state_digest_after"])

    def test_a_rejected_evaluation_does_not_move_the_carry(self) -> None:
        events = [
            activate(0),
            activate(1),
            evaluate(0, 0, record(9, {0: FAILED_BOUNDARY, 1: 0})),
            evaluate(0, 0, record(9, {0: FAILED_BOUNDARY, 1: 0})),
        ]
        result = run(events)
        self.assertEqual(codes(result)[-1], "REPLAY")
        self.assertEqual(
            int(result["final_state"]["performance_carry_atomic"]),
            c.FOUNDER_OPERATOR_LEG,
        )


class InputShapeTest(unittest.TestCase):
    """Input-shape failures abort the run rather than producing a trace record."""

    def test_events_must_be_an_array(self) -> None:
        with self.assertRaises(InputError):
            parse_events({})

    def test_duplicate_event_ids_are_rejected(self) -> None:
        with self.assertRaises(InputError):
            parse_events([activate(0) | {"id": "x"}, activate(1) | {"id": "x"}])

    def test_unknown_event_kind_is_rejected(self) -> None:
        with self.assertRaises(InputError):
            parse_events([{"id": "a", "kind": "evaluate_referral_permission"}])

    def test_the_removed_permission_kind_field_is_rejected(self) -> None:
        event = exercise(0, 0)
        event["permission_kind"] = "base"
        with self.assertRaises(InputError):
            parse_events([event])

    def test_a_record_carrying_a_verdict_is_inexpressible(self) -> None:
        """The schema admits measurements only, so a verdict cannot be supplied."""
        event = evaluate_alone(0, 0)
        event["cycle_uptime_record"]["entries"][0]["active"] = True
        with self.assertRaises(InputError):
            parse_events([event])

    def test_a_record_carrying_a_winner_list_is_inexpressible(self) -> None:
        event = evaluate_alone(0, 0)
        event["cycle_uptime_record"]["winners"] = [1]
        with self.assertRaises(InputError):
            parse_events([event])

    def test_uptime_must_be_an_exact_json_integer(self) -> None:
        for value in (True, "64800", 1.5, -1):
            event = evaluate_alone(0, 0)
            event["cycle_uptime_record"]["entries"][0]["uptime_seconds"] = value
            with self.assertRaises(InputError):
                parse_events([event])

    def test_a_non_canonical_amount_is_rejected(self) -> None:
        for value in ("01", "-1", "1.0", "", " 1"):
            with self.assertRaises(InputError):
                parse_events([direct(amount=value)])


if __name__ == "__main__":
    unittest.main()
