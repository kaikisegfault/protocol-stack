"""The independent derivation of `economy-transition-v2`'s recorded values.

This module imports nothing from `simulation/`. It restates by hand the
version-one field tables from `protocol-primitives-v1` and `ledger-transition-v1`,
the Founder Constitution's capacity figures, the accepted manifest's channel
order, and the accepted digest and Merkle constructions, so a value both this
module and the model reach has been derived from the accepted documents and from
the implementation independently.

The independence that matters most is structural. **This module builds the
version-one transfer as one flat 136-byte field table, exactly as
`protocol-primitives-v1` writes it, while the model builds it as a shared header,
a kind-specific body, and a shared trailer.** The whole compatibility argument is
that those two constructions coincide, so deriving it twice from two different
shapes is what makes the claim evidence rather than a restatement.
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

# `cycle-boundary-v1`, restated: 86,400 target seconds cut by the pinned M1
# three-second commit interval.
CYCLE_BLOCKS = 86_400 // 3

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

# Each kind's body, as a hand-written table of field widths.
BODY_FIELD_WIDTHS: dict[int, tuple[int, ...]] = {
    1: (32, 8),
    2: (4, 1, 4),
    3: (4, 2),
    4: (4, 2, 4),
    5: (4, 2),
    6: (1, 32, 32, 8, 32),
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
    14: "WINDOW_NOT_FINAL",
    15: "PERMISSION_NOT_FOUND",
    16: "INVALID_WINNER_SET",
    17: "INVALID_CHANNEL",
    18: "MISSING_RESEARCH_INPUT",
    19: "INVALID_RESEARCH_INPUT",
    20: "NOT_ELIGIBLE",
    21: "CHANNEL_CAP",
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

# The economy model's twenty-four declared codes, restated by hand from
# `founder-economy-simulator-v3.md`.
MODEL_RESULT_CODES: tuple[str, ...] = (
    "OK", "CYCLE_RANGE", "INVALID_REFERRER", "REPLAY", "SEAT_NOT_ACTIVATED",
    "MISSING_UPTIME_RECORD", "INVALID_UPTIME_RECORD", "INCONSISTENT_UPTIME_RECORD",
    "PERMISSION_NOT_FOUND", "INVALID_CHANNEL", "ZERO_AMOUNT",
    "MISSING_RESEARCH_INPUT", "INVALID_RESEARCH_INPUT", "NOT_ELIGIBLE",
    "CHANNEL_CAP", "ARITHMETIC_OVERFLOW", "INVARIANT", "HEIGHT_RANGE",
    "HEIGHT_NOT_MONOTONIC", "WINDOW_BEFORE_ISSUANCE", "WINDOW_AFTER_ISSUANCE",
    "WINDOW_NOT_FOR_CYCLE", "SEAT_NOT_IN_SCOPE", "INCOMPLETE_UPTIME_RECORD",
)

# Version-two genesis, as a hand-written field table.
GENESIS_FIELD_WIDTHS: tuple[int, ...] = (4, 2, 4, 8, 8, 8, 8, 32, 4)
ACCOUNT_ENTRY_BYTES = 48
RECEIPT_FIELD_WIDTHS: tuple[int, ...] = (4, 2, 32, 1, 1, 8, 8)

# Economy state entry widths, restated as (key, value) pairs. A `None` value
# width is the one variable-width value, the window result.
ENTRY_WIDTHS: dict[int, tuple[int, int | None]] = {
    1: (5, 13),
    2: (2, 16),
    3: (7, 1),
    4: (7, 0),
    5: (33, 0),
    6: (34, 8),
    7: (1, 8),
    8: (9, None),
}
WINDOW_RESULT_FIXED_VALUE_BYTES = 44


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


def signed_length(kind: int, winner_count: int = 0) -> int:
    variable = 4 * winner_count if kind == 4 else 0
    return HEADER_BYTES + fixed_body_bytes(kind) + variable + TRAILER_BYTES + SIGNATURE_BYTES


def genesis_prefix_bytes() -> int:
    return sum(GENESIS_FIELD_WIDTHS)


def max_genesis_accounts() -> int:
    return (MAX_OBJECT_BYTES - genesis_prefix_bytes()) // ACCOUNT_ENTRY_BYTES


def receipt_bytes() -> int:
    return sum(RECEIPT_FIELD_WIDTHS)


def entry_bytes(kind: int, in_scope_seats: int = 0) -> int:
    key_width, value_width = ENTRY_WIDTHS[kind]
    if value_width is None:
        value_width = WINDOW_RESULT_FIXED_VALUE_BYTES + (in_scope_seats + 7) // 8
    return key_width + value_width


def equal_split(portion: int, winner_count: int) -> tuple[int, int]:
    if winner_count == 0:
        return 0, portion
    share = portion // winner_count
    return share, portion - share * winner_count
