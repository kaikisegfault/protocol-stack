#!/usr/bin/env python3
"""Checked admission utility, hidden scope, churn, and lock tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from simulation.admission_cost.crosscheck import lock_replays, participation_cross_checks
from simulation.admission_cost.design import build_design
from simulation.admission_cost.model import (
    capital_cost,
    capital_lower_bound,
    ceil_div,
    identities,
    observe_point,
    operating_break_even,
    partition_units,
    scores,
)
from simulation.admission_cost.trajectories import build_scenario
from simulation.participation.domain import MAX_U64


class AdmissionCostModelTest(unittest.TestCase):
    def test_positive_work_partition_is_lossless_and_checked(self) -> None:
        self.assertEqual(partition_units(16, 1), [16])
        self.assertEqual(partition_units(16, 3), [6, 5, 5])
        self.assertEqual(partition_units(16, 16), [1] * 16)
        self.assertEqual(ceil_div(5, 2), 3)
        with self.assertRaises(ValueError):
            partition_units(16, 17)
        with self.assertRaises(OverflowError):
            scores(MAX_U64, 1, 2, 1)

    def test_distinct_registered_scopes_expose_hidden_principal(self) -> None:
        participant_map = identities(16)
        score_map = scores(16, 16, 1, 1)
        participant = observe_point(100, score_map, participant_map, "participant_cap")
        principal = observe_point(100, score_map, participant_map, "principal_cap")
        self.assertEqual(participant["payouts"], principal["payouts"])
        self.assertTrue(participant["principal_concentration"])
        self.assertFalse(participant["hidden_principal_concentration"])
        self.assertEqual(participant["dominant_payout"], 80)
        self.assertEqual(participant["honest_payout"], 5)

    def test_operating_and_capital_boundaries_are_exact(self) -> None:
        self.assertEqual(operating_break_even(5, 2), 3)
        self.assertEqual(operating_break_even(-1, 2), 0)
        self.assertEqual(capital_cost(10, 1, 3), 4)
        self.assertEqual(
            capital_lower_bound(5, 10),
            {"ratio": {"numerator": 2, "denominator": 5}, "inclusive": False},
        )
        with self.assertRaises(ValueError):
            operating_break_even(1, 0)
        with self.assertRaises(OverflowError):
            capital_cost(MAX_U64, 2, 1)

    def test_persistent_and_churn_work_are_identical(self) -> None:
        design = build_design()
        persistent = build_scenario("persistent", 7, design)
        churn = build_scenario("churn", 7, design)
        for scenario in (persistent, churn):
            self.assertEqual(len(scenario["contributions"]), 8)
            self.assertTrue(
                all(
                    sum(value for key, value in epoch.items() if key != "honest") == 16
                    for epoch in scenario["contributions"]
                )
            )
        self.assertEqual(len(persistent["participants"]), 8)
        self.assertEqual(len(churn["participants"]), 57)

    def test_native_lock_and_participation_boundaries_compose(self) -> None:
        for replay in lock_replays(4):
            self.assertEqual(replay["early_release_result"], "TOO_EARLY")
            self.assertEqual(replay["refunded_principal"], 16)
            self.assertEqual(replay["ending_locked_principal"], 0)
            self.assertTrue(replay["lock_enforced"])
        cross_checks = participation_cross_checks(16)
        self.assertEqual([item["participant_count"] for item in cross_checks], [2, 3, 17])
        self.assertTrue(all(item["funding_event_count"] > 0 for item in cross_checks))


if __name__ == "__main__":
    unittest.main()
