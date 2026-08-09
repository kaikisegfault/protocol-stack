"""Independent derivation of the uptime measurement pipeline.

This module imports nothing from `simulation/`. It restates the Founder
Constitution's figures by hand, derives the slot grid and every bound from them,
and walks the scenario with its own implementation of the specified challenge
selection. A vector both this module and a live model run reproduce has been
reached from the founder document and from the implementation independently.

Sources restated here, and nowhere derived from the model:

- "18 hours or more" of cumulative fully operational uptime, a "24-hour-target
  cycle", and a fragmentable "6-hour grace allowance" -
  `docs/project/founder-constitution.md`.
- "exactly 100,000 permanent biometric Founder Seats" - same document.
- `timeout_commit = "3s"` - the pinned M1 CometBFT configuration.

The digest construction is reimplemented from `protocol-primitives-v1` rather
than imported, so agreement on a selection is agreement between two
implementations of the specified rule.
"""

from __future__ import annotations

import hashlib
import json

# --- restated founder figures ------------------------------------------

CYCLE_TARGET_SECONDS = 86_400
ACTIVITY_THRESHOLD_SECONDS = 64_800
GRACE_ALLOWANCE_SECONDS = 21_600
TARGET_COMMIT_SECONDS = 3
FOUNDER_SEAT_CAPACITY = 100_000

# --- derived grid -------------------------------------------------------

CYCLE_BLOCKS = CYCLE_TARGET_SECONDS // TARGET_COMMIT_SECONDS
ACTIVITY_THRESHOLD_BLOCKS = ACTIVITY_THRESHOLD_SECONDS // TARGET_COMMIT_SECONDS
GRACE_ALLOWANCE_BLOCKS = GRACE_ALLOWANCE_SECONDS // TARGET_COMMIT_SECONDS

SLOTS_PER_WINDOW = 24
SLOT_BLOCKS = CYCLE_BLOCKS // SLOTS_PER_WINDOW
ACTIVITY_THRESHOLD_SLOTS = ACTIVITY_THRESHOLD_BLOCKS // SLOT_BLOCKS
GRACE_ALLOWANCE_SLOTS = GRACE_ALLOWANCE_BLOCKS // SLOT_BLOCKS
SLOT_SECONDS = SLOT_BLOCKS * TARGET_COMMIT_SECONDS

RESPONSE_DEADLINE_BLOCKS = 20
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

CHALLENGE_LABEL = "protocol-stack:uptime-measurement:challenge-v1"

# --- the scenario, restated ---------------------------------------------

ACTIVATIONS: dict[int, int] = {0: 0, 1: 10, 2: 11, 3: CYCLE_BLOCKS + 5}
SILENT_SEAT = 1
DUTY_FAILING_SEAT = 2
DUTY_FAILURE_SLOT = 3
DUTY_FAILURE_WINDOW = 1


def derived_grid_is_exact() -> bool:
    """Whether every founder figure is a whole number of slots.

    A remainder would put the 18-hour threshold between two slots, where the
    rule could only be applied by rounding a founder-directed value.
    """
    return (
        CYCLE_BLOCKS * TARGET_COMMIT_SECONDS == CYCLE_TARGET_SECONDS
        and SLOTS_PER_WINDOW * SLOT_BLOCKS == CYCLE_BLOCKS
        and ACTIVITY_THRESHOLD_SLOTS * SLOT_BLOCKS == ACTIVITY_THRESHOLD_BLOCKS
        and GRACE_ALLOWANCE_SLOTS * SLOT_BLOCKS == GRACE_ALLOWANCE_BLOCKS
        and ACTIVITY_THRESHOLD_SLOTS + GRACE_ALLOWANCE_SLOTS == SLOTS_PER_WINDOW
    )


def perfect_seat_survives_maximal_dispute() -> bool:
    """The containment theorem, derived rather than read from the model.

    A seat credited for every slot must still meet its cycle after the largest
    admissible dispute, or the Ecosystem AI alone can fail a fully operational
    node and owns the reward path the constitution keeps out of its hands.
    """
    return SLOTS_PER_WINDOW - DISPUTE_CAP_SLOTS_PER_SEAT >= ACTIVITY_THRESHOLD_SLOTS


# --- an independent implementation of challenge selection ---------------


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _digest(label: str, value: object) -> str:
    encoded = label.encode("ascii")
    prefix = bytes([len(encoded)]) + encoded
    return hashlib.sha256(prefix + _canonical_bytes(value)).hexdigest()


def beacon_for(height: int) -> str:
    return f"{height:064x}"


def is_challengeable_height(height: int) -> bool:
    offset = height % SLOT_BLOCKS
    return offset < CHALLENGEABLE_HEIGHTS_PER_SLOT


def is_selected(seat_id: int, height: int) -> bool:
    if not is_challengeable_height(height):
        return False
    preimage = {"beacon": beacon_for(height), "height": str(height), "seat_id": seat_id}
    return int(_digest(CHALLENGE_LABEL, preimage), 16) % CHALLENGE_PERIOD_BLOCKS == 0


def in_scope(window: int) -> list[int]:
    """Seats activated strictly before the window's first height."""
    first_height = window * CYCLE_BLOCKS
    return sorted(seat for seat, height in ACTIVATIONS.items() if height < first_height)


def walk(windows: int) -> dict[int, dict[int, int]]:
    """Credited slots per window per seat, from an independent walk.

    Reimplements the credit rule from the specification: a slot begins credited,
    a failed assigned duty clears it, and an unanswered challenge clears it at
    slot close. Nothing here consults the model.
    """
    last_height = (windows + DISPUTE_WINDOW_WINDOWS + 1) * CYCLE_BLOCKS
    credited: dict[int, dict[int, set[int]]] = {}
    issued: dict[int, int] = {}
    answered: dict[int, int] = {}
    previous: tuple[int, int] | None = None

    for height in range(0, last_height + 1):
        window = height // CYCLE_BLOCKS
        slot = (height % CYCLE_BLOCKS) // SLOT_BLOCKS
        scope = in_scope(window)

        if previous is not None and previous != (window, slot):
            previous_window, previous_slot = previous
            for seat in in_scope(previous_window):
                if issued.get(seat, 0) != answered.get(seat, 0):
                    credited[previous_window][seat].discard(previous_slot)
            issued, answered = {}, {}

        if window not in credited:
            credited[window] = {seat: set(range(SLOTS_PER_WINDOW)) for seat in scope}

        if (
            window == DUTY_FAILURE_WINDOW
            and slot == DUTY_FAILURE_SLOT
            and height % SLOT_BLOCKS == 0
            and DUTY_FAILING_SEAT in scope
        ):
            credited[window][DUTY_FAILING_SEAT].discard(slot)

        for seat in scope:
            if is_selected(seat, height):
                issued[seat] = issued.get(seat, 0) + 1
                if seat != SILENT_SEAT:
                    answered[seat] = answered.get(seat, 0) + 1

        previous = (window, slot)

    return {
        window: {seat: len(slots) for seat, slots in sorted(seats.items())}
        for window, seats in sorted(credited.items())
    }


def uptime_seconds(credited_slots: int) -> int:
    return credited_slots * SLOT_SECONDS


def met_cycle(credited_slots: int) -> bool:
    return uptime_seconds(credited_slots) >= ACTIVITY_THRESHOLD_SECONDS


def challenges_issued(seat_id: int, window: int) -> int:
    """Challenges a seat received across a complete window."""
    first = window * CYCLE_BLOCKS
    return sum(1 for height in range(first, first + CYCLE_BLOCKS) if is_selected(seat_id, height))
