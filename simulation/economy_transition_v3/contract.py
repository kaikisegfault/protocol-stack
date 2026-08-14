"""Fixed constants, tables, and code spaces of `economy-transition-v3`.

Every founder-directed figure here is read from an accepted contract rather than
restated. The channel identifiers are the accepted manifest's array indexes, the
seat capacity and issuance-cycle count come from the manifest layer, and the
window grid comes from the cycle-boundary contract, so one founder-directed
value keeps one home.

Version three differs from version two in four places the founder directed on
2026-08-14 and in two consequences of the first of them. What carries over
unchanged — the 80-byte header, the 16-byte trailer, kind 1's body, the two
version-one signing labels, the admission codes, and result codes 0 through 20 —
is repeated here rather than imported from the version-two package, because
version two is accepted evidence that must stay readable on its own and a
shared table would make one contract's constants depend on the other's file.
The one thing that is imported is the RFC 9162 tree, which is an accepted
construction rather than a version-two decision.
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

# The accepted manifest digest, bound into version-three genesis so that a chain
# whose channel table differs is a different chain rather than the same chain
# with a different table.
MANIFEST_DIGEST_HEX = manifest.MANIFEST_DIGEST

# The envelope. These three widths are the whole compatibility argument and are
# version two's unchanged: the header is the accepted version-one transfer's
# first 80 bytes and the trailer its last 16.
HEADER_BYTES = 80
TRAILER_BYTES = 16
SIGNATURE_BYTES = 64

TRANSACTION_MAGIC = b"PSTX"
RECEIPT_MAGIC = b"PSRC"
GENESIS_MAGIC = b"PSGN"

ENVELOPE_SCHEMA_VERSION = 1
RECEIPT_VERSION = 3
GENESIS_SCHEMA_VERSION = 3
SIGNATURE_SCHEME = 1

# Version-one labels, deliberately not re-versioned: the kind byte and the chain
# ID are both inside every signature preimage, and a new label would destroy the
# kind-1 byte identity for separation the preimage already carries.
SIGN_LABEL = "protocol-stack:v1:tx-sign"
TX_ID_LABEL = "protocol-stack:v1:tx-id"

CHAIN_ID_LABEL = "protocol-stack:v3:chain-id"
STATE_ROOT_LABEL = "protocol-stack:v3:state-root"
ECONOMY_TREE_PREFIX = "protocol-stack:v3:economy"

STATE_ROOT_SCHEMA_VERSION = 3

TRANSFER = 1
PURCHASE_SEAT = 2
ACTIVATE_SEAT = 3
MINT_NODE = 4
MINT_REFERRAL = 5
DIRECT_ISSUE = 6
MINT_NODE_VERIFIED = 7
SET_MINT_BIOMETRIC = 8
ADD_MANAGER = 9
HUB_VERIFY = 10

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
    HUB_VERIFY: "hub_verify",
}

# Every kind is fixed-length. Kinds 3 and 7 share a body length, which is the
# case version two anticipated when it required a decoder to dispatch on the
# kind byte rather than on the length: both name a seat and carry exactly one
# verifier signature, so their bodies coincide and their meanings do not.
BODY_BYTES: dict[int, int] = {
    TRANSFER: 40,
    PURCHASE_SEAT: 165,
    ACTIVATE_SEAT: 68,
    MINT_NODE: 4,
    MINT_REFERRAL: 0,
    DIRECT_ISSUE: 105,
    MINT_NODE_VERIFIED: 68,
    SET_MINT_BIOMETRIC: 69,
    ADD_MANAGER: 100,
    HUB_VERIFY: 96,
}

# The biometric verification signatures the ecosystem verifier produces off
# chain. Version two's family gated entry alone; version three adds a protected
# mint, the removal of that protection, a manager addition, and HUB
# verification. The labels are re-versioned because no accepted byte string
# depends on them, unlike the two transaction labels above.
BIOMETRIC_SIGNATURE_BYTES = 64
ENROLLMENT_LABEL = "protocol-stack:v3:seat-enrollment"
ACTIVATION_LABEL = "protocol-stack:v3:seat-activation"
MINT_LABEL = "protocol-stack:v3:seat-mint"
MINT_BIOMETRIC_DISABLE_LABEL = "protocol-stack:v3:mint-biometric-disable"
MANAGER_LABEL = "protocol-stack:v3:seat-manager"
HUB_LABEL = "protocol-stack:v3:hub-verification"

VERIFIER_MESSAGE_LABELS: tuple[str, ...] = (
    ENROLLMENT_LABEL,
    ACTIVATION_LABEL,
    MINT_LABEL,
    MINT_BIOMETRIC_DISABLE_LABEL,
    MANAGER_LABEL,
    HUB_LABEL,
)

BIOMETRIC_GATED_KINDS = frozenset(
    {PURCHASE_SEAT, ACTIVATE_SEAT, MINT_NODE_VERIFIED, ADD_MANAGER, HUB_VERIFY}
)

# The direct-mint channels kind 6 may name, as accepted manifest array indexes.
# `founder_referral` at index 7 is excluded: it is consumed exactly by the daily
# referral assignment and kind 5.
DIRECT_ISSUE_CHANNELS: tuple[int, ...] = (5, 6, 8, 9)

ADMISSION_CODES: dict[int, str] = {
    1: "MALFORMED_TRANSACTION",
    2: "WRONG_CHAIN",
    3: "INVALID_SIGNATURE",
}

# One flat space, extending version two's contiguously. Codes 0 through 8 are
# version one's and 0 through 20 are version two's, each with its exact meaning:
# a version-three chain is a different chain, so nothing forces the continuity,
# and it is kept because a code that names the same condition should not have to
# be relearned.
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

INHERITED_RESULT_CODES: tuple[int, ...] = tuple(range(0, 9))
VERSION_TWO_RESULT_CODES: tuple[int, ...] = tuple(range(0, 21))
ADDED_RESULT_CODES: tuple[int, ...] = tuple(range(21, 24))

CODE_NUMBER: dict[str, int] = {name: number for number, name in RESULT_CODES.items()}

# The total disposition of `founder-economy-simulator-v3`'s twenty-four model
# codes. The model is unchanged between transition versions two and three, so
# the partition is unchanged; the vectors still require the three sets to
# partition the model's declared set rather than trusting that.
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

# `ledger-transition-v1` already decides these: a checked-arithmetic violation
# is an internal invariant failure that invalidates the proposed block, not a
# transaction result.
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

# Economy state entry kinds, and the fixed widths their keys and values take.
SEAT_ENTRY = 1
CHANNEL_ENTRY = 2
CYCLE_ASSIGNMENT_ENTRY = 3
REFERRAL_BALANCE_ENTRY = 4
DIRECT_DECISION_ENTRY = 5
TYPED_CUSTODY_ENTRY = 6
CARRY_ENTRY = 7
VERIFIER_KEY_ENTRY = 8
SEAT_MANAGER_ENTRY = 9
HUB_REGISTRATION_ENTRY = 10
UNREFERRED_POOL_ENTRY = 11

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
    HUB_REGISTRATION_ENTRY: "hub_registration",
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
    HUB_REGISTRATION_ENTRY: 33,
    UNREFERRED_POOL_ENTRY: 1,
}

# The cycle assignment is the only variable-width value: it carries two bits per
# covered seat ID. Its fixed part is the per-winner share, the reallocated,
# winner, and in-scope counts, and the number of bits each bitmap covers. The
# bitmap lengths are derived from that count rather than prefixed, because a
# length beside a count from which it is computable is a second representation
# of one number.
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
    HUB_REGISTRATION_ENTRY: 40,
    UNREFERRED_POOL_ENTRY: 16,
}

CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES = 24

# The typed-custody beneficiary space, fixed here for the first time: version
# two used the byte and never enumerated its values. A Founder Seat and a
# referrer are absent because minted value lands in an ordinary account balance
# under ADR 0033, so only institutional beneficiaries and kind 6's named
# account remain.
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

# Version-three genesis. The field table is version two's with a different
# schema version, so the prefix is still 110 bytes and the object bound still
# admits 21,843 account entries.
GENESIS_PREFIX_BYTES = 110
ACCOUNT_ENTRY_BYTES = 48
MAX_GENESIS_ACCOUNTS = (MAX_OBJECT_BYTES - GENESIS_PREFIX_BYTES) // ACCOUNT_ENTRY_BYTES

# The five Founder Node distribution legs of one base permission, in the
# accepted manifest's channel order, each paired with the typed-custody
# beneficiary it reaches. The Founder operator leg reaches no custody kind: it
# credits the minting manager's own account balance.
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

# ADR 0033 directs a bounded accumulation of unminted permissions and names
# roughly thirty days, delegating the figure. A cycle is a 24-hour-target
# window, so thirty windows is thirty days on the accepted grid.
MINT_ACCUMULATION_CAP = 30

# A resource limit rather than a policy about founders: each addition already
# costs a fee and a fresh biometric approval, so the bound is what makes the
# per-seat state a constant, not what makes abuse expensive.
MAX_SEAT_MANAGERS = 16

# `uptime-measurement-v1` finalises window `w` at the first height of `w + 2`,
# so the assignment for `w` executes there and no earlier.
ASSIGNMENT_LAG_WINDOWS = 2
