#!/usr/bin/env python3
"""Study bounds, CLI identity, and dependency-boundary tests."""

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

from simulation.authority.domain import MAX_U64, canonical_json
from simulation.economic_stress.study import run_study


class EconomicStressErrorsTest(unittest.TestCase):
    def test_seed_bounds_are_strict(self) -> None:
        for start, count in ((-1, 1), (MAX_U64 + 1, 1), (0, 0), (0, 17), (MAX_U64, 2)):
            with self.subTest(start=start, count=count):
                with self.assertRaises(ValueError):
                    run_study(start, count)

    def test_command_line_output_matches_direct_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "study.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "simulation/economic_stress/study.py"),
                    "--seed-start",
                    "3",
                    "--seed-count",
                    "1",
                    "--output",
                    str(output),
                ],
                check=True,
                cwd=ROOT,
            )
            generated = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(canonical_json(generated), canonical_json(run_study(3, 1)))

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
