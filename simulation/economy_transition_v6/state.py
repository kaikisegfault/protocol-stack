"""The canonical economy state key space, its tree, and the version-six root.

A key is `u8(entry_kind)` followed by fixed-width big-endian fields, so unsigned
lexicographic order is total and no key is a prefix of another with a different
meaning. A leaf preimage uses the accepted `bytes` primitive for both key and
value.

Version six replaces the HUB address set with escrow and signer entries, adds the
verified-user enrollment and its counter, and shrinks the seat record to an
identity reference. The cycle assignment record is version three's, field for
field, and is encoded by importing that package rather than by restating it.

**An escrow's balance and nonce are not here.** They are the version-one account
entry keyed by the same 32 octets, which is what makes a version-six state a
version-one state plus an economy map.
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
from .identity import Posture

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


def hub_identity_key(hub_identity_hash: bytes) -> bytes:
    return u8(c.HUB_IDENTITY_ENTRY) + _octets(
        hub_identity_hash, 32, "HUB identity hash"
    )


def unreferred_pool_key() -> bytes:
    return u8(c.UNREFERRED_POOL_ENTRY)


def escrow_key(escrow_id: bytes) -> bytes:
    return u8(c.ESCROW_ENTRY) + _octets(escrow_id, 32, "escrow ID")


def signer_key(signer_id: bytes) -> bytes:
    """Keyed by signer, because that is the direction every scheme-1 transaction
    needs: which escrow does this key act on. It is one lookup, and enumerating
    an escrow's signers is a read-side index no transition performs."""
    return u8(c.SIGNER_ENTRY) + _octets(signer_id, 32, "signer ID")


def verified_user_key(hub_identity_hash: bytes) -> bytes:
    return u8(c.VERIFIED_USER_ENTRY) + _octets(
        hub_identity_hash, 32, "HUB identity hash"
    )


def verified_user_counter_key() -> bytes:
    return u8(c.VERIFIED_USER_COUNTER_ENTRY)


def hub_identity_value(
    hub_public_key: bytes,
    registered_at_height: int,
    next_escrow_index: int,
    escrow_count: int,
    seat_count: int,
) -> bytes:
    """52 bytes. The three counts are state rather than derived, for the reason
    ADR 0034 gives: a bound or an index obtained by iterating a key prefix inside
    a transition is an implicit cost two implementations disagree about.

    `next_escrow_index` and `escrow_count` are separate on purpose. The index
    never decreases so an identifier is never reissued; the count falls on
    deletion so the live figure is exact. One field cannot be both.
    """
    if escrow_count > next_escrow_index:
        raise InvalidStateEntry("live escrow count exceeds the next index")
    if not 0 <= seat_count <= c.MAX_SEATS_PER_IDENTITY:
        raise InvalidStateEntry(
            f"seat count {seat_count} is outside 0..{c.MAX_SEATS_PER_IDENTITY}"
        )
    return (
        _octets(hub_public_key, 32, "HUB public key")
        + u64(registered_at_height)
        + u32(next_escrow_index)
        + u32(escrow_count)
        + u32(seat_count)
    )


def escrow_value(
    owner_hub_identity: bytes, posture: Posture, signer_count: int
) -> bytes:
    """49 bytes, and no balance: that is the version-one account entry's."""
    if not 0 <= signer_count <= c.MAX_SIGNERS_PER_ESCROW:
        raise InvalidStateEntry(
            f"signer count {signer_count} is outside 0..{c.MAX_SIGNERS_PER_ESCROW}"
        )
    return (
        _octets(owner_hub_identity, 32, "owner identity")
        + u8(1 if posture.requires_confirmation else 0)
        + u64(posture.min_amount_atomic)
        + u32(posture.exempt_slot_mask)
        + u32(signer_count)
    )


def signer_value(escrow_id: bytes) -> bytes:
    return _octets(escrow_id, 32, "escrow ID")


def verified_user_value(
    enrolled_at_height: int, minted_through_window: int, issued_atomic: int
) -> bytes:
    maximum = c.VERIFIED_USER_CYCLES * c.VERIFIED_USER_DAILY_ATOMIC
    if issued_atomic > maximum:
        raise InvalidStateEntry("an identity cannot have been issued more than its period")
    return u64(enrolled_at_height) + u64(minted_through_window) + u64(issued_atomic)


def verified_user_counter_value(enrolled_count: int) -> bytes:
    if enrolled_count > c.VERIFIED_USER_POPULATION:
        raise InvalidStateEntry("more identities enrolled than the population permits")
    return u64(enrolled_count)


def seat_value(
    hub_identity_hash: bytes,
    referrer_hub_identity: bytes | None,
    activation_height: int | None = None,
    minted_through_window: int = 0,
) -> bytes:
    """82 bytes, down from version four's 119.

    The purchaser account, the biometric flag, and the manager count are gone
    with the concepts they served, and nothing replaced them: a seat is owned by
    an identity and read through it.
    """
    present = referrer_hub_identity is not None
    activated = activation_height is not None
    return (
        _octets(hub_identity_hash, 32, "HUB identity hash")
        + u8(1 if present else 0)
        + (
            _octets(referrer_hub_identity, 32, "referrer identity")
            if present
            else bytes(32)
        )
        + u8(1 if activated else 0)
        + u64(activation_height if activated else 0)
        + u64(minted_through_window)
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
    if kind in c.RETIRED_ENTRY_KINDS:
        raise InvalidStateEntry(
            f"entry kind {kind} is retired and permanently unassigned in version six"
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
    """The version-six root. Its label and version differ from all predecessors."""
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
    implies nothing about another. Version six must prove five.
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
    if version not in (2, 3, 4, 5):
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
