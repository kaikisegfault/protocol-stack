"""The independent derivation of `economy-transition-v7`'s recorded values.

Like every transition derivation since version four's, this module imports
nothing from `simulation/`: every value it produces comes from the accepted
documents rather than from the model it is checking.

**It reaches the unchanged documents through version six's accepted derivation
rather than through a second transcription of them.** The version-one transfer
field table, the channel order, the base permission legs, the digest and Merkle
constructions, the entry field tables, and the accumulation cap are version
six's, verified by the hosted matrix over 462 vectors. Copying all of it to
change one entry kind and one record would put a transcription risk into the one
artifact whose whole job is to be a second opinion.

**What is written here by hand is what version seven defines for itself**: the
five re-versioned labels, the retirement of entry kind 7, the recovery pool
entry and its five legs, the extended cycle assignment record, and — the part
that matters — the settlement's steps 5 through 7 and the mint walk's added
term, restated from `docs/specifications/economy-transition-v7.md` rather than
imported from the model.

The module is loaded by path because both files are named `expected.py`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1]


def _load(directory: str, name: str):
    path = _TOOLS / directory / "expected.py"
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise ImportError(f"cannot load the accepted derivation at {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


_v6 = _load("economy-transition-v6-vectors", "expected_version_six_for_seven")

# Version six's own derivation reaches version four's for the figures neither
# document changed, and re-exports only what it needed. Three that version seven
# needs are reached the same way rather than transcribed a third time.
_v4 = _load("economy-transition-v4-vectors", "expected_version_four_for_seven")

# Version six's accepted derivation, re-exported by name. Version seven changes
# none of the documents behind these.
MAX_U64 = _v6.MAX_U64
MAX_OBJECT_BYTES = _v6.MAX_OBJECT_BYTES
FOUNDER_SEAT_CAPACITY = _v6.FOUNDER_SEAT_CAPACITY
ISSUANCE_CYCLES_PER_SEAT = _v6.ISSUANCE_CYCLES_PER_SEAT
MAX_SEAT_ID = _v6.MAX_SEAT_ID
MAXIMUM_SUPPLY_ATOMIC = _v6.MAXIMUM_SUPPLY_ATOMIC
CYCLE_BLOCKS = _v6.CYCLE_BLOCKS
MINT_ACCUMULATION_CAP = _v6.MINT_ACCUMULATION_CAP
ASSIGNMENT_LAG_WINDOWS = _v6.ASSIGNMENT_LAG_WINDOWS
ACTIVITY_THRESHOLD_SECONDS = _v4.ACTIVITY_THRESHOLD_SECONDS
GENESIS_FIELD_WIDTHS = _v6.GENESIS_FIELD_WIDTHS
GENESIS_PREFIX_BYTES = sum(GENESIS_FIELD_WIDTHS)
ACCOUNT_ENTRY_BYTES = _v6.ACCOUNT_ENTRY_BYTES
MAX_GENESIS_ACCOUNTS = (MAX_OBJECT_BYTES - GENESIS_PREFIX_BYTES) // ACCOUNT_ENTRY_BYTES
KEY_FIELD_WIDTHS = dict(_v6.KEY_FIELD_WIDTHS)
BENEFICIARY_KINDS = _v6.BENEFICIARY_KINDS
ATOMIC_PER_DISPLAY = _v6.ATOMIC_PER_DISPLAY
RESULT_CODES = dict(_v6.RESULT_CODES)
KIND_NAMES = dict(_v6.KIND_NAMES)

domain = _v6.domain
digest = _v6.digest
merkle = _v6.merkle
bitmap_bytes = _v6.bitmap_bytes
base_permission_legs = _v4.base_permission_legs
accrues = _v4.accrues
walk_range = _v4.walk_range

# The channel order is version four's with channel 9 renamed, which is the only
# difference `founder-economy-manifest-v3` carries and the only reason version
# seven rebinds the manifest at all. Stated here rather than imported, because
# importing version six's would import the superseded identifier.
RENAMED_CHANNEL_FROM = "initial_mystery_box_incentives"
RENAMED_CHANNEL_TO = "mini_gamified_incentives"
CHANNEL_ORDER: tuple[str, ...] = tuple(
    RENAMED_CHANNEL_TO if name == RENAMED_CHANNEL_FROM else name
    for name in _v4.CHANNEL_ORDER
)
SUPERSEDED_CHANNEL_ORDER: tuple[str, ...] = tuple(_v4.CHANNEL_ORDER)

# --- version seven's identity ------------------------------------------------

CHAIN_ID_LABEL = "protocol-stack:v7:chain-id"
STATE_ROOT_LABEL = "protocol-stack:v7:state-root"
ECONOMY_TREE_PREFIX = "protocol-stack:v7:economy"
STATE_ROOT_SCHEMA_VERSION = 7
GENESIS_SCHEMA_VERSION = 7
RECEIPT_VERSION = 7

# Labels version seven keeps at the version that accepted them, because none of
# the artifacts behind them changed.
RETAINED_LABELS: dict[str, str] = {
    "account": "protocol-stack:v1:account",
    "escrow": "protocol-stack:v6:escrow",
    "transaction_sign": "protocol-stack:v1:tx-sign",
    "transaction_id": "protocol-stack:v1:tx-id",
    "hub_registration": "protocol-stack:v6:hub-registration",
}

PREDECESSOR_VERSIONS: tuple[int, ...] = (1, 2, 3, 4, 5, 6)

MANIFEST_DIGEST = "af153c99adf7c49e5a92563946cf0e60dfd7a58785462530988f661aa68faaa7"
SUPERSEDED_MANIFEST_DIGEST = (
    "84cca09865b6c62bf09d3f6bc3821a2527c7a4835652cffdc0ebefa34b314ce5"
)

# --- version seven's state surface -------------------------------------------

RECOVERY_POOL_ENTRY = 17
RECOVERY_POOL_LEGS: tuple[int, ...] = (0, 1, 2, 3, 4)
RECOVERY_POOL_LEG_WIDTH = 8

RETIRED_ENTRY_KINDS: dict[int, str] = {
    7: "carry",
    9: "seat_manager",
    11: "hub_address",
}

ENTRY_NAMES: dict[int, str] = {
    kind: name
    for kind, name in _v6.ENTRY_NAMES.items()
    if kind not in RETIRED_ENTRY_KINDS
}
ENTRY_NAMES[RECOVERY_POOL_ENTRY] = "recovery_pool"

ENTRY_KEY_FIELDS: dict[int, tuple[str, ...]] = {
    kind: fields
    for kind, fields in _v6.ENTRY_KEY_FIELDS.items()
    if kind not in RETIRED_ENTRY_KINDS
}
ENTRY_KEY_FIELDS[RECOVERY_POOL_ENTRY] = ()

ENTRY_VALUE_FIELDS: dict[int, tuple[int, ...] | None] = {
    kind: widths
    for kind, widths in _v6.ENTRY_VALUE_FIELDS.items()
    if kind not in RETIRED_ENTRY_KINDS
}
ENTRY_VALUE_FIELDS[RECOVERY_POOL_ENTRY] = (RECOVERY_POOL_LEG_WIDTH,) * len(
    RECOVERY_POOL_LEGS
)

# The record's fixed part, field by field, as the specification tabulates it.
CYCLE_ASSIGNMENT_FIXED_FIELDS: tuple[tuple[str, int], ...] = (
    ("share_per_winner_atomic", 8),
    ("reallocated_count", 4),
    ("winner_count", 4),
    ("in_scope_count", 4),
    ("bitmap_bits", 4),
) + tuple((f"pool_absorbed_atomic_{channel}", 8) for channel in RECOVERY_POOL_LEGS)

CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES = sum(
    width for _name, width in CYCLE_ASSIGNMENT_FIXED_FIELDS
)

GENESIS_ECONOMY_ENTRIES: tuple[str, ...] = tuple(
    ["channel"] * 10 + ["recovery_pool", "verifier_key", "unreferred_pool",
                        "verified_user_counter"]
)


def key_bytes_from_fields(kind: int) -> int:
    return 1 + sum(KEY_FIELD_WIDTHS[field] for field in ENTRY_KEY_FIELDS[kind])


def value_bytes_from_fields(kind: int, bitmap_bits: int = 0) -> int:
    widths = ENTRY_VALUE_FIELDS[kind]
    if widths is None:
        return CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES + 2 * bitmap_bytes(bitmap_bits)
    return sum(widths)


def entry_bytes(kind: int, bitmap_bits: int = 0) -> int:
    return key_bytes_from_fields(kind) + value_bytes_from_fields(kind, bitmap_bits)


def field_offset(name: str) -> int:
    offset = 0
    for field_name, width in CYCLE_ASSIGNMENT_FIXED_FIELDS:
        if field_name == name:
            return offset
        offset += width
    raise KeyError(name)


# --- the settlement, restated from the specification -------------------------


def met_cycle(uptime_seconds: int) -> bool:
    return uptime_seconds >= ACTIVITY_THRESHOLD_SECONDS


def eligible_set(seats: list[dict]) -> tuple[int, ...]:
    """Every in-scope seat that met the cycle and is under the cap, in span or
    not. This is the candidate set the winner derivation ranks."""
    return tuple(
        sorted(
            seat["seat_id"]
            for seat in seats
            if met_cycle(seat["uptime"]) and accrues(seat["window"], seat["mark"])
        )
    )


def contributing_set(seats: list[dict]) -> tuple[int, ...]:
    """The in-span seats. Each generates one base permission for the cycle."""
    return tuple(sorted(seat["seat_id"] for seat in seats if seat["in_span"]))


def winner_set(seats: list[dict]) -> tuple[int, ...]:
    eligible = set(eligible_set(seats))
    candidates = {
        seat["seat_id"]: seat["uptime"]
        for seat in seats
        if seat["seat_id"] in eligible
    }
    if not candidates:
        return ()
    best = max(candidates.values())
    return tuple(sorted(seat for seat, up in candidates.items() if up == best))


def accrued_set(seats: list[dict]) -> tuple[int, ...]:
    eligible = set(eligible_set(seats))
    return tuple(
        sorted(
            seat["seat_id"]
            for seat in seats
            if seat["in_span"] and seat["seat_id"] in eligible
        )
    )


def assign(seats: list[dict], pool_before: dict[int, int]) -> dict:
    """Steps 5 through 7 of version seven's settlement, in the specified order.

    Step 6 reads the pool before step 7 writes it, so a cycle's own dust and the
    residual of the pool it just divided both belong to the cycle after.
    """
    legs = base_permission_legs()
    winners = winner_set(seats)
    winner_count = len(winners)
    accrued = accrued_set(seats)
    contributing = contributing_set(seats)
    assigned = len(contributing)
    reallocated = assigned - len(accrued)

    absorbed = {
        channel: (pool_before[channel] if winner_count else 0)
        for channel in RECOVERY_POOL_LEGS
    }

    share: dict[int, int] = {}
    remainder: dict[int, int] = {}
    dust: dict[int, int] = {}
    pool_share: dict[int, int] = {}
    residual: dict[int, int] = {}
    after: dict[int, int] = {}
    outstanding: dict[int, int] = {}
    for channel in RECOVERY_POOL_LEGS:
        leg = legs[channel]
        share[channel] = leg // winner_count if winner_count else 0
        remainder[channel] = leg - winner_count * share[channel]
        dust[channel] = reallocated * remainder[channel]
        taken = absorbed[channel]
        pool_share[channel] = taken // winner_count if winner_count else 0
        residual[channel] = taken - winner_count * pool_share[channel]
        after[channel] = (
            pool_before[channel] - taken + residual[channel] + dust[channel]
        )
        outstanding[channel] = assigned * leg

    return {
        "winners": winners,
        "winner_count": winner_count,
        "accrued": accrued,
        "contributing": contributing,
        "eligible": eligible_set(seats),
        "assigned": assigned,
        "reallocated": reallocated,
        "share": share,
        "remainder": remainder,
        "dust": dust,
        "pool_before": dict(pool_before),
        "pool_absorbed": absorbed,
        "pool_share": pool_share,
        "pool_residual": residual,
        "pool_after": after,
        "outstanding_delta": outstanding,
    }


def collect(seat_id: int, mark: int, last_assigned: int | None,
            records: dict[int, dict]) -> dict[int, int]:
    """The mint walk with version seven's added term.

    A winner takes `reallocated_count * (leg / winner_count)` as in every
    version since three, and additionally `pool_absorbed(c) / winner_count`.
    """
    legs = base_permission_legs()
    per_channel = {channel: 0 for channel in RECOVERY_POOL_LEGS}
    span = walk_range(mark, last_assigned)
    if span is None:
        return per_channel
    first, last = span
    for window in range(first, last + 1):
        record = records.get(window)
        if record is None:
            continue
        if seat_id in record["accrued"]:
            for channel in RECOVERY_POOL_LEGS:
                per_channel[channel] += legs[channel]
        if seat_id in record["winners"]:
            winner_count = record["winner_count"]
            for channel in RECOVERY_POOL_LEGS:
                per_channel[channel] += (
                    record["reallocated"] * (legs[channel] // winner_count)
                )
                per_channel[channel] += (
                    record["pool_absorbed"][channel] // winner_count
                )
    return per_channel
