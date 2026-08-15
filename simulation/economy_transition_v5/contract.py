"""Fixed constants, tables, and code spaces of `economy-transition-v5`.

Version five is version four with one field's meaning corrected, so almost
everything here is version four's and is imported from it by name rather than
restated. A restatement would be a second copy of twelve kind identifiers,
twelve entry kinds, and twenty-six result codes with nothing keeping the two
equal, which is the reason ADR 0026 gives for sharing an implementation and
ADR 0029 for not sharing one — and the condition ADR 0029 names, a revised
transition, is not met by a relabelling.

What version five defines for itself is exactly what the specification's
version-identity table lists: the chain-ID, state-root, and economy-tree
labels, the state-root and genesis schema versions, the receipt version, and
the eight HUB message labels. The two transaction signing labels stay at
`protocol-stack:v1:` for the reason every version since two has given.

One table is new and is not a relabelling. `MESSAGE_IDENTITY_SOURCE` records,
for each of the eight HUB messages, where a chain obtains the identity the
message binds. Version four's `address_add` had no answer, which is the defect
[ADR 0037](../../docs/decisions/0037-economy-transition-v5-the-kind-eleven-identity.md)
records; writing the sources down makes that class of defect visible by reading
one table rather than by cross-referencing a body layout against a message.
"""

from __future__ import annotations

from simulation.economy_transition_v4.contract import (
    ACCOUNT_ENTRY_BYTES,
    ACTIVATE_SEAT,
    ACTIVITY_THRESHOLD_SECONDS,
    ADD_MANAGER,
    ADDED_RESULT_CODES,
    ADMISSION_CODES,
    ANY_SENDER_KINDS,
    ASSIGNMENT_LAG_WINDOWS,
    BASE_PERMISSION_LEGS,
    BASE_PERMISSION_TOTAL,
    BENEFICIARY_KINDS,
    BODY_BYTES,
    CARRIED_MODEL_CODES,
    CARRY_ENTRY,
    CHANNEL_ENTRY,
    CODE_NUMBER,
    COMMUNITY_GRANTS_BENEFICIARY,
    CYCLE_ASSIGNMENT_ENTRY,
    CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES,
    CYCLE_BLOCKS,
    DEVELOPER_INCENTIVES_BENEFICIARY,
    DIRECT_BENEFICIARY,
    DIRECT_DECISION_ENTRY,
    DIRECT_ISSUE,
    DIRECT_ISSUE_CHANNELS,
    ENTRY_KEY_BYTES,
    ENTRY_KINDS,
    ENTRY_VALUE_BYTES,
    ENVELOPE_SCHEMA_VERSION,
    FOUNDER_OPERATOR_CHANNEL,
    FOUNDER_SEAT_CAPACITY,
    GENESIS_MAGIC,
    GENESIS_PREFIX_BYTES,
    GUARD_MODEL_CODES,
    HEADER_BYTES,
    HUB_ADD_ADDRESS,
    HUB_ADDRESS_ENTRY,
    HUB_GATED_KINDS,
    HUB_IDENTITY_ENTRY,
    HUB_REGISTER,
    HUB_REMOVE_ADDRESS,
    HUB_SIGNATURE_BYTES,
    INHERITED_RESULT_CODES,
    ISSUANCE_CYCLES_PER_SEAT,
    LEG_BENEFICIARY_KIND,
    MANIFEST_DIGEST_HEX,
    MAX_CYCLE_INDEX,
    MAX_GENESIS_ACCOUNTS,
    MAX_IDENTITY_ADDRESSES,
    MAX_OBJECT_BYTES,
    MAX_SEAT_ID,
    MAX_SEAT_MANAGERS,
    MAX_SEATS_PER_IDENTITY,
    MAX_U64,
    MINT_ACCUMULATION_CAP,
    MINT_NODE,
    MINT_NODE_VERIFIED,
    MINT_REFERRAL,
    PURCHASE_SEAT,
    RECEIPT_MAGIC,
    REFERRAL_BALANCE_ENTRY,
    REFERRAL_CHANNEL,
    REFERRAL_LEG_ATOMIC,
    RESULT_CODES,
    SEAT_ENTRY,
    SEAT_MANAGER_ENTRY,
    SET_MINT_BIOMETRIC,
    SIGN_LABEL,
    SIGNATURE_BYTES,
    SIGNATURE_SCHEME,
    SINGLETON_BENEFICIARY_ID,
    SINGLETON_BENEFICIARY_KINDS,
    SYSTEM_CREATOR_BENEFICIARY,
    TRAILER_BYTES,
    TRANSACTION_KINDS,
    TRANSACTION_MAGIC,
    TRANSFER,
    TX_ID_LABEL,
    TYPED_CUSTODY_ENTRY,
    UNREFERRED_POOL_ENTRY,
    UNREPRESENTABLE_MODEL_CODES,
    VENTURE_ESCROW_BENEFICIARY,
    VERIFIER_KEY_ENTRY,
    VERSION_THREE_RESULT_CODES,
)

