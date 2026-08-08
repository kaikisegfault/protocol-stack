"""Fixed Founder Economy contract values from founder-economy-manifest-v2.

Every value here is founder-directed in the Founder Constitution or derived in
the accepted manifest specification. The loader compares a supplied manifest
against this table; it never treats the manifest as a parameter template.

The v1 table in `simulation/founder_economy/contract.py` is retained unchanged.
It states the superseded contract that the accepted M2 evidence proves.
"""

from __future__ import annotations

MANIFEST_SCHEMA = "protocol-stack/founder-economy-manifest/v2"
MANIFEST_LABEL = "protocol-stack:founder-economy:manifest-v2"
MANIFEST_CANONICAL_LENGTH = 2267
MANIFEST_DIGEST = "84cca09865b6c62bf09d3f6bc3821a2527c7a4835652cffdc0ebefa34b314ce5"

SUPERSEDED_SCHEMA = "protocol-stack/founder-economy-manifest/v1"
SUPERSEDED_DIGEST = "2a8923d40615589cc9c9ef90598c0cec56b72a7efa103cf8c05aceb5b54dc698"
SUPERSEDED_MAXIMUM_SUPPLY_DISPLAY = 55_743_940_100
SUPERSEDED_REFERRAL_AMOUNT = 1_710_000_000

STORAGE_TYPE = "u64"
DECIMAL_PLACES = 8
ATOMIC_UNITS_PER_DISPLAY_UNIT = 100_000_000
MAXIMUM_SUPPLY_DISPLAY = 56_993_950_100
MAXIMUM_SUPPLY_ATOMIC = 5_699_395_010_000_000_000

FOUNDER_SEAT_CAPACITY = 100_000
MAXIMUM_SEATS_PER_PERSON = 1_000
ISSUANCE_CYCLES_PER_SEAT = 731

BASE_PERMISSION = "base_permission"
DIRECT_MINT = "direct_mint"

# (channel id, issuance kind, cap in atomic units) in fixed manifest order.
# The order follows the Founder Constitution's two allocation tables: the five
# Founder Node distribution channels, then the five direct-mint channels.
CHANNELS: tuple[tuple[str, str, int], ...] = (
    ("founder_operator", BASE_PERMISSION, 2_500_020_000_000_000_000),
    ("venture_escrow", BASE_PERMISSION, 1_250_010_000_000_000_000),
    ("community_grants_escrow", BASE_PERMISSION, 250_002_000_000_000_000),
    ("developer_incentives_escrow", BASE_PERMISSION, 125_001_000_000_000_000),
    ("system_creator_issuance_royalty", BASE_PERMISSION, 73_100_000_000_000_000),
    ("liquidity_mining", DIRECT_MINT, 750_006_000_000_000_000),
    ("impermanent_loss_protection", DIRECT_MINT, 375_003_000_000_000_000),
    ("founder_referral", DIRECT_MINT, 250_002_000_000_000_000),
    ("hub_verified_user_incentives", DIRECT_MINT, 125_001_000_000_000_000),
    ("initial_mystery_box_incentives", DIRECT_MINT, 1_250_010_000_000_000),
)

# (channel, beneficiary kind, amount in atomic units) in fixed manifest order.
BASE_LEGS: tuple[tuple[str, str, int], ...] = (
    ("venture_escrow", "venture_escrow", 17_100_000_000),
    ("community_grants_escrow", "community_grants_escrow", 3_420_000_000),
    ("developer_incentives_escrow", "developer_incentives_escrow", 1_710_000_000),
    ("system_creator_issuance_royalty", "system_creator_company", 1_000_000_000),
    ("founder_operator", "cycle_founder_or_performance_winners", 34_200_000_000),
)
BASE_PERMISSION_TOTAL = 57_430_000_000
FOUNDER_OPERATOR_LEG = 34_200_000_000

REFERRAL_CHANNEL = "founder_referral"
REFERRAL_AMOUNT = 3_420_000_000
REFERRAL_UNCONDITIONAL = True
REFERRED_BENEFICIARY_KIND = "recorded_referrer"
UNREFERRED_BENEFICIARY_KIND = "unreferred_performance_pool"

# The referral benefit is one tenth of the Founder Node operator leg.
REFERRAL_OPERATOR_NUMERATOR = 1
REFERRAL_OPERATOR_DENOMINATOR = 10

# Activity, performance ranking, and the winner set are derived rules under
# ADR 0023 rather than supplied fixtures, so only direct-channel eligibility
# remains a research placeholder. The referral channel is excluded from it:
# its eligibility is the recorded referrer relationship the ledger holds.
RESEARCH_PLACEHOLDERS: tuple[str, ...] = ("direct_channel_eligibility_result",)
PLACEHOLDER_DIRECT_CHANNELS: frozenset[str] = frozenset(
    entry[0]
    for entry in CHANNELS
    if entry[1] == DIRECT_MINT and entry[0] != REFERRAL_CHANNEL
)

FOUNDER_CHANNEL_SUBTOTAL = 4_198_133_000_000_000_000
DIRECT_CHANNEL_SUBTOTAL = 1_501_262_010_000_000_000

SEAT_CYCLE_POPULATION = FOUNDER_SEAT_CAPACITY * ISSUANCE_CYCLES_PER_SEAT

CHANNEL_IDS: tuple[str, ...] = tuple(entry[0] for entry in CHANNELS)
DIRECT_CHANNEL_IDS: frozenset[str] = frozenset(
    entry[0] for entry in CHANNELS if entry[1] == DIRECT_MINT
)
CHANNEL_CAPS: dict[str, int] = {entry[0]: entry[2] for entry in CHANNELS}
