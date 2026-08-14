"""The independent derivation of `economy-transition-v3`'s recorded values.

This module imports nothing from `simulation/`. It restates by hand the
version-one field tables from `protocol-primitives-v1` and `ledger-transition-v1`,
the Founder Constitution's capacity figures, the accepted manifest's channel
order, and the accepted digest and Merkle constructions, so a value both this
module and the model reach has been derived from the accepted documents and from
the implementation independently.

Two kinds of independence matter here, and they are different.

**Structural, for the compatibility claim.** This module builds the version-one
transfer as one flat 136-byte field table, exactly as `protocol-primitives-v1`
writes it, while the model builds it as a shared header, a kind-specific body,
and a shared trailer. The whole compatibility argument is that those two
constructions coincide.

**Behavioural, for the settlement.** Version three adds an accumulation cap, a
winner rule that reads it, and a bounded mint walk, so this module carries a
second implementation of all three, written from the specification's prose
rather than from the model's code. A settlement defect that produced a
self-consistent record would still have to produce the same record twice.
"""

from __future__ import annotations

import hashlib

MAX_U64 = (1 << 64) - 1
MAX_OBJECT_BYTES = 1_048_576

# Founder Constitution, restated by hand.
FOUNDER_SEAT_CAPACITY = 100_000
ISSUANCE_CYCLES_PER_SEAT = 731
MAX_SEAT_ID = FOUNDER_SEAT_CAPACITY - 1
MAX_CYCLE_INDEX = ISSUANCE_CYCLES_PER_SEAT - 1
MAXIMUM_SUPPLY_ATOMIC = 5_699_395_010_000_000_000
FOUNDER_OPERATOR_LEG_ATOMIC = 34_200_000_000
# 18 hours of the 24-hour-target cycle, in whole seconds.
ACTIVITY_THRESHOLD_SECONDS = 18 * 3_600
REFERRAL_LEG_ATOMIC = 3_420_000_000

# `cycle-boundary-v1`, restated: 86,400 target seconds cut by the pinned M1
# three-second commit interval.
CYCLE_BLOCKS = 86_400 // 3

# ADR 0033 names roughly thirty days and delegates the figure; a cycle is one
# 24-hour-target window, so thirty windows is thirty days.
MINT_ACCUMULATION_CAP = 30
MAX_SEAT_MANAGERS = 16
# `uptime-measurement-v1` finalises window `w` over the whole of `w + 1`.
ASSIGNMENT_LAG_WINDOWS = 2

# The accepted manifest's channel array order. Index 7 is `founder_referral`,
# which kind 6 may not name because kind 5 consumes it exactly.
CHANNEL_ORDER: tuple[str, ...] = (
    "founder_operator",
    "venture_escrow",
    "community_grants_escrow",
    "developer_incentives_escrow",
    "system_creator_issuance_royalty",
    "liquidity_mining",
    "impermanent_loss_protection",
    "founder_referral",
    "hub_verified_user_incentives",
    "initial_mystery_box_incentives",
)
DIRECT_ISSUE_CHANNELS: tuple[int, ...] = (5, 6, 8, 9)

# `protocol-primitives-v1`'s version-one transfer, as one flat table of
# (offset, width) pairs rather than as three parts.
TRANSFER_FIELDS: tuple[tuple[str, int, int], ...] = (
    ("magic", 0, 4),
    ("schema_version", 4, 2),
    ("transaction_kind", 6, 1),
    ("chain_id", 7, 32),
    ("signature_scheme", 39, 1),
    ("sender_public_key", 40, 32),
    ("nonce", 72, 8),
    ("recipient_account_id", 80, 32),
    ("amount", 112, 8),
    ("fee_limit", 120, 8),
    ("valid_until_height", 128, 8),
)
UNSIGNED_TRANSFER_BYTES = 136
SIGNATURE_BYTES = 64
SIGNED_TRANSFER_BYTES = UNSIGNED_TRANSFER_BYTES + SIGNATURE_BYTES

