#!/usr/bin/env python3
"""Frozen reward-distribution evidence, replay, and CLI tests."""

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

from simulation.participation.domain import canonical_json
from simulation.reward_distribution.study import run_study
from tests.simulation.economic_stress_common import contains_float


class RewardDistributionStudyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_study()

    def test_default_study_fixes_exact_evidence(self) -> None:
        report = self.report
        self.assertEqual(
            report["study_digest"],
            "3cf94c8c5befbc7dffb185de05496738989d2e3fa50e8cb211cfcc6948594cb4",
        )
        summaries = {item["mechanism"]: item for item in report["exact_support"]}
        self.assertEqual(summaries["proportional"]["unsplit"]["point_count"], 76_800)
        self.assertEqual(
            summaries["participant_cap"]["split_advantage"]["positive_points"],
            56_052,
        )
        self.assertEqual(
            summaries["participant_cap"]["split_advantage"]["maximum_positive_amount"],
            495,
        )
        self.assertEqual(
            summaries["principal_cap"]["split_advantage"]["positive_points"], 0
        )
        self.assertEqual(
            summaries["principal_cap"]["unsplit"]["zero_payout_points"], 1_216
        )
        self.assertFalse(contains_float(report))

    def test_trajectory_split_and_liveness_tradeoffs_are_explicit(self) -> None:
        paired = {item["mechanism"]: item for item in self.report["paired_split_comparisons"]}
        self.assertEqual(paired["participant_cap"]["split_advantage"], 480)
        self.assertFalse(paired["participant_cap"]["nonprofitable_split"])
        self.assertEqual(paired["principal_cap"]["split_advantage"], 0)
        self.assertTrue(paired["principal_cap"]["nonprofitable_split"])
        dominant = next(
            item
            for item in self.report["trajectories"]
            if item["scenario_id"] == "dominant_unsplit"
            and item["mechanism"] == "principal_cap"
        )
        self.assertEqual(dominant["expired_credit"], 480)
        self.assertFalse(dominant["objectives"]["bounded_liveness"])
        self.assertTrue(dominant["objectives"]["funded"])
        self.assertTrue(
            all(item["native_funding_failures"] == 0 for item in self.report["trajectories"])
        )

    def test_repeated_study_and_cli_are_byte_identical(self) -> None:
        self.assertEqual(canonical_json(self.report), canonical_json(run_study()))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "reward-distribution.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "simulation/reward_distribution/study.py"),
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
        for path in (ROOT / "simulation/reward_distribution").glob("*.py"):
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
