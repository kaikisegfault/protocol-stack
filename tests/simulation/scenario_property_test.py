#!/usr/bin/env python3
"""Conservation properties over seeded random event sequences.

Every assertion here is written against the models' published result values.
Calling a model's own `assert_invariants` would re-run the check its engine
already ran, so a defect in an invariant could satisfy the test meant to catch
it.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.escrow_payout import contract as escrow_contract
from simulation.escrow_payout.engine import simulate as escrow_simulate
from simulation.founder_economy import contract as c
from simulation.founder_economy.engine import simulate as economy_simulate
from simulation.founder_economy.manifest import load_manifest_file
from simulation.founder_seats import contract as seat_contract
from simulation.founder_seats.engine import simulate as seat_simulate
from simulation.revenue_routing.engine import simulate as routing_simulate
from simulation.scenarios import (
    random_economy,
    random_escrow,
    random_routing,
    random_seats,
)
from simulation.scenarios.suite import MANIFEST_PATH
from tests.simulation.scenario_suite_common import rejected, total

SEEDS = (1, 2, 3, 5, 8, 13, 21)

# Seed 5 leaves every escrow untouched, which would satisfy the conservation
# equations vacuously, so the escrow properties use a set in which every seed
# releases value.
ESCROW_SEEDS = (1, 2, 3, 6, 8, 13, 21)

ECONOMY_EVENTS = 160
MARKET_EVENTS = 400
ESCROW_EVENTS = 300


class EconomyPropertyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest_file(MANIFEST_PATH)

    def results(self):
        for seed in SEEDS:
            events = random_economy.economy_events(seed, ECONOMY_EVENTS)
            yield seed, economy_simulate(self.manifest, events)

    def test_supply_is_always_fully_accounted(self) -> None:
        for seed, result in self.results():
            metrics = result["metrics"]
            issued = int(metrics["issued_supply_atomic"])
            outstanding = int(metrics["outstanding_permissions_atomic"])
            remaining = int(metrics["remaining_capacity_atomic"])
            with self.subTest(seed=seed):
                self.assertEqual(
                    issued + outstanding + remaining, c.MAXIMUM_SUPPLY_ATOMIC
                )

    def test_custody_always_equals_issued_supply(self) -> None:
        for seed, result in self.results():
            metrics = result["metrics"]
            custody = result["final_state"]["typed_custody"]
            with self.subTest(seed=seed):
                self.assertEqual(
                    total(custody), int(metrics["issued_supply_atomic"])
                )
                self.assertTrue(
                    all(int(value) > 0 for value in custody.values())
                )

    def test_no_channel_ever_exceeds_its_cap(self) -> None:
        for seed, result in self.results():
            channels = result["metrics"]["channels"]
            for channel, _, cap in c.CHANNELS:
                entry = channels[channel]
                with self.subTest(seed=seed, channel=channel):
                    self.assertLessEqual(
                        int(entry["issued_atomic"])
                        + int(entry["outstanding_atomic"]),
                        cap,
                    )

    def test_a_rejection_never_writes_or_journals(self) -> None:
        for seed, result in self.results():
            refused = rejected(result)
            with self.subTest(seed=seed):
                self.assertTrue(refused)
                for record in refused:
                    self.assertEqual(record["journal"], [])
                    self.assertEqual(
                        record["state_digest_before"],
                        record["state_digest_after"],
                    )

    def test_every_sequence_issues_value(self) -> None:
        """A property satisfied by an empty state is not evidence."""
        for seed, result in self.results():
            with self.subTest(seed=seed):
                self.assertGreater(
                    int(result["metrics"]["issued_supply_atomic"]), 0
                )

    def test_the_same_seed_reproduces_the_same_digest(self) -> None:
        events = random_economy.economy_events(SEEDS[0], ECONOMY_EVENTS)
        first = economy_simulate(self.manifest, events)
        second = economy_simulate(self.manifest, events)
        self.assertEqual(first["result_digest"], second["result_digest"])


class SeatPropertyTest(unittest.TestCase):
    def results(self):
        for seed in SEEDS:
            events = random_seats.seat_events(seed, MARKET_EVENTS)
            yield seed, seat_simulate(events)

    def test_prices_sum_to_proceeds_and_counts_to_seats_sold(self) -> None:
        for seed, result in self.results():
            state = result["final_state"]
            prices = sum(
                int(seat["price_usd_cents"]) for seat in state["seats"].values()
            )
            counts = total(state["principal_seat_counts"])
            with self.subTest(seed=seed):
                self.assertEqual(prices, int(state["proceeds_usd_cents"]))
                self.assertEqual(counts, state["seats_sold"])
                self.assertEqual(len(state["seats"]), state["seats_sold"])

    def test_no_bound_is_ever_exceeded(self) -> None:
        for seed, result in self.results():
            state = result["final_state"]
            with self.subTest(seed=seed):
                self.assertLessEqual(
                    state["seats_sold"], seat_contract.FOUNDER_SEAT_CAPACITY
                )
                for held in state["principal_seat_counts"].values():
                    self.assertLessEqual(
                        int(held), seat_contract.MAXIMUM_SEATS_PER_PERSON
                    )
                self.assertLessEqual(
                    int(state["proceeds_usd_cents"]),
                    seat_contract.FULL_SALE_PROCEEDS_CENTS,
                )

    def test_every_sequence_sells_seats(self) -> None:
        for seed, result in self.results():
            with self.subTest(seed=seed):
                self.assertGreater(result["final_state"]["seats_sold"], 0)

    def test_a_rejection_never_journals(self) -> None:
        for seed, result in self.results():
            with self.subTest(seed=seed):
                for record in rejected(result):
                    self.assertEqual(record["journal"], [])


class RoutingPropertyTest(unittest.TestCase):
    def results(self):
        for seed in SEEDS:
            events = random_routing.routing_events(seed, MARKET_EVENTS)
            yield seed, routing_simulate(events)

    def test_commercial_value_is_credited_or_pooled(self) -> None:
        for seed, result in self.results():
            state = result["final_state"]
            credited = (
                int(state["system_creator_balance"])
                + total(state["creator_balances"])
                + total(state["founder_commercial_balances"])
                + int(state["commercial_pool"])
                + int(state["commercial_carry"])
            )
            with self.subTest(seed=seed):
                self.assertEqual(
                    credited, int(state["commercial_routed_total"])
                )

    def test_fee_value_is_credited_or_pooled(self) -> None:
        for seed, result in self.results():
            state = result["final_state"]
            credited = (
                total(state["founder_fee_balances"])
                + int(state["fee_pool"])
                + int(state["fee_carry"])
            )
            with self.subTest(seed=seed):
                self.assertEqual(credited, int(state["fee_routed_total"]))

    def test_every_sequence_routes_value(self) -> None:
        for seed, result in self.results():
            state = result["final_state"]
            with self.subTest(seed=seed):
                self.assertGreater(int(state["commercial_routed_total"]), 0)
                self.assertGreater(int(state["fee_routed_total"]), 0)

    def test_no_stored_balance_is_zero(self) -> None:
        for seed, result in self.results():
            state = result["final_state"]
            balances = (
                state["creator_balances"],
                state["founder_commercial_balances"],
                state["founder_fee_balances"],
            )
            with self.subTest(seed=seed):
                for entries in balances:
                    self.assertTrue(
                        all(int(value) > 0 for value in entries.values())
                    )


class EscrowPropertyTest(unittest.TestCase):
    def results(self):
        for seed in ESCROW_SEEDS:
            events = random_escrow.escrow_events(seed, ESCROW_EVENTS)
            yield seed, escrow_simulate(events)

    def test_each_escrow_conserves_independently(self) -> None:
        for seed, result in self.results():
            state = result["final_state"]
            for escrow_id in escrow_contract.ESCROW_IDS:
                opening = int(state["opening_custody"][escrow_id])
                paid = int(state["paid_out_total"][escrow_id])
                available = int(state["available_custody"][escrow_id])
                charged = sum(
                    int(capability["spent"])
                    for capability in state["capabilities"].values()
                    if capability["escrow_id"] == escrow_id
                )
                with self.subTest(seed=seed, escrow=escrow_id):
                    self.assertEqual(available + paid, opening)
                    self.assertEqual(
                        total(state["recipient_balances"][escrow_id]), paid
                    )
                    self.assertEqual(charged, paid)

    def test_every_sequence_releases_value(self) -> None:
        for seed, result in self.results():
            state = result["final_state"]
            with self.subTest(seed=seed):
                self.assertGreater(total(state["paid_out_total"]), 0)

    def test_custody_never_rises_after_the_bind(self) -> None:
        for seed, result in self.results():
            state = result["final_state"]
            for escrow_id in escrow_contract.ESCROW_IDS:
                with self.subTest(seed=seed, escrow=escrow_id):
                    self.assertLessEqual(
                        int(state["available_custody"][escrow_id]),
                        int(state["opening_custody"][escrow_id]),
                    )
                    self.assertLessEqual(
                        int(state["opening_custody"][escrow_id]),
                        escrow_contract.ESCROW_CAPS[escrow_id],
                    )

    def test_no_payout_touches_two_escrows(self) -> None:
        for seed, result in self.results():
            for record in result["records"]:
                if record["kind"] != "execute_payout" or not record["accepted"]:
                    continue
                escrows = {
                    item["bucket"].split(":")[1] for item in record["journal"]
                }
                with self.subTest(seed=seed, event=record["event_id"]):
                    self.assertEqual(len(escrows), 1)

    def test_a_rejection_never_journals(self) -> None:
        for seed, result in self.results():
            with self.subTest(seed=seed):
                for record in rejected(result):
                    self.assertEqual(record["journal"], [])


if __name__ == "__main__":
    unittest.main()