# The header is every transfer field before the recipient, and the trailer is
# the fee limit and the valid-until height. Both are derived from the table
# above rather than asserted, so a mistyped offset shows up as a length.
HEADER_BYTES = sum(width for name, _, width in TRANSFER_FIELDS if name in
                   {"magic", "schema_version", "transaction_kind", "chain_id",
                    "signature_scheme", "sender_public_key", "nonce"})
TRAILER_BYTES = sum(width for name, _, width in TRANSFER_FIELDS if name in
                    {"fee_limit", "valid_until_height"})

# Each kind's body, as a hand-written table of field widths. Every kind is
# fixed-length in version three; kinds 3 and 7 coincide, which is the case
# version two anticipated when it required dispatch on the kind byte.
BODY_FIELD_WIDTHS: dict[int, tuple[int, ...]] = {
    1: (32, 8),
    2: (4, 32, 32, 1, 32, 64),
    3: (4, 64),
    4: (4,),
    5: (),
    6: (1, 32, 32, 8, 32),
    7: (4, 64),
    8: (4, 1, 64),
    9: (4, 32, 64),
    10: (32, 64),
}

KIND_NAMES: dict[int, str] = {
    1: "native_transfer",
    2: "purchase_seat",
    3: "activate_seat",
    4: "mint_node",
    5: "mint_referral",
    6: "direct_issue",
    7: "mint_node_verified",
    8: "set_mint_biometric",
    9: "add_manager",
    10: "hub_verify",
}

# The six messages the off-chain ecosystem verifier signs, each as its label and
# the widths of the fields that follow it.
VERIFIER_MESSAGES: dict[str, tuple[str, tuple[int, ...]]] = {
    "enrollment": ("protocol-stack:v3:seat-enrollment", (32, 4, 32, 32, 8)),
    "activation": ("protocol-stack:v3:seat-activation", (32, 4, 32, 8)),
    "mint": ("protocol-stack:v3:seat-mint", (32, 4, 32, 8)),
    "mint_biometric_disable": (
        "protocol-stack:v3:mint-biometric-disable",
        (32, 4, 32, 8),
    ),
    "manager": ("protocol-stack:v3:seat-manager", (32, 4, 32, 32, 8)),
    "hub": ("protocol-stack:v3:hub-verification", (32, 32, 32, 8)),
}

RESULT_CODES: dict[int, str] = {
    0: "SUCCESS",
    1: "ZERO_AMOUNT",
    2: "FEE_LIMIT_TOO_LOW",
    3: "EXPIRED",
    4: "SENDER_NOT_FOUND",
    5: "NONCE_EXHAUSTED",
    6: "NONCE_MISMATCH",
    7: "DEBIT_OVERFLOW",
    8: "INSUFFICIENT_BALANCE",
    9: "UNAUTHORIZED",
    10: "CYCLE_RANGE",
    11: "INVALID_REFERRER",
    12: "REPLAY",
    13: "SEAT_NOT_ACTIVATED",
    14: "SEAT_NOT_PURCHASED",
    15: "NOTHING_TO_MINT",
    16: "INVALID_CHANNEL",
    17: "MISSING_RESEARCH_INPUT",
    18: "INVALID_RESEARCH_INPUT",
    19: "NOT_ELIGIBLE",
    20: "CHANNEL_CAP",
    21: "NOT_HUB_VERIFIED",
    22: "BIOMETRIC_REQUIRED",
    23: "MANAGER_LIMIT",
}

# `ledger-transition-v1`'s admission and transfer-execution codes, restated so
# the claim that 0 through 8 keep their meanings is checked against that
# document rather than against the model's own table.
VERSION_ONE_TRANSFER_RESULTS: dict[int, str] = {
    0: "SUCCESS",
    1: "ZERO_AMOUNT",
    2: "FEE_LIMIT_TOO_LOW",
    3: "EXPIRED",
    4: "SENDER_NOT_FOUND",
    5: "NONCE_EXHAUSTED",
    6: "NONCE_MISMATCH",
    7: "DEBIT_OVERFLOW",
    8: "INSUFFICIENT_BALANCE",
}
# `economy-transition-v2`'s space, restated so the continuity claim is checked
# against that accepted document rather than against version three's own table.
VERSION_TWO_RESULT_COUNT = 21

