"""The canonical economy state key space, its tree, and the version-four root.

A key is `u8(entry_kind)` followed by fixed-width big-endian fields, so unsigned
lexicographic order is total and no key is a prefix of another with a different
meaning. A leaf preimage uses the accepted `bytes` primitive for both key and
value.

Version four adds the HUB registry — an identity record carrying the person's
public key and their two counts, and one address entry per linked account — and
re-keys the seat's identity and the referral balance from an account to a HUB
identity. The cycle assignment record is version three's, field for field, and
is encoded by importing that package rather than by restating it.
"""

from __future__ import annotations

from typing import Any

from simulation.economy_transition.merkle import digest, root
from simulation.economy_transition_v3.state import (
    bit_is_set,
    bitmap,
    bitmap_bytes,
    cycle_assignment_value,
    decode_cycle_assignment_value,
)

from . import contract as c
from .envelope import MalformedTransaction, u8, u16, u32, u64

__all__ = [
    "bit_is_set",
    "bitmap",
    "bitmap_bytes",
    "cycle_assignment_value",
    "decode_cycle_assignment_value",
    "InvalidStateEntry",
]


class InvalidStateEntry(ValueError):
    """A key or value that no transition could have written."""


def seat_key(seat_id: int) -> bytes:
    return u8(c.SEAT_ENTRY) + u32(seat_id)


def channel_key(channel_index: int) -> bytes:
    return u8(c.CHANNEL_ENTRY) + u8(channel_index)


def cycle_assignment_key(cycle_window: int) -> bytes:
    return u8(c.CYCLE_ASSIGNMENT_ENTRY) + u64(cycle_window)


def referral_balance_key(hub_identity_hash: bytes) -> bytes:
    """Keyed by the person, not by an address.

    A balance keyed by an address would be the one place where losing an
    address still lost value, which is exactly what the recovery direction
    exists to prevent over a 731-cycle benefit.
    """
    return u8(c.REFERRAL_BALANCE_ENTRY) + _octets(
        hub_identity_hash, 32, "HUB identity hash"
    )


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


def hub_identity_key(hub_identity_hash: bytes) -> bytes:
    return u8(c.HUB_IDENTITY_ENTRY) + _octets(
        hub_identity_hash, 32, "HUB identity hash"
    )


def hub_address_key(account_id: bytes) -> bytes:
    """Keyed by account, because that is the direction every transition needs.

    Enumerating a person's addresses is a read-side index rather than a
    transition need, and no transition performs it.
    """
    return u8(c.HUB_ADDRESS_ENTRY) + _octets(account_id, 32, "account ID")


def unreferred_pool_key() -> bytes:
    return u8(c.UNREFERRED_POOL_ENTRY)


def hub_identity_value(
    hub_public_key: bytes,
    registered_at_height: int,
    address_count: int,
    seat_count: int,
) -> bytes:
    """48 bytes. The public key is what every later proof of this person checks.

    Both counts are state rather than derived, for the reason ADR 0034 gives for
    `manager_count`: a bound enforced by iterating a key prefix inside a
    transition is an implicit cost two implementations disagree about.
    """
    if not 0 <= address_count <= c.MAX_IDENTITY_ADDRESSES:
        raise InvalidStateEntry(
            f"address count {address_count} is outside 0..{c.MAX_IDENTITY_ADDRESSES}"
        )
    if not 0 <= seat_count <= c.MAX_SEATS_PER_IDENTITY:
        raise InvalidStateEntry(
            f"seat count {seat_count} is outside 0..{c.MAX_SEATS_PER_IDENTITY}"
        )
    return (
        _octets(hub_public_key, 32, "HUB public key")
        + u64(registered_at_height)
        + u32(address_count)
        + u32(seat_count)
    )


def hub_address_value(hub_identity_hash: bytes) -> bytes:
    return _octets(hub_identity_hash, 32, "HUB identity hash")


def seat_value(
    hub_identity_hash: bytes,
    purchaser_account_id: bytes,
    referrer_hub_identity: bytes | None,
    activation_height: int | None = None,
    minted_through_window: int = 0,
    mint_requires_biometric: bool = False,
    manager_count: int = 1,
) -> bytes:
    """119 bytes, the same width as version three's.

    Two fields change meaning rather than size: the seat's own identity is a HUB
    identity rather than a purchase-time biometric hash, and the referrer is a
    HUB identity rather than an account. `purchaser_account_id` is retained as
    the historical record of which address bought the seat and carries no
    authority.
    """
    present = referrer_hub_identity is not None
    activated = activation_height is not None
    if not 1 <= manager_count <= c.MAX_SEAT_MANAGERS:
        raise InvalidStateEntry(
            f"manager count {manager_count} is outside 1..{c.MAX_SEAT_MANAGERS}"
        )
    return (
        _octets(hub_identity_hash, 32, "HUB identity hash")
        + _octets(purchaser_account_id, 32, "purchaser")
        + u8(1 if present else 0)
        + (
            _octets(referrer_hub_identity, 32, "referrer identity")
            if present
            else bytes(32)
        )
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
    """The version-four root. Its label and version differ from all predecessors."""
    return _root(
        c.STATE_ROOT_LABEL, c.STATE_ROOT_SCHEMA_VERSION, chain_id, height,
        supply_limit, total_supply, fee_pool_balance, accounts, economy,
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
    implies nothing about another. Version four must prove three.
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
    if version not in (2, 3):
        raise InvalidStateEntry(f"no predecessor root construction for version {version}")
    return _root(
        f"protocol-stack:v{version}:state-root", version, chain_id, height,
        supply_limit, total_supply, fee_pool_balance, accounts, economy or {},
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
