"""The independent derivation of `economy-transition-v4`'s recorded values.

This module imports nothing from `simulation/`. It restates by hand the
version-one field tables from `protocol-primitives-v1` and `ledger-transition-v1`,
the Founder Constitution's capacity figures, the accepted manifest's channel
order, and the accepted digest and Merkle constructions, so a value both this
module and the model reach has been derived from the accepted documents and from
the implementation independently.

The structural independence version two established is kept: this module builds
the version-one transfer as one flat 136-byte field table, exactly as
`protocol-primitives-v1` writes it, while the model builds it as a shared
header, a kind-specific body, and a shared trailer.

Version four adds a second registry to derive independently. The HUB registry's
two counts, its bounds, and the constitution's per-human seat bound are
reimplemented here from the specification's prose, so a defect that kept a
self-consistent registry would still have to keep the same one twice.
"""

from __future__ import annotations

import hashlib

MAX_U64 = (1 << 64) - 1
MAX_OBJECT_BYTES = 1_048_576

# Founder Constitution, restated by hand.
FOUNDER_SEAT_CAPACITY = 100_000
ISSUANCE_CYCLES_PER_SEAT = 731
MAX_SEAT_ID = FOUNDER_SEAT_CAPACITY - 1
MAXIMUM_SUPPLY_ATOMIC = 5_699_395_010_000_000_000
FOUNDER_OPERATOR_LEG_ATOMIC = 34_200_000_000
ACTIVITY_THRESHOLD_SECONDS = 18 * 3_600
REFERRAL_LEG_ATOMIC = 3_420_000_000
# "One human may control no more than 1,000 seats."
MAX_SEATS_PER_IDENTITY = 1_000

CYCLE_BLOCKS = 86_400 // 3
MINT_ACCUMULATION_CAP = 30
ASSIGNMENT_LAG_WINDOWS = 2
MAX_SEAT_MANAGERS = 16
MAX_IDENTITY_ADDRESSES = 16

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

HEADER_BYTES = sum(width for name, _, width in TRANSFER_FIELDS if name in
                   {"magic", "schema_version", "transaction_kind", "chain_id",
                    "signature_scheme", "sender_public_key", "nonce"})
TRAILER_BYTES = sum(width for name, _, width in TRANSFER_FIELDS if name in
                    {"fee_limit", "valid_until_height"})

# Each kind's body, as a hand-written table of field widths. Two pairs coincide
# — kinds 3 and 7, kinds 11 and 12 — which is the case version two anticipated
# when it required dispatch on the kind byte.
BODY_FIELD_WIDTHS: dict[int, tuple[int, ...]] = {
    1: (32, 8),
    2: (4, 32, 1, 32, 64),
    3: (4, 64),
    4: (4,),
    5: (),
    6: (1, 32, 32, 8, 32),
    7: (4, 64),
    8: (4, 1, 64),
    9: (4, 32, 64),
    10: (32, 32, 64),
    11: (32, 64),
    12: (32, 64),
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
    10: "hub_register",
    11: "hub_add_address",
    12: "hub_remove_address",
}

# The eight messages of the HUB signature family, each as its label and the
# widths of the fields that follow it. Only the first is signed by the
# ecosystem verifier key.
HUB_MESSAGES: dict[str, tuple[str, tuple[int, ...]]] = {
    "registration": ("protocol-stack:v4:hub-registration", (32, 32, 32, 32, 8)),
    "address_add": ("protocol-stack:v4:hub-address-add", (32, 32, 32, 8)),
    "address_remove": ("protocol-stack:v4:hub-address-remove", (32, 32, 32, 8)),
    "purchase": ("protocol-stack:v4:seat-purchase", (32, 32, 4, 32, 8)),
    "activation": ("protocol-stack:v4:seat-activation", (32, 32, 4, 8)),
    "mint": ("protocol-stack:v4:seat-mint", (32, 32, 4, 8)),
    "mint_biometric_disable": (
        "protocol-stack:v4:mint-biometric-disable",
        (32, 32, 4, 8),
    ),
    "manager": ("protocol-stack:v4:seat-manager", (32, 32, 4, 32, 8)),
}
VERIFIER_SIGNED_MESSAGES: tuple[str, ...] = ("registration",)

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
    24: "SEAT_LIMIT",
    25: "ADDRESS_LIMIT",
}

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
VERSION_THREE_RESULT_COUNT = 24

