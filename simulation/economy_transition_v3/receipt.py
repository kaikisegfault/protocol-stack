"""The 56-byte version-three receipt.

The layout is version two's and the version field is not. No field moves and no
width changes, but the admissible kind and result-code ranges both widen, so a
version-two reader presented with a version-three receipt must be able to tell
that it is looking at a contract it does not know. Leaving the version at `2`
would make such a reader classify a kind-7 receipt as invalid rather than as
unknown, which is the misreading a version field exists to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import contract as c
from .envelope import MalformedTransaction, u8, u16, u64

RECEIPT_BYTES = 56


class InvalidReceipt(ValueError):
    """A receipt no execution could have produced."""


@dataclass(frozen=True)
class Receipt:
    transaction_id: bytes
    kind: int
    result_code: int
    fee_charged: int
    issued_atomic: int


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


def require_consistent(receipt: Receipt) -> None:
    """The four combinations a conforming execution can never produce."""
    if type(receipt.transaction_id) is not bytes or len(receipt.transaction_id) != 32:
        raise MalformedTransaction("transaction ID is not 32 octets")
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


# Issuance happens at the two node mints, the referral mint, and direct issue.
# A transfer moves units that already exist; a purchase writes a seat record; an
# activation starts a schedule; setting protection, adding a manager, and
# recording a HUB verification write authority and identity rather than value.
NON_ISSUING_KINDS = frozenset(
    {
        c.TRANSFER,
        c.PURCHASE_SEAT,
        c.ACTIVATE_SEAT,
        c.SET_MINT_BIOMETRIC,
        c.ADD_MANAGER,
        c.HUB_VERIFY,
    }
)
