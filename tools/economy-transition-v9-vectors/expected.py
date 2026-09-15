"""Independent derivations for the version-nine vectors.

**This module imports nothing from `simulation/`.** Every value here is computed
from the specification's own statements — the field widths, the label strings,
the arithmetic, and `hashlib` — so a vector it agrees with the model about is
evidence rather than a restatement of one implementation by itself.

**The calendar is computed by accumulating month lengths from 1970**, not by the
closed form `simulation.calendar` uses, which is the method
`tools/calendar-vectors/expected.py` established for the same reason: two
algorithms agreeing is the evidence, and a single algorithm restating itself
would not be.

**The settlement is settled in closed form**, grouping the whole recorded
sequence by month and folding the balance forward, where the model is a machine
consuming one window at a time. The two constructions are different shapes on
purpose.

Where a figure is founder-directed or belongs to an accepted contract, it is
written as the specification writes it and checked against the accepted vector
file rather than against this module.
"""

from __future__ import annotations

import hashlib

# --- the grid, from the accepted contracts ----------------------------------

CYCLE_BLOCKS = 28_800
SLOTS_PER_WINDOW = 24
SLOT_SECONDS = 3_600
ASSIGNMENT_LAG_WINDOWS = 2
WINDOW_UPTIME_SECONDS_MAX = SLOTS_PER_WINDOW * SLOT_SECONDS
TARGET_COMMIT_SECONDS = 3

# --- the clock, from `calendar-v1` ------------------------------------------

MILLIS_PER_SECOND = 1_000
MILLIS_PER_DAY = 86_400_000
MIN_TIMESTAMP_MILLIS = 0
MAX_TIMESTAMP_MILLIS = 253_402_300_799_999
MIN_CALENDAR_YEAR = 1970
MAX_CALENDAR_YEAR = 9999
MONTHS_PER_YEAR = 12
MAX_MONTH_INDEX = (MAX_CALENDAR_YEAR - MIN_CALENDAR_YEAR) * MONTHS_PER_YEAR + 11
TIMESTAMP_TOLERANCE_MILLIS = 60_000

# --- version nine's own identity --------------------------------------------

CHAIN_ID_LABEL = "protocol-stack:v9:chain-id"
STATE_ROOT_LABEL = "protocol-stack:v9:state-root"
ECONOMY_TREE_PREFIX = "protocol-stack:v9:economy"
BLOCK_ID_LABEL = "protocol-stack:v9:block-id"
MINT_CONFIRM_LABEL = "protocol-stack:v6:mint-confirm"

SCHEMA_VERSION = 9
BLOCK_HEADER_SCHEMA_VERSION = 9
RECEIPT_VERSION = 9

# --- the widths -------------------------------------------------------------

HEADER_BYTES = 80
TRAILER_BYTES = 16
SIGNATURE_BYTES = 64
HUB_SIGNATURE_BYTES = 64

MINT_POOL = 22
MINT_POOL_BODY_BYTES = 4 + 32 + HUB_SIGNATURE_BYTES

TIMESTAMP_BYTES = 8
BLOCK_HEADER_BYTES = 146 + TIMESTAMP_BYTES
BLOCK_TIMESTAMP_OFFSET = 46

WINDOW_MONTH_ENTRY = 20
MONTHLY_FIGURE_ENTRY = 21
MONTHLY_CLAIM_ENTRY = 22
SETTLEMENT_CURSOR_ENTRY = 23
UNREFERRED_POOL_ENTRY = 12

WINDOW_MONTH_KEY_BYTES = 1 + 8
WINDOW_MONTH_VALUE_BYTES = 4
MONTHLY_FIGURE_KEY_BYTES = 1 + 4 + 4
MONTHLY_FIGURE_VALUE_BYTES = 8
MONTHLY_CLAIM_KEY_BYTES = 1 + 4
MONTHLY_CLAIM_VALUE_BYTES = 16
SETTLEMENT_CURSOR_KEY_BYTES = 1
SETTLEMENT_CURSOR_VALUE_BYTES = 4
UNREFERRED_POOL_VALUE_BYTES = 24

GENESIS_TIMESTAMP_BYTES = 8
GENESIS_PREFIX_BYTES = 142 + GENESIS_TIMESTAMP_BYTES
GENESIS_TIMESTAMP_OFFSET = 10
MAX_OBJECT_BYTES = 1_048_576
ACCOUNT_ENTRY_BYTES = 48
MAX_GENESIS_ACCOUNTS = (MAX_OBJECT_BYTES - GENESIS_PREFIX_BYTES) // ACCOUNT_ENTRY_BYTES