# The economy model's twenty-four declared codes, restated by hand from
# `founder-economy-simulator-v3.md`. The model is unchanged between transition
# versions two and three.
MODEL_RESULT_CODES: tuple[str, ...] = (
    "OK", "CYCLE_RANGE", "INVALID_REFERRER", "REPLAY", "SEAT_NOT_ACTIVATED",
    "MISSING_UPTIME_RECORD", "INVALID_UPTIME_RECORD", "INCONSISTENT_UPTIME_RECORD",
    "PERMISSION_NOT_FOUND", "INVALID_CHANNEL", "ZERO_AMOUNT",
    "MISSING_RESEARCH_INPUT", "INVALID_RESEARCH_INPUT", "NOT_ELIGIBLE",
    "CHANNEL_CAP", "ARITHMETIC_OVERFLOW", "INVARIANT", "HEIGHT_RANGE",
    "HEIGHT_NOT_MONOTONIC", "WINDOW_BEFORE_ISSUANCE", "WINDOW_AFTER_ISSUANCE",
    "WINDOW_NOT_FOR_CYCLE", "SEAT_NOT_IN_SCOPE", "INCOMPLETE_UPTIME_RECORD",
)

# Version-three genesis, as a hand-written field table: version one's fields
# plus the accepted manifest digest and the ecosystem verifier key.
GENESIS_FIELD_WIDTHS: tuple[int, ...] = (4, 2, 4, 8, 8, 8, 8, 32, 32, 4)
VERSION_ONE_GENESIS_PREFIX_BYTES = 46
ACCOUNT_ENTRY_BYTES = 48
RECEIPT_FIELD_WIDTHS: tuple[int, ...] = (4, 2, 32, 1, 1, 8, 8)

# Each entry key's fields, restated by name and width. The key width is derived
# from this table rather than asserted beside it, and the table is what makes
# "no entry is keyed by a seat and a cycle at once" a checkable statement about
# the key space instead of an arithmetic coincidence between two byte counts.
KEY_FIELD_WIDTHS: dict[str, int] = {
    "seat_id": 4,
    "channel_id": 1,
    "cycle_window": 8,
    "account_id": 32,
    "decision_id": 32,
    "beneficiary_kind": 1,
    "beneficiary_id": 32,
    "manager_account_id": 32,
}
ENTRY_KEY_FIELDS: dict[int, tuple[str, ...]] = {
    1: ("seat_id",),
    2: ("channel_id",),
    3: ("cycle_window",),
    4: ("account_id",),
    5: ("decision_id",),
    6: ("beneficiary_kind", "beneficiary_id"),
    7: ("channel_id",),
    8: (),
    9: ("seat_id", "manager_account_id"),
    10: ("account_id",),
    11: (),
}

# Economy state entry widths, restated as (key, value) pairs. A `None` value
# width is the one variable-width value, the cycle assignment.
ENTRY_WIDTHS: dict[int, tuple[int, int | None]] = {
    1: (5, 119),
    2: (2, 16),
    3: (9, None),
    4: (33, 24),
    5: (33, 0),
    6: (34, 8),
    7: (2, 8),
    8: (1, 32),
    9: (37, 0),
    10: (33, 40),
    11: (1, 16),
}
CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES = 24

BENEFICIARY_KINDS: dict[int, str] = {
    1: "venture_escrow",
    2: "community_grants_escrow",
    3: "developer_incentives_escrow",
    4: "system_creator_company",
    5: "direct_beneficiary",
}

# The five Founder Node distribution legs of one base permission, restated by
# hand from the Founder Constitution's per-cycle table in display units times
# the accepted eight-decimal denomination.
BASE_PERMISSION_DISPLAY: tuple[tuple[int, str], ...] = (
    (0, "342.0"),
    (1, "171.0"),
    (2, "34.2"),
    (3, "17.1"),
    (4, "10.0"),
)
ATOMIC_PER_DISPLAY = 100_000_000


