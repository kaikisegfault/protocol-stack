"""Closed-form derivation of the cycle boundary from the founder documents.

This module imports nothing from `simulation/`. It restates the Founder
Constitution's figures and the pinned M1 commit interval by hand, in the units
those documents state them in, and derives everything else. A vector both this
module and a live model run reproduce has been reached from the founder document
and from the implementation independently.

Sources restated here, and nowhere derived from the model:

- "731 eligible 24-hour-target cycles" and "exactly 100,000 permanent biometric
  Founder Seats" - `docs/project/founder-constitution.md`.
- "A cycle is met when cumulative fully operational uptime within the
  24-hour-target cycle is 18 hours or more. Equivalently, a cycle fails when
  cumulative downtime exceeds 6 hours." - the same document.
- `timeout_commit = "3s"` - `docs/specifications/consensus-application-v1.md`.
"""

from __future__ import annotations

SECONDS_PER_HOUR = 3_600

CYCLE_TARGET_HOURS = 24
ACTIVITY_THRESHOLD_HOURS = 18
GRACE_ALLOWANCE_HOURS = 6

CYCLE_TARGET_SECONDS = CYCLE_TARGET_HOURS * SECONDS_PER_HOUR
ACTIVITY_THRESHOLD_SECONDS = ACTIVITY_THRESHOLD_HOURS * SECONDS_PER_HOUR
GRACE_ALLOWANCE_SECONDS = GRACE_ALLOWANCE_HOURS * SECONDS_PER_HOUR

TARGET_COMMIT_SECONDS = 3

ISSUANCE_CYCLES_PER_SEAT = 731
FOUNDER_SEAT_CAPACITY = 100_000
GENESIS_HEIGHT = 0

MAX_U64 = (1 << 64) - 1
ACTIVATION_HEIGHT_BYTES = 8


def blocks_for(seconds: int) -> int:
    """Convert a founder-directed duration to blocks, refusing any remainder.

    A remainder would put the threshold between two blocks, where the rule could
    only be applied by rounding a founder-directed value in one direction or the
    other. That is not a choice this project may make, so it is an error here.
    """
    quotient, remainder = divmod(seconds, TARGET_COMMIT_SECONDS)
    if remainder != 0:
        raise ValueError(
            f"{seconds}s is not a whole number of {TARGET_COMMIT_SECONDS}s blocks"
        )
    return quotient


CYCLE_BLOCKS = blocks_for(CYCLE_TARGET_SECONDS)
ACTIVITY_THRESHOLD_BLOCKS = blocks_for(ACTIVITY_THRESHOLD_SECONDS)
GRACE_ALLOWANCE_BLOCKS = blocks_for(GRACE_ALLOWANCE_SECONDS)

MAX_WINDOW = MAX_U64 // CYCLE_BLOCKS
MAX_SEAT_ID = FOUNDER_SEAT_CAPACITY - 1
MAX_CYCLE_INDEX = ISSUANCE_CYCLES_PER_SEAT - 1

SCHEDULE_STORAGE_BYTES = FOUNDER_SEAT_CAPACITY * ACTIVATION_HEIGHT_BYTES


def window_of_height(height: int) -> int:
    return height // CYCLE_BLOCKS


def window_first_height(window: int) -> int:
    return window * CYCLE_BLOCKS


def window_last_height(window: int) -> int:
    return window * CYCLE_BLOCKS + CYCLE_BLOCKS - 1


def first_cycle_window(activation_height: int) -> int:
    return window_of_height(activation_height) + 1


def last_cycle_window(activation_height: int) -> int:
    return first_cycle_window(activation_height) + MAX_CYCLE_INDEX


def window_for_cycle(activation_height: int, cycle_index: int) -> int:
    return first_cycle_window(activation_height) + cycle_index


def cycle_for_window(activation_height: int, window: int) -> int | None:
    offset = window - first_cycle_window(activation_height)
    return offset if 0 <= offset <= MAX_CYCLE_INDEX else None


def span_is_representable(activation_height: int) -> bool:
    return (
        0 <= activation_height <= MAX_U64
        and last_cycle_window(activation_height) <= MAX_WINDOW
    )


def uptime_seconds_for_blocks(uptime_blocks: int) -> int:
    """The exact conversion the nominal-duration rule depends on."""
    if not 0 <= uptime_blocks <= CYCLE_BLOCKS:
        raise ValueError(f"{uptime_blocks} blocks is outside a window")
    return uptime_blocks * TARGET_COMMIT_SECONDS


def check_window(
    activation_heights: dict[int, int],
    seat_id: int,
    cycle_index: int,
    cycle_window: int,
) -> str:
    """The specified rejection order, restated independently of the model."""
    if seat_id > MAX_SEAT_ID:
        return "SEAT_RANGE"
    if cycle_index > MAX_CYCLE_INDEX:
        return "CYCLE_RANGE"
    activation_height = activation_heights.get(seat_id)
    if activation_height is None:
        return "SEAT_NOT_ACTIVATED"
    if cycle_window < first_cycle_window(activation_height):
        return "WINDOW_BEFORE_ISSUANCE"
    if cycle_window > last_cycle_window(activation_height):
        return "WINDOW_AFTER_ISSUANCE"
    if cycle_window != window_for_cycle(activation_height, cycle_index):
        return "WINDOW_NOT_FOR_CYCLE"
    return "ACCEPTED"


def record_activation(
    activation_heights: dict[int, int],
    last_activation_height: int | None,
    seat_id: int,
    height: int,
) -> str:
    """The specified activation rejection order, restated independently."""
    if seat_id > MAX_SEAT_ID:
        return "SEAT_RANGE"
    if height > MAX_U64 or not span_is_representable(height):
        return "HEIGHT_RANGE"
    if seat_id in activation_heights:
        return "REPLAY"
    if last_activation_height is not None and height < last_activation_height:
        return "HEIGHT_NOT_MONOTONIC"
    return "ACCEPTED"
