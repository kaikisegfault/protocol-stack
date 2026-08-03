#!/usr/bin/env python3
"""Founder Economy accounting, journal conservation, and schedule tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.founder_economy import contract as c
from simulation.founder_economy.engine import simulate
from simulation.founder_economy.operations import INCREASE, journal_delta
from tests.simulation.founder_economy_common import (
    activate,
    direct,
    evaluate_base,
    evaluate_referral,
    exercise,
    manifest,
    vectors,
)

VENTURE = "venture_escrow:global"
COMMUNITY = "community_grants_escrow:global"
DEVELOPER = "developer_incentives_escrow:global"
SYSTEM = "system_creator_company:global"


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


class BasePermissionTest(unittest.TestCase):
    def test_active_cycle_reserves_without_issuing(self) -> None:
        result = run([activate(0), evaluate_base(0, 0)])
        record = result["records"][-1]
        self.assertTrue(record["accepted"])

        reserved = bucket_totals(record["journal"], "outstanding:")
        self.assertEqual(reserved["venture_escrow"], 17_100_000_000)
        self.assertEqual(reserved["community_grants_escrow"], 3_420_000_000)
        self.assertEqual(reserved["developer_incentives_escrow"], 1_710_000_000)
        self.assertEqual(reserved["system_creator_issuance_royalty"], 1_000_000_000)
        self.assertEqual(reserved["founder_operator"], 34_200_000_000)
        self.assertEqual(sum(reserved.values()), c.BASE_PERMISSION_TOTAL)

        self.assertEqual(bucket_totals(record["journal"], "custody:"), {})
        self.assertEqual(result["metrics"]["issued_supply_atomic"], "0")
        self.assertEqual(
            result["metrics"]["outstanding_permissions_atomic"],
            str(c.BASE_PERMISSION_TOTAL),
        )
        self.assertEqual(result["final_state"]["typed_custody"], {})

    def test_exercise_issues_every_leg_to_its_typed_beneficiary(self) -> None:
        recorded = vectors()
        result = run([activate(0), evaluate_base(0, 0), exercise(0, 0)])
        self.assertTrue(all(record["accepted"] for record in result["records"]))

        custody = result["final_state"]["typed_custody"]
        self.assertEqual(custody[VENTURE], "17100000000")
        self.assertEqual(custody[COMMUNITY], "3420000000")
        self.assertEqual(custody[DEVELOPER], "1710000000")
        self.assertEqual(custody[SYSTEM], "1000000000")
        self.assertEqual(custody[seat(0)], recorded["base_permission.founder_operator"])
        self.assertEqual(
            result["metrics"]["issued_supply_atomic"],
            recorded["active_fixture.issued_delta_after_exercise"],
        )
        self.assertEqual(
            result["metrics"]["outstanding_permissions_atomic"],
            recorded["active_fixture.outstanding_delta_after_exercise"],
        )
        self.assertEqual(result["final_state"]["pending_permissions"], {})
        self.assertEqual(
            result["final_state"]["evaluated_permission_keys"],
            ["00000:000:base"],
        )

    def test_inactive_cycle_reallocates_only_the_founder_leg(self) -> None:
        recorded = vectors()
        events = [
            activate(0),
            activate(1),
            activate(2),
            evaluate_base(
                0,
                1,
                active=False,
                performance={
                    "seat_id": 0,
                    "cycle_index": 1,
                    "allocations": [
                        {"seat_id": 1, "amount_atomic": "17100000000"},
                        {"seat_id": 2, "amount_atomic": "17100000000"},
                    ],
                },
            ),
            exercise(0, 1),
        ]
        result = run(events)
        self.assertTrue(all(record["accepted"] for record in result["records"]))

        custody = result["final_state"]["typed_custody"]
        self.assertNotIn(seat(0), custody)
        self.assertEqual(custody[seat(1)], recorded["inactive_fixture.performance_amount0"])
        self.assertEqual(custody[seat(2)], recorded["inactive_fixture.performance_amount1"])
        self.assertEqual(custody[VENTURE], "17100000000")
        self.assertEqual(custody[COMMUNITY], "3420000000")
        self.assertEqual(custody[DEVELOPER], "1710000000")
        self.assertEqual(custody[SYSTEM], "1000000000")

        non_founder = 17_100_000_000 + 3_420_000_000 + 1_710_000_000 + 1_000_000_000
        self.assertEqual(non_founder, int(recorded["inactive_fixture.non_founder_legs_total"]))
        self.assertEqual(
            result["metrics"]["issued_supply_atomic"],
            recorded["inactive_fixture.base_total"],
        )

    def test_inactive_reallocation_is_permanent_after_later_activity(self) -> None:
        """A later active cycle cannot restore the reallocated Founder leg."""
        events = [
            activate(0),
            activate(1),
            evaluate_base(
                0,
                0,
                active=False,
                performance={
                    "seat_id": 0,
                    "cycle_index": 0,
                    "allocations": [{"seat_id": 1, "amount_atomic": "34200000000"}],
                },
            ),
            evaluate_base(0, 1),
            exercise(0, 0),
            exercise(0, 1),
        ]
        custody = run(events)["final_state"]["typed_custody"]
        self.assertEqual(custody[seat(0)], "34200000000")
        self.assertEqual(custody[seat(1)], "34200000000")


class ReferralPermissionTest(unittest.TestCase):
    def test_referral_credits_the_recorded_referrer(self) -> None:
        recorded = vectors()
        events = [
            activate(3),
            activate(0, referrer=3),
            evaluate_referral(0, 0),
            exercise(0, 0, "referral"),
        ]
        result = run(events)
        self.assertTrue(all(record["accepted"] for record in result["records"]))
        custody = result["final_state"]["typed_custody"]
        self.assertEqual(custody[seat(3)], recorded["referral_fixture.issued_delta_after_exercise"])
        self.assertNotIn(seat(0), custody)
        self.assertEqual(
            result["metrics"]["channels"]["founder_referral"]["issued_atomic"],
            recorded["referral_fixture.outstanding_delta"],
        )

    def test_declined_inactive_referral_consumes_the_key_without_value(self) -> None:
        events = [
            activate(3),
            activate(0, referrer=3),
            evaluate_referral(
                0,
                0,
                active=False,
                inactive_result={"seat_id": 0, "cycle_index": 0, "create": False},
            ),
        ]
        result = run(events)
        record = result["records"][-1]
        self.assertTrue(record["accepted"])
        self.assertEqual(record["journal"], [])
        self.assertEqual(
            result["final_state"]["evaluated_permission_keys"],
            ["00000:000:referral"],
        )
        self.assertEqual(result["metrics"]["outstanding_permissions_atomic"], "0")

    def test_base_and_referral_permissions_are_independent(self) -> None:
        events = [
            activate(3),
            activate(0, referrer=3),
            evaluate_base(0, 0),
            evaluate_referral(0, 0),
            exercise(0, 0, "referral"),
        ]
        result = run(events)
        self.assertTrue(all(record["accepted"] for record in result["records"]))
        state = result["final_state"]
        self.assertEqual(list(state["pending_permissions"]), ["00000:000:base"])
        self.assertEqual(
            state["channels"]["founder_operator"]["outstanding_atomic"],
            "34200000000",
        )
        self.assertEqual(state["channels"]["founder_referral"]["issued_atomic"], "1710000000")


class DirectChannelTest(unittest.TestCase):
    def test_direct_issue_credits_without_creating_a_permission(self) -> None:
        recorded = vectors()
        result = run(
            [
                direct(
                    recorded["direct_fixture.channel"],
                    recorded["direct_fixture.decision_id"],
                    recorded["direct_fixture.beneficiary_id"],
                    int(recorded["direct_fixture.amount"]),
                )
            ]
        )
        record = result["records"][-1]
        self.assertTrue(record["accepted"])
        self.assertEqual(
            result["final_state"]["typed_custody"],
            {
                f"direct_beneficiary:{recorded['direct_fixture.beneficiary_id']}":
                    recorded["direct_fixture.issued_delta"],
            },
        )
        self.assertEqual(
            result["metrics"]["outstanding_permissions_atomic"],
            recorded["direct_fixture.outstanding_delta"],
        )
        self.assertEqual(result["final_state"]["pending_permissions"], {})
        self.assertEqual(
            result["final_state"]["accepted_direct_decision_ids"],
            [recorded["direct_fixture.decision_id"]],
        )

    def test_a_direct_channel_issues_exactly_up_to_its_cap(self) -> None:
        channel = "initial_mystery_box_incentives"
        cap = c.CHANNEL_CAPS[channel]
        result = run(
            [
                direct(channel, "decision-cap", "beneficiary-cap", cap),
                direct(channel, "decision-over", "beneficiary-cap", 1),
            ]
        )
        self.assertTrue(result["records"][0]["accepted"])
        self.assertEqual(result["records"][1]["result"], "CHANNEL_CAP")
        self.assertEqual(
            result["metrics"]["channels"][channel],
            {
                "cap_atomic": str(cap),
                "issued_atomic": str(cap),
                "outstanding_atomic": "0",
                "remaining_atomic": "0",
            },
        )


class ConservationTest(unittest.TestCase):
    def test_every_accepted_journal_satisfies_both_balance_rules(self) -> None:
        events = [
            activate(3),
            activate(0, referrer=3),
            activate(1),
            evaluate_base(0, 0),
            evaluate_referral(0, 0),
            exercise(0, 0),
            exercise(0, 0, "referral"),
            direct("liquidity_mining", "decision-1", "beneficiary-1", 500),
        ]
        result = run(events)
        for record in result["records"]:
            with self.subTest(event=record["event_id"]):
                channel = sum(
                    journal_delta(item)
                    for item in record["journal"]
                    if not item["bucket"].startswith("custody:")
                )
                custody = sum(bucket_totals(record["journal"], "custody:").values())
                issued = sum(bucket_totals(record["journal"], "issued:").values())
                self.assertEqual(channel, 0)
                self.assertEqual(custody, issued)
                self.assertTrue(
                    all(int(item["amount_atomic"]) > 0 for item in record["journal"])
                )

    def test_custody_always_equals_issued_supply(self) -> None:
        events = [activate(0), evaluate_base(0, 0), exercise(0, 0)]
        result = run(events)
        custody = sum(int(value) for value in result["final_state"]["typed_custody"].values())
        self.assertEqual(str(custody), result["metrics"]["issued_supply_atomic"])
        self.assertEqual(custody, c.BASE_PERMISSION_TOTAL)

    def test_capacity_issued_and_outstanding_always_equal_each_cap(self) -> None:
        events = [activate(0), evaluate_base(0, 0), evaluate_base(0, 1), exercise(0, 0)]
        channels = run(events)["metrics"]["channels"]
        for channel_id, values in channels.items():
            with self.subTest(channel=channel_id):
                total = (
                    int(values["issued_atomic"])
                    + int(values["outstanding_atomic"])
                    + int(values["remaining_atomic"])
                )
                self.assertEqual(total, c.CHANNEL_CAPS[channel_id])


class FullSeatScheduleTest(unittest.TestCase):
    def test_one_seat_across_all_731_cycles_derives_the_per_seat_totals(self) -> None:
        recorded = vectors()
        events: list[dict] = [activate(3), activate(0, referrer=3)]
        for cycle in range(c.ISSUANCE_CYCLES_PER_SEAT):
            events.append(evaluate_base(0, cycle))
            events.append(evaluate_referral(0, cycle))
            events.append(exercise(0, cycle))
            events.append(exercise(0, cycle, "referral"))
        result = run(events)
        self.assertTrue(all(record["accepted"] for record in result["records"]))

        custody = result["final_state"]["typed_custody"]
        self.assertEqual(custody[seat(0)], recorded["per_seat_731.founder_operator"])
        self.assertEqual(custody[VENTURE], recorded["per_seat_731.venture_escrow"])
        self.assertEqual(custody[COMMUNITY], recorded["per_seat_731.community_grants_escrow"])
        self.assertEqual(custody[DEVELOPER], recorded["per_seat_731.developer_incentives_escrow"])
        self.assertEqual(
            custody[SYSTEM],
            recorded["per_seat_731.system_creator_issuance_royalty"],
        )
        self.assertEqual(custody[seat(3)], recorded["per_seat_731.referral"])

        base_total = sum(
            int(custody[key]) for key in (seat(0), VENTURE, COMMUNITY, DEVELOPER, SYSTEM)
        )
        self.assertEqual(base_total, int(recorded["per_seat_731.base_total"]))
        self.assertEqual(
            base_total + int(custody[seat(3)]),
            int(recorded["per_seat_731.founder_total"]),
        )
        self.assertEqual(
            result["metrics"]["issued_supply_atomic"],
            recorded["per_seat_731.founder_total"],
        )

    def test_cycle_731_is_outside_the_seat_schedule(self) -> None:
        events = [activate(0), evaluate_base(0, c.ISSUANCE_CYCLES_PER_SEAT)]
        self.assertEqual(run(events)["records"][-1]["result"], "CYCLE_RANGE")


class DeterminismTest(unittest.TestCase):
    def test_identical_inputs_produce_identical_digests(self) -> None:
        events = [
            activate(3),
            activate(0, referrer=3),
            evaluate_base(0, 0),
            evaluate_referral(0, 0),
            exercise(0, 0),
        ]
        first = run(events)
        second = run(events)
        for key in ("events_digest", "trace_digest", "state_digest", "result_digest"):
            with self.subTest(key=key):
                self.assertEqual(first[key], second[key])

    def test_event_order_changes_the_trace_digest(self) -> None:
        base = [activate(0), activate(1), evaluate_base(0, 0)]
        swapped = [activate(1), activate(0), evaluate_base(0, 0)]
        self.assertNotEqual(run(base)["trace_digest"], run(swapped)["trace_digest"])

    def test_journal_entries_use_unsigned_decimal_amounts(self) -> None:
        result = run([activate(0), evaluate_base(0, 0), exercise(0, 0)])
        for record in result["records"]:
            for item in record["journal"]:
                self.assertIn(item["direction"], {INCREASE, "decrease"})
                self.assertRegex(item["amount_atomic"], r"^[1-9][0-9]*$")


if __name__ == "__main__":
    unittest.main()
