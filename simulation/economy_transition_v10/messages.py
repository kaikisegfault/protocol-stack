"""Version ten's three signed constructions and the approval lifetime rule.

```text
registration_message =
  D("protocol-stack:v10:hub-registration") ||
  chain_id || u32(attesting_seat_id) || hub_identity_hash || hub_public_key ||
  first_signer_public_key || u64(valid_until_height)

attestation_message =
  D("protocol-stack:v10:machine-attestation") ||
  chain_id || u32(seat_id) || machine_public_key || build_digest ||
  u64(valid_until_height)

approval_message =
  D("protocol-stack:v10:hub-approval") || approved_bytes
```

`approved_bytes` is the transaction's unsigned encoding with its 64-octet
`hub_signature` set to zero octets. **The approval binds everything the
transaction says**, so the escrow's nonce makes it single-use and no per-kind
field list exists to fall out of step with a body.
"""

from __future__ import annotations

from dataclasses import replace

from simulation.common.canonical import label_prefix
from simulation.economy_transition_v6.envelope import (
    MalformedTransaction,
    Transaction,
    _octets,
    u32,
    u64,
)

from . import contract as c
from .envelope import unsigned_bytes

__all__ = [
    "approval_lifetime_exceeded",
    "approval_message",
    "approved_bytes",
    "attestation_message",
    "carries_hub_proof",
    "registration_message",
]

NO_SIGNATURE = bytes(c.HUB_SIGNATURE_BYTES)


def registration_message(
    chain_id: bytes,
    attesting_seat_id: int,
    hub_identity_hash: bytes,
    hub_public_key: bytes,
    first_signer_public_key: bytes,
    valid_until_height: int,
) -> bytes:
    """Binding the attesting seat means one machine's signature cannot be
    presented as another's, so each registration counts against the limit of
    the machine that actually signed it."""
    return (
        label_prefix(c.REGISTRATION_LABEL)
        + _octets(chain_id, 32, "chain ID")
        + u32(attesting_seat_id)
        + _octets(hub_identity_hash, 32, "HUB identity hash")
        + _octets(hub_public_key, 32, "HUB public key")
        + _octets(first_signer_public_key, 32, "first signer key")
        + u64(valid_until_height)
    )


def attestation_message(
    chain_id: bytes,
    seat_id: int,
    machine_public_key: bytes,
    build_digest: bytes,
    valid_until_height: int,
) -> bytes:
    return (
        label_prefix(c.ATTESTATION_LABEL)
        + _octets(chain_id, 32, "chain ID")
        + u32(seat_id)
        + _octets(machine_public_key, 32, "machine public key")
        + _octets(build_digest, c.BUILD_DIGEST_BYTES, "build digest")
        + u64(valid_until_height)
    )


def approved_bytes(transaction: Transaction) -> bytes:
    """The unsigned transaction with its HUB field zeroed: what a person approves."""
    if transaction.kind not in c.APPROVAL_KINDS:
        raise MalformedTransaction(
            f"kind {transaction.kind} carries no body HUB approval"
        )
    blank = replace(
        transaction, body=dict(transaction.body) | {"hub_signature": NO_SIGNATURE}
    )
    return unsigned_bytes(blank)


def approval_message(transaction: Transaction) -> bytes:
    return label_prefix(c.APPROVAL_LABEL) + approved_bytes(transaction)


def carries_hub_proof(transaction: Transaction) -> bool:
    """Kinds 10, 13 to 16, and 23 always do; the body-carried kinds do when
    their HUB field is not 64 zero octets; nothing else does."""
    if transaction.kind in c.ALWAYS_PROVEN_KINDS:
        return True
    if transaction.kind in c.APPROVAL_KINDS:
        return transaction.body["hub_signature"] != NO_SIGNATURE
    return False


def approval_lifetime_exceeded(transaction: Transaction, height: int) -> bool:
    """The rule applied immediately after `EXPIRED`. The nonce makes an approval
    single-use; this makes a withheld one die."""
    return carries_hub_proof(transaction) and (
        transaction.valid_until_height > height + c.APPROVAL_LIFETIME_BLOCKS
    )
