#!/usr/bin/env python3
"""Version seven runs version six's transitions, and this is what says so.

The claim this slice makes is unusual: **thirteen of the fourteen transitions are
not merely equivalent to version six's, they are version six's.** A test that
compared behaviour would pass equally well against a copy that had drifted in a
path no fixture reaches, so what is required here is object identity — the same
function, the same envelope check, the same escrow resolution — and the single
documented exception.

The receipt is the other half. Its layout, its widths, and every combination it
refuses are version six's; two octets are not, and a version-six reader must be
able to tell.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from simulation.economy_transition_v6 import execution as v6_execution
from simulation.economy_transition_v6 import receipt as v6_receipt
from simulation.economy_transition_v6 import transitions as v6_transitions
from simulation.economy_transition_v6 import value_transitions as v6_value
from simulation.economy_transition_v7 import contract as c
from simulation.economy_transition_v7 import execution as e
from simulation.economy_transition_v7 import receipt as r
from simulation.economy_transition_v7 import transitions as t
from simulation.economy_transition_v7 import value_transitions as vt
from simulation.economy_transition_v7 import genesis as g
from simulation.economy_transition_v7 import trace
from simulation.economy_transition_v7.ledger import Ledger


class DispatchTableTest(unittest.TestCase):
    """Fourteen kinds, thirteen of them version six's own function objects."""

    def test_the_table_covers_the_fourteen_kinds_exactly(self) -> None:
        covered = set(t.AUTHORITY_HANDLERS) | set(vt._HANDLERS)
        self.assertEqual(covered, set(c.TRANSACTION_KINDS))

    def test_no_kind_is_handled_twice(self) -> None:
        self.assertEqual(set(t.AUTHORITY_HANDLERS) & set(vt._HANDLERS), set())

    def test_the_six_authority_transitions_are_version_six_s_objects(self) -> None:
        self.assertEqual(set(t.AUTHORITY_HANDLERS), set(t.VERSION_SIX_HANDLERS))
        for kind, handler in t.AUTHORITY_HANDLERS.items():
            self.assertIs(
                handler,
                t.VERSION_SIX_HANDLERS[kind],
                f"kind {kind} is not version six's function",
            )

    def test_exactly_one_value_transition_is_rebound(self) -> None:
        self.assertEqual(set(vt._HANDLERS), set(vt.VERSION_SIX_HANDLERS))
        rebound = {
            kind
            for kind, handler in vt._HANDLERS.items()
            if handler is not vt.VERSION_SIX_HANDLERS[kind]
        }
        self.assertEqual(
            rebound,
            {c.MINT_NODE},
            "only the node mint reads a surface version seven moved",
        )

    def test_the_rebound_transition_is_version_seven_s_own(self) -> None:
        self.assertIs(vt._HANDLERS[c.MINT_NODE], vt.mint_node)
        self.assertIsNot(vt.mint_node, v6_value.mint_node)

    def test_the_retired_kinds_are_handled_by_nobody(self) -> None:
        for kind in c.RETIRED_KINDS:
            self.assertNotIn(kind, t.AUTHORITY_HANDLERS)
            self.assertNotIn(kind, vt._HANDLERS)


class ImportedSurfaceTest(unittest.TestCase):
    """Admission and the shared envelope checks are run, not reproduced."""

    def test_admission_is_version_six_s_function(self) -> None:
        self.assertIs(e.admit, v6_execution.admit)

    def test_the_escrow_resolution_is_version_six_s_function(self) -> None:
        self.assertIs(e._resolve, v6_execution._resolve)

    def test_the_shared_envelope_checks_are_version_six_s_function(self) -> None:
        self.assertIs(e._envelope_checks, v6_execution._envelope_checks)

    def test_the_admission_and_result_spaces_are_version_six_s(self) -> None:
        self.assertIs(e.ADMISSION_NUMBER, v6_execution.ADMISSION_NUMBER)
        self.assertIs(e.Outcome, v6_execution.Outcome)
        self.assertIs(e.Refused, v6_execution.Refused)
        self.assertIs(e.SignatureOracle, v6_execution.SignatureOracle)

    def test_execution_is_not_version_six_s_function(self) -> None:
        """The one place a rebinding was needed, and the reason this module exists."""
        self.assertIsNot(e.execute, v6_execution.execute)

    def test_the_zero_confirmation_rule_is_version_six_s(self) -> None:
        self.assertIs(e.require_zero_confirmation, v6_execution.require_zero_confirmation)


