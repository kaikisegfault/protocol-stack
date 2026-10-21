"""The version-ten economy key space, its tree, and the version-ten root.

Version nine's key space with four entry kinds added and nothing else moved.
Every key builder and value encoder version nine accepted is re-exported
unchanged, so a width that moved would have to move in an accepted module and
fail that version's own vectors first.

**Three values can be absent, and none can be zero:**

- a launch retirement exists or does not, and its height is never 0, because
  no height that runs a registry step is 0;
- a machine-key entry's `registered_at_height` is the height of the kind-23
  transaction that wrote it, which is at least 1;
- a founder's count is at least 1, because only a registration writes it, and
  never exceeds the founder limit, because the limit is checked first.

A decoder refuses each, so a restored state cannot hold a value no transition
writes.

**The root is version nine's preimage under version ten's label and version
field.** Its label and field already separate it from every predecessor, and
each non-collision is still required separately.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.economy_transition.merkle import digest, root
from simulation.economy_transition_v6.envelope import u16, u32, u64
from simulation.economy_transition_v6.state import u8
from simulation.economy_transition_v9 import state as v9state
from simulation.economy_transition_v9.state import (
    InvalidStateEntry,
    accounts_root,
    entry_leaf,
)

from . import contract as c

__all__ = [
    "FounderRegistrations",
    "InvalidStateEntry",
    "MachineKey",
    "decode_founder_registrations_value",
    "decode_launch_retirement_value",
    "decode_machine_key_owner_value",
    "decode_machine_key_value",
    "economy_root",
    "founder_registrations_key",
    "founder_registrations_parts",
    "founder_registrations_value",
    "launch_retirement_key",
    "launch_retirement_value",
    "machine_key_key",
    "machine_key_owner_key",
    "machine_key_owner_parts",
    "machine_key_owner_value",
    "machine_key_parts",
    "machine_key_value",
    "ordered_entries",
    "predecessor_state_root",
    "require_entry_shape",
    "state_root",
    "state_root_frame",
    "state_root_from_frame",
]


def _require_u64(value: int, name: str) -> int:
    if type(value) is not int or value < 0 or value > c.MAX_U64:
        raise InvalidStateEntry(f"{name} is not a u64")
    return value


def _require_u32(value: int, name: str) -> int:
    if type(value) is not int or value < 0 or value > 0xFFFFFFFF:
        raise InvalidStateEntry(f"{name} is not a u32")
    return value


def _octets(value: bytes, width: int, name: str) -> bytes:
    if type(value) is not bytes or len(value) != width:
        raise InvalidStateEntry(f"{name} is not {width} octets")
    return value


# --- kind 24, the machine key ------------------------------------------------


@dataclass(frozen=True)
class MachineKey:
    machine_public_key: bytes
    build_digest: bytes
    registered_at_height: int
    last_met_window: int = 0


def machine_key_key(seat_id: int) -> bytes:
    return u8(c.MACHINE_KEY_ENTRY) + u32(_require_u32(seat_id, "seat id"))


def machine_key_parts(key: bytes) -> int:
    if len(key) != c.ENTRY_KEY_BYTES[c.MACHINE_KEY_ENTRY] or key[0] != (
        c.MACHINE_KEY_ENTRY
    ):
        raise InvalidStateEntry("not a machine-key key")
    return int.from_bytes(key[1:5], "big")


def _require_machine_key(entry: MachineKey) -> None:
    _octets(entry.machine_public_key, 32, "machine public key")
    _octets(entry.build_digest, c.BUILD_DIGEST_BYTES, "build digest")
    if _require_u64(entry.registered_at_height, "registered height") == 0:
        raise InvalidStateEntry("a machine key is written at a height of at least one")
    _require_u64(entry.last_met_window, "last met window")


def machine_key_value(entry: MachineKey) -> bytes:
    _require_machine_key(entry)
    return (
        entry.machine_public_key
        + entry.build_digest
        + u64(entry.registered_at_height)
        + u64(entry.last_met_window)
    )


def decode_machine_key_value(raw: bytes) -> MachineKey:
    if len(raw) != c.ENTRY_VALUE_BYTES[c.MACHINE_KEY_ENTRY]:
        raise InvalidStateEntry("machine-key value is not 80 octets")
    entry = MachineKey(
        machine_public_key=raw[0:32],
        build_digest=raw[32:64],
        registered_at_height=int.from_bytes(raw[64:72], "big"),
        last_met_window=int.from_bytes(raw[72:80], "big"),
    )
    _require_machine_key(entry)
    return entry


# --- kind 25, the launch retirement ------------------------------------------


def launch_retirement_key() -> bytes:
    return u8(c.LAUNCH_RETIREMENT_ENTRY)


def launch_retirement_value(retired_at_height: int) -> bytes:
    if _require_u64(retired_at_height, "retirement height") == 0:
        raise InvalidStateEntry("a retirement of zero is absence, not a value")
    return u64(retired_at_height)


def decode_launch_retirement_value(raw: bytes) -> int:
    if len(raw) != c.ENTRY_VALUE_BYTES[c.LAUNCH_RETIREMENT_ENTRY]:
        raise InvalidStateEntry("launch retirement value is not eight octets")
    height = int.from_bytes(raw, "big")
    if height == 0:
        raise InvalidStateEntry("a retirement of zero is absence, not a value")
    return height


# --- kind 26, the machine-key owner ------------------------------------------


def machine_key_owner_key(machine_public_key: bytes) -> bytes:
    return u8(c.MACHINE_KEY_OWNER_ENTRY) + _octets(
        machine_public_key, 32, "machine public key"
    )


def machine_key_owner_parts(key: bytes) -> bytes:
    if len(key) != c.ENTRY_KEY_BYTES[c.MACHINE_KEY_OWNER_ENTRY] or key[0] != (
        c.MACHINE_KEY_OWNER_ENTRY
    ):
        raise InvalidStateEntry("not a machine-key owner key")
    return key[1:33]


def machine_key_owner_value(seat_id: int) -> bytes:
    return u32(_require_u32(seat_id, "seat id"))


def decode_machine_key_owner_value(raw: bytes) -> int:
    if len(raw) != c.ENTRY_VALUE_BYTES[c.MACHINE_KEY_OWNER_ENTRY]:
        raise InvalidStateEntry("machine-key owner value is not four octets")
    return int.from_bytes(raw, "big")


# --- kind 27, the founder's registrations ------------------------------------


@dataclass(frozen=True)
class FounderRegistrations:
    """The registrations one founder's machines attested in one window.

    Keyed by the founder's identity, because ADR 0106's limit belongs to the
    founder across all of their machines. Only the latest window's count is
    kept: a count from an earlier window reads as zero.
    """

    registration_window: int
    registrations_in_window: int


def founder_registrations_key(hub_identity_hash: bytes) -> bytes:
    return u8(c.FOUNDER_REGISTRATIONS_ENTRY) + _octets(
        hub_identity_hash, 32, "founder identity"
    )


def founder_registrations_parts(key: bytes) -> bytes:
    if len(key) != c.ENTRY_KEY_BYTES[c.FOUNDER_REGISTRATIONS_ENTRY] or key[0] != (
        c.FOUNDER_REGISTRATIONS_ENTRY
    ):
        raise InvalidStateEntry("not a founder-registrations key")
    return key[1:33]


def _require_founder_registrations(entry: FounderRegistrations) -> None:
    _require_u64(entry.registration_window, "registration window")
    count = _require_u32(entry.registrations_in_window, "registrations in window")
    if count == 0:
        raise InvalidStateEntry("a founder count of zero is absence, not a value")
    if count > c.FOUNDER_REGISTRATIONS_PER_WINDOW:
        raise InvalidStateEntry("a founder's machines signed more than the limit")


def founder_registrations_value(entry: FounderRegistrations) -> bytes:
    _require_founder_registrations(entry)
    return u64(entry.registration_window) + u32(entry.registrations_in_window)


def decode_founder_registrations_value(raw: bytes) -> FounderRegistrations:
    if len(raw) != c.ENTRY_VALUE_BYTES[c.FOUNDER_REGISTRATIONS_ENTRY]:
        raise InvalidStateEntry("founder-registrations value is not 12 octets")
    entry = FounderRegistrations(
        registration_window=int.from_bytes(raw[0:8], "big"),
        registrations_in_window=int.from_bytes(raw[8:12], "big"),
    )
    _require_founder_registrations(entry)
    return entry


# --- the tree ----------------------------------------------------------------

_ADDED_DECODERS = {
    c.MACHINE_KEY_ENTRY: decode_machine_key_value,
    c.LAUNCH_RETIREMENT_ENTRY: decode_launch_retirement_value,
    c.MACHINE_KEY_OWNER_ENTRY: decode_machine_key_owner_value,
    c.FOUNDER_REGISTRATIONS_ENTRY: decode_founder_registrations_value,
}


def require_entry_shape(key: bytes, value: bytes) -> None:
    """Version nine's rule for its kinds, and the added four's here."""
    if not key:
        raise InvalidStateEntry("empty economy key")
    kind = key[0]
    if kind not in c.ADDED_IN_V10_ENTRY_KINDS:
        v9state.require_entry_shape(key, value)
        return
    if len(key) != c.ENTRY_KEY_BYTES[kind]:
        raise InvalidStateEntry(f"entry kind {kind} key is not its fixed width")
    if len(value) != c.ENTRY_VALUE_BYTES[kind]:
        raise InvalidStateEntry(f"entry kind {kind} value is not its fixed width")
    _ADDED_DECODERS[kind](value)


def ordered_entries(entries: dict[bytes, bytes]) -> list[tuple[bytes, bytes]]:
    for key, value in entries.items():
        require_entry_shape(key, value)
    return sorted(entries.items(), key=lambda item: item[0])


def economy_root(entries: dict[bytes, bytes]) -> bytes:
    ordered = ordered_entries(entries)
    return root(
        [entry_leaf(key, value) for key, value in ordered], c.ECONOMY_TREE_PREFIX
    )


# --- the root ----------------------------------------------------------------


def state_root_frame(
    chain_id: bytes,
    supply_limit: int,
    total_supply: int,
    fee_pool_balance: int,
    accounts: list[tuple[bytes, int, int]],
    economy: dict[bytes, bytes],
) -> tuple[bytes, bytes]:
    """The root preimage split around the two fields a quiet height changes.

    Version nine's split, under version ten's version field and tree. `state_root`
    is defined through it, so a run of quiet heights and a block commit to one
    preimage rather than two that could drift.
    """
    head = u16(c.STATE_ROOT_SCHEMA_VERSION) + _octets(chain_id, 32, "chain ID")
    tail = (
        u64(supply_limit)
        + u64(total_supply)
        + u64(fee_pool_balance)
        + u64(len(accounts))
        + accounts_root(accounts)
        + u64(len(economy))
        + economy_root(economy)
    )
    return head, tail


def state_root_from_frame(
    frame: tuple[bytes, bytes], height: int, timestamp: int
) -> str:
    if not c.MIN_TIMESTAMP_MILLIS <= timestamp <= c.MAX_TIMESTAMP_MILLIS:
        raise InvalidStateEntry(
            f"timestamp {timestamp} is outside calendar-v1's accepted range"
        )
    head, tail = frame
    return digest(c.STATE_ROOT_LABEL, head + u64(height) + u64(timestamp) + tail).hex()


def state_root(
    chain_id: bytes,
    height: int,
    timestamp: int,
    supply_limit: int,
    total_supply: int,
    fee_pool_balance: int,
    accounts: list[tuple[bytes, int, int]],
    economy: dict[bytes, bytes],
) -> str:
    """Version nine's preimage under `protocol-stack:v10:state-root`, version 10."""
    frame = state_root_frame(
        chain_id, supply_limit, total_supply, fee_pool_balance, accounts, economy
    )
    return state_root_from_frame(frame, height, timestamp)


def predecessor_state_root(
    version: int,
    chain_id: bytes,
    height: int,
    timestamp: int,
    supply_limit: int,
    total_supply: int,
    fee_pool_balance: int,
    accounts: list[tuple[bytes, int, int]],
    economy: dict[bytes, bytes],
) -> str:
    """The same state under every earlier root, for the non-collision vectors.

    Version nine's root carries the timestamp, so it is computed by version
    nine's own function. Every earlier root carries none and is version nine's
    `predecessor_state_root`.
    """
    if version == 9:
        return v9state.state_root(
            chain_id,
            height,
            timestamp,
            supply_limit,
            total_supply,
            fee_pool_balance,
            accounts,
            economy,
        )
    return v9state.predecessor_state_root(
        version,
        chain_id,
        height,
        supply_limit,
        total_supply,
        fee_pool_balance,
        accounts,
        economy,
    )
