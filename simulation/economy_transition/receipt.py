"""The 56-byte version-two receipt.

Version one's 47-byte layout is not extended in place. `ledger-transition-v1`
fixes it, and a reader that trusts the length would silently misparse a longer
one, so version two takes a new receipt version rather than a wider field.

Two fields are new. The transaction kind is present because result codes are now
produced by six transitions and a reader must interpret a code without
re-fetching the transaction. The issued atomic units are present because the
milestone is about a fixed maximum supply: a receipt that commits to the units a
transaction created makes conservation auditable per transaction.
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


# Issuance happens at the two mints and at direct issue. A transfer moves units
# that already exist, a purchase writes a seat record, and an activation starts a
# schedule: until a permission is minted its units do not exist and are not
# circulating, which is why the daily assignment issues nothing either.
NON_ISSUING_KINDS = frozenset({c.TRANSFER, c.PURCHASE_SEAT, c.ACTIVATE_SEAT})
