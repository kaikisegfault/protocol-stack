"""Fixed constants, tables, and code spaces of `economy-transition-v6`.

Every founder-directed figure here is read from an accepted contract rather than
restated. The channel identifiers are the accepted manifest's array indexes, the
seat capacity, the per-person seat bound, and the issuance-cycle count come from
the manifest layer, and the window grid comes from the cycle-boundary contract,
so one founder-directed value keeps one home.

Version six makes a verified identity the root of every account. An escrow holds
value and has no key; a signer key is assigned to exactly one escrow and is what
acts on it; the identity is the admin over both. The settlement — the
accumulation cap, the cycle-assignment record, the bounded mint walk — is
version three's and is imported rather than copied, because a second
implementation of one accepted contract has nothing keeping the two equal.
"""

from __future__ import annotations

from simulation.cycle_boundary import contract as boundary
from simulation.economy_transition_v4 import contract as v4
from simulation.founder_economy_v2 import contract as manifest
from simulation.uptime_measurement import contract as uptime

MAX_U64 = (1 << 64) - 1
MAX_OBJECT_BYTES = v4.MAX_OBJECT_BYTES

FOUNDER_SEAT_CAPACITY = manifest.FOUNDER_SEAT_CAPACITY
ISSUANCE_CYCLES_PER_SEAT = manifest.ISSUANCE_CYCLES_PER_SEAT
MAX_SEAT_ID = FOUNDER_SEAT_CAPACITY - 1
CYCLE_BLOCKS = boundary.CYCLE_BLOCKS
SLOT_BLOCKS = uptime.SLOT_BLOCKS
SLOTS_PER_WINDOW = uptime.SLOTS_PER_WINDOW
MAX_SEATS_PER_IDENTITY = manifest.MAXIMUM_SEATS_PER_PERSON

MANIFEST_DIGEST_HEX = manifest.MANIFEST_DIGEST

# The envelope. Unchanged since version two, and the whole compatibility
# argument: the header is the accepted version-one transfer's first 80 bytes and
# the trailer its last 16.
HEADER_BYTES = v4.HEADER_BYTES
TRAILER_BYTES = v4.TRAILER_BYTES
SIGNATURE_BYTES = v4.SIGNATURE_BYTES
HUB_SIGNATURE_BYTES = v4.HUB_SIGNATURE_BYTES

TRANSACTION_MAGIC = v4.TRANSACTION_MAGIC
RECEIPT_MAGIC = v4.RECEIPT_MAGIC
GENESIS_MAGIC = v4.GENESIS_MAGIC

ENVELOPE_SCHEMA_VERSION = v4.ENVELOPE_SCHEMA_VERSION
RECEIPT_VERSION = 6
GENESIS_SCHEMA_VERSION = 6

# Version one fixes the scheme byte at 1 and reads offset 40 as the sender's
# public key. Version six reads that field as an authority public key and lets
# the scheme say whose. Both verify the envelope signature against the header
# key, so admission still reads no state.
SCHEME_SIGNER = 1
SCHEME_IDENTITY = 2
SIGNATURE_SCHEMES: dict[int, str] = {
    SCHEME_SIGNER: "signer_key",
    SCHEME_IDENTITY: "hub_identity_key",
}

SIGN_LABEL = v4.SIGN_LABEL
TX_ID_LABEL = v4.TX_ID_LABEL
ACCOUNT_LABEL = "protocol-stack:v1:account"

CHAIN_ID_LABEL = "protocol-stack:v6:chain-id"
STATE_ROOT_LABEL = "protocol-stack:v6:state-root"
ECONOMY_TREE_PREFIX = "protocol-stack:v6:economy"
ESCROW_LABEL = "protocol-stack:v6:escrow"

STATE_ROOT_SCHEMA_VERSION = 6

TRANSFER = 1
PURCHASE_SEAT = 2
ACTIVATE_SEAT = 3
MINT_NODE = 4
MINT_REFERRAL = 5
DIRECT_ISSUE = 6
HUB_REGISTER = 10
ESCROW_CREATE = 13
ESCROW_DELETE = 14
SIGNER_ADD = 15
SIGNER_REVOKE = 16
SET_SECURITY_POSTURE = 17
MINT_VERIFIED_USER = 18
TRANSFER_VERIFIED = 19

