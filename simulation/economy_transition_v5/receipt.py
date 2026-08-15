"""The 56-byte version-five receipt.

The layout is version two's and every consistency rule is version four's. Only
the version field moves, so that a version-four reader presented with a
version-five receipt can tell it is looking at a contract it does not know.
"""

from __future__ import annotations

from simulation.economy_transition_v4.receipt import (
    NON_ISSUING_KINDS,
    RECEIPT_BYTES,
    InvalidReceipt,
    Receipt,
    require_consistent,
)

from . import contract as c
from .envelope import u8, u16, u64

__all__ = [
    "NON_ISSUING_KINDS",
    "RECEIPT_BYTES",
    "InvalidReceipt",
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
