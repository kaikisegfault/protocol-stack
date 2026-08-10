"""Fixed Founder Economy contract values for founder-economy-simulator-v3.

Version three realizes the same accepted economic contract as version two. No
channel, cap, base leg, denomination, subtotal, beneficiary kind, seat capacity,
per-person bound, or issuance-cycle count moves, so `founder-economy-manifest-v2`
is the artifact this version loads and every manifest-level value is read from
the accepted v2 contract rather than restated. A third table of founder-directed
figures could drift from the two that already agree.

The window grid is read from the accepted `cycle-boundary-v1` contract for the
same reason. What version three adds is the enforcement, not the numbers.
"""

from __future__ import annotations

from simulation.common.canonical import MAX_JSON_INTEGER, InvariantError
from simulation.cycle_boundary import contract as boundary
from simulation.cycle_boundary.grid import MAX_WINDOW
from simulation.founder_economy_v2 import contract as economy_v2

# --- version three's own identity -------------------------------------------

MANIFEST_SCHEMA = economy_v2.MANIFEST_SCHEMA
MANIFEST_LABEL = economy_v2.MANIFEST_LABEL
MANIFEST_CANONICAL_LENGTH = economy_v2.MANIFEST_CANONICAL_LENGTH
MANIFEST_DIGEST = economy_v2.MANIFEST_DIGEST

# --- the manifest layer, bound rather than copied ----------------------------

STORAGE_TYPE = economy_v2.STORAGE_TYPE
DECIMAL_PLACES = economy_v2.DECIMAL_PLACES
ATOMIC_UNITS_PER_DISPLAY_UNIT = economy_v2.ATOMIC_UNITS_PER_DISPLAY_UNIT
MAXIMUM_SUPPLY_DISPLAY = economy_v2.MAXIMUM_SUPPLY_DISPLAY
MAXIMUM_SUPPLY_ATOMIC = economy_v2.MAXIMUM_SUPPLY_ATOMIC

FOUNDER_SEAT_CAPACITY = economy_v2.FOUNDER_SEAT_CAPACITY
MAXIMUM_SEATS_PER_PERSON = economy_v2.MAXIMUM_SEATS_PER_PERSON
ISSUANCE_CYCLES_PER_SEAT = economy_v2.ISSUANCE_CYCLES_PER_SEAT
SEAT_CYCLE_POPULATION = economy_v2.SEAT_CYCLE_POPULATION

BASE_PERMISSION = economy_v2.BASE_PERMISSION
DIRECT_MINT = economy_v2.DIRECT_MINT
CHANNELS = economy_v2.CHANNELS
CHANNEL_IDS = economy_v2.CHANNEL_IDS
CHANNEL_CAPS = economy_v2.CHANNEL_CAPS
DIRECT_CHANNEL_IDS = economy_v2.DIRECT_CHANNEL_IDS
FOUNDER_CHANNEL_SUBTOTAL = economy_v2.FOUNDER_CHANNEL_SUBTOTAL
DIRECT_CHANNEL_SUBTOTAL = economy_v2.DIRECT_CHANNEL_SUBTOTAL

BASE_LEGS = economy_v2.BASE_LEGS
BASE_PERMISSION_TOTAL = economy_v2.BASE_PERMISSION_TOTAL
FOUNDER_OPERATOR_LEG = economy_v2.FOUNDER_OPERATOR_LEG
FIXED_LEG_TOTAL = economy_v2.FIXED_LEG_TOTAL
FOUNDER_CHANNEL = economy_v2.FOUNDER_CHANNEL

CYCLE_TARGET_SECONDS = economy_v2.CYCLE_TARGET_SECONDS
ACTIVITY_THRESHOLD_SECONDS = economy_v2.ACTIVITY_THRESHOLD_SECONDS
GRACE_ALLOWANCE_SECONDS = economy_v2.GRACE_ALLOWANCE_SECONDS

REFERRAL_CHANNEL = economy_v2.REFERRAL_CHANNEL
REFERRAL_AMOUNT = economy_v2.REFERRAL_AMOUNT
REFERRAL_UNCONDITIONAL = economy_v2.REFERRAL_UNCONDITIONAL
REFERRED_BENEFICIARY_KIND = economy_v2.REFERRED_BENEFICIARY_KIND
UNREFERRED_BENEFICIARY_KIND = economy_v2.UNREFERRED_BENEFICIARY_KIND

RESEARCH_PLACEHOLDERS = economy_v2.RESEARCH_PLACEHOLDERS
PLACEHOLDER_DIRECT_CHANNELS = economy_v2.PLACEHOLDER_DIRECT_CHANNELS

SINGLETON_BENEFICIARY_KINDS = economy_v2.SINGLETON_BENEFICIARY_KINDS
FOUNDER_SEAT_KIND = economy_v2.FOUNDER_SEAT_KIND
DIRECT_BENEFICIARY_KIND = economy_v2.DIRECT_BENEFICIARY_KIND
SINGLETON_BENEFICIARY_ID = economy_v2.SINGLETON_BENEFICIARY_ID
UNREFERRED_POOL_KIND = economy_v2.UNREFERRED_POOL_KIND

# --- the window grid, bound rather than copied -------------------------------

MAX_HEIGHT = boundary.MAX_HEIGHT
CYCLE_BLOCKS = boundary.CYCLE_BLOCKS
TARGET_COMMIT_SECONDS = boundary.TARGET_COMMIT_SECONDS
MAX_SEAT_ID = boundary.MAX_SEAT_ID
MAX_CYCLE_INDEX = boundary.MAX_CYCLE_INDEX

