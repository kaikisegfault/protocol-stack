"""The version-eight canonical envelope and its two new bodies.

Version eight changes no framing. The 80-octet header, the 16-octet trailer, the
signature, the two signing labels, and the transaction identifier are version
one's and version six's, unchanged and deliberately not re-versioned: a label
names the artifact it derives, and none of those artifacts changed.

**What is restated here rather than imported is the dispatch**, because version
six's decoder reads version six's kind table and would refuse a kind-20
transaction as unknown. The framing is the subject of the compatibility claim,
so it is written where the claim is made and a vector requires a version-eight
kind-1 transfer to be byte-identical to version six's.

The two new bodies:

```text
kind 20  seat_id:u32 || challenge_height:u64 || answer:32              44 octets
kind 21  seat_id:u32 || cycle_window:u64 || slot_index:u8
         || reason_code:u8 || authority_signature:64                   78 octets
```
"""

from __future__ import annotations

from typing import Any

from simulation.common.canonical import label_prefix
from simulation.economy_transition.merkle import digest
from simulation.economy_transition_v6.envelope import (
    MalformedTransaction,
    Transaction,
    _decode_body as _decode_carried_body,
    _octets,
    _read,
    body_bytes as _carried_body_bytes,
    u8,
    u16,
    u32,
    u64,
)

from . import contract as c

__all__ = [
    "MalformedTransaction",
    "Transaction",
    "body_bytes",
    "decode_signed",
    "dispute_message",
    "expected_signed_length",
    "signed_bytes",
    "signing_message",
    "transaction_id",
    "unsigned_bytes",
]


def body_bytes(kind: int, body: dict[str, Any]) -> bytes:
    if kind == c.CHALLENGE_RESPONSE:
        return (
            u32(body["seat_id"])
            + u64(body["challenge_height"])
            + _octets(body["answer"], c.ANSWER_BYTES, "answer")
        )
    if kind == c.FILE_DISPUTE:
        return (
            u32(body["seat_id"])
            + u64(body["cycle_window"])
            + u8(body["slot_index"])
            + u8(body["reason_code"])
            + _octets(body["authority_signature"], 64, "authority signature")
        )
    return _carried_body_bytes(kind, body)


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
    """Version one's construction, unchanged twice over."""
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
            f"kind {kind} is retired and permanently unassigned in version eight"
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
    if kind == c.CHALLENGE_RESPONSE:
        return {
            "seat_id": _read(raw, 0, 4),
            "challenge_height": _read(raw, 4, 8),
            "answer": raw[12:44],
        }
    if kind == c.FILE_DISPUTE:
        return {
            "seat_id": _read(raw, 0, 4),
            "cycle_window": _read(raw, 4, 8),
            "slot_index": raw[12],
            "reason_code": raw[13],
            "authority_signature": raw[14:78],
        }
    return _decode_carried_body(kind, raw)


def dispute_message(
    chain_id: bytes,
    seat_id: int,
    cycle_window: int,
    slot_index: int,
    reason_code: int,
    valid_until_height: int,
) -> bytes:
    """What the dispute authority signs, and what a relayer cannot alter.

    The chain identity binds the dispute to one chain, `valid_until_height`
    bounds how long a signature may be held before it is relayed, and the reason
    code is bound even though it carries no protocol effect — so a relayer
    cannot restate the reason of a decision it did not make.
    """
    return (
        label_prefix(c.DISPUTE_LABEL)
        + _octets(chain_id, 32, "chain ID")
        + u32(seat_id)
        + u64(cycle_window)
        + u8(slot_index)
        + u8(reason_code)
        + u64(valid_until_height)
    )
