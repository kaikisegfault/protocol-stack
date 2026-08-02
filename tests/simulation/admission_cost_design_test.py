#!/usr/bin/env python3
"""Reviewed admission-cost design fixture tests."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from simulation.admission_cost.design import build_design
from simulation.participation.domain import domain_digest


class AdmissionCostDesignTest(unittest.TestCase):
    def test_reviewed_fixture_equals_construction(self) -> None:
        fixture = json.loads(
            (ROOT / "simulation/admission_cost/fixtures/design-v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(fixture, build_design())
        self.assertEqual(
            domain_digest("protocol-stack:admission-cost:design-v1", fixture),
            "5af307b2b7dcd4421951db807d37458fddb182e1c151529eb657519ad2244f0b",
        )

    def test_exact_domains_and_counts_are_fixed(self) -> None:
        design = build_design()
        self.assertEqual(design["base_coordinate_count"], 3_840)
        self.assertEqual(design["identity_form_count"], 61_440)
        self.assertEqual(design["dominant_total_units"], 16)
        self.assertEqual(design["trajectory"]["contribution_epochs"], 8)
        self.assertEqual(design["trajectory"]["drain_epochs"], 4)
        self.assertEqual(
            design["survivor_case_ids"],
            ["case_00", "case_01", "case_09", "case_15", "case_21", "case_24"],
        )


if __name__ == "__main__":
    unittest.main()
