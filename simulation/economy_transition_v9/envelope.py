"""The version-nine canonical envelope and its one new body.

Version nine changes no framing. The 80-octet header, the 16-octet trailer, the
signature, the two signing labels, and the transaction identifier are version
one's and version six's, unchanged and deliberately not re-versioned: a label
names the artifact it derives, and none of those artifacts changed. The block
header **is** re-versioned, and it lives in `block.py` rather than here, because
a block header is not an envelope.

**No new domain-separated label is added.** Version six's `mint_message` already
binds `u8(transaction_kind)`, precisely so a confirmation obtained for one mint
cannot be replayed onto another, and the kind byte separates kind 22 from kinds
4, 5 and 18 with no further construction. The vectors require the four to differ
on identical remaining fields.

**What is restated here rather than imported is the dispatch**, because version
eight's decoder reads version eight's kind table and would refuse a kind-22
transaction as unknown. The framing is the subject of the compatibility claim,
so it is written where the claim is made and a vector requires a version-nine
kind-1 transfer to be byte-identical to version one's.

The one new body:

```text
kind 22  seat_id:u32 || destination_escrow_id:32 || hub_signature:64  100 octets
```

which is kind 4's body exactly, and that is the point rather than a coincidence:
a mint of a seat's award is authorized the way a mint of a seat's permissions is.
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
from simulation.economy_transition_v8.envelope import (
    _decode_body as _decode_carried_body,
    body_bytes as _carried_body_bytes,
    dispute_message,
)

from . import contract as c

__all__ = [
    "MalformedTransaction",
    "Transaction",
    "body_bytes",
    "decode_signed",
    "dispute_message",
    "expected_signed_length",
    "assert_agrees_with_version_six",
    "mint_message",
    "signed_bytes",
    "signing_message",
    "transaction_id",
    "unsigned_bytes",
]


def body_bytes(kind: int, body: dict[str, Any]) -> bytes:
    if kind == c.MINT_POOL:
        return (
            u32(body["seat_id"])
            + _octets(body["destination_escrow_id"], 32, "destination")
            + _octets(body["hub_signature"], 64, "HUB signature")
        )
    return _carried_body_bytes(kind, body)


def mint_message(
    chain_id: bytes,
    hub_identity_hash: bytes,
    kind: int,
    seat_id: int,
    destination_escrow_id: bytes,
    valid_until_height: int,
) -> bytes:
    """Version six's `mint-confirm` construction over a widened kind set.

    **It could not be imported, and the reason is worth stating rather than
    working around.** Version six's own function guards its `kind` argument
    against version six's `CONFIRMABLE_MINTS`, which has three members; version
    nine has four. The guard is a statement about version six's kind space and is
    correct there, so this restates the construction rather than defeating the
    guard or splicing a byte into version six's output.

    **A restatement is only safe if something keeps the two equal**, so
    `assert_agrees_with_version_six` requires this function to reproduce version
    six's output byte for byte on all three of its kinds, and a vector runs it.
    What version nine adds is the fourth kind byte and nothing else.
    """
    if kind not in c.CONFIRMABLE_MINTS:
        raise MalformedTransaction(f"kind {kind} is not a confirmable mint")
    return (
        label_prefix(c.MINT_CONFIRM_LABEL)
        + _octets(chain_id, 32, "chain ID")
        + _octets(hub_identity_hash, 32, "HUB identity hash")
        + u8(kind)
        + u32(seat_id)
        + _octets(destination_escrow_id, 32, "destination")
        + u64(valid_until_height)
    )


def assert_agrees_with_version_six() -> None:
    """Require the restated mint message to be version six's on its own kinds.

    Fixed arguments rather than random ones: the construction is a concatenation,
    so one input that varies every field separates it from any other ordering of
    the same fields, and a vector records the agreement rather than trusting it.
    """
    from simulation.economy_transition_v6 import contract as v6
    from simulation.economy_transition_v6 import messages

    chain_id = bytes(range(32))
    identity = bytes(range(32, 64))
    destination = bytes(range(64, 96))
    for kind in sorted(v6.CONFIRMABLE_MINTS):
        here = mint_message(chain_id, identity, kind, 7, destination, 4_321)
        there = messages.mint_message(
            chain_id, identity, kind, 7, destination, 4_321
        )
        if here != there:
            raise MalformedTransaction(
                f"the version-nine mint message for kind {kind} is not version six's"
            )


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
    """Version one's construction, unchanged three times over."""
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
            f"kind {kind} is retired and permanently unassigned in version nine"
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


def _decode_body(kind: int, raw: bytes) -> dict[str, Any]:
    if len(raw) != c.BODY_BYTES[kind]:
        raise MalformedTransaction("body is not this kind's fixed width")
    if kind == c.MINT_POOL:
        return {
            "seat_id": _read(raw, 0, 4),
            "destination_escrow_id": raw[4:36],
            "hub_signature": raw[36:100],
        }
    return _decode_carried_body(kind, raw)
