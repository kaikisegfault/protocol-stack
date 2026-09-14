"""Independent model of the ecosystem's calendar.

Implements `docs/specifications/calendar-v1.md`: the canonical unit and range of
the consensus timestamp, the monotonicity rule, the two-sided acceptance
tolerance, the proleptic Gregorian derivation from a timestamp to a month, and
the month-opening predicate over a chain of heights.

This model derives a month. It ranks nothing, pays nothing, and observes no
machine. It reads no clock either: the one clock reading the contract needs is
a parameter the caller supplies to the admission check, which is the whole of
what makes the rest of it deterministic.
"""

from __future__ import annotations

from .chain import Block, Calendar
from .civil import civil_from_days, days_from_civil, days_in_month, is_leap_year
from .contract import (
    MAX_BOUNDARY_SHIFT_BLOCKS,
    MAX_MONTH_INDEX,
    MAX_TIMESTAMP_MILLIS,
    MILLIS_PER_DAY,
    MIN_TIMESTAMP_MILLIS,
    RESULT_CODES,
    STATE_LABEL,
    TIMESTAMP_TOLERANCE_MILLIS,
    TIMESTAMP_TOLERANCE_SECONDS,
    assert_agrees_with_cycle_boundary,
    assert_exact_derivation,
    assert_range_matches_the_calendar,
)
from .months import (
    day_index,
    in_range,
    month_end_millis,
    month_index,
    month_length_millis,
    month_start_millis,
    months_spanned,
    year_month_of,
)

__all__ = [
    "Block",
    "Calendar",
    "MAX_BOUNDARY_SHIFT_BLOCKS",
    "MAX_MONTH_INDEX",
    "MAX_TIMESTAMP_MILLIS",
    "MILLIS_PER_DAY",
    "MIN_TIMESTAMP_MILLIS",
    "RESULT_CODES",
    "STATE_LABEL",
    "TIMESTAMP_TOLERANCE_MILLIS",
    "TIMESTAMP_TOLERANCE_SECONDS",
    "assert_agrees_with_cycle_boundary",
    "assert_exact_derivation",
    "assert_range_matches_the_calendar",
    "civil_from_days",
    "day_index",
    "days_from_civil",
    "days_in_month",
    "in_range",
    "is_leap_year",
    "month_end_millis",
    "month_index",
    "month_length_millis",
    "month_start_millis",
    "months_spanned",
    "year_month_of",
]
