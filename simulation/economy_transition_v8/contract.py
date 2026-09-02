"""Fixed constants, tables, and code spaces of `economy-transition-v8`.

Version eight is version seven with an on-chain carrier for
`uptime-measurement-v1`. Five things move — the state key space gains two entry
kinds, the transaction kind space gains two, the result code space gains twelve,
genesis gains a field, and two labels are new — and everything else carries over
and is imported.

**The carried set is a declaration rather than a hundred copied lines.**
`CARRIED_FROM_V7` names every constant this version takes unchanged,
`REVISED_IN_V8` names the ones whose value moves, `ADDED_IN_V8` names the ones
that are new, and `REPLACED_DECLARATIONS` names version seven's own provenance
sets, which every version replaces with its own.
`tests/simulation/economy_transition_v8_carryover_test.py` requires them to
partition version seven's public surface exactly, so a constant that moved
without a vector reaching it fails a test rather than surviving as a copy nobody
compared.

Copying the tables by hand would produce a second implementation of an accepted
contract with nothing keeping the two equal, which is the defect ADR 0026 and
ADR 0029 both exist to avoid.
"""

from __future__ import annotations

from simulation.economy_transition_v7 import contract as v7

# --- what version eight takes unchanged -------------------------------------

CARRIED_FROM_V7: tuple[str, ...] = (
    "ACCOUNT_ENTRY_BYTES",
    "ACCOUNT_LABEL",
    "ACTIVATE_SEAT",
    "ACTIVATION_LABEL",
    "ADDED_RESULT_CODES",
    "ADMISSION_CODES",
    "ASSIGNMENT_LAG_WINDOWS",
    "BASE_PERMISSION_LEGS",
    "BASE_PERMISSION_TOTAL",
    "BENEFICIARY_KINDS",
    "CARRIED_MODEL_CODES",
    "CHANNEL_ENTRY",
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
    "ENVELOPE_SCHEMA_VERSION",
    "ESCROW_CREATE",
    "ESCROW_DELETE",
    "ESCROW_ENTRY",
    "ESCROW_LABEL",
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
    "ISSUING_KINDS",
    "LEG_BENEFICIARY_KIND",
    "MANIFEST_DIGEST_HEX",
    "MAX_EXEMPT_SLOT_MASK",
    "MAX_OBJECT_BYTES",
    "MAX_SEATS_PER_IDENTITY",
    "MAX_SEAT_ID",
    "MAX_SIGNERS_PER_ESCROW",
    "MAX_U64",
    "MINT_ACCUMULATION_CAP",
    "MINT_CONFIRM_LABEL",
    "MINT_NODE",
    "MINT_REFERRAL",
    "MINT_VERIFIED_USER",
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
    "RETIRED_ENTRY_KINDS",
    "RETIRED_KINDS",
    "SCHEME_IDENTITY",
    "SCHEME_SIGNER",
    "SEAT_ENTRY",
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

for _name in CARRIED_FROM_V7:
    globals()[_name] = getattr(v7, _name)
del _name

# --- version seven's own provenance sets, replaced rather than carried -------

# Every version declares what it took from its predecessor. Those declarations
# are about the *previous* pair and mean nothing here, so version eight replaces
# them with its own rather than inheriting a statement about version six.
REPLACED_DECLARATIONS: tuple[str, ...] = (
    "ADDED_IN_V7",
    "CARRIED_FROM_V6",
    "DECLARATIONS",
    "REBOUND",
    "REVISED_IN_V7",
)

# --- what version eight changes ---------------------------------------------

REVISED_IN_V8: tuple[str, ...] = (
    "BODY_BYTES",
    "CHAIN_ID_LABEL",
    "CODE_NUMBER",
    "ECONOMY_TREE_PREFIX",
    "ENTRY_KEY_BYTES",
    "ENTRY_KINDS",
    "ENTRY_VALUE_BYTES",
    "GENESIS_PREFIX_BYTES",
    "GENESIS_SCHEMA_VERSION",
    "KIND_SCHEME",
    "MAX_GENESIS_ACCOUNTS",
    "RECEIPT_VERSION",
    "RESULT_CODES",
    "STATE_ROOT_LABEL",
    "STATE_ROOT_SCHEMA_VERSION",
    "TRANSACTION_KINDS",
)

CHAIN_ID_LABEL = "protocol-stack:v8:chain-id"
STATE_ROOT_LABEL = "protocol-stack:v8:state-root"
ECONOMY_TREE_PREFIX = "protocol-stack:v8:economy"

STATE_ROOT_SCHEMA_VERSION = 8
GENESIS_SCHEMA_VERSION = 8
RECEIPT_VERSION = 8

# --- the two new transaction kinds ------------------------------------------

ADDED_IN_V8: tuple[str, ...] = (
    "ABSENT_MODEL_CODES",
    "ADDED_IN_V8_RESULT_CODES",
    "ANSWER_BYTES",
    "CHALLENGEABLE_HEIGHTS_PER_SLOT",
    "CHALLENGE_LABEL",
    "CHALLENGE_PERIOD_BLOCKS",
    "CHALLENGE_RESPONSE",
    "DISPUTE_AUTHORITY_KEY_BYTES",
    "DISPUTE_CAP_SLOTS_PER_SEAT",
    "DISPUTE_LABEL",
    "FILE_DISPUTE",
    "MAX_SLOT_INDEX",
    "OPEN_CHALLENGE_ENTRY",
    "RESPONSE_DEADLINE_BLOCKS",
    "RETAINED_WINDOWS",
    "SEAT_WINDOW_ENTRY",
    "SLOT_SECONDS",
    "UPTIME_LABELS",
)

# The four declarations are themselves public names, so the carryover test needs
# a name for them to require that everything else is classified.
DECLARATIONS: tuple[str, ...] = (
    "ADDED_IN_V8",
    "CARRIED_FROM_V7",
    "DECLARATIONS",
    "REPLACED_DECLARATIONS",
    "REVISED_IN_V8",
)

CHALLENGE_RESPONSE = 20
FILE_DISPUTE = 21

TRANSACTION_KINDS: dict[int, str] = dict(v7.TRANSACTION_KINDS) | {
    CHALLENGE_RESPONSE: "challenge_response",
    FILE_DISPUTE: "file_dispute",
}

ANSWER_BYTES = 32

# Kind 20 is `seat_id:u32 || challenge_height:u64 || answer:32`. Kind 21 is
# `seat_id:u32 || cycle_window:u64 || slot_index:u8 || reason_code:u8 ||
# authority_signature:64`. Neither width collides with an existing kind, which
# is recorded rather than relied on: a decoder dispatches on the kind byte.
BODY_BYTES: dict[int, int] = dict(v7.BODY_BYTES) | {
    CHALLENGE_RESPONSE: 4 + 8 + ANSWER_BYTES,
    FILE_DISPUTE: 4 + 8 + 1 + 1 + v7.SIGNATURE_BYTES,
}

# Both are scheme 1. A response is authorized by the acting escrow's owning
# identity matching the seat's, and a dispute is *relayed* by any signer while
# the authority signs the body — which is kind 10's pattern and the reason
# neither kind needs a third scheme.
KIND_SCHEME: dict[int, int] = dict(v7.KIND_SCHEME) | {
    CHALLENGE_RESPONSE: v7.SCHEME_SIGNER,
    FILE_DISPUTE: v7.SCHEME_SIGNER,
}

# --- the two new state entries ----------------------------------------------

OPEN_CHALLENGE_ENTRY = 18
SEAT_WINDOW_ENTRY = 19

ENTRY_KINDS: dict[int, str] = dict(v7.ENTRY_KINDS) | {
    OPEN_CHALLENGE_ENTRY: "open_challenge",
    SEAT_WINDOW_ENTRY: "seat_window_record",
}

# `u8(kind) || u64 || u32` for both: a height and a seat, or a window and a seat.
ENTRY_KEY_BYTES: dict[int, int] = dict(v7.ENTRY_KEY_BYTES) | {
    OPEN_CHALLENGE_ENTRY: 1 + 8 + 4,
    SEAT_WINDOW_ENTRY: 1 + 8 + 4,
}

# One octet of state for a challenge; two 24-bit bitmaps in the low bits of two
# `u32` fields for a window record.
ENTRY_VALUE_BYTES: dict[int, int | None] = dict(v7.ENTRY_VALUE_BYTES) | {
    OPEN_CHALLENGE_ENTRY: 1,
    SEAT_WINDOW_ENTRY: 8,
}

# --- the measurement figures, read from the accepted contract ----------------

# Every one of these is `uptime-measurement-v1`'s. They are named here because
# an encoding needs them and are not re-derived, for the reason that contract
# gives about three tables holding the same founder-directed constant.
RESPONSE_DEADLINE_BLOCKS = 20
CHALLENGE_PERIOD_BLOCKS = v7.SLOT_BLOCKS
CHALLENGEABLE_HEIGHTS_PER_SLOT = v7.SLOT_BLOCKS - RESPONSE_DEADLINE_BLOCKS
DISPUTE_CAP_SLOTS_PER_SEAT = 6
SLOT_SECONDS = 3_600
MAX_SLOT_INDEX = v7.SLOTS_PER_WINDOW - 1
RETAINED_WINDOWS = 2

CHALLENGE_LABEL = "protocol-stack:v8:challenge"
DISPUTE_LABEL = "protocol-stack:v8:dispute"

UPTIME_LABELS: tuple[str, ...] = (CHALLENGE_LABEL, DISPUTE_LABEL)

DISPUTE_AUTHORITY_KEY_BYTES = 32

# --- genesis ----------------------------------------------------------------

# One 32-octet key after the verifier key. `account_count` stays last because
# the account entries follow it.
GENESIS_PREFIX_BYTES = v7.GENESIS_PREFIX_BYTES + DISPUTE_AUTHORITY_KEY_BYTES
MAX_GENESIS_ACCOUNTS = (
    v7.MAX_OBJECT_BYTES - GENESIS_PREFIX_BYTES
) // v7.ACCOUNT_ENTRY_BYTES

# --- the result code space --------------------------------------------------

ADDED_IN_V8_RESULT_CODES: dict[int, str] = {
    33: "SEAT_NOT_IN_SCOPE",
    34: "CHALLENGE_NOT_ISSUED",
    35: "CHALLENGE_NOT_OPEN",
    36: "RESPONSE_TOO_LATE",
    37: "RESPONSE_REPLAY",
    38: "UNAUTHORIZED_DISPUTE",
    39: "SLOT_RANGE",
    40: "WINDOW_NOT_CLOSED",
    41: "DISPUTE_WINDOW_CLOSED",
    42: "DISPUTE_REPLAY",
    43: "DISPUTE_SLOT_NOT_CREDITED",
    44: "DISPUTE_CAP_EXCEEDED",
}

RESULT_CODES: dict[int, str] = dict(v7.RESULT_CODES) | ADDED_IN_V8_RESULT_CODES

CODE_NUMBER: dict[str, int] = {name: number for number, name in RESULT_CODES.items()}

# The measurement model's codes version eight deliberately does not encode, each
# with the reason. A code no path produces would claim coverage the vectors
# could not show, which is the opposite of what a code space is for.
ABSENT_MODEL_CODES: dict[str, str] = {
    "SCHEDULE_NOT_BOUND": "the chain's schedule is its own seat table",
    "INVALID_BOUND_SCHEDULE": "there is no external table to bind",
    "HEIGHT_RANGE": "a block-level condition; the block is rejected whole",
    "HEIGHT_NOT_MONOTONIC": "a block-level condition; the block is rejected whole",
    "RESPONSE_INVALID": "the answer predicate is the founder-reserved challenge content",
    "INVALID_DUTY_KIND": "version eight encodes no duty report",
    "DUTY_REPLAY": "version eight encodes no duty report",
    "RECORD_NOT_FINAL": "emitting a record is a derivation, not a transaction",
    "WINDOW_HAS_NO_SEATS": "emitting a record is a derivation, not a transaction",
}
