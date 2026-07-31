#!/usr/bin/env python3
"""Default study evidence and deterministic replay tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from simulation.authority.domain import canonical_json
from simulation.economic_stress.study import run_study
from tests.simulation.economic_stress_common import contains_float


class EconomicStressStudyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_study(0, 8)

    def test_default_study_fixes_evidence(self) -> None:
        report = self.report
        self.assertEqual(report["run_count"], 216)
        self.assertEqual(
            report["study_digest"],
            "d697f437a5e94d3cbba02cb131609b0591a59930968dc2c5880b49c9590f40de",
        )
        self.assertEqual(
            report["classification_counts"],
            {"robust": 12, "fragile": 92, "infeasible": 112},
        )
        self.assertEqual(report["objective_pass_counts"]["supply_conserved"], 216)
        self.assertEqual(report["objective_pass_counts"]["authority_available"], 144)
        self.assertEqual(report["objective_pass_counts"]["funding_complete"], 96)
        self.assertEqual(report["objective_pass_counts"]["authority_uncaptured"], 144)
        self.assertEqual(
            report["reverse_stress_counts"]["AUTHORITY_CAPTURE"],
            72,
        )
        self.assertFalse(contains_float(report))

    def test_replicated_runs_are_distinct_and_conserved(self) -> None:
        report = self.report
        self.assertTrue(all(run["objectives"]["supply_conserved"] for run in report["runs"]))
        self.assertGreater(
            len({run["trace_digests"]["authority"] for run in report["runs"]}),
            150,
        )
        self.assertEqual(
            sum(report["classification_counts"].values()),
            report["run_count"],
        )

    def test_small_study_is_byte_deterministic(self) -> None:
        first = run_study(7, 1)
        second = run_study(7, 1)
        self.assertEqual(canonical_json(first), canonical_json(second))


if __name__ == "__main__":
    unittest.main()
