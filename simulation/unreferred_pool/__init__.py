"""Independent model of the unreferred performance pool's monthly payout.

Implements `docs/specifications/unreferred-pool-payout-v1.md`: the monthly
candidate set, the ranking figure and which month a window's uptime counts
toward, the exact-tie split, the remainder, the carry, and the point in the
window-assignment sequence at which a month is paid.

It **binds** `calendar-v1` rather than restating it: a window's month arrives
from `simulation.calendar`, derived from the timestamp of the window's first
height. It measures nothing, encodes nothing, and reads no clock.
"""

from __future__ import annotations

from .contract import (
    ASSIGNMENT_LAG_WINDOWS,
    SLOTS_PER_WINDOW,
    SLOT_SECONDS,
    STATE_LABEL,
    WINDOW_UPTIME_SECONDS_MAX,
    assert_agrees_with_cycle_boundary,
    assert_agrees_with_uptime_measurement,
    assert_exact_derivation,
)
from .ledger import Payout, UnreferredPool, Window, month_of_window

__all__ = [
    "ASSIGNMENT_LAG_WINDOWS",
    "Payout",
    "SLOTS_PER_WINDOW",
    "SLOT_SECONDS",
    "STATE_LABEL",
    "UnreferredPool",
    "WINDOW_UPTIME_SECONDS_MAX",
    "Window",
    "assert_agrees_with_cycle_boundary",
    "assert_agrees_with_uptime_measurement",
    "assert_exact_derivation",
    "month_of_window",
]
