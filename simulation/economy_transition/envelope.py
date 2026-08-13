"""The canonical version-two transaction envelope and its six kind bodies.

A signed transaction is `header(80) || body || trailer(16) || signature(64)`.
The header is the accepted version-one transfer's first 80 bytes and the trailer
its last 16, so the kind-1 instance reproduces the accepted 136-byte unsigned and
200-byte signed transfer exactly. Nothing here computes a signature: the model
carries one and never implements a cryptographic primitive.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from simulation.common.canonical import label_prefix

from . import contract as c


class MalformedTransaction(ValueError):
    """Admission step 1 refused the bytes. Shape only; no state is read."""


def u8(value: int) -> bytes:
    return _fixed(value, 1)


def u16(value: int) -> bytes:
    return _fixed(value, 2)


def u32(value: int) -> bytes:
    return _fixed(value, 4)


def u64(value: int) -> bytes:
    return _fixed(value, 8)


def _fixed(value: int, width: int) -> bytes:
    if type(value) is not int or isinstance(value, bool):
        raise MalformedTransaction(f"{value!r} is not an integer")
    if not 0 <= value < (1 << (8 * width)):
        raise MalformedTransaction(f"{value} does not fit u{8 * width}")
    return value.to_bytes(width, "big")


def _read(raw: bytes, offset: int, width: int) -> int:
    return int.from_bytes(raw[offset : offset + width], "big")


@dataclass(frozen=True)
class Transaction:
    """One decoded transaction. `body` holds the kind's named fields."""

    kind: int
    chain_id: bytes
    sender_public_key: bytes
    nonce: int
    body: dict[str, Any]
    fee_limit: int
    valid_until_height: int


def body_bytes(kind: int, body: dict[str, Any]) -> bytes:
    if kind == c.TRANSFER:
        return body["recipient_account_id"] + u64(body["amount_atomic"])
    if kind == c.PURCHASE_SEAT:
        return (
            u32(body["seat_id"])
            + body["biometric_identity_hash"]
            + body["purchaser_account_id"]
            + u8(1 if body["has_referrer"] else 0)
            + body["referrer_account_id"]
            + body["biometric_signature"]
        )
    if kind == c.ACTIVATE_SEAT:
        return u32(body["seat_id"]) + body["biometric_signature"]
    if kind == c.MINT_NODE:
        return u32(body["seat_id"])
    if kind == c.MINT_REFERRAL:
        return b""
    if kind == c.DIRECT_ISSUE:
        return (
            u8(body["channel_id"])
            + body["decision_id"]
            + body["beneficiary_account_id"]
            + u64(body["amount_atomic"])
            + body["authorization"]
        )
    raise MalformedTransaction(f"unknown transaction kind {kind}")


def unsigned_bytes(transaction: Transaction) -> bytes:
    if len(transaction.chain_id) != 32:
        raise MalformedTransaction("chain ID is not 32 octets")
    if len(transaction.sender_public_key) != 32:
        raise MalformedTransaction("public key is not 32 octets")
    header = (
        c.TRANSACTION_MAGIC
        + u16(c.ENVELOPE_SCHEMA_VERSION)
        + u8(transaction.kind)
        + transaction.chain_id
        + u8(c.SIGNATURE_SCHEME)
        + transaction.sender_public_key
        + u64(transaction.nonce)
    )
    if len(header) != c.HEADER_BYTES:
        raise MalformedTransaction("header is not 80 octets")
    trailer = u64(transaction.fee_limit) + u64(transaction.valid_until_height)
    return header + body_bytes(transaction.kind, transaction.body) + trailer


def signed_bytes(transaction: Transaction, signature: bytes) -> bytes:
    if len(signature) != c.SIGNATURE_BYTES:
        raise MalformedTransaction("signature is not 64 octets")
    return unsigned_bytes(transaction) + signature


def signing_message(unsigned: bytes) -> bytes:
    """The version-one construction, unchanged and deliberately not re-versioned."""
    return label_prefix(c.SIGN_LABEL) + unsigned


