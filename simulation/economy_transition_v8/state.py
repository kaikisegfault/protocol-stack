"""The version-eight economy key space, its tree, and the version-eight root.

Version eight's key space is version seven's with two entry kinds added — the
open challenge and the seat window record — and no value encoding changed.

**Everything else is imported rather than restated.** Every key builder and
value encoder version seven accepted is re-exported here unchanged, so a width
that moved would have to move in version seven's accepted module and would fail
version seven's own vectors first.

The three entry-shape rules are version six's, inherited twice: a key is
`u8(entry_kind)` followed by fixed-width big-endian fields, unsigned
lexicographic key order is total, and a leaf preimage uses the accepted `bytes`
primitive for both halves.

**The two bitmaps of a window record are separate on purpose.** A dispute sets a
bit in `disputed` and never clears one in `credited`, so the record keeps what
the seat's own evidence said and the containment invariant stays checkable
against the evidence rather than against a bitmap a dispute has already
rewritten. Folding them would additionally make `DISPUTE_REPLAY` unreachable,
and a code the encoding cannot produce is coverage the vectors cannot show.
"""

from __future__ import annotations

from simulation.economy_transition.merkle import digest, root
from simulation.economy_transition_v6.envelope import MalformedTransaction, u16, u32, u64
from simulation.economy_transition_v6.state import u8
from simulation.economy_transition_v7.state import (
    InvalidStateEntry,
    accounts_root,
    channel_key,
    channel_value,
    cycle_assignment_key,
    cycle_assignment_value,
    decode_cycle_assignment_value,
    decode_recovery_pool_value,
    direct_decision_key,
    entry_leaf,
    escrow_key,
    escrow_value,
    hub_identity_key,
    hub_identity_value,
    recovery_pool_key,
    recovery_pool_value,
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

from . import contract as c

__all__ = [
    "CHALLENGE_ANSWERED",
    "CHALLENGE_OUTSTANDING",
    "InvalidStateEntry",
    "accounts_root",
    "all_slots_credited",
    "channel_key",
    "channel_value",
    "credited_slots",
    "cycle_assignment_key",
    "cycle_assignment_value",
    "decode_cycle_assignment_value",
    "decode_open_challenge_value",
    "decode_recovery_pool_value",
    "decode_seat_window_value",
    "direct_decision_key",
    "economy_root",
    "entry_leaf",
    "escrow_key",
    "escrow_value",
    "hub_identity_key",
    "hub_identity_value",
    "open_challenge_key",
    "open_challenge_value",
    "ordered_entries",
    "predecessor_state_root",
    "recovery_pool_key",
    "recovery_pool_value",
    "referral_balance_key",
    "referral_balance_value",
    "require_entry_shape",
    "seat_key",
    "seat_value",
    "seat_window_key",
    "seat_window_value",
    "signer_key",
    "signer_value",
    "state_root",
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

CHALLENGE_OUTSTANDING = 0
CHALLENGE_ANSWERED = 1

# Bit `i` of either bitmap is slot `i`. The upper eight bits of the `u32` each
# sits in are pad and must be clear.
_SLOT_MASK = (1 << c.SLOTS_PER_WINDOW) - 1


def all_slots_credited() -> int:
    """A window record that has lost nothing. An absent record reads as this."""
    return _SLOT_MASK


# --- the open challenge -----------------------------------------------------


def open_challenge_key(challenge_height: int, seat_id: int) -> bytes:
    return u8(c.OPEN_CHALLENGE_ENTRY) + u64(challenge_height) + u32(seat_id)


def open_challenge_value(state: int) -> bytes:
    """`0` while outstanding, `1` once answered, and never anything else.

    An answered challenge is kept until expiry rather than deleted, so a second
    response to it reports `RESPONSE_REPLAY` rather than the false
    `CHALLENGE_NOT_ISSUED`.
    """
    if state not in (CHALLENGE_OUTSTANDING, CHALLENGE_ANSWERED):
        raise InvalidStateEntry(f"open challenge state {state} is not 0 or 1")
    return u8(state)


def decode_open_challenge_value(raw: bytes) -> int:
    if len(raw) != c.ENTRY_VALUE_BYTES[c.OPEN_CHALLENGE_ENTRY]:
        raise InvalidStateEntry("open challenge value is not one octet")
    state = raw[0]
    if state not in (CHALLENGE_OUTSTANDING, CHALLENGE_ANSWERED):
        raise InvalidStateEntry(f"open challenge state {state} is not 0 or 1")
    return state


# --- the seat window record -------------------------------------------------


def seat_window_key(cycle_window: int, seat_id: int) -> bytes:
    return u8(c.SEAT_WINDOW_ENTRY) + u64(cycle_window) + u32(seat_id)


def seat_window_value(credited: int, disputed: int) -> bytes:
    """Two 24-bit bitmaps in the low bits of two `u32` fields."""
    _require_bitmap(credited, "credited")
    _require_bitmap(disputed, "disputed")
    if disputed & ~credited:
        raise InvalidStateEntry("a disputed slot was not credited")
    return u32(credited) + u32(disputed)


def decode_seat_window_value(raw: bytes) -> tuple[int, int]:
    if len(raw) != c.ENTRY_VALUE_BYTES[c.SEAT_WINDOW_ENTRY]:
        raise InvalidStateEntry("seat window value is not eight octets")
    credited = int.from_bytes(raw[0:4], "big")
    disputed = int.from_bytes(raw[4:8], "big")
    _require_bitmap(credited, "credited")
    _require_bitmap(disputed, "disputed")
    if disputed & ~credited:
        raise InvalidStateEntry("a disputed slot was not credited")
    return credited, disputed


def credited_slots(credited: int, disputed: int) -> int:
    """The slots a seat is finally credited for: its own evidence less voids."""
    return bin(credited & ~disputed).count("1")


def _require_bitmap(value: int, name: str) -> None:
    if type(value) is not int or value < 0:
        raise InvalidStateEntry(f"{name} bitmap is not a non-negative integer")
    if value > 0xFFFFFFFF:
        raise InvalidStateEntry(f"{name} bitmap does not fit in a u32")
    if value & ~_SLOT_MASK:
        raise InvalidStateEntry(f"{name} bitmap has a pad bit set")


# --- the tree ---------------------------------------------------------------


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
            f"entry kind {kind} is retired and permanently unassigned in version eight"
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
    elif kind == c.OPEN_CHALLENGE_ENTRY:
        decode_open_challenge_value(value)
    elif kind == c.SEAT_WINDOW_ENTRY:
        decode_seat_window_value(value)


def state_root(
    chain_id: bytes,
    height: int,
    supply_limit: int,
    total_supply: int,
    fee_pool_balance: int,
    accounts: list[tuple[bytes, int, int]],
    economy: dict[bytes, bytes],
) -> str:
    """The version-eight root. Its label and version differ from all seven
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
    implies nothing about another. Version eight must prove seven.
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
    if version not in (2, 3, 4, 5, 6, 7):
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


def _octets(value: object, width: int, name: str) -> bytes:
    if type(value) is not bytes or len(value) != width:
        raise MalformedTransaction(f"{name} is not {width} octets")
    return value
