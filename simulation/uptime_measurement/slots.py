"""The slot grid inside a window, and challenge selection.

Pure integer and digest functions. Selection is derived from a beacon on demand
and never stored, which is one of the three properties that make the storage
bound in uptime-measurement-v1 hold.
"""

from __future__ import annotations

from simulation.common.canonical import InvariantError, checked_add, checked_mul, digest
from simulation.cycle_boundary.grid import window_first_height, window_of_height

from .contract import (
    CHALLENGE_LABEL,
    CHALLENGE_PERIOD_BLOCKS,
    CYCLE_BLOCKS,
    MAX_SLOT_INDEX,
    RESPONSE_DEADLINE_BLOCKS,
    SLOT_BLOCKS,
    SLOTS_PER_WINDOW,
)


def slot_of_height(height: int) -> int:
    """The slot index a height belongs to within its own window."""
    offset = height - window_first_height(window_of_height(height))
    slot = offset // SLOT_BLOCKS
    if not 0 <= slot <= MAX_SLOT_INDEX:
        raise InvariantError(f"height {height} derives slot {slot}, outside the window")
    return slot


def slot_first_height(window: int, slot: int) -> int:
    _require_slot(slot)
    first = checked_add(window_first_height(window), checked_mul(slot, SLOT_BLOCKS))
    if first is None:
        raise InvariantError(f"slot {slot} of window {window} exceeds u64")
    return first


def slot_last_height(window: int, slot: int) -> int:
    last = checked_add(slot_first_height(window, slot), SLOT_BLOCKS - 1)
    if last is None:
        raise InvariantError(f"slot {slot} of window {window} exceeds u64")
    return last


def is_challengeable_height(height: int) -> bool:
    """Whether a challenge may be issued at this height.

    The final `RESPONSE_DEADLINE_BLOCKS` heights of a slot are excluded, so a
    challenge and its deadline always lie inside one slot. That containment is
    what lets the per-slot counters be discarded at the slot boundary instead of
    carried across it.
    """
    window = window_of_height(height)
    slot = slot_of_height(height)
    return height <= slot_last_height(window, slot) - RESPONSE_DEADLINE_BLOCKS


def is_selected(seat_id: int, height: int, beacon: str) -> bool:
    """Whether a seat is challenged at this height.

    The beacon is the canonical ledger state root at `height - 1`, which no
    participant can compute before that block commits, so a seat learns of its
    challenge at most one block before it must answer and cannot schedule uptime
    around its own audit.
    """
    if not is_challengeable_height(height):
        return False
    preimage = {"beacon": beacon, "height": str(height), "seat_id": seat_id}
    return int(digest(CHALLENGE_LABEL, preimage), 16) % CHALLENGE_PERIOD_BLOCKS == 0


def selected_heights_in_slot(seat_id: int, window: int, slot: int, beacons: dict[int, str]) -> list[int]:
    """Every height in a slot at which a seat was challenged.

    Recomputed from the beacons rather than read from stored state, which is why
    an issued challenge costs no storage.
    """
    first = slot_first_height(window, slot)
    last = slot_last_height(window, slot)
    return [
        height
        for height in range(first, last + 1)
        if height in beacons and is_selected(seat_id, height, beacons[height])
    ]


def _require_slot(slot: int) -> None:
    if not isinstance(slot, int) or isinstance(slot, bool):
        raise InvariantError(f"slot {slot!r} is not an integer")
    if not 0 <= slot <= MAX_SLOT_INDEX:
        raise InvariantError(f"slot {slot} outside 0..{MAX_SLOT_INDEX}")


def assert_slots_tile_window() -> None:
    """Require the slot grid to tile a window exactly, with no gap or overlap.

    Checked against the boundary contract's window rather than against this
    module's own constants, so a slot count that no longer divides a window is a
    failure rather than a silently shorter last slot.
    """
    if SLOTS_PER_WINDOW * SLOT_BLOCKS != CYCLE_BLOCKS:
        raise InvariantError(
            f"{SLOTS_PER_WINDOW} slots of {SLOT_BLOCKS} blocks do not tile {CYCLE_BLOCKS}"
        )
    covered = set()
    for slot in range(SLOTS_PER_WINDOW):
        first = slot_first_height(0, slot)
        last = slot_last_height(0, slot)
        if covered & set(range(first, last + 1)):
            raise InvariantError(f"slot {slot} overlaps an earlier slot")
        covered |= set(range(first, last + 1))
    if covered != set(range(0, CYCLE_BLOCKS)):
        raise InvariantError("the slot grid does not cover a window exactly")
