"""Closed-form expectations derived from the Founder Constitution.

This module is the independence in this verifier. It imports nothing from
`simulation/`: every literal below is converted by hand from the Founder
Constitution's tables, and every expectation is arithmetic over those literals
and the scenario parameters that `economy-scenario-suite-v1` states.

A second walk of four models would re-implement thousands of transitions to
learn totals that multiplication already fixes. Deriving them here checks the
run against the constitution instead of against a second reading of the same
specification.
"""

from __future__ import annotations

VERSION = "v1"

DECIMAL_PLACES = 8
ATOMIC_UNITS_PER_DISPLAY_UNIT = 100_000_000

# Maximum-supply allocation, converted from the Founder Constitution.
MAXIMUM_SUPPLY_DISPLAY = 55_743_940_100
MAXIMUM_SUPPLY_ATOMIC = MAXIMUM_SUPPLY_DISPLAY * ATOMIC_UNITS_PER_DISPLAY_UNIT

# Founder Node issuance, per eligible cycle. Display units above, atomic below.
VENTURE_ESCROW_LEG = 171 * ATOMIC_UNITS_PER_DISPLAY_UNIT
COMMUNITY_GRANTS_LEG = 342 * ATOMIC_UNITS_PER_DISPLAY_UNIT // 10
DEVELOPER_INCENTIVES_LEG = 171 * ATOMIC_UNITS_PER_DISPLAY_UNIT // 10
SYSTEM_CREATOR_LEG = 10 * ATOMIC_UNITS_PER_DISPLAY_UNIT
FOUNDER_OPERATOR_LEG = 342 * ATOMIC_UNITS_PER_DISPLAY_UNIT
BASE_PERMISSION_TOTAL = 5743 * ATOMIC_UNITS_PER_DISPLAY_UNIT // 10
REFERRAL_LEG = 171 * ATOMIC_UNITS_PER_DISPLAY_UNIT // 10

ISSUANCE_CYCLES_PER_SEAT = 731
FOUNDER_SEAT_CAPACITY = 100_000
MAXIMUM_SEATS_PER_PERSON = 1_000

# Seat price schedule, in USD cents.
BLOCK_SIZE = 100
BLOCK_COUNT = FOUNDER_SEAT_CAPACITY // BLOCK_SIZE
FIRST_BLOCK_PRICE_CENTS = 100 * 100
FIRST_STEP_CENTS = 10 * 100
TIER_BOUNDARY_PRICE_CENTS = 1_000 * 100
SECOND_STEP_CENTS = 100 * 100

# Commercial routing shares.
SHARE_DENOMINATOR = 100
FOUNDER_SHARE = 45
CREATOR_SHARE = 45
SYSTEM_CREATOR_SHARE = 10
CREATOR_SPLIT_PARTS = 2

# `economy-scenario-suite-v1` scenario 1 parameters, restated here so the
# expectations are computed from the specification rather than from the
# generator that produced the run.
POPULATION_SEATS = 3
POPULATION_REFERRED_SEATS = 2
INACTIVE_PERIOD = 73
INACTIVE_PHASE = 7

PROBES = (
    ("cycle_beyond_window", "probe-cycle-beyond-window"),
    ("base_replay", "probe-base-replay"),
    ("exercise_replay", "probe-exercise-replay"),
    ("activation_replay", "probe-activation-replay"),
    ("unreferred_referral", "probe-unreferred-referral"),
)

ACTIVATED_SEATS = POPULATION_SEATS

# Scenario 3 parameters.
ROUTING_CYCLES = 122
ACTIVE_PERIOD = 5
ACTIVE_STEP = 7
SEAT_STEP = 13
SEAT_MODULUS = 97
PAYMENT_BASE = 1_000_000_007
PAYMENT_STEP = 999_983
FEE_BASE = 500_003
FEE_STEP = 97

# Scenario 4 parameters.
PAYOUTS_PER_ESCROW = 7


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


def referral_permissions_created() -> int:
    """Every cycle of a referred seat, less the withheld inactive decisions.

    The supplied inactive-cycle decision creates the permission when the cycle
    index is even, so an inactive odd cycle creates none.
    """
    total = 0
    for seat_id in range(1, POPULATION_SEATS):
        withheld = sum(
            1
            for cycle in range(ISSUANCE_CYCLES_PER_SEAT)
            if is_inactive(seat_id, cycle) and cycle % 2 == 1
        )
        total += ISSUANCE_CYCLES_PER_SEAT - withheld
    return total


