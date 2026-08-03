#!/usr/bin/env python3
"""Negative, replay, binding, atomicity, and input-shape tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import MAX_JSON_INTEGER, MAX_U64, InvariantError
from simulation.founder_seats import contract as c
from simulation.founder_seats.domain import (
    Seat,
    assert_invariants,
    initial_state,
    state_digest,
)
from simulation.founder_seats.engine import apply_event, simulate
from simulation.founder_seats.validation import InputError, parse_events
from tests.simulation.founder_seat_common import (
    FIXTURES,
    ROOT,
    purchase,
    research_events,
    sale,
    vectors,
)


class RejectionTest(unittest.TestCase):
    def assert_rejected(self, events: list[dict], expected: str) -> dict:
        result = simulate(events)
        record = result["records"][-1]
        self.assertFalse(record["accepted"], record)
        self.assertEqual(record["result"], expected)
        self.assertEqual(record["journal"], [])
        return result

    def test_replayed_purchase_identifier(self) -> None:
        self.assert_rejected(
            [purchase(0), purchase(1, event_id="again", purchase_id="purchase-00000")],
            "REPLAY",
        )

    def test_unsold_or_out_of_range_referrer(self) -> None:
        for referrer in (0, 5, c.FOUNDER_SEAT_CAPACITY, MAX_JSON_INTEGER):
            with self.subTest(referrer=referrer):
                self.assert_rejected([purchase(0, referrer=referrer)], "INVALID_REFERRER")

    def test_missing_payment_result(self) -> None:
        self.assert_rejected([purchase(0, payment=None)], "MISSING_RESEARCH_INPUT")

    def test_unsettled_payment(self) -> None:
        self.assert_rejected([purchase(0, settled=False)], "PAYMENT_NOT_SETTLED")

    def test_payment_bound_to_the_wrong_action(self) -> None:
        cases = [
            {"seat_id": 7},
            {"price_usd_cents": "10001"},
            {"price_usd_cents": str(c.block_price_cents(1))},
            {"principal_id": "principal-other"},
            {"purchase_id": "some-other-purchase"},
        ]
        for binding in cases:
            with self.subTest(binding=binding):
                self.assert_rejected(
                    [purchase(0, binding=binding)], "INVALID_RESEARCH_INPUT"
                )

    def test_capacity_exhaustion_rejects_further_purchases(self) -> None:
        state = initial_state()
        state.seats_sold = c.FOUNDER_SEAT_CAPACITY
        record = apply_event(state, parse_events([purchase(0)])[0], 0)
        self.assertEqual(record["result"], "CAPACITY_EXHAUSTED")

    def test_an_ineligible_purchase_leaves_its_identifier_unconsumed(self) -> None:
        result = simulate(
            [
                purchase(0, settled=False),
                purchase(0, event_id="retry"),
            ]
        )
        self.assertEqual(result["records"][0]["result"], "PAYMENT_NOT_SETTLED")
        self.assertTrue(result["records"][1]["accepted"])
        self.assertEqual(result["final_state"]["seats_sold"], 1)
        self.assertEqual(
            result["final_state"]["accepted_purchase_ids"], ["purchase-00000"]
        )


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

    def test_rejections_consume_no_purchase_identifier(self) -> None:
        result = simulate(research_events())
        accepted = sum(1 for record in result["records"] if record["accepted"])
        self.assertEqual(
            len(result["final_state"]["accepted_purchase_ids"]),
            accepted,
        )
        self.assertEqual(result["final_state"]["seats_sold"], accepted)

    def test_a_handler_does_not_mutate_state_on_rejection(self) -> None:
        """The purity guarantee, checked directly rather than via the engine."""
        from simulation.founder_seats.handlers import purchase_seat

        state = initial_state()
        before = state_digest(state)
        outcome = purchase_seat(state, parse_events([purchase(0, payment=None)])[0])
        self.assertFalse(outcome.accepted)
        self.assertIsNone(outcome.effect)
        self.assertEqual(state_digest(state), before)

    def test_an_accepted_handler_call_also_leaves_state_untouched(self) -> None:
        """Acceptance returns an effect; only the engine commits it."""
        from simulation.founder_seats.handlers import purchase_seat

        state = initial_state()
        before = state_digest(state)
        outcome = purchase_seat(state, parse_events([purchase(0)])[0])
        self.assertTrue(outcome.accepted)
        self.assertIsNotNone(outcome.effect)
        self.assertEqual(state_digest(state), before)


class StateInvariantTest(unittest.TestCase):
    def test_a_seat_count_disagreeing_with_records_is_rejected(self) -> None:
        state = initial_state()
        state.seats_sold = 1
        with self.assertRaises(InvariantError):
            assert_invariants(state)

    def test_a_wrong_seat_price_is_rejected(self) -> None:
        state = initial_state()
        state.seats[0] = Seat("principal-alpha", 12_345, None)
        state.seats_sold = 1
        state.principal_seat_counts["principal-alpha"] = 1
        state.proceeds_usd_cents = 12_345
        with self.assertRaises(InvariantError):
            assert_invariants(state)

    def test_proceeds_disagreeing_with_seat_prices_are_rejected(self) -> None:
        state = initial_state()
        state.seats[0] = Seat("principal-alpha", c.seat_price_cents(0), None)
        state.seats_sold = 1
        state.principal_seat_counts["principal-alpha"] = 1
        state.proceeds_usd_cents = 1
        with self.assertRaises(InvariantError):
            assert_invariants(state)

    def test_a_principal_above_the_bound_is_rejected(self) -> None:
        state = initial_state()
        state.principal_seat_counts["principal-alpha"] = c.MAXIMUM_SEATS_PER_PERSON + 1
        with self.assertRaises(InvariantError):
            assert_invariants(state)

    def test_a_forward_or_self_referrer_is_rejected(self) -> None:
        for referrer in (0, 1):
            with self.subTest(referrer=referrer):
                state = initial_state()
                state.seats[0] = Seat("principal-alpha", c.seat_price_cents(0), referrer)
                state.seats_sold = 1
                state.principal_seat_counts["principal-alpha"] = 1
                state.proceeds_usd_cents = c.seat_price_cents(0)
                with self.assertRaises(InvariantError):
                    assert_invariants(state)


class InputShapeTest(unittest.TestCase):
    def assert_input_error(self, events: object) -> None:
        with self.assertRaises(InputError):
            parse_events(events)

    def test_malformed_events_are_rejected(self) -> None:
        base = purchase(0)
        cases: list[object] = [
            {},
            [[]],
            [{"id": "a", "kind": "unknown"}],
            [{"id": "a", "kind": "purchase_seat"}],
            [dict(base, id="A")],
            [dict(base, extra=1)],
            [dict(base, referrer_seat_id="0")],
            [dict(base, referrer_seat_id=MAX_JSON_INTEGER + 1)],
            [dict(base, referrer_seat_id=MAX_U64)],
            [dict(base, principal_id="Principal")],
            [purchase(0), purchase(1, event_id="purchase-00000")],
        ]
        for index, events in enumerate(cases):
            with self.subTest(case=index):
                self.assert_input_error(events)

    def test_malformed_payment_fixtures_are_rejected(self) -> None:
        for binding in (
            {"settled": "true"},
            {"price_usd_cents": 10_000},
            {"price_usd_cents": "010000"},
            {"price_usd_cents": str(MAX_U64 + 1)},
            {"seat_id": -1},
        ):
            with self.subTest(binding=binding):
                self.assert_input_error([purchase(0, binding=binding)])

    def test_a_missing_payment_field_is_rejected(self) -> None:
        event = purchase(0)
        del event["payment_result"]["settled"]
        self.assert_input_error([event])

    def test_parsing_an_accepted_event_array_is_idempotent(self) -> None:
        parsed = parse_events(sale(3))
        self.assertEqual(parse_events(parsed), parsed)


class CommandLineTest(unittest.TestCase):
    def test_the_runner_emits_the_recorded_trace_digest(self) -> None:
        script = ROOT / "simulation" / "founder_seats" / "run.py"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
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
        self.assertEqual(result["trace_digest"], vectors()["scenario.trace_digest"])
        self.assertEqual(result["state_digest"], vectors()["scenario.state_digest"])

    def test_the_runner_rejects_malformed_events(self) -> None:
        script = ROOT / "simulation" / "founder_seats" / "run.py"
        with tempfile.TemporaryDirectory() as directory:
            events = Path(directory) / "events.json"
            events.write_text('[{"id": "a", "kind": "unknown"}]', encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(script), str(events)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unsupported", completed.stderr)


if __name__ == "__main__":
    unittest.main()
