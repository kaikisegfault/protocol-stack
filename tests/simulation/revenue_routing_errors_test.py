#!/usr/bin/env python3
"""Negative, replay, overflow, atomicity, and input-shape tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import MAX_JSON_INTEGER, MAX_U64, InvariantError
from simulation.revenue_routing import contract as c
from simulation.revenue_routing.domain import (
    assert_invariants,
    initial_state,
    state_digest,
)
from simulation.revenue_routing.engine import (
    HANDLERS,
    apply_event,
    assert_balanced,
    simulate,
)
from simulation.revenue_routing.handlers_cycle import close_cycle
from simulation.revenue_routing.operations import Outcome, entry
from simulation.revenue_routing.validation import InputError, parse_events
from tests.simulation.revenue_routing_common import (
    FIXTURES,
    ROOT,
    close,
    fee,
    payment,
    research_events,
    vectors,
)


def one(event: dict) -> dict:
    return parse_events([event])[0]


class RejectionTest(unittest.TestCase):
    def assert_rejected(self, events: list[dict], expected: str) -> dict:
        result = simulate(events)
        record = result["records"][-1]
        self.assertFalse(record["accepted"], record)
        self.assertEqual(record["result"], expected)
        self.assertEqual(record["journal"], [])
        return result

    def test_a_replayed_payment_identifier(self) -> None:
        self.assert_rejected([payment(100), payment(200, event_id="again")], "REPLAY")

    def test_a_replayed_fee_identifier(self) -> None:
        self.assert_rejected([fee(100), fee(200, event_id="again")], "REPLAY")

    def test_a_zero_amount(self) -> None:
        self.assert_rejected([payment(0)], "ZERO_AMOUNT")
        self.assert_rejected([fee(0)], "ZERO_AMOUNT")

    def test_one_party_supplying_both_creator_roles(self) -> None:
        self.assert_rejected(
            [payment(100, project="creator-alpha", product="creator-alpha")],
            "DUPLICATE_CREATOR",
        )

    def test_closing_a_cycle_that_is_not_open(self) -> None:
        for cycle in (1, 5):
            with self.subTest(cycle=cycle):
                self.assert_rejected([close(cycle, [0])], "CYCLE_MISMATCH")
        self.assert_rejected(
            [close(0, [0]), close(0, [0], event_id="replay")], "CYCLE_MISMATCH"
        )

    def test_a_missing_or_unbound_snapshot(self) -> None:
        self.assert_rejected([close(0, [0], snapshot=None)], "MISSING_RESEARCH_INPUT")
        self.assert_rejected(
            [close(0, [0], snapshot_cycle=1)], "INVALID_RESEARCH_INPUT"
        )

    def test_a_rejected_event_consumes_no_identifier(self) -> None:
        result = simulate(
            [payment(0), payment(100, event_id="retry"), fee(0), fee(9, event_id="ok")]
        )
        state = result["final_state"]
        self.assertEqual(state["accepted_payment_ids"], ["payment-0001"])
        self.assertEqual(state["accepted_fee_ids"], ["fee-0001"])
        self.assertEqual(state["commercial_routed_total"], "100")


class OverflowTest(unittest.TestCase):
    def assert_overflow(self, state, event: dict) -> None:
        record = apply_event(state, one(event), 0)
        self.assertEqual(record["result"], "ARITHMETIC_OVERFLOW")
        self.assertEqual(record["journal"], [])

    def test_a_commercial_pool_at_the_maximum(self) -> None:
        state = initial_state()
        state.commercial_pool = MAX_U64
        self.assert_overflow(state, payment(100))

    def test_a_routed_total_at_the_maximum(self) -> None:
        state = initial_state()
        state.commercial_routed_total = MAX_U64
        self.assert_overflow(state, payment(100))

    def test_a_system_creator_balance_at_the_maximum(self) -> None:
        state = initial_state()
        state.system_creator_balance = MAX_U64
        self.assert_overflow(state, payment(100))

    def test_a_creator_balance_at_the_maximum(self) -> None:
        state = initial_state()
        state.creator_balances["creator-alpha"] = MAX_U64
        self.assert_overflow(state, payment(100))

    def test_a_fee_pool_at_the_maximum(self) -> None:
        state = initial_state()
        state.fee_pool = MAX_U64
        self.assert_overflow(state, fee(100))

    def test_a_seat_balance_at_the_maximum(self) -> None:
        state = initial_state()
        state.fee_pool = 10
        state.fee_routed_total = 10
        state.founder_fee_balances[0] = MAX_U64
        self.assert_overflow(state, close(0, [0, 1]))

    def test_a_cycle_counter_at_the_maximum(self) -> None:
        """The parser bounds a cycle index, so this guard is defence in depth."""
        state = initial_state()
        state.current_cycle = MAX_U64
        outcome = close_cycle(
            state,
            {
                "cycle_index": MAX_U64,
                "active_seats_result": {"cycle_index": MAX_U64, "seat_ids": []},
            },
        )
        self.assertEqual(outcome.code, "ARITHMETIC_OVERFLOW")


class AtomicityTest(unittest.TestCase):
    """Rejections must leave the full state digest unchanged."""

    def test_every_rejection_leaves_the_full_state_digest_unchanged(self) -> None:
        events = parse_events(research_events())
        state = initial_state()
        rejections = 0
        for index, event in enumerate(events):
            before = state_digest(state)
            record = apply_event(state, event, index)
            after = state_digest(state)
            with self.subTest(event=record["event_id"]):
                if record["accepted"]:
                    self.assertNotEqual(before, after)
                else:
                    self.assertEqual(before, after)
                    self.assertEqual(record["journal"], [])
                    rejections += 1
        self.assertEqual(rejections, int(vectors()["scenario.rejected_count"]))

    def test_a_handler_does_not_mutate_state_on_rejection(self) -> None:
        """The purity guarantee, checked directly rather than via the engine."""
        state = initial_state()
        before = state_digest(state)
        outcome = HANDLERS["route_commercial_payment"](state, one(payment(0)))
        self.assertFalse(outcome.accepted)
        self.assertIsNone(outcome.effect)
        self.assertEqual(state_digest(state), before)

    def test_an_accepted_handler_call_also_leaves_state_untouched(self) -> None:
        """Acceptance returns an effect; only the engine commits it."""
        state = initial_state()
        before = state_digest(state)
        outcome = HANDLERS["route_commercial_payment"](state, one(payment(100)))
        self.assertTrue(outcome.accepted)
        self.assertIsNotNone(outcome.effect)
        self.assertEqual(state_digest(state), before)

    def test_the_engine_rejects_a_handler_that_journals_the_wrong_amount(self) -> None:
        """assert_balanced re-derives the shares, so a lying handler is caught."""

        def lying(state, event):
            amount = int(event["amount_atomic"])
            return Outcome(
                code="OK",
                effect=None,
                journal=[
                    entry("payment", "decrease", amount),
                    entry("commercial_pool", "increase", amount),
                ],
            )

        state = initial_state()
        before = state_digest(state)
        original = HANDLERS["route_commercial_payment"]
        HANDLERS["route_commercial_payment"] = lying
        try:
            record = apply_event(state, one(payment(100)), 0)
        finally:
            HANDLERS["route_commercial_payment"] = original
        self.assertEqual(record["result"], "INVARIANT")
        self.assertEqual(record["journal"], [])
        self.assertEqual(state_digest(state), before)

    def test_a_forged_journal_is_rejected_directly(self) -> None:
        state = initial_state()
        event = one(payment(100))
        cases = [
            [entry("payment", "decrease", 100), entry("commercial_pool", "increase", 99)],
            [entry("payment", "decrease", 99), entry("commercial_pool", "increase", 99)],
            [
                entry("payment", "decrease", 100),
                entry("commercial_pool", "increase", 45),
                entry("creator:creator-beta", "increase", 45),
                entry("system_creator", "increase", 10),
            ],
        ]
        for index, journal in enumerate(cases):
            with self.subTest(case=index):
                with self.assertRaises(InvariantError):
                    assert_balanced(journal, state, event)


class StateInvariantTest(unittest.TestCase):
    def test_unaccounted_commercial_value_is_rejected(self) -> None:
        state = initial_state()
        state.commercial_routed_total = 100
        with self.assertRaises(InvariantError):
            assert_invariants(state)

    def test_unaccounted_fee_value_is_rejected(self) -> None:
        state = initial_state()
        state.fee_routed_total = 100
        with self.assertRaises(InvariantError):
            assert_invariants(state)

    def test_a_stored_zero_balance_is_rejected(self) -> None:
        state = initial_state()
        state.creator_balances["creator-alpha"] = 0
        with self.assertRaises(InvariantError):
            assert_invariants(state)

    def test_a_seat_beyond_the_capacity_is_rejected(self) -> None:
        state = initial_state()
        state.founder_fee_balances[c.FOUNDER_SEAT_CAPACITY] = 1
        state.fee_routed_total = 1
        with self.assertRaises(InvariantError):
            assert_invariants(state)


class InputShapeTest(unittest.TestCase):
    def assert_input_error(self, events: object) -> None:
        with self.assertRaises(InputError):
            parse_events(events)

    def test_malformed_events_are_rejected(self) -> None:
        base = payment(100)
        cases: list[object] = [
            {},
            [[]],
            [{"id": "a", "kind": "unknown"}],
            [{"id": "a", "kind": "route_transaction_fee"}],
            [dict(base, id="A")],
            [dict(base, extra=1)],
            [dict(base, amount_atomic=100)],
            [dict(base, amount_atomic="0100")],
            [dict(base, amount_atomic=str(MAX_U64 + 1))],
            [dict(base, project_creator_id=None)],
            [dict(base, product_creator_id="Creator")],
            [payment(1), payment(2, payment_id="other", event_id="payment-0001")],
        ]
        for index, events in enumerate(cases):
            with self.subTest(case=index):
                self.assert_input_error(events)

    def test_malformed_snapshots_are_rejected(self) -> None:
        cases: list[object] = [
            [close(0, [0], snapshot={"cycle_index": 0})],
            [close(0, [0], snapshot={"cycle_index": 0, "seat_ids": [0], "extra": 1})],
            [close(0, [0], snapshot={"cycle_index": 0, "seat_ids": "0"})],
            [close(0, [1, 0])],
            [close(0, [0, 0])],
            [close(0, [-1])],
            [close(0, [c.FOUNDER_SEAT_CAPACITY])],
            [close(0, list(range(c.FOUNDER_SEAT_CAPACITY + 1)))],
            [dict(close(0, [0]), cycle_index=MAX_JSON_INTEGER + 1)],
            [dict(close(0, [0]), cycle_index=True)],
        ]
        for index, events in enumerate(cases):
            with self.subTest(case=index):
                self.assert_input_error(events)

    def test_a_full_capacity_snapshot_is_accepted(self) -> None:
        events = parse_events([close(0, list(range(c.FOUNDER_SEAT_CAPACITY)))])
        self.assertEqual(
            len(events[0]["active_seats_result"]["seat_ids"]),
            c.FOUNDER_SEAT_CAPACITY,
        )

    def test_parsing_an_accepted_event_array_is_idempotent(self) -> None:
        parsed = parse_events(research_events())
        self.assertEqual(parse_events(parsed), parsed)


class CommandLineTest(unittest.TestCase):
    SCRIPT = ROOT / "simulation" / "revenue_routing" / "run.py"

    def test_the_runner_emits_the_recorded_trace_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(self.SCRIPT),
                    str(FIXTURES / "research-events-v1.json"),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
        recorded = vectors()
        self.assertEqual(result["trace_digest"], recorded["scenario.trace_digest"])
        self.assertEqual(result["state_digest"], recorded["scenario.state_digest"])

    def test_the_runner_rejects_a_floating_point_amount(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            events = Path(directory) / "events.json"
            events.write_text(
                '[{"id": "a", "kind": "route_transaction_fee",'
                ' "fee_id": "a", "amount_atomic": 1.5}]',
                encoding="utf-8",
            )
            completed = subprocess.run(
                [sys.executable, str(self.SCRIPT), str(events)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("floating-point", completed.stderr)


if __name__ == "__main__":
    unittest.main()
