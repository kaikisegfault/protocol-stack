"""The independent derivation of `economy-transition-v6`'s recorded values.

Like version four's and version five's, this module imports nothing from
`simulation/`: every value it produces comes from the accepted documents rather
than from the model it is checking.

**It reaches the unchanged documents through version four's accepted derivation
rather than through a second transcription of them.** The version-one transfer
field table, the Founder Constitution's capacity figures, the channel order, the
digest and Merkle constructions, and result codes 0 through 25 are version
four's, verified by the hosted matrix over 441 vectors. Copying all of it to
change a kind table would put a transcription risk into the one artifact whose
whole job is to be a second opinion.

**What is written here by hand is what version six defines for itself**: the two
authorization schemes, the fourteen kinds and their body field widths, the five
retired kinds, the escrow derivation, the posture predicates, the new entry
kinds and their widths, the seat record's new width, the seven new result codes,
and the verified-user channel's arithmetic. All of it is restated from
`docs/specifications/economy-transition-v6.md` rather than imported from the
model.

The module is loaded by path because both files are named `expected.py`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1]
_VERSION_FOUR = _TOOLS / "economy-transition-v4-vectors" / "expected.py"


def _load_version_four():
    specification = importlib.util.spec_from_file_location(
        "expected_version_four_for_six", _VERSION_FOUR
    )
    if specification is None or specification.loader is None:
        raise ImportError(f"cannot load version four's derivation from {_VERSION_FOUR}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


_v4 = _load_version_four()

# Version four's accepted derivation, re-exported by name. Version six changes
# none of the documents behind these.
MAX_U64 = _v4.MAX_U64
MAX_OBJECT_BYTES = _v4.MAX_OBJECT_BYTES
FOUNDER_SEAT_CAPACITY = _v4.FOUNDER_SEAT_CAPACITY
ISSUANCE_CYCLES_PER_SEAT = _v4.ISSUANCE_CYCLES_PER_SEAT
MAX_SEAT_ID = _v4.MAX_SEAT_ID
MAXIMUM_SUPPLY_ATOMIC = _v4.MAXIMUM_SUPPLY_ATOMIC
FOUNDER_OPERATOR_LEG_ATOMIC = _v4.FOUNDER_OPERATOR_LEG_ATOMIC
REFERRAL_LEG_ATOMIC = _v4.REFERRAL_LEG_ATOMIC
MAX_SEATS_PER_IDENTITY = _v4.MAX_SEATS_PER_IDENTITY
CYCLE_BLOCKS = _v4.CYCLE_BLOCKS
MINT_ACCUMULATION_CAP = _v4.MINT_ACCUMULATION_CAP
ASSIGNMENT_LAG_WINDOWS = _v4.ASSIGNMENT_LAG_WINDOWS
CHANNEL_ORDER = _v4.CHANNEL_ORDER
TRANSFER_FIELDS = _v4.TRANSFER_FIELDS
UNSIGNED_TRANSFER_BYTES = _v4.UNSIGNED_TRANSFER_BYTES
SIGNATURE_BYTES = _v4.SIGNATURE_BYTES
SIGNED_TRANSFER_BYTES = _v4.SIGNED_TRANSFER_BYTES
HEADER_BYTES = _v4.HEADER_BYTES
TRAILER_BYTES = _v4.TRAILER_BYTES
GENESIS_FIELD_WIDTHS = _v4.GENESIS_FIELD_WIDTHS
ACCOUNT_ENTRY_BYTES = _v4.ACCOUNT_ENTRY_BYTES
RECEIPT_FIELD_WIDTHS = _v4.RECEIPT_FIELD_WIDTHS
KEY_FIELD_WIDTHS = dict(_v4.KEY_FIELD_WIDTHS)
CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES = _v4.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES
BENEFICIARY_KINDS = _v4.BENEFICIARY_KINDS
ATOMIC_PER_DISPLAY = _v4.ATOMIC_PER_DISPLAY
MODEL_RESULT_CODES = _v4.MODEL_RESULT_CODES

domain = _v4.domain
digest = _v4.digest
merkle = _v4.merkle
be = _v4.be
flat_unsigned_transfer = _v4.flat_unsigned_transfer
genesis_prefix_bytes = _v4.genesis_prefix_bytes
max_genesis_accounts = _v4.max_genesis_accounts
receipt_bytes = _v4.receipt_bytes
bitmap_bytes = _v4.bitmap_bytes
accrues = _v4.accrues
walk_range = _v4.walk_range

# --- what version six defines for itself --------------------------------

SLOT_BLOCKS = 1_200
SLOTS_PER_WINDOW = 24
MAX_SIGNERS_PER_ESCROW = 16

SCHEME_SIGNER = 1
SCHEME_IDENTITY = 2
SCHEMES: dict[int, str] = {
    SCHEME_SIGNER: "signer_key",
    SCHEME_IDENTITY: "hub_identity_key",
}

# Channel 8 has left the reserved set: ADR 0042 decided its eligibility and rate.
DIRECT_ISSUE_CHANNELS: tuple[int, ...] = (5, 6, 9)

KIND_NAMES: dict[int, str] = {
    1: "native_transfer",
    2: "purchase_seat",
    3: "activate_seat",
    4: "mint_node",
    5: "mint_referral",
    6: "direct_issue",
    10: "hub_register",
    13: "escrow_create",
    14: "escrow_delete",
    15: "signer_add",
    16: "signer_revoke",
    17: "set_security_posture",
    18: "mint_verified_user",
    19: "native_transfer_verified",
}

RETIRED_KINDS: dict[int, str] = {
    7: "mint_node_verified",
    8: "set_mint_biometric",
    9: "add_manager",
    11: "hub_add_address",
    12: "hub_remove_address",
}

# Each body restated as its named fields, so a width is derived from a layout
# rather than copied as a number.
BODY_FIELD_WIDTHS: dict[int, tuple[int, ...]] = {
    1: (32, 8),
    2: (4, 1, 32, 64),
    3: (4, 64),
    4: (4, 32, 64),
    5: (32, 64),
    6: (1, 32, 32, 8, 32),
    10: (32, 32, 64),
    13: (32, 32),
    14: (32, 32, 32),
    15: (32, 32, 32),
    16: (32, 32, 32),
    17: (1, 8, 4, 64),
    18: (32, 64),
    19: (32, 8, 64),
}

KIND_SCHEME: dict[int, int] = {
    1: SCHEME_SIGNER,
    2: SCHEME_SIGNER,
    3: SCHEME_SIGNER,
    4: SCHEME_SIGNER,
    5: SCHEME_SIGNER,
    6: SCHEME_SIGNER,
    10: SCHEME_IDENTITY,
    13: SCHEME_IDENTITY,
    14: SCHEME_IDENTITY,
    15: SCHEME_IDENTITY,
    16: SCHEME_IDENTITY,
    17: SCHEME_SIGNER,
    18: SCHEME_SIGNER,
    19: SCHEME_SIGNER,
}

CONFIRMABLE_MINTS: tuple[int, ...] = (4, 5, 18)
NON_ISSUING_KINDS: tuple[int, ...] = (1, 2, 3, 13, 14, 15, 16, 17, 19)

# Six messages, each restated as the widths of its concatenated terms after the
# domain prefix.
HUB_MESSAGES: dict[str, tuple[str, tuple[int, ...]]] = {
    "registration": ("protocol-stack:v6:hub-registration", (32, 32, 32, 32, 8)),
    "purchase": ("protocol-stack:v6:seat-purchase", (32, 32, 4, 8)),
    "activation": ("protocol-stack:v6:seat-activation", (32, 32, 4, 8)),
    "mint": ("protocol-stack:v6:mint-confirm", (32, 32, 1, 4, 32, 8)),
    "posture_relax": ("protocol-stack:v6:posture-relax", (32, 32, 32, 1, 8, 4, 8)),
    "transfer_confirm": ("protocol-stack:v6:transfer-confirm", (32, 32, 32, 32, 8, 8)),
}
VERIFIER_SIGNED_MESSAGES: tuple[str, ...] = ("registration",)

# Admission's own three-code space, separate from the execution space and
# unchanged since version one.
ADMISSION_CODES: dict[int, str] = {
    1: "MALFORMED_TRANSACTION",
    2: "WRONG_CHAIN",
    3: "INVALID_SIGNATURE",
}

RESULT_CODES: dict[int, str] = dict(_v4.RESULT_CODES) | {
    26: "SIGNER_NOT_FOUND",
    27: "RECIPIENT_NOT_REGISTERED",
    28: "ESCROW_NOT_FOUND",
    29: "ESCROW_NOT_OWNED",
    30: "ESCROW_NOT_EMPTY",
    31: "SIGNER_LIMIT",
    32: "NOT_ENROLLED",
}
VERSION_FOUR_RESULT_COUNT = 26
UNREACHABLE_RESULT_CODES: tuple[int, ...] = (4, 23, 25)

ENTRY_KEY_FIELDS: dict[int, tuple[str, ...]] = {
    1: ("seat_id",),
    2: ("channel_id",),
    3: ("cycle_window",),
    4: ("hub_identity_hash",),
    5: ("decision_id",),
    6: ("beneficiary_kind", "beneficiary_id"),
    7: ("channel_id",),
    8: (),
    10: ("hub_identity_hash",),
    12: (),
    13: ("escrow_id",),
    14: ("signer_id",),
    15: ("hub_identity_hash",),
    16: (),
}

RETIRED_ENTRY_KINDS: dict[int, str] = {9: "seat_manager", 11: "hub_address"}

ENTRY_NAMES: dict[int, str] = {
    1: "seat",
    2: "channel",
    3: "cycle_assignment",
    4: "referral_balance",
    5: "direct_decision",
    6: "typed_custody",
    7: "carry",
    8: "verifier_key",
    10: "hub_identity",
    12: "unreferred_pool",
    13: "escrow",
    14: "signer",
    15: "verified_user_enrollment",
    16: "verified_user_counter",
}

# Each value restated as the widths of its named fields.
ENTRY_VALUE_FIELDS: dict[int, tuple[int, ...] | None] = {
    1: (32, 1, 32, 1, 8, 8),
    2: (8, 8),
    3: None,
    4: (8, 8, 8),
    5: (),
    6: (8,),
    7: (8,),
    8: (32,),
    10: (32, 8, 4, 4, 4),
    12: (8, 8),
    13: (32, 1, 8, 4, 4),
    14: (32,),
    15: (8, 8, 8),
    16: (8,),
}

KEY_FIELD_WIDTHS.update({"escrow_id": 32, "signer_id": 32})

ESCROW_LABEL = "protocol-stack:v6:escrow"
ACCOUNT_LABEL = "protocol-stack:v1:account"
CHAIN_ID_LABEL = "protocol-stack:v6:chain-id"
STATE_ROOT_LABEL = "protocol-stack:v6:state-root"
ECONOMY_TREE_PREFIX = "protocol-stack:v6:economy"
STATE_ROOT_SCHEMA_VERSION = 6
GENESIS_SCHEMA_VERSION = 6
RECEIPT_VERSION = 6

VERIFIED_USER_CHANNEL = 8
VERIFIED_USER_POPULATION = 1_000_000
VERIFIED_USER_CHANNEL_CAP_ATOMIC = 125_001_000_000_000_000
VERIFIED_USER_CYCLES = ISSUANCE_CYCLES_PER_SEAT


def fixed_body_bytes(kind: int) -> int:
    return sum(BODY_FIELD_WIDTHS[kind])


def unsigned_length(kind: int) -> int:
    return HEADER_BYTES + fixed_body_bytes(kind) + TRAILER_BYTES


def signed_length(kind: int) -> int:
    return unsigned_length(kind) + SIGNATURE_BYTES


def hub_message_bytes(name: str) -> int:
    label, widths = HUB_MESSAGES[name]
    return len(domain(label)) + sum(widths)


def key_bytes_from_fields(kind: int) -> int:
    return 1 + sum(KEY_FIELD_WIDTHS[field] for field in ENTRY_KEY_FIELDS[kind])


def value_bytes_from_fields(kind: int, bitmap_bits: int = 0) -> int:
    widths = ENTRY_VALUE_FIELDS[kind]
    if widths is None:
        return CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES + 2 * bitmap_bytes(bitmap_bits)
    return sum(widths)


def entry_bytes(kind: int, bitmap_bits: int = 0) -> int:
    return key_bytes_from_fields(kind) + value_bytes_from_fields(kind, bitmap_bits)


def escrow_id(hub_identity_hash: bytes, index: int) -> bytes:
    """The version-six derivation, restated from the specification."""
    return digest(ESCROW_LABEL, hub_identity_hash + be(index, 4))


def signer_id(public_key: bytes) -> bytes:
    """The accepted version-one derivation, restated with its subject moved."""
    return digest(ACCOUNT_LABEL, b"\x01" + public_key)


def slot_of(height: int) -> int:
    return (height % CYCLE_BLOCKS) // SLOT_BLOCKS


def requires_confirmation(
    on: bool, minimum: int, mask: int, amount: int, height: int
) -> bool:
    if not on:
        return False
    if amount < minimum:
        return False
    return not (mask >> slot_of(height)) & 1


def relaxes(
    current: tuple[bool, int, int], proposed: tuple[bool, int, int]
) -> bool:
    """The three disjuncts, restated from the specification's own wording."""
    on, minimum, mask = current
    proposed_on, proposed_minimum, proposed_mask = proposed
    if on and not proposed_on:
        return True
    if proposed_minimum > minimum:
        return True
    return bool(proposed_mask & ~mask)


