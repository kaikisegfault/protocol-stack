"""Fixed constants, tables, and code spaces of `economy-transition-v4`.

Every founder-directed figure here is read from an accepted contract rather than
restated. The channel identifiers are the accepted manifest's array indexes, the
seat capacity, the per-person seat bound, and the issuance-cycle count come from
the manifest layer, and the window grid comes from the cycle-boundary contract,
so one founder-directed value keeps one home.

Version four makes HUB verification the root of identity. A registration records
the person's own public key, and every later proof of that person is a signature
by it; the ecosystem verifier signs registrations and nothing else. The
settlement — the accumulation cap, the cycle-assignment record, the bounded mint
walk — is version three's and is imported rather than copied, because a second
implementation of one accepted contract has nothing keeping the two equal.
"""

from __future__ import annotations

from simulation.cycle_boundary import contract as boundary
from simulation.founder_economy_v2 import contract as manifest

MAX_U64 = (1 << 64) - 1

# Generic canonical bounds inherited from protocol-primitives-v1.
MAX_OBJECT_BYTES = 1_048_576

FOUNDER_SEAT_CAPACITY = manifest.FOUNDER_SEAT_CAPACITY
ISSUANCE_CYCLES_PER_SEAT = manifest.ISSUANCE_CYCLES_PER_SEAT
MAX_SEAT_ID = FOUNDER_SEAT_CAPACITY - 1
MAX_CYCLE_INDEX = ISSUANCE_CYCLES_PER_SEAT - 1
CYCLE_BLOCKS = boundary.CYCLE_BLOCKS
ACTIVITY_THRESHOLD_SECONDS = manifest.ACTIVITY_THRESHOLD_SECONDS

# The constitution's per-human bound, unenforceable before version four because
# no earlier version could tell that two identities were one person.
MAX_SEATS_PER_IDENTITY = manifest.MAXIMUM_SEATS_PER_PERSON

MANIFEST_DIGEST_HEX = manifest.MANIFEST_DIGEST

# The envelope. Unchanged since version two, and the whole compatibility
# argument: the header is the accepted version-one transfer's first 80 bytes and
# the trailer its last 16.
HEADER_BYTES = 80
TRAILER_BYTES = 16
SIGNATURE_BYTES = 64

TRANSACTION_MAGIC = b"PSTX"
RECEIPT_MAGIC = b"PSRC"
GENESIS_MAGIC = b"PSGN"

ENVELOPE_SCHEMA_VERSION = 1
RECEIPT_VERSION = 4
GENESIS_SCHEMA_VERSION = 4
SIGNATURE_SCHEME = 1

# Version-one labels, deliberately not re-versioned: re-versioning would destroy
# the kind-1 byte identity for separation the preimage already carries.
SIGN_LABEL = "protocol-stack:v1:tx-sign"
TX_ID_LABEL = "protocol-stack:v1:tx-id"

CHAIN_ID_LABEL = "protocol-stack:v4:chain-id"
STATE_ROOT_LABEL = "protocol-stack:v4:state-root"
ECONOMY_TREE_PREFIX = "protocol-stack:v4:economy"

STATE_ROOT_SCHEMA_VERSION = 4

TRANSFER = 1
PURCHASE_SEAT = 2
ACTIVATE_SEAT = 3
MINT_NODE = 4
MINT_REFERRAL = 5
DIRECT_ISSUE = 6
MINT_NODE_VERIFIED = 7
SET_MINT_BIOMETRIC = 8
ADD_MANAGER = 9
HUB_REGISTER = 10
HUB_ADD_ADDRESS = 11
HUB_REMOVE_ADDRESS = 12

