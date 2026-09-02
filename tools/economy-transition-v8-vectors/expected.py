"""Independent derivations for the version-eight vectors.

**This module imports nothing from `simulation/`.** Every value here is computed
from the specification's own statements — the field widths, the label strings,
the arithmetic, and `hashlib` — so a vector it agrees with the model about is
evidence rather than a restatement of one implementation by itself.

Where a figure is founder-directed or belongs to an accepted contract, it is
written as the specification writes it and checked against the accepted vector
file rather than against this module.
"""

from __future__ import annotations

import hashlib

CYCLE_BLOCKS = 28_800
SLOTS_PER_WINDOW = 24
SLOT_BLOCKS = CYCLE_BLOCKS // SLOTS_PER_WINDOW
SLOT_SECONDS = 3_600
RESPONSE_DEADLINE_BLOCKS = 20
CHALLENGE_PERIOD_BLOCKS = SLOT_BLOCKS
CHALLENGEABLE_HEIGHTS_PER_SLOT = SLOT_BLOCKS - RESPONSE_DEADLINE_BLOCKS
DISPUTE_CAP_SLOTS_PER_SEAT = 6
ACTIVITY_THRESHOLD_SECONDS = 64_800
ISSUANCE_CYCLES_PER_SEAT = 731
ASSIGNMENT_LAG_WINDOWS = 2
MAX_SLOT_INDEX = SLOTS_PER_WINDOW - 1

CHAIN_ID_LABEL = "protocol-stack:v8:chain-id"
STATE_ROOT_LABEL = "protocol-stack:v8:state-root"
ECONOMY_TREE_PREFIX = "protocol-stack:v8:economy"
CHALLENGE_LABEL = "protocol-stack:v8:challenge"
DISPUTE_LABEL = "protocol-stack:v8:dispute"

SCHEMA_VERSION = 8

CHALLENGE_RESPONSE = 20
FILE_DISPUTE = 21
OPEN_CHALLENGE_ENTRY = 18
SEAT_WINDOW_ENTRY = 19

ANSWER_BYTES = 32
SIGNATURE_BYTES = 64
DISPUTE_AUTHORITY_KEY_BYTES = 32

HEADER_BYTES = 80
TRAILER_BYTES = 16

CHALLENGE_RESPONSE_BODY_BYTES = 4 + 8 + ANSWER_BYTES
FILE_DISPUTE_BODY_BYTES = 4 + 8 + 1 + 1 + SIGNATURE_BYTES

OPEN_CHALLENGE_KEY_BYTES = 1 + 8 + 4
OPEN_CHALLENGE_VALUE_BYTES = 1
SEAT_WINDOW_KEY_BYTES = 1 + 8 + 4
SEAT_WINDOW_VALUE_BYTES = 4 + 4

GENESIS_PREFIX_BYTES = 110 + DISPUTE_AUTHORITY_KEY_BYTES
MAX_OBJECT_BYTES = 1_048_576
ACCOUNT_ENTRY_BYTES = 48
MAX_GENESIS_ACCOUNTS = (MAX_OBJECT_BYTES - GENESIS_PREFIX_BYTES) // ACCOUNT_ENTRY_BYTES

RESULT_CODE_COUNT = 45
ADDED_RESULT_CODES: dict[int, str] = {
    33: "SEAT_NOT_IN_SCOPE",
    34: "CHALLENGE_NOT_ISSUED",
    35: "CHALLENGE_NOT_OPEN",
    36: "RESPONSE_TOO_LATE",
    37: "RESPONSE_REPLAY",
    38: "UNAUTHORIZED_DISPUTE",
    39: "SLOT_RANGE",
    40: "WINDOW_NOT_CLOSED",
    41: "DISPUTE_WINDOW_CLOSED",
    42: "DISPUTE_REPLAY",
    43: "DISPUTE_SLOT_NOT_CREDITED",
    44: "DISPUTE_CAP_EXCEEDED",
}


