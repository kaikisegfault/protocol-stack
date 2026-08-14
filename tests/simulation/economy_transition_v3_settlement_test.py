#!/usr/bin/env python3
"""The accumulation cap, the cycle assignment, the mint walk, and conservation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v3 import contract as c
from simulation.economy_transition_v3 import scenario, settlement, state, winners
from simulation.founder_economy_v3 import uptime as economy_uptime


class CapPredicateTest(unittest.TestCase):
    def test_the_boundary_window_accrues_and_the_next_does_not(self) -> None:
        mark = 1_000
        self.assertTrue(settlement.accrues_in_window(mark + 1, mark))
        self.assertTrue(
            settlement.accrues_in_window(mark + c.MINT_ACCUMULATION_CAP, mark)
        )
        self.assertFalse(
            settlement.accrues_in_window(mark + c.MINT_ACCUMULATION_CAP + 1, mark)
        )

    def test_exactly_thirty_windows_accrue_after_a_mark(self) -> None:
        mark = 5_000
        accruing = [
            offset
            for offset in range(1, 3 * c.MINT_ACCUMULATION_CAP)
            if settlement.accrues_in_window(mark + offset, mark)
        ]
        self.assertEqual(len(accruing), c.MINT_ACCUMULATION_CAP)
        self.assertEqual(accruing, list(range(1, c.MINT_ACCUMULATION_CAP + 1)))

    def test_the_cap_is_thirty_windows_of_the_accepted_grid(self) -> None:
        self.assertEqual(c.MINT_ACCUMULATION_CAP, 30)
        self.assertEqual(
            c.MINT_ACCUMULATION_CAP * c.CYCLE_BLOCKS * 3, 30 * 24 * 3_600
        )

    def test_a_negative_mark_is_refused_rather_than_clamped(self) -> None:
        with self.assertRaises(settlement.InvalidSettlement):
            settlement.walk_range(-1, 100)
        with self.assertRaises(settlement.InvalidSettlement):
            settlement.accrues_in_window(-1, 0)


class LastAssignedWindowTest(unittest.TestCase):
    def test_a_window_is_assigned_two_windows_after_it_closes(self) -> None:
        self.assertIsNone(settlement.last_assigned_window(0))
        self.assertIsNone(settlement.last_assigned_window(c.CYCLE_BLOCKS))
        self.assertEqual(settlement.last_assigned_window(2 * c.CYCLE_BLOCKS), 0)
        self.assertEqual(
            settlement.last_assigned_window(scenario.ASSIGNMENT_HEIGHT),
            scenario.OUTAGE_WINDOW,
        )

    def test_the_lag_is_the_dispute_window_the_measurement_fixes(self) -> None:
        self.assertEqual(c.ASSIGNMENT_LAG_WINDOWS, 2)


class WalkBoundTest(unittest.TestCase):
    """The property the window form of the cap exists to give."""

    def test_the_walk_never_exceeds_the_cap_however_long_a_founder_waits(self) -> None:
        horizon = 100_000
        for behind in (0, 1, 29, 30, 31, 365, 3_650, 100_000):
            with self.subTest(behind):
                self.assertLessEqual(
                    settlement.walk_length(horizon - behind, horizon),
                    c.MINT_ACCUMULATION_CAP,
                )

    def test_a_current_seat_walks_only_what_accumulated(self) -> None:
        horizon = 100_000
        for behind in range(0, c.MINT_ACCUMULATION_CAP + 1):
            with self.subTest(behind):
                self.assertEqual(
                    settlement.walk_length(horizon - behind, horizon), behind
                )

    def test_a_mark_at_the_last_assigned_window_has_no_walk(self) -> None:
        self.assertIsNone(settlement.walk_range(201, 201))
        self.assertEqual(settlement.walk_length(201, 201), 0)

    def test_nothing_is_walked_before_the_chain_has_assigned_anything(self) -> None:
        self.assertIsNone(settlement.walk_range(0, None))

    def test_the_bound_is_exact_rather_than_conservative(self) -> None:
        """No window outside the walk can carry a bit for the seat.

        The mark changes only at a mint and a mint sets it to the last assigned
        window, so every window in `(mark, last]` was assigned while the mark
        held its current value — and the assignment applied the same predicate
        against that same mark.
        """
        mark = 1_000
        horizon = mark + 500
        first, last = settlement.walk_range(mark, horizon)
        for window in range(first, last + 1):
            self.assertTrue(settlement.accrues_in_window(window, mark))
        for window in range(last + 1, horizon + 1):
            self.assertFalse(settlement.accrues_in_window(window, mark))


class AssignmentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.seats = scenario.cycle_seats()
        self.assignment = settlement.derive_assignment(
            scenario.CYCLE_WINDOW, self.seats
        )

    def test_the_winner_set_is_the_next_highest_because_the_best_is_capped(
        self,
    ) -> None:
        """The discriminator between the two readings of the founder rule."""
        capped = [
            seat.seat_id
            for seat in self.seats
            if not settlement.accrues_in_window(
                scenario.CYCLE_WINDOW, seat.minted_through_window
            )
        ]
        self.assertEqual(capped, [11])
        best = max(seat.uptime_seconds for seat in self.seats)
        self.assertEqual(
            best, next(s.uptime_seconds for s in self.seats if s.seat_id == 11)
        )
        self.assertNotIn(11, self.assignment.winners)
        self.assertEqual(self.assignment.winners, (0, 4, 23))

    def test_the_uncapped_rule_would_give_a_different_winner(self) -> None:
        """The accepted economy model applies no cap, so it is the other reading."""
        record = {
            "entries": [
                {"seat_id": seat.seat_id, "uptime_seconds": seat.uptime_seconds}
                for seat in self.seats
            ]
        }
        self.assertEqual(economy_uptime.winner_seats(record), (11,))
        self.assertNotEqual(economy_uptime.winner_seats(record), self.assignment.winners)

    def test_every_winner_can_actually_collect(self) -> None:
        """The property excluding capped seats exists to preserve."""
        marks = {seat.seat_id: seat.minted_through_window for seat in self.seats}
        for seat_id in self.assignment.winners:
            with self.subTest(seat_id):
                self.assertTrue(
                    settlement.accrues_in_window(scenario.CYCLE_WINDOW, marks[seat_id])
                )

    def test_accruing_and_winning_are_independent(self) -> None:
        self.assertIn(23, self.assignment.winners)
        self.assertNotIn(23, self.assignment.accrued)
        self.assertIn(15, self.assignment.accrued)
        self.assertNotIn(15, self.assignment.winners)

    def test_a_seat_on_the_threshold_accrues(self) -> None:
        seat = next(s for s in self.seats if s.seat_id == 15)
        self.assertEqual(seat.uptime_seconds, scenario.THRESHOLD_UPTIME)
        self.assertTrue(economy_uptime.met_cycle(seat.uptime_seconds))
        self.assertIn(15, self.assignment.accrued)

    def test_a_failed_and_a_capped_seat_both_reallocate(self) -> None:
        self.assertEqual(self.assignment.reallocated_count, 2)
        self.assertNotIn(7, self.assignment.accrued)
        self.assertNotIn(11, self.assignment.accrued)

    def test_the_met_verdict_agrees_with_the_accepted_economy_model(self) -> None:
        for seat in self.seats:
            with self.subTest(seat.seat_id):
                self.assertEqual(
                    winners.met_cycle(seat.uptime_seconds),
                    economy_uptime.met_cycle(seat.uptime_seconds),
                )

    def test_a_cycle_no_seat_met_carries_the_whole_permission(self) -> None:
        outage = settlement.derive_assignment(
            scenario.OUTAGE_WINDOW, scenario.outage_seats()
        )
        self.assertEqual(outage.winners, ())
        self.assertEqual(outage.accrued, ())
        self.assertEqual(
            sum(outage.carry_per_channel.values()),
            outage.reallocated_count * c.BASE_PERMISSION_TOTAL,
        )

    def test_the_bitmaps_cover_seat_identifiers(self) -> None:
        _, value = settlement.assignment_entry(self.assignment)
        decoded = state.decode_cycle_assignment_value(value)
        self.assertEqual(decoded["bitmap_bits"], max(s.seat_id for s in self.seats) + 1)
        for seat_id in self.assignment.accrued:
            self.assertTrue(state.bit_is_set(decoded["accrued_bitmap"], seat_id))
        for seat_id in self.assignment.winners:
            self.assertTrue(state.bit_is_set(decoded["winner_bitmap"], seat_id))

    def test_a_duplicated_seat_is_refused(self) -> None:
        with self.assertRaises(settlement.InvalidSettlement):
            settlement.derive_assignment(1, self.seats + [self.seats[0]])


class SplitTest(unittest.TestCase):
    def test_every_leg_is_divided_and_the_split_conserves(self) -> None:
        for count in (1, 2, 3, 7, 13, 100, 99_999):
            with self.subTest(count):
                shares, carries = winners.split_permission(count)
                for channel, amount in c.BASE_PERMISSION_LEGS:
                    self.assertEqual(shares[channel] * count + carries[channel], amount)
                    self.assertLess(carries[channel], count)

    def test_an_empty_winner_set_carries_the_whole_permission(self) -> None:
        shares, carries = winners.split_permission(0)
        self.assertEqual(set(shares.values()), {0})
        self.assertEqual(sum(carries.values()), c.BASE_PERMISSION_TOTAL)

    def test_the_legs_are_the_founder_directed_ones(self) -> None:
        self.assertEqual(c.BASE_PERMISSION_TOTAL, 57_430_000_000)
        self.assertEqual(
            dict(c.BASE_PERMISSION_LEGS)[c.FOUNDER_OPERATOR_CHANNEL], 34_200_000_000
        )

    def test_an_uncanonical_winner_list_is_refused(self) -> None:
        for candidate in ((4, 0), (0, 0), (c.FOUNDER_SEAT_CAPACITY,)):
            with self.subTest(candidate):
                with self.assertRaises(winners.InvalidWinnerSet):
                    winners.require_canonical(candidate)


class MintWalkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.last = settlement.last_assigned_window(scenario.ASSIGNMENT_HEIGHT)
        self.records = scenario.assignment_records()
        self.marks = {
            seat.seat_id: seat.minted_through_window for seat in scenario.cycle_seats()
        }

    def test_a_seat_collects_its_own_cycle_and_its_winner_share(self) -> None:
        collection = settlement.collect(0, self.marks[0], self.last, self.records)
        legs = dict(c.BASE_PERMISSION_LEGS)
        assignment = scenario.assignments()[scenario.CYCLE_WINDOW]
        for channel, amount in legs.items():
            expected = amount + assignment.reallocated_count * (
                amount // assignment.winner_count
            )
            self.assertEqual(collection.per_channel[channel], expected)

    def test_a_seat_past_its_span_collects_only_its_winner_share(self) -> None:
        collection = settlement.collect(23, self.marks[23], self.last, self.records)
        self.assertEqual(collection.accrued_windows, ())
        self.assertEqual(collection.won_windows, (scenario.CYCLE_WINDOW,))
        self.assertGreater(collection.total_atomic, 0)

    def test_the_operator_leg_credits_an_account_and_the_rest_typed_custody(
        self,
    ) -> None:
        collection = settlement.collect(0, self.marks[0], self.last, self.records)
        self.assertEqual(
            collection.operator_atomic,
            collection.per_channel[c.FOUNDER_OPERATOR_CHANNEL],
        )
        self.assertEqual(
            set(collection.custody_atomic), set(c.SINGLETON_BENEFICIARY_KINDS)
        )
        self.assertEqual(
            collection.operator_atomic + sum(collection.custody_atomic.values()),
            collection.total_atomic,
        )

    def test_a_second_mint_finds_nothing(self) -> None:
        second = settlement.collect(0, self.last, self.last, self.records)
        self.assertEqual(second.total_atomic, 0)
        self.assertEqual(second.windows_walked, 0)
        self.assertIsNone(settlement.walk_range(self.last, self.last))

    def test_a_capped_seat_walks_the_cap_and_collects_nothing(self) -> None:
        """Which is why such a mint must succeed rather than be refused.

        Its walk lies entirely inside the thirty windows after its own stale
        mark, none of which hold a record, and the cycle it lost is outside that
        range. Refusing the mint would leave it permanently past the cap.
        """
        collection = settlement.collect(11, self.marks[11], self.last, self.records)
        self.assertEqual(collection.total_atomic, 0)
        self.assertEqual(collection.windows_walked, c.MINT_ACCUMULATION_CAP)
        first, last = settlement.walk_range(self.marks[11], self.last)
        self.assertNotIn(scenario.CYCLE_WINDOW, range(first, last + 1))

    def test_a_seat_that_failed_every_cycle_collects_nothing(self) -> None:
        collection = settlement.collect(7, self.marks[7], self.last, self.records)
        self.assertEqual(collection.total_atomic, 0)
        self.assertEqual(collection.accrued_windows, ())
        self.assertEqual(collection.won_windows, ())

    def test_a_window_with_no_record_contributes_nothing(self) -> None:
        collection = settlement.collect(0, self.marks[0], self.last, {})
        self.assertEqual(collection.total_atomic, 0)
        self.assertEqual(collection.windows_walked, 2)


class ReferralAccrualTest(unittest.TestCase):
    def setUp(self) -> None:
        self.seats = scenario.cycle_seats()
        self.in_span = [seat for seat in self.seats if seat.in_span]

    def test_the_channel_is_consumed_exactly(self) -> None:
        accruals, pool = settlement.referral_accrual(
            scenario.CYCLE_WINDOW, self.seats, scenario.REFERRER_MARKS
        )
        self.assertEqual(
            sum(accruals.values()) + pool,
            len(self.in_span) * c.REFERRAL_LEG_ATOMIC,
        )

    def test_an_unreferred_seat_and_a_capped_referrer_share_a_destination(self) -> None:
        _, pool = settlement.referral_accrual(
            scenario.CYCLE_WINDOW, self.seats, scenario.REFERRER_MARKS
        )
        unreferred = sum(1 for seat in self.in_span if seat.referrer_account_id is None)
        capped = sum(
            1
            for seat in self.in_span
            if seat.referrer_account_id is not None
            and not settlement.accrues_in_window(
                scenario.CYCLE_WINDOW,
                scenario.REFERRER_MARKS[seat.referrer_account_id],
            )
        )
        self.assertEqual(unreferred, 2)
        self.assertEqual(capped, 1)
        self.assertEqual(pool, (unreferred + capped) * c.REFERRAL_LEG_ATOMIC)

    def test_a_first_accrual_is_never_capped(self) -> None:
        """The entry is created lazily, so a referrer is paid before it is timed."""
        accruals, pool = settlement.referral_accrual(
            scenario.CYCLE_WINDOW, self.seats, {}
        )
        referred = sum(
            1 for seat in self.in_span if seat.referrer_account_id is not None
        )
        self.assertEqual(sum(accruals.values()), referred * c.REFERRAL_LEG_ATOMIC)
        self.assertEqual(
            pool, (len(self.in_span) - referred) * c.REFERRAL_LEG_ATOMIC
        )

    def test_a_seat_outside_its_span_accrues_no_referral(self) -> None:
        accruals, pool = settlement.referral_accrual(
            scenario.CYCLE_WINDOW, self.seats, scenario.REFERRER_MARKS
        )
        self.assertEqual(
            sum(accruals.values()) + pool,
            (len(self.seats) - 1) * c.REFERRAL_LEG_ATOMIC,
        )


class ConservationTest(unittest.TestCase):
    """The identity a settlement defect would break before anything else."""

    def setUp(self) -> None:
        self.last = settlement.last_assigned_window(scenario.ASSIGNMENT_HEIGHT)
        self.records = scenario.assignment_records()
        self.assignments = scenario.assignments()
        self.marks = {
            seat.seat_id: seat.minted_through_window for seat in scenario.cycle_seats()
        }

    def ledger(self) -> tuple[dict[int, int], dict[int, int], dict[int, int], int]:
        carry = {channel: 0 for channel, _ in c.BASE_PERMISSION_LEGS}
        outstanding = dict(carry)
        issued = dict(carry)
        for assignment in self.assignments.values():
            for channel, amount in settlement.outstanding_delta(assignment).items():
                outstanding[channel] += amount
            for channel, amount in assignment.carry_per_channel.items():
                carry[channel] += amount
        for seat_id in self.marks:
            collection = settlement.collect(
                seat_id, self.marks[seat_id], self.last, self.records
            )
            for channel, amount in collection.per_channel.items():
                issued[channel] += amount
                outstanding[channel] -= amount
        assigned = sum(a.assigned_permissions for a in self.assignments.values())
        return issued, outstanding, carry, assigned

    def test_the_carry_identity_holds_per_channel(self) -> None:
        issued, outstanding, carry, assigned = self.ledger()
        for channel, leg in c.BASE_PERMISSION_LEGS:
            with self.subTest(channel):
                self.assertEqual(
                    issued[channel] + outstanding[channel] + carry[channel],
                    assigned * leg,
                )

    def test_outstanding_falls_to_zero_once_every_seat_mints(self) -> None:
        _, outstanding, _, _ = self.ledger()
        self.assertEqual(set(outstanding.values()), {0})

    def test_the_carried_remainder_is_taken_out_of_outstanding(self) -> None:
        """Adding it beside outstanding would count the same value twice."""
        assignment = self.assignments[scenario.CYCLE_WINDOW]
        delta = settlement.outstanding_delta(assignment)
        for channel, leg in c.BASE_PERMISSION_LEGS:
            with self.subTest(channel):
                self.assertEqual(
                    delta[channel]
                    + assignment.carry_per_channel[channel],
                    assignment.assigned_permissions * leg,
                )

    def test_a_defect_that_overpaid_a_winner_would_break_the_identity(self) -> None:
        """The check has teeth: an inflated share fails it."""
        issued, outstanding, carry, assigned = self.ledger()
        inflated = dict(issued)
        inflated[c.FOUNDER_OPERATOR_CHANNEL] += 1
        self.assertNotEqual(
            inflated[c.FOUNDER_OPERATOR_CHANNEL]
            + outstanding[c.FOUNDER_OPERATOR_CHANNEL]
            + carry[c.FOUNDER_OPERATOR_CHANNEL],
            assigned * dict(c.BASE_PERMISSION_LEGS)[c.FOUNDER_OPERATOR_CHANNEL],
        )


if __name__ == "__main__":
    unittest.main()
