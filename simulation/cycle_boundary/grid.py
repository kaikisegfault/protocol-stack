"""The window grid and a seat's issuance span.

Pure integer functions over block heights. Every operation is addition,
subtraction, multiplication, comparison, or truncating division, and every
derived quantity is checked against the u64 bound rather than assumed to fit.
"""

from __future__ import annotations

from simulation.common.canonical import InvariantError, checked_add, checked_mul

from .contract import (
    CYCLE_BLOCKS,
    ISSUANCE_CYCLES_PER_SEAT,
    MAX_CYCLE_INDEX,
    MAX_HEIGHT,
)

# The largest window identifier whose first and last heights are representable.
MAX_WINDOW = MAX_HEIGHT // CYCLE_BLOCKS


def window_of_height(height: int) -> int:
    """The window a height belongs to. Every height belongs to exactly one."""
    _require_height(height)
    return height // CYCLE_BLOCKS


def window_first_height(window: int) -> int:
    _require_window(window)
    first = checked_mul(window, CYCLE_BLOCKS)
    if first is None:
        raise InvariantError(f"window {window} first height exceeds u64")
    return first


def window_last_height(window: int) -> int:
    last = checked_add(window_first_height(window), CYCLE_BLOCKS - 1)
    if last is None:
        raise InvariantError(f"window {window} last height exceeds u64")
    return last


def first_cycle_window(activation_height: int) -> int:
    """A seat's cycle 0 is the first window that starts after its activation.

    Counting the activating window would give a seat activated one block before
    a boundary a first cycle of one block, which cannot reach the 18-hour
    threshold, so the seat would fail a cycle it was never able to meet.
    """
    window = checked_add(window_of_height(activation_height), 1)
    if window is None:
        raise InvariantError("first cycle window exceeds u64")
    return window


def last_cycle_window(activation_height: int) -> int:
    window = checked_add(first_cycle_window(activation_height), MAX_CYCLE_INDEX)
    if window is None:
        raise InvariantError("last cycle window exceeds u64")
    return window


def span_is_representable(activation_height: int) -> bool:
    """Whether a seat's complete 731-window span fits in u64.

    Unreachable at any plausible height: the check leaves more than 640 trillion
    windows of headroom. It is a guard proved present, exercised directly by
    tests rather than by a scenario.
    """
    if activation_height > MAX_HEIGHT:
        return False
    first = checked_add(activation_height // CYCLE_BLOCKS, 1)
    if first is None:
        return False
    last = checked_add(first, MAX_CYCLE_INDEX)
    return last is not None and last <= MAX_WINDOW


def window_for_cycle(activation_height: int, cycle_index: int) -> int:
    if not 0 <= cycle_index <= MAX_CYCLE_INDEX:
        raise InvariantError(f"cycle index {cycle_index} outside 0..{MAX_CYCLE_INDEX}")
    window = checked_add(first_cycle_window(activation_height), cycle_index)
    if window is None:
        raise InvariantError("cycle window exceeds u64")
    return window


def cycle_for_window(activation_height: int, window: int) -> int | None:
    """The exact inverse of `window_for_cycle` on a seat's span, else None."""
    first = first_cycle_window(activation_height)
    if window < first:
        return None
    offset = window - first
    if offset > MAX_CYCLE_INDEX:
        return None
    return offset


def span_length(activation_height: int) -> int:
    """The number of windows in a seat's span, always the founder-directed 731."""
    length = last_cycle_window(activation_height) - first_cycle_window(activation_height) + 1
    if length != ISSUANCE_CYCLES_PER_SEAT:
        raise InvariantError(f"span holds {length} windows, not {ISSUANCE_CYCLES_PER_SEAT}")
    return length


def _require_height(height: int) -> None:
    if not isinstance(height, int) or isinstance(height, bool):
        raise InvariantError(f"height {height!r} is not an integer")
    if height < 0 or height > MAX_HEIGHT:
        raise InvariantError(f"height {height} outside 0..{MAX_HEIGHT}")


def _require_window(window: int) -> None:
    if not isinstance(window, int) or isinstance(window, bool):
        raise InvariantError(f"window {window!r} is not an integer")
    if window < 0 or window > MAX_WINDOW:
        raise InvariantError(f"window {window} outside 0..{MAX_WINDOW}")
