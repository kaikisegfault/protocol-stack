"""Admission, escrow resolution, the shared envelope checks, and dispatch.

This is the first module in the repository that **runs** a version-six
transition rather than encoding one. Everything recorded before it establishes
that values encode; nothing established that a transaction resolves an escrow,
charges a fee, advances a nonce, writes state atomically, and produces a
receipt.

**Two execution orders had to be derived, because the accepted contract admits
two readings of each and only one reading leaves the contract self-consistent.**
ADR 0045 records both and why each was chosen; they are repeated here because
the code is where a reader will look for them.

1. **`DEBIT_OVERFLOW` is returned at envelope check 8**, not at kind 1's step 5.
   Check 8 is "escrow balance is below what it must debit", and for a transfer
   what it must debit is `amount + fixed_fee`, which is exactly the sum kind 1's
   step 5 tests. Evaluating step 5 after check 8 would make check 8 undefined on
   an overflowing sum and would make code 7 unreachable in version six — while
   the specification lists exactly three unreachable frozen codes and does not
   list it.
2. **The zero-confirmation-field rule is an execution condition returning
   `UNAUTHORIZED`.** The specification places it at admission and names
   `MALFORMED_TRANSACTION`, and neither survives contact with the rest of the
   contract. Whether an operation requires a confirmation is a predicate over
   the escrow's stored posture, and the specification states twice that
   admission reads no state; and the admission and result code spaces are
   disjoint namespaces that share numbers, so result code `1` is `ZERO_AMOUNT`
   and no result code named `MALFORMED_TRANSACTION` exists to return. Dropping
   the rule would leave the malleability it exists to close — two byte strings
   with different transaction IDs and identical effects — so it is enforced
   where it can be evaluated, with the code version six assigns to a key the
   applicable rule refuses.

**No signature is ever computed here.** A `SignatureOracle` is a recorded table
of `(public key, message) -> signature`, so a signature presented over a
different message, or by a different key, simply is not in the table. That is
what lets the model exercise every `UNAUTHORIZED` path without implementing a
cryptographic primitive.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import contract as c
from .envelope import MalformedTransaction, Transaction, decode_signed, signing_message
from .envelope import transaction_id as derive_transaction_id
from .envelope import unsigned_bytes
from .identity import RegistryError
from .ledger import Ledger
from .receipt import Receipt

# Admission codes and result codes are disjoint namespaces that share numbers:
# admission `1` is `MALFORMED_TRANSACTION` and result `1` is `ZERO_AMOUNT`. They
# are looked up through separate tables so that one can never be read as the
# other, which is the confusion the second derived rule above turns on.
ADMISSION_NUMBER: dict[str, int] = {
    name: number for number, name in c.ADMISSION_CODES.items()
}

# Which body field names the escrow a scheme-2 kind acts on and charges.
SCHEME_TWO_FEE_FIELD: dict[int, str] = {
    c.ESCROW_CREATE: "fee_escrow_id",
    c.ESCROW_DELETE: "fee_escrow_id",
    c.SIGNER_ADD: "escrow_id",
    c.SIGNER_REVOKE: "escrow_id",
}


class SignatureOracle:
    """A recorded signature table. The model implements no cryptography.

    Verification is exact-match lookup on `(public key, message)`. A signature
    over a different message is absent and therefore invalid, which is the
    property every message-binding claim in the contract rests on.
    """

    def __init__(self) -> None:
        self._table: dict[tuple[bytes, bytes], bytes] = {}

    def record(self, public_key: bytes, message: bytes, signature: bytes) -> bytes:
        self._table[(public_key, message)] = signature
        return signature

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        return self._table.get((public_key, message)) == signature


@dataclass(frozen=True)
class Admission:
    """One raw input's admission outcome. A failure produces no receipt."""

    code: int | None
    transaction: Transaction | None = None
    transaction_id: bytes | None = None
    signature: bytes | None = None

    @property
    def admitted(self) -> bool:
        return self.code is None


@dataclass(frozen=True)
class Outcome:
    """One executed transaction's result, before it becomes a receipt."""

    result: str
    issued_atomic: int = 0
    fee_charged: int = 0

    @property
    def code(self) -> int:
        return c.CODE_NUMBER[self.result]

    @property
    def succeeded(self) -> bool:
        return self.result == "SUCCESS"


