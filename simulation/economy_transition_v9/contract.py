"""Fixed constants, tables, and code spaces of `economy-transition-v9`.

Version nine is version eight with a clock and a monthly settlement. Six things
move — the block header gains a field, genesis gains a field, the state key space
gains four entry kinds and widens one value, the transaction kind space gains
one, the state root commits to the timestamp, and four labels are re-versioned —
and everything else carries over and is imported.

**The result code space does not move**, which is worth stating as a table
rather than as an absence: kind 22 reuses kind 4's ladder exactly, so every
refusal it can produce already has a number and the space stays at forty-five.

**The carried set is a declaration rather than two hundred copied lines.**
`CARRIED_FROM_V8` names every constant this version takes unchanged,
`REVISED_IN_V9` names the ones whose value moves, `ADDED_IN_V9` names the ones
that are new, and `REPLACED_DECLARATIONS` names version eight's own provenance
sets, which every version replaces with its own.
`tests/simulation/economy_transition_v9_carryover_test.py` requires them to
partition version eight's public surface exactly, so a constant that moved
without a vector reaching it fails a test rather than surviving as a copy nobody
compared.

**The calendar figures are bound rather than restated.** Every timestamp
constant below is imported from `simulation.calendar`, which is the accepted
`calendar-v1` model, for the reason that specification gives about a tolerance
being a consensus parameter: a second copy is a second opinion, and two machines
holding different tolerances is a fork.
"""

from __future__ import annotations

from simulation.calendar import contract as calendar
from simulation.economy_transition_v6 import block as _v1_block
from simulation.economy_transition_v8 import contract as v8

# --- what version nine takes unchanged --------------------------------------

