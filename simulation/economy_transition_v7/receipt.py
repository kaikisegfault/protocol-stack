"""The 56-byte version-seven receipt.

The layout is version two's and every field, width, and consistency rule is
version six's. **One octet pair changes**: the version field reads `7`, which is
what makes a version-six reader presented with a version-seven receipt able to
tell that it is looking at a contract it does not know.

`require_consistent` is imported rather than restated, because the combinations
a conforming execution can never produce are stated over the transaction kinds
and the result codes, and version seven changes neither. A restatement here
would be a second copy of that table with nothing keeping the two equal.
"""

from __future__ import annotations

from simulation.economy_transition_v6.envelope import u8, u16, u64
from simulation.economy_transition_v6.receipt import (
    NON_ISSUING_KINDS,
    RECEIPT_BYTES,
    InvalidReceipt,
    Receipt,
    require_consistent,
)

from . import contract as c

__all__ = [
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
    """A version-six receipt is refused here, and the reverse also holds.

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
