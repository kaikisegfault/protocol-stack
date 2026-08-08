#!/usr/bin/env python3
"""Founder Economy v2 accounting, derived rules, and journal conservation."""

from __future__ import annotations

import sys
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import InvariantError
from simulation.founder_economy_v2 import contract as c
from simulation.founder_economy_v2.engine import simulate
from simulation.founder_economy_v2.operations import journal_delta
from simulation.founder_economy_v2.uptime import met_cycle, reallocate, winner_seats
from tests.simulation.founder_economy_v2_common import (
    FAILED_BOUNDARY,
    FULL_WINDOW,
    MET_BOUNDARY,
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


def bucket_totals(journal: list[dict], prefix: str) -> dict[str, int]:
    totals: dict[str, int] = {}
    for item in journal:
        if item["bucket"].startswith(prefix):
            name = item["bucket"][len(prefix):]
            totals[name] = totals.get(name, 0) + journal_delta(item)
    return totals


class CycleRuleTest(unittest.TestCase):
    """The threshold, the allowance, and the boundary resolved for the operator."""

    def test_threshold_and_allowance_span_the_cycle(self) -> None:
        self.assertEqual(
            c.ACTIVITY_THRESHOLD_SECONDS + c.GRACE_ALLOWANCE_SECONDS,
            c.CYCLE_TARGET_SECONDS,
        )

    def test_exactly_eighteen_hours_meets_the_cycle(self) -> None:
        self.assertTrue(met_cycle(MET_BOUNDARY))

    def test_one_second_below_the_threshold_fails(self) -> None:
        self.assertFalse(met_cycle(FAILED_BOUNDARY))

    def test_exactly_six_hours_of_downtime_meets_the_cycle(self) -> None:
        self.assertTrue(met_cycle(c.CYCLE_TARGET_SECONDS - c.GRACE_ALLOWANCE_SECONDS))

    def test_both_stated_forms_agree_across_the_whole_window(self) -> None:
        for uptime in range(0, c.CYCLE_TARGET_SECONDS + 1, 137):
            met_cycle(uptime)
        for uptime in range(MET_BOUNDARY - 5, MET_BOUNDARY + 5):
            self.assertEqual(met_cycle(uptime), uptime >= MET_BOUNDARY)

    def test_a_met_cycle_keeps_the_founder_portion(self) -> None:
        result = run([activate(0), evaluate_alone(0, 0, MET_BOUNDARY)])
        self.assertEqual(codes(result), ["OK", "OK"])
        legs = result["final_state"]["pending_permissions"]["00000:000"]["legs"]
        founder = [leg for leg in legs if leg["channel"] == c.FOUNDER_CHANNEL]
        self.assertEqual(len(founder), 1)
        self.assertEqual(founder[0]["custody_key"], seat(0))
        self.assertEqual(int(founder[0]["amount_atomic"]), c.FOUNDER_OPERATOR_LEG)

    def test_a_failed_cycle_retains_the_four_fixed_legs(self) -> None:
        result = run(
            [
                activate(0),
                activate(1),
                evaluate(0, 0, record(9, {0: FAILED_BOUNDARY, 1: FULL_WINDOW})),
            ]
        )
        permission = result["final_state"]["pending_permissions"]["00000:000"]
        self.assertFalse(permission["met_cycle"])
        fixed = {
            leg["channel"]: int(leg["amount_atomic"])
            for leg in permission["legs"]
            if leg["channel"] != c.FOUNDER_CHANNEL
        }
        self.assertEqual(sum(fixed.values()), c.FIXED_LEG_TOTAL)
        self.assertEqual(int(permission["total_atomic"]), c.BASE_PERMISSION_TOTAL)


class WinnerSetTest(unittest.TestCase):
    def test_winners_are_the_maximum_among_seats_that_met_the_cycle(self) -> None:
        entries = record(1, {0: 3600, 1: FULL_WINDOW, 2: FULL_WINDOW, 3: MET_BOUNDARY})
        self.assertEqual(winner_seats(entries), (1, 2))

    def test_the_maximum_need_not_be_a_full_window(self) -> None:
        entries = record(1, {0: 3600, 1: 70_000, 2: 69_999})
        self.assertEqual(winner_seats(entries), (1,))

    def test_a_failed_seat_never_wins(self) -> None:
        entries = record(1, {0: FAILED_BOUNDARY, 1: 3600})
        self.assertEqual(winner_seats(entries), ())

    def test_winners_are_ordered_by_seat(self) -> None:
        entries = record(1, {7: FULL_WINDOW, 2: FULL_WINDOW, 5: FULL_WINDOW})
        self.assertEqual(winner_seats(entries), (2, 5, 7))

    def test_the_evaluated_seat_is_excluded_by_failing(self) -> None:
        entries = record(1, {0: 3600, 1: FULL_WINDOW})
        self.assertNotIn(0, winner_seats(entries))


class ReallocationTest(unittest.TestCase):
    def test_an_equal_split_carries_its_remainder(self) -> None:
        code, legs, carry = reallocate(0, tuple(range(1, 8)))
        self.assertIsNone(code)
        self.assertEqual(len(legs), 7)
        self.assertEqual({leg.amount_atomic for leg in legs}, {4_885_714_285})
        self.assertEqual(carry, 5)
        self.assertEqual(sum(leg.amount_atomic for leg in legs) + carry,
                         c.FOUNDER_OPERATOR_LEG)

    def test_a_carried_remainder_reaches_the_next_reallocation(self) -> None:
        code, legs, carry = reallocate(5, (0,))
        self.assertIsNone(code)
        self.assertEqual(legs[0].amount_atomic, c.FOUNDER_OPERATOR_LEG + 5)
        self.assertEqual(carry, 0)

    def test_an_empty_winner_set_carries_the_whole_portion(self) -> None:
        code, legs, carry = reallocate(0, ())
        self.assertIsNone(code)
        self.assertEqual(legs, ())
        self.assertEqual(carry, c.FOUNDER_OPERATOR_LEG)

    def test_the_smallest_possible_share_is_far_above_zero(self) -> None:
        """A zero share is unreachable: the pot always exceeds the winner count."""
        smallest, _ = divmod(c.FOUNDER_OPERATOR_LEG, c.FOUNDER_SEAT_CAPACITY)
        self.assertEqual(smallest, 342_000)
        code, legs, carry = reallocate(0, tuple(range(c.FOUNDER_SEAT_CAPACITY)))
        self.assertIsNone(code)
        self.assertEqual({leg.amount_atomic for leg in legs}, {smallest})
        self.assertEqual(sum(leg.amount_atomic for leg in legs) + carry,
                         c.FOUNDER_OPERATOR_LEG)

    def test_a_zero_share_is_a_model_defect_rather_than_a_result(self) -> None:
        """The guard is proved present by shrinking the portion below the count."""
        with unittest.mock.patch.object(c, "FOUNDER_OPERATOR_LEG", 2):
            with self.assertRaises(InvariantError):
                reallocate(0, (0, 1, 2))

    def test_a_total_outage_then_a_winner_delivers_two_portions(self) -> None:
        result = run(
            [
                activate(0),
                activate(1),
                activate(2),
                # Nobody met window 10, so the whole portion carries forward.
                evaluate(0, 0, record(10, {0: 3600, 1: 0})),
                # Window 11 has a winner, which receives both portions.
                evaluate(1, 0, record(11, {1: 3600, 2: FULL_WINDOW})),
                exercise(1, 0),
            ]
        )
        self.assertEqual(codes(result), ["OK"] * 6)
        self.assertEqual(custody(result, seat(2)), c.FOUNDER_OPERATOR_LEG * 2)
        self.assertEqual(int(result["final_state"]["performance_carry_atomic"]), 0)

    def test_an_unexercised_reallocation_creates_nothing(self) -> None:
        result = run(
            [
                activate(0),
                activate(1),
                evaluate(0, 0, record(10, {0: 3600, 1: FULL_WINDOW})),
            ]
        )
        self.assertEqual(custody(result, seat(1)), 0)
        self.assertEqual(int(result["metrics"]["issued_supply_atomic"]), 0)


class FounderAccountingTest(unittest.TestCase):
    """Issued, outstanding, and carried value account every evaluated portion."""

    def test_identity_holds_across_mixed_paths(self) -> None:
        events = [activate(0), activate(1), activate(2), activate(3)]
        events += [
            evaluate_alone(0, 0, FULL_WINDOW, window=1),
            evaluate(1, 0, record(2, {1: 3600, 2: FULL_WINDOW, 3: FULL_WINDOW})),
            evaluate(2, 0, record(3, {2: 0, 3: 0})),
            evaluate(3, 0, record(4, {3: 3600, 0: FULL_WINDOW, 1: FULL_WINDOW,
                                      2: FULL_WINDOW})),
            exercise(0, 0),
            exercise(1, 0),
        ]
        result = run(events)
        self.assertEqual(codes(result), ["OK"] * len(events))
        metrics = result["metrics"]
        self.assertEqual(
            int(metrics["founder_accounted_atomic"]),
            metrics["evaluated_permission_key_count"] * c.FOUNDER_OPERATOR_LEG,
        )

    def test_every_base_evaluation_journals_exactly_one_portion(self) -> None:
        result = run(
            [
                activate(0),
                activate(1),
                evaluate_alone(0, 0, FULL_WINDOW, window=1),
                evaluate(1, 0, record(2, {1: 3600, 0: FULL_WINDOW})),
                evaluate(0, 1, record(3, {0: 0, 1: 0})),
            ]
        )
        for item in result["records"]:
            if item["kind"] != "evaluate_base_permission":
                continue
            outstanding = bucket_totals(item["journal"], "outstanding:")
            carry = bucket_totals(item["journal"], "carry:")
            self.assertEqual(
                outstanding.get(c.FOUNDER_CHANNEL, 0) + carry.get("performance", 0),
                c.FOUNDER_OPERATOR_LEG,
            )

    def test_only_a_base_evaluation_moves_the_carry(self) -> None:
        result = run(
            [
                activate(0),
                activate(1, 0),
                evaluate_alone(0, 0),
                accrue(1, 0),
                exercise(0, 0),
                direct(),
            ]
        )
        for item in result["records"]:
            if item["kind"] == "evaluate_base_permission":
                continue
            self.assertEqual(bucket_totals(item["journal"], "carry:"), {})


class ReferralAccrualTest(unittest.TestCase):
    def test_a_referred_seat_credits_its_referrer_immediately(self) -> None:
        result = run([activate(0), activate(1, 0), accrue(1, 0)])
        self.assertEqual(codes(result), ["OK", "OK", "OK"])
        self.assertEqual(custody(result, seat(0)), c.REFERRAL_AMOUNT)
        self.assertEqual(
            int(result["metrics"]["channels"][c.REFERRAL_CHANNEL]["issued_atomic"]),
            c.REFERRAL_AMOUNT,
        )

    def test_an_unreferred_seat_credits_the_pool(self) -> None:
        result = run([activate(0), accrue(0, 0)])
        self.assertEqual(custody(result, POOL), c.REFERRAL_AMOUNT)

    def test_the_accrual_is_unconditional(self) -> None:
        """A referred seat that failed its cycle still pays its referrer."""
        result = run(
            [
                activate(0),
                activate(1, 0),
                evaluate_alone(1, 0, 0, window=1),
                accrue(1, 0),
            ]
        )
        self.assertEqual(codes(result), ["OK"] * 4)
        self.assertEqual(custody(result, seat(0)), c.REFERRAL_AMOUNT)

    def test_the_accrual_reserves_no_outstanding_liability(self) -> None:
        result = run([activate(0), accrue(0, 0)])
        channel = result["metrics"]["channels"][c.REFERRAL_CHANNEL]
        self.assertEqual(int(channel["outstanding_atomic"]), 0)
        self.assertEqual(int(channel["issued_atomic"]), c.REFERRAL_AMOUNT)

    def test_both_destinations_consume_the_channel_at_the_same_rate(self) -> None:
        result = run([activate(0), activate(1, 0), accrue(0, 0), accrue(1, 0)])
        self.assertEqual(custody(result, POOL), c.REFERRAL_AMOUNT)
        self.assertEqual(custody(result, seat(0)), c.REFERRAL_AMOUNT)
        self.assertEqual(
            int(result["metrics"]["channels"][c.REFERRAL_CHANNEL]["issued_atomic"]),
            c.REFERRAL_AMOUNT * 2,
        )

    def test_the_channel_cap_is_the_complete_population_product(self) -> None:
        self.assertEqual(
            c.REFERRAL_AMOUNT * c.SEAT_CYCLE_POPULATION,
            c.CHANNEL_CAPS[c.REFERRAL_CHANNEL],
        )

    def test_base_and_referral_keys_are_independent(self) -> None:
        result = run(
            [
                activate(0),
                activate(1, 0),
                evaluate_alone(1, 0),
                accrue(1, 0),
                evaluate_alone(1, 0),
                accrue(1, 0),
            ]
        )
        self.assertEqual(
            codes(result), ["OK", "OK", "OK", "OK", "REPLAY", "REPLAY"]
        )


class RecordBindingTest(unittest.TestCase):
    def test_a_window_binds_once_and_admits_the_same_record(self) -> None:
        shared = record(5, {0: FULL_WINDOW, 1: FULL_WINDOW})
        result = run([activate(0), activate(1), evaluate(0, 0, shared),
                      evaluate(1, 0, shared)])
        self.assertEqual(codes(result), ["OK"] * 4)
        self.assertEqual(result["metrics"]["bound_uptime_record_count"], 1)

    def test_entry_order_does_not_change_the_binding(self) -> None:
        forward = record(5, {0: FULL_WINDOW, 1: FULL_WINDOW})
        reversed_entries = {"cycle_window": 5, "entries": list(reversed(forward["entries"]))}
        result = run([activate(0), activate(1), evaluate(0, 0, forward),
                      evaluate(1, 0, reversed_entries)])
        self.assertEqual(codes(result), ["OK"] * 4)

    def test_a_contradictory_record_for_a_bound_window_is_rejected(self) -> None:
        result = run(
            [
                activate(0),
                activate(1),
                evaluate(0, 0, record(5, {0: FULL_WINDOW, 1: FULL_WINDOW})),
                evaluate(1, 0, record(5, {0: FULL_WINDOW, 1: 3600})),
            ]
        )
        self.assertEqual(codes(result)[-1], "INCONSISTENT_UPTIME_RECORD")

    def test_a_rejected_evaluation_does_not_bind_a_window(self) -> None:
        result = run([activate(0), evaluate(0, 0, record(5, {1: FULL_WINDOW}))])
        self.assertEqual(codes(result)[-1], "INVALID_UPTIME_RECORD")
        self.assertEqual(result["metrics"]["bound_uptime_record_count"], 0)


class DirectIssuanceTest(unittest.TestCase):
    def test_the_referral_channel_is_not_reachable(self) -> None:
        result = run([activate(0), direct(channel=c.REFERRAL_CHANNEL)])
        self.assertEqual(codes(result)[-1], "INVALID_CHANNEL")

    def test_a_base_permission_channel_is_not_reachable(self) -> None:
        result = run([direct(channel=c.FOUNDER_CHANNEL)])
        self.assertEqual(codes(result), ["INVALID_CHANNEL"])

    def test_the_placeholder_covers_four_channels(self) -> None:
        self.assertEqual(len(c.PLACEHOLDER_DIRECT_CHANNELS), 4)
        self.assertNotIn(c.REFERRAL_CHANNEL, c.PLACEHOLDER_DIRECT_CHANNELS)
        self.assertEqual(c.RESEARCH_PLACEHOLDERS, ("direct_channel_eligibility_result",))


class DeterminismTest(unittest.TestCase):
    def test_repeated_runs_are_byte_identical(self) -> None:
        events = [activate(0), activate(1, 0), evaluate_alone(0, 0), accrue(1, 0),
                  exercise(0, 0), direct()]
        first = run(list(events))
        second = run(list(events))
        self.assertEqual(first["result_digest"], second["result_digest"])
        self.assertEqual(first["state_digest"], second["state_digest"])

    def test_every_domain_label_is_version_two(self) -> None:
        from simulation.founder_economy_v2.domain import STATE_LABEL
        from simulation.founder_economy_v2.engine import (
            EVENTS_LABEL,
            RESULT_LABEL,
            TRACE_LABEL,
        )
        from simulation.founder_economy_v2.uptime import RECORD_LABEL

        for label in (STATE_LABEL, EVENTS_LABEL, TRACE_LABEL, RESULT_LABEL, RECORD_LABEL):
            self.assertTrue(label.endswith("-v2"), label)


if __name__ == "__main__":
    unittest.main()
