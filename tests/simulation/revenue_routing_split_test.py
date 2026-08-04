#!/usr/bin/env python3
"""Share arithmetic, the creator sub-split, and the routing remainder."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import MAX_U64
from simulation.revenue_routing import contract as c
from tests.simulation.revenue_routing_common import vectors


def naive_share(amount: int, numerator: int) -> int:
    """The specification's direct form, safe under Python's big integers."""
    return (numerator * amount) // c.SHARE_DENOMINATOR


class ShareArithmeticTest(unittest.TestCase):
    NUMERATORS = (
        c.FOUNDER_SHARE_NUMERATOR,
        c.CREATOR_SHARE_NUMERATOR,
        c.SYSTEM_CREATOR_SHARE_NUMERATOR,
    )

    def test_the_numerators_sum_to_the_denominator(self) -> None:
        self.assertEqual(sum(self.NUMERATORS), c.SHARE_DENOMINATOR)

    def test_the_decomposed_share_equals_the_direct_form(self) -> None:
        for amount in list(range(2_000)) + [10**8, 123_456_789, 5 * 10**18]:
            for numerator in self.NUMERATORS:
                with self.subTest(amount=amount, numerator=numerator):
                    self.assertEqual(
                        c.share(amount, numerator), naive_share(amount, numerator)
                    )

    def test_the_share_never_overflows_across_the_u64_range(self) -> None:
        """The direct form would leave u64 here; the decomposed form must not."""
        for amount in (MAX_U64, MAX_U64 - 1, MAX_U64 // 45 + 1, 2**63):
            for numerator in self.NUMERATORS:
                with self.subTest(amount=amount, numerator=numerator):
                    derived = c.share(amount, numerator)
                    self.assertIsNotNone(derived)
                    self.assertEqual(derived, naive_share(amount, numerator))
                    self.assertLessEqual(derived, MAX_U64)

    def test_the_shares_never_exceed_the_payment(self) -> None:
        for amount in range(1_000):
            with self.subTest(amount=amount):
                total = sum(c.share(amount, n) for n in self.NUMERATORS)
                self.assertLessEqual(total, amount)


class CreatorSplitTest(unittest.TestCase):
    def test_a_single_creator_takes_the_whole_creator_share(self) -> None:
        for amount in (1, 7, 99, 10**8, 123_456_789):
            with self.subTest(amount=amount):
                creator = c.share(amount, c.CREATOR_SHARE_NUMERATOR)
                project, product = c.creator_legs(creator, product_creator=False)
                self.assertEqual((project, product), (creator, 0))

    def test_two_creators_split_the_creator_share_in_half(self) -> None:
        for amount in range(0, 4_000, 7):
            with self.subTest(amount=amount):
                creator = c.share(amount, c.CREATOR_SHARE_NUMERATOR)
                project, product = c.creator_legs(creator, product_creator=True)
                self.assertEqual(project, product)
                self.assertLessEqual(project + product, creator)
                self.assertLessEqual(creator - (project + product), 1)

    def test_each_creator_leg_is_22_5_percent_of_a_divisible_payment(self) -> None:
        amount = 1_000 * c.ATOMIC_UNITS_PER_DISPLAY_UNIT
        founder, project, product, system = c.split(amount, product_creator=True)
        self.assertEqual(project, amount * 225 // 1_000)
        self.assertEqual(product, amount * 225 // 1_000)
        self.assertEqual(founder, amount * 45 // 100)
        self.assertEqual(system, amount * 10 // 100)
        self.assertEqual(founder + project + product + system, amount)


class RemainderTest(unittest.TestCase):
    def cases(self) -> tuple[tuple[bool, str], ...]:
        return ((False, "single_creator"), (True, "two_creators"))

    def test_the_split_always_conserves_the_payment(self) -> None:
        amounts = list(range(3_000)) + [10**8, 123_456_789, MAX_U64]
        for amount in amounts:
            for product_creator in (False, True):
                with self.subTest(amount=amount, product=product_creator):
                    parts = c.split(amount, product_creator=product_creator)
                    self.assertEqual(sum(parts), amount)

    def test_the_remainder_bound_holds_over_a_complete_period(self) -> None:
        recorded = vectors()
        for product_creator, label in self.cases():
            observed = [
                c.routing_remainder(amount, product_creator=product_creator)
                for amount in range(c.REMAINDER_PERIOD)
            ]
            with self.subTest(case=label):
                self.assertEqual(
                    max(observed), int(recorded[f"remainder.{label}_maximum"])
                )
                self.assertEqual(
                    max(observed), c.maximum_remainder(product_creator=product_creator)
                )
                self.assertTrue(all(value >= 0 for value in observed))

    def test_the_remainder_is_periodic_so_the_scan_is_complete(self) -> None:
        for product_creator, label in self.cases():
            for amount in range(4 * c.REMAINDER_PERIOD):
                shifted = amount + c.REMAINDER_PERIOD
                with self.subTest(case=label, amount=amount):
                    self.assertEqual(
                        c.routing_remainder(amount, product_creator=product_creator),
                        c.routing_remainder(shifted, product_creator=product_creator),
                    )

    def test_the_remainder_goes_only_to_the_founder_credit(self) -> None:
        """No other beneficiary may ever receive more than its exact floor."""
        for amount in range(1_000):
            for product_creator in (False, True):
                with self.subTest(amount=amount, product=product_creator):
                    founder, project, product, system = c.split(
                        amount, product_creator=product_creator
                    )
                    creator = c.share(amount, c.CREATOR_SHARE_NUMERATOR)
                    legs = c.creator_legs(creator, product_creator=product_creator)
                    self.assertEqual((project, product), legs)
                    self.assertEqual(system, c.share(amount, 10))
                    self.assertGreaterEqual(
                        founder, c.share(amount, c.FOUNDER_SHARE_NUMERATOR)
                    )

    def test_the_recorded_anchor_shares_are_reproduced(self) -> None:
        recorded = vectors()
        for amount in (1, 2, 4, 7, 99, 10**8, 123_456_789, 400_000_000):
            for product_creator, label in ((False, "single"), (True, "two")):
                founder, project, product, system = c.split(
                    amount, product_creator=product_creator
                )
                prefix = f"amount{amount}.{label}"
                with self.subTest(amount=amount, case=label):
                    self.assertEqual(founder, int(recorded[f"{prefix}.founder_credit"]))
                    self.assertEqual(project, int(recorded[f"{prefix}.project"]))
                    self.assertEqual(
                        system, int(recorded[f"{prefix}.system_creator"])
                    )
                    if product_creator:
                        self.assertEqual(product, int(recorded[f"{prefix}.product"]))


if __name__ == "__main__":
    unittest.main()
