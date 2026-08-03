#!/usr/bin/env python3
"""Seat sale accounting, ownership bounds, and the complete-sale scenario."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.founder_seats import contract as c
from simulation.founder_seats.engine import simulate
from simulation.founder_seats.handlers import journal_delta
from tests.simulation.founder_seat_common import purchase, sale, vectors


def totals(journal: list[dict]) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in journal:
        result[item["bucket"]] = result.get(item["bucket"], 0) + journal_delta(item)
    return result


class PurchaseAccountingTest(unittest.TestCase):
    def test_a_purchase_allocates_the_next_seat_at_its_block_price(self) -> None:
        result = simulate([purchase(0), purchase(1), purchase(2)])
        self.assertTrue(all(record["accepted"] for record in result["records"]))
        state = result["final_state"]
        self.assertEqual(state["seats_sold"], 3)
        self.assertEqual(sorted(state["seats"]), ["00000", "00001", "00002"])
        self.assertEqual(state["proceeds_usd_cents"], str(3 * 10_000))
        for key in state["seats"]:
            self.assertEqual(state["seats"][key]["price_usd_cents"], "10000")

    def test_the_journal_moves_exactly_one_seat_at_the_block_price(self) -> None:
        result = simulate([purchase(0)])
        journal = totals(result["records"][0]["journal"])
        self.assertEqual(journal["remaining_seats"], -1)
        self.assertEqual(journal["seats_sold"], 1)
        self.assertEqual(journal["principal:principal-alpha"], 1)
        self.assertEqual(journal["proceeds"], c.seat_price_cents(0))
        self.assertEqual(len(journal), 4)

    def test_crossing_a_block_boundary_changes_the_price(self) -> None:
        events = sale(101)
        result = simulate(events)
        seats = result["final_state"]["seats"]
        self.assertEqual(seats["00099"]["price_usd_cents"], str(c.block_price_cents(0)))
        self.assertEqual(seats["00100"]["price_usd_cents"], str(c.block_price_cents(1)))
        self.assertEqual(
            result["metrics"]["proceeds_usd_cents"],
            str(100 * c.block_price_cents(0) + c.block_price_cents(1)),
        )

    def test_a_referrer_must_already_be_sold_and_is_recorded(self) -> None:
        result = simulate([purchase(0), purchase(1, "principal-beta", referrer=0)])
        seats = result["final_state"]["seats"]
        self.assertIsNone(seats["00000"]["referrer_seat_id"])
        self.assertEqual(seats["00001"]["referrer_seat_id"], "00000")

    def test_metrics_report_the_current_and_next_block(self) -> None:
        metrics = simulate(sale(100))["metrics"]
        self.assertEqual(metrics["seats_sold"], 100)
        self.assertEqual(metrics["seats_remaining"], 99_900)
        self.assertEqual(metrics["current_block_index"], 0)
        self.assertEqual(metrics["current_block_price_usd_cents"], "10000")
        self.assertEqual(metrics["next_block_index"], 1)
        self.assertEqual(metrics["next_block_price_usd_cents"], "11000")


class OwnershipBoundTest(unittest.TestCase):
    def test_one_principal_may_hold_exactly_the_maximum(self) -> None:
        events = [
            purchase(seat, "principal-solo")
            for seat in range(c.MAXIMUM_SEATS_PER_PERSON)
        ]
        result = simulate(events)
        self.assertTrue(all(record["accepted"] for record in result["records"]))
        counts = result["final_state"]["principal_seat_counts"]
        self.assertEqual(counts, {"principal-solo": str(c.MAXIMUM_SEATS_PER_PERSON)})
        self.assertEqual(result["metrics"]["largest_principal_holding"], "1000")

    def test_one_seat_beyond_the_maximum_is_rejected(self) -> None:
        limit = c.MAXIMUM_SEATS_PER_PERSON
        events = [purchase(seat, "principal-solo") for seat in range(limit)]
        events.append(purchase(limit, "principal-solo", purchase_id="over-limit"))
        events.append(purchase(limit, "principal-other", purchase_id="other-buyer"))
        result = simulate(events)
        self.assertEqual(result["records"][-2]["result"], "PRINCIPAL_SEAT_LIMIT")
        self.assertTrue(result["records"][-1]["accepted"])
        self.assertEqual(result["final_state"]["seats_sold"], limit + 1)

    def test_a_blocked_principal_does_not_consume_a_seat(self) -> None:
        events = [purchase(seat, "principal-solo") for seat in range(3)]
        events.append(purchase(3, "principal-solo", purchase_id="blocked"))
        result = simulate(events)
        self.assertTrue(result["records"][-1]["accepted"])
        self.assertEqual(result["final_state"]["seats_sold"], 4)


class CompleteSaleTest(unittest.TestCase):
    """The founder-directed scenario this model exists to prove.

    The sale is simulated once for the whole class; it is the one deliberately
    large scenario here, so running it per test would triple the suite.
    """

    result: dict

    @classmethod
    def setUpClass(cls) -> None:
        events = sale(c.FOUNDER_SEAT_CAPACITY)
        events.append(
            purchase(c.FOUNDER_SEAT_CAPACITY, "principal-late", purchase_id="past-capacity")
        )
        cls.result = simulate(events)

    def test_the_complete_sale_derives_the_stated_proceeds(self) -> None:
        metrics = self.result["metrics"]
        self.assertEqual(metrics["seats_sold"], c.FOUNDER_SEAT_CAPACITY)
        self.assertEqual(metrics["seats_remaining"], 0)
        self.assertEqual(metrics["proceeds_usd_cents"], str(c.FULL_SALE_PROCEEDS_CENTS))
        self.assertEqual(
            int(metrics["proceeds_usd_cents"]) // c.CENTS_PER_USD,
            4_231_855_000,
        )
        self.assertEqual(
            metrics["proceeds_usd_cents"],
            vectors()["denomination.full_sale_proceeds_cents"],
        )

    def test_the_complete_sale_exhausts_capacity_and_the_bound(self) -> None:
        self.assertEqual(self.result["records"][-1]["result"], "CAPACITY_EXHAUSTED")
        metrics = self.result["metrics"]
        self.assertEqual(metrics["distinct_principal_count"], 100)
        self.assertEqual(metrics["largest_principal_holding"], "1000")
        self.assertIsNone(metrics["next_block_index"])
        self.assertIsNone(metrics["next_block_price_usd_cents"])

    def test_the_last_seat_costs_the_final_block_price(self) -> None:
        last = self.result["final_state"]["seats"][f"{c.FOUNDER_SEAT_CAPACITY - 1:05d}"]
        self.assertEqual(last["price_usd_cents"], str(c.FINAL_BLOCK_PRICE_CENTS))
        self.assertEqual(int(last["price_usd_cents"]) // c.CENTS_PER_USD, 91_900)

    def test_proceeds_equal_the_sum_of_every_recorded_seat_price(self) -> None:
        seats = self.result["final_state"]["seats"]
        self.assertEqual(len(seats), c.FOUNDER_SEAT_CAPACITY)
        total = sum(int(seat["price_usd_cents"]) for seat in seats.values())
        self.assertEqual(total, c.FULL_SALE_PROCEEDS_CENTS)


class DeterminismTest(unittest.TestCase):
    def test_identical_inputs_produce_identical_digests(self) -> None:
        events = sale(250)
        first = simulate(events)
        second = simulate(events)
        for key in ("events_digest", "trace_digest", "state_digest", "result_digest"):
            with self.subTest(key=key):
                self.assertEqual(first[key], second[key])

    def test_a_different_principal_changes_the_state_digest(self) -> None:
        base = simulate([purchase(0, "principal-alpha")])
        other = simulate([purchase(0, "principal-beta")])
        self.assertNotEqual(base["state_digest"], other["state_digest"])

    def test_journal_amounts_are_unsigned_decimal_strings(self) -> None:
        for record in simulate(sale(3))["records"]:
            for item in record["journal"]:
                self.assertRegex(item["amount_usd_cents"], r"^[1-9][0-9]*$")
                self.assertIn(item["direction"], {"increase", "decrease"})


if __name__ == "__main__":
    unittest.main()
