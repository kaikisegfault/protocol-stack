#!/usr/bin/env python3
"""Ordered block execution, the prologue, and what version seven refuses.

Version six had to reject the alternative ordering by argument: writing a cycle
assignment after a block's transactions makes a boundary mint collect nothing and
forfeit that day permanently, which is expensive but produces a state a node
would accept. **Version seven refuses it outright**, because the window's
permissions enter `outstanding` with the only seat that could have claimed them
already marked past them, and the backing identity is an equality.

That is the claim this module exists to check, together with the two the block
layer inherits and must not have lost: an admission failure never reaches the
transaction root, and a refused transaction leaves the state root exactly as it
found it.
"""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from simulation.economy_transition_v3.settlement import SeatCycle
from simulation.economy_transition_v6 import block as v6_block
from simulation.economy_transition_v7 import contract as c
from simulation.economy_transition_v7 import trace
from simulation.economy_transition_v7.block import (
    BLOCK_HEADER_BYTES,
    BLOCK_HEADER_SCHEMA_VERSION,
    InvalidBlock,
    block_header,
    execute_block,
    transaction_root,
)
from simulation.economy_transition_v7.ledger import ConservationFailure, Ledger


class InheritedConstructionTest(unittest.TestCase):
    """The header and the transaction tree are version one's, not re-versioned."""

    def test_the_header_schema_version_is_still_one(self) -> None:
        self.assertEqual(BLOCK_HEADER_SCHEMA_VERSION, 1)

    def test_the_header_construction_is_version_six_s_function(self) -> None:
        self.assertIs(block_header, v6_block.block_header)

    def test_the_transaction_tree_is_version_six_s_function(self) -> None:
        self.assertIs(transaction_root, v6_block.transaction_root)

    def test_the_header_is_still_one_hundred_and_forty_six_octets(self) -> None:
        scenario, _signatures = trace.pool_scenario()
        for block in scenario.blocks:
            self.assertEqual(len(block.header), BLOCK_HEADER_BYTES)

    def test_the_receipts_are_version_seven_receipts(self) -> None:
        scenario, _signatures = trace.pool_scenario()
        for block in scenario.blocks:
            for raw in block.receipts:
                self.assertEqual(int.from_bytes(raw[4:6], "big"), 7)


class PrologueTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scenario, _signatures = trace.pool_scenario()

    def test_the_record_is_written_at_the_first_height_of_the_window_after_next(
        self,
    ) -> None:
        for block in self.scenario.blocks:
            if block.assigned_window is None:
                continue
            self.assertEqual(
                block.height,
                (block.assigned_window + c.ASSIGNMENT_LAG_WINDOWS) * c.CYCLE_BLOCKS,
            )

    def test_exactly_two_windows_were_assigned(self) -> None:
        assigned = [
            block.assigned_window
            for block in self.scenario.blocks
            if block.assigned_window is not None
        ]
        self.assertEqual(assigned, [trace.DEAD_WINDOW, trace.WON_WINDOW])

    def test_a_block_off_a_window_boundary_assigns_nothing(self) -> None:
        early = [block for block in self.scenario.blocks if block.height < c.CYCLE_BLOCKS]
        self.assertTrue(early)
        for block in early:
            self.assertIsNone(block.assigned_window)

    def test_the_mint_in_the_boundary_block_reached_the_record_it_wrote(self) -> None:
        """One block, and the mint sees a window written moments earlier."""
        boundary = self.scenario.blocks[-1]
        self.assertEqual(boundary.assigned_window, trace.WON_WINDOW)
        self.assertEqual(boundary.results[0], "SUCCESS")
        self.assertGreater(boundary.executed[0].outcome.issued_atomic, 0)

    def test_the_seat_that_generated_the_permissions_collected_nothing(self) -> None:
        """The reallocation is what it says it is: Bob's mint succeeds at zero."""
        boundary = self.scenario.blocks[-1]
        bob = boundary.executed[1]
        self.assertEqual(bob.result, "SUCCESS")
        self.assertEqual(bob.outcome.issued_atomic, 0)
        self.assertEqual(bob.outcome.fee_charged, trace.FIXED_FEE)

    def test_a_second_mint_in_the_same_block_has_nothing_to_mint(self) -> None:
        """The mark advance is what makes the walk range empty, not an equality."""
        boundary = self.scenario.blocks[-1]
        again = boundary.executed[2]
        self.assertEqual(again.result, "NOTHING_TO_MINT")
        self.assertEqual(again.outcome.fee_charged, 0)

    def test_a_version_six_bound_transaction_never_reaches_execution(self) -> None:
        self.assertEqual(
            self.scenario.rejected,
            {"carol_registers_on_the_version_six_chain": 2},
        )


