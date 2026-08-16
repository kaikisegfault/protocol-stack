#!/usr/bin/env python3
"""Ordered block execution, the assignment prologue, and the recorded trace.

The vector file records the commitments. What is tested here is what makes them
mean something: that an admission failure never reaches the transaction root,
that a refusal leaves the state root untouched, that the block header and the
transaction tree are the accepted version-one constructions rather than
restatements that drifted, and that the ordering derivation is a decision about
money rather than about style.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from simulation.economy_transition_v6 import contract as c
from simulation.economy_transition_v6 import trace
from simulation.economy_transition_v6.block import (
    BLOCK_HEADER_BYTES,
    BLOCK_HEADER_SCHEMA_VERSION,
    InvalidBlock,
    execute_block,
    transaction_root,
)
from simulation.economy_transition_v6.execution import SignatureOracle
from simulation.economy_transition_v6.ledger import Ledger

VECTORS = REPOSITORY_ROOT / "test-vectors" / "economy-transition-v6-execution.txt"
ACCEPTED = REPOSITORY_ROOT / "test-vectors"


def _read(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            key, _, value = stripped.partition("=")
            values[key] = value
    return values


class InheritedConstructionTest(unittest.TestCase):
    """Both are `protocol-primitives-v1`'s, because version six narrows neither."""

    def setUp(self) -> None:
        self.primitives = _read(ACCEPTED / "protocol-primitives-v1.txt")
        self.ledger_vectors = _read(ACCEPTED / "ledger-transition-v1.txt")

    def test_the_transaction_tree_is_the_accepted_one(self) -> None:
        items = [
            bytes.fromhex(self.primitives[f"tx.item{index}"]) for index in range(3)
        ]
        self.assertEqual(transaction_root(items).hex(), self.primitives["tx.root"])
        self.assertEqual(
            transaction_root([]).hex(), self.primitives["tx.empty_root"]
        )

    def test_the_block_header_is_the_accepted_one(self) -> None:
        from simulation.economy_transition_v6.block import block_header

        recorded = bytes.fromhex(self.ledger_vectors["block_header"])
        header = block_header(
            recorded[6:38],
            int.from_bytes(recorded[38:46], "big"),
            self.ledger_vectors["previous_state_root"],
            self.ledger_vectors["transaction_root"],
            self.ledger_vectors["resulting_state_root"],
            int.from_bytes(recorded[142:146], "big"),
        )
        self.assertEqual(header, recorded)
        self.assertEqual(len(header), BLOCK_HEADER_BYTES)

    def test_the_header_schema_version_is_not_re_versioned(self) -> None:
        """Genesis, the receipt, and the state root are; the header is not named."""
        self.assertEqual(BLOCK_HEADER_SCHEMA_VERSION, 1)
        self.assertEqual(c.GENESIS_SCHEMA_VERSION, 6)
        self.assertEqual(c.RECEIPT_VERSION, 6)
        self.assertEqual(c.STATE_ROOT_SCHEMA_VERSION, 6)


class BlockTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scenario, self.signatures = trace.registration_scenario()

    def test_an_admission_failure_never_enters_the_transaction_root(self) -> None:
        block = self.scenario.blocks[1]
        self.assertEqual(self.scenario.raw_inputs[1], 4)
        self.assertEqual(len(block.executed), 2)
        self.assertEqual(
            block.transaction_root, transaction_root(block.admitted_ids).hex()
        )

    def test_every_admitted_transaction_produces_exactly_one_receipt(self) -> None:
        for block in self.scenario.blocks:
            self.assertEqual(len(block.receipts), len(block.executed))
            for raw in block.receipts:
                self.assertEqual(len(raw), 56)

    def test_a_refusal_leaves_the_state_root_untouched(self) -> None:
        refusals = sum(block.atomic_failures for block in self.scenario.blocks)
        self.assertGreater(refusals, 0)
        # `execute_block` raises rather than returning when a refusal writes, so
        # a completed run is the evidence and the count is what it covered.
        self.assertEqual(
            refusals,
            sum(
                1
                for block in self.scenario.blocks
                for entry in block.executed
                if entry.result != "SUCCESS"
            ),
        )

    def test_a_block_beyond_the_raw_input_bound_is_rejected_whole(self) -> None:
        ledger = Ledger(
            chain_id=bytes(32),
            supply_limit=trace.SUPPLY_LIMIT,
            fixed_fee=trace.FIXED_FEE,
            verifier_key=trace.VERIFIER_KEY,
        )
        with self.assertRaises(InvalidBlock):
            execute_block(ledger, [b""] * 65_536, SignatureOracle())
        self.assertEqual(ledger.height, 0)

    def test_a_rejected_block_preserves_the_pre_block_state(self) -> None:
        """An invariant failure rejects the whole block, not one transaction.

        The state is rewound to just before the boundary block, which no real
        chain does — that is the point: it constructs the state a defect would
        produce, so the prologue is offered a window the state already holds.
        """
        from simulation.economy_transition_v6.ledger import ConservationFailure

        scenario, _signatures = trace.block_scenario()
        ledger = scenario.ledger
        ledger.height = trace.BOUNDARY_HEIGHT - 1
        before = ledger.state_root()
        with self.assertRaises(ConservationFailure):
            execute_block(
                ledger, [], SignatureOracle(), uptime=trace.uptime_records()
            )
        self.assertEqual(ledger.height, trace.BOUNDARY_HEIGHT - 1)
        self.assertEqual(ledger.state_root(), before)

    def test_an_empty_block_advances_height_and_commits_the_empty_root(self) -> None:
        ledger = Ledger.from_genesis(trace.genesis())
        block = execute_block(ledger, [], SignatureOracle())
        self.assertEqual(ledger.height, 1)
        self.assertEqual(block.transaction_root, transaction_root([]).hex())
        self.assertEqual(len(block.executed), 0)


