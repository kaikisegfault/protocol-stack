#!/usr/bin/env python3
"""Negative, replay, cap, overflow, and atomic-failure tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.founder_economy import contract as c
from simulation.founder_economy.canonical import (
    MAX_JSON_INTEGER,
    MAX_U64,
    InvariantError,
)
from simulation.founder_economy.domain import (
    Leg,
    PendingPermission,
    assert_invariants,
    initial_state,
    permission_key,
    state_digest,
)
from simulation.founder_economy.engine import simulate
from simulation.founder_economy.handlers_issuance import exercise_permission
from simulation.founder_economy.handlers_permissions import evaluate_base_permission
from simulation.founder_economy.validation import InputError, parse_events
from tests.simulation.founder_economy_common import (
    activate,
    direct,
    evaluate_base,
    evaluate_referral,
    exercise,
    manifest,
    vectors,
)

ROYALTY = "system_creator_issuance_royalty"


def run(events: list[dict]) -> dict:
    return simulate(manifest(), events)


def performance(seat_id: int, cycle: int, entries: list[tuple[int, int]]) -> dict:
    return {
        "seat_id": seat_id,
        "cycle_index": cycle,
        "allocations": [
            {"seat_id": recipient, "amount_atomic": str(amount)}
            for recipient, amount in entries
        ],
    }


class RejectionTest(unittest.TestCase):
    """Every rejection must be deterministic and write no state."""

    def assert_rejected(self, events: list[dict], expected: str) -> dict:
        result = run(events)
        record = result["records"][-1]
        self.assertFalse(record["accepted"], record)
        self.assertEqual(record["result"], expected)
        self.assertEqual(record["journal"], [])
        self.assertEqual(record["state_digest_before"], record["state_digest_after"])
        return result

    def test_bounds_activation_and_referrer_failures(self) -> None:
        cases = [
            ([activate(c.FOUNDER_SEAT_CAPACITY)], "CYCLE_RANGE"),
            ([activate(0, referrer=0)], "INVALID_REFERRER"),
            ([activate(0, referrer=c.FOUNDER_SEAT_CAPACITY)], "INVALID_REFERRER"),
            ([activate(0, referrer=7)], "SEAT_NOT_ACTIVATED"),
            ([activate(0), activate(0, id="activate-0-again")], "REPLAY"),
            ([evaluate_base(0, 0)], "SEAT_NOT_ACTIVATED"),
            ([activate(0), evaluate_base(c.FOUNDER_SEAT_CAPACITY, 0)], "CYCLE_RANGE"),
            (
                [activate(0), evaluate_base(0, c.ISSUANCE_CYCLES_PER_SEAT)],
                "CYCLE_RANGE",
            ),
            ([activate(0), evaluate_referral(0, 0)], "SEAT_NOT_REFERRED"),
            ([activate(0), exercise(0, c.ISSUANCE_CYCLES_PER_SEAT)], "CYCLE_RANGE"),
        ]
        for events, expected in cases:
            with self.subTest(expected=expected, kind=events[-1]["kind"]):
                self.assert_rejected(events, expected)

    def test_permission_replay_and_exercise_failures(self) -> None:
        cases = [
            (
                [
                    activate(0),
                    evaluate_base(0, 0),
                    evaluate_base(0, 0, event_id="base-0-0-again"),
                ],
                "REPLAY",
            ),
            ([activate(0), exercise(0, 0)], "PERMISSION_NOT_FOUND"),
            (
                [
                    activate(0),
                    evaluate_base(0, 0),
                    exercise(0, 0),
                    exercise(0, 0, event_id="exercise-again"),
                ],
                "PERMISSION_NOT_FOUND",
            ),
            (
                [
                    activate(0),
                    evaluate_base(0, 0),
                    exercise(0, 0, "referral", event_id="wrong-kind"),
                ],
                "PERMISSION_NOT_FOUND",
            ),
        ]
        for events, expected in cases:
            with self.subTest(expected=expected, count=len(events)):
                self.assert_rejected(events, expected)

    def test_missing_and_unbound_research_inputs(self) -> None:
        cases = [
            (
                [activate(0), evaluate_base(0, 0, activity_result=None)],
                "MISSING_RESEARCH_INPUT",
            ),
            (
                [
                    activate(0),
                    evaluate_base(
                        0, 0, activity_result={"seat_id": 1, "cycle_index": 0, "active": True}
                    ),
                ],
                "INVALID_RESEARCH_INPUT",
            ),
            (
                [
                    activate(0),
                    evaluate_base(
                        0, 0, activity_result={"seat_id": 0, "cycle_index": 5, "active": True}
                    ),
                ],
                "INVALID_RESEARCH_INPUT",
            ),
            (
                [activate(0), activate(1), evaluate_base(0, 0, active=False)],
                "MISSING_RESEARCH_INPUT",
            ),
            (
                [
                    activate(0),
                    activate(1),
                    evaluate_base(
                        0,
                        0,
                        active=False,
                        performance=performance(1, 0, [(1, c.FOUNDER_OPERATOR_LEG)]),
                    ),
                ],
                "INVALID_RESEARCH_INPUT",
            ),
            (
                [
                    activate(0),
                    activate(1),
                    evaluate_base(
                        0,
                        0,
                        performance=performance(0, 0, [(1, c.FOUNDER_OPERATOR_LEG)]),
                    ),
                ],
                "INVALID_RESEARCH_INPUT",
            ),
            (
                [activate(3), activate(0, referrer=3), evaluate_referral(0, 0, active=False)],
                "MISSING_RESEARCH_INPUT",
            ),
            (
                [
                    activate(3),
                    activate(0, referrer=3),
                    evaluate_referral(
                        0,
                        0,
                        inactive_result={"seat_id": 0, "cycle_index": 0, "create": True},
                    ),
                ],
                "INVALID_RESEARCH_INPUT",
            ),
            (
                [
                    activate(3),
                    activate(0, referrer=3),
                    evaluate_referral(
                        0,
                        0,
                        active=False,
                        inactive_result={"seat_id": 9, "cycle_index": 0, "create": True},
                    ),
                ],
                "INVALID_RESEARCH_INPUT",
            ),
        ]
        for index, (events, expected) in enumerate(cases):
            with self.subTest(case=index, expected=expected):
                self.assert_rejected(events, expected)

    def test_invalid_performance_allocations(self) -> None:
        leg = c.FOUNDER_OPERATOR_LEG
        half = leg // 2
        cases = [
            [],
            [(1, half), (1, half)],
            [(0, leg)],
            [(1, half), (0, half)],
            [(1, leg - 1)],
            [(1, leg + 1)],
            [(1, half), (2, half - 1)],
            [(1, 0), (2, leg)],
            [(c.FOUNDER_SEAT_CAPACITY, leg)],
            [(9, leg)],
            [(1, half), (2, MAX_U64)],
        ]
        for index, entries in enumerate(cases):
            with self.subTest(case=index, entries=entries):
                events = [
                    activate(0),
                    activate(1),
                    activate(2),
                    evaluate_base(
                        0,
                        0,
                        active=False,
                        performance=performance(0, 0, entries),
                    ),
                ]
                self.assert_rejected(events, "INVALID_PERFORMANCE_ALLOCATION")

    def test_direct_channel_failures(self) -> None:
        recorded = vectors()
        channel = recorded["direct_fixture.channel"]
        cases = [
            ([direct("venture_escrow", "decision-1", "beneficiary-1", 1)], "INVALID_CHANNEL"),
            ([direct("unknown-channel", "decision-1", "beneficiary-1", 1)], "INVALID_CHANNEL"),
            ([direct(channel, "decision-1", "beneficiary-1", 0)], "ZERO_AMOUNT"),
            (
                [direct(channel, "decision-1", "beneficiary-1", 1, eligible=None)],
                "MISSING_RESEARCH_INPUT",
            ),
            (
                [
                    direct(
                        channel,
                        "decision-1",
                        "beneficiary-1",
                        1,
                        binding={"amount_atomic": "2"},
                    )
                ],
                "INVALID_RESEARCH_INPUT",
            ),
            (
                [
                    direct(
                        channel,
                        "decision-1",
                        "beneficiary-1",
                        1,
                        binding={"beneficiary_id": "beneficiary-2"},
                    )
                ],
                "INVALID_RESEARCH_INPUT",
            ),
            (
                [
                    direct(
                        channel,
                        "decision-1",
                        "beneficiary-1",
                        1,
                        binding={"decision_id": "decision-2"},
                    )
                ],
                "INVALID_RESEARCH_INPUT",
            ),
            (
                [
                    direct(
                        channel,
                        "decision-1",
                        "beneficiary-1",
                        1,
                        binding={"channel": "hub_verified_user_incentives"},
                    )
                ],
                "INVALID_RESEARCH_INPUT",
            ),
            (
                [direct(channel, "decision-1", "beneficiary-1", 1, eligible=False)],
                "NOT_ELIGIBLE",
            ),
            (
                [
                    direct(channel, "decision-1", "beneficiary-1", 1),
                    direct(channel, "decision-1", "beneficiary-1", 1, event_id="replay"),
                ],
                "REPLAY",
            ),
            (
                [direct(channel, "decision-1", "beneficiary-1", c.CHANNEL_CAPS[channel] + 1)],
                "CHANNEL_CAP",
            ),
        ]
        for index, (events, expected) in enumerate(cases):
            with self.subTest(case=index, expected=expected):
                self.assert_rejected(events, expected)

    def test_an_ineligible_decision_identifier_stays_unconsumed(self) -> None:
        channel = "liquidity_mining"
        result = run(
            [
                direct(channel, "decision-1", "beneficiary-1", 5, eligible=False),
                direct(channel, "decision-1", "beneficiary-1", 5, event_id="retry"),
            ]
        )
        self.assertEqual(result["records"][0]["result"], "NOT_ELIGIBLE")
        self.assertTrue(result["records"][1]["accepted"])
        self.assertEqual(result["metrics"]["issued_supply_atomic"], "5")


class SeededStateTest(unittest.TestCase):
    """Cases that require a pre-state the event schema cannot construct."""

    def test_a_base_leg_above_its_channel_cap_is_rejected(self) -> None:
        state = initial_state()
        state.seats[0] = None
        state.channels[ROYALTY].issued_atomic = c.CHANNEL_CAPS[ROYALTY] - 999_999_999
        before = state_digest(state)
        outcome = evaluate_base_permission(state, parse_events([evaluate_base(0, 0)])[0])
        self.assertEqual(outcome.code, "CHANNEL_CAP")
        self.assertEqual(outcome.journal, [])
        self.assertEqual(state_digest(state), before)

    def test_a_base_leg_exactly_at_its_channel_cap_is_accepted(self) -> None:
        state = initial_state()
        state.seats[0] = None
        state.channels[ROYALTY].issued_atomic = c.CHANNEL_CAPS[ROYALTY] - 1_000_000_000
        outcome = evaluate_base_permission(state, parse_events([evaluate_base(0, 0)])[0])
        self.assertEqual(outcome.code, "OK")
        self.assertEqual(state.capacity(ROYALTY), 0)

    def test_a_custody_credit_that_would_exceed_u64_is_rejected(self) -> None:
        state = self._pending_permission_state(total=c.REFERRAL_AMOUNT)
        state.typed_custody["founder_seat:00001"] = MAX_U64
        before = state_digest(state)
        outcome = exercise_permission(
            state, parse_events([exercise(0, 0, "referral")])[0]
        )
        self.assertEqual(outcome.code, "ARITHMETIC_OVERFLOW")
        self.assertEqual(outcome.journal, [])
        self.assertEqual(state_digest(state), before)

    def test_a_permission_whose_legs_do_not_sum_to_its_total_is_rejected(self) -> None:
        state = self._pending_permission_state(total=c.REFERRAL_AMOUNT + 1)
        before = state_digest(state)
        outcome = exercise_permission(
            state, parse_events([exercise(0, 0, "referral")])[0]
        )
        self.assertEqual(outcome.code, "INVARIANT")
        self.assertEqual(outcome.journal, [])
        self.assertEqual(state_digest(state), before)

    def _pending_permission_state(self, total: int):
        state = initial_state()
        state.seats[1] = None
        state.seats[0] = 1
        key = permission_key(0, 0, "referral")
        legs = (
            Leg(
                channel=c.REFERRAL_CHANNEL,
                custody_key="founder_seat:00001",
                amount_atomic=c.REFERRAL_AMOUNT,
            ),
        )
        state.channels[c.REFERRAL_CHANNEL].outstanding_atomic = c.REFERRAL_AMOUNT
        state.pending_permissions[key] = PendingPermission(
            seat_id=0,
            cycle_index=0,
            kind="referral",
            total_atomic=total,
            legs=legs,
        )
        state.evaluated_permission_keys.add(key)
        return state


class InputShapeTest(unittest.TestCase):
    """Shape-invalid input aborts the run instead of producing a trace."""

    def assert_input_error(self, events: object) -> None:
        with self.assertRaises(InputError):
            parse_events(events)

    def test_malformed_events_are_rejected(self) -> None:
        cases: list[object] = [
            {},
            [[]],
            [{"id": "a", "kind": "unknown"}],
            [{"id": "a", "kind": "activate_seat"}],
            [{"id": "a", "kind": "activate_seat", "seat_id": 0}],
            [{"id": "A", "kind": "activate_seat", "seat_id": 0, "referrer_seat_id": None}],
            [{"id": "a", "kind": "activate_seat", "seat_id": "0", "referrer_seat_id": None}],
            [{"id": "a", "kind": "activate_seat", "seat_id": -1, "referrer_seat_id": None}],
            [{"id": "a", "kind": "activate_seat", "seat_id": True, "referrer_seat_id": None}],
            [activate(0), activate(1, id="activate-0")],
            [exercise(0, 0, "other")],
            [direct("liquidity_mining", "d1", "b1", 0) | {"amount_atomic": "00"}],
            [direct("liquidity_mining", "d1", "b1", 0) | {"amount_atomic": str(MAX_U64 + 1)}],
            [direct("liquidity_mining", "d1", "b1", 0) | {"amount_atomic": 1}],
        ]
        for index, events in enumerate(cases):
            with self.subTest(case=index):
                self.assert_input_error(events)

    def test_a_non_boolean_research_flag_is_rejected(self) -> None:
        event = evaluate_base(0, 0)
        event["activity_result"]["active"] = "true"
        self.assert_input_error([event])

    def test_counts_above_the_exact_json_integer_bound_are_rejected(self) -> None:
        """A count that could not be canonicalized must not reach a digest."""
        for value in (MAX_JSON_INTEGER + 1, MAX_U64, 10**18):
            with self.subTest(value=value):
                self.assert_input_error([activate(value)])
                self.assert_input_error([activate(0, referrer=value)])
                self.assert_input_error([exercise(0, value)])

    def test_the_largest_exact_count_parses_and_is_rejected_at_runtime(self) -> None:
        result = run([activate(MAX_JSON_INTEGER)])
        self.assertEqual(result["records"][-1]["result"], "CYCLE_RANGE")


class StateInvariantTest(unittest.TestCase):
    def test_an_unknown_referrer_violates_the_seat_invariant(self) -> None:
        state = initial_state()
        state.seats[0] = 7
        with self.assertRaises(InvariantError):
            assert_invariants(state)

    def test_a_self_referrer_violates_the_seat_invariant(self) -> None:
        state = initial_state()
        state.seats[0] = 0
        with self.assertRaises(InvariantError):
            assert_invariants(state)

    def test_custody_that_does_not_equal_issued_supply_is_rejected(self) -> None:
        state = initial_state()
        state.typed_custody["venture_escrow:global"] = 1
        with self.assertRaises(InvariantError):
            assert_invariants(state)

    def test_a_channel_above_its_cap_is_rejected(self) -> None:
        state = initial_state()
        state.channels[c.REFERRAL_CHANNEL].outstanding_atomic = (
            c.CHANNEL_CAPS[c.REFERRAL_CHANNEL] + 1
        )
        with self.assertRaises(InvariantError):
            assert_invariants(state)

    def test_parsing_an_accepted_event_array_is_idempotent(self) -> None:
        events = [activate(3), activate(0, referrer=3), evaluate_base(0, 0), exercise(0, 0)]
        parsed = parse_events(events)
        self.assertEqual(parse_events(parsed), parsed)


if __name__ == "__main__":
    unittest.main()
