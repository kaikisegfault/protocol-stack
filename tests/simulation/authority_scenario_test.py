#!/usr/bin/env python3
"""Seeded authority study and command-line reproducibility tests."""

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

from simulation.authority import generate_scenario, simulate
from simulation.authority.domain import MAX_U64, canonical_json
from simulation.authority.scenario import SplitMix64
from simulation.authority.study import run_study


class AuthorityScenarioTest(unittest.TestCase):
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

    def test_study_covers_adversarial_results_and_both_adapters(self) -> None:
        report = run_study(0, 24)
        self.assertTrue(report["all_adapter_events_accepted"])
        self.assertEqual(len(report["runs"]), 24)
        self.assertTrue(all(run["rejected_count"] >= 19 for run in report["runs"]))
        self.assertTrue(all(run["recoveries"] == 2 for run in report["runs"]))
        required = {
            "ACTION_REPLAY",
            "DIGEST_MISMATCH",
            "DOMAIN_MISMATCH",
            "DUPLICATE_MEMBER",
            "EXPIRED",
            "PAUSED",
            "PROOF_REPLAY",
            "RESULT_REPLAY",
            "THRESHOLD",
            "TOO_EARLY",
            "UNAUTHORIZED_MEMBER",
            "WRONG_SET",
        }
        self.assertTrue(required <= set(report["observed_result_codes"]))

    def test_generator_and_replay_are_byte_identical(self) -> None:
        first_manifest, first_events = generate_scenario(0x5EED)
        second_manifest, second_events = generate_scenario(0x5EED)
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
                    str(ROOT / "simulation/authority/generate.py"),
                    "--seed",
                    "0x5eed",
                    "--manifest",
                    str(manifest_path),
                    "--events",
                    str(events_path),
                ],
                check=True,
                cwd=ROOT,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "simulation/authority/run.py"),
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
                    str(ROOT / "simulation/authority/study.py"),
                    "--seed-count",
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
                    "all_adapter_events_accepted"
                ]
            )

    def test_generator_bounds_and_study_digest(self) -> None:
        with self.assertRaises(ValueError):
            generate_scenario(-1)
        with self.assertRaises(ValueError):
            generate_scenario(MAX_U64 + 1)
        first = run_study(0, 24)
        second = run_study(0, 24)
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertEqual(
            first["study_digest"],
            "74e0913b379151a3fd72529837b0dcb31002dbe33251ad5e3ae4bb2fc1739ea4",
        )

    def test_package_imports_only_standard_library_and_local_models(self) -> None:
        allowed = {"simulation"}
        standard = set(sys.stdlib_module_names)
        for path in (ROOT / "simulation/authority").glob("*.py"):
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