# One u64 activation height per activated seat. Every window identifier is
# derived on demand, so the bound does not grow with a seat's progress.
ACTIVATION_HEIGHT_BYTES = boundary.ACTIVATION_HEIGHT_BYTES
SCHEDULE_STORAGE_BYTES = boundary.SCHEDULE_STORAGE_BYTES

# Version two's codes, plus the seven this version adds.
#
# Coverage is recorded as a derived claim rather than asserted, so a later
# change cannot quietly lose a code or declare one no path reaches. The declared
# set is partitioned honestly: most codes are produced by executing an event
# array, and two are guards against defects that no event array can reach at
# any representable scale. Those two are proved present by direct exercise
# instead of being deleted, because the arithmetic they check is real.
RESULT_CODES: tuple[str, ...] = (
    "OK",
    "CYCLE_RANGE",
    "INVALID_REFERRER",
    "REPLAY",
    "SEAT_NOT_ACTIVATED",
    "MISSING_UPTIME_RECORD",
    "INVALID_UPTIME_RECORD",
    "INCONSISTENT_UPTIME_RECORD",
    "PERMISSION_NOT_FOUND",
    "INVALID_CHANNEL",
    "ZERO_AMOUNT",
    "MISSING_RESEARCH_INPUT",
    "INVALID_RESEARCH_INPUT",
    "NOT_ELIGIBLE",
    "CHANNEL_CAP",
    "ARITHMETIC_OVERFLOW",
    "INVARIANT",
    # Added by version three.
    "HEIGHT_RANGE",
    "HEIGHT_NOT_MONOTONIC",
    "WINDOW_BEFORE_ISSUANCE",
    "WINDOW_AFTER_ISSUANCE",
    "WINDOW_NOT_FOR_CYCLE",
    "SEAT_NOT_IN_SCOPE",
    "INCOMPLETE_UPTIME_RECORD",
)

ADDED_RESULT_CODES: tuple[str, ...] = (
    "HEIGHT_RANGE",
    "HEIGHT_NOT_MONOTONIC",
    "WINDOW_BEFORE_ISSUANCE",
    "WINDOW_AFTER_ISSUANCE",
    "WINDOW_NOT_FOR_CYCLE",
    "SEAT_NOT_IN_SCOPE",
    "INCOMPLETE_UPTIME_RECORD",
)

# Reachable only by a defect, not by an input. Every accumulated quantity is
# bounded far below u64 by a channel cap, so an overflow inside a transition
# means the arithmetic itself is wrong, and an invariant failure means a
# transition wrote a state its own rules forbid. Both are exercised directly
# rather than through a scenario, in the same way version two exercises its two
# unreachable guards.
GUARD_RESULT_CODES: tuple[str, ...] = ("ARITHMETIC_OVERFLOW", "INVARIANT")

EVENT_REACHABLE_RESULT_CODES: tuple[str, ...] = tuple(
    code for code in RESULT_CODES if code not in GUARD_RESULT_CODES
)


def assert_agrees_with_bindings() -> None:
    """Require the bound contracts to still agree on every shared figure.

    Version three owns no founder-directed number. It reads the manifest layer
    from the accepted v2 contract and the grid from the accepted cycle-boundary
    contract, and both of those already defer to one another for the three
    seconds figures. This restates nothing; it proves the deferral still holds
    so that a future edit to either table fails here rather than silently
    changing what a window means.
    """
    for name, here, there in (
        ("CYCLE_TARGET_SECONDS", CYCLE_TARGET_SECONDS, boundary.CYCLE_TARGET_SECONDS),
        (
            "ACTIVITY_THRESHOLD_SECONDS",
            ACTIVITY_THRESHOLD_SECONDS,
            boundary.ACTIVITY_THRESHOLD_SECONDS,
        ),
        (
            "GRACE_ALLOWANCE_SECONDS",
            GRACE_ALLOWANCE_SECONDS,
            boundary.GRACE_ALLOWANCE_SECONDS,
        ),
        (
            "ISSUANCE_CYCLES_PER_SEAT",
            ISSUANCE_CYCLES_PER_SEAT,
            boundary.ISSUANCE_CYCLES_PER_SEAT,
        ),
        ("FOUNDER_SEAT_CAPACITY", FOUNDER_SEAT_CAPACITY, boundary.FOUNDER_SEAT_CAPACITY),
    ):
        if here != there:
            raise InvariantError(f"{name} is {here} here and {there} in cycle-boundary-v1")
    boundary.assert_exact_derivation()
    boundary.assert_agrees_with_economy()
    assert_window_rendering_is_safe()


def assert_window_rendering_is_safe() -> None:
    """Require every representable window to be an exact JSON integer.

    A height is a u64 and is rendered as a canonical decimal string, because it
    can exceed the largest integer a conforming JSON stack represents exactly. A
    window is not: it is a height divided by 28,800, so the largest one
    reachable from a representable height is far below that bound. That is what
    keeps `cycle_window` a JSON number and therefore keeps the uptime record's
    shape identical to the one `uptime-measurement-v1` emits, so this is derived
    rather than assumed.
    """
    if MAX_WINDOW * CYCLE_BLOCKS > MAX_HEIGHT:
        raise InvariantError("the maximum window's first height is not representable")
    if MAX_WINDOW > MAX_JSON_INTEGER:
        raise InvariantError(
            f"window {MAX_WINDOW} exceeds the exact JSON integer bound {MAX_JSON_INTEGER}"
        )