TRANSACTION_KINDS: dict[int, str] = {
    TRANSFER: "native_transfer",
    PURCHASE_SEAT: "purchase_seat",
    ACTIVATE_SEAT: "activate_seat",
    MINT_NODE: "mint_node",
    MINT_REFERRAL: "mint_referral",
    DIRECT_ISSUE: "direct_issue",
    MINT_NODE_VERIFIED: "mint_node_verified",
    SET_MINT_BIOMETRIC: "set_mint_biometric",
    ADD_MANAGER: "add_manager",
    HUB_REGISTER: "hub_register",
    HUB_ADD_ADDRESS: "hub_add_address",
    HUB_REMOVE_ADDRESS: "hub_remove_address",
}

# Every kind is fixed-length. Two pairs share a length — kinds 3 and 7 both name
# a seat and carry one signature, kinds 11 and 12 both name an account and carry
# one — which is the case version two anticipated when it required a decoder to
# dispatch on the kind byte rather than on the length.
BODY_BYTES: dict[int, int] = {
    TRANSFER: 40,
    PURCHASE_SEAT: 133,
    ACTIVATE_SEAT: 68,
    MINT_NODE: 4,
    MINT_REFERRAL: 0,
    DIRECT_ISSUE: 105,
    MINT_NODE_VERIFIED: 68,
    SET_MINT_BIOMETRIC: 69,
    ADD_MANAGER: 100,
    HUB_REGISTER: 128,
    HUB_ADD_ADDRESS: 96,
    HUB_REMOVE_ADDRESS: 96,
}

# The HUB signature family. Seven of the eight verify against a person's own
# recorded public key; only the registration verifies against the
# genesis-configured ecosystem verifier key, which is the one judgement no chain
# can make.
HUB_SIGNATURE_BYTES = 64
REGISTRATION_LABEL = "protocol-stack:v4:hub-registration"
ADDRESS_ADD_LABEL = "protocol-stack:v4:hub-address-add"
ADDRESS_REMOVE_LABEL = "protocol-stack:v4:hub-address-remove"
PURCHASE_LABEL = "protocol-stack:v4:seat-purchase"
ACTIVATION_LABEL = "protocol-stack:v4:seat-activation"
MINT_LABEL = "protocol-stack:v4:seat-mint"
MINT_BIOMETRIC_DISABLE_LABEL = "protocol-stack:v4:mint-biometric-disable"
MANAGER_LABEL = "protocol-stack:v4:seat-manager"

HUB_MESSAGE_LABELS: tuple[str, ...] = (
    REGISTRATION_LABEL,
    ADDRESS_ADD_LABEL,
    ADDRESS_REMOVE_LABEL,
    PURCHASE_LABEL,
    ACTIVATION_LABEL,
    MINT_LABEL,
    MINT_BIOMETRIC_DISABLE_LABEL,
    MANAGER_LABEL,
)
# The only message the ecosystem verifier signs.
VERIFIER_SIGNED_LABELS: tuple[str, ...] = (REGISTRATION_LABEL,)

HUB_GATED_KINDS = frozenset(
    {
        PURCHASE_SEAT,
        ACTIVATE_SEAT,
        MINT_NODE_VERIFIED,
        ADD_MANAGER,
        HUB_REGISTER,
        HUB_ADD_ADDRESS,
        HUB_REMOVE_ADDRESS,
    }
)
# Kinds whose sender is unconstrained because the signature is the authority:
# exactly the transactions a person must be able to make holding none of their
# own addresses.
ANY_SENDER_KINDS = frozenset({ADD_MANAGER, HUB_ADD_ADDRESS, HUB_REMOVE_ADDRESS})

DIRECT_ISSUE_CHANNELS: tuple[int, ...] = (5, 6, 8, 9)

ADMISSION_CODES: dict[int, str] = {
    1: "MALFORMED_TRANSACTION",
    2: "WRONG_CHAIN",
    3: "INVALID_SIGNATURE",
}

# One flat space, extending version three's contiguously. Codes 0 through 23
# keep their exact version-three meanings and 0 through 8 their version-one
# meanings.
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