GENESIS_ECONOMY_ENTRY_COUNT = 16
LIVE_WINDOW_MONTHS = 2
RESULT_CODE_COUNT = 45

TIMESTAMP_CONDITIONS = (
    "HEIGHT_NOT_NEXT",
    "TIMESTAMP_RANGE",
    "TIMESTAMP_NOT_MONOTONIC",
    "TIMESTAMP_AHEAD_OF_TOLERANCE",
    "TIMESTAMP_BEHIND_TOLERANCE",
)

# --- primitives -------------------------------------------------------------


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


# --- the calendar, by accumulation rather than by closed form ----------------


def is_leap_year(year: int) -> bool:
    """The whole Gregorian rule, not the abbreviation of it."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_in_month(year: int, month: int) -> int:
    lengths = (31, 29 if is_leap_year(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    return lengths[month - 1]


def month_index(timestamp: int) -> int:
    """Walk months forward from the epoch until the day index is reached.

    Deliberately the slow construction: `simulation.calendar` reaches the same
    answer by the standard closed form, so two different algorithms agreeing is
    the evidence. The walk is at most 96,360 iterations and the recorded cases
    are all inside this century.
    """
    if not MIN_TIMESTAMP_MILLIS <= timestamp <= MAX_TIMESTAMP_MILLIS:
        raise ValueError(f"timestamp {timestamp} is outside the accepted range")
    day = timestamp // MILLIS_PER_DAY
    index = 0
    year, month = MIN_CALENDAR_YEAR, 1
    while True:
        length = days_in_month(year, month)
        if day < length:
            return index
        day -= length
        index += 1
        month += 1
        if month > MONTHS_PER_YEAR:
            month, year = 1, year + 1


def month_start_millis(index: int) -> int:
    days = 0
    year, month = MIN_CALENDAR_YEAR, 1
    for _ in range(index):
        days += days_in_month(year, month)
        month += 1
        if month > MONTHS_PER_YEAR:
            month, year = 1, year + 1
    return days * MILLIS_PER_DAY


# --- the timestamp rules, in `calendar-v1`'s order --------------------------


def timestamp_condition(
    next_height: int,
    head_timestamp: int,
    height: int,
    timestamp: int,
    observed_clock: int | None,
) -> str:
    """The first condition that fires, or `ACCEPTED`.

    `observed_clock` of `None` is the replay path: conditions 4 and 5 are not
    applied at all, which is the separation the whole rule rests on.
    """
    if height != next_height:
        return "HEIGHT_NOT_NEXT"
    if not MIN_TIMESTAMP_MILLIS <= timestamp <= MAX_TIMESTAMP_MILLIS:
        return "TIMESTAMP_RANGE"
    if timestamp < head_timestamp:
        return "TIMESTAMP_NOT_MONOTONIC"
    if observed_clock is None:
        return "ACCEPTED"
    if timestamp - observed_clock > TIMESTAMP_TOLERANCE_MILLIS:
        return "TIMESTAMP_AHEAD_OF_TOLERANCE"
    if observed_clock - timestamp > TIMESTAMP_TOLERANCE_MILLIS:
        return "TIMESTAMP_BEHIND_TOLERANCE"
    return "ACCEPTED"


# --- the encodings ----------------------------------------------------------


def window_month_key(cycle_window: int) -> bytes:
    return u8(WINDOW_MONTH_ENTRY) + u64(cycle_window)


def window_month_value(month: int) -> bytes:
    return u32(month)


def monthly_figure_key(month: int, seat_id: int) -> bytes:
    return u8(MONTHLY_FIGURE_ENTRY) + u32(month) + u32(seat_id)


def monthly_figure_value(seconds: int) -> bytes:
    return u64(seconds)


def monthly_claim_key(seat_id: int) -> bytes:
    return u8(MONTHLY_CLAIM_ENTRY) + u32(seat_id)


def monthly_claim_value(accrued: int, minted: int) -> bytes:
    return u64(accrued) + u64(minted)


def settlement_cursor_key() -> bytes:
    return u8(SETTLEMENT_CURSOR_ENTRY)


def settlement_cursor_value(month: int) -> bytes:
    return u32(month)


def unreferred_pool_value(accrued: int, payable: int, minted: int) -> bytes:
    return u64(accrued) + u64(payable) + u64(minted)


def mint_message(
    chain_id: bytes,
    hub_identity_hash: bytes,
    kind: int,
    seat_id: int,
    destination_escrow_id: bytes,
    valid_until_height: int,
) -> bytes:
    return (
        label_prefix(MINT_CONFIRM_LABEL)
        + chain_id
        + hub_identity_hash
        + u8(kind)
        + u32(seat_id)
        + destination_escrow_id
        + u64(valid_until_height)
    )


def mint_pool_body(
    seat_id: int, destination_escrow_id: bytes, hub_signature: bytes
) -> bytes:
    return u32(seat_id) + destination_escrow_id + hub_signature


def genesis_bytes(
    magic: bytes,
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
    """The encoder's field order, which is not the declaration's."""
    return (
        magic
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
    magic: bytes,
    chain_id: bytes,
    height: int,
    timestamp: int,
    previous_state_root: bytes,
    transaction_root: bytes,
    resulting_state_root: bytes,
    transaction_count: int,
) -> bytes:
    """Version one's header with the timestamp inserted after the height."""
    return (
        magic
        + u16(BLOCK_HEADER_SCHEMA_VERSION)
        + chain_id
        + u64(height)
        + u64(timestamp)
        + previous_state_root
        + transaction_root
        + resulting_state_root
        + u32(transaction_count)
    )


