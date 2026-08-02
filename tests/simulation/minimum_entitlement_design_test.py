#!/usr/bin/env python3
"""Reviewed minimum-entitlement design fixture tests."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from simulation.minimum_entitlement.design import build_design
from simulation.participation.domain import domain_digest


class MinimumEntitlementDesignTest(unittest.TestCase):
    def test_reviewed_fixture_equals_construction(self) -> None:
        fixture = json.loads(
            (
                ROOT
                / "simulation/minimum_entitlement/fixtures/design-v1.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(fixture, build_design())
        self.assertEqual(
            domain_digest("protocol-stack:minimum-entitlement:design-v1", fixture),
            "b4063b2ec8b6035a1f9b76008100c3d6dbf63cfbb8f52a989f8e1d9f2daef03f",
        )

    def test_zero_credit_support_and_counts_are_fixed(self) -> None:
        design = build_design()
        self.assertEqual(design["retained_coordinate_count"], 80)
        self.assertEqual(design["zero_family_form_count"], 3_840)
        self.assertEqual(design["positive_family_form_count"], 23_040)
        self.assertEqual(design["evaluated_form_count"], 49_920)
        self.assertEqual(design["common_floor_range"]["maximum"], 5)
        self.assertEqual(design["retained_coordinates"][0]["selected_weight"], 7)
        self.assertEqual(design["retained_coordinates"][-1]["selected_weight"], 16)
        self.assertEqual({item["budget"] for item in design["retained_coordinates"]}, {100})


if __name__ == "__main__":
    unittest.main()
