#!/usr/bin/env python3
"""Version-two suite tests: population, uptime derivation, restart, properties.

These assert what version one's suite asserted, plus the two things that are new
in version two and could not be tested before: that the winner set and the
activity verdict are derived from measurements the generator supplies rather
than from a supplied answer, and that the unreferred performance pool consumes
the referral channel exactly.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "scenario-suite-vectors"))

import expected_v2 as x

from simulation.founder_economy_v2 import contract as c
from simulation.founder_economy_v2.engine import simulate
from simulation.founder_economy_v2.manifest import load_manifest_file
from simulation.founder_economy_v2.validation import parse_events
from simulation.scenarios import economy_population_v2 as population
from simulation.scenarios import random_economy_v2 as generator
from tests.simulation import scenario_v2_common as common

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "test-vectors" / "founder-economy-manifest-v2.json"
SEEDS = range(8)
EVENTS_PER_SEED = 300
PREFIXES = (1, 2, 3, 500, 5_000)


class UptimeRecordTest(unittest.TestCase):
    """The record carries measurements only; the model derives the rest."""

    def test_a_record_cannot_express_a_verdict_or_a_winner(self) -> None:
        record = population.uptime_record(0)
        self.assertEqual(set(record), {"cycle_window", "entries"})
        for entry in record["entries"]:
            self.assertEqual(set(entry), {"seat_id", "uptime_seconds"})

    def test_every_window_has_at_most_one_failing_seat(self) -> None:
        """Two failures in one window would make the winner order-dependent."""
        for tick in range(population.LAST_TICK + 1):
            population.failing_seat(tick)

    def test_a_window_record_is_a_pure_function_of_its_tick(self) -> None:
        for tick in (0, 61, 122, 500, population.LAST_TICK):
            with self.subTest(tick=tick):
                self.assertEqual(
                    population.uptime_record(tick), population.uptime_record(tick)
                )

    def test_the_intended_winner_holds_the_only_maximal_uptime(self) -> None:
        checked = 0
        for tick in range(population.LAST_TICK + 1):
            failing = population.failing_seat(tick)
            if failing is None:
                continue
            record = population.uptime_record(tick)
            uptimes = {e["seat_id"]: e["uptime_seconds"] for e in record["entries"]}
            winner = population.performance_winner(failing)
            maximal = [s for s, u in uptimes.items() if u == max(uptimes.values())]
            self.assertEqual(maximal, [winner])
            self.assertLess(uptimes[failing], c.ACTIVITY_THRESHOLD_SECONDS)
            checked += 1
        self.assertGreater(checked, 0)

    def test_non_winning_seats_sit_exactly_on_the_threshold(self) -> None:
        """So the founder-directed boundary is exercised by the long run."""
        record = population.uptime_record(0)
        uptimes = sorted(e["uptime_seconds"] for e in record["entries"])
        self.assertIn(c.ACTIVITY_THRESHOLD_SECONDS, uptimes)


class SharedFixtureTest(unittest.TestCase):
    """The risk the cached fixture introduces, guarded rather than assumed.

    `scenario_v2_common` executes the population run once and copies it, so a
    test that mutates its result must not reach the next test's. Two callers
    therefore get distinct objects that start from the same state.
    """

    def test_two_callers_get_independent_copies_of_one_run(self) -> None:
        first, second = common.economy_result(), common.economy_result()
        self.assertIsNot(first, second)
        self.assertEqual(first["state_digest"], second["state_digest"])
        first["final_state"]["typed_custody"].clear()
        self.assertNotEqual(
            first["final_state"]["typed_custody"],
            second["final_state"]["typed_custody"],
        )
        self.assertEqual(
            sum(int(value) for value in second["final_state"]["typed_custody"].values()),
            int(second["metrics"]["issued_supply_atomic"]),
        )

    def test_the_escrow_fixture_is_copied_the_same_way(self) -> None:
        first, second = common.escrow_result(), common.escrow_result()
        self.assertIsNot(first, second)
        self.assertEqual(
            first["final_state"]["bound_state_digest"],
            second["final_state"]["bound_state_digest"],
        )
        first["final_state"]["opening_custody"].clear()
        self.assertNotEqual(
            first["final_state"]["opening_custody"],
            second["final_state"]["opening_custody"],
        )


class PopulationRunTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = common.economy_result()
        cls.metrics = cls.result["metrics"]
        cls.state = cls.result["final_state"]

    def test_every_seat_completes_its_whole_issuance_window(self) -> None:
        self.assertEqual(
            self.metrics["evaluated_permission_key_count"],
            x.evaluated_permission_keys(),
        )

    def test_channel_totals_equal_their_closed_form(self) -> None:
        for channel_id, closed_form in x.economy_channel_totals().items():
            with self.subTest(channel=channel_id):
                self.assertEqual(
                    int(self.metrics["channels"][channel_id]["issued_atomic"]),
                    closed_form,
                )

    def test_reallocation_moves_a_beneficiary_and_not_an_amount(self) -> None:
        """Every evaluation reserves exactly one Founder leg, met or failed."""
        self.assertEqual(
            int(self.metrics["channels"]["founder_operator"]["issued_atomic"]),
            x.evaluated_permission_keys() * x.FOUNDER_OPERATOR_LEG,
        )

    def test_the_performance_carry_ends_at_zero(self) -> None:
        """One winner per reallocating window leaves no integer remainder."""
        self.assertEqual(int(self.state["performance_carry_atomic"]), 0)

    def test_seat_custody_equals_its_closed_form(self) -> None:
        for seat_id, closed_form in x.economy_seat_custody().items():
            with self.subTest(seat=seat_id):
                self.assertEqual(
                    int(self.state["typed_custody"][f"founder_seat:{seat_id:05d}"]),
                    closed_form,
                )

    def test_the_unreferred_pool_holds_the_unreferred_seats_accruals(self) -> None:
        self.assertEqual(
            int(self.state["typed_custody"]["unreferred_performance_pool:global"]),
            x.unreferred_pool_custody(),
        )

    def test_the_referral_channel_is_consumed_exactly_by_both_destinations(self) -> None:
        """Referrer custody plus the pool must equal the channel's issuance."""
        custody = self.state["typed_custody"]
        referred = x.POPULATION_REFERRED_SEATS * x.ISSUANCE_CYCLES_PER_SEAT * x.REFERRAL_LEG
        self.assertEqual(
            referred + int(custody["unreferred_performance_pool:global"]),
            int(self.metrics["channels"]["founder_referral"]["issued_atomic"]),
        )

    def test_custody_equals_issued_supply(self) -> None:
        self.assertEqual(
            sum(int(value) for value in self.state["typed_custody"].values()),
            int(self.metrics["issued_supply_atomic"]),
        )

    def test_supply_stays_inside_the_revised_maximum(self) -> None:
        self.assertLessEqual(
            int(self.metrics["issued_supply_atomic"]), x.MAXIMUM_SUPPLY_ATOMIC
        )
        self.assertEqual(
            int(self.metrics["issued_supply_atomic"])
            + int(self.metrics["outstanding_permissions_atomic"])
            + int(self.metrics["remaining_capacity_atomic"]),
            x.MAXIMUM_SUPPLY_ATOMIC,
        )

    def test_boundary_probes_are_still_refused_after_the_long_run(self) -> None:
        records = {r["event_id"]: r for r in self.result["records"]}
        for _, event_id in x.PROBES:
            with self.subTest(probe=event_id):
                record = records[event_id]
                self.assertFalse(record["accepted"])
                self.assertEqual(record["journal"], [])
                self.assertEqual(
                    record["state_digest_before"], record["state_digest_after"]
                )

    def test_the_three_uptime_probes_reach_three_distinct_conditions(self) -> None:
        records = {r["event_id"]: r for r in self.result["records"]}
        self.assertEqual(
            [
                records["probe-missing-uptime-record"]["result"],
                records["probe-invalid-uptime-record"]["result"],
                records["probe-inconsistent-uptime-record"]["result"],
            ],
            ["MISSING_UPTIME_RECORD", "INVALID_UPTIME_RECORD", "INCONSISTENT_UPTIME_RECORD"],
        )

    def test_direct_issue_refuses_the_referral_channel(self) -> None:
        records = {r["event_id"]: r for r in self.result["records"]}
        self.assertEqual(records["probe-direct-referral"]["result"], "INVALID_CHANNEL")

    def test_no_rejection_writes_or_journals(self) -> None:
        for record in self.result["records"]:
            if not record["accepted"]:
                self.assertEqual(record["journal"], [])
                self.assertEqual(
                    record["state_digest_before"], record["state_digest_after"]
                )


class RestartEquivalenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.events = population.events()
        cls.manifest = load_manifest_file(MANIFEST)
        cls.result = common.economy_result()

    def test_a_replayed_prefix_reaches_the_recorded_digest(self) -> None:
        for length in PREFIXES:
            with self.subTest(prefix=length):
                replayed = simulate(
                    self.manifest, parse_events(self.events[:length])
                )
                self.assertEqual(
                    replayed["state_digest"],
                    self.result["records"][length - 1]["state_digest_after"],
                )

    def test_the_full_run_ends_at_its_last_recorded_digest(self) -> None:
        self.assertEqual(
            self.result["records"][-1]["state_digest_after"],
            self.result["state_digest"],
        )


class EscrowJoinTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.economy = common.economy_result()
        cls.escrow = common.escrow_result()

    def test_the_drain_binds_the_version_two_population_run(self) -> None:
        self.assertEqual(
            self.escrow["final_state"]["bound_state_digest"],
            self.economy["state_digest"],
        )

    def test_every_escrow_opens_at_what_the_population_run_issued(self) -> None:
        channels = x.economy_channel_totals()
        opening = self.escrow["final_state"]["opening_custody"]
        for escrow_id in ("venture_escrow", "community_grants_escrow", "developer_incentives_escrow"):
            with self.subTest(escrow=escrow_id):
                self.assertEqual(int(opening[escrow_id]), channels[escrow_id])

    def test_every_escrow_is_drained(self) -> None:
        state = self.escrow["final_state"]
        for escrow_id, opening in state["opening_custody"].items():
            with self.subTest(escrow=escrow_id):
                self.assertEqual(int(state["available_custody"][escrow_id]), 0)
                self.assertEqual(int(state["paid_out_total"][escrow_id]), int(opening))

    def test_the_drain_uses_the_version_two_escrow_schema(self) -> None:
        self.assertEqual(self.escrow["schema"], "protocol-stack/escrow-payout-result/v2")


class EconomyPropertyTest(unittest.TestCase):
    """Seeded hostile traffic against the model's conservation equations."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest_file(MANIFEST)
        cls.results = [
            (
                seed,
                simulate(
                    cls.manifest,
                    parse_events(generator.economy_events(seed, EVENTS_PER_SEED)),
                ),
            )
            for seed in SEEDS
        ]

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

    def test_the_same_seed_reproduces_the_same_digest(self) -> None:
        for seed in SEEDS:
            with self.subTest(seed=seed):
                first = simulate(
                    self.manifest,
                    parse_events(generator.economy_events(seed, EVENTS_PER_SEED)),
                )
                second = simulate(
                    self.manifest,
                    parse_events(generator.economy_events(seed, EVENTS_PER_SEED)),
                )
                self.assertEqual(first["result_digest"], second["result_digest"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
