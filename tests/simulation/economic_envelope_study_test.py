#!/usr/bin/env python3
"""Frozen economic envelope evidence, replay, and CLI tests."""

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

from simulation.authority.domain import canonical_json
from simulation.economic_stress.envelope_study import run_study
from tests.simulation.economic_stress_common import contains_float


class EconomicEnvelopeStudyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_study()

    def test_default_study_fixes_exact_evidence(self) -> None:
        report = self.report
        self.assertEqual(
            report["study_digest"],
            "3af8b35f0ea7e0b378e1974da307dd9d16ae2475089ff4b53e582e815e48559f",
        )
        self.assertEqual(
            report["financial_classification_counts"],
            {"solvent": 12_535_520, "mixed": 0, "insolvent": 8_367_586},
        )
        self.assertEqual(
            report["concentration_classification_counts"],
            {"within_bound": 0, "mixed": 1_536, "concentrated": 0},
        )
        self.assertEqual(len(report["financial_profiles"]), 8_706)
        self.assertEqual(len(report["concentration_cells"]), 1_536)
        self.assertFalse(contains_float(report))

    def test_profiles_and_cells_are_ordered_and_complete(self) -> None:
        report = self.report
        profiles = report["financial_profiles"]
        cells = report["concentration_cells"]
        self.assertEqual(
            [(item["family_id"], item["reward_budget_per_role"]) for item in profiles],
            sorted(
                (item["family_id"], item["reward_budget_per_role"])
                for item in profiles
            ),
        )
        self.assertEqual(
            [
                (item["family_id"], item["validator_weight"], item["node_weight"])
                for item in cells
            ],
            sorted(
                (item["family_id"], item["validator_weight"], item["node_weight"])
                for item in cells
            ),
        )
        self.assertEqual(
            sum(report["financial_classification_counts"].values()),
            report["financial_cell_count"],
        )
        self.assertEqual(
            sum(report["concentration_classification_counts"].values()),
            report["concentration_cell_count"],
        )

    def test_repeated_study_and_cli_are_byte_identical(self) -> None:
        self.assertEqual(canonical_json(self.report), canonical_json(run_study()))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "envelope.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "simulation/economic_stress/envelope_study.py"),
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
        for path in (ROOT / "simulation/economic_stress").glob("*.py"):
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
