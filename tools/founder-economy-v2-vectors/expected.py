"""Closed-form expectations derived from the Founder Constitution.

This module is the independence in this verifier. It imports nothing from
`simulation/`: every literal below is converted by hand from the Founder
Constitution's tables, and every expectation is arithmetic over those literals.

The constitution states the economy twice — once as per-eligible-cycle amounts
and once as maximum channel totals — without deriving either from the other.
Recomputing each channel total here as `per_cycle * seats * cycles` and
requiring it to equal the separately stated total checks the two tables against
each other, which reading the manifest alone cannot do.

Display units are converted through exact integer arithmetic. An amount stated
to one decimal place, such as 34.2, is written as `342 * D // 10` so no
floating-point value ever appears.
"""

from __future__ import annotations

DECIMAL_PLACES = 8
D = 100_000_000  # atomic units per display unit

# "The intended permanent maximum supply is exactly 56,993,950,100 native
# units", revised from 55,743,940,100 on 2026-08-07.
MAXIMUM_SUPPLY_DISPLAY = 56_993_950_100
MAXIMUM_SUPPLY_ATOMIC = MAXIMUM_SUPPLY_DISPLAY * D
SUPERSEDED_MAXIMUM_SUPPLY_DISPLAY = 55_743_940_100

# Founder Seats: exactly 100,000 seats, at most 1,000 per human, each seat
# receiving 731 eligible cycles.
FOUNDER_SEAT_CAPACITY = 100_000
MAXIMUM_SEATS_PER_PERSON = 1_000
ISSUANCE_CYCLES_PER_SEAT = 731
SEAT_CYCLE_POPULATION = FOUNDER_SEAT_CAPACITY * ISSUANCE_CYCLES_PER_SEAT

# Founder Node issuance, per eligible cycle, totalling 574.3 native units.
BASE_LEGS_DISPLAY_TENTHS: dict[str, int] = {
    "venture_escrow": 1710,
    "community_grants_escrow": 342,
    "developer_incentives_escrow": 171,
    "system_creator_issuance_royalty": 100,
    "founder_operator": 3420,
}
BASE_PERMISSION_TOTAL_DISPLAY_TENTHS = 5743

# The Founder referral benefit is 34.2 units per cycle, ten per cent of the
# 342-unit operator leg, and is unconditional.
REFERRAL_DISPLAY_TENTHS = 342
REFERRAL_OPERATOR_NUMERATOR = 1
REFERRAL_OPERATOR_DENOMINATOR = 10
SUPERSEDED_REFERRAL_DISPLAY_TENTHS = 171

# Maximum-supply allocation, in display units, exactly as the two tables read.
FOUNDER_NODE_CHANNELS_DISPLAY: dict[str, int] = {
    "founder_operator": 25_000_200_000,
    "venture_escrow": 12_500_100_000,
    "community_grants_escrow": 2_500_020_000,
    "developer_incentives_escrow": 1_250_010_000,
    "system_creator_issuance_royalty": 731_000_000,
}
FOUNDER_NODE_SUBTOTAL_DISPLAY = 41_981_330_000

DIRECT_MINT_CHANNELS_DISPLAY: dict[str, int] = {
    "liquidity_mining": 7_500_060_000,
    "impermanent_loss_protection": 3_750_030_000,
    "founder_referral": 2_500_020_000,
    "hub_verified_user_incentives": 1_250_010_000,
    "initial_mystery_box_incentives": 12_500_100,
}
DIRECT_MINT_SUBTOTAL_DISPLAY = 15_012_620_100
SUPERSEDED_REFERRAL_CHANNEL_DISPLAY = 1_250_010_000

# The superseded v1 allocation, converted by hand from the accepted
# `founder-economy-manifest-v1` cap table. It is carried here only to prove
# that the revised maximum funds the referral channel and nothing else.
SUPERSEDED_CHANNELS_DISPLAY: dict[str, int] = {
    "founder_operator": 25_000_200_000,
    "venture_escrow": 12_500_100_000,
    "community_grants_escrow": 2_500_020_000,
    "developer_incentives_escrow": 1_250_010_000,
    "founder_referral": SUPERSEDED_REFERRAL_CHANNEL_DISPLAY,
    "system_creator_issuance_royalty": 731_000_000,
    "liquidity_mining": 7_500_060_000,
    "impermanent_loss_protection": 3_750_030_000,
    "hub_verified_user_incentives": 1_250_010_000,
    "initial_mystery_box_incentives": 12_500_100,
}

