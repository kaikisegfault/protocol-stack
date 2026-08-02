#!/usr/bin/env python3
"""Frozen admission-cost evidence, replay, CLI, and import tests."""

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

from simulation.admission_cost.study import run_study
from simulation.participation.domain import canonical_json
from tests.simulation.economic_stress_common import contains_float


class AdmissionCostStudyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_study()

    def test_default_study_fixes_exact_evidence(self) -> None:
        report = self.report
        self.assertEqual(
            report["study_digest"],
            "011c4a787a22dc72ef85e30a5b71f9444c0d53b6767674a8c5aa562e550e5da7",
        )
        support = {item["mechanism"]: item for item in report["exact_support"]}
        self.assertEqual(support["participant_cap"]["point_count"], 61_440)
        self.assertEqual(
            support["participant_cap"]["profitable_zero_cost_split_forms"], 51_960
        )
        self.assertEqual(support["participant_cap"]["maximum_zero_cost_gain"], 495)
        self.assertEqual(support["participant_cap"]["operating_deterrence_floor"], 495)
        self.assertEqual(support["participant_cap"]["smallest_honest_entry_ceiling"], 0)
        self.assertFalse(contains_float(report))

    def test_churn_and_cost_only_failure_are_explicit(self) -> None:
        combined = {
            item["mechanism"]: item for item in self.report["combined_cost_boundaries"]
        }
        capped = combined["participant_cap"]
        self.assertEqual(capped["operating_cost_interval"]["minimum"], 632)
        self.assertEqual(capped["operating_cost_interval"]["maximum"], 0)
        self.assertFalse(capped["operating_cost_interval"]["feasible"])
        self.assertFalse(capped["any_capital_rate_range"])
        trajectory = next(
            item
            for item in self.report["trajectory_results"]
            if item["mechanism"] == "participant_cap"
            and item["scenario_id"] == "churn_16"
        )
        self.assertEqual(trajectory["dominant_payout"], 640)
        self.assertEqual(trajectory["zero_cost_gain"], 520)
        self.assertEqual(trajectory["operating_break_even"], 5)
        self.assertTrue(trajectory["objectives"]["funded"])

    def test_native_lock_funding_and_scope_objectives_are_frozen(self) -> None:
        report = self.report
        self.assertEqual(len(report["native_lock_replays"]), 32)
        self.assertTrue(all(item["lock_enforced"] for item in report["native_lock_replays"]))
        self.assertEqual(len(report["adapter_cross_checks"]), 3)
        self.assertTrue(report["objectives"]["registered_scope_equivalence"])
        self.assertTrue(report["objectives"]["funded"])
        self.assertTrue(report["objectives"]["lock_enforced"])
        self.assertFalse(report["objectives"]["hidden_concentration"])
        self.assertFalse(report["objectives"]["capped_joint_operating_cost_range"])
        self.assertFalse(report["objectives"]["capped_joint_capital_rate_range"])

    def test_repeated_study_and_cli_are_byte_identical(self) -> None:
        self.assertEqual(canonical_json(self.report), canonical_json(run_study()))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "admission-cost.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "simulation/admission_cost/study.py"),
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
        for path in (ROOT / "simulation/admission_cost").glob("*.py"):
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
