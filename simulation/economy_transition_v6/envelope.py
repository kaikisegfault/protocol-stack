"""The canonical version-six transaction envelope and its fourteen kind bodies.

A signed transaction is `header(80) || body || trailer(16) || signature(64)`.
The header is the accepted version-one transfer's first 80 bytes and the trailer
its last 16, so the kind-1 instance reproduces the accepted 136-byte unsigned and
200-byte signed transfer exactly. Nothing here computes a signature: the model
carries one and never implements a cryptographic primitive.

**The signature-scheme byte carries the second authorization mode.** Version one
fixes it at `1` and reads offset 40 as the sender's public key; version six reads
that field as an authority public key and lets the scheme say whose. Both schemes
verify the envelope signature against the header key, so admission still reads no
state — which is why the scheme selects a key rather than a verification rule.

Five kinds share a 96-octet body. A decoder therefore dispatches on the kind
byte, which is the rule version two stated for exactly this case; the kind byte
sits at offset 6 inside every signature preimage, so no signature crosses a kind.
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


def _octets(value: Any, width: int, name: str) -> bytes:
    if type(value) is not bytes or len(value) != width:
        raise MalformedTransaction(f"{name} is not {width} octets")
    return value


@dataclass(frozen=True)
class Transaction:
    """One decoded transaction. `body` holds the kind's named fields.

    `authority_public_key` is the header's 32-byte field. Under scheme 1 it is a
    signer key and the acting escrow is resolved from the signer entry; under
    scheme 2 it is an identity's HUB key and the body names the escrow.
    """

    kind: int
    scheme: int
    chain_id: bytes
    authority_public_key: bytes
    nonce: int
    body: dict[str, Any]
    fee_limit: int
    valid_until_height: int


def body_bytes(kind: int, body: dict[str, Any]) -> bytes:
    if kind == c.TRANSFER:
        return _octets(body["recipient_escrow_id"], 32, "recipient") + u64(
            body["amount_atomic"]
        )
    if kind == c.TRANSFER_VERIFIED:
        return (
            _octets(body["recipient_escrow_id"], 32, "recipient")
            + u64(body["amount_atomic"])
            + _octets(body["hub_signature"], 64, "HUB signature")
        )
    if kind == c.PURCHASE_SEAT:
        present = bool(body["has_referrer"])
        return (
            u32(body["seat_id"])
            + u8(1 if present else 0)
            + _octets(body["referrer_escrow_id"], 32, "referrer")
            + _octets(body["hub_signature"], 64, "HUB signature")
        )
    if kind == c.ACTIVATE_SEAT:
        return u32(body["seat_id"]) + _octets(
            body["hub_signature"], 64, "HUB signature"
        )
    if kind == c.MINT_NODE:
        return (
            u32(body["seat_id"])
            + _octets(body["destination_escrow_id"], 32, "destination")
            + _octets(body["hub_signature"], 64, "HUB signature")
        )
    if kind in (c.MINT_REFERRAL, c.MINT_VERIFIED_USER):
        return _octets(body["destination_escrow_id"], 32, "destination") + _octets(
            body["hub_signature"], 64, "HUB signature"
        )
    if kind == c.DIRECT_ISSUE:
        return (
            u8(body["channel_id"])
            + _octets(body["decision_id"], 32, "decision ID")
            + _octets(body["beneficiary_escrow_id"], 32, "beneficiary")
            + u64(body["amount_atomic"])
            + _octets(body["authorization"], 32, "authorization")
        )
    if kind == c.HUB_REGISTER:
        return (
            _octets(body["hub_identity_hash"], 32, "HUB identity hash")
            + _octets(body["first_signer_public_key"], 32, "first signer key")
            + _octets(body["verifier_signature"], 64, "verifier signature")
        )
    if kind == c.ESCROW_CREATE:
        return _octets(body["hub_identity_hash"], 32, "HUB identity hash") + _octets(
            body["fee_escrow_id"], 32, "fee escrow"
        )
    if kind == c.ESCROW_DELETE:
        return (
            _octets(body["hub_identity_hash"], 32, "HUB identity hash")
            + _octets(body["target_escrow_id"], 32, "target escrow")
            + _octets(body["fee_escrow_id"], 32, "fee escrow")
        )
    if kind == c.SIGNER_ADD:
        return (
            _octets(body["hub_identity_hash"], 32, "HUB identity hash")
            + _octets(body["escrow_id"], 32, "escrow")
            + _octets(body["signer_public_key"], 32, "signer key")
        )
    if kind == c.SIGNER_REVOKE:
        return (
            _octets(body["hub_identity_hash"], 32, "HUB identity hash")
            + _octets(body["escrow_id"], 32, "escrow")
            + _octets(body["signer_id"], 32, "signer ID")
        )
    if kind == c.SET_SECURITY_POSTURE:
        return (
            u8(1 if body["requires_confirmation"] else 0)
            + u64(body["min_amount_atomic"])
            + u32(body["exempt_slot_mask"])
            + _octets(body["hub_signature"], 64, "HUB signature")
        )
    raise MalformedTransaction(f"unknown transaction kind {kind}")


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
    """The version-one construction, unchanged and deliberately not re-versioned."""
    return label_prefix(c.SIGN_LABEL) + unsigned


def transaction_id(signed: bytes) -> str:
    return hashlib.sha256(label_prefix(c.TX_ID_LABEL) + signed).hexdigest()


def expected_signed_length(kind: int) -> int:
    """Every kind is fixed-length, so this is a table lookup rather than math."""
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
            f"kind {kind} is retired and permanently unassigned in version six"
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
        # A registration has no escrow yet, so it has no nonce sequence and no
        # fee. Both fields take their one canonical value; a second encoding of
        # "not applicable" is the non-minimal representation the primitives
        # forbid, and its replay protection is the identity check instead.
        if nonce != 0:
            raise MalformedTransaction("a registration carries a zero nonce")
        if fee_limit != 0:
            raise MalformedTransaction("a registration is fee-exempt and carries a zero fee limit")

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


def _decode_body(kind: int, raw: bytes) -> dict[str, Any]:
    if len(raw) != c.BODY_BYTES[kind]:
        raise MalformedTransaction("body is not this kind's fixed width")
    if kind == c.TRANSFER:
        return {"recipient_escrow_id": raw[0:32], "amount_atomic": _read(raw, 32, 8)}
    if kind == c.TRANSFER_VERIFIED:
        return {
            "recipient_escrow_id": raw[0:32],
            "amount_atomic": _read(raw, 32, 8),
            "hub_signature": raw[40:104],
        }
    if kind == c.PURCHASE_SEAT:
        return _decode_purchase(raw)
    if kind == c.ACTIVATE_SEAT:
        return {"seat_id": _read(raw, 0, 4), "hub_signature": raw[4:68]}
    if kind == c.MINT_NODE:
        return {
            "seat_id": _read(raw, 0, 4),
            "destination_escrow_id": raw[4:36],
            "hub_signature": raw[36:100],
        }
    if kind in (c.MINT_REFERRAL, c.MINT_VERIFIED_USER):
        return {"destination_escrow_id": raw[0:32], "hub_signature": raw[32:96]}
    if kind == c.HUB_REGISTER:
        return {
            "hub_identity_hash": raw[0:32],
            "first_signer_public_key": raw[32:64],
            "verifier_signature": raw[64:128],
        }
    if kind == c.ESCROW_CREATE:
        return {"hub_identity_hash": raw[0:32], "fee_escrow_id": raw[32:64]}
    if kind == c.ESCROW_DELETE:
        return {
            "hub_identity_hash": raw[0:32],
            "target_escrow_id": raw[32:64],
            "fee_escrow_id": raw[64:96],
        }
    if kind == c.SIGNER_ADD:
        return {
            "hub_identity_hash": raw[0:32],
            "escrow_id": raw[32:64],
            "signer_public_key": raw[64:96],
        }
    if kind == c.SIGNER_REVOKE:
        return {
            "hub_identity_hash": raw[0:32],
            "escrow_id": raw[32:64],
            "signer_id": raw[64:96],
        }
    if kind == c.SET_SECURITY_POSTURE:
        return _decode_posture(raw)
    return {
        "channel_id": raw[0],
        "decision_id": raw[1:33],
        "beneficiary_escrow_id": raw[33:65],
        "amount_atomic": _read(raw, 65, 8),
        "authorization": raw[73:105],
    }


def _decode_purchase(raw: bytes) -> dict[str, Any]:
    flag = raw[4]
    if flag not in (0, 1):
        raise MalformedTransaction("has_referrer is not a canonical bool")
    referrer = raw[5:37]
    if flag == 0 and referrer != bytes(32):
        # A second encoding of "no referrer" is the non-minimal representation
        # protocol-primitives-v1 forbids.
        raise MalformedTransaction("absent referrer must encode as 32 zero octets")
    return {
        "seat_id": _read(raw, 0, 4),
        "has_referrer": flag == 1,
        "referrer_escrow_id": referrer,
        "hub_signature": raw[37:101],
    }


def _decode_posture(raw: bytes) -> dict[str, Any]:
    flag = raw[0]
    if flag not in (0, 1):
        raise MalformedTransaction("requires_confirmation is not a canonical bool")
    mask = _read(raw, 9, 4)
    if mask > c.MAX_EXEMPT_SLOT_MASK:
        # A window has 24 slots, so the high 8 bits name nothing.
        raise MalformedTransaction("exempt slot mask sets a bit above slot 23")
    return {
        "requires_confirmation": flag == 1,
        "min_amount_atomic": _read(raw, 1, 8),
        "exempt_slot_mask": mask,
        "hub_signature": raw[13:77],
    }
