"""Fixed uptime-measurement constants from uptime-measurement-v1.

The window, the founder-directed threshold, and the allowance are read from the
cycle-boundary contract, which in turn defers to the accepted economy manifest.
Three tables holding the same founder-directed constant can drift, so this one
holds none of them independently.
"""

from __future__ import annotations

from simulation.common.canonical import MAX_U64, InvariantError
from simulation.cycle_boundary import contract as boundary

STATE_SCHEMA = "protocol-stack/uptime-measurement-state/v1"
STATE_LABEL = "protocol-stack:uptime-measurement:state-v1"
CHALLENGE_LABEL = "protocol-stack:uptime-measurement:challenge-v1"
RECORD_SCHEMA = "protocol-stack/founder-economy-uptime-record/v2"

MAX_HEIGHT = MAX_U64

CYCLE_BLOCKS = boundary.CYCLE_BLOCKS
ACTIVITY_THRESHOLD_BLOCKS = boundary.ACTIVITY_THRESHOLD_BLOCKS
GRACE_ALLOWANCE_BLOCKS = boundary.GRACE_ALLOWANCE_BLOCKS
TARGET_COMMIT_SECONDS = boundary.TARGET_COMMIT_SECONDS
FOUNDER_SEAT_CAPACITY = boundary.FOUNDER_SEAT_CAPACITY
MAX_SEAT_ID = boundary.MAX_SEAT_ID

# 24 slots is the granularity at which all three founder-directed figures are
# whole slots, so the rule is applied in the units it was written in.
SLOTS_PER_WINDOW = 24
SLOT_BLOCKS = CYCLE_BLOCKS // SLOTS_PER_WINDOW
ACTIVITY_THRESHOLD_SLOTS = ACTIVITY_THRESHOLD_BLOCKS // SLOT_BLOCKS
GRACE_ALLOWANCE_SLOTS = GRACE_ALLOWANCE_BLOCKS // SLOT_BLOCKS
SLOT_SECONDS = SLOT_BLOCKS * TARGET_COMMIT_SECONDS
MAX_SLOT_INDEX = SLOTS_PER_WINDOW - 1

# Sixty seconds: enough for propagation and inclusion, far below a slot, so a
# node cannot be absent for a slot and answer for it afterwards.
RESPONSE_DEADLINE_BLOCKS = 20

# One probe per credited unit. This equality is the whole of the sampling-rate
# decision: the coarsest rate that supplies evidence for every slot it credits.
CHALLENGE_PERIOD_BLOCKS = SLOT_BLOCKS
CHALLENGEABLE_HEIGHTS_PER_SLOT = SLOT_BLOCKS - RESPONSE_DEADLINE_BLOCKS

DISPUTE_WINDOW_WINDOWS = 1
DISPUTE_CAP_SLOTS_PER_SEAT = GRACE_ALLOWANCE_SLOTS
RETAINED_WINDOWS = 1 + DISPUTE_WINDOW_WINDOWS

LIVE_SLOT_BYTES_PER_SEAT = 2
WINDOW_BITMAP_BYTES_PER_SEAT = SLOTS_PER_WINDOW // 8
MEASUREMENT_STORAGE_BYTES = FOUNDER_SEAT_CAPACITY * (
    LIVE_SLOT_BYTES_PER_SEAT + RETAINED_WINDOWS * WINDOW_BITMAP_BYTES_PER_SEAT
)

DUTY_KINDS: tuple[str, ...] = ("VALIDATOR", "SERVICING")

RESULT_CODES: tuple[str, ...] = (
    "ACCEPTED",
    "SEAT_RANGE",
    "SEAT_NOT_IN_SCOPE",
    "SCHEDULE_NOT_BOUND",
    "INVALID_BOUND_SCHEDULE",
    "REPLAY",
    "HEIGHT_RANGE",
    "HEIGHT_NOT_MONOTONIC",
    "INVALID_DUTY_KIND",
    "DUTY_REPLAY",
    "CHALLENGE_NOT_ISSUED",
    "CHALLENGE_NOT_OPEN",
    "RESPONSE_TOO_LATE",
    "RESPONSE_REPLAY",
    "RESPONSE_INVALID",
    "UNAUTHORIZED_DISPUTE",
    "SLOT_RANGE",
    "WINDOW_NOT_CLOSED",
    "DISPUTE_WINDOW_CLOSED",
    "DISPUTE_REPLAY",
    "DISPUTE_SLOT_NOT_CREDITED",
    "DISPUTE_CAP_EXCEEDED",
    "RECORD_NOT_FINAL",
    "WINDOW_HAS_NO_SEATS",
)
# There is deliberately no ARITHMETIC_OVERFLOW code. Every quantity this model
# accumulates is bounded far below u64 by an earlier condition - credited slots
# by 24, uptime seconds by 86,400, and a height by HEIGHT_RANGE - so an overflow
# is not a rejectable input but a defect, and the checked height arithmetic
# raises an invariant failure rather than returning a code. Declaring a code no
# path produces would claim coverage the vectors could not show.


