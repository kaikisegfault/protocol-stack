"""The version-five transaction envelope: version four's, with kind 11 corrected.

Every byte of every kind is version four's, so this module encodes and decodes
by delegating to that package rather than by restating an envelope it does not
change. What it defines for itself is the one field whose meaning moved and the
sender derivation that field's correction requires.

Kind 11's 32-byte field at offset 80 is the **HUB identity hash**, and the
account being linked is the **sender**. The body stays 96 octets and kinds 11
and 12 still share a length, so the correction is invisible to a length check
and visible only to a decoder that dispatches on the kind byte — which is the
rule version two stated for exactly this case.

`sender_account_id` is the accepted `protocol-primitives-v1` derivation. No
earlier transition package needed it, because version five is the first
contract in which a signed message is built from the sender rather than from an
argument the caller supplies. That difference is the whole defect: a message
assembled from arguments can name an identity the transaction does not carry,
and one assembled from the transaction cannot.
"""

from __future__ import annotations

from dataclasses import replace

from simulation.economy_transition.merkle import digest
from simulation.economy_transition_v4 import envelope as v4
from simulation.economy_transition_v4.envelope import (
    MalformedTransaction,
    Transaction,
    expected_signed_length,
    signing_message,
    transaction_id,
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
    "expected_signed_length",
    "sender_account_id",
    "signed_bytes",
    "signing_message",
    "transaction_id",
    "u8",
    "u16",
    "u32",
    "u64",
    "unsigned_bytes",
]


def sender_account_id(transaction: Transaction) -> bytes:
    """`H(D("protocol-stack:v1:account") || 0x01 || sender_public_key)`.

    The accepted version-one derivation, restated rather than reimplemented:
    the digest construction is the same domain-separated SHA-256 every model
    uses, and no cryptographic primitive is written here.
    """
    if type(transaction.sender_public_key) is not bytes:
        raise MalformedTransaction("public key is not octets")
    if len(transaction.sender_public_key) != 32:
        raise MalformedTransaction("public key is not 32 octets")
    return digest(
        c.ACCOUNT_ID_LABEL,
        bytes([c.ACCOUNT_ID_DOMAIN]) + transaction.sender_public_key,
    )


def body_bytes(kind: int, body: dict) -> bytes:
    if kind == c.HUB_ADD_ADDRESS:
        return _add_address_body(body)
    return v4.body_bytes(kind, body)


def unsigned_bytes(transaction: Transaction) -> bytes:
    return v4.unsigned_bytes(_named_as_version_four(transaction))


def signed_bytes(transaction: Transaction, signature: bytes) -> bytes:
    return v4.signed_bytes(_named_as_version_four(transaction), signature)


def decode_signed(raw: bytes) -> tuple[Transaction, bytes]:
    """Admission step 1, with kind 11's 32-byte field read as an identity."""
    transaction, signature = v4.decode_signed(raw)
    if transaction.kind == c.HUB_ADD_ADDRESS:
        transaction = replace(
            transaction,
            body={
                "hub_identity_hash": transaction.body["account_id"],
                "hub_signature": transaction.body["hub_signature"],
            },
        )
    return transaction, signature


def _add_address_body(body: dict) -> bytes:
    return _octets(body["hub_identity_hash"], 32, "HUB identity hash") + _octets(
        body["hub_signature"], c.HUB_SIGNATURE_BYTES, "HUB signature"
    )


def _named_as_version_four(transaction: Transaction) -> Transaction:
    """The same 96 octets, under the field name version four's encoder knows.

    Expressing the encoding as a rename rather than as a second body table is
    what makes "the body stays 96 octets" structural instead of asserted: there
    is one encoder, and version five hands it the same bytes in the same order.
    """
    if transaction.kind != c.HUB_ADD_ADDRESS:
        return transaction
    return replace(
        transaction,
        body={
            "account_id": _octets(
                transaction.body["hub_identity_hash"], 32, "HUB identity hash"
            ),
            "hub_signature": transaction.body["hub_signature"],
        },
    )


def _octets(value: object, width: int, name: str) -> bytes:
    if type(value) is not bytes or len(value) != width:
        raise MalformedTransaction(f"{name} is not {width} octets")
    return value
