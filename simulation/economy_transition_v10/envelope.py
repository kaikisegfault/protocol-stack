"""The version-ten envelope: version nine's framing, two bodies changed.

The 80-octet header, the 16-octet trailer, the signature, the two signing
labels, and the transaction identifier are version one's, unchanged. What moves
is two bodies:

```text
kind 10  hub_identity_hash:32 || first_signer_public_key:32 ||
         attesting_seat_id:u32 || attestation_signature:64            132 octets
kind 23  seat_id:u32 || machine_public_key:32 || build_digest:32 ||
         attestation_signature:64 || hub_signature:64                 196 octets
```

**The framing is restated rather than imported, and the reason is the same as
version nine's.** Version nine's decoder reads version nine's kind table and
would refuse kind 23 as unknown, and its length check would refuse a 132-octet
kind 10. A vector requires a version-ten kind-1 transfer to be byte-identical to
version one's, which is the compatibility claim the restatement must keep.
"""

from __future__ import annotations

from typing import Any

from simulation.common.canonical import label_prefix
from simulation.economy_transition.merkle import digest
from simulation.economy_transition_v6.envelope import (
    MalformedTransaction,
    Transaction,
    _octets,
    _read,
    u8,
    u16,
    u32,
    u64,
)
from simulation.economy_transition_v9 import envelope as v9envelope

from . import contract as c

__all__ = [
    "MalformedTransaction",
    "Transaction",
    "body_bytes",
    "decode_signed",
    "expected_signed_length",
    "signed_bytes",
    "signing_message",
    "transaction_id",
    "unsigned_bytes",
]


def body_bytes(kind: int, body: dict[str, Any]) -> bytes:
    if kind == c.HUB_REGISTER:
        return (
            _octets(body["hub_identity_hash"], 32, "HUB identity hash")
            + _octets(body["first_signer_public_key"], 32, "first signer key")
            + u32(body["attesting_seat_id"])
            + _octets(body["attestation_signature"], 64, "attestation signature")
        )
    if kind == c.REGISTER_MACHINE_KEY:
        return (
            u32(body["seat_id"])
            + _octets(body["machine_public_key"], 32, "machine public key")
            + _octets(body["build_digest"], c.BUILD_DIGEST_BYTES, "build digest")
            + _octets(body["attestation_signature"], 64, "attestation signature")
            + _octets(body["hub_signature"], 64, "HUB signature")
        )
    return v9envelope.body_bytes(kind, body)


def _decode_body(kind: int, raw: bytes) -> dict[str, Any]:
    if len(raw) != c.BODY_BYTES[kind]:
        raise MalformedTransaction("body is not this kind's fixed width")
    if kind == c.HUB_REGISTER:
        return {
            "hub_identity_hash": raw[0:32],
            "first_signer_public_key": raw[32:64],
            "attesting_seat_id": _read(raw, 64, 4),
            "attestation_signature": raw[68:132],
        }
    if kind == c.REGISTER_MACHINE_KEY:
        return {
            "seat_id": _read(raw, 0, 4),
            "machine_public_key": raw[4:36],
            "build_digest": raw[36:68],
            "attestation_signature": raw[68:132],
            "hub_signature": raw[132:196],
        }
    return v9envelope._decode_body(kind, raw)


def unsigned_bytes(transaction: Transaction) -> bytes:
    _octets(transaction.chain_id, 32, "chain ID")
    _octets(transaction.authority_public_key, 32, "authority public key")
    if transaction.scheme not in c.SIGNATURE_SCHEMES:
        raise MalformedTransaction(f"unknown signature scheme {transaction.scheme}")
    if c.KIND_SCHEME.get(transaction.kind) != transaction.scheme:
        raise MalformedTransaction("this kind does not permit this signature scheme")
    header = (
        c.TRANSACTION_MAGIC
        + u16(c.ENVELOPE_SCHEMA_VERSION)
        + u8(transaction.kind)
        + transaction.chain_id
        + u8(transaction.scheme)
        + transaction.authority_public_key
        + u64(transaction.nonce)
    )
    if len(header) != c.HEADER_BYTES:
        raise MalformedTransaction("header is not 80 octets")
    trailer = u64(transaction.fee_limit) + u64(transaction.valid_until_height)
    return header + body_bytes(transaction.kind, transaction.body) + trailer


def signed_bytes(transaction: Transaction, signature: bytes) -> bytes:
    return unsigned_bytes(transaction) + _octets(signature, 64, "signature")


def signing_message(unsigned: bytes) -> bytes:
    """Version one's construction, unchanged four times over."""
    return label_prefix(c.SIGN_LABEL) + unsigned


def transaction_id(signed: bytes) -> str:
    return digest(c.TX_ID_LABEL, signed).hex()


def expected_signed_length(kind: int) -> int:
    return c.HEADER_BYTES + c.BODY_BYTES[kind] + c.TRAILER_BYTES + c.SIGNATURE_BYTES


def decode_signed(raw: bytes) -> tuple[Transaction, bytes]:
    """Admission step 1. Shape only: no state is read and no value is judged."""
    minimum = c.HEADER_BYTES + c.TRAILER_BYTES + c.SIGNATURE_BYTES
    if len(raw) < minimum:
        raise MalformedTransaction("shorter than an empty-bodied transaction")
    if raw[0:4] != c.TRANSACTION_MAGIC:
        raise MalformedTransaction("wrong magic")
    if _read(raw, 4, 2) != c.ENVELOPE_SCHEMA_VERSION:
        raise MalformedTransaction("wrong schema version")

    kind = raw[6]
    if kind in c.RETIRED_KINDS:
        raise MalformedTransaction(
            f"kind {kind} is retired and permanently unassigned in version ten"
        )
    if kind not in c.TRANSACTION_KINDS:
        raise MalformedTransaction(f"unknown transaction kind {kind}")

    scheme = raw[39]
    if scheme not in c.SIGNATURE_SCHEMES:
        raise MalformedTransaction("unknown signature scheme")
    if c.KIND_SCHEME[kind] != scheme:
        raise MalformedTransaction("this kind does not permit this signature scheme")

    if len(raw) != expected_signed_length(kind):
        raise MalformedTransaction("length is not the exact length this kind requires")
    body_end = len(raw) - c.TRAILER_BYTES - c.SIGNATURE_BYTES
    body = _decode_body(kind, raw[c.HEADER_BYTES : body_end])

    nonce = _read(raw, 72, 8)
    fee_limit = _read(raw, body_end, 8)
    if kind == c.HUB_REGISTER:
        if nonce != 0:
            raise MalformedTransaction("a registration carries a zero nonce")
        if fee_limit != 0:
            raise MalformedTransaction(
                "a registration is fee-exempt and carries a zero fee limit"
            )
    if kind == c.CHALLENGE_RESPONSE and fee_limit != 0:
        raise MalformedTransaction(
            "a challenge response is fee-exempt and carries a zero fee limit"
        )

    transaction = Transaction(
        kind=kind,
        scheme=scheme,
        chain_id=raw[7:39],
        authority_public_key=raw[40:72],
        nonce=nonce,
        body=body,
        fee_limit=fee_limit,
        valid_until_height=_read(raw, body_end + 8, 8),
    )
    return transaction, raw[len(raw) - c.SIGNATURE_BYTES :]
