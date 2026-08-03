"""Fixed Founder Economy contract values from founder-economy-manifest-v1.

Every value here is founder-directed or derived in the accepted manifest
specification. The loader compares a supplied manifest against this table; it
never treats the manifest as a parameter template.
"""

from __future__ import annotations

MANIFEST_SCHEMA = "protocol-stack/founder-economy-manifest/v1"
MANIFEST_LABEL = "protocol-stack:founder-economy:manifest-v1"
MANIFEST_CANONICAL_LENGTH = 2297
MANIFEST_DIGEST = "2a8923d40615589cc9c9ef90598c0cec56b72a7efa103cf8c05aceb5b54dc698"

STORAGE_TYPE = "u64"
DECIMAL_PLACES = 8
ATOMIC_UNITS_PER_DISPLAY_UNIT = 100_000_000
MAXIMUM_SUPPLY_DISPLAY = 55_743_940_100
MAXIMUM_SUPPLY_ATOMIC = 5_574_394_010_000_000_000

FOUNDER_SEAT_CAPACITY = 100_000
MAXIMUM_SEATS_PER_PERSON = 1_000
ISSUANCE_CYCLES_PER_SEAT = 731

BASE_PERMISSION = "base_permission"
REFERRAL_PERMISSION = "referral_permission"
DIRECT_MINT = "direct_mint"

# (channel id, issuance kind, cap in atomic units) in fixed manifest order.
CHANNELS: tuple[tuple[str, str, int], ...] = (
    ("founder_operator", BASE_PERMISSION, 2_500_020_000_000_000_000),
    ("venture_escrow", BASE_PERMISSION, 1_250_010_000_000_000_000),
    ("community_grants_escrow", BASE_PERMISSION, 250_002_000_000_000_000),
    ("developer_incentives_escrow", BASE_PERMISSION, 125_001_000_000_000_000),
    ("founder_referral", REFERRAL_PERMISSION, 125_001_000_000_000_000),
    ("system_creator_issuance_royalty", BASE_PERMISSION, 73_100_000_000_000_000),
    ("liquidity_mining", DIRECT_MINT, 750_006_000_000_000_000),
    ("impermanent_loss_protection", DIRECT_MINT, 375_003_000_000_000_000),
    ("hub_verified_user_incentives", DIRECT_MINT, 125_001_000_000_000_000),
    ("initial_mystery_box_incentives", DIRECT_MINT, 1_250_010_000_000_000),
)

# (channel, beneficiary kind, amount in atomic units) in fixed manifest order.
BASE_LEGS: tuple[tuple[str, str, int], ...] = (
    ("venture_escrow", "venture_escrow", 17_100_000_000),
    ("community_grants_escrow", "community_grants_escrow", 3_420_000_000),
    ("developer_incentives_escrow", "developer_incentives_escrow", 1_710_000_000),
    ("system_creator_issuance_royalty", "system_creator_company", 1_000_000_000),
    ("founder_operator", "cycle_founder_or_performance_result", 34_200_000_000),
)
BASE_PERMISSION_TOTAL = 57_430_000_000
FOUNDER_OPERATOR_LEG = 34_200_000_000

REFERRAL_CHANNEL = "founder_referral"
REFERRAL_BENEFICIARY_KIND = "recorded_referrer"
REFERRAL_AMOUNT = 1_710_000_000

RESEARCH_PLACEHOLDERS: tuple[str, ...] = (
    "activity_eligibility_result",
    "inactive_performance_allocation_result",
    "inactive_referral_eligibility_result",
    "direct_channel_eligibility_result",
)

FOUNDER_CHANNEL_SUBTOTAL = 4_323_134_000_000_000_000
DIRECT_CHANNEL_SUBTOTAL = 1_251_260_010_000_000_000

SINGLETON_BENEFICIARY_KINDS = frozenset(
    {
        "venture_escrow",
        "community_grants_escrow",
        "developer_incentives_escrow",
        "system_creator_company",
    }
)
FOUNDER_SEAT_KIND = "founder_seat"
DIRECT_BENEFICIARY_KIND = "direct_beneficiary"
SINGLETON_BENEFICIARY_ID = "global"

CHANNEL_IDS: tuple[str, ...] = tuple(entry[0] for entry in CHANNELS)
DIRECT_CHANNEL_IDS: frozenset[str] = frozenset(
    entry[0] for entry in CHANNELS if entry[1] == DIRECT_MINT
)
CHANNEL_CAPS: dict[str, int] = {entry[0]: entry[2] for entry in CHANNELS}
