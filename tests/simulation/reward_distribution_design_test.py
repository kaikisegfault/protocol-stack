#!/usr/bin/env python3
"""Reviewed reward-distribution design fixture tests."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from simulation.participation.domain import domain_digest
from simulation.reward_distribution.design import build_design


class RewardDistributionDesignTest(unittest.TestCase):
    def test_reviewed_fixture_equals_construction(self) -> None:
        fixture = json.loads(
            (
                ROOT
                / "simulation/reward_distribution/fixtures/design-v1.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(fixture, build_design())
        self.assertEqual(
            domain_digest(
                "protocol-stack:reward-distribution:design-v1", fixture
            ),
            "9d9157802b488f4e5029859aba8354570b1b725d8ccc00bd19704652e7856eb2",
        )

    def test_exact_domains_and_trajectories_are_fixed(self) -> None:
        design = build_design()
        self.assertEqual(design["support_point_count"], 76_800)
        self.assertEqual(design["history_epochs"], 4)
        self.assertEqual(design["drain_epochs"], 4)
        self.assertEqual(
            [item["scenario_id"] for item in design["scenarios"]],
            [
                "honest_variance",
                "intermittent_availability",
                "population_change",
                "dominant_unsplit",
                "dominant_split",
            ],
        )
        self.assertEqual(
            design["survivor_case_ids"],
            ["case_00", "case_01", "case_09", "case_15", "case_21", "case_24"],
        )
        self.assertTrue(
            all(len(item["contributions"]) == 8 for item in design["scenarios"])
        )


if __name__ == "__main__":
    unittest.main()
