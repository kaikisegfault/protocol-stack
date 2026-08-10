"""The version-three research scenario, its vectors, and its determinism.

The scenario run is deterministic and takes no input from a test, so it is
executed once and copied per use. The two tests that exist to prove that
determinism build their own runs instead, because a cached run would make both
of them tautologies.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from simulation.cycle_boundary.grid import window_for_cycle
from simulation.founder_economy_v3 import contract as c
from simulation.founder_economy_v3.engine import simulate

from .founder_economy_v3_common import (
    manifest,
    scenario,
    scenario_events,
    vectors,
)

ROOT = Path(__file__).resolve().parents[2]
V2_VECTORS = ROOT / "test-vectors" / "founder-economy-simulator-v2.txt"
V2_EVENTS = (
    ROOT / "simulation" / "founder_economy_v2" / "fixtures" / "research-events-v2.json"
)


class ScenarioTest(unittest.TestCase):
    def setUp(self) -> None:
        self.result = scenario()
        self.records = self.result["records"]
        self.recorded = vectors()

    def test_every_event_reaches_its_recorded_result(self) -> None:
        for record in self.records:
            with self.subTest(event=record["event_id"]):
                self.assertEqual(
                    record["result"], self.recorded[f"record{record['index']}.result"]
                )

    def test_the_digests_match_the_normative_vectors(self) -> None:
        for name in ("state_digest", "trace_digest", "events_digest", "result_digest"):
            self.assertEqual(self.result[name], self.recorded[f"scenario.{name}"])

    def test_every_code_version_three_adds_is_reached(self) -> None:
        produced = {record["result"] for record in self.records}
        self.assertTrue(set(c.ADDED_RESULT_CODES) <= produced)

    def test_the_only_codes_not_reached_are_the_two_guards_and_the_cap(self) -> None:
        """Coverage stated as a set difference rather than as a count."""
        produced = {record["result"] for record in self.records}
        missing = set(c.RESULT_CODES) - produced
        self.assertEqual(missing, set(c.GUARD_RESULT_CODES) | {"CHANNEL_CAP"})

    def test_a_rejected_event_writes_nothing(self) -> None:
        for record in self.records:
            if record["accepted"]:
                continue
            with self.subTest(event=record["event_id"]):
                self.assertEqual(record["journal"], [])
                self.assertEqual(
                    record["state_digest_before"], record["state_digest_after"]
                )

    def test_every_pending_permission_holds_its_own_cycle_window(self) -> None:
        """The enforced form of the gap version two records."""
        seats = self.result["final_state"]["seats"]
        for key, permission in self.result["final_state"]["pending_permissions"].items():
            with self.subTest(permission=key):
                height = int(seats[f"{permission['seat_id']:05d}"]["activation_height"])
                self.assertEqual(
                    permission["cycle_window"],
                    window_for_cycle(height, permission["cycle_index"]),
                )

    def test_the_carry_conservation_identity_holds_at_the_end(self) -> None:
        metrics = self.result["metrics"]
        self.assertEqual(
            int(metrics["founder_accounted_atomic"]),
            metrics["evaluated_permission_key_count"] * c.FOUNDER_OPERATOR_LEG,
        )

    def test_typed_custody_equals_issued_supply(self) -> None:
        custody = sum(
            int(value)
            for value in self.result["final_state"]["typed_custody"].values()
        )
        self.assertEqual(custody, int(self.result["metrics"]["issued_supply_atomic"]))


class DeterminismTest(unittest.TestCase):
    """These build their own runs; a cached one would make them tautologies."""

    def test_two_runs_agree(self) -> None:
        events = scenario_events()
        first = simulate(manifest(), events)
        second = simulate(manifest(), events)
        self.assertEqual(first["result_digest"], second["result_digest"])

    def test_a_prefix_reproduces_the_state_it_held(self) -> None:
        events = scenario_events()
        full = simulate(manifest(), events)
        cut = len(events) // 2
        prefix = simulate(manifest(), events[:cut])
        self.assertEqual(
            prefix["state_digest"], full["records"][cut - 1]["state_digest_after"]
        )


class SharedFixtureTest(unittest.TestCase):
    """Guard the risk the shared run introduces: two callers must not alias."""

    def test_two_callers_get_distinct_objects(self) -> None:
        first = scenario()
        second = scenario()
        self.assertIsNot(first, second)
        first["records"][0]["result"] = "MUTATED"
        self.assertNotEqual(second["records"][0]["result"], "MUTATED")


class RetainedEvidenceTest(unittest.TestCase):
    def test_the_version_two_scenario_still_reproduces_its_recorded_digests(self) -> None:
        """Version three must not perturb the accepted version-two evidence."""
        from simulation.founder_economy_v2.engine import simulate as simulate_v2
        from simulation.founder_economy_v2.manifest import load_manifest_file
        from simulation.founder_economy_v2.validation import load_events_file

        recorded: dict[str, str] = {}
        for line in V2_VECTORS.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.strip().partition("=")
            if separator and not key.startswith("#"):
                recorded[key] = value

        result = simulate_v2(
            load_manifest_file(ROOT / "test-vectors" / "founder-economy-manifest-v2.json"),
            load_events_file(V2_EVENTS),
        )
        self.assertEqual(result["state_digest"], recorded["scenario.state_digest"])
        self.assertEqual(result["result_digest"], recorded["scenario.result_digest"])


if __name__ == "__main__":
    unittest.main()
