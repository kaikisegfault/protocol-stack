#!/usr/bin/env python3
"""Cross-simulator objectives, capture, and shortfall tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from simulation.economic_stress.compose import run_configuration
from simulation.economic_stress.design import configurations


class EconomicStressModelTest(unittest.TestCase):
    def test_robust_case_completes_all_three_boundaries(self) -> None:
        run = run_configuration(configurations()[21], 0)
        self.assertEqual(run["classification"], "robust")
        self.assertTrue(all(run["objectives"].values()))
        self.assertEqual(run["reverse_stress"], [])
        self.assertEqual(set(run["authority_control"].values()), {"OK"})
        self.assertEqual(
            run["counts"]["accepted_authority_results"],
            run["counts"]["expected_authority_results"],
        )

    def test_exact_compromised_threshold_is_infeasible_but_conserved(self) -> None:
        run = run_configuration(configurations()[5], 0)
        self.assertEqual(run["configuration"]["values"]["authority_threshold"], 1)
        self.assertEqual(run["configuration"]["values"]["correlated_shock"], "severe")
        self.assertEqual(run["classification"], "infeasible")
        self.assertFalse(run["objectives"]["authority_uncaptured"])
        self.assertTrue(run["captured_issue"]["authorized"])
        self.assertTrue(run["captured_issue"]["accepted"])
        self.assertTrue(run["objectives"]["supply_conserved"])
        self.assertIn("AUTHORITY_CAPTURE", run["reverse_stress"])

    def test_unavailable_quorum_fails_closed_without_capture(self) -> None:
        run = run_configuration(configurations()[2], 0)
        self.assertEqual(run["configuration"]["values"]["authority_threshold"], 3)
        self.assertEqual(run["configuration"]["values"]["correlated_shock"], "severe")
        self.assertEqual(run["classification"], "fragile")
        self.assertFalse(run["objectives"]["authority_available"])
        self.assertTrue(run["objectives"]["authority_uncaptured"])
        self.assertFalse(run["objectives"]["rotation_available"])
        self.assertFalse(run["objectives"]["recovery_available"])
        self.assertEqual(run["authority_control"]["schedule"], "THRESHOLD")

    def test_created_obligation_shortfall_is_infeasible(self) -> None:
        run = run_configuration(configurations()[3], 0)
        self.assertTrue(run["objectives"]["participation_complete"])
        self.assertFalse(run["objectives"]["funding_complete"])
        self.assertFalse(run["objectives"]["economy_complete"])
        self.assertTrue(run["objectives"]["supply_conserved"])
        self.assertEqual(run["classification"], "infeasible")
        self.assertLess(
            run["entitlements"]["funded_amount"],
            run["entitlements"]["requested_amount"],
        )

    def test_within_role_concentration_alarm_is_exact_rational(self) -> None:
        run = run_configuration(configurations()[0], 0)
        self.assertFalse(run["objectives"]["concentration_within_bound"])
        self.assertIn("REWARD_CONCENTRATION", run["reverse_stress"])
        share = run["entitlements"]["maximum_share"]
        self.assertGreater(4 * share["numerator"], 3 * share["denominator"])


if __name__ == "__main__":
    unittest.main()
