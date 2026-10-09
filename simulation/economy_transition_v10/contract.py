"""Fixed constants, tables, and code spaces of `economy-transition-v10`.

Version ten is version nine with a registry of attested machine keys in place of
the single verifier key, and HUB approvals that can be used once. Five things
move:

- genesis renames `verifier_key` to `launch_key` and gains `build_authority_key`;
- the state gains entry kinds 24, 25, and 26;
- kind 10's body names its attesting seat, and kind 23 is added;
- one approval message replaces five;
- the prologue gains the registry step.

Everything else carries over and is imported.

**The carried set is a declaration rather than a copy.** `CARRIED_FROM_V9` names
every constant this version takes unchanged, `REVISED_IN_V10` the ones whose
value moves, `WITHDRAWN_IN_V10` the five per-action HUB labels version ten no
longer uses, and `REPLACED_DECLARATIONS` version nine's own provenance sets.
`tests/simulation/economy_transition_v10_contract_test.py` requires the four to
partition version nine's public surface exactly. A constant that moved without a
vector reaching it then fails a test, instead of surviving as a copy nobody
compared.

**The founder figures are named once and bound to their ADRs.** ADR 0101 fixes
the cutoff, the meaning of an active machine, and the limit. A second copy
anywhere would be a second opinion, and two machines holding different values
would fork.
"""

from __future__ import annotations

from simulation.cycle_boundary import contract as cycle_boundary
from simulation.economy_transition_v9 import contract as v9

# --- what version ten takes unchanged ---------------------------------------

CARRIED_FROM_V9: tuple[str, ...] = (
    "ABSENT_MODEL_CODES",
    "ACCOUNT_ENTRY_BYTES",
    "ACCOUNT_LABEL",
    "ACTIVATE_SEAT",
    "ADDED_FEE_EXEMPT_KIND",
    "ADDED_IN_V8_RESULT_CODES",
    "ADDED_IN_V9_ENTRY_KINDS",
    "ADDED_RESULT_CODES",
    "ADMISSION_CODES",
    "ANSWER_BYTES",
    "ASSIGNMENT_LAG_WINDOWS",
    "BASE_PERMISSION_LEGS",
    "BASE_PERMISSION_TOTAL",
    "BENEFICIARY_KINDS",
    "BLOCK_HEADER_BYTES",
    "BLOCK_HEADER_SCHEMA_VERSION",
    "BLOCK_ID_LABEL",
    "CARRIED_MODEL_CODES",
    "CHALLENGEABLE_HEIGHTS_PER_SLOT",
    "CHALLENGE_LABEL",
    "CHALLENGE_PERIOD_BLOCKS",
    "CHALLENGE_RESPONSE",
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
    "GENESIS_ECONOMY_ENTRY_COUNT",
    "GENESIS_MAGIC",
    "GENESIS_TIMESTAMP_BYTES",
    "GUARD_MODEL_CODES",
    "HEADER_BYTES",
    "HUB_IDENTITY_ENTRY",
    "HUB_REGISTER",
    "HUB_SIGNATURE_BYTES",
    "INHERITED_RESULT_CODES",
    "ISSUANCE_CYCLES_PER_SEAT",
    "ISSUING_KINDS",
    "LEG_BENEFICIARY_KIND",
    "LIVE_WINDOW_MONTHS",
    "MANIFEST_DIGEST_HEX",
    "MAX_EXEMPT_SLOT_MASK",
    "MAX_MONTH_INDEX",
    "MAX_OBJECT_BYTES",
    "MAX_SEATS_PER_IDENTITY",
    "MAX_SEAT_ID",
    "MAX_SIGNERS_PER_ESCROW",
    "MAX_SLOT_INDEX",
    "MAX_TIMESTAMP_MILLIS",
    "MAX_U64",
    "MILLIS_PER_DAY",
    "MINT_ACCUMULATION_CAP",
    "MINT_NODE",
    "MINT_POOL",
    "MINT_REFERRAL",
    "MINT_VERIFIED_USER",
    "MIN_TIMESTAMP_MILLIS",
    "MONTHLY_CLAIM_ENTRY",
    "MONTHLY_FIGURE_ENTRY",
    "OPEN_CHALLENGE_ENTRY",
    "PURCHASE_SEAT",
    "RECEIPT_MAGIC",
    "RECOVERY_POOL_ENTRY",
    "RECOVERY_POOL_LEGS",
    "REFERRAL_BALANCE_ENTRY",
    "REFERRAL_CHANNEL",
    "REFERRAL_LEG_ATOMIC",
    "RESPONSE_DEADLINE_BLOCKS",
    "RETAINED_WINDOWS",
    "RETIRED_ENTRY_KINDS",
    "RETIRED_KINDS",
    "SCHEME_IDENTITY",
    "SCHEME_SIGNER",
    "SEAT_ENTRY",
    "SEAT_WINDOW_ENTRY",
    "SETTLEMENT_CURSOR_ENTRY",
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
    "TIMESTAMP_BYTES",
    "TIMESTAMP_CONDITIONS",
    "TIMESTAMP_TOLERANCE_MILLIS",
    "TRAILER_BYTES",
    "TRANSACTION_MAGIC",
    "TRANSFER",
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
    "VERSION_FOUR_RESULT_CODES",
    "WINDOW_MONTH_ENTRY",
)