class AssignmentPrologueTest(unittest.TestCase):
    """Where the cycle assignment lands decides whether a founder is paid."""

    def setUp(self) -> None:
        self.scenario, _signatures = trace.block_scenario()
        self.accepted = self.scenario.blocks[-1]
        self.rejected = self.scenario.notes["rejected_ordering"]

    def test_the_boundary_block_writes_the_window_it_is_due(self) -> None:
        self.assertEqual(self.accepted.assigned_window, trace.ASSIGNED_WINDOW)
        self.assertEqual(
            self.accepted.height, (trace.ASSIGNED_WINDOW + 2) * c.CYCLE_BLOCKS
        )

    def test_a_mint_in_that_block_collects_the_window_it_wrote(self) -> None:
        self.assertEqual(self.accepted.results[1], "SUCCESS")
        self.assertGreater(self.accepted.executed[1].receipt.issued_atomic, 0)

    def test_the_epilogue_reading_forfeits_the_cycle_permanently(self) -> None:
        rejected_ledger = self.scenario.notes["rejected_ledger"]
        self.assertEqual(self.rejected.results[1], "SUCCESS")
        self.assertEqual(self.rejected.executed[1].receipt.issued_atomic, 0)
        # The mark advances to the last assigned window whatever the walk found,
        # so the day is gone rather than deferred.
        self.assertEqual(
            rejected_ledger.seats[0].minted_through_window, trace.ASSIGNED_WINDOW
        )
        self.assertLess(
            rejected_ledger.total_supply, self.scenario.ledger.total_supply
        )

    def test_a_referral_is_deferred_rather_than_forfeited(self) -> None:
        rejected_ledger = self.scenario.notes["rejected_ledger"]
        self.assertEqual(self.rejected.results[2], "NOTHING_TO_MINT")
        self.assertGreater(
            rejected_ledger.channel_outstanding[c.REFERRAL_CHANNEL], 0
        )

    def test_no_window_is_assigned_twice(self) -> None:
        from simulation.economy_transition_v3.settlement import derive_assignment
        from simulation.economy_transition_v6.ledger import ConservationFailure

        seats = trace.uptime_records()[trace.ASSIGNED_WINDOW]
        assignment = derive_assignment(trace.ASSIGNED_WINDOW, seats)
        with self.assertRaises(ConservationFailure):
            self.scenario.ledger.apply_assignment(assignment, {}, 0)


class DeterminismTest(unittest.TestCase):
    def test_every_scenario_replays_to_the_same_commitments(self) -> None:
        for maker in trace.SCENARIOS:
            first, _ = maker()
            second, _ = maker()
            self.assertEqual(
                [block.resulting_state_root for block in first.blocks],
                [block.resulting_state_root for block in second.blocks],
            )
            self.assertEqual(
                [block.block_id for block in first.blocks],
                [block.block_id for block in second.blocks],
            )
            self.assertEqual(
                [block.receipts for block in first.blocks],
                [block.receipts for block in second.blocks],
            )

    def test_every_scenario_ends_conserved(self) -> None:
        for maker in trace.SCENARIOS:
            scenario, _ = maker()
            self.assertEqual(
                scenario.ledger.conservation_failures(), [], scenario.name
            )


class VectorFileTest(unittest.TestCase):
    def test_the_verifier_accepts_the_recorded_file(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(
                    REPOSITORY_ROOT
                    / "tools"
                    / "economy-transition-v6-execution-vectors"
                    / "verify.py"
                ),
                "--vectors",
                str(VECTORS),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_no_boolean_vector_is_false(self) -> None:
        recorded = _read(VECTORS)
        self.assertTrue(recorded)
        self.assertEqual([key for key, value in recorded.items() if value == "false"], [])

    def test_the_predecessor_vector_files_are_untouched(self) -> None:
        """This slice adds a file; it edits none, which is the repository rule."""
        for name, count in (
            ("economy-transition-v2.txt", 238),
            ("economy-transition-v3.txt", 579),
            ("economy-transition-v4.txt", 441),
            ("economy-transition-v5.txt", 550),
            ("economy-transition-v6.txt", 462),
        ):
            recorded = _read(ACCEPTED / name)
            self.assertEqual(len(recorded), count, name)


if __name__ == "__main__":
    unittest.main()
