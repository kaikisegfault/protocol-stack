#!/usr/bin/env python3
"""Version-three suite tests: schedule, population, restart, escrow, sharing.

These assert what version two's suite asserted, plus the two things that are new
in version three and could not be tested before: that every window a seat
evaluates is the window its recorded activation height assigns, and that every
record covers exactly its window's in-scope seat set. The second changes the
early windows, so the run reaches the founder-directed empty-winner rule with a
complete population rather than in a unit test.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "tools" / "scenario-suite-vectors")
)

import expected_v3 as x

from simulation.cycle_boundary.grid import first_cycle_window, window_for_cycle
from simulation.founder_economy_v3 import contract as c
from simulation.founder_economy_v3.engine import simulate
from simulation.founder_economy_v2.manifest import load_manifest_file
from simulation.founder_economy_v3.validation import parse_events
from simulation.scenarios import economy_population_v3 as population
from simulation.scenarios import economy_schedule_v3 as schedule
from tests.simulation import scenario_v3_common as common

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "test-vectors" / "founder-economy-manifest-v2.json"
PREFIXES = (1, 2, 3, 500, 5_000)

ADDED_CODES = {
    "probe-height-range": "HEIGHT_RANGE",
    "probe-height-not-monotonic": "HEIGHT_NOT_MONOTONIC",
    "probe-window-before-issuance": "WINDOW_BEFORE_ISSUANCE",
    "probe-window-after-issuance": "WINDOW_AFTER_ISSUANCE",
    "probe-window-not-for-cycle": "WINDOW_NOT_FOR_CYCLE",
    "probe-seat-not-in-scope": "SEAT_NOT_IN_SCOPE",
    "probe-incomplete-uptime-record": "INCOMPLETE_UPTIME_RECORD",
}


class ScheduleTest(unittest.TestCase):
    """The enforced schedule, derived from the grid rather than from a tick."""

    def test_the_window_is_the_tick_plus_one_for_every_seat(self) -> None:
        """The property the activation heights exist to produce."""
        checked = 0
        for tick in range(schedule.LAST_TICK + 1):
            for seat_id in range(schedule.SEATS):
                cycle_index = schedule.cycle_at(seat_id, tick)
                if cycle_index is None:
                    continue
                self.assertEqual(
                    window_for_cycle(schedule.HEIGHTS[seat_id], cycle_index),
                    schedule.window_at(tick),
                )
                checked += 1
        self.assertEqual(checked, schedule.SEATS * c.ISSUANCE_CYCLES_PER_SEAT)

    def test_activation_heights_are_non_decreasing_in_emission_order(self) -> None:
        heights = [
            int(event["activation_height"]) for event in population.activations()
        ]
        self.assertEqual(heights, sorted(heights))

    def test_a_seat_enters_the_record_when_its_own_schedule_opens(self) -> None:
        for seat_id in range(schedule.SEATS):
            opens = seat_id * schedule.STAGGER
            with self.subTest(seat=seat_id):
                if opens > 0:
                    self.assertNotIn(seat_id, schedule.in_scope_at(opens - 1))
                self.assertIn(seat_id, schedule.in_scope_at(opens))

    def test_a_seat_stays_in_scope_after_its_issuance_ends(self) -> None:
        """The in-scope set has no upper bound; a paid-out seat is still measured."""
        last_issuing_tick = c.ISSUANCE_CYCLES_PER_SEAT - 1
        self.assertIsNone(schedule.cycle_at(0, last_issuing_tick + 1))
        self.assertIn(0, schedule.in_scope_at(schedule.LAST_TICK))

    def test_the_probe_seats_are_never_in_scope_during_the_run(self) -> None:
        probes = {schedule.PROBE_SEAT, schedule.PEER_SEAT, schedule.LATE_SEAT}
        for tick in range(schedule.LAST_TICK + 1):
            self.assertEqual(probes & set(schedule.in_scope_at(tick)), set())

    def test_the_peer_seat_shares_the_probe_seat_window(self) -> None:
        self.assertEqual(
            first_cycle_window(schedule.HEIGHTS[schedule.PEER_SEAT]),
            first_cycle_window(schedule.HEIGHTS[schedule.PROBE_SEAT]),
        )
        self.assertEqual(
            first_cycle_window(schedule.HEIGHTS[schedule.PROBE_SEAT]),
            schedule.PROBE_WINDOW,
        )

    def test_the_late_seat_opens_exactly_one_window_later(self) -> None:
        self.assertEqual(
            first_cycle_window(schedule.HEIGHTS[schedule.LATE_SEAT]),
            schedule.PROBE_WINDOW + 1,
        )

    def test_exactly_one_window_has_no_eligible_recipient(self) -> None:
        """Seat 0 fails its cycle 0 where it is the only seat in scope."""
        self.assertEqual(schedule.unrewarded_ticks(), (0,))
        self.assertEqual(schedule.in_scope_at(0), (0,))
        self.assertEqual(schedule.failing_seat(0), 0)

    def test_a_record_cannot_express_a_verdict_or_a_winner(self) -> None:
        record = schedule.uptime_record(0)
        self.assertEqual(set(record), {"cycle_window", "entries"})
        for entry in record["entries"]:
            self.assertEqual(set(entry), {"seat_id", "uptime_seconds"})

    def test_every_window_has_at_most_one_failing_seat(self) -> None:
        for tick in range(schedule.LAST_TICK + 1):
            schedule.failing_seat(tick)

    def test_a_window_record_is_a_pure_function_of_its_tick(self) -> None:
        for tick in (0, 61, 122, 500, schedule.LAST_TICK):
            with self.subTest(tick=tick):
                self.assertEqual(
                    schedule.uptime_record(tick), schedule.uptime_record(tick)
                )

    def test_a_record_covers_exactly_its_windows_in_scope_set(self) -> None:
        for tick in range(schedule.LAST_TICK + 1):
            listed = [
                entry["seat_id"] for entry in schedule.uptime_record(tick)["entries"]
            ]
            self.assertEqual(tuple(listed), schedule.in_scope_at(tick))

    def test_the_intended_winner_holds_the_only_maximal_uptime_in_scope(self) -> None:
        rewarded = 0
        for tick in range(schedule.LAST_TICK + 1):
            failing = schedule.failing_seat(tick)
            if failing is None:
                continue
            record = schedule.uptime_record(tick)
            uptimes = {e["seat_id"]: e["uptime_seconds"] for e in record["entries"]}
            self.assertLess(uptimes[failing], c.ACTIVITY_THRESHOLD_SECONDS)
            winner = schedule.rewarded_winner(tick)
            maximal = [s for s, u in uptimes.items() if u == max(uptimes.values())]
            if winner is None:
                self.assertEqual(maximal, [failing])
                continue
            self.assertEqual(maximal, [winner])
            rewarded += 1
        self.assertGreater(rewarded, 0)

    def test_non_winning_seats_sit_exactly_on_the_threshold(self) -> None:
        """So the founder-directed boundary is exercised by the long run."""
        uptimes = [
            entry["uptime_seconds"]
            for entry in schedule.uptime_record(127)["entries"]
        ]
        self.assertIn(c.ACTIVITY_THRESHOLD_SECONDS, uptimes)


class PopulationRunTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = common.economy_result()
        cls.metrics = cls.result["metrics"]
        cls.state = cls.result["final_state"]
        cls.records = common.records_by_id(cls.result)

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
        """Every evaluation accounts one Founder leg, met, reallocated, or carried."""
        self.assertEqual(
            int(self.metrics["channels"]["founder_operator"]["issued_atomic"]),
            x.evaluated_permission_keys() * x.FOUNDER_OPERATOR_LEG,
        )

    def test_the_carry_ends_at_zero_despite_an_unrewarded_window(self) -> None:
        self.assertEqual(x.unrewarded_window_count(), 1)
        self.assertEqual(int(self.state["performance_carry_atomic"]), 0)

    def test_the_unrewarded_windows_portion_is_delivered_not_lost(self) -> None:
        """The whole portion is carried and paid at the next reallocation."""
        received, carried, _ = x.reallocation()
        self.assertEqual(carried, 0)
        self.assertEqual(
            sum(received.values()),
            sum(
                x.inactive_cycle_count(seat_id)
                for seat_id in range(x.POPULATION_SEATS)
            ),
        )

    def test_seat_custody_equals_its_closed_form(self) -> None:
        for seat_id, closed_form in x.economy_seat_custody().items():
            with self.subTest(seat=seat_id):
                self.assertEqual(
                    int(self.state["typed_custody"][f"founder_seat:{seat_id:05d}"]),
                    closed_form,
                )

    def test_the_unreferred_pool_holds_the_unreferred_accruals(self) -> None:
        self.assertEqual(
            int(self.state["typed_custody"]["unreferred_performance_pool:global"]),
            x.unreferred_pool_custody(),
        )

    def test_the_referral_channel_is_consumed_exactly_by_both_destinations(self) -> None:
        custody = self.state["typed_custody"]
        referred = (
            x.POPULATION_REFERRED_SEATS * x.ISSUANCE_CYCLES_PER_SEAT * x.REFERRAL_LEG
        )
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
        self.assertEqual(
            int(self.metrics["issued_supply_atomic"])
            + int(self.metrics["outstanding_permissions_atomic"])
            + int(self.metrics["remaining_capacity_atomic"]),
            x.MAXIMUM_SUPPLY_ATOMIC,
        )

    def test_one_record_is_bound_per_window_and_shared_by_its_seats(self) -> None:
        bound = {int(window) for window in self.state["bound_uptime_records"]}
        expected = set(range(1, schedule.LAST_TICK + 2)) | {x.PROBE_WINDOW}
        self.assertEqual(bound, expected)
        self.assertLess(len(bound), x.evaluated_permission_keys())

    def test_every_recorded_schedule_matches_the_accepted_grid(self) -> None:
        for key, seat in self.state["seats"].items():
            with self.subTest(seat=key):
                height = int(seat["activation_height"])
                self.assertEqual(
                    seat["first_cycle_window"], first_cycle_window(height)
                )

    def test_boundary_probes_are_still_refused_after_the_long_run(self) -> None:
        for _, event_id in x.PROBES:
            with self.subTest(probe=event_id):
                record = self.records[event_id]
                self.assertFalse(record["accepted"])
                self.assertEqual(record["journal"], [])
                self.assertEqual(
                    record["state_digest_before"], record["state_digest_after"]
                )

    def test_the_seven_added_codes_are_reached_by_the_probes(self) -> None:
        self.assertEqual(
            set(ADDED_CODES.values()), set(c.ADDED_RESULT_CODES)
        )
        for event_id, code in ADDED_CODES.items():
            with self.subTest(probe=event_id):
                self.assertEqual(self.records[event_id]["result"], code)

    def test_the_uptime_probes_reach_their_conditions_in_order(self) -> None:
        self.assertEqual(
            [
                self.records["probe-missing-uptime-record"]["result"],
                self.records["probe-invalid-uptime-record"]["result"],
                self.records["probe-incomplete-uptime-record"]["result"],
                self.records["probe-inconsistent-uptime-record"]["result"],
            ],
            [
                "MISSING_UPTIME_RECORD",
                "INVALID_UPTIME_RECORD",
                "INCOMPLETE_UPTIME_RECORD",
                "INCONSISTENT_UPTIME_RECORD",
            ],
        )

    def test_the_peer_events_bind_the_probe_window(self) -> None:
        """Without them the contradiction probe would reach a window code."""
        for _, event_id in x.PEER_EVENTS:
            with self.subTest(event=event_id):
                self.assertTrue(self.records[event_id]["accepted"])

    def test_direct_issue_refuses_the_referral_channel(self) -> None:
        self.assertEqual(
            self.records["probe-direct-referral"]["result"], "INVALID_CHANNEL"
        )

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

    def test_the_drain_binds_the_version_three_population_run(self) -> None:
        self.assertEqual(
            self.escrow["final_state"]["bound_state_digest"],
            self.economy["state_digest"],
        )

    def test_every_escrow_opens_at_what_the_population_run_issued(self) -> None:
        channels = x.economy_channel_totals()
        opening = self.escrow["final_state"]["opening_custody"]
        for escrow_id in (
            "venture_escrow",
            "community_grants_escrow",
            "developer_incentives_escrow",
        ):
            with self.subTest(escrow=escrow_id):
                self.assertEqual(int(opening[escrow_id]), channels[escrow_id])

    def test_every_escrow_is_drained(self) -> None:
        state = self.escrow["final_state"]
        for escrow_id, opening in state["opening_custody"].items():
            with self.subTest(escrow=escrow_id):
                self.assertEqual(int(state["available_custody"][escrow_id]), 0)
                self.assertEqual(
                    int(state["paid_out_total"][escrow_id]), int(opening)
                )

    def test_the_drain_uses_the_version_three_escrow_schema(self) -> None:
        self.assertEqual(
            self.escrow["schema"], "protocol-stack/escrow-payout-result/v3"
        )


class VersionIndependenceTest(unittest.TestCase):
    """Scenarios 2 and 3 are re-proved unchanged rather than inherited."""

    ECONOMY_TOKENS = (
        "founder_economy",
        "ISSUANCE_CYCLES_PER_SEAT",
        "founder_referral",
        "venture_escrow",
        "56993950100",
        "55743940100",
    )
    MARKET_PACKAGES = ("founder_seats", "revenue_routing")

    def test_the_market_models_carry_no_economy_figure(self) -> None:
        for package in self.MARKET_PACKAGES:
            for path in sorted((ROOT / "simulation" / package).glob("*.py")):
                source = path.read_text(encoding="utf-8")
                for token in self.ECONOMY_TOKENS:
                    with self.subTest(path=path.name, token=token):
                        self.assertNotIn(token, source)

    def test_the_market_scenarios_record_identical_vectors(self) -> None:
        files = [
            common.vectors(ROOT / "test-vectors" / f"economy-scenario-suite-{v}.txt")
            for v in ("v1", "v2", "v3")
        ]
        shared = {
            key: value
            for key, value in files[0].items()
            if key.startswith(("seats.", "routing."))
        }
        self.assertGreater(len(shared), 40)
        for index, other in enumerate(files[1:], start=2):
            with self.subTest(version=f"v{index}"):
                self.assertEqual(
                    {k: other[k] for k in shared}, shared
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