class Refused(Exception):
    """A transition condition refused. Carries the version-six code name."""

    def __init__(self, result: str) -> None:
        super().__init__(result)
        self.result = result


def admit(raw: bytes, chain_id: bytes, oracle: SignatureOracle) -> Admission:
    """Version one's four steps, unchanged in order and in meaning.

    Step 4 is unchanged by the second scheme, which is why the scheme byte
    selects a key rather than a verification rule: under both schemes the
    envelope signature verifies against the 32-byte header field, so admission
    reads no state in either case.
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

    Every non-success result performs no state write and charges no fee. The
    transitions are written to validate completely before writing anything, so
    atomicity is structural here rather than enforced by a rollback — and the
    trace checks it by requiring the state root to be unchanged across every
    failure.
    """
    from . import transitions

    try:
        escrow = _resolve(ledger, transaction)
        if transaction.kind != c.HUB_REGISTER:
            _envelope_checks(ledger, transaction, escrow)
        outcome = transitions.dispatch(ledger, transaction, escrow, oracle)
    except Refused as refusal:
        return Outcome(result=refusal.result)
    except RegistryError as refusal:
        return Outcome(result=refusal.code)
    return outcome


def receipt_for(
    transaction_id: bytes, transaction: Transaction, outcome: Outcome
) -> Receipt:
    return Receipt(
        transaction_id=transaction_id,
        kind=transaction.kind,
        result_code=outcome.code,
        fee_charged=outcome.fee_charged,
        issued_atomic=outcome.issued_atomic,
    )


def _resolve(ledger: Ledger, transaction: Transaction) -> bytes | None:
    """Which escrow acts, and which pays. A registration has neither.

    `SENDER_NOT_FOUND` is frozen and unreachable from here: a signer entry names
    an escrow, an escrow entry implies a version-one account entry, and the two
    are written and deleted together, so an escrow that resolves always exists.
    """
    if transaction.kind == c.HUB_REGISTER:
        return None
    if transaction.scheme == c.SCHEME_SIGNER:
        escrow = ledger.registry.escrow_of_signer(transaction.authority_public_key)
        if escrow not in ledger.registry.accounts:
            raise Refused("SENDER_NOT_FOUND")
        return escrow
    identity_hash = transaction.body["hub_identity_hash"]
    ledger.registry.require_identity(identity_hash, transaction.authority_public_key)
    named = transaction.body[SCHEME_TWO_FEE_FIELD[transaction.kind]]
    ledger.registry.require_owned(named, identity_hash)
    return named


def _envelope_checks(ledger: Ledger, transaction: Transaction, escrow: bytes) -> None:
    """Checks 2, 3, 5, 6, and 8, in version one's order and with its meanings.

    A registration is exempt from all of them but expiry, and the exemption is
    forced rather than chosen: its fee limit is required to be zero, so on any
    chain with a nonzero fixed fee a fee-limit check would refuse every
    registration and close the ecosystem to new members — which is the opposite
    of what fee exemption exists to guarantee. It has no escrow, so it has no
    nonce sequence and no balance to check.
    """
    if transaction.fee_limit < ledger.fixed_fee:
        raise Refused("FEE_LIMIT_TOO_LOW")
    _require_unexpired(ledger, transaction)
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


def _require_unexpired(ledger: Ledger, transaction: Transaction) -> None:
    if transaction.valid_until_height < ledger.height:
        raise Refused("EXPIRED")


def _debit_of(ledger: Ledger, transaction: Transaction) -> int:
    """What the acting escrow must cover: the fee, plus a transfer's amount.

    Computed in unbounded arithmetic so the sum can be tested against `u64`
    before it is compared to a balance. A C++20 implementation performs the same
    test with a checked add and reports the same code.
    """
    if transaction.kind in (c.TRANSFER, c.TRANSFER_VERIFIED):
        return ledger.fixed_fee + transaction.body["amount_atomic"]
    return ledger.fixed_fee


def require_zero_confirmation(field: bytes) -> None:
    """The confirmation field of an operation that requires none must be zero.

    Refused at execution rather than at admission, and with `UNAUTHORIZED`
    rather than the `MALFORMED_TRANSACTION` the specification names, for the two
    reasons this module's docstring gives: admission cannot read the posture the
    predicate needs, and the result-code space has no such name.
    """
    if field != bytes(c.HUB_SIGNATURE_BYTES):
        raise Refused("UNAUTHORIZED")