TRANSACTION_KINDS: dict[int, str] = {
    TRANSFER: "native_transfer",
    PURCHASE_SEAT: "purchase_seat",
    ACTIVATE_SEAT: "activate_seat",
    MINT_NODE: "mint_node",
    MINT_REFERRAL: "mint_referral",
    DIRECT_ISSUE: "direct_issue",
    HUB_REGISTER: "hub_register",
    ESCROW_CREATE: "escrow_create",
    ESCROW_DELETE: "escrow_delete",
    SIGNER_ADD: "signer_add",
    SIGNER_REVOKE: "signer_revoke",
    SET_SECURITY_POSTURE: "set_security_posture",
    MINT_VERIFIED_USER: "mint_verified_user",
    TRANSFER_VERIFIED: "native_transfer_verified",
}

# Retired rather than reused. Each lost its subject when the account model
# changed, and assigning a new meaning to a number a reader associates with an
# accepted contract is the cheapest possible way to create an auditing mistake.
RETIRED_KINDS: dict[int, str] = {
    7: "mint_node_verified",
    8: "set_mint_biometric",
    9: "add_manager",
    11: "hub_add_address",
    12: "hub_remove_address",
}

# Every kind is fixed-length. Five kinds share a 96-octet body, which is the
# case version two anticipated when it required a decoder to dispatch on the
# kind byte rather than on the length.
BODY_BYTES: dict[int, int] = {
    TRANSFER: 40,
    PURCHASE_SEAT: 101,
    ACTIVATE_SEAT: 68,
    MINT_NODE: 100,
    MINT_REFERRAL: 96,
    DIRECT_ISSUE: 105,
    HUB_REGISTER: 128,
    ESCROW_CREATE: 64,
    ESCROW_DELETE: 96,
    SIGNER_ADD: 96,
    SIGNER_REVOKE: 96,
    SET_SECURITY_POSTURE: 77,
    MINT_VERIFIED_USER: 96,
    TRANSFER_VERIFIED: 104,
}

# A kind fixes its scheme, so no transaction is ambiguous about which rule
# authorizes it. The six identity-administration kinds are scheme 2 because
# they must work for a person holding no key at all.
KIND_SCHEME: dict[int, int] = {
    TRANSFER: SCHEME_SIGNER,
    PURCHASE_SEAT: SCHEME_SIGNER,
    ACTIVATE_SEAT: SCHEME_SIGNER,
    MINT_NODE: SCHEME_SIGNER,
    MINT_REFERRAL: SCHEME_SIGNER,
    DIRECT_ISSUE: SCHEME_SIGNER,
    HUB_REGISTER: SCHEME_IDENTITY,
    ESCROW_CREATE: SCHEME_IDENTITY,
    ESCROW_DELETE: SCHEME_IDENTITY,
    SIGNER_ADD: SCHEME_IDENTITY,
    SIGNER_REVOKE: SCHEME_IDENTITY,
    SET_SECURITY_POSTURE: SCHEME_SIGNER,
    MINT_VERIFIED_USER: SCHEME_SIGNER,
    TRANSFER_VERIFIED: SCHEME_SIGNER,
}

# The three mints carry a confirmation field that must be 64 zero octets when
# the destination's posture requires none. A transfer cannot, because widening
# kind 1's body would end a byte identity carried since M1, so it is two kinds.
CONFIRMABLE_MINTS = frozenset({MINT_NODE, MINT_REFERRAL, MINT_VERIFIED_USER})
ISSUING_KINDS = frozenset({HUB_REGISTER, MINT_NODE, MINT_REFERRAL, MINT_VERIFIED_USER, DIRECT_ISSUE})

# Six messages, down from version four's eight: address add, address remove, and
# the seat manager message lost their kinds, and the mint and posture messages
# replace the two the per-seat flag needed.
REGISTRATION_LABEL = "protocol-stack:v6:hub-registration"
PURCHASE_LABEL = "protocol-stack:v6:seat-purchase"
ACTIVATION_LABEL = "protocol-stack:v6:seat-activation"
MINT_CONFIRM_LABEL = "protocol-stack:v6:mint-confirm"
POSTURE_RELAX_LABEL = "protocol-stack:v6:posture-relax"
TRANSFER_CONFIRM_LABEL = "protocol-stack:v6:transfer-confirm"

