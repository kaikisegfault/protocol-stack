"""The version-seven economy key space, its tree, and the version-seven root.

Version seven's key space is version six's with entry kind 7 removed and entry
kind 17 — the recovery pool — added, and with one value encoding extended: the
cycle assignment record gains the five amounts that cycle absorbed from the
pool.

**Everything else is imported rather than restated.** Every key builder and
value encoder version six accepted is re-exported here unchanged, so a width
that moved would have to move in version six's accepted module and would fail
version six's own vectors first.

The three entry-shape rules are version six's: a key is `u8(entry_kind)`
followed by fixed-width big-endian fields, unsigned lexicographic key order is
total, and a leaf preimage uses the accepted `bytes` primitive for both halves.
"""

from __future__ import annotations

from typing import Any

from simulation.economy_transition.merkle import digest, root
from simulation.economy_transition_v3.state import bit_is_set, bitmap, bitmap_bytes
from simulation.economy_transition_v6.envelope import MalformedTransaction, u16, u32, u64
from simulation.economy_transition_v6.state import (
    channel_key,
    channel_value,
    cycle_assignment_key,
    direct_decision_key,
    escrow_key,
    escrow_value,
    hub_identity_key,
    hub_identity_value,
    referral_balance_key,
    referral_balance_value,
    seat_key,
    seat_value,
    signer_key,
    signer_value,
    typed_custody_key,
    typed_custody_value,
    unreferred_pool_key,
    unreferred_pool_value,
    verified_user_counter_key,
    verified_user_counter_value,
    verified_user_key,
    verified_user_value,
    verifier_key_key,
    verifier_key_value,
)
from simulation.economy_transition_v6.state import u8

from . import contract as c

__all__ = [
    "bit_is_set",
    "bitmap",
    "bitmap_bytes",
    "channel_key",
    "channel_value",
    "cycle_assignment_key",
    "cycle_assignment_value",
    "decode_cycle_assignment_value",
    "direct_decision_key",
    "escrow_key",
    "escrow_value",
    "hub_identity_key",
    "hub_identity_value",
    "InvalidStateEntry",
    "recovery_pool_key",
    "recovery_pool_value",
    "decode_recovery_pool_value",
    "referral_balance_key",
    "referral_balance_value",
    "seat_key",
    "seat_value",
    "signer_key",
    "signer_value",
    "typed_custody_key",
    "typed_custody_value",
    "unreferred_pool_key",
    "unreferred_pool_value",
    "verified_user_counter_key",
    "verified_user_counter_value",
    "verified_user_key",
    "verified_user_value",
    "verifier_key_key",
    "verifier_key_value",
]


class InvalidStateEntry(ValueError):
    """A key or value that no transition could have written."""


# --- the recovery pool ------------------------------------------------------


def recovery_pool_key() -> bytes:
    """One octet. Exactly one such entry exists on any chain."""
    return u8(c.RECOVERY_POOL_ENTRY)


def recovery_pool_value(legs: dict[int, int]) -> bytes:
    """The five Founder Node legs, in channel order 0 through 4.

    A dictionary rather than a tuple, so a caller cannot silently transpose two
    legs whose amounts happen to be interchangeable at the moment it is called.
    """
    if set(legs) != set(c.RECOVERY_POOL_LEGS):
        raise InvalidStateEntry("the recovery pool carries exactly the five node legs")
    return b"".join(u64(legs[channel]) for channel in c.RECOVERY_POOL_LEGS)


def decode_recovery_pool_value(raw: bytes) -> dict[int, int]:
    width = 8 * len(c.RECOVERY_POOL_LEGS)
    if len(raw) != width:
        raise InvalidStateEntry("the recovery pool value is not its fixed width")
    return {
        channel: int.from_bytes(raw[8 * index : 8 * index + 8], "big")
        for index, channel in enumerate(c.RECOVERY_POOL_LEGS)
    }


# --- the extended cycle assignment record -----------------------------------


