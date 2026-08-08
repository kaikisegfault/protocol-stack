#!/usr/bin/env python3
"""Founder Economy v2 complete-schedule, cap, overflow, and vector scenarios."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import MAX_U64
from simulation.founder_economy_v2 import contract as c
from simulation.founder_economy_v2.engine import simulate
from simulation.founder_economy_v2.uptime import reallocate
from simulation.founder_economy_v2.validation import load_events_file
from tests.simulation.founder_economy_v2_common import (
    EVENTS_PATH,
    FULL_WINDOW,
    accrue,
    activate,
    codes,
    custody,
    direct,
    evaluate,
    evaluate_alone,
    exercise,
    manifest,
    record,
    simulator_vectors,
)

VENTURE = "venture_escrow:global"
COMMUNITY = "community_grants_escrow:global"
DEVELOPER = "developer_incentives_escrow:global"
SYSTEM = "system_creator_company:global"
POOL = "unreferred_performance_pool:global"


def seat(index: int) -> str:
    return f"founder_seat:{index:05d}"


def run(events: list[dict]) -> dict:
    return simulate(manifest(), events)


class CompleteScheduleTest(unittest.TestCase):
    """One seat across all 731 cycles reproduces the manifest's per-seat products."""

    @classmethod
    def setUpClass(cls) -> None:
        events = [activate(0)]
        for cycle in range(c.ISSUANCE_CYCLES_PER_SEAT):
            events.append(evaluate_alone(0, cycle, FULL_WINDOW, window=cycle))
            events.append(exercise(0, cycle))
            events.append(accrue(0, cycle))
        cls.result = run(events)
        cls.event_count = len(events)

    def test_every_event_was_accepted(self) -> None:
        self.assertEqual(set(codes(self.result)), {"OK"})
        self.assertEqual(self.event_count, 1 + 3 * c.ISSUANCE_CYCLES_PER_SEAT)

    def test_per_seat_products_match_the_contract(self) -> None:
        cycles = c.ISSUANCE_CYCLES_PER_SEAT
        self.assertEqual(custody(self.result, seat(0)), 34_200_000_000 * cycles)
        self.assertEqual(custody(self.result, seat(0)), 25_000_200_000_000)
        self.assertEqual(custody(self.result, VENTURE), 12_500_100_000_000)
        self.assertEqual(custody(self.result, COMMUNITY), 2_500_020_000_000)
        self.assertEqual(custody(self.result, DEVELOPER), 1_250_010_000_000)
        self.assertEqual(custody(self.result, SYSTEM), 731_000_000_000)

    def test_the_unreferred_pool_receives_the_whole_referral_schedule(self) -> None:
        self.assertEqual(
            custody(self.result, POOL), c.REFERRAL_AMOUNT * c.ISSUANCE_CYCLES_PER_SEAT
        )
        self.assertEqual(custody(self.result, POOL), 2_500_020_000_000)

    def test_issued_supply_is_the_complete_per_seat_schedule(self) -> None:
        base = c.BASE_PERMISSION_TOTAL * c.ISSUANCE_CYCLES_PER_SEAT
        referral = c.REFERRAL_AMOUNT * c.ISSUANCE_CYCLES_PER_SEAT
        self.assertEqual(base, 41_981_330_000_000)
        self.assertEqual(
            int(self.result["metrics"]["issued_supply_atomic"]), base + referral
        )

    def test_nothing_remains_outstanding_or_carried(self) -> None:
        metrics = self.result["metrics"]
        self.assertEqual(int(metrics["outstanding_permissions_atomic"]), 0)
        self.assertEqual(int(metrics["performance_carry_atomic"]), 0)
        self.assertEqual(metrics["pending_permission_count"], 0)
        self.assertEqual(
            metrics["evaluated_permission_key_count"], c.ISSUANCE_CYCLES_PER_SEAT
        )
        self.assertEqual(
            metrics["referral_accrual_key_count"], c.ISSUANCE_CYCLES_PER_SEAT
        )

    def test_one_seat_consumes_a_bounded_share_of_every_channel(self) -> None:
        for channel_id, channel in self.result["metrics"]["channels"].items():
            issued = int(channel["issued_atomic"])
            cap = c.CHANNEL_CAPS[channel_id]
            self.assertLessEqual(issued, cap)
            if channel_id in {c.FOUNDER_CHANNEL, c.REFERRAL_CHANNEL}:
                # A single seat is one hundred-thousandth of the population.
                self.assertEqual(issued * c.FOUNDER_SEAT_CAPACITY, cap)


class PrefixDeterminismTest(unittest.TestCase):
    """A prefix run reproduces the state the full run held at that point."""

    def test_every_prefix_matches_the_full_run(self) -> None:
        events = [
            activate(0),
            activate(1, 0),
            activate(2, 0),
            evaluate(0, 0, record(1, {0: 3600, 1: FULL_WINDOW, 2: FULL_WINDOW})),
            accrue(1, 0),
            exercise(0, 0),
            evaluate(1, 0, record(2, {1: 0, 2: 0})),
            accrue(2, 0),
            direct(),
        ]
        full = run(list(events))
        for length in range(1, len(events) + 1):
            prefix = run(list(events[:length]))
            self.assertEqual(
                prefix["state_digest"],
                full["records"][length - 1]["state_digest_after"],
                f"prefix of length {length} diverged",
            )


