#!/usr/bin/env python3
"""Economic envelope survivor fixture and exact-grid tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from simulation.authority.domain import domain_digest
from simulation.economic_stress.envelope_design import (
    CONCENTRATION_CELL_COUNT,
    FINANCIAL_CELL_COUNT,
    JOINT_COMBINATION_COUNT,
    assert_design,
    design_value,
    survivor_configurations,
    with_values,
)
from simulation.economic_stress.study import run_study as run_broad_study
from tests.simulation.economic_stress_common import fixture


class EconomicEnvelopeDesignTest(unittest.TestCase):
    def test_reviewed_survivor_fixture_equals_construction(self) -> None:
        assert_design()
        self.assertEqual(fixture("envelope-design-v1.json"), design_value())
        self.assertEqual(
            domain_digest(
                "protocol-stack:economic-envelope:design-v1",
                design_value(),
            ),
            "d1c62bd5e925dfb2217db18001f1316dd52380d4527e07249c082a5c2874277d",
        )

    def test_exact_domains_and_survivor_authority_are_fixed(self) -> None:
        self.assertEqual(FINANCIAL_CELL_COUNT, 20_903_106)
        self.assertEqual(CONCENTRATION_CELL_COUNT, 1_536)
        self.assertEqual(JOINT_COMBINATION_COUNT, 160_000)
        survivors = survivor_configurations()
        self.assertEqual(
            [config.case_id for config in survivors],
            ["case_00", "case_01", "case_09", "case_15", "case_21", "case_24"],
        )
        for config in survivors:
            threshold = config.values["authority_threshold"]
            self.assertGreaterEqual(config.honest_available, threshold)
            self.assertLess(config.compromised_available, threshold)

    def test_survivors_are_exactly_the_broad_screen_robust_families(self) -> None:
        broad = run_broad_study()
        robust = {
            run["case_id"]
            for run in broad["runs"]
            if run["classification"] == "robust"
        }
        self.assertEqual(
            robust,
            {config.case_id for config in survivor_configurations()},
        )

    def test_configuration_replacement_is_bounded_to_known_factors(self) -> None:
        original = survivor_configurations()[0]
        changed = with_values(original, issuance_amount=480)
        self.assertEqual(changed.values["issuance_amount"], 480)
        self.assertEqual(original.values["issuance_amount"], 100)
        with self.assertRaises(ValueError):
            with_values(original, unknown_factor=1)


if __name__ == "__main__":
    unittest.main()