def economy_channel_totals() -> dict[str, int]:
    """Each channel's issued total over the complete population run.

    The Founder operator total is independent of inactivity: a reallocation
    changes the beneficiary of the 342-unit leg, never its amount.
    """
    per_seat = POPULATION_SEATS * ISSUANCE_CYCLES_PER_SEAT
    return {
        "founder_operator": per_seat * FOUNDER_OPERATOR_LEG,
        "venture_escrow": per_seat * VENTURE_ESCROW_LEG,
        "community_grants_escrow": per_seat * COMMUNITY_GRANTS_LEG,
        "developer_incentives_escrow": per_seat * DEVELOPER_INCENTIVES_LEG,
        "system_creator_issuance_royalty": per_seat * SYSTEM_CREATOR_LEG,
        "founder_referral": referral_permissions_created() * REFERRAL_LEG,
    }


def economy_seat_custody() -> dict[int, int]:
    """Each seat's custody: its own active legs, plus what it was allocated.

    Seat `k` receives the whole 342-unit leg of every inactive cycle of the
    seat that names it, which is seat `k - 1` modulo the population. Seat 0 is
    additionally the recorded referrer of both other seats.
    """
    custody: dict[int, int] = {}
    for seat_id in range(POPULATION_SEATS):
        active = ISSUANCE_CYCLES_PER_SEAT - inactive_cycle_count(seat_id)
        source = (seat_id - 1) % POPULATION_SEATS
        received = inactive_cycle_count(source)
        custody[seat_id] = (active + received) * FOUNDER_OPERATOR_LEG
    custody[0] += referral_permissions_created() * REFERRAL_LEG
    return custody


def evaluated_permission_keys() -> int:
    base = POPULATION_SEATS * ISSUANCE_CYCLES_PER_SEAT
    referral = POPULATION_REFERRED_SEATS * ISSUANCE_CYCLES_PER_SEAT
    return base + referral


def block_price_cents(block_index: int) -> int:
    """Walk the constitutional price schedule one block at a time."""
    price = FIRST_BLOCK_PRICE_CENTS
    for _ in range(block_index):
        step = (
            FIRST_STEP_CENTS
            if price < TIER_BOUNDARY_PRICE_CENTS
            else SECOND_STEP_CENTS
        )
        price += step
    return price


def full_sale_proceeds_cents() -> int:
    return sum(
        BLOCK_SIZE * block_price_cents(block) for block in range(BLOCK_COUNT)
    )


def minimum_principals() -> int:
    return FOUNDER_SEAT_CAPACITY // MAXIMUM_SEATS_PER_PERSON


def active_seat_count(cycle_index: int) -> int:
    size = (cycle_index * ACTIVE_STEP) % ACTIVE_PERIOD
    return len(
        {(cycle_index * SEAT_STEP + offset) % SEAT_MODULUS for offset in range(size)}
    )


def empty_cycle_count() -> int:
    return sum(
        1 for cycle in range(ROUTING_CYCLES) if active_seat_count(cycle) == 0
    )


def routing_totals() -> dict[str, int]:
    payments = sum(
        PAYMENT_BASE + cycle * PAYMENT_STEP for cycle in range(ROUTING_CYCLES)
    )
    fees = sum(FEE_BASE + cycle * FEE_STEP for cycle in range(ROUTING_CYCLES))
    return {"commercial": payments, "fee": fees}


def system_creator_total() -> int:
    """Ten percent of each payment, floored per payment and then summed."""
    return sum(
        (PAYMENT_BASE + cycle * PAYMENT_STEP) * SYSTEM_CREATOR_SHARE
        // SHARE_DENOMINATOR
        for cycle in range(ROUTING_CYCLES)
    )


def payout_amounts(custody: int) -> list[int]:
    """Seven payouts that drain one escrow exactly."""
    if custody == 0:
        return []
    maximum = -(-custody // PAYOUTS_PER_ESCROW)
    amounts = []
    remaining = custody
    while remaining > 0:
        amounts.append(min(maximum, remaining))
        remaining -= amounts[-1]
    return amounts