INHERITED_RESULT_CODES: tuple[int, ...] = tuple(range(0, 9))
VERSION_THREE_RESULT_CODES: tuple[int, ...] = tuple(range(0, 24))
ADDED_RESULT_CODES: tuple[int, ...] = tuple(range(24, 26))

CODE_NUMBER: dict[str, int] = {name: number for number, name in RESULT_CODES.items()}

# The economy model is unchanged between transition versions two, three, and
# four, so its total three-way disposition is unchanged with it.
CARRIED_MODEL_CODES: dict[str, str] = {
    "OK": "SUCCESS",
    "CYCLE_RANGE": "CYCLE_RANGE",
    "INVALID_REFERRER": "INVALID_REFERRER",
    "REPLAY": "REPLAY",
    "SEAT_NOT_ACTIVATED": "SEAT_NOT_ACTIVATED",
    "INVALID_CHANNEL": "INVALID_CHANNEL",
    "ZERO_AMOUNT": "ZERO_AMOUNT",
    "MISSING_RESEARCH_INPUT": "MISSING_RESEARCH_INPUT",
    "INVALID_RESEARCH_INPUT": "INVALID_RESEARCH_INPUT",
    "NOT_ELIGIBLE": "NOT_ELIGIBLE",
    "CHANNEL_CAP": "CHANNEL_CAP",
}

GUARD_MODEL_CODES: tuple[str, ...] = ("ARITHMETIC_OVERFLOW", "INVARIANT")

UNREPRESENTABLE_MODEL_CODES: dict[str, str] = {
    "MISSING_UPTIME_RECORD": "no transaction supplies a record; the chain writes it",
    "INVALID_UPTIME_RECORD": "no transaction supplies a record; the chain writes it",
    "INCONSISTENT_UPTIME_RECORD": "one assignment per cycle, by construction",
    "SEAT_NOT_IN_SCOPE": "the in-scope set is derived, not supplied",
    "INCOMPLETE_UPTIME_RECORD": "the in-scope set is derived, not supplied",
    "WINDOW_BEFORE_ISSUANCE": "no transaction names a window",
    "WINDOW_AFTER_ISSUANCE": "no transaction names a window",
    "WINDOW_NOT_FOR_CYCLE": "no transaction names a window",
    "HEIGHT_RANGE": "the activation height is the executing block height",
    "HEIGHT_NOT_MONOTONIC": "block heights increase by construction",
    "PERMISSION_NOT_FOUND": "a mint takes everything, so there is no per-cycle key",
}

SEAT_ENTRY = 1
CHANNEL_ENTRY = 2
CYCLE_ASSIGNMENT_ENTRY = 3
REFERRAL_BALANCE_ENTRY = 4
DIRECT_DECISION_ENTRY = 5
TYPED_CUSTODY_ENTRY = 6
CARRY_ENTRY = 7
VERIFIER_KEY_ENTRY = 8
SEAT_MANAGER_ENTRY = 9
HUB_IDENTITY_ENTRY = 10
HUB_ADDRESS_ENTRY = 11
UNREFERRED_POOL_ENTRY = 12

ENTRY_KINDS: dict[int, str] = {
    SEAT_ENTRY: "seat",
    CHANNEL_ENTRY: "channel",
    CYCLE_ASSIGNMENT_ENTRY: "cycle_assignment",
    REFERRAL_BALANCE_ENTRY: "referral_balance",
    DIRECT_DECISION_ENTRY: "direct_decision",
    TYPED_CUSTODY_ENTRY: "typed_custody",
    CARRY_ENTRY: "carry",
    VERIFIER_KEY_ENTRY: "verifier_key",
    SEAT_MANAGER_ENTRY: "seat_manager",
    HUB_IDENTITY_ENTRY: "hub_identity",
    HUB_ADDRESS_ENTRY: "hub_address",
    UNREFERRED_POOL_ENTRY: "unreferred_pool",
}