MODEL_RESULT_CODES: tuple[str, ...] = (
    "OK", "CYCLE_RANGE", "INVALID_REFERRER", "REPLAY", "SEAT_NOT_ACTIVATED",
    "MISSING_UPTIME_RECORD", "INVALID_UPTIME_RECORD", "INCONSISTENT_UPTIME_RECORD",
    "PERMISSION_NOT_FOUND", "INVALID_CHANNEL", "ZERO_AMOUNT",
    "MISSING_RESEARCH_INPUT", "INVALID_RESEARCH_INPUT", "NOT_ELIGIBLE",
    "CHANNEL_CAP", "ARITHMETIC_OVERFLOW", "INVARIANT", "HEIGHT_RANGE",
    "HEIGHT_NOT_MONOTONIC", "WINDOW_BEFORE_ISSUANCE", "WINDOW_AFTER_ISSUANCE",
    "WINDOW_NOT_FOR_CYCLE", "SEAT_NOT_IN_SCOPE", "INCOMPLETE_UPTIME_RECORD",
)

GENESIS_FIELD_WIDTHS: tuple[int, ...] = (4, 2, 4, 8, 8, 8, 8, 32, 32, 4)
VERSION_ONE_GENESIS_PREFIX_BYTES = 46
ACCOUNT_ENTRY_BYTES = 48
RECEIPT_FIELD_WIDTHS: tuple[int, ...] = (4, 2, 32, 1, 1, 8, 8)

KEY_FIELD_WIDTHS: dict[str, int] = {
    "seat_id": 4,
    "channel_id": 1,
    "cycle_window": 8,
    "hub_identity_hash": 32,
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
    4: ("hub_identity_hash",),
    5: ("decision_id",),
    6: ("beneficiary_kind", "beneficiary_id"),
    7: ("channel_id",),
    8: (),
    9: ("seat_id", "manager_account_id"),
    10: ("hub_identity_hash",),
    11: ("account_id",),
    12: (),
}

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
    10: (33, 48),
    11: (33, 32),
    12: (1, 16),
}
CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES = 24

BENEFICIARY_KINDS: dict[int, str] = {
    1: "venture_escrow",
    2: "community_grants_escrow",
    3: "developer_incentives_escrow",
    4: "system_creator_company",
    5: "direct_beneficiary",
}

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


def hub_message_bytes(name: str) -> int:
    label, widths = HUB_MESSAGES[name]
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
        value_width = CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES + 2 * bitmap_bytes(bitmap_bits)
    return key_width + value_width


def base_permission_legs() -> dict[int, int]:
    legs = {}
    for channel, display in BASE_PERMISSION_DISPLAY:
        whole, _, fraction = display.partition(".")
        tenths = int(whole) * 10 + int(fraction)
        legs[channel] = tenths * ATOMIC_PER_DISPLAY // 10
    return legs


def accrues(cycle_window: int, mark: int) -> bool:
    return cycle_window <= mark + MINT_ACCUMULATION_CAP


def walk_range(mark: int, last_assigned: int | None):
    assert mark >= 0
    if last_assigned is None or mark >= last_assigned:
        return None
    return mark + 1, min(last_assigned, mark + MINT_ACCUMULATION_CAP)


class Registry:
    """A second implementation of the HUB registry, from the specification.

    Written from the prose rather than from the model, so a defect that kept a
    self-consistent registry would still have to keep the same one twice.
    """

    def __init__(self) -> None:
        self.identities: dict[bytes, dict] = {}
        self.addresses: dict[bytes, bytes] = {}

    def register(self, identity: bytes, key: bytes, account: bytes, height: int) -> str:
        if identity in self.identities:
            return "REPLAY"
        if account in self.addresses:
            return "REPLAY"
        self.identities[identity] = {
            "key": key, "height": height, "addresses": 1, "seats": 0
        }
        self.addresses[account] = identity
        return "SUCCESS"

    def add_address(self, identity: bytes, account: bytes) -> str:
        record = self.identities.get(identity)
        if record is None:
            return "NOT_HUB_VERIFIED"
        if account in self.addresses:
            return "REPLAY"
        if record["addresses"] >= MAX_IDENTITY_ADDRESSES:
            return "ADDRESS_LIMIT"
        self.addresses[account] = identity
        record["addresses"] += 1
        return "SUCCESS"

    def remove_address(self, account: bytes) -> str:
        identity = self.addresses.get(account)
        if identity is None:
            return "NOT_HUB_VERIFIED"
        del self.addresses[account]
        self.identities[identity]["addresses"] -= 1
        return "SUCCESS"

    def claim_seat(self, identity: bytes) -> str:
        record = self.identities.get(identity)
        if record is None:
            return "NOT_HUB_VERIFIED"
        if record["seats"] >= MAX_SEATS_PER_IDENTITY:
            return "SEAT_LIMIT"
        record["seats"] += 1
        return "SUCCESS"
