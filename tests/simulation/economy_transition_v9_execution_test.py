#!/usr/bin/env python3
"""Version nine's execution half: the clock in a block, the settlement, kind 22.

The recorded vectors run three scenarios end to end. These cover what a scenario
cannot: that a block-level timestamp failure rejects the whole block and restores
the state exactly, that the carried dispatch is version eight's own function
object rather than a copy, that the prologue refuses the states it must, and that
the receipt's boundary against version eight holds in both directions.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v6.receipt import Receipt
from simulation.economy_transition_v6.trace import Signatures
from simulation.economy_transition_v8 import receipt as v8receipt
from simulation.economy_transition_v8 import transitions as v8transitions
from simulation.economy_transition_v9 import contract as c
from simulation.economy_transition_v9 import receipt, trace, transitions
from simulation.economy_transition_v9.block import InvalidBlock, execute_block
from simulation.economy_transition_v9.ledger import ConservationFailure, Ledger


def fresh() -> tuple[Ledger, Signatures]:
    return Ledger.from_genesis(trace.genesis()), Signatures()


# Each scenario is a real chain of over a hundred thousand heights, so it is run
# once and shared. Nothing below mutates one except the shorthand refusal, which
# raises before it writes.
_SCENARIOS: dict[str, object] = {}


def scenario(name: str):
    if name not in _SCENARIOS:
        builder = getattr(trace, f"{name}_scenario")
        _SCENARIOS[name] = builder()[0]
    return _SCENARIOS[name]


class TimestampTest(unittest.TestCase):
    def test_a_block_below_its_predecessors_stamp_is_rejected_whole(self) -> None:
        ledger, signatures = fresh()
        execute_block(ledger, trace.GENESIS_MILLIS + 1_000, [], signatures.oracle)
        before = ledger.state_root()
        with self.assertRaises(InvalidBlock) as rejected:
            execute_block(ledger, trace.GENESIS_MILLIS, [], signatures.oracle)
        self.assertIn("TIMESTAMP_NOT_MONOTONIC", str(rejected.exception))
        self.assertEqual(ledger.state_root(), before)
        self.assertEqual(ledger.height, 1)

    def test_a_stamp_outside_the_range_is_rejected_whole(self) -> None:
        ledger, signatures = fresh()
        before = ledger.state_root()
        with self.assertRaises(InvalidBlock) as rejected:
            execute_block(
                ledger, c.MAX_TIMESTAMP_MILLIS + 1, [], signatures.oracle
            )
        self.assertIn("TIMESTAMP_RANGE", str(rejected.exception))
        self.assertEqual(ledger.state_root(), before)
        self.assertEqual(ledger.height, 0)

    def test_two_consecutive_blocks_may_carry_one_millisecond(self) -> None:
        ledger, signatures = fresh()
        stamp = trace.GENESIS_MILLIS + 5_000
        execute_block(ledger, stamp, [], signatures.oracle)
        execute_block(ledger, stamp, [], signatures.oracle)
        self.assertEqual(ledger.height, 2)
        self.assertEqual(ledger.timestamp, stamp)

    def test_the_block_adopts_its_own_stamp(self) -> None:
        ledger, signatures = fresh()
        stamp = trace.GENESIS_MILLIS + 9_000
        block = execute_block(ledger, stamp, [], signatures.oracle)
        self.assertEqual(ledger.timestamp, stamp)
        self.assertEqual(block.timestamp, stamp)

    def test_execution_cannot_reach_a_clock(self) -> None:
        """`block.py` binds `timeline.replay` and never binds `timeline.accept`.

        The separation is structural rather than textual: the module's namespace
        holds the clockless path and not the admission one, and `replay` takes no
        clock argument at all, so there is nothing to pass that would make a
        replaying machine check a tolerance.
        """
        import inspect

        from simulation.economy_transition_v9 import block as block_module
        from simulation.economy_transition_v9 import timeline

        bound = {
            name for name, value in vars(block_module).items()
            if value is timeline.accept
        }
        self.assertEqual(bound, set())
        self.assertIs(block_module.replay_timestamp, timeline.replay)
        self.assertNotIn(
            "observed_clock", inspect.signature(timeline.replay).parameters
        )


class PrologueTest(unittest.TestCase):
    def test_the_shorthand_carries_the_timestamp(self) -> None:
        ledger, _signatures = fresh()
        ledger.advance_to(100, trace.timestamp_of_height(100))
        self.assertEqual(ledger.timestamp, trace.timestamp_of_height(100))
        self.assertEqual(ledger.conservation_failures(), [])

    def test_the_shorthand_is_refused_once_a_seat_is_activated(self) -> None:
        built = scenario("settled")
        with self.assertRaises(ConservationFailure):
            built.ledger.advance_to(
                built.ledger.height + 10,
                trace.timestamp_of_height(built.ledger.height + 10),
            )

    def test_exactly_two_window_months_are_retained(self) -> None:
        built = scenario("settled")
        self.assertEqual(len(built.ledger.window_months), 2)
        self.assertEqual(built.ledger.conservation_failures(), [])

    def test_every_open_figure_belongs_to_the_cursors_month(self) -> None:
        built = scenario("settled")
        ledger = built.ledger
        for month, _seat in ledger.figures:
            self.assertEqual(month, ledger.accumulating_month)


class SettlementTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scenario = scenario("settled")

    def test_the_pool_paid_its_best_performer(self) -> None:
        block = self.scenario.notes["settlement_block"]
        self.assertEqual(block.settled.winners, (trace.ALICE_SEAT,))
        self.assertGreater(block.settled.share, 0)

    def test_both_pool_identities_hold_after_the_run(self) -> None:
        ledger = self.scenario.ledger
        assigned = sum(accrued for accrued, _ in ledger.claims.values())
        taken = sum(minted for _, minted in ledger.claims.values())
        self.assertEqual(ledger.pool_accrued, ledger.pool_payable + assigned)
        self.assertEqual(ledger.pool_minted, taken)
        self.assertEqual(ledger.conservation_failures(), [])

    def test_the_winner_minted_and_the_claim_is_kept(self) -> None:
        results = self.scenario.results()
        self.assertEqual(results["winner_mints_the_pool"], "SUCCESS")
        self.assertEqual(results["a_second_mint_collects_nothing"], "NOTHING_TO_MINT")
        accrued, minted = self.scenario.ledger.claims[trace.ALICE_SEAT]
        self.assertEqual(accrued, minted)
        self.assertGreater(accrued, 0)

    def test_a_refusal_writes_nothing_and_leaves_the_nonce(self) -> None:
        results = self.scenario.results()
        self.assertEqual(
            results["an_unconfirmed_mint_is_refused"], "BIOMETRIC_REQUIRED"
        )
        self.assertEqual(results["winner_mints_the_pool"], "SUCCESS")

    def test_a_stranger_cannot_mint_another_seats_award(self) -> None:
        self.assertEqual(
            self.scenario.results()["a_stranger_cannot_mint_another_seats_award"],
            "UNAUTHORIZED",
        )


class HaltTest(unittest.TestCase):
    def test_one_assignment_closes_one_month_and_skips_three(self) -> None:
        built = scenario("halted")
        skipping = [
            block for block in built.notes["audit_blocks"] if block.skipped_months
        ]
        self.assertEqual(len(skipping), 1)
        self.assertEqual(len(skipping[0].skipped_months), 3)
        self.assertIsNotNone(skipping[0].settled)

    def test_the_halted_chain_conserves_every_unit(self) -> None:
        built = scenario("halted")
        self.assertEqual(built.ledger.conservation_failures(), [])


class RestartTest(unittest.TestCase):
    def test_the_run_is_contiguous_from_genesis(self) -> None:
        built = scenario("restart")
        self.assertEqual([block.height for block in built.blocks], [1, 2, 3, 4])
        for previous, block in zip(built.blocks, built.blocks[1:]):
            self.assertEqual(block.previous_state_root, previous.resulting_state_root)

    def test_its_first_two_blocks_are_the_settled_chains(self) -> None:
        # The docstring's claim, checked: a layer replaying this run is replaying
        # the prefix of the chain the settlement vectors record, not a lookalike.
        restart = scenario("restart")
        settled = scenario("settled")
        for index in (0, 1):
            self.assertEqual(restart.blocks[index].header, settled.blocks[index].header)

    def test_the_repeated_stamp_is_admitted_and_one_below_it_is_not(self) -> None:
        built = scenario("restart")
        self.assertEqual(built.blocks[2].timestamp, built.blocks[1].timestamp)
        self.assertEqual(
            built.notes["refused_below_the_predecessor"], "TIMESTAMP_NOT_MONOTONIC"
        )
        self.assertEqual(
            built.notes["root_after_the_refusal"], built.blocks[1].resulting_state_root
        )


class DispatchTest(unittest.TestCase):
    def test_the_carried_path_is_version_eights_own_object(self) -> None:
        self.assertIs(transitions.VERSION_EIGHT_DISPATCH, v8transitions.dispatch)

    def test_version_nine_adds_one_kind_and_no_code(self) -> None:
        self.assertEqual(len(c.TRANSACTION_KINDS), 17)
        self.assertEqual(len(c.RESULT_CODES), 45)


class ReceiptTest(unittest.TestCase):
    def receipt(self, **overrides) -> Receipt:
        fields = dict(
            transaction_id=bytes(32), kind=c.MINT_POOL, result_code=0,
            fee_charged=trace.FIXED_FEE, issued_atomic=500,
        )
        fields.update(overrides)
        return Receipt(**fields)

    def test_kind_twenty_two_issues_and_is_not_exempt(self) -> None:
        self.assertNotIn(c.MINT_POOL, receipt.NON_ISSUING_KINDS)
        self.assertNotIn(c.MINT_POOL, receipt.FEE_EXEMPT_KINDS)
        self.assertEqual(len(receipt.encode(self.receipt())), 56)

    def test_the_boundary_against_version_eight_holds_both_ways(self) -> None:
        mine = receipt.encode(self.receipt())
        with self.assertRaises(v8receipt.InvalidReceipt):
            v8receipt.decode(mine)
        theirs = v8receipt.encode(
            Receipt(
                transaction_id=bytes(32), kind=c.TRANSFER, result_code=0,
                fee_charged=trace.FIXED_FEE, issued_atomic=0,
            )
        )
        with self.assertRaises(receipt.InvalidReceipt):
            receipt.decode(theirs)

    def test_a_failed_transaction_charges_and_issues_nothing(self) -> None:
        with self.assertRaises(receipt.InvalidReceipt):
            receipt.encode(self.receipt(result_code=c.CODE_NUMBER["NOTHING_TO_MINT"]))


if __name__ == "__main__":
    unittest.main()