ENTRY_KEY_BYTES: dict[int, int] = {
    SEAT_ENTRY: 5,
    CHANNEL_ENTRY: 2,
    CYCLE_ASSIGNMENT_ENTRY: 9,
    REFERRAL_BALANCE_ENTRY: 33,
    DIRECT_DECISION_ENTRY: 33,
    TYPED_CUSTODY_ENTRY: 34,
    CARRY_ENTRY: 2,
    VERIFIER_KEY_ENTRY: 1,
    SEAT_MANAGER_ENTRY: 37,
    HUB_IDENTITY_ENTRY: 33,
    HUB_ADDRESS_ENTRY: 33,
    UNREFERRED_POOL_ENTRY: 1,
}

ENTRY_VALUE_BYTES: dict[int, int | None] = {
    SEAT_ENTRY: 119,
    CHANNEL_ENTRY: 16,
    CYCLE_ASSIGNMENT_ENTRY: None,
    REFERRAL_BALANCE_ENTRY: 24,
    DIRECT_DECISION_ENTRY: 0,
    TYPED_CUSTODY_ENTRY: 8,
    CARRY_ENTRY: 8,
    VERIFIER_KEY_ENTRY: 32,
    SEAT_MANAGER_ENTRY: 0,
    HUB_IDENTITY_ENTRY: 48,
    HUB_ADDRESS_ENTRY: 32,
    UNREFERRED_POOL_ENTRY: 16,
}

CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES = 24

VENTURE_ESCROW_BENEFICIARY = 1
COMMUNITY_GRANTS_BENEFICIARY = 2
DEVELOPER_INCENTIVES_BENEFICIARY = 3
SYSTEM_CREATOR_BENEFICIARY = 4
DIRECT_BENEFICIARY = 5

BENEFICIARY_KINDS: dict[int, str] = {
    VENTURE_ESCROW_BENEFICIARY: "venture_escrow",
    COMMUNITY_GRANTS_BENEFICIARY: "community_grants_escrow",
    DEVELOPER_INCENTIVES_BENEFICIARY: "developer_incentives_escrow",
    SYSTEM_CREATOR_BENEFICIARY: "system_creator_company",
    DIRECT_BENEFICIARY: "direct_beneficiary",
}
SINGLETON_BENEFICIARY_KINDS: tuple[int, ...] = (1, 2, 3, 4)
SINGLETON_BENEFICIARY_ID = bytes(32)

GENESIS_PREFIX_BYTES = 110
ACCOUNT_ENTRY_BYTES = 48
MAX_GENESIS_ACCOUNTS = (MAX_OBJECT_BYTES - GENESIS_PREFIX_BYTES) // ACCOUNT_ENTRY_BYTES

BASE_PERMISSION_LEGS: tuple[tuple[int, int], ...] = (
    (0, 34_200_000_000),
    (1, 17_100_000_000),
    (2, 3_420_000_000),
    (3, 1_710_000_000),
    (4, 1_000_000_000),
)
LEG_BENEFICIARY_KIND: dict[int, int | None] = {
    0: None,
    1: VENTURE_ESCROW_BENEFICIARY,
    2: COMMUNITY_GRANTS_BENEFICIARY,
    3: DEVELOPER_INCENTIVES_BENEFICIARY,
    4: SYSTEM_CREATOR_BENEFICIARY,
}
BASE_PERMISSION_TOTAL = sum(amount for _, amount in BASE_PERMISSION_LEGS)
FOUNDER_OPERATOR_CHANNEL = 0
REFERRAL_CHANNEL = 7
REFERRAL_LEG_ATOMIC = 3_420_000_000

# Confirmed unchanged by the owner on 2026-08-14: a seat is full when thirty
# days have passed since it last collected.
MINT_ACCUMULATION_CAP = 30
ASSIGNMENT_LAG_WINDOWS = 2

# Resource limits rather than statements about participants. Both make a
# per-entity storage bound a constant, which requirement 12 asks for.
MAX_SEAT_MANAGERS = 16
MAX_IDENTITY_ADDRESSES = 16