for _name in CARRIED_FROM_V9:
    globals()[_name] = getattr(v9, _name)
del _name

# --- version nine's own provenance sets, replaced rather than carried --------

REPLACED_DECLARATIONS: tuple[str, ...] = (
    "ADDED_IN_V9",
    "CARRIED_FROM_V8",
    "DECLARATIONS",
    "REPLACED_DECLARATIONS",
    "REVISED_IN_V9",
)

# --- what version ten withdraws ---------------------------------------------

# The five per-action HUB labels. Version ten's one approval message signs the
# whole transaction, so none of them derives anything any more. They are named
# here rather than silently dropped, so the partition still accounts for every
# name version nine exported.
WITHDRAWN_IN_V10: tuple[str, ...] = (
    "ACTIVATION_LABEL",
    "MINT_CONFIRM_LABEL",
    "POSTURE_RELAX_LABEL",
    "PURCHASE_LABEL",
    "TRANSFER_CONFIRM_LABEL",
)

# --- what version ten changes ------------------------------------------------

REVISED_IN_V10: tuple[str, ...] = (
    "ACCOUNT_BOUND_UNDER_THE_WIDER_PREFIX",
    "BODY_BYTES",
    "CHAIN_ID_LABEL",
    "CODE_NUMBER",
    "ECONOMY_TREE_PREFIX",
    "ENTRY_KEY_BYTES",
    "ENTRY_KINDS",
    "ENTRY_VALUE_BYTES",
    "GENESIS_PREFIX_BYTES",
    "GENESIS_SCHEMA_VERSION",
    "HUB_MESSAGE_LABELS",
    "KIND_SCHEME",
    "MAX_GENESIS_ACCOUNTS",
    "RECEIPT_VERSION",
    "REGISTRATION_LABEL",
    "RESULT_CODES",
    "STATE_ROOT_LABEL",
    "STATE_ROOT_SCHEMA_VERSION",
    "TRANSACTION_KINDS",
    "VERIFIER_SIGNED_LABELS",
)

CHAIN_ID_LABEL = "protocol-stack:v10:chain-id"
STATE_ROOT_LABEL = "protocol-stack:v10:state-root"
ECONOMY_TREE_PREFIX = "protocol-stack:v10:economy"

STATE_ROOT_SCHEMA_VERSION = 10
GENESIS_SCHEMA_VERSION = 10
RECEIPT_VERSION = 10

