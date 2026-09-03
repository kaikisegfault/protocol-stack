#!/usr/bin/env python3
"""Version eight delegates fourteen transitions and restates three things.

The claim this slice makes is narrow and it is the one worth guarding. Version
seven could import version six's `Outcome`, `admit`, `require_consistent`, and
whole dispatch table because it changed neither the kind space nor the code
space. Version eight changes both, so it restates exactly three of them — the
outcome, the admission, and the receipt's consistency rule — and delegates
everything else to version seven's own function object.

What is required here is therefore **object identity for the carried path** and
behaviour for the three restatements, plus the one property that makes the mixed
types safe: version six's code numbering and version eight's must agree on every
name version six defines, or a carried transition's outcome would report a
different number from a new one's.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from simulation.economy_transition_v6 import contract as c6
from simulation.economy_transition_v6 import execution as v6_execution
from simulation.economy_transition_v6.receipt import Receipt
from simulation.economy_transition_v7 import contract as c7
from simulation.economy_transition_v7 import transitions as v7_transitions
from simulation.economy_transition_v8 import contract as c
from simulation.economy_transition_v8 import execution as e
from simulation.economy_transition_v8 import receipt as r
from simulation.economy_transition_v8 import transitions as t
from simulation.economy_transition_v8 import trace
from simulation.economy_transition_v8.envelope import MalformedTransaction
from simulation.economy_transition_v8.ledger import Ledger


class DispatchTest(unittest.TestCase):
    """Two handlers of its own; everything else is version seven's function."""

    def test_the_carried_path_is_version_seven_s_own_dispatch(self) -> None:
        self.assertIs(t.VERSION_SEVEN_DISPATCH, v7_transitions.dispatch)

    def test_only_the_two_new_kinds_are_handled_here(self) -> None:
        added = set(c.TRANSACTION_KINDS) - set(c7.TRANSACTION_KINDS)
        self.assertEqual(added, {c.CHALLENGE_RESPONSE, c.FILE_DISPUTE})

    def test_the_two_new_kinds_are_scheme_one(self) -> None:
        for kind in (c.CHALLENGE_RESPONSE, c.FILE_DISPUTE):
            self.assertEqual(c.KIND_SCHEME[kind], c.SCHEME_SIGNER)


class OutcomeTest(unittest.TestCase):
    """The one property that makes two outcome types on one path safe."""

    def test_the_two_code_tables_agree_on_every_version_six_name(self) -> None:
        for name, number in c6.CODE_NUMBER.items():
            self.assertEqual(
                c.CODE_NUMBER[name], number, f"{name} moved between the versions"
            )

    def test_a_carried_outcome_reports_the_same_number_as_a_new_one(self) -> None:
        carried = v6_execution.Outcome(result="SUCCESS")
        mine = e.Outcome(result="SUCCESS")
        self.assertEqual(carried.code, mine.code)

    def test_the_twelve_added_codes_are_unreachable_from_version_six(self) -> None:
        for number, name in c.ADDED_IN_V8_RESULT_CODES.items():
            self.assertNotIn(name, c6.CODE_NUMBER)
            self.assertEqual(e.Outcome(result=name).code, number)
            with self.assertRaises(KeyError):
                v6_execution.Outcome(result=name).code


class AdmissionTest(unittest.TestCase):
    """Version one's four steps, over a kind table with two more rows."""

    def setUp(self) -> None:
        self.signatures = trace.Signatures()
        self.ledger = Ledger.from_genesis(trace.genesis())

    def _response(self, fee_limit: int) -> bytes:
        from simulation.economy_transition_v8.envelope import (
            Transaction,
            signed_bytes,
            signing_message,
            unsigned_bytes,
        )

        transaction = Transaction(
            kind=c.CHALLENGE_RESPONSE,
            scheme=c.SCHEME_SIGNER,
            chain_id=self.ledger.chain_id,
            authority_public_key=trace.ALICE_SIGNER_KEY,
            nonce=1,
            body={
                "seat_id": 0,
                "challenge_height": 1,
                "answer": bytes(c.ANSWER_BYTES),
            },
            fee_limit=fee_limit,
            valid_until_height=trace.VALID_UNTIL,
        )
        unsigned = unsigned_bytes(transaction)
        return signed_bytes(
            transaction,
            self.signatures.sign(
                trace.ALICE_SIGNER_KEY, signing_message(unsigned)
            ),
        )

    def test_a_response_with_a_zero_fee_limit_is_admitted(self) -> None:
        admission = e.admit(
            self._response(0), self.ledger.chain_id, self.signatures.oracle
        )
        self.assertTrue(admission.admitted)

    def test_a_response_with_a_nonzero_fee_limit_is_malformed(self) -> None:
        admission = e.admit(
            self._response(trace.FIXED_FEE),
            self.ledger.chain_id,
            self.signatures.oracle,
        )
        self.assertEqual(
            admission.code, e.ADMISSION_NUMBER["MALFORMED_TRANSACTION"]
        )

    def test_a_nonzero_fee_limit_is_refused_by_the_decoder_itself(self) -> None:
        from simulation.economy_transition_v8.envelope import decode_signed

        with self.assertRaises(MalformedTransaction):
            decode_signed(self._response(trace.FIXED_FEE))


class ReceiptTest(unittest.TestCase):
    """Two octets, two more non-issuing kinds, and one more fee-exempt kind."""

    def _receipt(self, kind: int, fee: int, issued: int, code: str = "SUCCESS"):
        return Receipt(
            transaction_id=bytes(range(32)),
            kind=kind,
            result_code=c.CODE_NUMBER[code],
            fee_charged=fee,
            issued_atomic=issued,
        )

    def test_the_version_field_is_eight(self) -> None:
        raw = r.encode(self._receipt(c.FILE_DISPUTE, trace.FIXED_FEE, 0))
        self.assertEqual(int.from_bytes(raw[4:6], "big"), 8)

    def test_the_two_new_kinds_are_non_issuing(self) -> None:
        for kind in (c.CHALLENGE_RESPONSE, c.FILE_DISPUTE):
            self.assertIn(kind, r.NON_ISSUING_KINDS)
            with self.assertRaises(r.InvalidReceipt):
                r.encode(self._receipt(kind, 0, 1))

    def test_the_challenge_response_is_fee_exempt_and_the_dispute_is_not(self) -> None:
        self.assertEqual(r.FEE_EXEMPT_KINDS, {c.HUB_REGISTER, c.CHALLENGE_RESPONSE})
        with self.assertRaises(r.InvalidReceipt):
            r.encode(self._receipt(c.CHALLENGE_RESPONSE, trace.FIXED_FEE, 0))
        r.encode(self._receipt(c.FILE_DISPUTE, trace.FIXED_FEE, 0))

    def test_the_added_codes_are_encodable_and_version_seven_refuses_them(self) -> None:
        from simulation.economy_transition_v7.receipt import (
            require_consistent as v7_require,
        )

        for name in c.ADDED_IN_V8_RESULT_CODES.values():
            receipt = self._receipt(c.CHALLENGE_RESPONSE, 0, 0, code=name)
            r.encode(receipt)
            with self.assertRaises(Exception):
                v7_require(receipt)

    def test_a_version_seven_receipt_is_refused(self) -> None:
        from simulation.economy_transition_v7.receipt import encode as v7_encode

        raw = v7_encode(self._receipt(1, trace.FIXED_FEE, 0))
        with self.assertRaises(r.InvalidReceipt):
            r.decode(raw)


if __name__ == "__main__":
    unittest.main()