CARRIED_FROM_V8: tuple[str, ...] = (
    "ABSENT_MODEL_CODES",
    "ACCOUNT_ENTRY_BYTES",
    "ACCOUNT_LABEL",
    "ACTIVATE_SEAT",
    "ACTIVATION_LABEL",
    "ADDED_FEE_EXEMPT_KIND",
    "ADDED_IN_V8_RESULT_CODES",
    "ADDED_RESULT_CODES",
    "ADMISSION_CODES",
    "ANSWER_BYTES",
    "ASSIGNMENT_LAG_WINDOWS",
    "BASE_PERMISSION_LEGS",
    "BASE_PERMISSION_TOTAL",
    "BENEFICIARY_KINDS",
    "CARRIED_MODEL_CODES",
    "CHALLENGEABLE_HEIGHTS_PER_SLOT",
    "CHALLENGE_LABEL",
    "CHALLENGE_PERIOD_BLOCKS",
    "CHALLENGE_RESPONSE",
    "CHANNEL_ENTRY",
    "CODE_NUMBER",
    "CONFIRMABLE_MINTS",
    "CYCLE_ASSIGNMENT_ENTRY",
    "CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES",
    "CYCLE_BLOCKS",
    "DEFAULT_EXEMPT_SLOT_MASK",
    "DEFAULT_MIN_AMOUNT_ATOMIC",
    "DEFAULT_REQUIRES_CONFIRMATION",
    "DIRECT_DECISION_ENTRY",
    "DIRECT_ISSUE",
    "DIRECT_ISSUE_CHANNELS",
    "DISPUTE_AUTHORITY_KEY_BYTES",
    "DISPUTE_CAP_SLOTS_PER_SEAT",
    "DISPUTE_LABEL",
    "ENVELOPE_SCHEMA_VERSION",
    "ESCROW_CREATE",
    "ESCROW_DELETE",
    "ESCROW_ENTRY",
    "ESCROW_LABEL",
    "FILE_DISPUTE",
    "FOUNDER_OPERATOR_CHANNEL",
    "FOUNDER_SEAT_CAPACITY",
    "GENESIS_MAGIC",
    "GUARD_MODEL_CODES",
    "HEADER_BYTES",
    "HUB_IDENTITY_ENTRY",
    "HUB_MESSAGE_LABELS",
    "HUB_REGISTER",
    "HUB_SIGNATURE_BYTES",
    "INHERITED_RESULT_CODES",
    "ISSUANCE_CYCLES_PER_SEAT",
    "LEG_BENEFICIARY_KIND",
    "MANIFEST_DIGEST_HEX",
    "MAX_EXEMPT_SLOT_MASK",
    "MAX_OBJECT_BYTES",
    "MAX_SEATS_PER_IDENTITY",
    "MAX_SEAT_ID",
    "MAX_SIGNERS_PER_ESCROW",
    "MAX_SLOT_INDEX",
    "MAX_U64",
    "MINT_ACCUMULATION_CAP",
    "MINT_CONFIRM_LABEL",
    "MINT_NODE",
    "MINT_REFERRAL",
    "MINT_VERIFIED_USER",
    "OPEN_CHALLENGE_ENTRY",
    "POSTURE_RELAX_LABEL",
    "PURCHASE_LABEL",
    "PURCHASE_SEAT",
    "RECEIPT_MAGIC",
    "RECOVERY_POOL_ENTRY",
    "RECOVERY_POOL_LEGS",
    "REFERRAL_BALANCE_ENTRY",
    "REFERRAL_CHANNEL",
    "REFERRAL_LEG_ATOMIC",
    "REGISTRATION_LABEL",
    "RESPONSE_DEADLINE_BLOCKS",
    "RESULT_CODES",
    "RETAINED_WINDOWS",
    "RETIRED_ENTRY_KINDS",
    "RETIRED_KINDS",
    "SCHEME_IDENTITY",
    "SCHEME_SIGNER",
    "SEAT_ENTRY",
    "SEAT_WINDOW_ENTRY",
    "SET_SECURITY_POSTURE",
    "SIGNATURE_BYTES",
    "SIGNATURE_SCHEMES",
    "SIGNER_ADD",
    "SIGNER_ENTRY",
    "SIGNER_REVOKE",
    "SIGN_LABEL",
    "SINGLETON_BENEFICIARY_ID",
    "SINGLETON_BENEFICIARY_KINDS",
    "SLOTS_PER_WINDOW",
    "SLOT_BLOCKS",
    "SLOT_SECONDS",
    "SUPERSEDED_MANIFEST_DIGEST_HEX",
    "TRAILER_BYTES",
    "TRANSACTION_MAGIC",
    "TRANSFER",
    "TRANSFER_CONFIRM_LABEL",
    "TRANSFER_VERIFIED",
    "TX_ID_LABEL",
    "TYPED_CUSTODY_ENTRY",
    "UNREACHABLE_RESULT_CODES",
    "UNREFERRED_POOL_ENTRY",
    "UNREPRESENTABLE_MODEL_CODES",
    "UPTIME_LABELS",
    "VERIFIED_USER_CHANNEL",
    "VERIFIED_USER_CHANNEL_CAP",
    "VERIFIED_USER_COUNTER_ENTRY",
    "VERIFIED_USER_CYCLES",
    "VERIFIED_USER_DAILY_ATOMIC",
    "VERIFIED_USER_ENTRY",
    "VERIFIED_USER_POPULATION",
    "VERIFIER_KEY_ENTRY",
    "VERIFIER_SIGNED_LABELS",
    "VERSION_FOUR_RESULT_CODES",
)

for _name in CARRIED_FROM_V8:
    globals()[_name] = getattr(v8, _name)
del _name

# --- version eight's own provenance sets, replaced rather than carried -------

REPLACED_DECLARATIONS: tuple[str, ...] = (
    "ADDED_IN_V8",
    "CARRIED_FROM_V7",
    "DECLARATIONS",
    "REPLACED_DECLARATIONS",
    "REVISED_IN_V8",
)

# --- what version nine changes ----------------------------------------------

