#!/usr/bin/env python3
"""Version ten's execution half: what a fixed vector cannot pin.

The recorded vectors fix one outcome per case. These cover the structure behind
them: that every carried kind runs on version nine's own dispatch, that the
approval adapter redirects exactly the five withdrawn messages, where the
lifetime rule sits among the envelope checks, that a chain with no machine key
is untouched by the registry step, and that a run is deterministic.
"""

from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import label_prefix
from simulation.economy_transition_v6.receipt import InvalidReceipt, Receipt
from simulation.economy_transition_v9 import contract as v9c
from simulation.economy_transition_v9 import transitions as v9transitions
from simulation.economy_transition_v10 import contract as c
from simulation.economy_transition_v10 import population, transitions
from simulation.economy_transition_v10.approval import WITHDRAWN_PREFIXES, ApprovalOracle
from simulation.economy_transition_v10.block import execute_block, open_window
from simulation.economy_transition_v10.envelope import decode_signed
from simulation.economy_transition_v10.execution import execute
from simulation.economy_transition_v10.fixture import (
    ALICE,
    Builder,
    LAUNCH_KEY,
    Signatures,
    genesis,
    timestamp_of_height,
)
from simulation.economy_transition_v10.ledger import Ledger
from simulation.economy_transition_v10.messages import approval_message
from simulation.economy_transition_v10.receipt import encode as encode_receipt


def registered_chain() -> tuple[Ledger, Builder]:
    """Alice registered under the launch key at height 1, and nothing else."""
    signatures = Signatures()
    ledger = Ledger.from_genesis(genesis())
    build = Builder(signatures, ledger)
    block = execute_block(
        ledger, timestamp_of_height(1),
        [build.registration(ALICE, c.LAUNCH_ATTESTER, LAUNCH_KEY, 1 + 1_200)],
        signatures.oracle,
    )
    assert block.results == ["SUCCESS"]
    return ledger, build


class CarriedPathTest(unittest.TestCase):
    def test_carried_kinds_run_on_version_nines_own_dispatch(self) -> None:
        self.assertIs(transitions.VERSION_NINE_DISPATCH, v9transitions.dispatch)

    def test_the_adapter_redirects_exactly_the_five_withdrawn_labels(self) -> None:
        expected = {label_prefix(getattr(v9c, name)) for name in c.WITHDRAWN_IN_V10}
        self.assertEqual(set(WITHDRAWN_PREFIXES), expected)
        self.assertEqual(len(WITHDRAWN_PREFIXES), 5)


class ApprovalOracleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger, self.build = registered_chain()
        self.oracle = self.build.signatures.oracle
        raw = self.build.purchase(ALICE, 0, 1, 1 + 1_200)
        self.purchase, _ = decode_signed(raw)

    def test_a_withdrawn_message_verifies_as_the_whole_transaction(self) -> None:
        adapter = ApprovalOracle(self.oracle, self.purchase)
        withdrawn = label_prefix(v9c.PURCHASE_LABEL) + b"anything at all"
        signature = self.purchase.body["hub_signature"]
        self.assertTrue(adapter.verify(ALICE.hub_key, withdrawn, signature))
        self.assertFalse(adapter.verify(ALICE.signer_key, withdrawn, signature))

    def test_a_kind_without_a_body_approval_never_verifies_a_withdrawn_one(self) -> None:
        transfer, _ = decode_signed(self.build.transfer(ALICE, ALICE, 1, 2))
        adapter = ApprovalOracle(self.oracle, transfer)
        withdrawn = label_prefix(v9c.TRANSFER_CONFIRM_LABEL)
        self.assertFalse(adapter.verify(ALICE.hub_key, withdrawn, bytes(64)))

    def test_any_other_message_passes_through(self) -> None:
        message = b"\x05other" + bytes(8)
        signature = self.build.signatures.sign(LAUNCH_KEY, message)
        adapter = ApprovalOracle(self.oracle, self.purchase)
        self.assertTrue(adapter.verify(LAUNCH_KEY, message, signature))

    def test_the_approval_is_the_contract_halfs_construction(self) -> None:
        blank = replace(
            self.purchase, body=self.purchase.body | {"hub_signature": bytes(64)}
        )
        self.assertEqual(approval_message(self.purchase), approval_message(blank))


class LifetimePlacementTest(unittest.TestCase):
    """The rule sits straight after `EXPIRED` and ahead of every escrow check."""

    def setUp(self) -> None:
        self.ledger, self.build = registered_chain()
        self.ledger.height = 2

    def outcome(self, raw: bytes) -> str:
        transaction, _ = decode_signed(raw)
        return execute(self.ledger, transaction, self.build.signatures.oracle).result

    def test_it_precedes_the_nonce(self) -> None:
        raw = self.build.purchase(ALICE, 0, 9, 2 + 1_201)
        self.assertEqual(self.outcome(raw), "APPROVAL_LIFETIME_EXCEEDED")

    def test_it_follows_the_fee_limit(self) -> None:
        transaction, _ = decode_signed(self.build.purchase(ALICE, 0, 1, 2 + 1_201))
        low = replace(transaction, fee_limit=1)
        result = execute(self.ledger, low, self.build.signatures.oracle).result
        self.assertEqual(result, "FEE_LIMIT_TOO_LOW")

    def test_an_absent_field_is_never_governed(self) -> None:
        raw = self.build.posture(ALICE, 1, True, 10_000_000_000, approve=False)
        # A tightening that changes nothing is refused for that, not for its life.
        self.assertEqual(self.outcome(raw), "REPLAY")


class ReceiptTest(unittest.TestCase):
    def test_kind_23_issues_nothing_and_is_charged(self) -> None:
        charged = Receipt(bytes(32), c.REGISTER_MACHINE_KEY, 0, 1_000, 0)
        self.assertEqual(len(encode_receipt(charged)), 56)
        with self.assertRaises(InvalidReceipt):
            encode_receipt(replace(charged, issued_atomic=1))

    def test_a_new_code_is_a_failure(self) -> None:
        refused = Receipt(bytes(32), c.HUB_REGISTER, 48, 0, 0)
        encode_receipt(refused)
        with self.assertRaises(InvalidReceipt):
            encode_receipt(replace(refused, fee_charged=1))


class RegistryStepTest(unittest.TestCase):
    def test_a_chain_with_no_machine_key_is_untouched(self) -> None:
        ledger, _build = registered_chain()
        for window in (1, 2, 3):
            ledger.height = window * c.CYCLE_BLOCKS
            ledger.timestamp = timestamp_of_height(ledger.height)
            outcome = open_window(ledger)
            if window >= c.ASSIGNMENT_LAG_WINDOWS:
                self.assertEqual(outcome.active_machines, 0)
            self.assertFalse(outcome.retired)
        self.assertEqual(ledger.machine_keys, {})
        self.assertIsNone(ledger.launch_retired_at)

    def test_the_window_0_assignment_counts_no_unmarked_key(self) -> None:
        harness = population.span_run(through_window=2)
        self.assertEqual(harness.windows[2].active_machines, 0)
        self.assertEqual(harness.ledger.machine_keys[0].last_met_window, 0)

    def test_a_run_is_deterministic(self) -> None:
        first = population.span_run(through_window=40).ledger.state_root()
        second = population.span_run(through_window=40).ledger.state_root()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
