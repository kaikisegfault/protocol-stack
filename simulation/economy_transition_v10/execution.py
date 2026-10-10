"""Admission, escrow resolution, the shared envelope checks, and dispatch.

**Three things are restated here, and everything else is version six's or
version eight's own function object.**

* `Outcome`, because a transition's result must resolve against version ten's
  fifty-code space, and five of those codes are new.
* `admit`, because version nine's decoder reads version nine's kind table and
  would refuse kind 23 as unknown and a 132-octet kind 10 as the wrong length.
  The four steps, their order, and their meanings are unchanged.
* the shared envelope checks, because the approval lifetime rule is applied
  **immediately after `EXPIRED`**, which falls inside version six's sequence
  rather than before or after it. The other five checks and their order are
  version six's: the fee limit, the expiry, the nonce pair, and the debit pair.

**The lifetime rule reads the transaction, never the state**, so where it sits
among the envelope checks decides only which refusal a transaction that fails
two of them receives. Placing it straight after the expiry keeps the two rules
about a transaction's validity window together, and ahead of every check that
reads the escrow.

The fee-exempt kind keeps version eight's checks. A challenge response carries
no HUB proof, so the lifetime rule never governs it.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.economy_transition_v6.execution import (
    ADMISSION_NUMBER,
    SCHEME_TWO_FEE_FIELD,
    Admission,
    Refused,
    SignatureOracle,
    _debit_of,
    _resolve,
    require_zero_confirmation,
)
from simulation.economy_transition_v6.identity import RegistryError
from simulation.economy_transition_v8.execution import _fee_exempt_envelope_checks
from simulation.economy_transition_v9.execution import Outcome as OutcomeV9

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
from .messages import approval_lifetime_exceeded
from .receipt import Receipt

__all__ = [
    "ADMISSION_NUMBER",
    "SCHEME_TWO_FEE_FIELD",
    "Admission",
    "Outcome",
    "Refused",
    "SignatureOracle",
    "admit",
    "execute",
    "receipt_for",
    "require_fresh",
    "require_zero_confirmation",
]


@dataclass(frozen=True)
class Outcome(OutcomeV9):
    """Version six's three fields over version ten's fifty-code space."""

    @property
    def code(self) -> int:
        return c.CODE_NUMBER[self.result]


def admit(raw: bytes, chain_id: bytes, oracle: SignatureOracle) -> Admission:
    """Version one's four steps, unchanged in order and in meaning."""
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

    Every refusal writes nothing and charges nothing. The two new transitions
    validate completely before writing, so atomicity stays structural, and the
    block checks it by requiring the root to be unchanged across every refusal.
    """
    from . import transitions

    try:
        escrow = _resolve(ledger, transaction)
        if transaction.kind == c.ADDED_FEE_EXEMPT_KIND:
            assert escrow is not None
            _fee_exempt_envelope_checks(ledger, transaction, escrow)
        elif transaction.kind != c.HUB_REGISTER:
            assert escrow is not None
            _envelope_checks(ledger, transaction, escrow)
        outcome = transitions.dispatch(ledger, transaction, escrow, oracle)
    except Refused as refusal:
        return Outcome(result=refusal.result)
    except RegistryError as refusal:
        return Outcome(result=refusal.code)
    return Outcome(
        result=outcome.result,
        issued_atomic=outcome.issued_atomic,
        fee_charged=outcome.fee_charged,
    )


def require_fresh(ledger: Ledger, transaction: Transaction) -> None:
    """`EXPIRED`, then the approval lifetime rule, as one pair.

    A registration has no escrow and runs only this pair before its own
    conditions. Every other kind runs it inside the shared envelope checks.
    """
    if transaction.valid_until_height < ledger.height:
        raise Refused("EXPIRED")
    if approval_lifetime_exceeded(transaction, ledger.height):
        raise Refused("APPROVAL_LIFETIME_EXCEEDED")


def _envelope_checks(ledger: Ledger, transaction: Transaction, escrow: bytes) -> None:
    """Version six's checks, with the lifetime rule straight after the expiry."""
    if transaction.fee_limit < ledger.fixed_fee:
        raise Refused("FEE_LIMIT_TOO_LOW")
    require_fresh(ledger, transaction)
    stored = ledger.nonce(escrow)
    if stored == c.MAX_U64:
        raise Refused("NONCE_EXHAUSTED")
    if transaction.nonce != stored + 1:
        raise Refused("NONCE_MISMATCH")
    debit = _debit_of(ledger, transaction)
    if debit > c.MAX_U64:
        raise Refused("DEBIT_OVERFLOW")
    if ledger.balance(escrow) < debit:
        raise Refused("INSUFFICIENT_BALANCE")


def receipt_for(
    transaction_id: bytes, transaction: Transaction, outcome: Outcome
) -> Receipt:
    """The version-ten receipt. The dataclass is version six's; `encode` is not."""
    return Receipt(
        transaction_id=transaction_id,
        kind=transaction.kind,
        result_code=outcome.code,
        fee_charged=outcome.fee_charged,
        issued_atomic=outcome.issued_atomic,
    )
