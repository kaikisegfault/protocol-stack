"""The canonical economy state key space, its tree, and the version-three root.

A key is `u8(entry_kind)` followed by fixed-width big-endian fields, so unsigned
lexicographic order is total and no key is a prefix of another with a different
meaning. A leaf preimage uses the accepted `bytes` primitive for both key and
value, making the boundary explicit rather than inferred from the entry kind.

Version three adds three entry kinds — the seat manager set, the HUB registry,
and the unreferred pool — widens the seat record and the referral balance, and
changes the cycle assignment record in three ways that
`economy-transition-v3.md` records as repairs rather than as choices.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from simulation.economy_transition.merkle import digest, root

from . import contract as c
from .envelope import MalformedTransaction, u8, u16, u32, u64


class InvalidStateEntry(ValueError):
    """A key or value that no transition could have written."""


def seat_key(seat_id: int) -> bytes:
    return u8(c.SEAT_ENTRY) + u32(seat_id)


def channel_key(channel_index: int) -> bytes:
    return u8(c.CHANNEL_ENTRY) + u8(channel_index)


def cycle_assignment_key(cycle_window: int) -> bytes:
    return u8(c.CYCLE_ASSIGNMENT_ENTRY) + u64(cycle_window)


def referral_balance_key(account_id: bytes) -> bytes:
    return u8(c.REFERRAL_BALANCE_ENTRY) + _octets(account_id, 32, "account ID")


def direct_decision_key(decision_id: bytes) -> bytes:
    return u8(c.DIRECT_DECISION_ENTRY) + _octets(decision_id, 32, "decision ID")


def typed_custody_key(beneficiary_kind: int, beneficiary_id: bytes) -> bytes:
    if beneficiary_kind not in c.BENEFICIARY_KINDS:
        raise InvalidStateEntry(f"unknown beneficiary kind {beneficiary_kind}")
    if (
        beneficiary_kind in c.SINGLETON_BENEFICIARY_KINDS
        and beneficiary_id != c.SINGLETON_BENEFICIARY_ID
    ):
        raise InvalidStateEntry("a singleton beneficiary takes a zero beneficiary ID")
    return (
        u8(c.TYPED_CUSTODY_ENTRY)
        + u8(beneficiary_kind)
        + _octets(beneficiary_id, 32, "beneficiary ID")
    )


def carry_key(channel_index: int) -> bytes:
    return u8(c.CARRY_ENTRY) + u8(channel_index)


def verifier_key_key() -> bytes:
    return u8(c.VERIFIER_KEY_ENTRY)


def seat_manager_key(seat_id: int, manager_account_id: bytes) -> bytes:
    return (
        u8(c.SEAT_MANAGER_ENTRY)
        + u32(seat_id)
        + _octets(manager_account_id, 32, "manager account ID")
    )


def hub_registration_key(account_id: bytes) -> bytes:
    return u8(c.HUB_REGISTRATION_ENTRY) + _octets(account_id, 32, "account ID")


def unreferred_pool_key() -> bytes:
    return u8(c.UNREFERRED_POOL_ENTRY)


def seat_value(
    biometric_identity_hash: bytes,
    purchaser_account_id: bytes,
    referrer_account_id: bytes | None,
    activation_height: int | None = None,
    minted_through_window: int = 0,
    mint_requires_biometric: bool = False,
    manager_count: int = 1,
) -> bytes:
    """119 bytes. Activation is a flag rather than an inferred sentinel.

    `manager_count` is state because the per-seat bound must be enforceable
    without iterating a key prefix inside a transition, which is the kind of
    implicit cost two implementations disagree about.
    """
    present = referrer_account_id is not None
    activated = activation_height is not None
    if not 1 <= manager_count <= c.MAX_SEAT_MANAGERS:
        raise InvalidStateEntry(
            f"manager count {manager_count} is outside 1..{c.MAX_SEAT_MANAGERS}"
        )
    return (
        _octets(biometric_identity_hash, 32, "biometric hash")
        + _octets(purchaser_account_id, 32, "purchaser")
        + u8(1 if present else 0)
        + (_octets(referrer_account_id, 32, "referrer") if present else bytes(32))
        + u8(1 if activated else 0)
        + u64(activation_height if activated else 0)
        + u64(minted_through_window)
        + u8(1 if mint_requires_biometric else 0)
        + u32(manager_count)
    )


def channel_value(issued_atomic: int, outstanding_atomic: int) -> bytes:
    return u64(issued_atomic) + u64(outstanding_atomic)


def referral_balance_value(
    accrued_atomic: int, minted_atomic: int, collected_through_window: int
) -> bytes:
    if minted_atomic > accrued_atomic:
        raise InvalidStateEntry("a referrer cannot have minted more than it accrued")
    return u64(accrued_atomic) + u64(minted_atomic) + u64(collected_through_window)


def unreferred_pool_value(accrued_atomic: int, minted_atomic: int) -> bytes:
    if minted_atomic > accrued_atomic:
        raise InvalidStateEntry("the pool cannot have minted more than it accrued")
    return u64(accrued_atomic) + u64(minted_atomic)


def typed_custody_value(amount_atomic: int) -> bytes:
    return u64(amount_atomic)


def carry_value(carry_atomic: int) -> bytes:
    return u64(carry_atomic)


def verifier_key_value(public_key: bytes) -> bytes:
    return _octets(public_key, 32, "verifier key")


def seat_manager_value() -> bytes:
    """Presence only. Membership is the fact; the entry carries nothing else."""
    return b""


def hub_registration_value(
    hub_uniqueness_hash: bytes, verified_at_height: int
) -> bytes:
    return (
        _octets(hub_uniqueness_hash, 32, "HUB uniqueness hash")
        + u64(verified_at_height)
    )


def cycle_assignment_value(
    share_per_winner_atomic: int,
    reallocated_count: int,
    winner_count: int,
    in_scope_count: int,
    bitmap_bits: int,
    accrued_bitmap: bytes,
    winner_bitmap: bytes,
) -> bytes:
    """One record per cycle. Two bitmaps indexed by seat ID over one bit count.

    Indexing by seat ID rather than by rank within the in-scope set is what makes
    a mint's lookup a shift and a mask. Under version two's rank index, reading
    one seat's bit first required deriving the whole in-scope set for that
    window, which is an `O(n)` operation inside a transition version two
    described as constant.
    """
    expected = bitmap_bytes(bitmap_bits)
    if len(accrued_bitmap) != expected or len(winner_bitmap) != expected:
        raise InvalidStateEntry("a bitmap is not the width its bit count implies")
    return (
        u64(share_per_winner_atomic)
        + u32(reallocated_count)
        + u32(winner_count)
        + u32(in_scope_count)
        + u32(bitmap_bits)
        + accrued_bitmap
        + winner_bitmap
    )


def decode_cycle_assignment_value(raw: bytes) -> dict[str, Any]:
    if len(raw) < c.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES:
        raise InvalidStateEntry("cycle assignment is shorter than its fixed part")
    bits = int.from_bytes(raw[20:24], "big")
    width = bitmap_bytes(bits)
    if len(raw) != c.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES + 2 * width:
        raise InvalidStateEntry("cycle assignment length disagrees with its bit count")
    start = c.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES
    return {
        "share_per_winner_atomic": int.from_bytes(raw[0:8], "big"),
        "reallocated_count": int.from_bytes(raw[8:12], "big"),
        "winner_count": int.from_bytes(raw[12:16], "big"),
        "in_scope_count": int.from_bytes(raw[16:20], "big"),
        "bitmap_bits": bits,
        "accrued_bitmap": raw[start : start + width],
        "winner_bitmap": raw[start + width : start + 2 * width],
    }


def bitmap_bytes(bitmap_bits: int) -> int:
    if type(bitmap_bits) is not int or bitmap_bits < 0:
        raise InvalidStateEntry("bit count is not a non-negative integer")
    return (bitmap_bits + 7) // 8


def bitmap(seat_ids: Iterable[int], bitmap_bits: int) -> bytes:
    """One bit per seat ID, ascending, most significant bit first."""
    packed = bytearray(bitmap_bytes(bitmap_bits))
    for seat_id in seat_ids:
        if not 0 <= seat_id < bitmap_bits:
            raise InvalidStateEntry(f"seat {seat_id} is outside the bitmap")
        packed[seat_id // 8] |= 0x80 >> (seat_id % 8)
    return bytes(packed)


def bit_is_set(packed: bytes, seat_id: int) -> bool:
    """Absent bits read as clear, so a seat beyond the record is simply not in it."""
    if seat_id < 0:
        raise InvalidStateEntry(f"seat {seat_id} is not a seat identifier")
    if seat_id // 8 >= len(packed):
        return False
    return bool(packed[seat_id // 8] & (0x80 >> (seat_id % 8)))


def entry_leaf(key: bytes, value: bytes) -> bytes:
    """`bytes(key) || bytes(value)`, the accepted length-prefixed primitive."""
    return u32(len(key)) + key + u32(len(value)) + value


def economy_root(entries: dict[bytes, bytes]) -> bytes:
    ordered = ordered_entries(entries)
    return root([entry_leaf(key, value) for key, value in ordered], c.ECONOMY_TREE_PREFIX)


def ordered_entries(entries: dict[bytes, bytes]) -> list[tuple[bytes, bytes]]:
    """Unsigned lexicographic key order, with every key validated for shape."""
    for key, value in entries.items():
        _require_entry_shape(key, value)
    return sorted(entries.items(), key=lambda item: item[0])


def _require_entry_shape(key: bytes, value: bytes) -> None:
    if not key:
        raise InvalidStateEntry("empty economy key")
    kind = key[0]
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
    """The version-three root. Its label and version differ from both predecessors.

    Distinct labels are strings rather than a chain, so refusing a version-one
    collision implies nothing about a version-two one. Both are required.
    """
    return _root(c.STATE_ROOT_LABEL, c.STATE_ROOT_SCHEMA_VERSION, chain_id, height,
                 supply_limit, total_supply, fee_pool_balance, accounts, economy)


def version_two_state_root(
    chain_id: bytes,
    height: int,
    supply_limit: int,
    total_supply: int,
    fee_pool_balance: int,
    accounts: list[tuple[bytes, int, int]],
    economy: dict[bytes, bytes] | None = None,
) -> str:
    """The accepted version-two root, restated so the non-collision is checkable."""
    return _root("protocol-stack:v2:state-root", 2, chain_id, height, supply_limit,
                 total_supply, fee_pool_balance, accounts, economy or {},
                 tree_prefix="protocol-stack:v2:economy")


def version_one_state_root(
    chain_id: bytes,
    height: int,
    supply_limit: int,
    total_supply: int,
    fee_pool_balance: int,
    accounts: list[tuple[bytes, int, int]],
) -> str:
    """The accepted version-one root, restated so the non-collision is checkable."""
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
    tree_prefix: str | None = None,
) -> str:
    leaves = [
        entry_leaf(key, value) for key, value in sorted(economy.items())
    ]
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
        + root(leaves, tree_prefix or c.ECONOMY_TREE_PREFIX)
    )
    return digest(label, preimage).hex()


def _octets(value: Any, width: int, name: str) -> bytes:
    if type(value) is not bytes or len(value) != width:
        raise MalformedTransaction(f"{name} is not {width} octets")
    return value
