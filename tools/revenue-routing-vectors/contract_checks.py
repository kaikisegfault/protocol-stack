"""Derive the split contract from the constitution and the independent form.

Nothing here reads the model's own arithmetic as authority. The percentages come
from literals quoted out of the Founder Constitution, and every share is
recomputed with the naive form in `walk.py` so the contract's overflow-free
decomposition has to earn its agreement.
"""

from __future__ import annotations

import walk as w
from checker import Checker

from simulation.revenue_routing import contract as c

# Anchors quoted directly from docs/project/founder-constitution.md.
CONSTITUTION_FOUNDER_PERCENT = 45
CONSTITUTION_CREATOR_PERCENT = 45
CONSTITUTION_SYSTEM_CREATOR_PERCENT = 10
# The two creator legs are stated as 22.5% each, held here per mille so the
# check stays integer-only.
CONSTITUTION_CREATOR_LEG_PER_MILLE = 225
CONSTITUTION_SEAT_CAPACITY = 100_000

ANCHOR_AMOUNTS = (1, 2, 4, 7, 99, 100_000_000, 123_456_789, 400_000_000)
CASES = ((False, "single"), (True, "two"))
REMAINDER_CASES = ((False, "single_creator"), (True, "two_creators"))


def check_constitution_anchors(check: Checker) -> None:
    """The contract must carry the constitution's percentages, not its own."""
    percentages = (
        (c.FOUNDER_SHARE_NUMERATOR, CONSTITUTION_FOUNDER_PERCENT),
        (c.CREATOR_SHARE_NUMERATOR, CONSTITUTION_CREATOR_PERCENT),
        (c.SYSTEM_CREATOR_SHARE_NUMERATOR, CONSTITUTION_SYSTEM_CREATOR_PERCENT),
    )
    for numerator, stated in percentages:
        if numerator != stated:
            check.failures.append(f"contract: numerator {numerator} is not {stated}%")
    if sum(numerator for numerator, _ in percentages) != c.SHARE_DENOMINATOR:
        check.failures.append("contract: the numerators do not sum to the denominator")
    legs = CONSTITUTION_CREATOR_LEG_PER_MILLE * c.CREATOR_SPLIT_PARTS
    if c.CREATOR_SHARE_NUMERATOR * 10 != legs:
        check.failures.append("contract: the creator legs are not 22.5% each")
    if c.FOUNDER_SEAT_CAPACITY != CONSTITUTION_SEAT_CAPACITY:
        check.failures.append("contract: the seat capacity is not 100,000")


def scan_remainders() -> dict[bool, dict[int, int]]:
    """Count the remainder of every residue, in both creator cases.

    The remainder repeats with the recorded period, so this scan is a complete
    proof of the bound rather than a sample.
    """
    counts: dict[bool, dict[int, int]] = {False: {}, True: {}}
    for product_creator in (False, True):
        for amount in range(c.REMAINDER_PERIOD):
            remainder = w.direct_remainder(amount, product_creator=product_creator)
            counts[product_creator][remainder] = (
                counts[product_creator].get(remainder, 0) + 1
            )
    return counts


def check_share_agreement(check: Checker) -> int:
    """The contract and the naive form must agree, and the period must hold."""
    numerators = (
        c.FOUNDER_SHARE_NUMERATOR,
        c.CREATOR_SHARE_NUMERATOR,
        c.SYSTEM_CREATOR_SHARE_NUMERATOR,
    )
    compared = 0
    for amount in range(4 * c.REMAINDER_PERIOD):
        for numerator in numerators:
            if c.share(amount, numerator) != w.direct_share(amount, numerator):
                check.failures.append(f"share({amount}, {numerator}) disagrees")
                return compared
            compared += 1
        for product_creator in (False, True):
            derived = c.routing_remainder(amount, product_creator=product_creator)
            expected = w.direct_remainder(amount, product_creator=product_creator)
            periodic = w.direct_remainder(
                amount + c.REMAINDER_PERIOD, product_creator=product_creator
            )
            if derived != expected or expected != periodic:
                check.failures.append(f"remainder({amount}) disagrees or is aperiodic")
                return compared

    huge = (1 << 64) - 1
    if c.share(huge, c.FOUNDER_SHARE_NUMERATOR) != w.direct_share(
        huge, c.FOUNDER_SHARE_NUMERATOR
    ):
        check.failures.append("the decomposed share overflows at the u64 maximum")
    return compared


def check_contract_vectors(check: Checker, counts: dict[bool, dict[int, int]]) -> None:
    check.equal("denomination.decimal_places", c.DECIMAL_PLACES)
    check.equal(
        "denomination.atomic_units_per_display_unit",
        c.ATOMIC_UNITS_PER_DISPLAY_UNIT,
    )

    check.equal("split.share_denominator", c.SHARE_DENOMINATOR)
    check.equal("split.founder_share_numerator", CONSTITUTION_FOUNDER_PERCENT)
    check.equal("split.creator_share_numerator", CONSTITUTION_CREATOR_PERCENT)
    check.equal(
        "split.system_creator_share_numerator", CONSTITUTION_SYSTEM_CREATOR_PERCENT
    )
    check.equal("split.creator_split_parts", c.CREATOR_SPLIT_PARTS)
    check.equal(
        "split.numerator_sum",
        CONSTITUTION_FOUNDER_PERCENT
        + CONSTITUTION_CREATOR_PERCENT
        + CONSTITUTION_SYSTEM_CREATOR_PERCENT,
    )
    check.equal("split.founder_seat_capacity", CONSTITUTION_SEAT_CAPACITY)

    check.equal("remainder.period", c.REMAINDER_PERIOD)
    check.equal("remainder.residues_scanned", c.REMAINDER_PERIOD)
    for product_creator, label in REMAINDER_CASES:
        histogram = counts[product_creator]
        check.equal(f"remainder.{label}_maximum", max(histogram))
        for value in sorted(histogram):
            check.equal(f"remainder.{label}_count_{value}", histogram[value])
        smallest = next(
            amount
            for amount in range(1, c.REMAINDER_PERIOD)
            if w.direct_remainder(amount, product_creator=product_creator)
            == max(histogram)
        )
        check.equal(f"remainder.{label}_smallest_maximum_amount", smallest)


def check_anchor_vectors(check: Checker) -> None:
    for amount in ANCHOR_AMOUNTS:
        for product_creator, label in CASES:
            founder, project, product, system = w.direct_split(
                amount, product_creator=product_creator
            )
            prefix = f"amount{amount}.{label}"
            check.equal(f"{prefix}.founder_credit", founder)
            check.equal(f"{prefix}.project", project)
            if product_creator:
                check.equal(f"{prefix}.product", product)
            check.equal(f"{prefix}.system_creator", system)
            check.equal(
                f"{prefix}.remainder",
                w.direct_remainder(amount, product_creator=product_creator),
            )
