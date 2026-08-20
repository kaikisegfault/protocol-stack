#!/usr/bin/env python3
"""The version-seven ledger state, and the two identities it is stated over.

The vector file records what a run of this ledger commits to. What is tested here
is what makes those commitments mean something: that the state version seven
writes is fourteen genesis entries and no carry, that the assignment prologue
leaves the pool the specified order produces, and — the part this whole version
exists for — that the backing identity is an equality a stranded unit and an
invented one both break, in opposite directions.

**Every identity is probed rather than only satisfied.** A conservation check
that has never failed is a check nobody has shown to be load-bearing, so each is
broken deliberately here and required to report exactly the failure it names.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from simulation.economy_transition_v6 import contract as v6
from simulation.economy_transition_v6.ledger import Ledger as LedgerV6
from simulation.economy_transition_v7 import contract as c
from simulation.economy_transition_v7 import trace
from simulation.economy_transition_v7.ledger import ConservationFailure, Ledger
from simulation.economy_transition_v7.settlement import claimable, collect
from simulation.economy_transition_v7.state import (
    InvalidStateEntry,
    decode_recovery_pool_value,
    recovery_pool_key,
    require_entry_shape,
)


def _fresh() -> Ledger:
    return Ledger.from_genesis(trace.genesis())


def _through_the_dead_cycle() -> Ledger:
    """A chain stopped one block after the cycle nobody won, so the pool is full.

    Reached by running the trace's own fixture rather than by assembling a state
    by hand: a hand-built state can satisfy an identity it was built to satisfy,
    while this one was produced by the same blocks the vectors record.
    """
    signatures = trace.Signatures()
    scenario = trace._seated_chain(
        signatures,
        "probe",
        [
            (trace.ALICE_IDENTITY, trace.ALICE_KEY, trace.ALICE_SIGNER_KEY, trace.ALICE_SEAT),
            (trace.BOB_IDENTITY, trace.BOB_KEY, trace.BOB_SIGNER_KEY, trace.BOB_SEAT),
        ],
        trace.DEAD_WINDOW,
    )
    trace._advance_to_boundary(scenario, trace.DEAD_WINDOW)
    trace._run(scenario, signatures, [], uptime=trace.POOL_UPTIME)
    return scenario.ledger


class GenesisStateTest(unittest.TestCase):
    def test_genesis_writes_fourteen_economy_entries(self) -> None:
        self.assertEqual(len(_fresh().economy_entries()), 14)

    def test_genesis_writes_one_recovery_pool_entry_with_five_zero_legs(self) -> None:
        entries = _fresh().economy_entries()
        self.assertIn(recovery_pool_key(), entries)
        legs = decode_recovery_pool_value(entries[recovery_pool_key()])
        self.assertEqual(legs, {channel: 0 for channel in c.RECOVERY_POOL_LEGS})

    def test_no_entry_is_written_under_the_retired_carry_kind(self) -> None:
        for key in _fresh().economy_entries():
            self.assertNotEqual(key[0], v6.CARRY_ENTRY)

    def test_the_projection_refuses_a_carry_entry_outright(self) -> None:
        """A regression to version six's projection fails at the root itself."""
        with self.assertRaises(InvalidStateEntry):
            require_entry_shape(bytes([v6.CARRY_ENTRY, 0]), bytes(8))

    def test_a_fresh_ledger_is_conserved(self) -> None:
        _fresh().require_conserved()

    def test_the_root_is_not_the_version_six_root_of_the_same_state(self) -> None:
        """Both roots exist over the same chain and must never coincide."""
        mine = _fresh()
        theirs = LedgerV6.from_genesis(trace.genesis())
        theirs.chain_id = mine.chain_id
        self.assertNotEqual(mine.state_root(), theirs.state_root())


class ChannelCapBindingTest(unittest.TestCase):
    def test_the_cap_predicate_reads_the_version_three_manifest(self) -> None:
        from simulation.founder_economy_manifest_v3 import contract as manifest

        ledger = _fresh()
        for index, channel in enumerate(manifest.CHANNEL_IDS):
            cap = manifest.CHANNEL_CAPS[channel]
            self.assertTrue(ledger.fits_channel(index, cap))
            self.assertFalse(ledger.fits_channel(index, cap + 1))

    def test_the_renamed_channel_is_the_one_the_manifest_names(self) -> None:
        from simulation.founder_economy_manifest_v3 import contract as manifest

        self.assertEqual(manifest.CHANNEL_IDS[9], "mini_gamified_incentives")


class ProloguePoolTest(unittest.TestCase):
    """One cycle at a time, against the pool the ledger actually holds."""

    def setUp(self) -> None:
        self.scenario, _signatures = trace.pool_scenario()
        self.ledger = self.scenario.ledger

    def test_the_dead_cycle_left_its_whole_contribution_in_the_pool(self) -> None:
        legs = dict(c.BASE_PERMISSION_LEGS)
        pool = self.scenario.notes["pool_after_dead_cycle"]
        for channel in c.RECOVERY_POOL_LEGS:
            self.assertEqual(pool[channel], 2 * legs[channel])

    def test_the_dead_cycle_owed_nobody_anything(self) -> None:
        self.assertEqual(
            self.scenario.notes["claimable_after_dead_cycle"],
            {channel: 0 for channel in c.RECOVERY_POOL_LEGS},
        )

    def test_the_won_cycle_absorbed_the_pool_and_the_mint_took_it(self) -> None:
        legs = dict(c.BASE_PERMISSION_LEGS)
        issued = self.scenario.notes["issued_after_mint"]
        for channel in c.RECOVERY_POOL_LEGS:
            self.assertEqual(issued[channel], 4 * legs[channel])

    def test_nothing_is_left_outstanding_and_nothing_is_left_pooled(self) -> None:
        """The claim version seven exists to make, in one assertion."""
        self.assertEqual(
            self.scenario.notes["pool_after_mint"],
            {channel: 0 for channel in c.RECOVERY_POOL_LEGS},
        )
        for channel in c.RECOVERY_POOL_LEGS:
            self.assertEqual(
                self.scenario.notes["outstanding_after_mint"][channel], 0
            )

    def test_a_cycle_window_cannot_be_assigned_twice(self) -> None:
        window = self.scenario.notes["won_window"]
        assignment = _one_cycle_assignment(self.ledger, window)
        with self.assertRaises(ConservationFailure):
            self.ledger.apply_assignment(assignment, {}, 0)