class RejectedOrderingTest(unittest.TestCase):
    """The reading version six argued against, and version seven cannot accept."""

    def setUp(self) -> None:
        self.scenario, _signatures = trace.boundary_scenario()

    def test_the_rejected_ordering_breaks_the_backing_identity(self) -> None:
        refusal = self.scenario.notes["rejected_ordering_refusal"]
        self.assertIsNotNone(refusal, "the rejected ordering produced a block")
        for channel in c.RECOVERY_POOL_LEGS:
            self.assertIn(f"channel {channel} breaks the backing identity", refusal)

    def test_the_rejected_block_preserved_the_pre_block_state(self) -> None:
        self.assertTrue(self.scenario.notes["rejected_ordering_preserved_state"])

    def test_the_accepted_ordering_pays_on_the_same_inputs(self) -> None:
        self.assertEqual(
            self.scenario.notes["accepted_ordering_issued"],
            4 * c.BASE_PERMISSION_TOTAL,
        )

    def test_the_difference_is_the_whole_of_what_the_mint_would_have_lost(self) -> None:
        """Under version six this was a forfeit; here it is an unconstructible block."""
        self.assertGreater(self.scenario.notes["accepted_ordering_issued"], 0)
        self.assertIsNotNone(self.scenario.notes["rejected_ordering_refusal"])


class PermanenceTest(unittest.TestCase):
    """A machine past its own 731 cycles, and the cycle that contributes nothing."""

    def setUp(self) -> None:
        self.scenario, _signatures = trace.permanence_scenario()

    def test_the_drained_cycle_assigned_no_permission_at_all(self) -> None:
        self.assertEqual(
            self.scenario.notes["assigned_after_drained_cycle"],
            self.scenario.notes["assigned_after_stranded_cycle"],
        )

    def test_a_cycle_with_no_contributing_seat_still_drained_the_pool(self) -> None:
        self.assertEqual(
            self.scenario.notes["pool_after_mint"],
            {channel: 0 for channel in c.RECOVERY_POOL_LEGS},
        )

    def test_the_out_of_span_machine_collected_a_whole_base_permission(self) -> None:
        self.assertEqual(
            self.scenario.notes["carol_issued"], c.BASE_PERMISSION_TOTAL
        )

    def test_the_contributing_seat_never_accrued_a_bit(self) -> None:
        """Alice generated the permission and Carol was paid all of it."""
        self.assertEqual(
            self.scenario.notes["alice_never_accrued"], trace.STRANDED_WINDOW - 1
        )

    def test_nothing_is_left_outstanding(self) -> None:
        for channel in c.RECOVERY_POOL_LEGS:
            self.assertEqual(self.scenario.notes["outstanding_after_mint"][channel], 0)


class MeasurementBindingTest(unittest.TestCase):
    """Three fields are measured; the mark and the referrer are chain state."""

    def _at_a_boundary(self) -> tuple[Ledger, trace.Signatures]:
        signatures = trace.Signatures()
        scenario = trace._seated_chain(
            signatures,
            "binding",
            [(trace.ALICE_IDENTITY, trace.ALICE_KEY, trace.ALICE_SIGNER_KEY,
              trace.ALICE_SEAT)],
            trace.DEAD_WINDOW,
        )
        trace._advance_to_boundary(scenario, trace.DEAD_WINDOW)
        return scenario.ledger, signatures

    def test_a_measurement_naming_an_unsold_seat_rejects_the_block(self) -> None:
        ledger, signatures = self._at_a_boundary()
        before = ledger.state_root()
        uptime = {
            trace.DEAD_WINDOW: [SeatCycle(4242, trace.MET_UPTIME_SECONDS, True, 0)]
        }
        with self.assertRaises(InvalidBlock):
            execute_block(ledger, [], signatures.oracle, uptime=uptime)
        self.assertEqual(ledger.state_root(), before)

    def test_a_supplied_mark_is_ignored_in_favour_of_the_seat_entry(self) -> None:
        """The accumulation cap is applied against the mark the mint will read.

        The measurement here claims a mark thirty-one windows stale, which would
        put the seat over the cap and stop it accruing. The seat entry says
        otherwise and the seat entry is what counts, so the bit is set.
        """
        ledger, signatures = self._at_a_boundary()
        stale = trace.DEAD_WINDOW - c.MINT_ACCUMULATION_CAP - 1
        uptime = {
            trace.DEAD_WINDOW: [
                SeatCycle(trace.ALICE_SEAT, trace.MET_UPTIME_SECONDS, True, stale)
            ]
        }
        execute_block(ledger, [], signatures.oracle, uptime=uptime)
        record = ledger.assignments[trace.DEAD_WINDOW]
        from simulation.economy_transition_v7.state import (
            bit_is_set,
            decode_cycle_assignment_value,
        )

        decoded = decode_cycle_assignment_value(record)
        self.assertTrue(bit_is_set(decoded["accrued_bitmap"], trace.ALICE_SEAT))
        self.assertTrue(bit_is_set(decoded["winner_bitmap"], trace.ALICE_SEAT))
        ledger.require_conserved()