def assert_exact_derivation() -> None:
    """Require every derived slot count to be exact and self-consistent.

    The grid rests on 24 slots dividing all three founder-directed block figures
    exactly. A remainder anywhere would put the 18-hour threshold between two
    slots, where the rule could only be applied by rounding a founder-directed
    value toward the operator or against them. That is a defect, so it raises.
    """
    for name, blocks, slots in (
        ("cycle", CYCLE_BLOCKS, SLOTS_PER_WINDOW),
        ("activity threshold", ACTIVITY_THRESHOLD_BLOCKS, ACTIVITY_THRESHOLD_SLOTS),
        ("grace allowance", GRACE_ALLOWANCE_BLOCKS, GRACE_ALLOWANCE_SLOTS),
    ):
        if blocks % SLOT_BLOCKS != 0:
            raise InvariantError(f"{name} of {blocks} blocks is not a whole number of slots")
        if slots * SLOT_BLOCKS != blocks:
            raise InvariantError(f"{name} slot count does not convert back to {blocks} blocks")

    if ACTIVITY_THRESHOLD_SLOTS + GRACE_ALLOWANCE_SLOTS != SLOTS_PER_WINDOW:
        raise InvariantError("the threshold and allowance do not sum to a window")
    if SLOT_SECONDS * SLOTS_PER_WINDOW != CYCLE_BLOCKS * TARGET_COMMIT_SECONDS:
        raise InvariantError("slot seconds do not sum to the window's nominal duration")

    # The containment theorem. A seat credited for every slot must still meet
    # its cycle after a maximal dispute, or the AI alone can fail a fully
    # operational node and owns the reward path.
    if SLOTS_PER_WINDOW - DISPUTE_CAP_SLOTS_PER_SEAT < ACTIVITY_THRESHOLD_SLOTS:
        raise InvariantError(
            f"a dispute cap of {DISPUTE_CAP_SLOTS_PER_SEAT} can fail a perfect seat"
        )

    if RESPONSE_DEADLINE_BLOCKS >= SLOT_BLOCKS:
        raise InvariantError("a response deadline at or beyond a slot cannot be contained")
    if CHALLENGEABLE_HEIGHTS_PER_SLOT + RESPONSE_DEADLINE_BLOCKS != SLOT_BLOCKS:
        raise InvariantError("challengeable heights and the deadline do not span a slot")


def assert_agrees_with_boundary() -> None:
    """Require the shared figures to match the accepted cycle-boundary contract.

    The cycle-boundary contract is the accepted one, so this table defers to it
    rather than the reverse. That contract in turn defers to the economy
    manifest, so one founder-directed value has one home.
    """
    for name, here, there in (
        ("CYCLE_BLOCKS", CYCLE_BLOCKS, boundary.CYCLE_BLOCKS),
        (
            "ACTIVITY_THRESHOLD_BLOCKS",
            ACTIVITY_THRESHOLD_BLOCKS,
            boundary.ACTIVITY_THRESHOLD_BLOCKS,
        ),
        ("GRACE_ALLOWANCE_BLOCKS", GRACE_ALLOWANCE_BLOCKS, boundary.GRACE_ALLOWANCE_BLOCKS),
        ("TARGET_COMMIT_SECONDS", TARGET_COMMIT_SECONDS, boundary.TARGET_COMMIT_SECONDS),
        ("FOUNDER_SEAT_CAPACITY", FOUNDER_SEAT_CAPACITY, boundary.FOUNDER_SEAT_CAPACITY),
    ):
        if here != there:
            raise InvariantError(f"{name} is {here} here and {there} in cycle-boundary-v1")
    boundary.assert_exact_derivation()
    boundary.assert_agrees_with_economy()