HUB_MESSAGE_LABELS: tuple[str, ...] = (
    REGISTRATION_LABEL,
    PURCHASE_LABEL,
    ACTIVATION_LABEL,
    MINT_CONFIRM_LABEL,
    POSTURE_RELAX_LABEL,
    TRANSFER_CONFIRM_LABEL,
)
# The only message the ecosystem verifier signs.
VERIFIER_SIGNED_LABELS: tuple[str, ...] = (REGISTRATION_LABEL,)

# Channel 8 has left the reserved set, because ADR 0042 decided both its
# eligibility and its rate. Kinds 10 and 18 issue it.
DIRECT_ISSUE_CHANNELS: tuple[int, ...] = (5, 6, 9)

ADMISSION_CODES: dict[int, str] = dict(v4.ADMISSION_CODES)

RESULT_CODES: dict[int, str] = dict(v4.RESULT_CODES) | {
    26: "SIGNER_NOT_FOUND",
    27: "RECIPIENT_NOT_REGISTERED",
    28: "ESCROW_NOT_FOUND",
    29: "ESCROW_NOT_OWNED",
    30: "ESCROW_NOT_EMPTY",
    31: "SIGNER_LIMIT",
    32: "NOT_ENROLLED",
}

INHERITED_RESULT_CODES: tuple[int, ...] = tuple(range(0, 9))
VERSION_FOUR_RESULT_CODES: tuple[int, ...] = tuple(range(0, 26))
ADDED_RESULT_CODES: tuple[int, ...] = tuple(range(26, 33))

# Frozen and unreachable here. Each lost its subject rather than its meaning,
# and renumbering a frozen code space is the compatibility break the space
# exists to prevent.
UNREACHABLE_RESULT_CODES: dict[int, str] = {
    4: "an escrow that resolves always has an account entry",
    23: "a seat has no managers",
    25: "an identity's addresses are escrows it creates, not accounts it links",
}

CODE_NUMBER: dict[str, int] = {name: number for number, name in RESULT_CODES.items()}

# The economy model is unchanged between transition versions two through six,
# so its total three-way disposition is unchanged with it.
CARRIED_MODEL_CODES: dict[str, str] = dict(v4.CARRIED_MODEL_CODES)
GUARD_MODEL_CODES: tuple[str, ...] = v4.GUARD_MODEL_CODES
UNREPRESENTABLE_MODEL_CODES: dict[str, str] = dict(v4.UNREPRESENTABLE_MODEL_CODES)

SEAT_ENTRY = 1
CHANNEL_ENTRY = 2
CYCLE_ASSIGNMENT_ENTRY = 3
REFERRAL_BALANCE_ENTRY = 4
DIRECT_DECISION_ENTRY = 5
TYPED_CUSTODY_ENTRY = 6
CARRY_ENTRY = 7
VERIFIER_KEY_ENTRY = 8
HUB_IDENTITY_ENTRY = 10
UNREFERRED_POOL_ENTRY = 12
ESCROW_ENTRY = 13
SIGNER_ENTRY = 14
VERIFIED_USER_ENTRY = 15
VERIFIED_USER_COUNTER_ENTRY = 16

ENTRY_KINDS: dict[int, str] = {
    SEAT_ENTRY: "seat",
    CHANNEL_ENTRY: "channel",
    CYCLE_ASSIGNMENT_ENTRY: "cycle_assignment",
    REFERRAL_BALANCE_ENTRY: "referral_balance",
    DIRECT_DECISION_ENTRY: "direct_decision",
    TYPED_CUSTODY_ENTRY: "typed_custody",
    CARRY_ENTRY: "carry",
    VERIFIER_KEY_ENTRY: "verifier_key",
    HUB_IDENTITY_ENTRY: "hub_identity",
    UNREFERRED_POOL_ENTRY: "unreferred_pool",
    ESCROW_ENTRY: "escrow",
    SIGNER_ENTRY: "signer",
    VERIFIED_USER_ENTRY: "verified_user_enrollment",
    VERIFIED_USER_COUNTER_ENTRY: "verified_user_counter",
}

RETIRED_ENTRY_KINDS: dict[int, str] = {9: "seat_manager", 11: "hub_address"}

