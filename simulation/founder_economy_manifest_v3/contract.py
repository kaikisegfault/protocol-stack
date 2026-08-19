"""Fixed Founder Economy contract values from founder-economy-manifest-v3.

Version three renames issuance channel 9 and changes nothing else. The whole
founder-directed table is therefore *derived* from the accepted version-two
table by applying that one rename, rather than restated. A third hand-written
copy of ten caps, five legs, and a denomination would make "nothing else moved"
a claim a reader has to check by eye; deriving it makes a moved cap impossible
to express here at all.

Independence still comes from outside this module. The verifier's `expected.py`
converts the Founder Constitution's two allocation tables by hand and imports
nothing from `simulation/`, so the founder-directed values are compared against
their source rather than against version two's reading of it.

`simulation/founder_economy_v2/contract.py` is the retained version-two table
and is not modified. Both contracts coexist: version two states what the
accepted M3.1 through M3.10 evidence proves.
"""

from __future__ import annotations

from ..founder_economy_v2 import contract as manifest_v2

# --- version three's own identity -------------------------------------------

MANIFEST_SCHEMA = "protocol-stack/founder-economy-manifest/v3"
MANIFEST_LABEL = "protocol-stack:founder-economy:manifest-v3"
MANIFEST_CANONICAL_LENGTH = 2261
MANIFEST_DIGEST = "af153c99adf7c49e5a92563946cf0e60dfd7a58785462530988f661aa68faaa7"

SUPERSEDED_SCHEMA = manifest_v2.MANIFEST_SCHEMA
SUPERSEDED_LABEL = manifest_v2.MANIFEST_LABEL
SUPERSEDED_DIGEST = manifest_v2.MANIFEST_DIGEST
SUPERSEDED_CANONICAL_LENGTH = manifest_v2.MANIFEST_CANONICAL_LENGTH

# --- the one change ----------------------------------------------------------

# The 2026-08-19 direction renames channel 9. The Founder Constitution's
# direct-mint table reads "Initial mini-gamified incentives"; the identifier
# drops the leading word the same way "Liquidity mining" gives `liquidity_mining`.
# ADR 0049 records the pivot this belongs to and ADR 0053 records this version.
RENAMED_CHANNEL_FROM = "initial_mystery_box_incentives"
RENAMED_CHANNEL_TO = "mini_gamified_incentives"


def _renamed(channel_id: str) -> str:
    return RENAMED_CHANNEL_TO if channel_id == RENAMED_CHANNEL_FROM else channel_id


# --- the manifest layer, derived rather than copied --------------------------

STORAGE_TYPE = manifest_v2.STORAGE_TYPE
DECIMAL_PLACES = manifest_v2.DECIMAL_PLACES
ATOMIC_UNITS_PER_DISPLAY_UNIT = manifest_v2.ATOMIC_UNITS_PER_DISPLAY_UNIT
MAXIMUM_SUPPLY_DISPLAY = manifest_v2.MAXIMUM_SUPPLY_DISPLAY
MAXIMUM_SUPPLY_ATOMIC = manifest_v2.MAXIMUM_SUPPLY_ATOMIC

FOUNDER_SEAT_CAPACITY = manifest_v2.FOUNDER_SEAT_CAPACITY
MAXIMUM_SEATS_PER_PERSON = manifest_v2.MAXIMUM_SEATS_PER_PERSON
ISSUANCE_CYCLES_PER_SEAT = manifest_v2.ISSUANCE_CYCLES_PER_SEAT
SEAT_CYCLE_POPULATION = manifest_v2.SEAT_CYCLE_POPULATION

BASE_PERMISSION = manifest_v2.BASE_PERMISSION
DIRECT_MINT = manifest_v2.DIRECT_MINT

