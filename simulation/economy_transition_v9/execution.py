"""Admission, escrow resolution, the shared envelope checks, and dispatch.

**Two things are restated here and everything else is version eight's or version
six's own function object.**

* `Outcome`, because the type a transition returns must resolve a result name
  against *this* version's code space. Version nine's space is version eight's
  exactly — kind 22 reuses kind 4's ladder, so it adds no code — and the subclass
  is declared anyway, because a version that later did add one would otherwise
  inherit a lookup table that silently refused its own result.
* `admit`, because version eight's decoder reads version eight's kind table and
  would refuse a kind-22 transaction as unknown. The four steps, their order, and
  their meanings are unchanged.

**The fee-exempt path is version eight's, unchanged.** Kind 20 is still the one
exempt kind with an escrow, and kind 22 is not exempt: every mint in this
contract charges, and version eight's exemption was a founder answer about a cost
a machine bears every hour to prove uptime it is paid for, which collecting an
award is not.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.economy_transition_v6.execution import (
    ADMISSION_NUMBER,
    SCHEME_TWO_FEE_FIELD,
    Admission,
    Refused,
    SignatureOracle,
    require_zero_confirmation,
)
from simulation.economy_transition_v6.execution import _envelope_checks, _resolve
from simulation.economy_transition_v6.identity import RegistryError
from simulation.economy_transition_v8.execution import (
    Outcome as OutcomeV8,
    _fee_exempt_envelope_checks,
)

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
    "OutcomeV8",
    "Refused",
    "SignatureOracle",
    "admit",
    "execute",
    "receipt_for",
    "require_zero_confirmation",
]


@dataclass(frozen=True)
class Outcome(OutcomeV8):
    """Version six's three fields over version nine's code space."""

    @property
    def code(self) -> int:
        return c.CODE_NUMBER[self.result]


def admit(raw: bytes, chain_id: bytes, oracle: SignatureOracle) -> Admission:
    """Version one's four steps, unchanged in order and in meaning.

    Only the decoder differs from version eight's, and only because the kind
    table it reads has one more row. Admission still reads no state.
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


def execute(
    ledger: Ledger, transaction: Transaction, oracle: SignatureOracle
) -> Outcome:
    """Resolve the acting escrow, apply the shared checks, then the kind's own.

    Every non-success result performs no state write and charges no fee, and the
    new transition validates completely before writing anything, so atomicity
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


def receipt_for(
    transaction_id: bytes, transaction: Transaction, outcome: OutcomeV8
) -> Receipt:
    """The version-nine receipt. The dataclass is version six's; `encode` is not."""
    return Receipt(
        transaction_id=transaction_id,
        kind=transaction.kind,
        result_code=outcome.code,
        fee_charged=outcome.fee_charged,
        issued_atomic=outcome.issued_atomic,
    )