# --- the settlement, in closed form -----------------------------------------


def first_cycle_window(activation_height: int) -> int:
    return activation_height // CYCLE_BLOCKS + 1


def settle(
    sequence: tuple[tuple[int, dict[int, int], int], ...],
    activations: dict[int, int],
    month_of_window,
) -> dict:
    """Fold the whole recorded window sequence forward, month by month.

    The model is a machine that consumes one window at a time and carries a
    balance; this groups the sequence by month first and settles each completed
    month against the balance standing before the assignment that closed it. The
    two shapes reaching the same claims is what makes a recorded value evidence.
    """
    ordered = sorted(sequence)
    figures: dict[int, dict[int, int]] = {}
    accruals: dict[int, int] = {}
    last_window: dict[int, int] = {}
    for index, uptime, accrual in ordered:
        month = month_of_window(index)
        last_window[month] = index
        accruals[month] = accruals.get(month, 0) + accrual
        for seat, seconds in uptime.items():
            if seconds:
                figures.setdefault(month, {})[seat] = (
                    figures.get(month, {}).get(seat, 0) + seconds
                )

    months = [month_of_window(index) for index, _u, _a in ordered]
    payable = 0
    accrued = 0
    claims: dict[int, int] = {}
    settlements: list[dict] = []
    skipped: list[int] = []
    cursor = months[0]
    for position, month in enumerate(months):
        if month > cursor:
            settlement = _settle_one(
                cursor, activations, last_window, figures, payable, claims
            )
            settlements.append(settlement)
            payable = settlement["remainder"]
            # Every index strictly between the cursor's month and this one is an
            # empty month: no window is attributed to it, so it has neither an
            # accrual nor a candidate, and a pass over it would leave the balance
            # exactly as it found it. They are recorded as skipped rather than
            # settled, which is the single-pass rule stated from the other side.
            skipped.extend(range(cursor + 1, month))
            cursor = month
        _index, _uptime, accrual = ordered[position]
        payable += accrual
        accrued += accrual
    return {
        "accrued": accrued,
        "payable": payable,
        "claims": claims,
        "settlements": tuple(settlements),
        "skipped": tuple(skipped),
        "open_figures": figures.get(cursor, {}),
        "cursor": cursor,
    }


def _settle_one(
    month: int,
    activations: dict[int, int],
    last_window: dict[int, int],
    figures: dict[int, dict[int, int]],
    payable: int,
    claims: dict[int, int],
) -> dict:
    window = last_window.get(month)
    candidates = (
        tuple(
            seat
            for seat in sorted(activations)
            if first_cycle_window(activations[seat]) <= window
        )
        if window is not None
        else ()
    )
    month_figures = figures.get(month, {})
    if not candidates:
        return {
            "month": month,
            "candidate_count": 0,
            "best_figure": 0,
            "winners": (),
            "payable_before": payable,
            "share": 0,
            "remainder": payable,
            "assigned": 0,
        }
    best = max(month_figures.get(seat, 0) for seat in candidates)
    winners = tuple(seat for seat in candidates if month_figures.get(seat, 0) == best)
    share = payable // len(winners)
    assigned = share * len(winners)
    if share:
        for seat in winners:
            claims[seat] = claims.get(seat, 0) + share
    figures.pop(month, None)
    return {
        "month": month,
        "candidate_count": len(candidates),
        "best_figure": best,
        "winners": winners,
        "payable_before": payable,
        "share": share,
        "remainder": payable - assigned,
        "assigned": assigned,
    }