ADDED_IN_V10: tuple[str, ...] = (
    "ACTIVITY_THRESHOLD_SECONDS",
    "ADDED_IN_V10_ENTRY_KINDS",
    "ADDED_IN_V10_RESULT_CODES",
    "ALWAYS_PROVEN_KINDS",
    "APPROVAL_KINDS",
    "APPROVAL_LABEL",
    "APPROVAL_LIFETIME_BLOCKS",
    "ATTESTATION_LABEL",
    "BUILD_AUTHORITY_KEY_BYTES",
    "BUILD_DIGEST_BYTES",
    "LAUNCH_ATTESTER",
    "LAUNCH_RETIREMENT_ACTIVE_MACHINES",
    "LAUNCH_RETIREMENT_ENTRY",
    "MACHINE_KEY_ENTRY",
    "MACHINE_KEY_OWNER_ENTRY",
    "MACHINE_REGISTRATIONS_PER_WINDOW",
    "REGISTER_MACHINE_KEY",
)

DECLARATIONS: tuple[str, ...] = (
    "ADDED_IN_V10",
    "CARRIED_FROM_V9",
    "DECLARATIONS",
    "REPLACED_DECLARATIONS",
    "REVISED_IN_V10",
    "WITHDRAWN_IN_V10",
)

# --- the founder answers (ADR 0101) ------------------------------------------

LAUNCH_RETIREMENT_ACTIVE_MACHINES = 100
MACHINE_REGISTRATIONS_PER_WINDOW = 1_000

# "Met" is the uptime test, bound to `cycle-boundary-v1` rather than restated.
ACTIVITY_THRESHOLD_SECONDS = cycle_boundary.ACTIVITY_THRESHOLD_SECONDS

# --- engineering's figures ---------------------------------------------------

# One slot, about an hour at the commit target. Bound to the grid rather than
# written as a number, so a slot that moved would move this with it.
APPROVAL_LIFETIME_BLOCKS = v9.SLOT_BLOCKS

# `u32` maximum, which no seat identifier can take, because the capacity stops
# at 99,999. A registration names it to say the launch key signed.
LAUNCH_ATTESTER = 0xFFFFFFFF

BUILD_AUTHORITY_KEY_BYTES = 32
BUILD_DIGEST_BYTES = 32

# --- the labels --------------------------------------------------------------

REGISTRATION_LABEL = "protocol-stack:v10:hub-registration"
APPROVAL_LABEL = "protocol-stack:v10:hub-approval"
ATTESTATION_LABEL = "protocol-stack:v10:machine-attestation"

# The HUB key and the attesting key between them sign these two, where version
# nine signed six. The registration is the only one an attester signs.
HUB_MESSAGE_LABELS: tuple[str, ...] = (REGISTRATION_LABEL, APPROVAL_LABEL)
VERIFIER_SIGNED_LABELS: tuple[str, ...] = (REGISTRATION_LABEL,)

# --- the one new transaction kind --------------------------------------------

REGISTER_MACHINE_KEY = 23

TRANSACTION_KINDS: dict[int, str] = dict(v9.TRANSACTION_KINDS) | {
    REGISTER_MACHINE_KEY: "register_machine_key",
}

# Kind 10 gains `attesting_seat_id:u32`. Kind 23 is
# `seat_id:u32 || machine_public_key:32 || build_digest:32 ||
# attestation_signature:64 || hub_signature:64`.
BODY_BYTES: dict[int, int] = dict(v9.BODY_BYTES) | {
    v9.HUB_REGISTER: v9.BODY_BYTES[v9.HUB_REGISTER] + 4,
    REGISTER_MACHINE_KEY: 4
    + 32
    + BUILD_DIGEST_BYTES
    + v9.SIGNATURE_BYTES
    + v9.HUB_SIGNATURE_BYTES,
}

KIND_SCHEME: dict[int, int] = dict(v9.KIND_SCHEME) | {
    REGISTER_MACHINE_KEY: v9.SCHEME_SIGNER,
}