def cycle_assignment_value(
    share_per_winner_atomic: int,
    reallocated_count: int,
    winner_count: int,
    in_scope_count: int,
    bitmap_bits: int,
    pool_absorbed: dict[int, int],
    accrued_bitmap: bytes,
    winner_bitmap: bytes,
) -> bytes:
    """Version three's record with the five absorbed amounts appended to its
    fixed part.

    The absorbed amount is recorded rather than the per-winner share, because
    the residual a cycle returns to the pool is `absorbed - winner_count *
    (absorbed // winner_count)` and a share alone cannot express it. It is also
    the same shape as the reallocation, which records two counts and derives its
    share.
    """
    expected = bitmap_bytes(bitmap_bits)
    if len(accrued_bitmap) != expected or len(winner_bitmap) != expected:
        raise InvalidStateEntry("a bitmap is not the width its bit count implies")
    if set(pool_absorbed) != set(c.RECOVERY_POOL_LEGS):
        raise InvalidStateEntry("the absorbed amounts are exactly the five node legs")
    if winner_count == 0 and any(pool_absorbed[leg] for leg in c.RECOVERY_POOL_LEGS):
        raise InvalidStateEntry("a cycle with no winner absorbed a nonzero amount")
    return (
        u64(share_per_winner_atomic)
        + u32(reallocated_count)
        + u32(winner_count)
        + u32(in_scope_count)
        + u32(bitmap_bits)
        + b"".join(u64(pool_absorbed[channel]) for channel in c.RECOVERY_POOL_LEGS)
        + accrued_bitmap
        + winner_bitmap
    )


def decode_cycle_assignment_value(raw: bytes) -> dict[str, Any]:
    fixed = c.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES
    if len(raw) < fixed:
        raise InvalidStateEntry("cycle assignment is shorter than its fixed part")
    bits = int.from_bytes(raw[20:24], "big")
    width = bitmap_bytes(bits)
    if len(raw) != fixed + 2 * width:
        raise InvalidStateEntry("cycle assignment length disagrees with its bit count")
    winner_count = int.from_bytes(raw[12:16], "big")
    absorbed = {
        channel: int.from_bytes(raw[24 + 8 * index : 32 + 8 * index], "big")
        for index, channel in enumerate(c.RECOVERY_POOL_LEGS)
    }
    if winner_count == 0 and any(absorbed.values()):
        raise InvalidStateEntry("a cycle with no winner absorbed a nonzero amount")
    return {
        "share_per_winner_atomic": int.from_bytes(raw[0:8], "big"),
        "reallocated_count": int.from_bytes(raw[8:12], "big"),
        "winner_count": winner_count,
        "in_scope_count": int.from_bytes(raw[16:20], "big"),
        "bitmap_bits": bits,
        "pool_absorbed": absorbed,
        "accrued_bitmap": raw[fixed : fixed + width],
        "winner_bitmap": raw[fixed + width : fixed + 2 * width],
    }


# --- the tree and the root --------------------------------------------------


def entry_leaf(key: bytes, value: bytes) -> bytes:
    """`bytes(key) || bytes(value)`, the accepted length-prefixed primitive."""
    return u32(len(key)) + key + u32(len(value)) + value


def economy_root(entries: dict[bytes, bytes]) -> bytes:
    ordered = ordered_entries(entries)
    return root(
        [entry_leaf(key, value) for key, value in ordered], c.ECONOMY_TREE_PREFIX
    )


def ordered_entries(entries: dict[bytes, bytes]) -> list[tuple[bytes, bytes]]:
    """Unsigned lexicographic key order, with every key validated for shape."""
    for key, value in entries.items():
        require_entry_shape(key, value)
    return sorted(entries.items(), key=lambda item: item[0])