def label_prefix(label: str) -> bytes:
    """`D(L) = u8(byte_length(L)) || ascii(L)`, the accepted separator."""
    encoded = label.encode("ascii")
    return bytes([len(encoded)]) + encoded


def digest(label: str, payload: bytes) -> bytes:
    return hashlib.sha256(label_prefix(label) + payload).digest()


def u8(value: int) -> bytes:
    return value.to_bytes(1, "big")


def u16(value: int) -> bytes:
    return value.to_bytes(2, "big")


def u32(value: int) -> bytes:
    return value.to_bytes(4, "big")


def u64(value: int) -> bytes:
    return value.to_bytes(8, "big")


def challenge_preimage(beacon: bytes, seat_id: int, height: int) -> bytes:
    return beacon + u32(seat_id) + u64(height)


def selection_value(beacon: bytes, seat_id: int, height: int) -> int:
    raw = digest(CHALLENGE_LABEL, challenge_preimage(beacon, seat_id, height))
    return int.from_bytes(raw[0:8], "big")


def slot_of_height(height: int) -> int:
    return (height % CYCLE_BLOCKS) // SLOT_BLOCKS


def slot_last_height(height: int) -> int:
    window_start = (height // CYCLE_BLOCKS) * CYCLE_BLOCKS
    return window_start + (slot_of_height(height) + 1) * SLOT_BLOCKS - 1


def is_challengeable_height(height: int) -> bool:
    return height <= slot_last_height(height) - RESPONSE_DEADLINE_BLOCKS


def is_selected(beacon: bytes, seat_id: int, height: int) -> bool:
    if not is_challengeable_height(height):
        return False
    return selection_value(beacon, seat_id, height) % CHALLENGE_PERIOD_BLOCKS == 0


def dispute_message(
    chain_id: bytes,
    seat_id: int,
    cycle_window: int,
    slot_index: int,
    reason_code: int,
    valid_until_height: int,
) -> bytes:
    return (
        label_prefix(DISPUTE_LABEL)
        + chain_id
        + u32(seat_id)
        + u64(cycle_window)
        + u8(slot_index)
        + u8(reason_code)
        + u64(valid_until_height)
    )


def open_challenge_key(challenge_height: int, seat_id: int) -> bytes:
    return u8(OPEN_CHALLENGE_ENTRY) + u64(challenge_height) + u32(seat_id)


def seat_window_key(cycle_window: int, seat_id: int) -> bytes:
    return u8(SEAT_WINDOW_ENTRY) + u64(cycle_window) + u32(seat_id)


def seat_window_value(credited: int, disputed: int) -> bytes:
    return u32(credited) + u32(disputed)


def all_slots_credited() -> int:
    return (1 << SLOTS_PER_WINDOW) - 1


def credited_slots(credited: int, disputed: int) -> int:
    return bin(credited & ~disputed).count("1")


def uptime_seconds(credited: int, disputed: int) -> int:
    return credited_slots(credited, disputed) * SLOT_SECONDS


def first_cycle_window(activation_height: int) -> int:
    return activation_height // CYCLE_BLOCKS + 1


def genesis_bytes(
    magic: bytes,
    schema_version: int,
    network_id: int,
    supply_limit: int,
    total_supply: int,
    fixed_transfer_fee: int,
    initial_fee_pool: int,
    manifest_digest: bytes,
    verifier_key: bytes,
    dispute_authority_key: bytes,
    account_count: int,
) -> bytes:
    """The encoder's field order, which is not the declaration's."""
    return (
        magic
        + u16(schema_version)
        + u32(network_id)
        + u64(supply_limit)
        + u64(total_supply)
        + u64(fixed_transfer_fee)
        + u64(initial_fee_pool)
        + manifest_digest
        + verifier_key
        + dispute_authority_key
        + u32(account_count)
    )
