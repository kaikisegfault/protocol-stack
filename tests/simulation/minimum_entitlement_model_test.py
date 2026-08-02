#!/usr/bin/env python3
"""Checked minimum-entitlement projection and boundary tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from simulation.minimum_entitlement.model import (
    evaluate_floor,
    floor_share,
    identities,
    maximum_floor,
    maximum_identities,
    partition_units,
    work_maps,
)
from simulation.participation.domain import MAX_U64
from simulation.reward_distribution.model import evaluate_point


class MinimumEntitlementModelTest(unittest.TestCase):
    def test_positive_work_partition_is_lossless_and_checked(self) -> None:
        self.assertEqual(partition_units(16, 1), [16])
        self.assertEqual(partition_units(16, 3), [6, 5, 5])
        self.assertEqual(partition_units(16, 16), [1] * 16)
        self.assertEqual(floor_share(100, 1, 113), 0)
        with self.assertRaises(ValueError):
            partition_units(16, 17)
        with self.assertRaises(OverflowError):
            floor_share(MAX_U64, MAX_U64, MAX_U64 - 1)

    def test_zero_floor_is_accepted_projection(self) -> None:
        participants = identities(16)
        raw_units, scores = work_maps(16, 7)
        for mechanism in ("proportional", "participant_cap", "principal_cap"):
            result = evaluate_floor(
                100, raw_units, scores, participants, "zero", 0, mechanism
            )
            accepted = evaluate_point(100, scores, participants, mechanism)
            self.assertEqual(result["payouts"], accepted["payouts"])
            self.assertEqual(result["honest_payout"], 0)

    def test_positive_floors_fund_honest_without_hidden_increase(self) -> None:
        for family in ("per_participant", "work_proportional"):
            observations = []
            for identity_count in (1, 2, 16):
                raw_units, scores = work_maps(identity_count, 7)
                observations.append(
                    evaluate_floor(
                        100,
                        raw_units,
                        scores,
                        identities(identity_count),
                        family,
                        1,
                        "proportional",
                    )
                )
            self.assertEqual([item["honest_payout"] for item in observations], [1, 1, 1])
            self.assertEqual([item["dominant_payout"] for item in observations], [98, 98, 96])

    def test_exact_funding_boundaries_reject_deficit(self) -> None:
        raw_units, scores = work_maps(16, 7)
        participants = identities(16)
        self.assertEqual(maximum_floor(100, "per_participant", 16), 5)
        self.assertEqual(maximum_floor(100, "work_proportional", 16), 5)
        self.assertEqual(maximum_identities(100, "per_participant", 5), 16)
        self.assertEqual(maximum_identities(100, "work_proportional", 5), 16)
        boundary = evaluate_floor(
            100, raw_units, scores, participants, "per_participant", 5, "proportional"
        )
        beyond = evaluate_floor(
            100, raw_units, scores, participants, "per_participant", 6, "proportional"
        )
        self.assertTrue(boundary["feasible"])
        self.assertFalse(beyond["feasible"])
        self.assertIsNone(beyond["payouts"])

    def test_zero_work_never_receives_reserve(self) -> None:
        participants = {
            **identities(1),
            "zero_probe": {
                "principal": "zero_owner",
                "payout_account": "zero_payout",
            },
        }
        raw_units, scores = work_maps(1, 7)
        result = evaluate_floor(
            100,
            {**raw_units, "zero_probe": 0},
            {**scores, "zero_probe": 0},
            participants,
            "per_participant",
            1,
            "proportional",
        )
        self.assertNotIn("zero_probe", result["credits"])
        with self.assertRaises(ValueError):
            evaluate_floor(
                100,
                {**raw_units, "zero_probe": 0},
                {**scores, "zero_probe": 1},
                participants,
                "per_participant",
                1,
                "proportional",
            )


if __name__ == "__main__":
    unittest.main()
