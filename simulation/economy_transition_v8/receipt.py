"""The 56-byte version-eight receipt.

The layout is version two's and every field and width is version six's. **Two
things change and they are exactly what version eight adds**: the version field
reads `8`, and `require_consistent` is *restated* rather than imported.

Version seven could import that function because it changed neither the
transaction kind space nor the result code space, so version six's tables were
still the right ones to check against. Version eight changes both — two kinds
and twelve codes — so version six's table would refuse a conforming kind-20
receipt as an unknown kind and would accept a code no version can produce. The
restatement is the same eight rules over version eight's tables, with two rows
added:

* **kinds 20 and 21 issue nothing.** A response is evidence and a dispute is a
  judgment; neither moves a unit of the asset.
* **kind 20 charges no fee**, which is the founder answer of 2026-09-02 stated
  where a reader checks a receipt rather than only where one is produced. It is
  the second kind with that rule and the table now names both.
"""

from __future__ import annotations

from simulation.economy_transition_v6.envelope import MalformedTransaction, u8, u16, u64
from simulation.economy_transition_v6.receipt import (
    RECEIPT_BYTES,
    InvalidReceipt,
    Receipt,
)
from simulation.economy_transition_v6.receipt import (
    NON_ISSUING_KINDS as _V6_NON_ISSUING_KINDS,
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

# Version six's nine, plus the two version eight adds. Stated as an extension of
# the accepted set rather than as a fresh list, so a kind that changed side would
# have to change in version six's own module and fail version six's vectors.
NON_ISSUING_KINDS = frozenset(
    _V6_NON_ISSUING_KINDS | {c.CHALLENGE_RESPONSE, c.FILE_DISPUTE}
)

# The registration and the challenge response. A dispute is not here: a response
# is a machine answering an audit the chain demanded of it, and a dispute is a
# third party relaying someone else's judgment.
FEE_EXEMPT_KINDS = frozenset({c.HUB_REGISTER, c.ADDED_FEE_EXEMPT_KIND})


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
    """A version-seven receipt is refused here, and the reverse also holds.

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
    """The combinations a conforming version-eight execution can never produce."""
    if type(receipt.transaction_id) is not bytes or len(receipt.transaction_id) != 32:
        raise MalformedTransaction("transaction ID is not 32 octets")
    if receipt.kind in c.RETIRED_KINDS:
        raise InvalidReceipt(f"kind {receipt.kind} is retired in version eight")
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