def verified_user_daily_atomic() -> int:
    """The rate the three founder-supplied figures determine, with no remainder."""
    per_user, remainder = divmod(
        VERIFIED_USER_CHANNEL_CAP_ATOMIC, VERIFIED_USER_POPULATION
    )
    if remainder:
        raise ValueError("the channel cap does not divide by the population")
    daily, remainder = divmod(per_user, VERIFIED_USER_CYCLES)
    if remainder:
        raise ValueError("the per-user allocation does not divide by the period")
    return daily


def verified_user_collection(
    mark: int, enrolled_window: int, height: int
) -> tuple[int, int, int]:
    """`(window_start, collectable_end, count)` for a kind-18 mint.

    Restated from the specification rather than imported, so a model that moved
    the cap's application point disagrees here rather than agreeing with itself.
    """
    last_completed = (height // CYCLE_BLOCKS) - 1
    period_end = enrolled_window + VERIFIED_USER_CYCLES - 1
    collectable_end = min(last_completed, period_end)
    if collectable_end <= mark:
        return mark, mark, 0
    window_start = max(mark, collectable_end - MINT_ACCUMULATION_CAP)
    return window_start, collectable_end, collectable_end - window_start


def hub_message(name: str, terms: list[bytes]) -> bytes:
    """A message built from its own field table, so a width that moved fails.

    The terms are supplied in offset order and each is checked against the
    width the table records, which is what makes this a second construction
    rather than a second call into the model.
    """
    label, widths = HUB_MESSAGES[name]
    if len(terms) != len(widths):
        raise ValueError(f"{name} takes {len(widths)} terms")
    raw = domain(label)
    for index, (term, width) in enumerate(zip(terms, widths)):
        if len(term) != width:
            raise ValueError(f"{name} term {index} is not {width} octets")
        raw += term
    return raw


def receipt_hex(
    transaction_id: bytes, kind: int, code: int, fee: int, issued: int
) -> str:
    """The 56-byte receipt built from its own field-width table."""
    parts = [b"PSRC", be(RECEIPT_VERSION, 2), transaction_id, be(kind, 1), be(code, 1),
             be(fee, 8), be(issued, 8)]
    raw = b""
    for part, width in zip(parts, RECEIPT_FIELD_WIDTHS):
        if len(part) != width:
            raise ValueError("receipt field is not its recorded width")
        raw += part
    return raw.hex()


def genesis_bytes(
    network_id: int,
    supply_limit: int,
    fixed_fee: int,
    manifest_digest: bytes,
    verifier_key: bytes,
) -> bytes:
    """Version-six genesis built from its own field-width table.

    Total supply, the initial fee pool, and the account count are all zero,
    which version six requires rather than merely expects.
    """
    parts = [b"PSGN", be(GENESIS_SCHEMA_VERSION, 2), be(network_id, 4),
             be(supply_limit, 8), be(0, 8), be(fixed_fee, 8), be(0, 8),
             manifest_digest, verifier_key, be(0, 4)]
    raw = b""
    for part, width in zip(parts, GENESIS_FIELD_WIDTHS):
        if len(part) != width:
            raise ValueError("genesis field is not its recorded width")
        raw += part
    return raw


def state_root_hex(
    label: str,
    schema_version: int,
    chain_id: bytes,
    height: int,
    supply_limit: int,
    total_supply: int,
    fee_pool: int,
    accounts: list[tuple[bytes, int, int]],
    economy: dict[bytes, bytes],
    tree_prefix: str,
) -> str:
    """The root preimage, assembled term by term from the specification."""
    account_leaves = [
        account + be(balance, 8) + be(nonce, 8) for account, balance, nonce in accounts
    ]
    economy_leaves = [
        be(len(key), 4) + key + be(len(value), 4) + value
        for key, value in sorted(economy.items())
    ]
    preimage = (
        be(schema_version, 2)
        + chain_id
        + be(height, 8)
        + be(supply_limit, 8)
        + be(total_supply, 8)
        + be(fee_pool, 8)
        + be(len(accounts), 8)
        + merkle(account_leaves, "protocol-stack:v1:state")
        + be(len(economy), 8)
        + merkle(economy_leaves, tree_prefix)
    )
    return digest(label, preimage).hex()


def verified_user_remainder_at(cycles: int) -> int:
    """What the channel cap leaves over at a period other than 731.

    ADR 0042's figure: `cap mod (population * cycles)`. It is 420,000,000 atomic
    at 730 and zero at 731, which is what fixes the period rather than making it
    a choice.
    """
    return VERIFIED_USER_CHANNEL_CAP_ATOMIC % (VERIFIED_USER_POPULATION * cycles)


def per_person_storage_bytes(escrows: int, signers: int) -> int:
    """`85 + 130 * escrows + 65 * signers`, derived from the entry widths."""
    identity = entry_bytes(10)
    escrow = entry_bytes(13) + ACCOUNT_ENTRY_BYTES
    signer = entry_bytes(14)
    return identity + escrow * escrows + signer * signers