BASE_PERMISSION_KIND = "base_permission"
DIRECT_MINT_KIND = "direct_mint"
REFERRAL_CHANNEL = "founder_referral"

# "A cycle is met when cumulative fully operational uptime within the
# 24-hour-target cycle is 18 hours or more. Equivalently, a cycle fails when
# cumulative downtime exceeds 6 hours." The allowance is 6 hours, cumulative
# and fragmentable, and exactly 6 hours of downtime leaves the cycle met.
SECONDS_PER_HOUR = 3_600
CYCLE_TARGET_HOURS = 24
ACTIVITY_THRESHOLD_HOURS = 18
GRACE_ALLOWANCE_HOURS = 6

CYCLE_TARGET_SECONDS = CYCLE_TARGET_HOURS * SECONDS_PER_HOUR
ACTIVITY_THRESHOLD_SECONDS = ACTIVITY_THRESHOLD_HOURS * SECONDS_PER_HOUR
GRACE_ALLOWANCE_SECONDS = GRACE_ALLOWANCE_HOURS * SECONDS_PER_HOUR

# The referral names two destinations and no third. Every seat-cycle reaches
# exactly one of them, which is what consumes the channel to the unit.
REFERRED_BENEFICIARY_KIND = "recorded_referrer"
UNREFERRED_BENEFICIARY_KIND = "unreferred_performance_pool"

# Direct-channel eligibility is the one remaining founder-reserved placeholder.
# It covers the four direct-mint channels other than the referral, whose
# eligibility is the recorded referrer relationship the ledger already holds.
PLACEHOLDER_DIRECT_CHANNELS: frozenset[str] = frozenset(
    set(DIRECT_MINT_CHANNELS_DISPLAY) - {REFERRAL_CHANNEL}
)


def _tenths_to_atomic(tenths: int) -> int:
    """Convert a display amount stated in tenths of a unit to atomic units."""
    atomic, remainder = divmod(tenths * D, 10)
    if remainder:
        raise ValueError(f"{tenths} tenths is not representable in atomic units")
    return atomic


BASE_LEGS: dict[str, int] = {
    channel: _tenths_to_atomic(tenths)
    for channel, tenths in BASE_LEGS_DISPLAY_TENTHS.items()
}
BASE_PERMISSION_TOTAL = _tenths_to_atomic(BASE_PERMISSION_TOTAL_DISPLAY_TENTHS)
REFERRAL_AMOUNT = _tenths_to_atomic(REFERRAL_DISPLAY_TENTHS)
SUPERSEDED_REFERRAL_AMOUNT = _tenths_to_atomic(SUPERSEDED_REFERRAL_DISPLAY_TENTHS)

# Channel caps in the manifest's fixed order: the five Founder Node
# distribution channels, then the five direct-mint channels.
CHANNEL_ORDER: tuple[str, ...] = (
    *FOUNDER_NODE_CHANNELS_DISPLAY,
    *DIRECT_MINT_CHANNELS_DISPLAY,
)
CHANNEL_KINDS: dict[str, str] = {
    **{channel: BASE_PERMISSION_KIND for channel in FOUNDER_NODE_CHANNELS_DISPLAY},
    **{channel: DIRECT_MINT_KIND for channel in DIRECT_MINT_CHANNELS_DISPLAY},
}
CHANNEL_CAPS: dict[str, int] = {
    channel: display * D
    for channel, display in {
        **FOUNDER_NODE_CHANNELS_DISPLAY,
        **DIRECT_MINT_CHANNELS_DISPLAY,
    }.items()
}