def transaction_id(signed: bytes) -> str:
    return hashlib.sha256(label_prefix(c.TX_ID_LABEL) + signed).hexdigest()


def expected_signed_length(kind: int) -> int:
    """Every kind is fixed-length, so this is a table lookup rather than math."""
    return (
        c.HEADER_BYTES + c.BODY_BYTES[kind] + c.TRAILER_BYTES + c.SIGNATURE_BYTES
    )


def decode_signed(raw: bytes) -> tuple[Transaction, bytes]:
    """Admission step 1. Shape only: no state is read and no value is judged.

    A bounded numeric field outside its range decodes here and is refused at
    execution, because admission produces no receipt and no transaction-root
    entry, so a range violation classified here would leave no canonical trace.
    """
    minimum = c.HEADER_BYTES + c.TRAILER_BYTES + c.SIGNATURE_BYTES
    if len(raw) < minimum:
        raise MalformedTransaction("shorter than an empty-bodied transaction")
    if raw[0:4] != c.TRANSACTION_MAGIC:
        raise MalformedTransaction("wrong magic")
    if _read(raw, 4, 2) != c.ENVELOPE_SCHEMA_VERSION:
        raise MalformedTransaction("wrong schema version")

    kind = raw[6]
    if kind not in c.TRANSACTION_KINDS:
        raise MalformedTransaction(f"unknown transaction kind {kind}")
    if raw[39] != c.SIGNATURE_SCHEME:
        raise MalformedTransaction("unknown signature scheme")

    if len(raw) != expected_signed_length(kind):
        raise MalformedTransaction("length is not the exact length this kind requires")
    body_end = len(raw) - c.TRAILER_BYTES - c.SIGNATURE_BYTES
    body = _decode_body(kind, raw[c.HEADER_BYTES : body_end])

    transaction = Transaction(
        kind=kind,
        chain_id=raw[7:39],
        sender_public_key=raw[40:72],
        nonce=_read(raw, 72, 8),
        body=body,
        fee_limit=_read(raw, body_end, 8),
        valid_until_height=_read(raw, body_end + 8, 8),
    )
    return transaction, raw[len(raw) - c.SIGNATURE_BYTES :]


def _decode_body(kind: int, raw: bytes) -> dict[str, Any]:
    if len(raw) != c.BODY_BYTES[kind]:
        raise MalformedTransaction("body is not this kind's fixed width")
    if kind == c.TRANSFER:
        return {
            "recipient_account_id": raw[0:32],
            "amount_atomic": _read(raw, 32, 8),
        }
    if kind == c.PURCHASE_SEAT:
        return _decode_purchase(raw)
    if kind == c.ACTIVATE_SEAT:
        return {"seat_id": _read(raw, 0, 4), "biometric_signature": raw[4:68]}
    if kind == c.MINT_NODE:
        return {"seat_id": _read(raw, 0, 4)}
    if kind == c.MINT_REFERRAL:
        return {}
    return {
        "channel_id": raw[0],
        "decision_id": raw[1:33],
        "beneficiary_account_id": raw[33:65],
        "amount_atomic": _read(raw, 65, 8),
        "authorization": raw[73:105],
    }


def _decode_purchase(raw: bytes) -> dict[str, Any]:
    flag = raw[68]
    if flag not in (0, 1):
        raise MalformedTransaction("has_referrer is not a canonical bool")
    referrer = raw[69:101]
    if flag == 0 and referrer != bytes(32):
        # A second encoding of "no referrer" is the non-minimal representation
        # protocol-primitives-v1 forbids.
        raise MalformedTransaction("absent referrer must encode as 32 zero octets")
    return {
        "seat_id": _read(raw, 0, 4),
        "biometric_identity_hash": raw[4:36],
        "purchaser_account_id": raw[36:68],
        "has_referrer": flag == 1,
        "referrer_account_id": referrer,
        "biometric_signature": raw[101:165],
    }