def domain(label: str) -> bytes:
    encoded = label.encode("ascii")
    assert 0 < len(encoded) < 256
    return bytes([len(encoded)]) + encoded


def digest(label: str, payload: bytes = b"") -> bytes:
    return hashlib.sha256(domain(label) + payload).digest()


def merkle(leaves: list[bytes], prefix: str) -> bytes:
    """RFC 9162, restated independently of the model's implementation."""
    if not leaves:
        return digest(f"{prefix}-empty")
    if len(leaves) == 1:
        return digest(f"{prefix}-leaf", leaves[0])
    split = 1
    while split * 2 < len(leaves):
        split *= 2
    return digest(
        f"{prefix}-node", merkle(leaves[:split], prefix) + merkle(leaves[split:], prefix)
    )


def be(value: int, width: int) -> bytes:
    return value.to_bytes(width, "big")


def flat_unsigned_transfer(
    chain_id: bytes,
    public_key: bytes,
    nonce: int,
    recipient: bytes,
    amount: int,
    fee_limit: int,
    valid_until: int,
) -> bytes:
    """The transfer built from the flat version-one table, in offset order."""
    parts = {
        "magic": b"PSTX",
        "schema_version": be(1, 2),
        "transaction_kind": be(1, 1),
        "chain_id": chain_id,
        "signature_scheme": be(1, 1),
        "sender_public_key": public_key,
        "nonce": be(nonce, 8),
        "recipient_account_id": recipient,
        "amount": be(amount, 8),
        "fee_limit": be(fee_limit, 8),
        "valid_until_height": be(valid_until, 8),
    }
    raw = b""
    for name, offset, width in TRANSFER_FIELDS:
        assert len(raw) == offset, f"{name} is not at offset {offset}"
        assert len(parts[name]) == width, f"{name} is not {width} octets"
        raw += parts[name]
    assert len(raw) == UNSIGNED_TRANSFER_BYTES
    return raw


def fixed_body_bytes(kind: int) -> int:
    return sum(BODY_FIELD_WIDTHS[kind])


def signed_length(kind: int) -> int:
    return HEADER_BYTES + fixed_body_bytes(kind) + TRAILER_BYTES + SIGNATURE_BYTES


def verifier_message_bytes(name: str) -> int:
    label, widths = VERIFIER_MESSAGES[name]
    return len(domain(label)) + sum(widths)


def genesis_prefix_bytes() -> int:
    return sum(GENESIS_FIELD_WIDTHS)


def max_genesis_accounts() -> int:
    return (MAX_OBJECT_BYTES - genesis_prefix_bytes()) // ACCOUNT_ENTRY_BYTES


def receipt_bytes() -> int:
    return sum(RECEIPT_FIELD_WIDTHS)


def key_bytes_from_fields(kind: int) -> int:
    """One discriminator octet plus the kind's named fields, in order."""
    return 1 + sum(KEY_FIELD_WIDTHS[name] for name in ENTRY_KEY_FIELDS[kind])


def keys_a_seat_and_a_cycle(kind: int) -> bool:
    fields = set(ENTRY_KEY_FIELDS[kind])
    return "seat_id" in fields and "cycle_window" in fields


def bitmap_bytes(bits: int) -> int:
    return (bits + 7) // 8


def entry_bytes(kind: int, bitmap_bits: int = 0) -> int:
    key_width, value_width = ENTRY_WIDTHS[kind]
    if value_width is None:
        # Two bitmaps over the same seat-ID range, their width derived from the
        # recorded bit count rather than prefixed beside it.
        value_width = CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES + 2 * bitmap_bytes(bitmap_bits)
    return key_width + value_width


def base_permission_legs() -> dict[int, int]:
    """Derive each leg in atomic units from the constitution's display table."""
    legs = {}
    for channel, display in BASE_PERMISSION_DISPLAY:
        whole, _, fraction = display.partition(".")
        tenths = int(whole) * 10 + int(fraction)
        legs[channel] = tenths * ATOMIC_PER_DISPLAY // 10
    return legs


