"""Independent model of the Founder Economy uptime measurement pipeline.

Implements `docs/specifications/uptime-measurement-v1.md`: the slot grid credit
is taken over, on-chain duty evidence, challenge-response with beacon-derived
selection, a bounded Ecosystem AI dispute window that finalises by expiry, and
the complete `cycle_uptime_record` the pipeline produces.

This model measures. It holds no value, issues nothing, credits no unit, and
activates nothing. It observes no real machine: the challenge protocol is
defined here and the challenge content is a founder-reserved value belonging to
the Founder Node milestone.
"""

from __future__ import annotations

from .contract import (
    ACTIVITY_THRESHOLD_SLOTS,
    CHALLENGE_PERIOD_BLOCKS,
    DISPUTE_CAP_SLOTS_PER_SEAT,
    GRACE_ALLOWANCE_SLOTS,
    MEASUREMENT_STORAGE_BYTES,
    RESPONSE_DEADLINE_BLOCKS,
    SLOT_BLOCKS,
    SLOT_SECONDS,
    SLOTS_PER_WINDOW,
    STATE_LABEL,
    assert_agrees_with_boundary,
    assert_exact_derivation,
)
from .model import DutyReport, UptimeMeasurement, UptimeRecord
from .slots import (
    assert_slots_tile_window,
    is_challengeable_height,
    is_selected,
    slot_first_height,
    slot_last_height,
    slot_of_height,
)

__all__ = [
    "ACTIVITY_THRESHOLD_SLOTS",
    "CHALLENGE_PERIOD_BLOCKS",
    "DISPUTE_CAP_SLOTS_PER_SEAT",
    "DutyReport",
    "GRACE_ALLOWANCE_SLOTS",
    "MEASUREMENT_STORAGE_BYTES",
    "RESPONSE_DEADLINE_BLOCKS",
    "SLOTS_PER_WINDOW",
    "SLOT_BLOCKS",
    "SLOT_SECONDS",
    "STATE_LABEL",
    "UptimeMeasurement",
    "UptimeRecord",
    "assert_agrees_with_boundary",
    "assert_exact_derivation",
    "assert_slots_tile_window",
    "is_challengeable_height",
    "is_selected",
    "slot_first_height",
    "slot_last_height",
    "slot_of_height",
]
