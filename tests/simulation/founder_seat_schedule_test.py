#!/usr/bin/env python3
"""Price schedule, capacity, and recorded-vector agreement tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import MAX_U64
from simulation.founder_seats import contract as c
from tests.simulation.founder_seat_common import vectors

# Figures quoted from docs/project/founder-constitution.md, not from the model.
CONSTITUTION_FIRST_BLOCK_USD = 100
CONSTITUTION_TIER_BOUNDARY_USD = 1_000
CONSTITUTION_FINAL_BLOCK_USD = 91_900
CONSTITUTION_FULL_SALE_USD = 4_231_855_000


def walk() -> tuple[list[int], list[int]]:
    """Independently walk the constitutional rule, sharing no contract code."""
    prices: list[int] = []
    price = CONSTITUTION_FIRST_BLOCK_USD * 100
    boundary = CONSTITUTION_TIER_BOUNDARY_USD * 100
    for _ in range(1000):
        prices.append(price)
        price = price + 1_000 if price < boundary else price + 10_000
    cumulative: list[int] = []
    running = 0
    for block_price in prices:
        running += block_price * 100
        cumulative.append(running)
    return prices, cumulative


class ConstitutionalAnchorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.prices, self.cumulative = walk()

    def test_the_walk_reproduces_every_stated_figure(self) -> None:
        self.assertEqual(self.prices[0], CONSTITUTION_FIRST_BLOCK_USD * 100)
        self.assertIn(CONSTITUTION_TIER_BOUNDARY_USD * 100, self.prices)
        self.assertEqual(self.prices[-1], CONSTITUTION_FINAL_BLOCK_USD * 100)
        self.assertEqual(self.cumulative[-1], CONSTITUTION_FULL_SALE_USD * 100)
        self.assertEqual(len(self.prices) * 100, 100_000)

    def test_the_contract_agrees_with_the_walk_on_every_block(self) -> None:
        for index, (price, total) in enumerate(zip(self.prices, self.cumulative)):
            if c.block_price_cents(index) != price:
                self.fail(f"block {index} price disagrees")
            if c.cumulative_proceeds_cents(index) != total:
                self.fail(f"block {index} cumulative disagrees")

    def test_the_tier_boundary_is_block_90(self) -> None:
        self.assertEqual(c.LAST_LOW_TIER_BLOCK, 90)
        self.assertEqual(c.block_price_cents(90), CONSTITUTION_TIER_BOUNDARY_USD * 100)
        self.assertEqual(c.block_price_cents(89), 99_000)
        self.assertEqual(c.block_price_cents(91), 110_000)
        self.assertEqual(c.block_price_cents(91) - c.block_price_cents(90), 10_000)
        self.assertEqual(c.block_price_cents(90) - c.block_price_cents(89), 1_000)

    def test_prices_strictly_increase_across_the_whole_schedule(self) -> None:
        prices = [c.block_price_cents(index) for index in range(c.BLOCK_COUNT)]
        self.assertTrue(all(b > a for a, b in zip(prices, prices[1:])))
        self.assertEqual(len(set(prices)), c.BLOCK_COUNT)

    def test_the_full_sale_fits_u64_with_wide_margin(self) -> None:
        self.assertEqual(c.FULL_SALE_PROCEEDS_CENTS, CONSTITUTION_FULL_SALE_USD * 100)
        self.assertLess(c.FULL_SALE_PROCEEDS_CENTS, MAX_U64)


class SeatMappingTest(unittest.TestCase):
    def test_seats_map_to_their_block(self) -> None:
        cases = {0: 0, 99: 0, 100: 1, 199: 1, 9_000: 90, 9_099: 90, 9_100: 91, 99_999: 999}
        for seat_id, expected in cases.items():
            with self.subTest(seat=seat_id):
                self.assertEqual(c.block_index(seat_id), expected)
                self.assertEqual(
                    c.seat_price_cents(seat_id),
                    c.block_price_cents(expected),
                )

    def test_every_seat_in_a_block_costs_the_same(self) -> None:
        for block in (0, 90, 91, 999):
            first = block * c.SEATS_PER_BLOCK
            prices = {
                c.seat_price_cents(seat)
                for seat in range(first, first + c.SEATS_PER_BLOCK)
            }
            self.assertEqual(prices, {c.block_price_cents(block)})

    def test_out_of_range_indexes_are_unpriced(self) -> None:
        self.assertIsNone(c.block_price_cents(-1))
        self.assertIsNone(c.block_price_cents(c.BLOCK_COUNT))
        self.assertIsNone(c.seat_price_cents(-1))
        self.assertIsNone(c.seat_price_cents(c.FOUNDER_SEAT_CAPACITY))
        self.assertIsNone(c.cumulative_proceeds_cents(c.BLOCK_COUNT))


class ClosedFormTest(unittest.TestCase):
    def test_closed_form_matches_sequential_accumulation_everywhere(self) -> None:
        running = 0
        for block in range(c.BLOCK_COUNT):
            running += c.block_price_cents(block) * c.SEATS_PER_BLOCK
            if c.cumulative_proceeds_cents(block) != running:
                self.fail(f"closed form disagrees at block {block}")
        self.assertEqual(running, c.FULL_SALE_PROCEEDS_CENTS)

    def test_recorded_cumulative_points(self) -> None:
        recorded = vectors()
        for block in (0, 1, 89, 90, 91, 998, 999):
            with self.subTest(block=block):
                self.assertEqual(
                    c.cumulative_proceeds_cents(block),
                    int(recorded[f"block{block}.cumulative_cents"]),
                )
                self.assertEqual(
                    c.block_price_cents(block),
                    int(recorded[f"block{block}.price_cents"]),
                )


class RecordedVectorTest(unittest.TestCase):
    def test_capacity_and_bounds_match_the_vector_file(self) -> None:
        recorded = vectors()
        self.assertEqual(int(recorded["capacity.founder_seat_capacity"]), 100_000)
        self.assertEqual(int(recorded["capacity.seats_per_block"]), 100)
        self.assertEqual(int(recorded["capacity.block_count"]), 1_000)
        self.assertEqual(int(recorded["capacity.maximum_seats_per_person"]), 1_000)
        self.assertEqual(int(recorded["denomination.cents_per_usd"]), 100)
        self.assertEqual(
            int(recorded["denomination.full_sale_proceeds_usd"]),
            CONSTITUTION_FULL_SALE_USD,
        )

    def test_schedule_parameters_match_the_vector_file(self) -> None:
        recorded = vectors()
        self.assertEqual(
            int(recorded["schedule.first_block_price_cents"]),
            c.FIRST_BLOCK_PRICE_CENTS,
        )
        self.assertEqual(int(recorded["schedule.low_tier_step_cents"]), c.LOW_TIER_STEP_CENTS)
        self.assertEqual(
            int(recorded["schedule.tier_boundary_price_cents"]),
            c.TIER_BOUNDARY_PRICE_CENTS,
        )
        self.assertEqual(
            int(recorded["schedule.high_tier_step_cents"]),
            c.HIGH_TIER_STEP_CENTS,
        )
        self.assertEqual(
            int(recorded["schedule.last_low_tier_block"]),
            c.LAST_LOW_TIER_BLOCK,
        )


if __name__ == "__main__":
    unittest.main()
