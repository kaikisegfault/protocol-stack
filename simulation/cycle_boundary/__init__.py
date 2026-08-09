"""Independent model of the Founder Economy cycle boundary.

Implements `docs/specifications/cycle-boundary-v1.md`: the global block-height
grid a cycle window is cut from, the mapping from a seat's activation height to
its 731-window issuance span, and the check
`founder-economy-simulator-v2` records that it cannot make.

This model is a schedule and a check. It measures nothing, observes no node,
and activates nothing.
"""

from __future__ import annotations

from .contract import (
    ACTIVITY_THRESHOLD_BLOCKS,
    CYCLE_BLOCKS,
    GRACE_ALLOWANCE_BLOCKS,
    STATE_LABEL,
    assert_exact_derivation,
)
from .grid import (
    cycle_for_window,
    first_cycle_window,
    last_cycle_window,
    window_first_height,
    window_last_height,
    window_for_cycle,
    window_of_height,
)
from .model import CycleBoundary

__all__ = [
    "ACTIVITY_THRESHOLD_BLOCKS",
    "CYCLE_BLOCKS",
    "CycleBoundary",
    "GRACE_ALLOWANCE_BLOCKS",
    "STATE_LABEL",
    "assert_exact_derivation",
    "cycle_for_window",
    "first_cycle_window",
    "last_cycle_window",
    "window_first_height",
    "window_for_cycle",
    "window_last_height",
    "window_of_height",
]
