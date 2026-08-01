#!/usr/bin/env python3
"""Independent envelope arithmetic and full-composition cross-checks."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from simulation.economic_stress.compose import run_configuration
from simulation.economic_stress.envelope_design import (
    survivor_configurations,
    with_values,
)
from simulation.economic_stress.envelope_projection import (
    MAX_U64,
    checked_add,
    checked_mul,
    concentration_cell,
    financial_profile,
    floor_share,
    project_point,
    role_entitlements,
    units_from_seed,
)


ROBUST_ANCHORS = (
    (0, 2),
    (0, 6),
    (0, 7),
    (1, 3),
    (9, 2),
    (15, 2),
    (15, 6),
    (15, 7),
    (21, 0),
    (21, 4),
    (21, 5),
    (24, 1),
)


class EconomicEnvelopeProjectionTest(unittest.TestCase):
    def test_checked_floor_arithmetic_and_remainders(self) -> None:
        self.assertEqual(role_entitlements(21, 1, 2, 1), (7, 14))
        self.assertEqual(role_entitlements(100, 11, 7, 1), (61, 38))
        self.assertEqual(floor_share(MAX_U64, 1, MAX_U64), 1)
        with self.assertRaises(OverflowError):
            checked_add(MAX_U64, 1)
        with self.assertRaises(OverflowError):
            checked_mul(MAX_U64, 2)
        for arguments in (
            (100, 0, 1, 1),
            (100, 1, 21, 1),
            (100, 1, 1, 0),
            (100, 1, 1, 17),
        ):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                role_entitlements(*arguments)

    def test_all_screened_robust_anchors_match_full_composition(self) -> None:
        by_index = {config.case_index: config for config in survivor_configurations()}
        for case_index, seed in ROBUST_ANCHORS:
            with self.subTest(case_index=case_index, seed=seed):
                config = by_index[case_index]
                projection = project_point(config, units_from_seed(config, seed))
                composed = run_configuration(config, seed)
                self._assert_matches(projection, composed)
                self.assertTrue(all(composed["objectives"].values()))

    def test_treasury_threshold_matches_full_failure_atomicity(self) -> None:
        base = survivor_configurations()[0]
        below = with_values(base, issuance_amount=479, reward_budget_per_role=500)
        boundary = with_values(base, issuance_amount=480, reward_budget_per_role=500)
        for config, expected in ((below, False), (boundary, True)):
            projection = project_point(config, units_from_seed(config, 0))
            composed = run_configuration(config, 0)
            self._assert_matches(projection, composed)
            self.assertEqual(projection["funding_complete"], expected)
            self.assertTrue(composed["objectives"]["supply_conserved"])
            self.assertTrue(composed["objectives"]["authority_available"])
            self.assertTrue(composed["objectives"]["authority_uncaptured"])

    def test_every_family_grid_extreme_matches_full_composition(self) -> None:
        for base in survivor_configurations():
            variants = (
                with_values(
                    base,
                    issuance_amount=100,
                    reward_budget_per_role=50,
                    validator_weight=1,
                    node_weight=1,
                ),
                with_values(
                    base,
                    issuance_amount=2_500,
                    reward_budget_per_role=1_500,
                    validator_weight=16,
                    node_weight=16,
                ),
            )
            for config in variants:
                with self.subTest(case_id=base.case_id, values=config.values):
                    projection = project_point(config, units_from_seed(config, 0))
                    composed = run_configuration(config, 0)
                    self._assert_matches(projection, composed)
                    self.assertTrue(composed["objectives"]["supply_conserved"])
                    self.assertTrue(composed["objectives"]["authority_available"])
                    self.assertTrue(composed["objectives"]["authority_uncaptured"])

    def test_exact_profiles_and_concentration_cells_cover_boundaries(self) -> None:
        config = survivor_configurations()[0]
        profile = financial_profile(config, 500)
        self.assertEqual(profile["minimum_issuance_for_treasury_funding"], 480)
        self.assertEqual(profile["fallback_classification"], "insolvent")
        self.assertEqual(
            profile["classification_counts"],
            {"solvent": 2_021, "mixed": 0, "insolvent": 380},
        )
        low = concentration_cell(config, 1, 1)
        high = concentration_cell(config, 16, 16)
        self.assertEqual(low["classification"], "mixed")
        self.assertEqual(high["classification"], "mixed")
        self.assertGreater(low["passing_combination_count"], high["passing_combination_count"])
        with self.assertRaises(ValueError):
            financial_profile(config, 49)
        with self.assertRaises(ValueError):
            project_point(
                with_values(config, issuance_amount=2_501),
                units_from_seed(config, 0),
            )

    def _assert_matches(self, projection: dict, composed: dict) -> None:
        self.assertEqual(
            projection["entitlement_total"],
            composed["entitlements"]["requested_amount"],
        )
        self.assertEqual(
            projection["retained_remainder"],
            composed["entitlements"]["retained_remainder"],
        )
        self.assertEqual(
            projection["funding_complete"],
            composed["objectives"]["funding_complete"],
        )
        self.assertEqual(
            projection["concentration_within_bound"],
            composed["objectives"]["concentration_within_bound"],
        )


if __name__ == "__main__":
    unittest.main()