def split_permission(winner_count: int) -> tuple[dict[int, int], dict[int, int]]:
    shares, carries = {}, {}
    for channel, amount in base_permission_legs().items():
        if winner_count == 0:
            shares[channel], carries[channel] = 0, amount
            continue
        share = amount // winner_count
        shares[channel] = share
        carries[channel] = amount - share * winner_count
    return shares, carries


def bitmap(seat_ids, bits: int) -> bytes:
    packed = bytearray(bitmap_bytes(bits))
    for seat_id in seat_ids:
        packed[seat_id // 8] |= 0x80 >> (seat_id % 8)
    return bytes(packed)


def bit_is_set(packed: bytes, seat_id: int) -> bool:
    if seat_id // 8 >= len(packed):
        return False
    return bool(packed[seat_id // 8] & (0x80 >> (seat_id % 8)))


def accrues(cycle_window: int, mark: int) -> bool:
    return cycle_window <= mark + MINT_ACCUMULATION_CAP


def last_assigned_window(height: int) -> int | None:
    window = height // CYCLE_BLOCKS
    return None if window < ASSIGNMENT_LAG_WINDOWS else window - ASSIGNMENT_LAG_WINDOWS


def walk_range(mark: int, last_assigned: int | None):
    assert mark >= 0, "a mark is a window and windows are non-negative"
    if last_assigned is None or mark >= last_assigned:
        return None
    return mark + 1, min(last_assigned, mark + MINT_ACCUMULATION_CAP)


def derive_cycle(cycle_window: int, seats: list[dict]) -> dict:
    """A second implementation of the assignment, from the specification's prose.

    Each seat is `{"seat_id", "uptime_seconds", "in_span", "mark"}`. The order of
    the steps is the specification's: the in-scope set, the met verdict, the
    winner set restricted to seats that met *and* are under the cap, the accrued
    set, and only then the split and its carried remainder.
    """
    met = {s["seat_id"]: s["uptime_seconds"] >= ACTIVITY_THRESHOLD_SECONDS
           for s in seats}
    under_cap = {s["seat_id"]: accrues(cycle_window, s["mark"]) for s in seats}
    eligible = {
        s["seat_id"]: s["uptime_seconds"]
        for s in seats
        if met[s["seat_id"]] and under_cap[s["seat_id"]]
    }
    if eligible:
        best = max(eligible.values())
        winners = tuple(sorted(k for k, v in eligible.items() if v == best))
    else:
        winners = ()
    accrued = tuple(sorted(
        s["seat_id"] for s in seats
        if s["in_span"] and met[s["seat_id"]] and under_cap[s["seat_id"]]
    ))
    assigned = sum(1 for s in seats if s["in_span"])
    reallocated = assigned - len(accrued)
    shares, remainders = split_permission(len(winners))
    return {
        "winners": winners,
        "accrued": accrued,
        "assigned": assigned,
        "reallocated_count": reallocated,
        "in_scope_count": len(seats),
        "bitmap_bits": max((s["seat_id"] for s in seats), default=-1) + 1,
        "shares": shares,
        "carries": {ch: remainder * reallocated for ch, remainder in remainders.items()},
    }


def collect(seat_id: int, mark: int, last_assigned: int | None,
            cycles: dict[int, dict]) -> dict[int, int]:
    """A second implementation of the mint walk, over derived cycle outcomes."""
    legs = base_permission_legs()
    totals = {channel: 0 for channel in legs}
    span = walk_range(mark, last_assigned)
    if span is None:
        return totals
    first, last = span
    for window in range(first, last + 1):
        cycle = cycles.get(window)
        if cycle is None:
            continue
        if seat_id in cycle["accrued"]:
            for channel, amount in legs.items():
                totals[channel] += amount
        if seat_id in cycle["winners"]:
            for channel in legs:
                totals[channel] += cycle["reallocated_count"] * cycle["shares"][channel]
    return totals
