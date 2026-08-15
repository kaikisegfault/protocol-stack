"""The economy state key space and the version-five roots.

Not one key, value, width, or ordering rule moves in version five, so every
builder here is version four's, imported by name. What version five defines is
the two constructions that separate one chain's commitments from another's: the
economy tree prefix and the state-root label and version field.

`predecessor_state_root` gains a fourth entry. The labels are distinct strings
rather than a chain, so refusing one collision implies nothing about another,
and version five must prove four rather than three. Each predecessor
construction is required to reproduce its own version's accepted vectors before
any non-collision claim rests on it, because a lookalike would make "the roots
differ" trivially true.
"""

from __future__ import annotations

from typing import Any

from simulation.economy_transition.merkle import digest, root
from simulation.economy_transition_v4.state import (
    InvalidStateEntry,
    accounts_root,
    bit_is_set,
    bitmap,
    bitmap_bytes,
    carry_key,
    carry_value,
    channel_key,
    channel_value,
    cycle_assignment_key,
    cycle_assignment_value,
    decode_cycle_assignment_value,
    direct_decision_key,
    entry_leaf,
    hub_address_key,
    hub_address_value,
    hub_identity_key,
    hub_identity_value,
    ordered_entries,
    referral_balance_key,
    referral_balance_value,
    seat_key,
    seat_manager_key,
    seat_manager_value,
    seat_value,
    typed_custody_key,
    typed_custody_value,
    unreferred_pool_key,
    unreferred_pool_value,
    verifier_key_key,
    verifier_key_value,
)

from . import contract as c
from .envelope import MalformedTransaction, u16, u64

__all__ = [
    "InvalidStateEntry",
    "accounts_root",
    "bit_is_set",
    "bitmap",
    "bitmap_bytes",
    "carry_key",
    "carry_value",
    "channel_key",
    "channel_value",
    "cycle_assignment_key",
    "cycle_assignment_value",
    "decode_cycle_assignment_value",
    "direct_decision_key",
    "economy_root",
    "entry_leaf",
    "hub_address_key",
    "hub_address_value",
    "hub_identity_key",
    "hub_identity_value",
    "ordered_entries",
    "predecessor_state_root",
    "referral_balance_key",
    "referral_balance_value",
    "seat_key",
    "seat_manager_key",
    "seat_manager_value",
    "seat_value",
    "state_root",
    "typed_custody_key",
    "typed_custody_value",
    "unreferred_pool_key",
    "unreferred_pool_value",
    "verifier_key_key",
    "verifier_key_value",
]

# Every predecessor construction, as the label and version field that version
# recorded. Version one is the outlier: it has no economy tree at all.
PREDECESSOR_ROOTS: dict[int, tuple[str, str | None]] = {
    1: ("protocol-stack:v1:state-root", None),
    2: ("protocol-stack:v2:state-root", "protocol-stack:v2:economy"),
    3: ("protocol-stack:v3:state-root", "protocol-stack:v3:economy"),
    4: ("protocol-stack:v4:state-root", "protocol-stack:v4:economy"),
}


def economy_root(entries: dict[bytes, bytes]) -> bytes:
    ordered = ordered_entries(entries)
    return root(
        [entry_leaf(key, value) for key, value in ordered], c.ECONOMY_TREE_PREFIX
    )


def state_root(
    chain_id: bytes,
    height: int,
    supply_limit: int,
    total_supply: int,
    fee_pool_balance: int,
    accounts: list[tuple[bytes, int, int]],
    economy: dict[bytes, bytes],
) -> str:
    """The version-five root. Its label and version differ from all four predecessors."""
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
    """An earlier version's root, restated so each non-collision is checkable."""
    if version not in PREDECESSOR_ROOTS:
        raise InvalidStateEntry(
            f"no predecessor root construction for version {version}"
        )
    label, tree_prefix = PREDECESSOR_ROOTS[version]
    if tree_prefix is None:
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
        return digest(label, preimage).hex()
    return _root(
        label,
        version,
        chain_id,
        height,
        supply_limit,
        total_supply,
        fee_pool_balance,
        accounts,
        economy or {},
        tree_prefix,
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