REVISED_IN_V9: tuple[str, ...] = (
    "BODY_BYTES",
    "CHAIN_ID_LABEL",
    "ECONOMY_TREE_PREFIX",
    "ENTRY_KEY_BYTES",
    "ENTRY_KINDS",
    "ENTRY_VALUE_BYTES",
    "GENESIS_PREFIX_BYTES",
    "GENESIS_SCHEMA_VERSION",
    "KIND_SCHEME",
    "MAX_GENESIS_ACCOUNTS",
    "RECEIPT_VERSION",
    "STATE_ROOT_LABEL",
    "STATE_ROOT_SCHEMA_VERSION",
    "TRANSACTION_KINDS",
)

CHAIN_ID_LABEL = "protocol-stack:v9:chain-id"
STATE_ROOT_LABEL = "protocol-stack:v9:state-root"
ECONOMY_TREE_PREFIX = "protocol-stack:v9:economy"

STATE_ROOT_SCHEMA_VERSION = 9
GENESIS_SCHEMA_VERSION = 9
RECEIPT_VERSION = 9

ADDED_IN_V9: tuple[str, ...] = (
    "ADDED_IN_V9_ENTRY_KINDS",
    "BLOCK_HEADER_BYTES",
    "BLOCK_HEADER_SCHEMA_VERSION",
    "BLOCK_ID_LABEL",
    "GENESIS_ECONOMY_ENTRY_COUNT",
    "GENESIS_TIMESTAMP_BYTES",
    "LIVE_WINDOW_MONTHS",
    "MAX_MONTH_INDEX",
    "MAX_TIMESTAMP_MILLIS",
    "MILLIS_PER_DAY",
    "MIN_TIMESTAMP_MILLIS",
    "MINT_POOL",
    "MONTHLY_CLAIM_ENTRY",
    "MONTHLY_FIGURE_ENTRY",
    "SETTLEMENT_CURSOR_ENTRY",
    "TIMESTAMP_BYTES",
    "TIMESTAMP_CONDITIONS",
    "TIMESTAMP_TOLERANCE_MILLIS",
    "WINDOW_MONTH_ENTRY",
)

DECLARATIONS: tuple[str, ...] = (
    "ADDED_IN_V9",
    "CARRIED_FROM_V8",
    "DECLARATIONS",
    "REPLACED_DECLARATIONS",
    "REVISED_IN_V9",
)

# --- the clock, bound from the accepted calendar model ----------------------

MILLIS_PER_DAY = calendar.MILLIS_PER_DAY
MIN_TIMESTAMP_MILLIS = calendar.MIN_TIMESTAMP_MILLIS
MAX_TIMESTAMP_MILLIS = calendar.MAX_TIMESTAMP_MILLIS
MAX_MONTH_INDEX = calendar.MAX_MONTH_INDEX
TIMESTAMP_TOLERANCE_MILLIS = calendar.TIMESTAMP_TOLERANCE_MILLIS

TIMESTAMP_BYTES = 8
GENESIS_TIMESTAMP_BYTES = 8

# `calendar-v1`'s ordered rejection conditions, in the order a machine applies
# them. The first three are deterministic and are re-applied on every replay;
# the last two are the two sides of C5 and are applied once, at admission.
TIMESTAMP_CONDITIONS: tuple[str, ...] = (
    "HEIGHT_NOT_NEXT",
    "TIMESTAMP_RANGE",
    "TIMESTAMP_NOT_MONOTONIC",
    "TIMESTAMP_AHEAD_OF_TOLERANCE",
    "TIMESTAMP_BEHIND_TOLERANCE",
)

# None of the five is a transaction result. They are block-level conditions and
# belong to the application contract's status space, which is why they are named
# here as strings rather than added to `RESULT_CODES`.

# --- the block header -------------------------------------------------------

# Version one's 146-octet header with `timestamp:u64` inserted after the height,
# which moves every later offset. Appending would have preserved them, and that
# is a hazard rather than a benefit: a loose decoder would read a version-nine
# header as a version-one header with eight trailing octets and agree with
# itself about every field.
BLOCK_HEADER_BYTES = _v1_block.BLOCK_HEADER_BYTES + TIMESTAMP_BYTES
BLOCK_HEADER_SCHEMA_VERSION = 9
BLOCK_ID_LABEL = "protocol-stack:v9:block-id"

# --- the one new transaction kind -------------------------------------------

