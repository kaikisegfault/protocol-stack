"""Fixed constants, tables, and code spaces of `economy-transition-v7`.

Version seven is version six with the per-channel carry deleted from state and
replaced by a recovery pool. Four things move — the state key space, the cycle
assignment record's fixed part, the settlement's steps 5 through 7, and the
per-channel conservation identity — and the manifest binding moves from version
two to version three. Everything else carries over and is imported.

**The carried set is a declaration rather than a hundred copied lines.**
`CARRIED_FROM_V6` names every constant this version takes unchanged, `REBOUND`
names the ones whose value is identical and whose source moved to the version
three manifest, `REVISED_IN_V7` names the ones that changed, and `ADDED_IN_V7`
names the ones that are new. `tests/simulation/economy_transition_v7_carryover_test.py`
requires the four sets to partition version six's public surface exactly, so a
constant that moved without a vector reaching it fails a test rather than
surviving as a copy nobody compared.

Copying the tables by hand would produce a second implementation of an accepted
contract with nothing keeping the two equal, which is the defect ADR 0026 and
ADR 0029 both exist to avoid and which ADR 0038 applied in this direction.
"""

from __future__ import annotations

from simulation.economy_transition_v6 import contract as v6
from simulation.founder_economy_manifest_v3 import contract as manifest

# --- what version seven takes unchanged -------------------------------------

CARRIED_FROM_V6: tuple[str, ...] = (
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
    "BODY_BYTES",
    "CARRIED_MODEL_CODES",
    "CHANNEL_ENTRY",
    "CODE_NUMBER",
    "CONFIRMABLE_MINTS",
    "CYCLE_ASSIGNMENT_ENTRY",
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
    "GENESIS_MAGIC",
    "GENESIS_PREFIX_BYTES",
    "GUARD_MODEL_CODES",
    "HEADER_BYTES",
    "HUB_IDENTITY_ENTRY",
    "HUB_MESSAGE_LABELS",
    "HUB_REGISTER",
    "HUB_SIGNATURE_BYTES",
    "INHERITED_RESULT_CODES",
    "ISSUING_KINDS",
    "KIND_SCHEME",
    "LEG_BENEFICIARY_KIND",
    "MAX_EXEMPT_SLOT_MASK",
    "MAX_GENESIS_ACCOUNTS",
    "MAX_OBJECT_BYTES",
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
    "REFERRAL_BALANCE_ENTRY",
    "REFERRAL_CHANNEL",
    "REFERRAL_LEG_ATOMIC",
    "REGISTRATION_LABEL",
    "RESULT_CODES",
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
    "TRAILER_BYTES",
    "TRANSACTION_KINDS",
    "TRANSACTION_MAGIC",
    "TRANSFER",
    "TRANSFER_CONFIRM_LABEL",
    "TRANSFER_VERIFIED",
    "TX_ID_LABEL",
    "TYPED_CUSTODY_ENTRY",
    "UNREACHABLE_RESULT_CODES",
    "UNREFERRED_POOL_ENTRY",
    "UNREPRESENTABLE_MODEL_CODES",
    "VERIFIED_USER_COUNTER_ENTRY",
    "VERIFIED_USER_CYCLES",
    "VERIFIED_USER_DAILY_ATOMIC",
    "VERIFIED_USER_ENTRY",
    "VERIFIED_USER_POPULATION",
    "VERIFIER_KEY_ENTRY",
    "VERIFIER_SIGNED_LABELS",
    "VERSION_FOUR_RESULT_CODES",
)

for _name in CARRIED_FROM_V6:
    globals()[_name] = getattr(v6, _name)
del _name

# --- the same value, read from the version three manifest -------------------

# ADR 0053's manifest renames channel 9 and changes nothing else, so every
# figure below is identical to the one version six reads from version two. The
# rebinding is what makes the accepted contract this version names the one it
# actually reads; the vectors record the two digests and the unchanged figures
# together.
REBOUND: tuple[str, ...] = (
    "FOUNDER_SEAT_CAPACITY",
    "ISSUANCE_CYCLES_PER_SEAT",
    "MAX_SEATS_PER_IDENTITY",
    "VERIFIED_USER_CHANNEL",
    "VERIFIED_USER_CHANNEL_CAP",
)