class ChannelCapTest(unittest.TestCase):
    """A channel cap binds exactly, and exhaustion is a rejection not an overflow."""

    CHANNEL = "initial_mystery_box_incentives"

    def test_the_whole_cap_is_issuable_in_one_decision(self) -> None:
        cap = c.CHANNEL_CAPS[self.CHANNEL]
        result = run([direct(channel=self.CHANNEL, amount=str(cap))])
        self.assertEqual(codes(result), ["OK"])
        self.assertEqual(
            int(result["metrics"]["channels"][self.CHANNEL]["remaining_atomic"]), 0
        )

    def test_one_atomic_unit_above_the_cap_is_rejected(self) -> None:
        cap = c.CHANNEL_CAPS[self.CHANNEL]
        self.assertEqual(
            codes(run([direct(channel=self.CHANNEL, amount=str(cap + 1))])),
            ["CHANNEL_CAP"],
        )

    def test_an_exhausted_channel_rejects_the_next_unit(self) -> None:
        cap = c.CHANNEL_CAPS[self.CHANNEL]
        result = run(
            [
                direct(channel=self.CHANNEL, amount=str(cap)),
                direct(channel=self.CHANNEL, amount="1"),
            ]
        )
        self.assertEqual(codes(result), ["OK", "CHANNEL_CAP"])

    def test_a_u64_maximum_amount_is_a_cap_rejection(self) -> None:
        self.assertEqual(
            codes(run([direct(channel=self.CHANNEL, amount=str(MAX_U64))])),
            ["CHANNEL_CAP"],
        )

    def test_exhausting_one_channel_leaves_the_others_untouched(self) -> None:
        cap = c.CHANNEL_CAPS[self.CHANNEL]
        result = run(
            [
                direct(channel=self.CHANNEL, amount=str(cap)),
                activate(0),
                evaluate_alone(0, 0),
                exercise(0, 0),
            ]
        )
        self.assertEqual(codes(result), ["OK"] * 4)
        self.assertEqual(custody(result, seat(0)), c.FOUNDER_OPERATOR_LEG)


class OverflowGuardTest(unittest.TestCase):
    """The checked arithmetic is exercised directly, because caps hide it."""

    def test_a_carry_near_the_u64_maximum_is_an_overflow(self) -> None:
        code, legs, carry = reallocate(MAX_U64, (0,))
        self.assertEqual(code, "ARITHMETIC_OVERFLOW")
        self.assertEqual(legs, ())
        self.assertEqual(carry, MAX_U64)

    def test_overflow_is_unreachable_through_ordinary_events(self) -> None:
        """Every channel cap is far below `u64`, so no event can reach the guard."""
        for cap in c.CHANNEL_CAPS.values():
            self.assertLess(cap * 2, MAX_U64)
        self.assertLess(c.MAXIMUM_SUPPLY_ATOMIC * 2, MAX_U64)


class FixtureVectorTest(unittest.TestCase):
    """The checked-in fixture reproduces the recorded normative vectors."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.result = simulate(manifest(), load_events_file(EVENTS_PATH))
        cls.vectors = simulator_vectors()

    def test_recorded_digests_are_reproduced(self) -> None:
        for name in ("events_digest", "trace_digest", "state_digest", "result_digest"):
            self.assertEqual(self.result[name], self.vectors[f"scenario.{name}"])

    def test_recorded_trace_results_are_reproduced(self) -> None:
        for item in self.result["records"]:
            index = item["index"]
            self.assertEqual(item["kind"], self.vectors[f"record{index}.kind"])
            self.assertEqual(item["result"], self.vectors[f"record{index}.result"])

    def test_the_fixture_reaches_every_modelled_result_code(self) -> None:
        recorded = set(self.vectors["scenario.result_codes"].split(","))
        self.assertEqual({item["result"] for item in self.result["records"]}, recorded)
        self.assertEqual(self.vectors["scenario.result_codes_are_modelled"], "true")

    def test_custody_totals_equal_issued_supply(self) -> None:
        custodied = sum(
            int(value) for value in self.result["final_state"]["typed_custody"].values()
        )
        self.assertEqual(custodied, int(self.result["metrics"]["issued_supply_atomic"]))
        self.assertEqual(str(custodied), self.vectors["scenario.custody_total"])

    def test_the_carry_identity_holds_at_the_recorded_totals(self) -> None:
        metrics = self.result["metrics"]
        self.assertEqual(
            int(metrics["founder_accounted_atomic"]),
            metrics["evaluated_permission_key_count"] * c.FOUNDER_OPERATOR_LEG,
        )
        self.assertEqual(
            metrics["founder_accounted_atomic"],
            self.vectors["scenario.founder_accounted_identity"],
        )


if __name__ == "__main__":
    unittest.main()
