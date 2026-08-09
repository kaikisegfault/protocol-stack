"""Fixed cycle-boundary constants from cycle-boundary-v1.

The three seconds figures are founder-directed in the Founder Constitution and
are already fixed by `founder-economy-simulator-v2`. They are restated here only
to derive their block equivalents, and `assert_exact_derivation` requires this
table to agree with the economy contract rather than hold a second opinion.
"""

from __future__ import annotations

from simulation.common.canonical import MAX_U64, InvariantError

STATE_SCHEMA = "protocol-stack/cycle-boundary-state/v1"
STATE_LABEL = "protocol-stack:cycle-boundary:state-v1"

GENESIS_HEIGHT = 0
MAX_HEIGHT = MAX_U64

# The pinned M1 CometBFT commit interval from consensus-application-v1. It is an
# input to the derivation below and never to a transition; nothing in this model
# reads a clock.
TARGET_COMMIT_SECONDS = 3

CYCLE_TARGET_SECONDS = 86_400
ACTIVITY_THRESHOLD_SECONDS = 64_800
GRACE_ALLOWANCE_SECONDS = 21_600

# A window is exactly this many heights. It is the normative quantity: a later
# change to the commit interval changes how long a window takes in the world,
# not how many blocks it holds or which window a height belongs to.
CYCLE_BLOCKS = CYCLE_TARGET_SECONDS // TARGET_COMMIT_SECONDS
ACTIVITY_THRESHOLD_BLOCKS = ACTIVITY_THRESHOLD_SECONDS // TARGET_COMMIT_SECONDS
GRACE_ALLOWANCE_BLOCKS = GRACE_ALLOWANCE_SECONDS // TARGET_COMMIT_SECONDS

ISSUANCE_CYCLES_PER_SEAT = 731
FOUNDER_SEAT_CAPACITY = 100_000

MAX_SEAT_ID = FOUNDER_SEAT_CAPACITY - 1
MAX_CYCLE_INDEX = ISSUANCE_CYCLES_PER_SEAT - 1

# One u64 activation height per activated seat, and nothing else. Every window
# identifier is derived on demand, so the bound does not grow with how far
# through its span a seat has progressed.
ACTIVATION_HEIGHT_BYTES = 8
SCHEDULE_STORAGE_BYTES = FOUNDER_SEAT_CAPACITY * ACTIVATION_HEIGHT_BYTES

RESULT_CODES: tuple[str, ...] = (
    "ACCEPTED",
    "SEAT_RANGE",
    "HEIGHT_RANGE",
    "REPLAY",
    "HEIGHT_NOT_MONOTONIC",
    "CYCLE_RANGE",
    "SEAT_NOT_ACTIVATED",
    "WINDOW_BEFORE_ISSUANCE",
    "WINDOW_AFTER_ISSUANCE",
    "WINDOW_NOT_FOR_CYCLE",
)


def assert_exact_derivation() -> None:
    """Require every derived block count to be exact and self-consistent.

    The whole grid rests on 3 seconds dividing all three founder-directed
    figures exactly. A remainder anywhere would put the 18-hour threshold
    between two blocks, where the rule could only be applied by rounding a
    founder-directed value. That is a defect rather than an input, so it raises.
    """
    for name, seconds, blocks in (
        ("cycle target", CYCLE_TARGET_SECONDS, CYCLE_BLOCKS),
        ("activity threshold", ACTIVITY_THRESHOLD_SECONDS, ACTIVITY_THRESHOLD_BLOCKS),
        ("grace allowance", GRACE_ALLOWANCE_SECONDS, GRACE_ALLOWANCE_BLOCKS),
    ):
        if seconds % TARGET_COMMIT_SECONDS != 0:
            raise InvariantError(
                f"{name} of {seconds}s is not a whole number of "
                f"{TARGET_COMMIT_SECONDS}s blocks"
            )
        if blocks * TARGET_COMMIT_SECONDS != seconds:
            raise InvariantError(f"{name} block count does not convert back to {seconds}s")

    if ACTIVITY_THRESHOLD_BLOCKS + GRACE_ALLOWANCE_BLOCKS != CYCLE_BLOCKS:
        raise InvariantError("the threshold and allowance do not sum to a window")
    if ACTIVITY_THRESHOLD_SECONDS + GRACE_ALLOWANCE_SECONDS != CYCLE_TARGET_SECONDS:
        raise InvariantError("the threshold and allowance do not sum to the target")


def assert_agrees_with_economy() -> None:
    """Require the shared founder figures to match the accepted economy contract.

    Two tables holding the same founder-directed constant can drift. The economy
    contract is the accepted one, so this table defers to it rather than the
    reverse.
    """
    from simulation.founder_economy_v2 import contract as economy

    for name, here, there in (
        ("CYCLE_TARGET_SECONDS", CYCLE_TARGET_SECONDS, economy.CYCLE_TARGET_SECONDS),
        (
            "ACTIVITY_THRESHOLD_SECONDS",
            ACTIVITY_THRESHOLD_SECONDS,
            economy.ACTIVITY_THRESHOLD_SECONDS,
        ),
        (
            "GRACE_ALLOWANCE_SECONDS",
            GRACE_ALLOWANCE_SECONDS,
            economy.GRACE_ALLOWANCE_SECONDS,
        ),
        (
            "ISSUANCE_CYCLES_PER_SEAT",
            ISSUANCE_CYCLES_PER_SEAT,
            economy.ISSUANCE_CYCLES_PER_SEAT,
        ),
        (
            "FOUNDER_SEAT_CAPACITY",
            FOUNDER_SEAT_CAPACITY,
            economy.FOUNDER_SEAT_CAPACITY,
        ),
    ):
        if here != there:
            raise InvariantError(
                f"{name} is {here} here and {there} in founder-economy-manifest-v2"
            )
