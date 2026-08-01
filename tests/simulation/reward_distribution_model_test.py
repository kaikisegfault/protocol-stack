#!/usr/bin/env python3
"""Checked cap arithmetic, history, and accepted-adapter cross-checks."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from simulation.participation.domain import MAX_U64
from simulation.reward_distribution.crosscheck import cross_check_proportional
from simulation.reward_distribution.design import build_design
from simulation.reward_distribution.model import (
    credits_for_scores,
    evaluate_point,
    run_trajectory,
)


def identities(split: bool = False) -> dict:
    result = {
        "baseline": {"principal": "beta", "payout_account": "beta"},
    }
    keys = ("dominant_a", "dominant_b") if split else ("dominant",)
    result.update(
        {key: {"principal": "alpha", "payout_account": "alpha"} for key in keys}
    )
    return result


class RewardDistributionModelTest(unittest.TestCase):
    def test_floor_credit_and_checked_inputs(self) -> None:
        self.assertEqual(credits_for_scores(10, {"a": 3, "b": 1}), {"a": 7, "b": 2})
        self.assertEqual(credits_for_scores(10, {}), {})
        with self.assertRaises(ValueError):
            credits_for_scores(0, {"a": 1})
        with self.assertRaises(ValueError):
            credits_for_scores(10, {"a": -1})
        with self.assertRaises(OverflowError):
            credits_for_scores(MAX_U64, {"a": MAX_U64, "b": MAX_U64})

    def test_cap_enforces_scope_and_exposes_identity_split(self) -> None:
        unsplit = evaluate_point(
            100,
            {"dominant": 18, "baseline": 2},
            identities(),
            "participant_cap",
        )
        split_participant = evaluate_point(
            100,
            {"dominant_a": 9, "dominant_b": 9, "baseline": 2},
            identities(True),
            "participant_cap",
        )
        split_principal = evaluate_point(
            100,
            {"dominant_a": 9, "dominant_b": 9, "baseline": 2},
            identities(True),
            "principal_cap",
        )
        self.assertEqual(unsplit["payouts"], {"baseline": 10, "dominant": 30})
        self.assertEqual(split_participant["paid_credit"], 100)
        self.assertFalse(split_participant["principal_concentration"])
        self.assertEqual(sum(split_principal["payouts"].values()), 40)
        self.assertTrue(split_principal["principal_concentration"])

    def test_history_conserves_credit_and_bounds_liveness_loss(self) -> None:
        scenarios = {item["scenario_id"]: item for item in build_design()["scenarios"]}
        result = run_trajectory(scenarios["dominant_unsplit"], "principal_cap", 4)
        self.assertEqual(result["created_credit"], 800)
        self.assertEqual(result["paid_credit"], 320)
        self.assertEqual(result["expired_credit"], 480)
        self.assertEqual(result["ending_pending_credit"], 0)
        self.assertTrue(result["objectives"]["bounded_history"])
        self.assertFalse(result["objectives"]["bounded_liveness"])
        self.assertTrue(result["objectives"]["principal_concentration"])

    def test_same_owner_participation_adapter_cross_check(self) -> None:
        result = cross_check_proportional(
            "same_owner",
            identities(True),
            {"dominant_a": 9, "dominant_b": 9, "baseline": 2},
        )
        self.assertEqual(result["funding_event_count"], 3)
        self.assertEqual(result["funded_amount"], 100)


if __name__ == "__main__":
    unittest.main()
