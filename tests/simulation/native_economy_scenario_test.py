#!/usr/bin/env python3
"""Seeded scenario and command-line reproducibility tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from simulation.native_economy import generate_scenario, simulate
from simulation.native_economy.scenario import SplitMix64
from simulation.native_economy.study import run_study
from simulation.native_economy.types import canonical_json


class NativeEconomyScenarioTest(unittest.TestCase):
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

    def test_seeded_multi_actor_runs_are_conserved(self) -> None:
        digests = set()
        for seed in range(24):
            manifest, events = generate_scenario(seed, rounds=4)
            result = simulate(manifest, events)
            self.assertTrue(all(record["accepted"] for record in result["records"]))
            self.assertTrue(
                all(
                    sum(entry["delta"] for entry in record["journal"]) == 0
                    for record in result["records"]
                )
            )
            inventory = result["metrics"]["inventory"]
            custody = sum(
                inventory[key]
                for key in (
                    "accounts",
                    "fee_pool",
                    "treasury",
                    "escrows",
                    "bonded",
                    "unbonding",
                    "reward_pool",
                    "validator_claims",
                    "node_claims",
                    "penalty_pool",
                )
            )
            self.assertEqual(custody, inventory["issued_supply"])
            self.assertEqual(
                inventory["issued_supply"] + inventory["issuance_capacity"],
                inventory["supply_limit"],
            )
            digests.add(result["trace_digest"])
        self.assertEqual(len(digests), 24)

    def test_generator_and_replay_are_byte_identical(self) -> None:
        first_manifest, first_events = generate_scenario(0x5EED, rounds=6)
        second_manifest, second_events = generate_scenario(0x5EED, rounds=6)
        self.assertEqual(canonical_json(first_manifest), canonical_json(second_manifest))
        self.assertEqual(canonical_json(first_events), canonical_json(second_events))
        self.assertEqual(
            canonical_json(simulate(first_manifest, first_events)),
            canonical_json(simulate(second_manifest, second_events)),
        )

    def test_command_line_generation_and_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            events_path = root / "events.json"
            result_path = root / "result.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "simulation/native_economy/generate.py"),
                    "0x5eed",
                    str(manifest_path),
                    str(events_path),
                    "--rounds",
                    "3",
                ],
                check=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "simulation/native_economy/run.py"),
                    str(manifest_path),
                    str(events_path),
                    "--output",
                    str(result_path),
                ],
                check=True,
            )
            generated = json.loads(result_path.read_text(encoding="utf-8"))
            direct = simulate(
                json.loads(manifest_path.read_text(encoding="utf-8")),
                json.loads(events_path.read_text(encoding="utf-8")),
            )
            self.assertEqual(canonical_json(generated), canonical_json(direct))

    def test_generator_rejects_invalid_bounds(self) -> None:
        with self.assertRaises(ValueError):
            generate_scenario(-1)
        with self.assertRaises(ValueError):
            generate_scenario(0, rounds=0)
        with self.assertRaises(ValueError):
            generate_scenario(0, rounds=65)

    def test_study_report_is_exact_and_repeatable(self) -> None:
        first = run_study(0, 24, 4)
        second = run_study(0, 24, 4)
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertTrue(first["all_events_accepted"])
        self.assertTrue(first["all_runs_conserved"])
        self.assertEqual(len(first["runs"]), 24)
        self.assertEqual(
            first["study_digest"],
            "13e5f4dab789137b99e87197bb8c735e200ec9892e823e8b26a0bac1827d98f1",
        )


if __name__ == "__main__":
    unittest.main()
