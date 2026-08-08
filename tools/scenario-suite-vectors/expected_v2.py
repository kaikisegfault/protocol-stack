"""Closed-form expectations for suite version two.

This module is the independence in the version-two verifier. Like `expected.py`
it imports nothing from `simulation/`: every economy literal below is converted
by hand from the Founder Constitution as revised on 2026-08-07, and every
expectation is arithmetic over those literals and the scenario parameters that
`economy-scenario-suite-v2` states.

The seat price schedule and the routing shares are re-used from `expected.py`
rather than restated. Neither depends on the economy contract — the seat model
and the routing model carry no supply or channel figure at all — so copying them
would create two statements of one constitutional rule with nothing to keep
them equal.
"""

from __future__ import annotations

from expected import (  # noqa: F401  (re-exported as the shared constitution)
    ACTIVE_PERIOD,
    ACTIVE_STEP,
    ATOMIC_UNITS_PER_DISPLAY_UNIT,
    BLOCK_COUNT,
    BLOCK_SIZE,
    CREATOR_SHARE,
    CREATOR_SPLIT_PARTS,
    DECIMAL_PLACES,
    FEE_BASE,
    FEE_STEP,
    FIRST_BLOCK_PRICE_CENTS,
    FIRST_STEP_CENTS,
    FOUNDER_SEAT_CAPACITY,
    FOUNDER_SHARE,
    ISSUANCE_CYCLES_PER_SEAT,
    MAXIMUM_SEATS_PER_PERSON,
    PAYMENT_BASE,
    PAYMENT_STEP,
    PAYOUTS_PER_ESCROW,
    ROUTING_CYCLES,
    SEAT_MODULUS,
    SEAT_STEP,
    SECOND_STEP_CENTS,
    SHARE_DENOMINATOR,
    SYSTEM_CREATOR_SHARE,
    TIER_BOUNDARY_PRICE_CENTS,
    active_seat_count,
    block_price_cents,
    empty_cycle_count,
    full_sale_proceeds_cents,
    minimum_principals,
    payout_amounts,
    routing_totals,
    system_creator_total,
)

VERSION = "v2"

# Maximum-supply allocation, converted from the Founder Constitution as revised
# by ADR 0023. The rise from 55,743,940,100 is accounted to the referral channel
# alone, which `founder-economy-manifest-v2.txt` proves separately.
MAXIMUM_SUPPLY_DISPLAY = 56_993_950_100
MAXIMUM_SUPPLY_ATOMIC = MAXIMUM_SUPPLY_DISPLAY * ATOMIC_UNITS_PER_DISPLAY_UNIT

# Founder Node issuance, per eligible cycle. Unrevised except the referral.
VENTURE_ESCROW_LEG = 171 * ATOMIC_UNITS_PER_DISPLAY_UNIT
COMMUNITY_GRANTS_LEG = 342 * ATOMIC_UNITS_PER_DISPLAY_UNIT // 10
DEVELOPER_INCENTIVES_LEG = 171 * ATOMIC_UNITS_PER_DISPLAY_UNIT // 10
SYSTEM_CREATOR_LEG = 10 * ATOMIC_UNITS_PER_DISPLAY_UNIT
FOUNDER_OPERATOR_LEG = 342 * ATOMIC_UNITS_PER_DISPLAY_UNIT
BASE_PERMISSION_TOTAL = 5743 * ATOMIC_UNITS_PER_DISPLAY_UNIT // 10
# Doubled from 17.1 display units and moved to the direct-mint channels.
REFERRAL_LEG = 342 * ATOMIC_UNITS_PER_DISPLAY_UNIT // 10

# `economy-scenario-suite-v2` scenario 1 parameters, restated here so the
# expectations are computed from the specification rather than from the
# generator that produced the run.
POPULATION_SEATS = 3
POPULATION_REFERRED_SEATS = 2
POPULATION_UNREFERRED_SEATS = POPULATION_SEATS - POPULATION_REFERRED_SEATS
INACTIVE_PERIOD = 73
INACTIVE_PHASE = 7
# Activated so a probe has an unevaluated key; it issues nothing.
PROBE_SEATS = 1
ACTIVATED_SEATS = POPULATION_SEATS + PROBE_SEATS

