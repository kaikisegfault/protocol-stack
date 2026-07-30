#!/usr/bin/env python3
"""Seeded participation scenario and command-line reproducibility tests."""

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

from simulation.participation import generate_scenario, simulate
from simulation.participation.domain import canonical_json
from simulation.participation.scenario import SplitMix64
from simulation.participation.study import run_study


class ParticipationScenarioTest(unittest.TestCase):
    def test_splitmix64_v1_known_stream(self) -> None:
        stream = SplitMix64(0)
        self.assertEqual(
            [stream.next() for _ in range(4)],
            [
                16294208416658607535,
                7960286522194355700,
                487617019471545679,
                17909611376780542444,
            ],
        )

    def test_seeded_runs_cover_lifecycle_and_fund_claims(self) -> None:
        report = run_study(0, 24, 4)
        self.assertTrue(report["all_events_accepted"])
        self.assertTrue(report["all_claims_funded"])
        self.assertEqual(len(report["runs"]), 24)
        self.assertTrue(all(run["accepted_proofs"] > 0 for run in report["runs"]))
        self.assertTrue(
            all(15 <= run["funding_event_count"] <= 16 for run in report["runs"])
        )
        self.assertTrue(any(run["funding_event_count"] == 15 for run in report["runs"]))
        self.assertTrue(
            all(
                run["participants"]["validator"]["exited"] == 1
                and run["participants"]["node"]["removed"] == 1
                for run in report["runs"]
            )
        )

    def test_generator_and_replay_are_byte_identical(self) -> None:
        first_manifest, first_events = generate_scenario(0x5EED, 6)
        second_manifest, second_events = generate_scenario(0x5EED, 6)
        self.assertEqual(canonical_json(first_manifest), canonical_json(second_manifest))
        self.assertEqual(canonical_json(first_events), canonical_json(second_events))
        self.assertEqual(
            canonical_json(simulate(first_manifest, first_events)),
            canonical_json(simulate(second_manifest, second_events)),
        )

    def test_command_line_generation_execution_and_study(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            events_path = root / "events.json"
            result_path = root / "result.json"
            study_path = root / "study.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "simulation/participation/generate.py"),
                    "0x5eed",
                    str(manifest_path),
                    str(events_path),
                    "--rounds",
                    "3",
                ],
                check=True,
                cwd=ROOT,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "simulation/participation/run.py"),
                    str(manifest_path),
                    str(events_path),
                    "--output",
                    str(result_path),
                ],
                check=True,
                cwd=ROOT,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "simulation/participation/study.py"),
                    "--seed-count",
                    "2",
                    "--rounds",
                    "2",
                    "--output",
                    str(study_path),
                ],
                check=True,
                cwd=ROOT,
            )
            direct = simulate(
                json.loads(manifest_path.read_text(encoding="utf-8")),
                json.loads(events_path.read_text(encoding="utf-8")),
            )
            generated = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(canonical_json(generated), canonical_json(direct))
            self.assertTrue(
                json.loads(study_path.read_text(encoding="utf-8"))[
                    "all_claims_funded"
                ]
            )

    def test_generator_bounds_and_study_digest(self) -> None:
        with self.assertRaises(ValueError):
            generate_scenario(-1)
        with self.assertRaises(ValueError):
            generate_scenario(0, 0)
        with self.assertRaises(ValueError):
            generate_scenario(0, 33)
        first = run_study(0, 24, 4)
        second = run_study(0, 24, 4)
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertEqual(
            first["study_digest"],
            "a76ab6f63132d99ae80809aa1d8f9e8d61763218a7414e8d8efd5e3000a68a57",
        )

    def test_package_imports_only_standard_library_and_local_models(self) -> None:
        allowed = {"simulation"}
        standard = set(sys.stdlib_module_names)
        for path in (ROOT / "simulation/participation").glob("*.py"):
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