class KindCoverageTest(unittest.TestCase):
    """Every kind version seven admits is executed by the recorded trace.

    Version six's execution trace reaches eleven of the fourteen. Version
    seven's reaches all fourteen, and the reason it must is not tidiness: the
    version-six vectors record version-six roots and version-six receipts, so a
    kind version seven never executes has no recorded version-seven commitment
    for a second implementation to reproduce.
    """

    def setUp(self) -> None:
        self.reached = set()
        for maker in trace.SCENARIOS:
            scenario, _signatures = maker()
            for block in scenario.blocks:
                for entry in block.executed:
                    self.reached.add(entry.kind)

    def test_every_kind_is_executed(self) -> None:
        self.assertEqual(self.reached, set(c.TRANSACTION_KINDS))

    def test_no_retired_kind_is_executed(self) -> None:
        self.assertEqual(self.reached & set(c.RETIRED_KINDS), set())

    def test_every_kind_produced_a_version_seven_receipt(self) -> None:
        """The claim the version-six vectors cannot make about these bytes."""
        versions = set()
        for maker in trace.SCENARIOS:
            scenario, _signatures = maker()
            for block in scenario.blocks:
                for raw in block.receipts:
                    versions.add(int.from_bytes(raw[4:6], "big"))
        self.assertEqual(versions, {7})


class BlockAtomicityTest(unittest.TestCase):
    """Inherited, and required here because losing it would be silent."""

    def _funded(self) -> tuple[Ledger, trace.Signatures]:
        signatures = trace.Signatures()
        ledger = Ledger.from_genesis(trace.genesis())
        raw = trace._register(
            signatures, ledger, trace.ALICE_IDENTITY, trace.ALICE_KEY,
            trace.ALICE_SIGNER_KEY, valid_until=trace.VALID_UNTIL,
        )
        execute_block(ledger, [raw], signatures.oracle)
        return ledger, signatures

    def test_an_admission_failure_never_reaches_the_transaction_root(self) -> None:
        ledger, signatures = self._funded()
        foreign = trace._register(
            signatures, copy.deepcopy(ledger), trace.BOB_IDENTITY, trace.BOB_KEY,
            trace.BOB_SIGNER_KEY, valid_until=trace.VALID_UNTIL,
        )
        broken = bytearray(foreign)
        broken[6] ^= 0xFF  # a chain-ID octet: admitted nowhere, executed nowhere
        block = execute_block(ledger, [bytes(broken)], signatures.oracle)
        self.assertEqual(block.executed, [])
        self.assertEqual(block.transaction_root, transaction_root([]).hex())
        self.assertEqual(len(block.admissions), 1)
        self.assertFalse(block.admissions[0].admitted)

    def test_a_refused_transaction_leaves_the_state_root_untouched(self) -> None:
        ledger, signatures = self._funded()
        replayed = trace._register(
            signatures, ledger, trace.ALICE_IDENTITY, trace.ALICE_KEY,
            trace.ALICE_SIGNER_KEY, valid_until=trace.VALID_UNTIL,
        )
        block = execute_block(ledger, [replayed], signatures.oracle)
        self.assertEqual(block.results, ["REPLAY"])
        self.assertEqual(block.atomic_failures, 1)
        self.assertEqual(block.executed[0].receipt.fee_charged, 0)

    def test_the_height_advances_by_exactly_one(self) -> None:
        ledger, signatures = self._funded()
        before = ledger.height
        block = execute_block(ledger, [], signatures.oracle)
        self.assertEqual(block.height, before + 1)
        self.assertEqual(ledger.height, before + 1)

    def test_an_invariant_failure_rejects_the_whole_block(self) -> None:
        ledger, signatures = self._funded()
        ledger.channel_outstanding[0] += 1
        before = copy.deepcopy(ledger.__dict__)
        with self.assertRaises(ConservationFailure):
            execute_block(ledger, [], signatures.oracle)
        self.assertEqual(ledger.height, before["height"])


if __name__ == "__main__":
    unittest.main()