PROBES = (
    ("cycle_beyond_window", "probe-cycle-beyond-window"),
    ("base_replay", "probe-base-replay"),
    ("exercise_replay", "probe-exercise-replay"),
    ("activation_replay", "probe-activation-replay"),
    ("missing_uptime_record", "probe-missing-uptime-record"),
    ("invalid_uptime_record", "probe-invalid-uptime-record"),
    ("inconsistent_uptime_record", "probe-inconsistent-uptime-record"),
    ("accrual_replay", "probe-accrual-replay"),
    ("direct_referral", "probe-direct-referral"),
)


def base_permission_total() -> int:
    """The five base legs must sum to the 574.3-unit base permission."""
    return (
        VENTURE_ESCROW_LEG
        + COMMUNITY_GRANTS_LEG
        + DEVELOPER_INCENTIVES_LEG
        + SYSTEM_CREATOR_LEG
        + FOUNDER_OPERATOR_LEG
    )


def is_inactive(seat_id: int, cycle_index: int) -> bool:
    return (cycle_index + INACTIVE_PHASE * seat_id) % INACTIVE_PERIOD == 0


def inactive_cycle_count(seat_id: int) -> int:
    return sum(
        1
        for cycle in range(ISSUANCE_CYCLES_PER_SEAT)
        if is_inactive(seat_id, cycle)
    )


def referral_accruals_created() -> int:
    """One accrual per seat-cycle, unconditionally.

    Version one withheld a referral on some inactive cycles and created none at
    all for an unreferred seat. Version two does neither: the accrual does not
    depend on activity, and an unreferred seat's accrual reaches the unreferred
    performance pool instead of being rejected. The count is therefore the whole
    population's cycles, which is what consumes the channel exactly.
    """
    return POPULATION_SEATS * ISSUANCE_CYCLES_PER_SEAT


def unreferred_pool_custody() -> int:
    """The unreferred seats' accruals, which no referrer receives."""
    return POPULATION_UNREFERRED_SEATS * ISSUANCE_CYCLES_PER_SEAT * REFERRAL_LEG


def economy_channel_totals() -> dict[str, int]:
    """Each channel's issued total over the complete population run.

    The Founder operator total is independent of inactivity: a reallocation
    changes the beneficiary of the 342-unit leg, never its amount. The scenario
    gives every reallocating window exactly one winner, so the equal split has
    no remainder and the performance carry ends at zero.
    """
    per_seat = POPULATION_SEATS * ISSUANCE_CYCLES_PER_SEAT
    return {
        "founder_operator": per_seat * FOUNDER_OPERATOR_LEG,
        "venture_escrow": per_seat * VENTURE_ESCROW_LEG,
        "community_grants_escrow": per_seat * COMMUNITY_GRANTS_LEG,
        "developer_incentives_escrow": per_seat * DEVELOPER_INCENTIVES_LEG,
        "system_creator_issuance_royalty": per_seat * SYSTEM_CREATOR_LEG,
        "founder_referral": referral_accruals_created() * REFERRAL_LEG,
    }


def economy_seat_custody() -> dict[int, int]:
    """Each seat's custody: its own met cycles, plus what it was allocated.

    Seat `k` receives the whole 342-unit leg of every failed cycle of the seat
    that names it, which is seat `k - 1` modulo the population, because the
    generator gives the intended winner the only maximal uptime in that window.
    Seat 0 is additionally the recorded referrer of both other seats.
    """
    custody: dict[int, int] = {}
    for seat_id in range(POPULATION_SEATS):
        met = ISSUANCE_CYCLES_PER_SEAT - inactive_cycle_count(seat_id)
        source = (seat_id - 1) % POPULATION_SEATS
        received = inactive_cycle_count(source)
        custody[seat_id] = (met + received) * FOUNDER_OPERATOR_LEG
    custody[0] += POPULATION_REFERRED_SEATS * ISSUANCE_CYCLES_PER_SEAT * REFERRAL_LEG
    return custody


def evaluated_permission_keys() -> int:
    """Base evaluations only; version two's referral is not a permission."""
    return POPULATION_SEATS * ISSUANCE_CYCLES_PER_SEAT