def _one_cycle_assignment(ledger: Ledger, window: int):
    from simulation.economy_transition_v3.settlement import SeatCycle
    from simulation.economy_transition_v7.settlement import derive_assignment

    return derive_assignment(
        window,
        [SeatCycle(trace.ALICE_SEAT, trace.MET_UPTIME_SECONDS, True, 0)],
        ledger.pool,
    )


class IdentityTest(unittest.TestCase):
    """Both identities, each broken deliberately in the direction it guards."""

    def setUp(self) -> None:
        scenario, _signatures = trace.pool_scenario()
        self.ledger = scenario.ledger
        self.ledger.require_conserved()

    def test_value_created_without_a_claimant_breaks_the_channel_identity(self) -> None:
        self.ledger.channel_outstanding[0] += 1
        self.assertIn(
            "channel 0 breaks the channel identity", self.ledger.conservation_failures()
        )

    def test_a_claim_destroyed_without_payment_breaks_the_backing_identity(self) -> None:
        """The failure the channel identity alone cannot see.

        Moving a unit out of the pool without paying it keeps
        `issued + outstanding` exactly where it was, so the channel identity
        still holds and only the backing identity notices.
        """
        self.ledger.pool[0] += 1
        failures = self.ledger.conservation_failures()
        self.assertIn("channel 0 breaks the backing identity", failures)
        self.assertNotIn("channel 0 breaks the channel identity", failures)

    def test_a_stranded_unit_breaks_the_backing_identity(self) -> None:
        """The other direction, and the one version six could not see at all.

        A unit that leaves the pool without being paid to anybody is stranded:
        `issued + outstanding` has not moved, so version six's carry identity
        would have held with the unit sitting in a term nothing ever releases.
        The backing identity reports it because `claimable + recovery_pool` is
        now one short of `outstanding`.
        """
        ledger = _through_the_dead_cycle()
        ledger.require_conserved()
        self.assertGreater(ledger.pool[0], 0)
        ledger.pool[0] -= 1
        failures = ledger.conservation_failures()
        self.assertIn("channel 0 breaks the backing identity", failures)
        self.assertNotIn("channel 0 breaks the channel identity", failures)

    def test_an_entry_under_the_retired_carry_kind_is_a_failure(self) -> None:
        self.ledger.carry[0] = 1
        self.assertIn(
            "version seven wrote an entry under the retired carry kind",
            self.ledger.conservation_failures(),
        )

    def test_the_channel_identity_has_two_terms_rather_than_three(self) -> None:
        """Version six's third term is gone rather than zero."""
        legs = dict(c.BASE_PERMISSION_LEGS)
        for channel in c.RECOVERY_POOL_LEGS:
            self.assertEqual(
                self.ledger.channel_issued[channel]
                + self.ledger.channel_outstanding[channel],
                self.ledger.assigned_permissions * legs[channel],
            )

    def test_require_conserved_raises_on_any_failure(self) -> None:
        self.ledger.pool[4] += 1
        with self.assertRaises(ConservationFailure):
            self.ledger.require_conserved()


class ClaimableTest(unittest.TestCase):
    """`claimable` is the mint's own walk, run once per seat."""

    def setUp(self) -> None:
        scenario, _signatures = trace.pool_scenario()
        self.ledger = scenario.ledger

    def test_it_is_what_a_sequence_of_mints_would_collect(self) -> None:
        last = max(self.ledger.assignments) if self.ledger.assignments else None
        by_hand = {channel: 0 for channel in c.RECOVERY_POOL_LEGS}
        for seat_id, mark in self.ledger.marks().items():
            for channel, amount in collect(
                seat_id, mark, last, self.ledger.assignments
            ).per_channel.items():
                by_hand[channel] += amount
        self.assertEqual(self.ledger.claimable(), by_hand)

    def test_the_marks_are_the_seat_entries(self) -> None:
        self.assertEqual(
            self.ledger.marks(),
            {
                seat_id: seat.minted_through_window
                for seat_id, seat in self.ledger.seats.items()
            },
        )

    def test_a_chain_with_no_assignment_owes_nothing(self) -> None:
        self.assertEqual(
            claimable({0: 0, 1: 0}, {}),
            {channel: 0 for channel in c.RECOVERY_POOL_LEGS},
        )

    def test_a_seat_marked_past_every_record_is_owed_nothing(self) -> None:
        last = max(self.ledger.assignments)
        self.assertEqual(
            claimable({trace.ALICE_SEAT: last}, self.ledger.assignments),
            {channel: 0 for channel in c.RECOVERY_POOL_LEGS},
        )


if __name__ == "__main__":
    unittest.main()
