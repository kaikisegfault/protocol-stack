"""The version-nine application block header and the identifier over it.

It lives in the contract half rather than beside block execution because it is a
canonical encoding: what a block header *is* belongs with the state keys and the
genesis bytes, and what a block *does* belongs with the transition. Version
eight's model imports version one's header from its block module for the same
reason version eight did not need one of its own — the bytes had not changed.
Version nine's have.

**The timestamp is inserted after the height rather than appended**, and the
schema version changes with it. Appending would have kept every existing offset
identical, which is a hazard rather than a benefit: a decoder that read the
length loosely would parse a version-nine header as a version-one header with
eight trailing octets and agree with itself about every field. Moving the offsets
makes a mis-versioned decode fail at the first comparison.

**The block identifier is re-versioned** because it derives a different artifact.
Every version through eight kept `protocol-stack:v1:block-id`, and each was
right to: the bytes it hashed were version one's.
"""

from __future__ import annotations

from simulation.economy_transition.merkle import digest
from simulation.economy_transition_v6.block import BLOCK_MAGIC
from simulation.economy_transition_v6.envelope import (
    MalformedTransaction,
    u16,
    u32,
    u64,
)

from . import contract as c

__all__ = [
    "BLOCK_MAGIC",
    "block_header",
    "block_id",
    "predecessor_block_id",
]


def block_header(
    chain_id: bytes,
    height: int,
    timestamp: int,
    previous_state_root: str,
    transaction_root: str,
    resulting_state_root: str,
    transaction_count: int,
) -> bytes:
    """Exactly `BLOCK_HEADER_BYTES` octets, or nothing at all."""
    if not c.MIN_TIMESTAMP_MILLIS <= timestamp <= c.MAX_TIMESTAMP_MILLIS:
        raise MalformedTransaction(
            f"timestamp {timestamp} is outside calendar-v1's accepted range"
        )
    raw = (
        BLOCK_MAGIC
        + u16(c.BLOCK_HEADER_SCHEMA_VERSION)
        + _octets(chain_id, 32, "chain ID")
        + u64(height)
        + u64(timestamp)
        + _root(previous_state_root, "previous state root")
        + _root(transaction_root, "transaction root")
        + _root(resulting_state_root, "resulting state root")
        + u32(transaction_count)
    )
    if len(raw) != c.BLOCK_HEADER_BYTES:
        raise MalformedTransaction(
            f"block header is not {c.BLOCK_HEADER_BYTES} octets"
        )
    return raw


def block_id(header: bytes) -> str:
    if len(header) != c.BLOCK_HEADER_BYTES:
        raise MalformedTransaction("a block identifier is taken over a whole header")
    return digest(c.BLOCK_ID_LABEL, header).hex()


def predecessor_block_id(header: bytes) -> str:
    """The same octets under version one's label, for the non-collision claim.

    A version-nine header is 154 octets and version one's is 146, so no earlier
    identifier can be taken over these bytes at all. The comparison is recorded
    anyway, because distinct labels are strings rather than a chain and each
    non-collision is required separately.
    """
    return digest("protocol-stack:v1:block-id", header).hex()


def _octets(value: bytes, width: int, name: str) -> bytes:
    if type(value) is not bytes or len(value) != width:
        raise MalformedTransaction(f"{name} is not {width} octets")
    return value


def _root(value: str, name: str) -> bytes:
    raw = bytes.fromhex(value)
    return _octets(raw, 32, name)