class ReceiptTest(unittest.TestCase):
    def _receipt(self, **overrides) -> r.Receipt:
        fields = {
            "transaction_id": bytes(range(32)),
            "kind": c.TRANSFER,
            "result_code": c.CODE_NUMBER["SUCCESS"],
            "fee_charged": 1_000,
            "issued_atomic": 0,
        }
        fields.update(overrides)
        return r.Receipt(**fields)

    def test_the_version_field_is_seven(self) -> None:
        raw = r.encode(self._receipt())
        self.assertEqual(int.from_bytes(raw[4:6], "big"), 7)

    def test_the_layout_is_unchanged(self) -> None:
        receipt = self._receipt()
        mine = r.encode(receipt)
        theirs = v6_receipt.encode(receipt)
        self.assertEqual(len(mine), len(theirs))
        self.assertEqual(mine[0:4], theirs[0:4])
        self.assertEqual(mine[6:], theirs[6:])
        self.assertEqual(
            [index for index in range(len(mine)) if mine[index] != theirs[index]],
            [5],
            "the version octet pair is the only difference, and it is one octet",
        )

    def test_a_version_six_receipt_is_refused(self) -> None:
        raw = v6_receipt.encode(self._receipt())
        with self.assertRaises(r.InvalidReceipt):
            r.decode(raw)

    def test_a_version_seven_receipt_is_refused_by_version_six(self) -> None:
        raw = r.encode(self._receipt())
        with self.assertRaises(v6_receipt.InvalidReceipt):
            v6_receipt.decode(raw)

    def test_a_round_trip_is_exact(self) -> None:
        receipt = self._receipt(kind=c.MINT_NODE, issued_atomic=57_430_000_000)
        self.assertEqual(r.decode(r.encode(receipt)), receipt)

    def test_the_consistency_rules_are_version_six_s(self) -> None:
        self.assertIs(r.require_consistent, v6_receipt.require_consistent)

    def test_a_failed_transaction_still_charges_no_fee(self) -> None:
        with self.assertRaises(r.InvalidReceipt):
            r.encode(self._receipt(result_code=c.CODE_NUMBER["REPLAY"]))

    def test_a_retired_kind_is_still_refused(self) -> None:
        for kind in c.RETIRED_KINDS:
            with self.assertRaises(r.InvalidReceipt):
                r.encode(self._receipt(kind=kind, fee_charged=0))


class ChainBindingTest(unittest.TestCase):
    """The version-six and version-seven chains are alternatives, not a sequence.

    The specification says a version-six transaction of any kind is a
    version-seven transaction of that kind **by shape** and belongs to a
    different chain **by binding**. Nothing about the bytes separates them; the
    chain ID inside every signed message does, and that is what this checks —
    over the identical genesis fields, so the only difference in play is the
    label and schema version the chain identity is derived under.
    """

    def setUp(self) -> None:
        self.signatures = trace.Signatures()
        self.ledger = Ledger.from_genesis(trace.genesis())
        self.version_six_chain = g.predecessor_chain_id(trace.genesis(), 6)
        self.raw = trace._register(
            self.signatures,
            self.ledger,
            trace.ALICE_IDENTITY,
            trace.ALICE_KEY,
            trace.ALICE_SIGNER_KEY,
            valid_until=trace.VALID_UNTIL,
        )

    def test_the_two_chain_identities_differ(self) -> None:
        self.assertNotEqual(self.ledger.chain_id, self.version_six_chain)

    def test_the_transaction_is_admitted_on_its_own_chain(self) -> None:
        admission = e.admit(self.raw, self.ledger.chain_id, self.signatures.oracle)
        self.assertTrue(admission.admitted)

    def test_the_same_bytes_are_refused_on_the_version_six_chain(self) -> None:
        admission = e.admit(self.raw, self.version_six_chain, self.signatures.oracle)
        self.assertEqual(admission.code, e.ADMISSION_NUMBER["WRONG_CHAIN"])
        self.assertIsNone(admission.transaction)


if __name__ == "__main__":
    unittest.main()
