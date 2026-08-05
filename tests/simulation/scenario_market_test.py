#!/usr/bin/env python3
"""Seat concentration, routing population, and restart-equivalence tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.founder_seats import contract as seat_contract
from simulation.founder_seats.domain import initial_state as seat_state
from simulation.founder_seats.engine import apply_event as seat_apply
from simulation.founder_seats.engine import simulate as seat_simulate
from simulation.founder_seats.engine import state_digest as seat_digest
from simulation.founder_seats.validation import parse_events as seat_parse
from simulation.revenue_routing.domain import initial_state as routing_state
from simulation.revenue_routing.engine import apply_event as routing_apply
from simulation.revenue_routing.engine import simulate as routing_simulate
from simulation.revenue_routing.engine import state_digest as routing_digest
from simulation.revenue_routing.validation import parse_events as routing_parse
from simulation.scenarios import routing_population, seat_concentration
from tests.simulation.scenario_suite_common import total, vectors

SEAT_SPLITS = (1, 1_000, 50_000)
ROUTING_SPLITS = (1, 3, 180, 360)


def split_resume(parse, initial, apply, digest, events, index):
    """Apply events in two parts to one state and return its digest."""
    parsed = parse(events)
    state = initial()
    for position, event in enumerate(parsed[:index]):
        apply(state, event, position)
    for position, event in enumerate(parsed[index:], start=index):
        apply(state, event, position)
    return digest(state)


class SeatConcentrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.events = seat_concentration.events()
        cls.result = seat_simulate(cls.events)
        cls.recorded = vectors()

    def test_one_hundred_principals_absorb_the_whole_capacity(self) -> None:
        metrics = self.result["metrics"]
        self.assertEqual(metrics["seats_sold"], seat_contract.FOUNDER_SEAT_CAPACITY)
        self.assertEqual(metrics["seats_remaining"], 0)
        self.assertEqual(
            metrics["distinct_principal_count"],
            seat_concentration.MINIMUM_PRINCIPALS,
        )
        self.assertEqual(
            metrics["largest_principal_holding"],
            str(seat_contract.MAXIMUM_SEATS_PER_PERSON),
        )

    def test_every_principal_sits_exactly_on_the_bound(self) -> None:
        counts = self.result["final_state"]["principal_seat_counts"]
        self.assertEqual(len(counts), seat_concentration.MINIMUM_PRINCIPALS)
        for principal, held in counts.items():
            with self.subTest(principal=principal):
                self.assertEqual(
                    int(held), seat_contract.MAXIMUM_SEATS_PER_PERSON
                )

    def test_a_saturated_principal_never_consumes_a_seat(self) -> None:
        blocked = [
            record
            for record in self.result["records"]
            if record["result"] == "PRINCIPAL_SEAT_LIMIT"
        ]
        self.assertEqual(
            len(blocked), seat_concentration.over_limit_attempts()
        )
        for record in blocked:
            with self.subTest(event=record["event_id"]):
                self.assertEqual(record["journal"], [])

    def test_proceeds_equal_the_sum_of_every_recorded_seat_price(self) -> None:
        seats = self.result["final_state"]["seats"]
        summed = sum(int(seat["price_usd_cents"]) for seat in seats.values())
        self.assertEqual(
            summed, int(self.result["final_state"]["proceeds_usd_cents"])
        )
        self.assertEqual(summed, seat_contract.FULL_SALE_PROCEEDS_CENTS)

    def test_replay_is_refused_after_capacity_is_exhausted(self) -> None:
        codes = {
            record["event_id"]: record["result"]
            for record in self.result["records"]
        }
        self.assertEqual(codes["beyond-capacity"], "CAPACITY_EXHAUSTED")
        self.assertEqual(codes["probe-purchase-replay"], "REPLAY")

    def test_a_split_run_reaches_the_recorded_digest(self) -> None:
        for index in SEAT_SPLITS:
            with self.subTest(split=index):
                self.assertEqual(
                    split_resume(
                        seat_parse,
                        seat_state,
                        seat_apply,
                        seat_digest,
                        self.events,
                        index,
                    ),
                    self.result["state_digest"],
                )

    def test_a_replayed_prefix_reaches_its_own_digest(self) -> None:
        for index in SEAT_SPLITS:
            with self.subTest(prefix=index):
                replayed = seat_simulate(self.events[:index])["state_digest"]
                parsed = seat_parse(self.events[:index])
                state = seat_state()
                for position, event in enumerate(parsed):
                    seat_apply(state, event, position)
                self.assertEqual(replayed, seat_digest(state))


class RoutingPopulationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.events = routing_population.events()
        cls.result = routing_simulate(cls.events)
        cls.recorded = vectors()

    def test_the_population_changes_every_cycle_and_empties(self) -> None:
        sizes = [
            len(routing_population.active_seats(cycle))
            for cycle in range(routing_population.CYCLES)
        ]
        self.assertEqual(
            len(routing_population.empty_cycles()),
            int(self.recorded["routing.empty_cycles"]),
        )
        self.assertGreater(len(set(sizes)), 1)
        self.assertEqual(min(sizes), 0)

    def test_both_conservation_equations_hold(self) -> None:
        state = self.result["final_state"]
        commercial = (
            int(state["system_creator_balance"])
            + total(state["creator_balances"])
            + total(state["founder_commercial_balances"])
            + int(state["commercial_pool"])
            + int(state["commercial_carry"])
        )
        fees = (
            total(state["founder_fee_balances"])
            + int(state["fee_pool"])
            + int(state["fee_carry"])
        )
        self.assertEqual(commercial, int(state["commercial_routed_total"]))
        self.assertEqual(fees, int(state["fee_routed_total"]))

    def test_routed_totals_equal_the_summed_scenario_amounts(self) -> None:
        state = self.result["final_state"]
        payments = sum(
            routing_population.payment_amount(cycle)
            for cycle in range(routing_population.CYCLES)
        )
        fees = sum(
            routing_population.fee_amount(cycle)
            for cycle in range(routing_population.CYCLES)
        )
        self.assertEqual(int(state["commercial_routed_total"]), payments)
        self.assertEqual(int(state["fee_routed_total"]), fees)

    def test_an_empty_cycle_carries_its_whole_pool_forward(self) -> None:
        """Nothing is burned by an absent population, and it is paid later."""
        empty = routing_population.empty_cycles()[3]
        through_empty = routing_simulate(self.events[: 3 * (empty + 1)])
        state = through_empty["final_state"]
        self.assertEqual(state["commercial_pool"], "0")
        self.assertGreater(int(state["commercial_carry"]), 0)

        carried = int(state["commercial_carry"])
        credited_before = total(state["founder_commercial_balances"])
        following = routing_simulate(self.events[: 3 * (empty + 2)])
        after = following["final_state"]
        self.assertGreater(
            total(after["founder_commercial_balances"]),
            credited_before,
        )
        self.assertLess(int(after["commercial_carry"]), carried)

    def test_a_carry_stays_below_the_active_seat_count(self) -> None:
        """Read every close's journal rather than re-simulating each cycle."""
        checked = 0
        for record in self.result["records"]:
            if record["kind"] != "close_cycle" or not record["accepted"]:
                continue
            seats = routing_population.active_seats(record["index"] // 3)
            if not seats:
                continue
            for side in ("commercial", "fee"):
                carry = sum(
                    int(item["amount_atomic"])
                    for item in record["journal"]
                    if item["bucket"] == f"{side}_carry"
                )
                with self.subTest(event=record["event_id"], side=side):
                    self.assertLess(carry, len(seats))
            checked += 1
        self.assertEqual(
            checked,
            routing_population.CYCLES - len(routing_population.empty_cycles()),
        )

    def test_boundary_probes_are_refused(self) -> None:
        codes = {
            record["event_id"]: record["result"]
            for record in self.result["records"]
        }
        self.assertEqual(codes["probe-payment-replay"], "REPLAY")
        self.assertEqual(codes["probe-close-wrong-cycle"], "CYCLE_MISMATCH")
        self.assertEqual(
            codes["probe-close-stale-snapshot"], "INVALID_RESEARCH_INPUT"
        )

    def test_a_split_run_reaches_the_recorded_digest(self) -> None:
        for index in ROUTING_SPLITS:
            with self.subTest(split=index):
                self.assertEqual(
                    split_resume(
                        routing_parse,
                        routing_state,
                        routing_apply,
                        routing_digest,
                        self.events,
                        index,
                    ),
                    self.result["state_digest"],
                )

    def test_a_replayed_prefix_reaches_its_own_digest(self) -> None:
        for index in ROUTING_SPLITS:
            with self.subTest(prefix=index):
                replayed = routing_simulate(self.events[:index])["state_digest"]
                parsed = routing_parse(self.events[:index])
                state = routing_state()
                for position, event in enumerate(parsed):
                    routing_apply(state, event, position)
                self.assertEqual(replayed, routing_digest(state))


if __name__ == "__main__":
    unittest.main()
