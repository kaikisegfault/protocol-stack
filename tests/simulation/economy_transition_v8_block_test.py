#!/usr/bin/env python3
"""The four ordered steps, the six added invariants, and the one refused habit.

Version eight is the first version in this repository whose block transition does
something at *every* height whether or not a transaction was offered. That has
one consequence a version-seven reader will not expect and which this file exists
to pin: **`Ledger.advance_to` is no longer a valid shorthand once any seat is
activated**, because a run of transaction-free blocks issues challenges, expires
them, and clears slot bits.

The rest is the block's own contract: the prologue derives its schedule from
state and takes nothing from a caller, the issue step writes one entry per
selected in-scope seat against the previous state root, the expiry step runs
after the transactions, and a block that would write a height twice is rejected
whole with the pre-block state restored exactly.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from simulation.economy_transition_v8 import block as b
from simulation.economy_transition_v8 import contract as c
from simulation.economy_transition_v8 import trace
from simulation.economy_transition_v8.ledger import ConservationFailure, Ledger, Seat
from simulation.economy_transition_v8.schedule import derive_schedule
from simulation.economy_transition_v8.slots import in_scope, is_selected
from simulation.economy_transition_v8.state import (
    all_slots_credited,
    open_challenge_key,
    open_challenge_value,
    seat_window_key,
    seat_window_value,
    state_root_frame,
    state_root_from_frame,
)


def _ledger() -> Ledger:
    return Ledger.from_genesis(trace.genesis())


class AdvanceToTest(unittest.TestCase):
    """The shorthand is exact while no seat is in scope and refused after."""

    def test_it_is_allowed_before_any_activation(self) -> None:
        ledger = _ledger()
        ledger.seats[0] = Seat(hub_identity_hash=bytes(32), referrer_hub_identity=None)
        self.assertEqual(ledger.advance_to(100), 100)
        self.assertEqual(ledger.height, 100)

    def test_it_is_refused_once_a_seat_is_activated(self) -> None:
        ledger = _ledger()
        ledger.seats[0] = Seat(
            hub_identity_hash=bytes(32),
            referrer_hub_identity=None,
            is_activated=True,
            activation_height=10,
        )
        with self.assertRaises(ConservationFailure):
            ledger.advance_to(100)


class StateRootFrameTest(unittest.TestCase):
    """The fast path is the same preimage, not a second one that agrees."""

    def test_the_frame_reproduces_the_root_at_every_height(self) -> None:
        ledger = _ledger()
        frame = state_root_frame(
            ledger.chain_id, ledger.supply_limit, ledger.total_supply,
            ledger.fee_pool, ledger.accounts(), ledger.economy_entries(),
        )
        for height in (0, 1, 19, c.CYCLE_BLOCKS, 10 ** 12):
            ledger.height = height
            self.assertEqual(state_root_from_frame(frame, height), ledger.state_root())

    def test_a_written_entry_changes_the_root_the_frame_no_longer_matches(self) -> None:
        ledger = _ledger()
        frame = state_root_frame(
            ledger.chain_id, ledger.supply_limit, ledger.total_supply,
            ledger.fee_pool, ledger.accounts(), ledger.economy_entries(),
        )
        ledger.uptime[open_challenge_key(5, 0)] = open_challenge_value(0)
        self.assertNotEqual(state_root_from_frame(frame, 0), ledger.state_root())


class ScheduleTest(unittest.TestCase):
    """Record completeness is structural, and the mark is not derivable here."""

    def test_an_absent_record_reads_as_a_fully_credited_seat(self) -> None:
        measured = derive_schedule({0: 10}, 1, {})
        self.assertEqual(len(measured), 1)
        self.assertEqual(
            measured[0].uptime_seconds, c.SLOTS_PER_WINDOW * c.SLOT_SECONDS
        )

    def test_a_seat_out_of_scope_is_absent_rather_than_zero(self) -> None:
        # Activated inside window 1, so window 1 is not its.
        self.assertEqual(derive_schedule({0: c.CYCLE_BLOCKS + 10}, 1, {}), [])

    def test_a_seat_past_its_own_span_is_present_and_out_of_span(self) -> None:
        window = 1 + c.ISSUANCE_CYCLES_PER_SEAT
        measured = derive_schedule({0: 10}, window, {})
        self.assertEqual(len(measured), 1)
        self.assertFalse(measured[0].in_span)

    def test_a_measured_seat_carries_three_fields_and_not_five(self) -> None:
        measured = derive_schedule({0: 10}, 1, {})[0]
        self.assertEqual(
            set(vars(measured)), {"seat_id", "uptime_seconds", "in_span"}
        )

    def test_a_cleared_bit_reduces_the_derived_uptime(self) -> None:
        economy = {
            seat_window_key(1, 0): seat_window_value(all_slots_credited() & ~1, 0)
        }
        measured = derive_schedule({0: 10}, 1, economy)
        self.assertEqual(
            measured[0].uptime_seconds, (c.SLOTS_PER_WINDOW - 1) * c.SLOT_SECONDS
        )


class IssueStepTest(unittest.TestCase):
    """One entry per selected in-scope seat, and a height is written once."""

    def setUp(self) -> None:
        self.ledger = _ledger()
        self.ledger.seats[0] = Seat(
            hub_identity_hash=bytes(32),
            referrer_hub_identity=None,
            is_activated=True,
            activation_height=10,
        )
        self.ledger.height = c.CYCLE_BLOCKS + 100

    def test_it_issues_exactly_the_seats_selection_names(self) -> None:
        root = self.ledger.state_root()
        beacon = bytes.fromhex(root)
        expected = [
            seat
            for seat in self.ledger.seats
            if in_scope(10, self.ledger.height // c.CYCLE_BLOCKS)
            and is_selected(beacon, seat, self.ledger.height)
        ]
        self.assertEqual(b._issue_step(self.ledger, root), expected)

    def test_an_unactivated_seat_is_never_issued_a_challenge(self) -> None:
        self.ledger.seats[1] = Seat(
            hub_identity_hash=bytes(32), referrer_hub_identity=None
        )
        self.assertNotIn(1, b._issue_step(self.ledger, self.ledger.state_root()))

    def test_writing_a_height_twice_rejects_the_block(self) -> None:
        # Force the collision: an entry already stands at this height for a seat
        # selection is about to name.
        root = self.ledger.state_root()
        beacon = bytes.fromhex(root)
        for offset in range(c.CHALLENGE_PERIOD_BLOCKS * 4):
            height = self.ledger.height + offset
            if is_selected(beacon, 0, height):
                self.ledger.height = height
                break
        else:  # pragma: no cover - a beacon that selects nobody in four periods
            self.skipTest("no selected height near this beacon")
        self.ledger.uptime[open_challenge_key(self.ledger.height, 0)] = (
            open_challenge_value(0)
        )
        with self.assertRaises(b.InvalidBlock):
            b._issue_step(self.ledger, root)


class ExpiryStepTest(unittest.TestCase):
    """The slot-close sweep, made incremental: one bit per lost slot."""

    def setUp(self) -> None:
        self.ledger = _ledger()
        self.ledger.seats[0] = Seat(
            hub_identity_hash=bytes(32),
            referrer_hub_identity=None,
            is_activated=True,
            activation_height=10,
        )

    def _expire_at(self, challenge_height: int, state: int) -> None:
        self.ledger.uptime[open_challenge_key(challenge_height, 0)] = (
            open_challenge_value(state)
        )
        self.ledger.height = challenge_height + c.RESPONSE_DEADLINE_BLOCKS
        b._expiry_step(self.ledger)

    def test_an_answered_challenge_is_deleted_and_writes_nothing(self) -> None:
        self._expire_at(c.CYCLE_BLOCKS + 40, 1)
        self.assertEqual(self.ledger.uptime, {})

    def test_an_outstanding_challenge_clears_its_own_slot(self) -> None:
        self._expire_at(c.CYCLE_BLOCKS + 40, 0)
        self.assertEqual(self.ledger.window_records(), {(1, 0): (0xFFFFFE, 0)})

    def test_two_lost_challenges_in_one_slot_cost_one_slot(self) -> None:
        self._expire_at(c.CYCLE_BLOCKS + 40, 0)
        self._expire_at(c.CYCLE_BLOCKS + 60, 0)
        self.assertEqual(self.ledger.window_records(), {(1, 0): (0xFFFFFE, 0)})

    def test_nothing_expires_before_the_deadline_can_have_passed(self) -> None:
        self.ledger.uptime[open_challenge_key(1, 0)] = open_challenge_value(0)
        self.ledger.height = c.RESPONSE_DEADLINE_BLOCKS
        self.assertEqual(b._expiry_step(self.ledger), ([], []))


class InvariantTest(unittest.TestCase):
    """Each of the six is checked, and each is broken on purpose to prove it."""

    def setUp(self) -> None:
        self.ledger = _ledger()
        self.ledger.height = c.CYCLE_BLOCKS + 100

    def test_a_clean_state_reports_nothing(self) -> None:
        self.assertEqual(self.ledger.uptime_failures(), [])

    def test_a_challenge_past_its_deadline_is_reported(self) -> None:
        self.ledger.uptime[open_challenge_key(1, 0)] = open_challenge_value(0)
        self.assertEqual(
            self.ledger.uptime_failures(), ["an open challenge outlived its deadline"]
        )

    def test_a_challenge_inside_its_deadline_is_not(self) -> None:
        oldest = self.ledger.height - c.RESPONSE_DEADLINE_BLOCKS + 1
        self.ledger.uptime[open_challenge_key(oldest, 0)] = open_challenge_value(0)
        self.assertEqual(self.ledger.uptime_failures(), [])

    def test_the_window_before_the_executing_one_is_retained(self) -> None:
        self.ledger.uptime[seat_window_key(0, 0)] = seat_window_value(1, 0)
        self.assertEqual(self.ledger.uptime_failures(), [])

    def test_a_record_two_windows_old_is_reported(self) -> None:
        self.ledger.height = 2 * c.CYCLE_BLOCKS + 100
        self.ledger.uptime[seat_window_key(0, 0)] = seat_window_value(1, 0)
        self.assertEqual(
            self.ledger.uptime_failures(),
            ["a seat window record outlived its retention"],
        )

    def test_a_disputed_bitmap_past_the_cap_is_reported(self) -> None:
        over = (1 << (c.DISPUTE_CAP_SLOTS_PER_SEAT + 1)) - 1
        self.ledger.uptime[seat_window_key(1, 0)] = seat_window_value(
            all_slots_credited(), over
        )
        self.assertIn(
            "a disputed bitmap exceeds the dispute cap", self.ledger.uptime_failures()
        )

    def test_a_maximal_dispute_leaves_a_perfect_seat_at_the_threshold(self) -> None:
        capped = (1 << c.DISPUTE_CAP_SLOTS_PER_SEAT) - 1
        self.ledger.uptime[seat_window_key(1, 0)] = seat_window_value(
            all_slots_credited(), capped
        )
        self.assertEqual(self.ledger.uptime_failures(), [])

    def test_an_entry_of_another_kind_is_reported(self) -> None:
        self.ledger.uptime[bytes([1]) + bytes(4)] = b""
        self.assertEqual(
            self.ledger.uptime_failures(),
            ["the uptime map holds an entry of another kind"],
        )


class BlockAtomicityTest(unittest.TestCase):
    """An invariant failure restores the pre-block state exactly."""

    def test_a_rejected_block_leaves_the_state_root_unchanged(self) -> None:
        ledger = _ledger()
        ledger.seats[0] = Seat(
            hub_identity_hash=bytes(32),
            referrer_hub_identity=None,
            is_activated=True,
            activation_height=10,
        )
        ledger.height = 2 * c.CYCLE_BLOCKS + 100
        # A record two windows old, which no conforming block could have left
        # behind: the prologue deletes the due window's records at every window
        # boundary. The retention invariant fails and the block is refused whole.
        ledger.uptime[seat_window_key(0, 0)] = seat_window_value(1, 0)
        before = ledger.state_root()
        height = ledger.height
        with self.assertRaises(ConservationFailure):
            b.execute_block(ledger, [], trace.Signatures().oracle)
        self.assertEqual(ledger.height, height)
        self.assertEqual(ledger.state_root(), before)


if __name__ == "__main__":
    unittest.main()