# (channel id, issuance kind, cap in atomic units) in fixed manifest order.
# The order and every cap are version two's; only entry 9's identifier moves.
CHANNELS: tuple[tuple[str, str, int], ...] = tuple(
    (_renamed(channel_id), kind, cap)
    for channel_id, kind, cap in manifest_v2.CHANNELS
)

# No base permission leg names the renamed channel, so the legs are version
# two's unchanged. Mapping them through the rename anyway means a later version
# that does move a leg cannot leave this table behind.
BASE_LEGS: tuple[tuple[str, str, int], ...] = tuple(
    (_renamed(channel_id), beneficiary_kind, amount)
    for channel_id, beneficiary_kind, amount in manifest_v2.BASE_LEGS
)
BASE_PERMISSION_TOTAL = manifest_v2.BASE_PERMISSION_TOTAL
FOUNDER_OPERATOR_LEG = manifest_v2.FOUNDER_OPERATOR_LEG
FIXED_LEG_TOTAL = manifest_v2.FIXED_LEG_TOTAL
FOUNDER_CHANNEL = _renamed(manifest_v2.FOUNDER_CHANNEL)

CYCLE_TARGET_SECONDS = manifest_v2.CYCLE_TARGET_SECONDS
ACTIVITY_THRESHOLD_SECONDS = manifest_v2.ACTIVITY_THRESHOLD_SECONDS
GRACE_ALLOWANCE_SECONDS = manifest_v2.GRACE_ALLOWANCE_SECONDS

REFERRAL_CHANNEL = _renamed(manifest_v2.REFERRAL_CHANNEL)
REFERRAL_AMOUNT = manifest_v2.REFERRAL_AMOUNT
REFERRAL_UNCONDITIONAL = manifest_v2.REFERRAL_UNCONDITIONAL
REFERRED_BENEFICIARY_KIND = manifest_v2.REFERRED_BENEFICIARY_KIND
UNREFERRED_BENEFICIARY_KIND = manifest_v2.UNREFERRED_BENEFICIARY_KIND
REFERRAL_OPERATOR_NUMERATOR = manifest_v2.REFERRAL_OPERATOR_NUMERATOR
REFERRAL_OPERATOR_DENOMINATOR = manifest_v2.REFERRAL_OPERATOR_DENOMINATOR

# Direct-channel eligibility is still the one founder-reserved placeholder. The
# rename changes which identifier it covers and not how many channels it covers,
# which the vectors record as a count derived from the renamed table.
RESEARCH_PLACEHOLDERS: tuple[str, ...] = manifest_v2.RESEARCH_PLACEHOLDERS

FOUNDER_CHANNEL_SUBTOTAL = manifest_v2.FOUNDER_CHANNEL_SUBTOTAL
DIRECT_CHANNEL_SUBTOTAL = manifest_v2.DIRECT_CHANNEL_SUBTOTAL

SINGLETON_BENEFICIARY_KINDS = manifest_v2.SINGLETON_BENEFICIARY_KINDS
FOUNDER_SEAT_KIND = manifest_v2.FOUNDER_SEAT_KIND
DIRECT_BENEFICIARY_KIND = manifest_v2.DIRECT_BENEFICIARY_KIND
SINGLETON_BENEFICIARY_ID = manifest_v2.SINGLETON_BENEFICIARY_ID
UNREFERRED_POOL_KIND = manifest_v2.UNREFERRED_POOL_KIND

CHANNEL_IDS: tuple[str, ...] = tuple(entry[0] for entry in CHANNELS)
DIRECT_CHANNEL_IDS: frozenset[str] = frozenset(
    entry[0] for entry in CHANNELS if entry[1] == DIRECT_MINT
)
CHANNEL_CAPS: dict[str, int] = {entry[0]: entry[2] for entry in CHANNELS}
PLACEHOLDER_DIRECT_CHANNELS: frozenset[str] = frozenset(
    entry[0]
    for entry in CHANNELS
    if entry[1] == DIRECT_MINT and entry[0] != REFERRAL_CHANNEL
)
