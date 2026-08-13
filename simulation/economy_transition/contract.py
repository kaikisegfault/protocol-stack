"""Fixed constants, tables, and code spaces of `economy-transition-v2`.

Every founder-directed figure here is read from an accepted contract rather than
restated. The channel identifiers are the accepted manifest's array indexes, the
seat capacity and issuance-cycle count come from the manifest layer, and the
window grid comes from the cycle-boundary contract, so one founder-directed
value keeps one home.
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

# The accepted manifest digest, bound into version-two genesis so that a chain
# whose channel table differs is a different chain rather than the same chain
# with a different table.
MANIFEST_DIGEST_HEX = manifest.MANIFEST_DIGEST

# The envelope. These three widths are the whole compatibility argument: the
# header is the accepted version-one transfer's first 80 bytes and the trailer
# its last 16, so kind 1's body is what remains and the version-one transaction
# is the kind-1 instance of this envelope.
HEADER_BYTES = 80
TRAILER_BYTES = 16
SIGNATURE_BYTES = 64

TRANSACTION_MAGIC = b"PSTX"
RECEIPT_MAGIC = b"PSRC"
GENESIS_MAGIC = b"PSGN"

ENVELOPE_SCHEMA_VERSION = 1
RECEIPT_VERSION = 2
GENESIS_SCHEMA_VERSION = 2
SIGNATURE_SCHEME = 1

# Version-one labels, deliberately not re-versioned: the kind byte and the chain
# ID are both inside every signature preimage, so a signature cannot cross a
# kind or a chain, and a new label would destroy the kind-1 byte identity for
# separation the preimage already carries.
SIGN_LABEL = "protocol-stack:v1:tx-sign"
TX_ID_LABEL = "protocol-stack:v1:tx-id"

CHAIN_ID_LABEL = "protocol-stack:v2:chain-id"
STATE_ROOT_LABEL = "protocol-stack:v2:state-root"
ECONOMY_TREE_PREFIX = "protocol-stack:v2:economy"
WINNER_TREE_PREFIX = "protocol-stack:v2:winner"

STATE_ROOT_SCHEMA_VERSION = 2

TRANSFER = 1
ACTIVATE_SEAT = 2
EVALUATE_BASE_PERMISSION = 3
EXERCISE_PERMISSION = 4
ACCRUE_REFERRAL = 5
DIRECT_ISSUE = 6

TRANSACTION_KINDS: dict[int, str] = {
    TRANSFER: "native_transfer",
    ACTIVATE_SEAT: "activate_seat",
    EVALUATE_BASE_PERMISSION: "evaluate_base_permission",
    EXERCISE_PERMISSION: "exercise_permission",
    ACCRUE_REFERRAL: "accrue_referral",
    DIRECT_ISSUE: "direct_issue",
}

# Fixed body widths. Kind 4 is the only variable-length kind: its width is
# FIXED_BODY_BYTES[4] plus four bytes per carried winner.
FIXED_BODY_BYTES: dict[int, int] = {
    TRANSFER: 40,
    ACTIVATE_SEAT: 9,
    EVALUATE_BASE_PERMISSION: 6,
    EXERCISE_PERMISSION: 10,
    ACCRUE_REFERRAL: 6,
    DIRECT_ISSUE: 105,
}

VARIABLE_LENGTH_KINDS = frozenset({EXERCISE_PERMISSION})

# The direct-mint channels kind 6 may name, as accepted manifest array indexes.
# `founder_referral` at index 7 is excluded: it is consumed exactly by kind 5,
# and admitting it here would mint referral units outside the per-seat-cycle
# accounting. Indexes 0 through 4 are base-permission channels.
DIRECT_ISSUE_CHANNELS: tuple[int, ...] = (5, 6, 8, 9)

ADMISSION_CODES: dict[int, str] = {
    1: "MALFORMED_TRANSACTION",
    2: "WRONG_CHAIN",
    3: "INVALID_SIGNATURE",
}

# One flat space so a code means one thing regardless of the kind that produced
# it. Codes 0 through 8 are version one's, frozen with their exact meanings,
# because the conditions they name are properties of the shared header and
# trailer rather than of a transfer.
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

INHERITED_RESULT_CODES: tuple[int, ...] = tuple(range(0, 9))
ADDED_RESULT_CODES: tuple[int, ...] = tuple(range(9, 22))

CODE_NUMBER: dict[str, int] = {name: number for number, name in RESULT_CODES.items()}

# The total disposition of `founder-economy-simulator-v3`'s twenty-four model
# codes. Every code has exactly one entry, and the vectors require the three
# sets to partition the model's declared set, so a later encoding that
# reintroduces a supplied uptime record must move a code out of this table
# rather than quietly widen an input.
CARRIED_MODEL_CODES: dict[str, str] = {
    "OK": "SUCCESS",
    "CYCLE_RANGE": "CYCLE_RANGE",
    "INVALID_REFERRER": "INVALID_REFERRER",
    "REPLAY": "REPLAY",
    "SEAT_NOT_ACTIVATED": "SEAT_NOT_ACTIVATED",
    "PERMISSION_NOT_FOUND": "PERMISSION_NOT_FOUND",
    "INVALID_CHANNEL": "INVALID_CHANNEL",
    "ZERO_AMOUNT": "ZERO_AMOUNT",
    "MISSING_RESEARCH_INPUT": "MISSING_RESEARCH_INPUT",
    "INVALID_RESEARCH_INPUT": "INVALID_RESEARCH_INPUT",
    "NOT_ELIGIBLE": "NOT_ELIGIBLE",
    "CHANNEL_CAP": "CHANNEL_CAP",
}

# `ledger-transition-v1` already decides these: a checked-arithmetic violation
# is an internal invariant failure that invalidates the proposed block, not a
# transaction result. Version two adds nothing and refuses to give a defect a
# receipt.
GUARD_MODEL_CODES: tuple[str, ...] = ("ARITHMETIC_OVERFLOW", "INVARIANT")

# Unreachable because the input does not exist in a transaction. Eight because
# the uptime record and the cycle window are read from state rather than
# supplied, and two because the activation height is the executing block height.
UNREPRESENTABLE_MODEL_CODES: dict[str, str] = {
    "MISSING_UPTIME_RECORD": "the record is state, not an input",
    "INVALID_UPTIME_RECORD": "the record is state, not an input",
    "INCONSISTENT_UPTIME_RECORD": "one finalised record per window, by construction",
    "SEAT_NOT_IN_SCOPE": "the record's seat set is derived, not supplied",
    "INCOMPLETE_UPTIME_RECORD": "the record's seat set is derived, not supplied",
    "WINDOW_BEFORE_ISSUANCE": "the window is derived from the seat's schedule",
    "WINDOW_AFTER_ISSUANCE": "the window is derived from the seat's schedule",
    "WINDOW_NOT_FOR_CYCLE": "the window is derived from the seat's schedule",
    "HEIGHT_RANGE": "the activation height is the executing block height",
    "HEIGHT_NOT_MONOTONIC": "block heights increase by construction",
}

# Economy state entry kinds, and the fixed widths their keys and values take.
SEAT_ENTRY = 1
CHANNEL_ENTRY = 2
PENDING_PERMISSION_ENTRY = 3
REFERRAL_ACCRUAL_ENTRY = 4
DIRECT_DECISION_ENTRY = 5
TYPED_CUSTODY_ENTRY = 6
PERFORMANCE_CARRY_ENTRY = 7
WINDOW_RESULT_ENTRY = 8

ENTRY_KINDS: dict[int, str] = {
    SEAT_ENTRY: "seat",
    CHANNEL_ENTRY: "channel",
    PENDING_PERMISSION_ENTRY: "pending_permission",
    REFERRAL_ACCRUAL_ENTRY: "referral_accrual",
    DIRECT_DECISION_ENTRY: "direct_decision",
    TYPED_CUSTODY_ENTRY: "typed_custody",
    PERFORMANCE_CARRY_ENTRY: "performance_carry",
    WINDOW_RESULT_ENTRY: "window_result",
}

ENTRY_KEY_BYTES: dict[int, int] = {
    SEAT_ENTRY: 5,
    CHANNEL_ENTRY: 2,
    PENDING_PERMISSION_ENTRY: 7,
    REFERRAL_ACCRUAL_ENTRY: 7,
    DIRECT_DECISION_ENTRY: 33,
    TYPED_CUSTODY_ENTRY: 34,
    PERFORMANCE_CARRY_ENTRY: 1,
    WINDOW_RESULT_ENTRY: 9,
}

# The window-result value is the only variable-width value: it carries one bit
# per in-scope seat. The fixed part is the winner root, the winner count, the
# unevaluated count, and the bitmap's own length prefix.
ENTRY_VALUE_BYTES: dict[int, int | None] = {
    SEAT_ENTRY: 13,
    CHANNEL_ENTRY: 16,
    PENDING_PERMISSION_ENTRY: 1,
    REFERRAL_ACCRUAL_ENTRY: 0,
    DIRECT_DECISION_ENTRY: 0,
    TYPED_CUSTODY_ENTRY: 8,
    PERFORMANCE_CARRY_ENTRY: 8,
    WINDOW_RESULT_ENTRY: None,
}

WINDOW_RESULT_FIXED_VALUE_BYTES = 44

# A pending permission's verdict byte, which answers both the verdict question
# and the replay question, so the model's separate evaluated-key set disappears.
VERDICT_FAILED = 0
VERDICT_MET = 1
VERDICT_EXERCISED = 2

VERDICTS: dict[int, str] = {
    VERDICT_FAILED: "failed",
    VERDICT_MET: "met",
    VERDICT_EXERCISED: "exercised",
}

# Version-two genesis. The prefix through `account count` is 78 bytes, which is
# version one's 46 plus the 32-byte manifest digest, so the object bound admits
# one fewer account entry.
GENESIS_PREFIX_BYTES = 78
ACCOUNT_ENTRY_BYTES = 48
MAX_GENESIS_ACCOUNTS = (MAX_OBJECT_BYTES - GENESIS_PREFIX_BYTES) // ACCOUNT_ENTRY_BYTES