MINT_POOL = 22

TRANSACTION_KINDS: dict[int, str] = dict(v8.TRANSACTION_KINDS) | {
    MINT_POOL: "mint_monthly_pool",
}

# `seat_id:u32 || destination_escrow_id:32 || hub_signature:64`, which is kind
# 4's body exactly. The shape is the point: a mint of a seat's award is
# authorized the way a mint of a seat's permissions is.
BODY_BYTES: dict[int, int] = dict(v8.BODY_BYTES) | {
    MINT_POOL: 4 + 32 + v8.HUB_SIGNATURE_BYTES,
}

KIND_SCHEME: dict[int, int] = dict(v8.KIND_SCHEME) | {MINT_POOL: v8.SCHEME_SIGNER}

# Kind 22 is confirmable and issuing, on kind 4's own terms. Both sets are
# rebuilt rather than mutated, because version eight's are frozensets it exports
# and a version that edited one in place would change its predecessor's table.
CONFIRMABLE_MINTS = frozenset(v8.CONFIRMABLE_MINTS | {MINT_POOL})
ISSUING_KINDS = frozenset(v8.ISSUING_KINDS | {MINT_POOL})

# --- the four new state entries ---------------------------------------------

WINDOW_MONTH_ENTRY = 20
MONTHLY_FIGURE_ENTRY = 21
MONTHLY_CLAIM_ENTRY = 22
SETTLEMENT_CURSOR_ENTRY = 23

ADDED_IN_V9_ENTRY_KINDS: dict[int, str] = {
    WINDOW_MONTH_ENTRY: "window_month",
    MONTHLY_FIGURE_ENTRY: "monthly_uptime_figure",
    MONTHLY_CLAIM_ENTRY: "monthly_pool_claim",
    SETTLEMENT_CURSOR_ENTRY: "settlement_cursor",
}

ENTRY_KINDS: dict[int, str] = dict(v8.ENTRY_KINDS) | ADDED_IN_V9_ENTRY_KINDS

ENTRY_KEY_BYTES: dict[int, int] = dict(v8.ENTRY_KEY_BYTES) | {
    WINDOW_MONTH_ENTRY: 1 + 8,
    MONTHLY_FIGURE_ENTRY: 1 + 4 + 4,
    MONTHLY_CLAIM_ENTRY: 1 + 4,
    SETTLEMENT_CURSOR_ENTRY: 1,
}

# Kind 12's value widens from sixteen octets to twenty-four: `payable` is
# inserted between `accrued` and `minted` rather than appended, so a
# version-eight decoder pointed at a version-nine value produces an obvious
# mismatch rather than a plausible pair of numbers.
ENTRY_VALUE_BYTES: dict[int, int | None] = dict(v8.ENTRY_VALUE_BYTES) | {
    v8.UNREFERRED_POOL_ENTRY: 24,
    WINDOW_MONTH_ENTRY: 4,
    MONTHLY_FIGURE_ENTRY: 8,
    MONTHLY_CLAIM_ENTRY: 16,
    SETTLEMENT_CURSOR_ENTRY: 4,
}

# The open window's month and its predecessor's. `unreferred-pool-payout-v1`
# sized this at three — the open window and the two inside the assignment lag —
# and version nine deletes the oldest of the three in the same prologue that
# assigns it, so the encoded count is two. The smaller figure is the real one
# and the vectors measure it rather than asserting it.
LIVE_WINDOW_MONTHS = 2

# --- genesis ----------------------------------------------------------------

# One `u64` after the network identifier. `account_count` stays last because the
# account entries follow it.
GENESIS_PREFIX_BYTES = v8.GENESIS_PREFIX_BYTES + GENESIS_TIMESTAMP_BYTES
MAX_GENESIS_ACCOUNTS = (
    v8.MAX_OBJECT_BYTES - GENESIS_PREFIX_BYTES
) // v8.ACCOUNT_ENTRY_BYTES

# Version eight's fourteen, plus the settlement cursor and window zero's month.
GENESIS_ECONOMY_ENTRY_COUNT = 16
