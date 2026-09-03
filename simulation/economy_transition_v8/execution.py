"""Admission, escrow resolution, the shared envelope checks, and dispatch.

Version seven's whole module is one rebound name, because version seven changes
no transaction. Version eight adds two, so **three things are restated here and
everything else is version six's own function object**:

* `Outcome`, because version eight's result space has forty-five codes and
  version six's `CODE_NUMBER` would raise on twelve of them. It is a subclass, so
  a carried transition's version-six `Outcome` and a new transition's
  version-eight one are the same shape and agree on every code version six
  defines — which `tests/simulation/economy_transition_v8_execution_test.py`
  requires rather than assumes.
* `admit`, because version six's decoder reads version six's kind table and
  would refuse a kind-20 transaction as unknown. The four steps, their order,
  and their meanings are unchanged.
* the shared envelope checks **for the one fee-exempt kind version eight adds**.
  Every other kind runs version six's `_envelope_checks` unchanged.

**The fee-exempt path is derived rather than chosen, and it is the one rule this
module had to derive.** The owner answered on 2026-09-02 that answering a
mandatory audit costs an operator nothing. The specification draws two encoding
consequences from that — a zero fee limit refused at admission, and a kept nonce
— and leaves a third to the execution model: what the acting escrow must cover.
Version six defines that as "the fee, plus a transfer's amount", and a kind-20
response is charged no fee, so its debit is zero and both checks stated over the
debit become vacuous. Leaving the debit at the fixed fee would refuse a response
from an escrow holding less than one fee, which is a balance an operator must
own in order to be paid — the exact cost the answer removes. `FEE_LIMIT_TOO_LOW`,
`DEBIT_OVERFLOW`, and `INSUFFICIENT_BALANCE` are therefore all unreachable for
kind 20, and the expiry and the two nonce conditions are not.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.economy_transition_v6.execution import (
    ADMISSION_NUMBER,
    SCHEME_TWO_FEE_FIELD,
    Admission,
    Outcome as OutcomeV6,
    Refused,
    SignatureOracle,
    require_zero_confirmation,
)
from simulation.economy_transition_v6.execution import (
    _envelope_checks,
    _resolve,
)
from simulation.economy_transition_v6.identity import RegistryError

from . import contract as c
from .envelope import (
    MalformedTransaction,
    Transaction,
    decode_signed,
    signing_message,
    transaction_id as derive_transaction_id,
    unsigned_bytes,
)
from .ledger import Ledger
from .receipt import Receipt

__all__ = [
    "ADMISSION_NUMBER",
    "SCHEME_TWO_FEE_FIELD",
    "Admission",
    "Outcome",
    "OutcomeV6",
    "Refused",
    "SignatureOracle",
    "admit",
    "execute",
    "receipt_for",
    "require_zero_confirmation",
]


@dataclass(frozen=True)
class Outcome(OutcomeV6):
    """Version six's three fields over version eight's forty-five-code space."""

    @property
    def code(self) -> int:
        return c.CODE_NUMBER[self.result]


def admit(raw: bytes, chain_id: bytes, oracle: SignatureOracle) -> Admission:
    """Version one's four steps, unchanged in order and in meaning.

    Only the decoder differs from version six's, and only because the kind table
    it reads has two more rows. Admission still reads no state, which is what
    makes the fee-limit rule of a fee-exempt kind an admission rule at all: it is
    a condition on the bytes rather than on a balance.
    """
    try:
        transaction, signature = decode_signed(raw)
    except MalformedTransaction:
        return Admission(code=ADMISSION_NUMBER["MALFORMED_TRANSACTION"])
    if transaction.chain_id != chain_id:
        return Admission(code=ADMISSION_NUMBER["WRONG_CHAIN"])
    message = signing_message(unsigned_bytes(transaction))
    if not oracle.verify(transaction.authority_public_key, message, signature):
        return Admission(code=ADMISSION_NUMBER["INVALID_SIGNATURE"])
    return Admission(
        code=None,
        transaction=transaction,
        transaction_id=bytes.fromhex(derive_transaction_id(raw)),
        signature=signature,
    )


def execute(ledger: Ledger, transaction: Transaction, oracle: SignatureOracle) -> Outcome:
    """Resolve the acting escrow, apply the shared checks, then the kind's own.

    Every non-success result performs no state write and charges no fee, and the
    two new transitions validate completely before writing anything, so atomicity
    stays structural — and the trace checks it by requiring the state root to be
    unchanged across every failure.
    """
    from . import transitions

    try:
        escrow = _resolve(ledger, transaction)
        if transaction.kind == c.ADDED_FEE_EXEMPT_KIND:
            assert escrow is not None
            _fee_exempt_envelope_checks(ledger, transaction, escrow)
        elif transaction.kind != c.HUB_REGISTER:
            _envelope_checks(ledger, transaction, escrow)
        outcome = transitions.dispatch(ledger, transaction, escrow, oracle)
    except Refused as refusal:
        return Outcome(result=refusal.result)
    except RegistryError as refusal:
        return Outcome(result=refusal.code)
    return outcome


def _fee_exempt_envelope_checks(
    ledger: Ledger, transaction: Transaction, escrow: bytes
) -> None:
    """Checks 3, 5, and 6 of version one's order. The other two are vacuous.

    Check 2 is the fee limit and does not run: the limit is required to be zero
    at admission, so comparing it to a nonzero fixed fee would refuse every
    conforming response. Checks 7 and 8 are stated over the debit, which is zero
    here, so neither can fire — a sum of zero never leaves `u64` and no balance
    is below it. They are omitted rather than written as conditions that can only
    be false, and the vectors record the two codes as unreachable for this kind.
    """
    if transaction.valid_until_height < ledger.height:
        raise Refused("EXPIRED")
    stored = ledger.nonce(escrow)
    if stored == c.MAX_U64:
        raise Refused("NONCE_EXHAUSTED")
    if transaction.nonce != stored + 1:
        raise Refused("NONCE_MISMATCH")


def receipt_for(
    transaction_id: bytes, transaction: Transaction, outcome: OutcomeV6
) -> Receipt:
    """The version-eight receipt. The dataclass is version six's; `encode` is not."""
    return Receipt(
        transaction_id=transaction_id,
        kind=transaction.kind,
        result_code=outcome.code,
        fee_charged=outcome.fee_charged,
        issued_atomic=outcome.issued_atomic,
    )