def require_entry_shape(key: bytes, value: bytes) -> None:
    if not key:
        raise InvalidStateEntry("empty economy key")
    kind = key[0]
    if kind in c.RETIRED_ENTRY_KINDS:
        raise InvalidStateEntry(
            f"entry kind {kind} is retired and permanently unassigned in version seven"
        )
    if kind not in c.ENTRY_KINDS:
        raise InvalidStateEntry(f"unknown economy entry kind {kind}")
    if len(key) != c.ENTRY_KEY_BYTES[kind]:
        raise InvalidStateEntry(f"entry kind {kind} key is not its fixed width")
    expected = c.ENTRY_VALUE_BYTES[kind]
    if expected is None:
        decode_cycle_assignment_value(value)
        return
    if len(value) != expected:
        raise InvalidStateEntry(f"entry kind {kind} value is not its fixed width")
    if kind == c.RECOVERY_POOL_ENTRY:
        decode_recovery_pool_value(value)


def accounts_root(accounts: list[tuple[bytes, int, int]]) -> bytes:
    """The accepted version-one accounts tree, entry-for-entry unchanged."""
    leaves = []
    previous: bytes | None = None
    for account_id, balance, nonce in accounts:
        if previous is not None and account_id <= previous:
            raise InvalidStateEntry("account IDs are not strictly increasing")
        previous = account_id
        leaves.append(_octets(account_id, 32, "account ID") + u64(balance) + u64(nonce))
    return root(leaves, "protocol-stack:v1:state")


def state_root(
    chain_id: bytes,
    height: int,
    supply_limit: int,
    total_supply: int,
    fee_pool_balance: int,
    accounts: list[tuple[bytes, int, int]],
    economy: dict[bytes, bytes],
) -> str:
    """The version-seven root. Its label and version differ from all six
    predecessors, and each non-collision is required separately."""
    return _root(
        c.STATE_ROOT_LABEL,
        c.STATE_ROOT_SCHEMA_VERSION,
        chain_id,
        height,
        supply_limit,
        total_supply,
        fee_pool_balance,
        accounts,
        economy,
        c.ECONOMY_TREE_PREFIX,
    )


def predecessor_state_root(
    version: int,
    chain_id: bytes,
    height: int,
    supply_limit: int,
    total_supply: int,
    fee_pool_balance: int,
    accounts: list[tuple[bytes, int, int]],
    economy: dict[bytes, bytes] | None = None,
) -> str:
    """An earlier version's root, restated so each non-collision is checkable.

    Distinct labels are strings rather than a chain, so refusing one collision
    implies nothing about another. Version seven must prove six.
    """
    if version == 1:
        preimage = (
            u16(1)
            + _octets(chain_id, 32, "chain ID")
            + u64(height)
            + u64(supply_limit)
            + u64(total_supply)
            + u64(fee_pool_balance)
            + u64(len(accounts))
            + accounts_root(accounts)
        )
        return digest("protocol-stack:v1:state-root", preimage).hex()
    if version not in (2, 3, 4, 5, 6):
        raise InvalidStateEntry(
            f"no predecessor root construction for version {version}"
        )
    return _root(
        f"protocol-stack:v{version}:state-root",
        version,
        chain_id,
        height,
        supply_limit,
        total_supply,
        fee_pool_balance,
        accounts,
        economy or {},
        f"protocol-stack:v{version}:economy",
    )


def _root(
    label: str,
    schema_version: int,
    chain_id: bytes,
    height: int,
    supply_limit: int,
    total_supply: int,
    fee_pool_balance: int,
    accounts: list[tuple[bytes, int, int]],
    economy: dict[bytes, bytes],
    tree_prefix: str,
) -> str:
    leaves = [entry_leaf(key, value) for key, value in sorted(economy.items())]
    preimage = (
        u16(schema_version)
        + _octets(chain_id, 32, "chain ID")
        + u64(height)
        + u64(supply_limit)
        + u64(total_supply)
        + u64(fee_pool_balance)
        + u64(len(accounts))
        + accounts_root(accounts)
        + u64(len(economy))
        + root(leaves, tree_prefix)
    )
    return digest(label, preimage).hex()


def _octets(value: Any, width: int, name: str) -> bytes:
    if type(value) is not bytes or len(value) != width:
        raise MalformedTransaction(f"{name} is not {width} octets")
    return value
