#!/usr/bin/env python3
"""Frozen minimum-entitlement evidence, CLI, and import tests."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from simulation.minimum_entitlement.study import run_study
from simulation.participation.domain import canonical_json
from tests.simulation.economic_stress_common import contains_float


class MinimumEntitlementStudyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_study()

    def test_default_study_fixes_exact_evidence(self) -> None:
        report = self.report
        self.assertEqual(
            report["study_digest"],
            "e07a9d6f9e0b691a772b7195440d1c9d010dd0fd17f934c92b36dc98e2cec67b",
        )
        support = {
            (item["floor_family"], item["mechanism"]): item
            for item in report["exact_support"]
        }
        proportional = support[("work_proportional", "proportional")]
        self.assertEqual(proportional["point_count"], 7_680)
        self.assertEqual(proportional["positive_same_floor_split_forms"], 0)
        self.assertEqual(proportional["positive_baseline_amplification_forms"], 0)
        self.assertEqual(proportional["global_joint_break_even"], 1)
        self.assertEqual(proportional["minimum_positive_honest_payout"], 1)
        self.assertFalse(contains_float(report))

    def test_capped_failure_and_funding_boundaries_are_explicit(self) -> None:
        support = {
            (item["floor_family"], item["mechanism"]): item
            for item in self.report["exact_support"]
        }
        capped = support[("work_proportional", "participant_cap")]
        self.assertEqual(capped["positive_same_floor_split_forms"], 7_200)
        self.assertEqual(capped["maximum_same_floor_split_gain"], 99)
        self.assertEqual(capped["positive_baseline_amplification_forms"], 7_600)
        self.assertIsNone(capped["global_joint_break_even"])
        boundaries = self.report["funding_boundaries"]
        self.assertEqual(boundaries["common_floor_ceiling"], 5)
        self.assertEqual(boundaries["budget_exhaustion_instances"], 4)
        self.assertTrue(boundaries["boundary_safe"])

    def test_accepted_paths_and_objectives_are_frozen(self) -> None:
        report = self.report
        self.assertEqual(report["zero_floor_cross_check_count"], 3_840)
        self.assertEqual(len(report["participation_cross_checks"]), 6)
        self.assertEqual(len(report["native_funding_replays"]), 126)
        self.assertEqual(len(report["coordinate_break_evens"]), 480)
        self.assertTrue(report["objectives"]["strictly_funded"])
        self.assertTrue(report["objectives"]["zero_work_rejected"])
        self.assertTrue(report["objectives"]["native_funding"])
        self.assertTrue(report["objectives"]["global_joint_floor_exists"])
        self.assertFalse(report["objectives"]["hidden_concentration"])

    def test_repeated_study_and_cli_are_byte_identical(self) -> None:
        self.assertEqual(canonical_json(self.report), canonical_json(run_study()))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "minimum-entitlement.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "simulation/minimum_entitlement/study.py"),
                    "--output",
                    str(output),
                ],
                check=True,
                cwd=ROOT,
            )
            generated = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(canonical_json(generated), canonical_json(self.report))

    def test_package_imports_only_standard_library_and_local_models(self) -> None:
        allowed = {"simulation"}
        standard = set(sys.stdlib_module_names)
        for path in (ROOT / "simulation/minimum_entitlement").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots = {alias.name.split(".")[0] for alias in node.names}
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    roots = {str(node.module).split(".")[0]}
                else:
                    continue
                self.assertTrue(
                    roots <= standard | allowed,
                    f"{path.name} imports nonstandard modules: {roots}",
                )


if __name__ == "__main__":
    unittest.main()
