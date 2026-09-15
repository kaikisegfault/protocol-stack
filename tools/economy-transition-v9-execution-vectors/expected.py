"""Independent derivations for the version-nine execution vectors.

**This module imports nothing from `simulation/`.** Every value here is computed
from the specification's own statements — the field widths, the label strings,
the arithmetic, and `hashlib` — so a vector it agrees with the model about is
evidence rather than a restatement of one implementation by itself.

**The calendar is computed by accumulating month lengths from 1970**, which is
deliberately not the closed form the model uses. It is duplicated from the
contract-half tool rather than imported from it, because what independence means
here is independence from `simulation/`, and two tools that shared a derivation
would still be two copies of the same *second* implementation.
"""

from __future__ import annotations

import hashlib

CYCLE_BLOCKS = 28_800
SLOTS_PER_WINDOW = 24
SLOT_SECONDS = 3_600
ASSIGNMENT_LAG_WINDOWS = 2
WINDOW_UPTIME_SECONDS_MAX = SLOTS_PER_WINDOW * SLOT_SECONDS

MILLIS_PER_DAY = 86_400_000
MIN_CALENDAR_YEAR = 1970
MONTHS_PER_YEAR = 12

CHAIN_ID_LABEL = "protocol-stack:v9:chain-id"
STATE_ROOT_LABEL = "protocol-stack:v9:state-root"
ECONOMY_TREE_PREFIX = "protocol-stack:v9:economy"
BLOCK_ID_LABEL = "protocol-stack:v9:block-id"
TRANSACTION_TREE_PREFIX = "protocol-stack:v1:tx"

GENESIS_MAGIC = b"PSGN"
BLOCK_MAGIC = b"PSBL"
RECEIPT_MAGIC = b"PSRC"

SCHEMA_VERSION = 9
RECEIPT_VERSION = 9
BLOCK_HEADER_BYTES = 154
GENESIS_PREFIX_BYTES = 150
RECEIPT_BYTES = 56

MINT_POOL = 22
REFERRAL_CHANNEL = 7
# `founder-economy-manifest-v3`: 34.2 units per cycle at eight decimals.
REFERRAL_LEG_ATOMIC = 3_420_000_000

MILLIS_PER_BLOCK = 90_000


def label_prefix(label: str) -> bytes:
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


# --- the calendar, by accumulation ------------------------------------------


def is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_in_month(year: int, month: int) -> int:
    lengths = (
        31, 29 if is_leap_year(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31
    )
    return lengths[month - 1]


def month_index(timestamp: int) -> int:
    day = timestamp // MILLIS_PER_DAY
    index, year, month = 0, MIN_CALENDAR_YEAR, 1
    while True:
        length = days_in_month(year, month)
        if day < length:
            return index
        day -= length
        index += 1
        month += 1
        if month > MONTHS_PER_YEAR:
            month, year = 1, year + 1


def month_of_window(window: int, genesis_millis: int, halt_height=None, halt_millis=0):
    """A window's month: the month of its first height's stamp.

    The stamp is this module's own arithmetic over the fixture's block rate, not
    the model's, which is what makes the attribution derived twice rather than
    read twice.
    """
    height = window * CYCLE_BLOCKS
    stamp = genesis_millis + height * MILLIS_PER_BLOCK
    if halt_height is not None and height >= halt_height:
        stamp += halt_millis
    return month_index(stamp)


# --- the settlement arithmetic ----------------------------------------------


def share_and_remainder(payable: int, winners: int) -> tuple[int, int]:
    if winners == 0:
        return 0, payable
    share = payable // winners
    return share, payable - share * winners


def accrual_for(contributing_seats: int, windows: int) -> int:
    """What an unreferred population routes to the pool over a run of windows."""
    return contributing_seats * windows * REFERRAL_LEG_ATOMIC


def first_cycle_window(activation_height: int) -> int:
    return activation_height // CYCLE_BLOCKS + 1


def uptime_seconds(credited_slots: int) -> int:
    return credited_slots * SLOT_SECONDS


# --- the encodings ----------------------------------------------------------


def genesis_bytes(
    schema_version: int,
    network_id: int,
    genesis_timestamp: int,
    supply_limit: int,
    total_supply: int,
    fixed_transfer_fee: int,
    initial_fee_pool: int,
    manifest_digest: bytes,
    verifier_key: bytes,
    dispute_authority_key: bytes,
    account_count: int,
) -> bytes:
    return (
        GENESIS_MAGIC
        + u16(schema_version)
        + u32(network_id)
        + u64(genesis_timestamp)
        + u64(supply_limit)
        + u64(total_supply)
        + u64(fixed_transfer_fee)
        + u64(initial_fee_pool)
        + manifest_digest
        + verifier_key
        + dispute_authority_key
        + u32(account_count)
    )


def block_header(
    chain_id: bytes,
    height: int,
    timestamp: int,
    previous_state_root: bytes,
    transaction_root: bytes,
    resulting_state_root: bytes,
    transaction_count: int,
) -> bytes:
    return (
        BLOCK_MAGIC
        + u16(SCHEMA_VERSION)
        + chain_id
        + u64(height)
        + u64(timestamp)
        + previous_state_root
        + transaction_root
        + resulting_state_root
        + u32(transaction_count)
    )


def receipt_bytes(
    transaction_id: bytes,
    kind: int,
    result_code: int,
    fee_charged: int,
    issued_atomic: int,
) -> bytes:
    return (
        RECEIPT_MAGIC
        + u16(RECEIPT_VERSION)
        + transaction_id
        + u8(kind)
        + u8(result_code)
        + u64(fee_charged)
        + u64(issued_atomic)
    )


def tx_tree(ids: list[bytes]) -> bytes:
    """RFC 9162's shape, version one's labels, restated over a list of IDs."""
    if not ids:
        return digest(f"{TRANSACTION_TREE_PREFIX}-empty", b"")
    if len(ids) == 1:
        return digest(f"{TRANSACTION_TREE_PREFIX}-leaf", ids[0])
    split = 1
    while split * 2 < len(ids):
        split *= 2
    return digest(
        f"{TRANSACTION_TREE_PREFIX}-node", tx_tree(ids[:split]) + tx_tree(ids[split:])
    )
