"""The 56-byte version-nine receipt.

The layout is version two's and every field and width is version six's. **Two
things change and they are exactly what version nine adds**: the version field
reads `9`, and `require_consistent` is restated over version nine's kind table.

Version nine adds a kind and no code, so the restatement is version eight's eight
rules with one row moved: **kind 22 issues**, because a pool mint moves units of
the asset out of the referral channel's `outstanding` and into a winner's escrow.
It is not fee-exempt — every mint in this contract charges, and version eight's
exemption was a founder answer about a cost a machine bears every hour to prove
uptime it is paid for, which collecting an award is not.
"""

from __future__ import annotations

from simulation.economy_transition_v6.envelope import MalformedTransaction, u8, u16, u64
from simulation.economy_transition_v6.receipt import (
    RECEIPT_BYTES,
    InvalidReceipt,
    Receipt,
)
from simulation.economy_transition_v8.receipt import (
    FEE_EXEMPT_KINDS,
    NON_ISSUING_KINDS,
)

from . import contract as c

__all__ = [
    "FEE_EXEMPT_KINDS",
    "InvalidReceipt",
    "NON_ISSUING_KINDS",
    "RECEIPT_BYTES",
    "Receipt",
    "decode",
    "encode",
    "require_consistent",
]


def encode(receipt: Receipt) -> bytes:
    require_consistent(receipt)
    raw = (
        c.RECEIPT_MAGIC
        + u16(c.RECEIPT_VERSION)
        + receipt.transaction_id
        + u8(receipt.kind)
        + u8(receipt.result_code)
        + u64(receipt.fee_charged)
        + u64(receipt.issued_atomic)
    )
    if len(raw) != RECEIPT_BYTES:
        raise InvalidReceipt("encoded receipt is not 56 octets")
    return raw


def decode(raw: bytes) -> Receipt:
    """A version-eight receipt is refused here, and the reverse also holds.

    The version field is the only octet pair that separates them, so refusing on
    it is the whole compatibility boundary for this artifact.
    """
    if len(raw) != RECEIPT_BYTES:
        raise InvalidReceipt("receipt is not 56 octets")
    if raw[0:4] != c.RECEIPT_MAGIC:
        raise InvalidReceipt("wrong magic")
    if int.from_bytes(raw[4:6], "big") != c.RECEIPT_VERSION:
        raise InvalidReceipt("wrong receipt version")
    receipt = Receipt(
        transaction_id=raw[6:38],
        kind=raw[38],
        result_code=raw[39],
        fee_charged=int.from_bytes(raw[40:48], "big"),
        issued_atomic=int.from_bytes(raw[48:56], "big"),
    )
    require_consistent(receipt)
    return receipt


def require_consistent(receipt: Receipt) -> None:
    """The combinations a conforming version-nine execution can never produce.

    `NON_ISSUING_KINDS` and `FEE_EXEMPT_KINDS` are version eight's own sets,
    imported rather than restated: kind 22 is in neither, so neither moves, and a
    kind that changed side would have to change in version eight's module and
    fail version eight's vectors first.
    """
    if type(receipt.transaction_id) is not bytes or len(receipt.transaction_id) != 32:
        raise MalformedTransaction("transaction ID is not 32 octets")
    if receipt.kind in c.RETIRED_KINDS:
        raise InvalidReceipt(f"kind {receipt.kind} is retired in version nine")
    if receipt.kind not in c.TRANSACTION_KINDS:
        raise InvalidReceipt(f"unknown transaction kind {receipt.kind}")
    if receipt.result_code not in c.RESULT_CODES:
        raise InvalidReceipt(f"unknown result code {receipt.result_code}")
    failed = receipt.result_code != c.CODE_NUMBER["SUCCESS"]
    if failed and receipt.fee_charged:
        raise InvalidReceipt("a failed transaction charges no fee")
    if failed and receipt.issued_atomic:
        raise InvalidReceipt("a failed transaction issues nothing")
    if receipt.kind in NON_ISSUING_KINDS and receipt.issued_atomic:
        raise InvalidReceipt(f"kind {receipt.kind} issues nothing")
    if receipt.kind in FEE_EXEMPT_KINDS and receipt.fee_charged:
        raise InvalidReceipt(f"kind {receipt.kind} is fee-exempt")
