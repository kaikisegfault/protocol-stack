#!/usr/bin/env python3
"""Scenario, distribution, conservation, and determinism tests."""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.revenue_routing import contract as c
from simulation.revenue_routing.domain import assert_invariants, initial_state
from simulation.revenue_routing.engine import apply_event, simulate
from simulation.revenue_routing.validation import parse_events
from tests.simulation.revenue_routing_common import (
    close,
    fee,
    payment,
    research_events,
    vectors,
)


def totals(state_value: dict) -> tuple[int, int]:
    commercial = (
        int(state_value["system_creator_balance"])
        + sum(int(v) for v in state_value["creator_balances"].values())
        + sum(int(v) for v in state_value["founder_commercial_balances"].values())
        + int(state_value["commercial_pool"])
        + int(state_value["commercial_carry"])
    )
    fees = (
        sum(int(v) for v in state_value["founder_fee_balances"].values())
        + int(state_value["fee_pool"])
        + int(state_value["fee_carry"])
    )
    return commercial, fees


class ScenarioTest(unittest.TestCase):
    def setUp(self) -> None:
        self.result = simulate(research_events())
        self.recorded = vectors()

    def test_the_recorded_digests_are_reproduced(self) -> None:
        for key, field in (
            ("scenario.events_digest", "events_digest"),
            ("scenario.trace_digest", "trace_digest"),
            ("scenario.state_digest", "state_digest"),
            ("scenario.result_digest", "result_digest"),
        ):
            with self.subTest(key=key):
                self.assertEqual(self.result[field], self.recorded[key])

    def test_the_recorded_trace_codes_are_reproduced(self) -> None:
        for index, record in enumerate(self.result["records"]):
            with self.subTest(index=index):
                self.assertEqual(
                    record["event_id"], self.recorded[f"record{index}.event_id"]
                )
                self.assertEqual(record["result"], self.recorded[f"record{index}.result"])

    def test_the_recorded_final_totals_are_reproduced(self) -> None:
        state = self.result["final_state"]
        pairs = (
            ("scenario.commercial_routed_total", "commercial_routed_total"),
            ("scenario.fee_routed_total", "fee_routed_total"),
            ("scenario.commercial_carry", "commercial_carry"),
            ("scenario.fee_carry", "fee_carry"),
            ("scenario.system_creator_balance", "system_creator_balance"),
        )
        for key, field in pairs:
            with self.subTest(key=key):
                self.assertEqual(state[field], self.recorded[key])
        self.assertEqual(
            state["current_cycle"], int(self.recorded["scenario.cycles_closed"])
        )

    def test_repeated_runs_are_byte_identical(self) -> None:
        again = simulate(research_events())
        self.assertEqual(again, self.result)

    def test_the_invariant_stride_does_not_change_the_result(self) -> None:
        for stride in (0, 1, 3, 1_000):
            with self.subTest(stride=stride):
                self.assertEqual(
                    simulate(research_events(), invariant_stride=stride), self.result
                )


class ConservationTest(unittest.TestCase):
    def test_conservation_holds_after_every_accepted_event(self) -> None:
        from simulation.revenue_routing.domain import state_value

        events = parse_events(research_events())
        state = initial_state()
        for index, event in enumerate(events):
            apply_event(state, event, index)
            assert_invariants(state)
            commercial, fees = totals(state_value(state))
            with self.subTest(index=index):
                self.assertEqual(commercial, state.commercial_routed_total)
                self.assertEqual(fees, state.fee_routed_total)

    def test_the_scenario_conserves_every_routed_unit(self) -> None:
        result = simulate(research_events())
        commercial, fees = totals(result["final_state"])
        recorded = vectors()
        self.assertEqual(
            commercial, int(recorded["conservation.commercial_credited_and_pooled"])
        )
        self.assertEqual(fees, int(recorded["conservation.fee_credited_and_pooled"]))


