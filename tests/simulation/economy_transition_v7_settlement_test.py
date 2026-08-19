#!/usr/bin/env python3
"""The recovery pool's arithmetic, the two seat sets, and both identities.

The vector file records one schedule and its figures. This module covers what a
recorded schedule cannot reach: the branches it does not enter, the orders it
does not distinguish, and the properties that must hold over every schedule
rather than over one.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v3.settlement import SeatCycle
from simulation.economy_transition_v6 import contract as v6
from simulation.economy_transition_v7 import contract as c
from simulation.economy_transition_v7 import settlement as t
from simulation.economy_transition_v7.conservation import (
    CycleSeat,
    SettlementFailure,
    SettlementLedger,
)
from simulation.economy_transition_v7.state import decode_cycle_assignment_value

LEGS = dict(c.BASE_PERMISSION_LEGS)
MET = 72_000
BEST = 79_200
FAILED = 3_600


def seats(*entries: tuple[int, int, bool]) -> list[SeatCycle]:
    return [
        SeatCycle(
            seat_id=seat,
            uptime_seconds=uptime,
            in_span=in_span,
            minted_through_window=0,
        )
        for seat, uptime, in_span in entries
    ]


def cycle_seats(*entries: tuple[int, int, bool]) -> list[CycleSeat]:
    return [
        CycleSeat(seat_id=seat, uptime_seconds=uptime, in_span=in_span)
        for seat, uptime, in_span in entries
    ]


class ZeroWinnerTest(unittest.TestCase):
    """ADR 0049: a zero-winner cycle contributes its whole base permission."""

    def test_every_leg_moves_not_only_the_operator_leg(self) -> None:
        derived = t.derive_assignment(
            3, seats((0, FAILED, True), (1, FAILED, True)), t.empty_pool()
        )
        self.assertEqual(derived.winners, ())
        self.assertEqual(derived.reallocated_count, 2)
        for channel, leg in c.BASE_PERMISSION_LEGS:
            self.assertEqual(derived.pool_after[channel], 2 * leg)

    def test_the_whole_permission_is_accounted_for(self) -> None:
        derived = t.derive_assignment(
            3, seats((0, FAILED, True)), t.empty_pool()
        )
        self.assertEqual(sum(derived.pool_after.values()), c.BASE_PERMISSION_TOTAL)

    def test_nothing_is_absorbed_and_the_pool_is_untouched(self) -> None:
        before = {channel: 41 for channel in c.RECOVERY_POOL_LEGS}
        derived = t.derive_assignment(3, seats((0, FAILED, True)), before)
        self.assertEqual(derived.pool_absorbed, {ch: 0 for ch in c.RECOVERY_POOL_LEGS})
        for channel, leg in c.BASE_PERMISSION_LEGS:
            self.assertEqual(derived.pool_after[channel], 41 + leg)

    def test_a_cycle_with_no_in_scope_seat_at_all_changes_nothing(self) -> None:
        before = {channel: 7 for channel in c.RECOVERY_POOL_LEGS}
        derived = t.derive_assignment(3, [], before)
        self.assertEqual(derived.winners, ())
        self.assertEqual(derived.assigned_permissions, 0)
        self.assertEqual(derived.pool_after, before)
        self.assertEqual(derived.bitmap_bits, 0)


class AbsorptionOrderTest(unittest.TestCase):
    """Step 6 reads the pool before step 7 writes it."""

    def test_a_cycle_does_not_pay_itself_its_own_dust(self) -> None:
        # Three winners and one reallocating seat leaves dust on the leg that
        # does not divide by three. That dust must not be inside what the same
        # cycle absorbed.
        derived = t.derive_assignment(
            3,
            seats(
                (0, MET, True),
                (1, MET, True),
                (2, MET, True),
                (3, FAILED, True),
            ),
            t.empty_pool(),
        )
        self.assertEqual(derived.winner_count, 3)
        self.assertEqual(derived.reallocated_count, 1)
        self.assertEqual(derived.pool_absorbed, {ch: 0 for ch in c.RECOVERY_POOL_LEGS})
        self.assertEqual(derived.dust_per_channel[4], 1)
        self.assertEqual(derived.pool_after[4], 1)

    def test_the_residual_of_the_absorbed_pool_returns_to_the_pool(self) -> None:
        before = {channel: 5 for channel in c.RECOVERY_POOL_LEGS}
        derived = t.derive_assignment(
            3, seats((0, MET, True), (1, MET, True), (2, MET, True)), before
        )
        self.assertEqual(derived.winner_count, 3)
        for channel in c.RECOVERY_POOL_LEGS:
            self.assertEqual(derived.pool_share_per_channel[channel], 1)
            self.assertEqual(derived.pool_residual_per_channel[channel], 2)
            self.assertEqual(derived.pool_after[channel], 2)

    def test_an_absorbed_pool_below_the_winner_count_is_returned_whole(self) -> None:
        before = {channel: 2 for channel in c.RECOVERY_POOL_LEGS}
        derived = t.derive_assignment(
            3,
            seats((0, MET, True), (1, MET, True), (2, MET, True)),
            before,
        )
        for channel in c.RECOVERY_POOL_LEGS:
            self.assertEqual(derived.pool_share_per_channel[channel], 0)
            self.assertEqual(derived.pool_after[channel], 2)

    def test_no_unit_is_created_or_destroyed_by_absorption(self) -> None:
        before = {channel: 1_000 + channel for channel in c.RECOVERY_POOL_LEGS}
        derived = t.derive_assignment(
            3,
            seats((0, MET, True), (1, MET, True), (2, MET, True), (3, FAILED, True)),
            before,
        )
        for channel in c.RECOVERY_POOL_LEGS:
            paid = derived.winner_count * derived.pool_share_per_channel[channel]
            self.assertEqual(
                before[channel],
                paid + derived.pool_residual_per_channel[channel],
            )


class TriggerTest(unittest.TestCase):
    """Having any winner is the trigger, not having reallocated anything."""

    def test_a_cycle_with_winners_and_no_reallocation_still_absorbs(self) -> None:
        before = {channel: 100 for channel in c.RECOVERY_POOL_LEGS}
        derived = t.derive_assignment(
            3, seats((0, MET, True), (1, MET, True)), before
        )
        self.assertEqual(derived.reallocated_count, 0)
        self.assertEqual(derived.pool_absorbed, before)
        for channel in c.RECOVERY_POOL_LEGS:
            self.assertEqual(derived.pool_share_per_channel[channel], 50)

    def test_a_cycle_with_no_contributing_seat_still_absorbs(self) -> None:
        before = {channel: 90 for channel in c.RECOVERY_POOL_LEGS}
        derived = t.derive_assignment(
            3, seats((8, MET, False), (9, MET, False), (10, MET, False)), before
        )
        self.assertEqual(derived.assigned_permissions, 0)
        self.assertEqual(derived.winners, (8, 9, 10))
        self.assertEqual(derived.pool_absorbed, before)
        for channel in c.RECOVERY_POOL_LEGS:
            self.assertEqual(derived.pool_share_per_channel[channel], 30)
            self.assertEqual(derived.pool_after[channel], 0)


class TwoSetsTest(unittest.TestCase):
    """The eligible set is not narrowed to the contributing set."""

    def test_a_seat_past_its_span_can_win(self) -> None:
        derived = t.derive_assignment(
            3, seats((0, MET, True), (9, BEST, False)), t.empty_pool()
        )
        self.assertEqual(derived.winners, (9,))
        self.assertEqual(derived.accrued, (0,))
        self.assertEqual(derived.assigned_permissions, 1)

    def test_a_seat_past_its_span_never_contributes(self) -> None:
        derived = t.derive_assignment(
            3, seats((9, MET, False), (10, MET, False)), t.empty_pool()
        )
        self.assertEqual(derived.assigned_permissions, 0)
        self.assertEqual(derived.accrued, ())
        for channel in c.RECOVERY_POOL_LEGS:
            self.assertEqual(t.outstanding_delta(derived)[channel], 0)

    def test_the_winner_bitmap_carries_a_seat_the_accrued_bitmap_does_not(self) -> None:
        derived = t.derive_assignment(
            3, seats((0, MET, True), (9, BEST, False)), t.empty_pool()
        )
        _key, value = t.assignment_entry(derived)
        decoded = decode_cycle_assignment_value(value)
        from simulation.economy_transition_v7.state import bit_is_set

        self.assertTrue(bit_is_set(decoded["winner_bitmap"], 9))
        self.assertFalse(bit_is_set(decoded["accrued_bitmap"], 9))
        self.assertTrue(bit_is_set(decoded["accrued_bitmap"], 0))

    def test_the_pool_would_strand_if_the_winner_set_were_span_filtered(self) -> None:
        """The regression ADR 0054 decision 5 exists to prevent."""
        population = seats((9, MET, False), (10, MET, False))
        derived = t.derive_assignment(
            3, population, {channel: 55 for channel in c.RECOVERY_POOL_LEGS}
        )
        self.assertNotEqual(derived.winners, ())
        narrowed = [seat for seat in population if seat.in_span]
        stranded = t.derive_assignment(
            3, narrowed, {channel: 55 for channel in c.RECOVERY_POOL_LEGS}
        )
        self.assertEqual(stranded.winners, ())
        self.assertEqual(stranded.pool_after[0], 55)


class CollectionTest(unittest.TestCase):
    def test_a_winner_collects_its_pool_share(self) -> None:
        ledger = SettlementLedger()
        ledger.assign(1, cycle_seats((0, FAILED, True), (1, FAILED, True)))
        ledger.assign(2, cycle_seats((0, BEST, True), (1, MET, True)))
        collection = ledger.mint(0, 2)
        for channel, leg in c.BASE_PERMISSION_LEGS:
            # window 2: its own accrual, plus the whole two-permission pool.
            self.assertEqual(collection.per_channel[channel], leg + 2 * leg)

    def test_a_seat_past_its_span_collects_without_ever_accruing(self) -> None:
        ledger = SettlementLedger()
        ledger.assign(1, cycle_seats((0, FAILED, True), (1, FAILED, True)))
        ledger.assign(2, cycle_seats((0, MET, True), (9, BEST, False)))
        collection = ledger.mint(9, 2)
        self.assertEqual(collection.accrued_windows, ())
        self.assertEqual(collection.won_windows, (2,))
        self.assertEqual(collection.total_atomic, 2 * c.BASE_PERMISSION_TOTAL)

    def test_a_window_with_no_record_contributes_nothing(self) -> None:
        ledger = SettlementLedger()
        ledger.assign(4, cycle_seats((0, MET, True)))
        collection = ledger.mint(0, 4)
        self.assertEqual(collection.windows_walked, 4)
        self.assertEqual(collection.accrued_windows, (4,))

    def test_an_empty_walk_is_refused(self) -> None:
        ledger = SettlementLedger()
        with self.assertRaises(SettlementFailure):
            ledger.mint(0, None)


class ConservationTest(unittest.TestCase):
    def test_both_identities_hold_over_a_mixed_schedule(self) -> None:
        ledger = SettlementLedger()
        schedule = [
            (1, cycle_seats((0, FAILED, True), (1, FAILED, True), (2, FAILED, True))),
            (2, cycle_seats((0, MET, True), (1, MET, True), (2, MET, True))),
            (3, cycle_seats((0, BEST, True), (1, MET, True), (2, FAILED, True))),
            (4, cycle_seats((0, MET, True), (1, MET, True), (9, MET, False))),
            (5, cycle_seats((9, MET, False), (10, MET, False))),
        ]
        for window, population in schedule:
            ledger.assign(window, population)
            self.assertEqual(ledger.identity_failures(), [])
        for seat in (0, 1, 9):
            ledger.mint(seat, 5)
            self.assertEqual(ledger.identity_failures(), [])

    def test_every_assigned_unit_is_issued_claimable_or_pooled(self) -> None:
        ledger = SettlementLedger()
        ledger.assign(1, cycle_seats((0, FAILED, True), (1, FAILED, True)))
        ledger.assign(2, cycle_seats((0, MET, True), (1, MET, True), (2, MET, True)))
        ledger.mint(0, 2)
        owed = ledger.claimable()
        for channel in c.RECOVERY_POOL_LEGS:
            self.assertEqual(
                ledger.channel_issued[channel] + owed[channel] + ledger.pool[channel],
                ledger.assigned_total(channel),
            )

    def test_the_identity_has_no_third_term(self) -> None:
        """Version six subtracted the carry here; version seven does not."""
        ledger = SettlementLedger()
        ledger.assign(1, cycle_seats((0, FAILED, True), (1, FAILED, True)))
        for channel, leg in c.BASE_PERMISSION_LEGS:
            self.assertEqual(ledger.channel_outstanding[channel], 2 * leg)
            self.assertEqual(ledger.pool[channel], 2 * leg)

    def test_a_lost_claim_fails_the_backing_identity(self) -> None:
        ledger = SettlementLedger()
        ledger.assign(1, cycle_seats((0, MET, True), (1, MET, True)))
        self.assertEqual(ledger.identity_failures(), [])
        ledger.pool[0] += 1
        failures = ledger.identity_failures()
        self.assertTrue(any("backing identity" in failure for failure in failures))

    def test_a_created_unit_fails_the_channel_identity(self) -> None:
        ledger = SettlementLedger()
        ledger.assign(1, cycle_seats((0, MET, True)))
        ledger.channel_outstanding[1] += 1
        failures = ledger.identity_failures()
        self.assertTrue(any("channel identity" in failure for failure in failures))

    def test_assigning_a_window_twice_is_refused(self) -> None:
        ledger = SettlementLedger()
        ledger.assign(1, cycle_seats((0, MET, True)))
        with self.assertRaises(SettlementFailure):
            ledger.assign(1, cycle_seats((0, MET, True)))


class AccumulationCapTest(unittest.TestCase):
    def test_a_seat_over_the_cap_neither_accrues_nor_wins(self) -> None:
        over = c.MINT_ACCUMULATION_CAP + 1
        derived = t.derive_assignment(
            over,
            [
                SeatCycle(0, BEST, True, minted_through_window=0),
                SeatCycle(1, MET, True, minted_through_window=over - 1),
            ],
            t.empty_pool(),
        )
        self.assertEqual(derived.winners, (1,))
        self.assertEqual(derived.accrued, (1,))
        self.assertEqual(derived.reallocated_count, 1)

    def test_a_cycle_where_every_seat_is_over_the_cap_has_no_winner(self) -> None:
        over = c.MINT_ACCUMULATION_CAP + 1
        derived = t.derive_assignment(
            over,
            [
                SeatCycle(0, BEST, True, minted_through_window=0),
                SeatCycle(1, MET, True, minted_through_window=0),
            ],
            t.empty_pool(),
        )
        self.assertEqual(derived.winners, ())
        self.assertEqual(sum(derived.pool_after.values()), 2 * c.BASE_PERMISSION_TOTAL)

    def test_no_bit_exists_outside_the_window_a_mint_reaches(self) -> None:
        """What makes `claimable` exact rather than a bound."""
        ledger = SettlementLedger()
        for window in range(1, c.MINT_ACCUMULATION_CAP + 2):
            ledger.assign(window, cycle_seats((0, MET, True), (1, MET, True)))
            if window == 5:
                ledger.mint(1, window)
        last = c.MINT_ACCUMULATION_CAP + 1
        from simulation.economy_transition_v7.state import bit_is_set

        record = decode_cycle_assignment_value(ledger.assignments[last])
        self.assertFalse(bit_is_set(record["accrued_bitmap"], 0))
        self.assertFalse(bit_is_set(record["winner_bitmap"], 0))
        first, walked = t.walk_range(0, last)
        self.assertEqual((first, walked), (1, c.MINT_ACCUMULATION_CAP))
        self.assertEqual(ledger.identity_failures(), [])
        ledger.mint(0, last)
        self.assertEqual(ledger.identity_failures(), [])


class CarriedSettlementTest(unittest.TestCase):
    """The half version seven does not change is version three's, imported."""

    def test_the_walk_range_and_cap_predicate_are_version_three_s(self) -> None:
        from simulation.economy_transition_v3 import settlement as v3

        self.assertIs(t.walk_range, v3.walk_range)
        self.assertIs(t.accrues_in_window, v3.accrues_in_window)
        self.assertIs(t.last_assigned_window, v3.last_assigned_window)
        self.assertIs(t.referral_accrual, v3.referral_accrual)

    def test_the_winner_rule_and_tie_rule_are_version_three_s(self) -> None:
        from simulation.economy_transition_v3 import winners as v3

        self.assertIs(t.derive_winner_set, v3.derive_winner_set)
        self.assertIs(t.split_permission, v3.split_permission)
        self.assertIs(t.met_cycle, v3.met_cycle)

    def test_the_base_permission_legs_are_version_six_s(self) -> None:
        self.assertEqual(c.BASE_PERMISSION_LEGS, v6.BASE_PERMISSION_LEGS)
        self.assertEqual(sum(LEGS.values()), c.BASE_PERMISSION_TOTAL)


if __name__ == "__main__":
    unittest.main()