FOUNDER_SEAT_CAPACITY = manifest.FOUNDER_SEAT_CAPACITY
ISSUANCE_CYCLES_PER_SEAT = manifest.ISSUANCE_CYCLES_PER_SEAT
MAX_SEATS_PER_IDENTITY = manifest.MAXIMUM_SEATS_PER_PERSON
VERIFIED_USER_CHANNEL = manifest.CHANNEL_IDS.index("hub_verified_user_incentives")
VERIFIED_USER_CHANNEL_CAP = manifest.CHANNEL_CAPS["hub_verified_user_incentives"]

# --- what version seven changes ---------------------------------------------

REVISED_IN_V7: tuple[str, ...] = (
    "CHAIN_ID_LABEL",
    "CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES",
    "ECONOMY_TREE_PREFIX",
    "ENTRY_KEY_BYTES",
    "ENTRY_KINDS",
    "ENTRY_VALUE_BYTES",
    "GENESIS_SCHEMA_VERSION",
    "MANIFEST_DIGEST_HEX",
    "RECEIPT_VERSION",
    "RETIRED_ENTRY_KINDS",
    "STATE_ROOT_LABEL",
    "STATE_ROOT_SCHEMA_VERSION",
)

CHAIN_ID_LABEL = "protocol-stack:v7:chain-id"
STATE_ROOT_LABEL = "protocol-stack:v7:state-root"
ECONOMY_TREE_PREFIX = "protocol-stack:v7:economy"

STATE_ROOT_SCHEMA_VERSION = 7
GENESIS_SCHEMA_VERSION = 7
RECEIPT_VERSION = 7

MANIFEST_DIGEST_HEX = manifest.MANIFEST_DIGEST
SUPERSEDED_MANIFEST_DIGEST_HEX = manifest.SUPERSEDED_DIGEST

# --- the recovery pool ------------------------------------------------------

ADDED_IN_V7: tuple[str, ...] = (
    "RECOVERY_POOL_ENTRY",
    "RECOVERY_POOL_LEGS",
)

RECOVERY_POOL_ENTRY = 17

# The five Founder Node legs of a base permission, in the accepted manifest's
# channel order. The other five channels have no base permission and therefore
# no remainder, which is why one entry with five fields replaces ten entries of
# which five were structurally always zero.
RECOVERY_POOL_LEGS: tuple[int, ...] = tuple(
    channel for channel, _amount in v6.BASE_PERMISSION_LEGS
)

# The record's fixed part grows by the five absorbed amounts, which sit after
# `bitmap_bits` so every fixed-width field stays contiguous ahead of the
# variable-length tail.
CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES = v6.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES + 8 * len(
    RECOVERY_POOL_LEGS
)

# Kind 7 joins 9 and 11. A retired number is never reused: assigning a new
# meaning to a number a reader associates with an accepted contract is the
# cheapest possible way to create an auditing mistake.
RETIRED_ENTRY_KINDS: dict[int, str] = {
    7: "carry",
    9: "seat_manager",
    11: "hub_address",
}

ENTRY_KINDS: dict[int, str] = {
    kind: name
    for kind, name in v6.ENTRY_KINDS.items()
    if kind not in RETIRED_ENTRY_KINDS
}
ENTRY_KINDS[RECOVERY_POOL_ENTRY] = "recovery_pool"

ENTRY_KEY_BYTES: dict[int, int] = {
    kind: width
    for kind, width in v6.ENTRY_KEY_BYTES.items()
    if kind not in RETIRED_ENTRY_KINDS
}
ENTRY_KEY_BYTES[RECOVERY_POOL_ENTRY] = 1

ENTRY_VALUE_BYTES: dict[int, int | None] = {
    kind: width
    for kind, width in v6.ENTRY_VALUE_BYTES.items()
    if kind not in RETIRED_ENTRY_KINDS
}
ENTRY_VALUE_BYTES[RECOVERY_POOL_ENTRY] = 8 * len(RECOVERY_POOL_LEGS)