class FeeIndependenceTest(unittest.TestCase):
    def test_fees_do_not_touch_any_commercial_bucket(self) -> None:
        result = simulate([fee(1_000), fee(7, fee_id="fee-0002")])
        state = result["final_state"]
        self.assertEqual(state["commercial_routed_total"], "0")
        self.assertEqual(state["commercial_pool"], "0")
        self.assertEqual(state["system_creator_balance"], "0")
        self.assertEqual(state["creator_balances"], {})
        self.assertEqual(state["fee_pool"], "1007")

    def test_removing_fee_events_leaves_commercial_routing_unchanged(self) -> None:
        events = research_events()
        full = simulate(events)["final_state"]
        without = simulate(
            [e for e in events if e["kind"] != "route_transaction_fee"]
        )["final_state"]
        for field in ("commercial_routed_total", "system_creator_balance"):
            with self.subTest(field=field):
                self.assertEqual(full[field], without[field])
        self.assertEqual(full["creator_balances"], without["creator_balances"])

    def test_a_fee_is_never_deducted_from_a_commercial_payment(self) -> None:
        amount = 1_000 * c.ATOMIC_UNITS_PER_DISPLAY_UNIT
        alone = simulate([payment(amount)])["final_state"]
        with_fee = simulate([payment(amount), fee(amount)])["final_state"]
        self.assertEqual(alone["commercial_pool"], with_fee["commercial_pool"])
        self.assertEqual(
            alone["system_creator_balance"], with_fee["system_creator_balance"]
        )
        self.assertEqual(with_fee["fee_pool"], str(amount))


class DistributionTest(unittest.TestCase):
    def test_every_active_seat_receives_the_same_amount(self) -> None:
        seats = list(range(7))
        result = simulate([payment(1_000_000), fee(999), close(0, seats)])
        state = result["final_state"]
        credited = set(state["founder_commercial_balances"].values())
        self.assertEqual(len(credited), 1)
        self.assertEqual(len(state["founder_commercial_balances"]), len(seats))
        self.assertEqual(int(state["commercial_carry"]), 450_000 % len(seats))
        self.assertEqual(int(state["fee_carry"]), 999 % len(seats))

    def test_an_empty_snapshot_carries_the_whole_pool_forward(self) -> None:
        result = simulate([payment(1_000_000), fee(999), close(0, [])])
        state = result["final_state"]
        self.assertEqual(state["founder_commercial_balances"], {})
        self.assertEqual(state["founder_fee_balances"], {})
        self.assertEqual(state["commercial_pool"], "0")
        self.assertEqual(int(state["commercial_carry"]), 450_000)
        self.assertEqual(int(state["fee_carry"]), 999)

    def test_a_pool_smaller_than_the_population_credits_nobody(self) -> None:
        result = simulate([fee(3), close(0, [0, 1, 2, 3, 4])])
        state = result["final_state"]
        self.assertEqual(state["founder_fee_balances"], {})
        self.assertEqual(state["fee_carry"], "3")

    def test_a_carry_is_distributed_by_a_later_cycle(self) -> None:
        events = [
            fee(3),
            close(0, [0, 1, 2, 3, 4]),
            fee(7, fee_id="fee-0002"),
            close(1, [0, 1, 2, 3, 4]),
        ]
        state = simulate(events)["final_state"]
        self.assertEqual(set(state["founder_fee_balances"].values()), {"2"})
        self.assertEqual(state["fee_carry"], "0")
        self.assertEqual(state["fee_routed_total"], "10")

    def test_an_empty_cycle_still_advances_with_an_empty_journal(self) -> None:
        result = simulate([close(0, [0, 1])])
        self.assertTrue(result["records"][0]["accepted"])
        self.assertEqual(result["records"][0]["journal"], [])
        self.assertEqual(result["final_state"]["current_cycle"], 1)

    def test_the_complete_seat_population_distributes_in_bounded_time(self) -> None:
        """The founder-directed population is a scenario this model must run."""
        seats = list(range(c.FOUNDER_SEAT_CAPACITY))
        amount = c.FOUNDER_SEAT_CAPACITY * c.ATOMIC_UNITS_PER_DISPLAY_UNIT
        started = time.monotonic()
        result = simulate([payment(amount), fee(amount), close(0, seats)])
        elapsed = time.monotonic() - started
        state = result["final_state"]
        self.assertEqual(len(state["founder_commercial_balances"]), len(seats))
        self.assertEqual(
            set(state["founder_fee_balances"].values()),
            {str(amount // c.FOUNDER_SEAT_CAPACITY)},
        )
        self.assertLess(elapsed, 30.0)


if __name__ == "__main__":
    unittest.main()
