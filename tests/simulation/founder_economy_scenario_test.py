#!/usr/bin/env python3
"""Fixture scenario, population, cap-exhaustion, and command-line tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.founder_economy import contract as c
from simulation.founder_economy.engine import simulate
from simulation.founder_economy.validation import parse_events
from tests.simulation.founder_economy_common import (
    FIXTURES,
    MANIFEST_PATH,
    ROOT,
    activate,
    direct,
    evaluate_base,
    evaluate_referral,
    exercise,
    manifest,
    research_events,
)

SIMULATOR_VECTORS = ROOT / "test-vectors" / "founder-economy-simulator-v1.txt"


def simulator_vectors() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in SIMULATOR_VECTORS.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            key, _, value = stripped.partition("=")
            values[key] = value
    return values


class ResearchFixtureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.result = simulate(manifest(), research_events())
        self.recorded = simulator_vectors()

    def test_fixture_reproduces_its_recorded_digests(self) -> None:
        self.assertEqual(self.result["schema"], self.recorded["schema"])
        for name in ("events_digest", "trace_digest", "state_digest", "result_digest"):
            with self.subTest(name=name):
                self.assertEqual(self.result[name], self.recorded[f"scenario.{name}"])

    def test_fixture_reproduces_its_recorded_trace(self) -> None:
        records = self.result["records"]
        self.assertEqual(len(records), int(self.recorded["scenario.event_count"]))
        for index, record in enumerate(records):
            with self.subTest(index=index):
                self.assertEqual(record["kind"], self.recorded[f"record{index}.kind"])
                self.assertEqual(record["result"], self.recorded[f"record{index}.result"])
                self.assertEqual(record["index"], index)

    def test_fixture_reproduces_its_recorded_totals(self) -> None:
        metrics = self.result["metrics"]
        self.assertEqual(
            metrics["issued_supply_atomic"],
            self.recorded["scenario.issued_supply"],
        )
        self.assertEqual(
            metrics["outstanding_permissions_atomic"],
            self.recorded["scenario.outstanding_permissions"],
        )
        self.assertEqual(
            str(metrics["activated_seat_count"]),
            self.recorded["scenario.activated_seat_count"],
        )
        self.assertEqual(
            str(metrics["evaluated_permission_key_count"]),
            self.recorded["scenario.evaluated_permission_key_count"],
        )

    def test_rejections_consume_no_replay_identifier(self) -> None:
        records = self.result["records"]
        rejected = [record for record in records if not record["accepted"]]
        self.assertEqual(len(rejected), int(self.recorded["scenario.rejected_count"]))
        for record in rejected:
            with self.subTest(event=record["event_id"]):
                self.assertEqual(record["journal"], [])
                self.assertEqual(
                    record["state_digest_before"],
                    record["state_digest_after"],
                )

        creations = sum(
            1
            for record in records
            if record["accepted"] and record["kind"].startswith("evaluate_")
        )
        direct_issues = sum(
            1
            for record in records
            if record["accepted"] and record["kind"] == "direct_issue"
        )
        state = self.result["final_state"]
        self.assertEqual(len(state["evaluated_permission_keys"]), creations)
        self.assertEqual(len(state["accepted_direct_decision_ids"]), direct_issues)

    def test_each_record_chains_to_the_next(self) -> None:
        records = self.result["records"]
        for previous, current in zip(records, records[1:]):
            with self.subTest(event=current["event_id"]):
                self.assertEqual(
                    previous["state_digest_after"],
                    current["state_digest_before"],
                )
        self.assertEqual(records[-1]["state_digest_after"], self.result["state_digest"])

    def test_supply_never_exceeds_the_maximum(self) -> None:
        metrics = self.result["metrics"]
        issued = int(metrics["issued_supply_atomic"])
        outstanding = int(metrics["outstanding_permissions_atomic"])
        remaining = int(metrics["remaining_capacity_atomic"])
        self.assertEqual(issued + outstanding + remaining, c.MAXIMUM_SUPPLY_ATOMIC)
        self.assertLessEqual(issued + outstanding, c.MAXIMUM_SUPPLY_ATOMIC)


class PopulationScenarioTest(unittest.TestCase):
    def test_a_referral_chain_credits_each_recorded_referrer(self) -> None:
        events: list[dict] = [activate(0)]
        for seat_id in range(1, 6):
            events.append(activate(seat_id, referrer=seat_id - 1))
        for seat_id in range(1, 6):
            events.append(evaluate_referral(seat_id, 0))
            events.append(exercise(seat_id, 0, "referral"))
        result = simulate(manifest(), events)
        self.assertTrue(all(record["accepted"] for record in result["records"]))

        custody = result["final_state"]["typed_custody"]
        for seat_id in range(0, 5):
            with self.subTest(referrer=seat_id):
                self.assertEqual(
                    custody[f"founder_seat:{seat_id:05d}"],
                    str(c.REFERRAL_AMOUNT),
                )
        self.assertNotIn("founder_seat:00005", custody)
        self.assertEqual(
            result["metrics"]["issued_supply_atomic"],
            str(c.REFERRAL_AMOUNT * 5),
        )

    def test_accumulated_permissions_are_not_issued_supply(self) -> None:
        events: list[dict] = [activate(0)]
        for cycle in range(10):
            events.append(evaluate_base(0, cycle))
        result = simulate(manifest(), events)
        metrics = result["metrics"]
        self.assertEqual(metrics["issued_supply_atomic"], "0")
        self.assertEqual(
            metrics["outstanding_permissions_atomic"],
            str(c.BASE_PERMISSION_TOTAL * 10),
        )
        self.assertEqual(result["final_state"]["typed_custody"], {})
        self.assertEqual(metrics["pending_permission_count"], 10)

        events += [exercise(0, cycle) for cycle in range(10)]
        exercised = simulate(manifest(), events)
        self.assertEqual(
            exercised["metrics"]["issued_supply_atomic"],
            str(c.BASE_PERMISSION_TOTAL * 10),
        )
        self.assertEqual(exercised["metrics"]["outstanding_permissions_atomic"], "0")
        self.assertEqual(exercised["metrics"]["pending_permission_count"], 0)

    def test_an_exhausted_direct_channel_blocks_later_decisions(self) -> None:
        channel = "initial_mystery_box_incentives"
        cap = c.CHANNEL_CAPS[channel]
        events = [
            direct(channel, "decision-a", "beneficiary-a", cap - 1),
            direct(channel, "decision-b", "beneficiary-b", 2),
            direct(channel, "decision-c", "beneficiary-b", 1),
            direct(channel, "decision-d", "beneficiary-b", 1),
        ]
        results = [record["result"] for record in simulate(manifest(), events)["records"]]
        self.assertEqual(results, ["OK", "CHANNEL_CAP", "OK", "CHANNEL_CAP"])

    def test_an_exhausted_channel_does_not_block_another_channel(self) -> None:
        exhausted = "initial_mystery_box_incentives"
        events = [
            direct(exhausted, "decision-a", "beneficiary-a", c.CHANNEL_CAPS[exhausted]),
            direct(exhausted, "decision-b", "beneficiary-a", 1),
            direct("liquidity_mining", "decision-c", "beneficiary-a", 1),
        ]
        results = [record["result"] for record in simulate(manifest(), events)["records"]]
        self.assertEqual(results, ["OK", "CHANNEL_CAP", "OK"])


class CommandLineTest(unittest.TestCase):
    def test_the_runner_emits_a_reproducible_result(self) -> None:
        script = ROOT / "simulation" / "founder_economy" / "run.py"
        events = FIXTURES / "research-events-v1.json"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    str(events),
                    "--manifest",
                    str(MANIFEST_PATH),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["trace_digest"], simulator_vectors()["scenario.trace_digest"])

    def test_the_runner_rejects_malformed_events(self) -> None:
        script = ROOT / "simulation" / "founder_economy" / "run.py"
        with tempfile.TemporaryDirectory() as directory:
            events = Path(directory) / "events.json"
            events.write_text('[{"id": "a", "kind": "unknown"}]', encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(script), str(events)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unsupported", completed.stderr)


class VectorFileTest(unittest.TestCase):
    def test_recorded_events_file_matches_the_checked_in_fixture(self) -> None:
        recorded = simulator_vectors()
        self.assertEqual(
            recorded["events_file"],
            "simulation/founder_economy/fixtures/research-events-v1.json",
        )
        self.assertEqual(
            recorded["manifest_file"],
            "test-vectors/founder-economy-manifest-v1.json",
        )
        self.assertTrue((ROOT / recorded["events_file"]).is_file())
        self.assertTrue((ROOT / recorded["manifest_file"]).is_file())

    def test_the_fixture_parses_under_the_strict_event_schema(self) -> None:
        events = parse_events(research_events())
        self.assertEqual(len(events), int(simulator_vectors()["scenario.event_count"]))


if __name__ == "__main__":
    unittest.main()