# Version five's own identity. Every construction that separates one contract's
# commitments from another's takes `v5`; nothing else does.
RECEIPT_VERSION = 5
GENESIS_SCHEMA_VERSION = 5

CHAIN_ID_LABEL = "protocol-stack:v5:chain-id"
STATE_ROOT_LABEL = "protocol-stack:v5:state-root"
ECONOMY_TREE_PREFIX = "protocol-stack:v5:economy"

STATE_ROOT_SCHEMA_VERSION = 5

# The accepted version-one account derivation. Version five needs it and no
# earlier transition package did, because this is the first contract in which a
# message is built from the sender rather than from a supplied argument.
ACCOUNT_ID_LABEL = "protocol-stack:v1:account"
ACCOUNT_ID_DOMAIN = 0x01

REGISTRATION_LABEL = "protocol-stack:v5:hub-registration"
ADDRESS_ADD_LABEL = "protocol-stack:v5:hub-address-add"
ADDRESS_REMOVE_LABEL = "protocol-stack:v5:hub-address-remove"
PURCHASE_LABEL = "protocol-stack:v5:seat-purchase"
ACTIVATION_LABEL = "protocol-stack:v5:seat-activation"
MINT_LABEL = "protocol-stack:v5:seat-mint"
MINT_BIOMETRIC_DISABLE_LABEL = "protocol-stack:v5:mint-biometric-disable"
MANAGER_LABEL = "protocol-stack:v5:seat-manager"

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
VERIFIER_SIGNED_LABELS: tuple[str, ...] = (REGISTRATION_LABEL,)

# Where a chain obtains the HUB identity each message binds. Every source is
# either the transaction's own bytes or one state entry the transaction names,
# so every message is computable from a transaction and the state it reads.
BODY_SOURCE = "body"
SENDER_ADDRESS_ENTRY_SOURCE = "sender_address_entry"
NAMED_ADDRESS_ENTRY_SOURCE = "named_account_address_entry"
SEAT_ENTRY_SOURCE = "seat_entry"
NO_SOURCE = "none"

MESSAGE_IDENTITY_SOURCE: dict[str, str] = {
    "registration": BODY_SOURCE,
    "address_add": BODY_SOURCE,
    "address_remove": NAMED_ADDRESS_ENTRY_SOURCE,
    "purchase": SENDER_ADDRESS_ENTRY_SOURCE,
    "activation": SEAT_ENTRY_SOURCE,
    "mint": SEAT_ENTRY_SOURCE,
    "mint_biometric_disable": SEAT_ENTRY_SOURCE,
    "manager": SEAT_ENTRY_SOURCE,
}

# Version four's one unreachable source, recorded so the correction is legible
# beside the table rather than only in the ADR. Its kind 11 body carried an
# account and no identity, its sender was deliberately unconstrained, and
# trying every registered key is neither canonical nor bounded.
VERSION_FOUR_ADDRESS_ADD_IDENTITY_SOURCE = NO_SOURCE

# Kind 11's ordered rejection conditions. Condition 2 is what changes: the
# sender is the account being linked, so it is the sender that must be
# unlinked, and squatting on another person's address becomes unrepresentable.
ADD_ADDRESS_REJECTION_ORDER: tuple[str, ...] = (
    "NOT_HUB_VERIFIED",
    "REPLAY",
    "ADDRESS_LIMIT",
    "UNAUTHORIZED",
)
