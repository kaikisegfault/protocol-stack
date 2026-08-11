#!/usr/bin/env python3
"""Seeded hostile traffic against the version-three conservation equations.

The properties are the model's own equations, checked against the recorded final
state; the generator predicts nothing. What is new in version three is that a
window and a seat set are now enforced, so a purely random draw would be refused
almost always and the runs would exercise two conditions instead of eighteen.
The generator therefore installs an accepted schedule first and aims each later
event at one condition. That aiming is only useful if it never disturbs the
schedule, which the first test below requires directly.
"""

from __future__ import annotations

import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.founder_economy_v3 import contract as c
from simulation.founder_economy_v3.engine import simulate
from simulation.founder_economy_v2.manifest import load_manifest_file
from simulation.founder_economy_v3.validation import parse_events
from simulation.scenarios import random_economy_v3 as generator

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "test-vectors" / "founder-economy-manifest-v2.json"
SEEDS = range(8)
EVENTS_PER_SEED = 300

# The five conditions the enforced schedule added that an event array can reach
# through a record. `HEIGHT_RANGE` and `HEIGHT_NOT_MONOTONIC` are reached
# through an activation and are asserted separately.
RECORD_CODES = (
    "WINDOW_BEFORE_ISSUANCE",
    "WINDOW_AFTER_ISSUANCE",
    "WINDOW_NOT_FOR_CYCLE",
    "SEAT_NOT_IN_SCOPE",
    "INCOMPLETE_UPTIME_RECORD",
)
ACTIVATION_CODES = ("HEIGHT_RANGE", "HEIGHT_NOT_MONOTONIC")


class EconomyPropertyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest_file(MANIFEST)
        cls.results = [
            (seed, simulate(cls.manifest, parse_events(
                generator.economy_events(seed, EVENTS_PER_SEED)
            )))
            for seed in SEEDS
        ]

    def test_no_hostile_activation_ever_installs_a_seat(self) -> None:
        """Otherwise the generator would aim at sets the model no longer holds."""
        for seed, result in self.results:
            with self.subTest(seed=seed):
                recorded = sorted(result["final_state"]["seats"])
                self.assertEqual(
                    recorded,
                    [f"{seat:05d}" for seat in range(generator.ECONOMY_SEATS)],
                )

    def test_the_runs_reach_every_condition_the_schedule_added(self) -> None:
        codes = Counter(
            record["result"]
            for _, result in self.results
            for record in result["records"]
        )
        for code in RECORD_CODES + ACTIVATION_CODES:
            with self.subTest(code=code):
                self.assertGreater(codes[code], 0)

    def test_the_runs_reach_an_acceptance_as_well_as_a_rejection(self) -> None:
        for seed, result in self.results:
            with self.subTest(seed=seed):
                accepted = sum(1 for r in result["records"] if r["accepted"])
                self.assertGreater(accepted, 0)
                self.assertLess(accepted, len(result["records"]))

    def test_supply_is_always_fully_accounted(self) -> None:
        for seed, result in self.results:
            with self.subTest(seed=seed):
                metrics = result["metrics"]
                self.assertEqual(
                    int(metrics["issued_supply_atomic"])
                    + int(metrics["outstanding_permissions_atomic"])
                    + int(metrics["remaining_capacity_atomic"]),
                    c.MAXIMUM_SUPPLY_ATOMIC,
                )

    def test_custody_always_equals_issued_supply(self) -> None:
        for seed, result in self.results:
            with self.subTest(seed=seed):
                self.assertEqual(
                    sum(
                        int(value)
                        for value in result["final_state"]["typed_custody"].values()
                    ),
                    int(result["metrics"]["issued_supply_atomic"]),
                )

    def test_the_founder_carry_identity_always_holds(self) -> None:
        """Issued plus outstanding plus carried equals the evaluated portions."""
        for seed, result in self.results:
            with self.subTest(seed=seed):
                state = result["final_state"]
                channel = state["channels"]["founder_operator"]
                accounted = (
                    int(channel["issued_atomic"])
                    + int(channel["outstanding_atomic"])
                    + int(state["performance_carry_atomic"])
                )
                self.assertEqual(
                    accounted,
                    len(state["evaluated_permission_keys"]) * c.FOUNDER_OPERATOR_LEG,
                )

    def test_every_pending_permission_holds_its_own_windows(self) -> None:
        """The enforced schedule, read back off an arbitrary hostile run."""
        for seed, result in self.results:
            state = result["final_state"]
            for key, permission in state["pending_permissions"].items():
                with self.subTest(seed=seed, permission=key):
                    seat = state["seats"][f"{permission['seat_id']:05d}"]
                    self.assertEqual(
                        permission["cycle_window"],
                        seat["first_cycle_window"] + permission["cycle_index"],
                    )
                    self.assertLessEqual(
                        permission["cycle_window"], seat["last_cycle_window"]
                    )

    def test_no_channel_ever_exceeds_its_cap(self) -> None:
        for seed, result in self.results:
            with self.subTest(seed=seed):
                for channel_id, channel in result["final_state"]["channels"].items():
                    total = int(channel["issued_atomic"]) + int(
                        channel["outstanding_atomic"]
                    )
                    self.assertLessEqual(total, c.CHANNEL_CAPS[channel_id])

    def test_the_referral_channel_is_never_reached_by_direct_issue(self) -> None:
        for seed, result in self.results:
            with self.subTest(seed=seed):
                for record in result["records"]:
                    if record["kind"] == "direct_issue" and record["accepted"]:
                        self.assertNotEqual(
                            record.get("channel"), c.REFERRAL_CHANNEL
                        )

    def test_a_rejection_never_writes_or_journals(self) -> None:
        for seed, result in self.results:
            with self.subTest(seed=seed):
                for record in result["records"]:
                    if not record["accepted"]:
                        self.assertEqual(record["journal"], [])
                        self.assertEqual(
                            record["state_digest_before"],
                            record["state_digest_after"],
                        )

    def test_the_same_seed_reproduces_the_same_digest(self) -> None:
        for seed, result in self.results:
            with self.subTest(seed=seed):
                replayed = simulate(
                    self.manifest,
                    parse_events(generator.economy_events(seed, EVENTS_PER_SEED)),
                )
                self.assertEqual(replayed["result_digest"], result["result_digest"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