FOUNDER_NODE_SUBTOTAL = FOUNDER_NODE_SUBTOTAL_DISPLAY * D
DIRECT_MINT_SUBTOTAL = DIRECT_MINT_SUBTOTAL_DISPLAY * D


def per_seat_schedule(amount: int) -> int:
    return amount * ISSUANCE_CYCLES_PER_SEAT


def full_schedule(amount: int) -> int:
    return amount * SEAT_CYCLE_POPULATION


def check_constitution_is_self_consistent() -> list[str]:
    """Cross-check the constitution's per-cycle table against its cap table.

    Each Founder Node channel cap must be its per-cycle leg times the complete
    seat-cycle population, and the referral cap must be the per-cycle benefit
    times the same population with no remainder. Neither table is derived from
    the other in the constitution, so agreement is evidence rather than
    restatement.
    """
    failures: list[str] = []
    for channel, leg in BASE_LEGS.items():
        derived = full_schedule(leg)
        if derived != CHANNEL_CAPS[channel]:
            failures.append(
                f"{channel}: per-cycle schedule {derived} is not the stated cap "
                f"{CHANNEL_CAPS[channel]}"
            )
    if sum(BASE_LEGS.values()) != BASE_PERMISSION_TOTAL:
        failures.append("base legs do not sum to the stated 574.3-unit total")
    if full_schedule(BASE_PERMISSION_TOTAL) != FOUNDER_NODE_SUBTOTAL:
        failures.append("base permission schedule is not the Founder Node subtotal")
    if full_schedule(REFERRAL_AMOUNT) != CHANNEL_CAPS[REFERRAL_CHANNEL]:
        failures.append("referral schedule is not the stated referral cap")
    if REFERRAL_AMOUNT * REFERRAL_OPERATOR_DENOMINATOR != (
        BASE_LEGS["founder_operator"] * REFERRAL_OPERATOR_NUMERATOR
    ):
        failures.append("referral benefit is not one tenth of the operator leg")
    if sum(FOUNDER_NODE_CHANNELS_DISPLAY.values()) != FOUNDER_NODE_SUBTOTAL_DISPLAY:
        failures.append("Founder Node caps do not sum to the stated subtotal")
    if sum(DIRECT_MINT_CHANNELS_DISPLAY.values()) != DIRECT_MINT_SUBTOTAL_DISPLAY:
        failures.append("direct-mint caps do not sum to the stated subtotal")
    if (
        FOUNDER_NODE_SUBTOTAL_DISPLAY + DIRECT_MINT_SUBTOTAL_DISPLAY
        != MAXIMUM_SUPPLY_DISPLAY
    ):
        failures.append("the two subtotals do not add to the stated maximum supply")
    if sum(SUPERSEDED_CHANNELS_DISPLAY.values()) != SUPERSEDED_MAXIMUM_SUPPLY_DISPLAY:
        failures.append("the v1 caps do not sum to the superseded maximum supply")
    if set(SUPERSEDED_CHANNELS_DISPLAY) != set(CHANNEL_ORDER):
        failures.append("v1 and v2 do not carry the same channel identifiers")
    # The constitution states the cycle rule twice without deriving either form
    # from the other. They agree only because the threshold and the allowance
    # sum to the target, so requiring that is a check and not a restatement.
    if ACTIVITY_THRESHOLD_SECONDS + GRACE_ALLOWANCE_SECONDS != CYCLE_TARGET_SECONDS:
        failures.append("the uptime threshold and grace allowance do not span a cycle")
    return failures


def met_cycle(uptime_seconds: int) -> bool:
    """Restate the cycle rule from the constitution's own two forms."""
    by_uptime = uptime_seconds >= ACTIVITY_THRESHOLD_SECONDS
    by_downtime = (CYCLE_TARGET_SECONDS - uptime_seconds) <= GRACE_ALLOWANCE_SECONDS
    if by_uptime is not by_downtime:
        raise ValueError(f"the two stated forms disagree at {uptime_seconds} seconds")
    return by_uptime


def equal_split(pot: int, winners: int) -> tuple[int, int]:
    """Split a pot equally, carrying the integer remainder forward."""
    return divmod(pot, winners)