ENTRY_KEY_BYTES: dict[int, int] = {
    SEAT_ENTRY: 5,
    CHANNEL_ENTRY: 2,
    CYCLE_ASSIGNMENT_ENTRY: 9,
    REFERRAL_BALANCE_ENTRY: 33,
    DIRECT_DECISION_ENTRY: 33,
    TYPED_CUSTODY_ENTRY: 34,
    CARRY_ENTRY: 2,
    VERIFIER_KEY_ENTRY: 1,
    HUB_IDENTITY_ENTRY: 33,
    UNREFERRED_POOL_ENTRY: 1,
    ESCROW_ENTRY: 33,
    SIGNER_ENTRY: 33,
    VERIFIED_USER_ENTRY: 33,
    VERIFIED_USER_COUNTER_ENTRY: 1,
}

ENTRY_VALUE_BYTES: dict[int, int | None] = {
    SEAT_ENTRY: 82,
    CHANNEL_ENTRY: 16,
    CYCLE_ASSIGNMENT_ENTRY: None,
    REFERRAL_BALANCE_ENTRY: 24,
    DIRECT_DECISION_ENTRY: 0,
    TYPED_CUSTODY_ENTRY: 8,
    CARRY_ENTRY: 8,
    VERIFIER_KEY_ENTRY: 32,
    HUB_IDENTITY_ENTRY: 52,
    UNREFERRED_POOL_ENTRY: 16,
    ESCROW_ENTRY: 49,
    SIGNER_ENTRY: 32,
    VERIFIED_USER_ENTRY: 24,
    VERIFIED_USER_COUNTER_ENTRY: 8,
}

CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES = v4.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES

BENEFICIARY_KINDS: dict[int, str] = dict(v4.BENEFICIARY_KINDS)
SINGLETON_BENEFICIARY_KINDS: tuple[int, ...] = v4.SINGLETON_BENEFICIARY_KINDS
SINGLETON_BENEFICIARY_ID = v4.SINGLETON_BENEFICIARY_ID

GENESIS_PREFIX_BYTES = v4.GENESIS_PREFIX_BYTES
ACCOUNT_ENTRY_BYTES = v4.ACCOUNT_ENTRY_BYTES
MAX_GENESIS_ACCOUNTS = v4.MAX_GENESIS_ACCOUNTS

BASE_PERMISSION_LEGS = v4.BASE_PERMISSION_LEGS
LEG_BENEFICIARY_KIND = v4.LEG_BENEFICIARY_KIND
BASE_PERMISSION_TOTAL = v4.BASE_PERMISSION_TOTAL
FOUNDER_OPERATOR_CHANNEL = v4.FOUNDER_OPERATOR_CHANNEL
REFERRAL_CHANNEL = v4.REFERRAL_CHANNEL
REFERRAL_LEG_ATOMIC = v4.REFERRAL_LEG_ATOMIC

MINT_ACCUMULATION_CAP = v4.MINT_ACCUMULATION_CAP
ASSIGNMENT_LAG_WINDOWS = v4.ASSIGNMENT_LAG_WINDOWS

# A resource limit rather than a statement about participants. Escrows per
# identity are deliberately unbounded: the founder direction is that a person
# holds as many as they want, and each costs a fee to create.
MAX_SIGNERS_PER_ESCROW = 16

# Channel 8, decided by ADR 0042. The population and the period are
# founder-supplied and the rate is what they and the accepted cap determine.
VERIFIED_USER_CHANNEL = manifest.CHANNEL_IDS.index("hub_verified_user_incentives")
VERIFIED_USER_POPULATION = 1_000_000
VERIFIED_USER_CYCLES = ISSUANCE_CYCLES_PER_SEAT
VERIFIED_USER_DAILY_ATOMIC = 171_000_000
VERIFIED_USER_CHANNEL_CAP = manifest.CHANNEL_CAPS["hub_verified_user_incentives"]

# The default posture a new escrow takes: confirmation on for every financial
# operation, which is what the constitution directs.
DEFAULT_REQUIRES_CONFIRMATION = True
DEFAULT_MIN_AMOUNT_ATOMIC = 0
DEFAULT_EXEMPT_SLOT_MASK = 0
MAX_EXEMPT_SLOT_MASK = (1 << SLOTS_PER_WINDOW) - 1
