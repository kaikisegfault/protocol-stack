#!/usr/bin/env python3
"""Orthogonal design fixture, balance, and mapping tests."""

from __future__ import annotations

import sys
import unittest
from itertools import combinations, product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from simulation.authority.domain import domain_digest
from simulation.economic_stress.design import (
    FACTORS,
    assert_design,
    configurations,
    design_value,
    matrix,
)
from tests.simulation.economic_stress_common import fixture


class EconomicStressDesignTest(unittest.TestCase):
    def test_reviewed_fixture_equals_construction(self) -> None:
        self.assertEqual(fixture("design-v1.json"), design_value())
        self.assertEqual(
            domain_digest(
                "protocol-stack:economic-stress:design-v1",
                design_value(),
            ),
            "b59793533b8c963c47ca0d3d182eb320c144b8e4d3929b41b75e777c7dc83647",
        )

    def test_every_factor_and_pair_is_balanced(self) -> None:
        assert_design()
        values = matrix()
        for column in range(len(FACTORS)):
            self.assertEqual(
                [sum(row[column] == level for row in values) for level in range(3)],
                [9, 9, 9],
            )
        for left, right in combinations(range(len(FACTORS)), 2):
            counts = [
                sum((row[left], row[right]) == pair for row in values)
                for pair in product(range(3), repeat=2)
            ]
            self.assertEqual(counts, [3] * 9)

    def test_configuration_mapping_and_shocks_are_exact(self) -> None:
        values = configurations()
        self.assertEqual(len(values), 27)
        self.assertEqual(values[0].case_id, "case_00")
        self.assertEqual(values[-1].case_id, "case_26")
        self.assertEqual(values[0].values["issuance_amount"], 100)
        self.assertEqual(values[0].honest_available, 3)
        severe = next(
            item for item in values if item.values["correlated_shock"] == "severe"
        )
        self.assertEqual((severe.honest_available, severe.compromised_available), (1, 2))


if __name__ == "__main__":
    unittest.main()