# The kinds whose body carries a HUB approval. Kind 17 carries one only when it
# relaxes; the lifetime rule reads the field rather than the kind, so a
# tightening presented with the field absent is not governed.
APPROVAL_KINDS = frozenset(
    {
        v9.PURCHASE_SEAT,
        v9.ACTIVATE_SEAT,
        v9.MINT_NODE,
        v9.MINT_REFERRAL,
        v9.SET_SECURITY_POSTURE,
        v9.MINT_VERIFIED_USER,
        v9.TRANSFER_VERIFIED,
        v9.MINT_POOL,
        REGISTER_MACHINE_KEY,
    }
)

# The kinds that always carry a HUB proof: the registration, the four identity
# administration kinds the HUB key signs whole, and kind 23.
ALWAYS_PROVEN_KINDS = frozenset(
    {
        v9.HUB_REGISTER,
        v9.ESCROW_CREATE,
        v9.ESCROW_DELETE,
        v9.SIGNER_ADD,
        v9.SIGNER_REVOKE,
        REGISTER_MACHINE_KEY,
    }
)

# --- the three new state entries ----------------------------------------------

MACHINE_KEY_ENTRY = 24
LAUNCH_RETIREMENT_ENTRY = 25
MACHINE_KEY_OWNER_ENTRY = 26

ADDED_IN_V10_ENTRY_KINDS: dict[int, str] = {
    MACHINE_KEY_ENTRY: "machine_key",
    LAUNCH_RETIREMENT_ENTRY: "launch_retirement",
    MACHINE_KEY_OWNER_ENTRY: "machine_key_owner",
}

ENTRY_KINDS: dict[int, str] = dict(v9.ENTRY_KINDS) | ADDED_IN_V10_ENTRY_KINDS

ENTRY_KEY_BYTES: dict[int, int] = dict(v9.ENTRY_KEY_BYTES) | {
    MACHINE_KEY_ENTRY: 1 + 4,
    LAUNCH_RETIREMENT_ENTRY: 1,
    MACHINE_KEY_OWNER_ENTRY: 1 + 32,
}

# The machine-key value: key, build digest, registered height, last met window,
# registration window, and the count in that window.
ENTRY_VALUE_BYTES: dict[int, int | None] = dict(v9.ENTRY_VALUE_BYTES) | {
    MACHINE_KEY_ENTRY: 32 + BUILD_DIGEST_BYTES + 8 + 8 + 8 + 4,
    LAUNCH_RETIREMENT_ENTRY: 8,
    MACHINE_KEY_OWNER_ENTRY: 4,
}

# --- the result code space ---------------------------------------------------

ADDED_IN_V10_RESULT_CODES: dict[int, str] = {
    45: "LAUNCH_KEY_RETIRED",
    46: "MACHINE_KEY_NOT_FOUND",
    47: "MACHINE_NOT_ACTIVE",
    48: "REGISTRATION_LIMIT",
    49: "APPROVAL_LIFETIME_EXCEEDED",
}

RESULT_CODES: dict[int, str] = dict(v9.RESULT_CODES) | ADDED_IN_V10_RESULT_CODES

CODE_NUMBER: dict[str, int] = {name: number for number, name in RESULT_CODES.items()}

# --- genesis -----------------------------------------------------------------

# Version nine's prefix with `build_authority_key` after `dispute_authority_key`.
# `account_count` stays last, because the account entries follow it.
GENESIS_PREFIX_BYTES = v9.GENESIS_PREFIX_BYTES + BUILD_AUTHORITY_KEY_BYTES

# **The account bound moves for the first time**, from 21,842 to 21,841. A
# thirty-two-octet field crosses an entry boundary where version nine's eight
# octets did not. The bound stays unreachable, because zero genesis accounts is
# still required.
ACCOUNT_BOUND_UNDER_THE_WIDER_PREFIX = (
    v9.MAX_OBJECT_BYTES - GENESIS_PREFIX_BYTES
) // v9.ACCOUNT_ENTRY_BYTES
MAX_GENESIS_ACCOUNTS = ACCOUNT_BOUND_UNDER_THE_WIDER_PREFIX
