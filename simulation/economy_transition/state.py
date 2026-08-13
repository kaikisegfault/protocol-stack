"""The canonical economy state key space, its tree, and the version-two root.

A key is `u8(entry_kind)` followed by fixed-width big-endian fields, so unsigned
lexicographic order is total and no key is a prefix of another with a different
meaning. A leaf preimage uses the accepted `bytes` primitive for both key and
value, making the boundary explicit rather than inferred from the entry kind.
"""

from __future__ import annotations

from typing import Any

from . import contract as c
from .envelope import MalformedTransaction, u8, u16, u32, u64
from .merkle import digest, root


class InvalidStateEntry(ValueError):
    """A key or value that no transition could have written."""


def seat_key(seat_id: int) -> bytes:
    return u8(c.SEAT_ENTRY) + u32(seat_id)


def channel_key(channel_index: int) -> bytes:
    return u8(c.CHANNEL_ENTRY) + u8(channel_index)


def pending_permission_key(seat_id: int, cycle_index: int) -> bytes:
    return u8(c.PENDING_PERMISSION_ENTRY) + u32(seat_id) + u16(cycle_index)


def referral_accrual_key(seat_id: int, cycle_index: int) -> bytes:
    return u8(c.REFERRAL_ACCRUAL_ENTRY) + u32(seat_id) + u16(cycle_index)


def direct_decision_key(decision_id: bytes) -> bytes:
    return u8(c.DIRECT_DECISION_ENTRY) + _octets(decision_id, 32, "decision ID")


def typed_custody_key(beneficiary_kind: int, beneficiary_id: bytes) -> bytes:
    return (
        u8(c.TYPED_CUSTODY_ENTRY)
        + u8(beneficiary_kind)
        + _octets(beneficiary_id, 32, "beneficiary ID")
    )


def performance_carry_key() -> bytes:
    return u8(c.PERFORMANCE_CARRY_ENTRY)


def window_result_key(cycle_window: int) -> bytes:
    return u8(c.WINDOW_RESULT_ENTRY) + u64(cycle_window)


def seat_value(activation_height: int, referrer_seat_id: int | None) -> bytes:
    present = referrer_seat_id is not None
    return (
        u64(activation_height)
        + u8(1 if present else 0)
        + u32(referrer_seat_id if present else 0)
    )


def channel_value(issued_atomic: int, outstanding_atomic: int) -> bytes:
    return u64(issued_atomic) + u64(outstanding_atomic)


def pending_permission_value(verdict: int) -> bytes:
    if verdict not in c.VERDICTS:
        raise InvalidStateEntry(f"unknown verdict byte {verdict}")
    return u8(verdict)


def typed_custody_value(amount_atomic: int) -> bytes:
    return u64(amount_atomic)


def performance_carry_value(carry_atomic: int) -> bytes:
    return u64(carry_atomic)


def window_result_value(
    winner_root: bytes,
    winner_count: int,
    unevaluated_count: int,
    met_bitmap: bytes,
) -> bytes:
    return (
        _octets(winner_root, 32, "winner root")
        + u32(winner_count)
        + u32(unevaluated_count)
        + u32(len(met_bitmap))
        + met_bitmap
    )


def met_bitmap(met_flags: list[bool]) -> bytes:
    """One bit per in-scope seat, ascending seat order, most significant first."""
    packed = bytearray((len(met_flags) + 7) // 8)
    for index, met in enumerate(met_flags):
        if met:
            packed[index // 8] |= 0x80 >> (index % 8)
    return bytes(packed)


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
        if len(value) < c.WINDOW_RESULT_FIXED_VALUE_BYTES:
            raise InvalidStateEntry("window result value is shorter than its fixed part")
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
    """The version-two root. Its label and version both differ from version one.

    A construction that collided with a version-one root over an identical
    account set and an empty economy would be a version-one root reinterpreted,
    which `protocol-primitives-v1` forbids.
    """
    preimage = (
        u16(c.STATE_ROOT_SCHEMA_VERSION)
        + _octets(chain_id, 32, "chain ID")
        + u64(height)
        + u64(supply_limit)
        + u64(total_supply)
        + u64(fee_pool_balance)
        + u64(len(accounts))
        + accounts_root(accounts)
        + u64(len(economy))
        + economy_root(economy)
    )
    return digest(c.STATE_ROOT_LABEL, preimage).hex()


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


def _octets(value: Any, width: int, name: str) -> bytes:
    if type(value) is not bytes or len(value) != width:
        raise MalformedTransaction(f"{name} is not {width} octets")
    return value
