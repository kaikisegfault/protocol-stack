"""The independent derivation of `economy-transition-v5`'s recorded values.

Like version four's, this module imports nothing from `simulation/`: every
value it produces comes from the accepted documents rather than from the model
it is checking.

**It reaches those documents through version four's accepted derivation rather
than through a second transcription of them.** Version five changes eight
labels, four version fields, and one body field's meaning; everything else it
restates — the version-one transfer field table, the Founder Constitution's
capacity figures, the channel order, the result-code space, the entry widths,
the digest and Merkle constructions — is version four's, verified on
2026-08-15 by the hosted matrix over 441 vectors. Copying all of it to change
eight strings would put a transcription risk into the one artifact whose whole
job is to be a second opinion, and would leave two hand-written restatements of
one accepted table with nothing keeping them equal.

The module is loaded by path because both files are named `expected.py`. That
is deliberate: the loaded module is version four's accepted artifact, unedited,
and this file's diff shows exactly what version five derives differently.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1]
_VERSION_FOUR = _TOOLS / "economy-transition-v4-vectors" / "expected.py"


def _load_version_four():
    specification = importlib.util.spec_from_file_location(
        "expected_version_four", _VERSION_FOUR
    )
    if specification is None or specification.loader is None:
        raise ImportError(f"cannot load version four's derivation from {_VERSION_FOUR}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


_v4 = _load_version_four()

# Version four's accepted derivation, re-exported by name. Every one of these
# is a hand restatement of an accepted document, and version five changes none
# of the documents behind them.
MAX_U64 = _v4.MAX_U64
MAX_OBJECT_BYTES = _v4.MAX_OBJECT_BYTES
FOUNDER_SEAT_CAPACITY = _v4.FOUNDER_SEAT_CAPACITY
ISSUANCE_CYCLES_PER_SEAT = _v4.ISSUANCE_CYCLES_PER_SEAT
MAX_SEAT_ID = _v4.MAX_SEAT_ID
MAXIMUM_SUPPLY_ATOMIC = _v4.MAXIMUM_SUPPLY_ATOMIC
FOUNDER_OPERATOR_LEG_ATOMIC = _v4.FOUNDER_OPERATOR_LEG_ATOMIC
ACTIVITY_THRESHOLD_SECONDS = _v4.ACTIVITY_THRESHOLD_SECONDS
REFERRAL_LEG_ATOMIC = _v4.REFERRAL_LEG_ATOMIC
MAX_SEATS_PER_IDENTITY = _v4.MAX_SEATS_PER_IDENTITY
CYCLE_BLOCKS = _v4.CYCLE_BLOCKS
MINT_ACCUMULATION_CAP = _v4.MINT_ACCUMULATION_CAP
ASSIGNMENT_LAG_WINDOWS = _v4.ASSIGNMENT_LAG_WINDOWS
MAX_SEAT_MANAGERS = _v4.MAX_SEAT_MANAGERS
MAX_IDENTITY_ADDRESSES = _v4.MAX_IDENTITY_ADDRESSES

CHANNEL_ORDER = _v4.CHANNEL_ORDER
DIRECT_ISSUE_CHANNELS = _v4.DIRECT_ISSUE_CHANNELS

TRANSFER_FIELDS = _v4.TRANSFER_FIELDS
UNSIGNED_TRANSFER_BYTES = _v4.UNSIGNED_TRANSFER_BYTES
SIGNATURE_BYTES = _v4.SIGNATURE_BYTES
SIGNED_TRANSFER_BYTES = _v4.SIGNED_TRANSFER_BYTES
HEADER_BYTES = _v4.HEADER_BYTES
TRAILER_BYTES = _v4.TRAILER_BYTES

BODY_FIELD_WIDTHS = _v4.BODY_FIELD_WIDTHS
KIND_NAMES = _v4.KIND_NAMES

RESULT_CODES = _v4.RESULT_CODES
VERSION_ONE_TRANSFER_RESULTS = _v4.VERSION_ONE_TRANSFER_RESULTS
VERSION_THREE_RESULT_COUNT = _v4.VERSION_THREE_RESULT_COUNT
MODEL_RESULT_CODES = _v4.MODEL_RESULT_CODES

GENESIS_FIELD_WIDTHS = _v4.GENESIS_FIELD_WIDTHS
ACCOUNT_ENTRY_BYTES = _v4.ACCOUNT_ENTRY_BYTES
RECEIPT_FIELD_WIDTHS = _v4.RECEIPT_FIELD_WIDTHS

KEY_FIELD_WIDTHS = _v4.KEY_FIELD_WIDTHS
ENTRY_KEY_FIELDS = _v4.ENTRY_KEY_FIELDS
ENTRY_WIDTHS = _v4.ENTRY_WIDTHS
CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES = _v4.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES
BENEFICIARY_KINDS = _v4.BENEFICIARY_KINDS

BASE_PERMISSION_DISPLAY = _v4.BASE_PERMISSION_DISPLAY
ATOMIC_PER_DISPLAY = _v4.ATOMIC_PER_DISPLAY

domain = _v4.domain
digest = _v4.digest
merkle = _v4.merkle
be = _v4.be
flat_unsigned_transfer = _v4.flat_unsigned_transfer
fixed_body_bytes = _v4.fixed_body_bytes
signed_length = _v4.signed_length
genesis_prefix_bytes = _v4.genesis_prefix_bytes
max_genesis_accounts = _v4.max_genesis_accounts
receipt_bytes = _v4.receipt_bytes
key_bytes_from_fields = _v4.key_bytes_from_fields
keys_a_seat_and_a_cycle = _v4.keys_a_seat_and_a_cycle
bitmap_bytes = _v4.bitmap_bytes
entry_bytes = _v4.entry_bytes
base_permission_legs = _v4.base_permission_legs
accrues = _v4.accrues
walk_range = _v4.walk_range
Registry = _v4.Registry

# --- What version five derives differently ------------------------------------

# The eight messages, restated from the version-five specification. The field
# widths are version four's; the labels are not.
HUB_MESSAGES: dict[str, tuple[str, tuple[int, ...]]] = {
    "registration": ("protocol-stack:v5:hub-registration", (32, 32, 32, 32, 8)),
    "address_add": ("protocol-stack:v5:hub-address-add", (32, 32, 32, 8)),
    "address_remove": ("protocol-stack:v5:hub-address-remove", (32, 32, 32, 8)),
    "purchase": ("protocol-stack:v5:seat-purchase", (32, 32, 4, 32, 8)),
    "activation": ("protocol-stack:v5:seat-activation", (32, 32, 4, 8)),
    "mint": ("protocol-stack:v5:seat-mint", (32, 32, 4, 8)),
    "mint_biometric_disable": (
        "protocol-stack:v5:mint-biometric-disable",
        (32, 32, 4, 8),
    ),
    "manager": ("protocol-stack:v5:seat-manager", (32, 32, 4, 32, 8)),
}
VERIFIER_SIGNED_MESSAGES: tuple[str, ...] = ("registration",)

VERSION_FIVE_LABELS: dict[str, str] = {
    "chain_id": "protocol-stack:v5:chain-id",
    "state_root": "protocol-stack:v5:state-root",
    "economy_tree": "protocol-stack:v5:economy",
}
VERSION_FIVE_SCHEMA_VERSIONS: dict[str, int] = {
    "state_root": 5,
    "genesis": 5,
    "receipt": 5,
}

# Kind 11's corrected body, as a hand-written field table. The widths are
# version four's; what the 32-byte field at offset 80 *is* is not.
ADD_ADDRESS_BODY_FIELDS: tuple[tuple[str, int, int], ...] = (
    ("hub_identity_hash", 0, 32),
    ("hub_signature", 32, 64),
)
ADD_ADDRESS_REJECTION_ORDER: tuple[str, ...] = (
    "NOT_HUB_VERIFIED",
    "REPLAY",
    "ADDRESS_LIMIT",
    "UNAUTHORIZED",
)

# Where a chain obtains the identity each message binds, restated from the
# specification. Version four's address add had no answer, which is the defect.
MESSAGE_IDENTITY_SOURCE: dict[str, str] = {
    "registration": "body",
    "address_add": "body",
    "address_remove": "named_account_address_entry",
    "purchase": "sender_address_entry",
    "activation": "seat_entry",
    "mint": "seat_entry",
    "mint_biometric_disable": "seat_entry",
    "manager": "seat_entry",
}
VERSION_FOUR_ADDRESS_ADD_IDENTITY_SOURCE = "none"

# The accepted version-one account derivation, restated. Version five is the
# first transition contract whose evidence needs it, because it is the first in
# which a signed message is built from the sender.
ACCOUNT_ID_LABEL = "protocol-stack:v1:account"
ACCOUNT_ID_DOMAIN = 0x01

# Every predecessor construction, as the labels that version recorded.
PREDECESSOR_STATE_ROOTS: dict[int, str] = {
    1: "protocol-stack:v1:state-root",
    2: "protocol-stack:v2:state-root",
    3: "protocol-stack:v3:state-root",
    4: "protocol-stack:v4:state-root",
}
PREDECESSOR_CHAIN_IDS: dict[int, str] = {
    2: "protocol-stack:v2:chain-id",
    3: "protocol-stack:v3:chain-id",
    4: "protocol-stack:v4:chain-id",
}
PREDECESSOR_ECONOMY_TREES: dict[int, str] = {
    2: "protocol-stack:v2:economy",
    3: "protocol-stack:v3:economy",
    4: "protocol-stack:v4:economy",
}


def account_id(public_key: bytes) -> bytes:
    """`H(D("protocol-stack:v1:account") || 0x01 || public_key)`."""
    return digest(ACCOUNT_ID_LABEL, bytes([ACCOUNT_ID_DOMAIN]) + public_key)


def hub_message_bytes(name: str) -> int:
    label, widths = HUB_MESSAGES[name]
    return len(domain(label)) + sum(widths)


def add_address_body_bytes() -> int:
    return sum(width for _, _, width in ADD_ADDRESS_BODY_FIELDS)
