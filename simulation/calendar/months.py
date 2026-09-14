"""The derivation from a consensus timestamp to a calendar month, and back.

Every function here is a pure function of a millisecond count. None reads a
clock: a timestamp is a field a block already carries by the time anything in
this module is asked about it.
"""

from __future__ import annotations

from simulation.calendar import contract as c
from simulation.calendar.civil import civil_from_days, days_from_civil
from simulation.common.canonical import InvariantError


def in_range(timestamp: int) -> bool:
    return c.MIN_TIMESTAMP_MILLIS <= timestamp <= c.MAX_TIMESTAMP_MILLIS


def require_in_range(timestamp: int) -> int:
    """Refuse a timestamp outside the accepted range before deriving from it.

    Every derivation below is total only on the accepted range, so a caller
    that skipped the range check would reach a year this specification does not
    define. That is a defect rather than a chain input: the ordered rejection
    conditions refuse an out-of-range timestamp first, so nothing reaching here
    can be outside it.
    """
    if not in_range(timestamp):
        raise InvariantError(
            f"timestamp {timestamp} is outside the accepted calendar range"
        )
    return timestamp


def day_index(timestamp: int) -> int:
    """Whole days since 1970-01-01.

    Exact because `MILLIS_PER_DAY` is a constant rather than a measurement: no
    leap second is represented, so every day is the same length.
    """
    return require_in_range(timestamp) // c.MILLIS_PER_DAY


def year_month_of(timestamp: int) -> tuple[int, int]:
    year, month, _day = civil_from_days(day_index(timestamp))
    return (year, month)


def month_index(timestamp: int) -> int:
    """The monotone month number, zero for the epoch month.

    Anchoring at 1970 rather than at year zero keeps the index inside a u32
    with five decimal orders to spare and makes the epoch month index 0 rather
    than an arbitrary constant.
    """
    year, month = year_month_of(timestamp)
    return (year - c.MIN_CALENDAR_YEAR) * c.MONTHS_PER_YEAR + (month - 1)


def year_of_index(index: int) -> int:
    return c.MIN_CALENDAR_YEAR + index // c.MONTHS_PER_YEAR


def month_of_index(index: int) -> int:
    return index % c.MONTHS_PER_YEAR + 1


def month_start_millis(index: int) -> int:
    """The first millisecond of a month index.

    `MAX_MONTH_INDEX + 1` is accepted and is the single value this derivation
    computes outside the accepted timestamp range: it is the exclusive end of
    December 9999 and is what `month_end_millis` subtracts one from. That is
    why the range ends at the last millisecond of 9999 rather than at the u64
    bound — the one-past-the-end value has to be representable.
    """
    if not 0 <= index <= c.MAX_MONTH_INDEX + 1:
        raise InvariantError(f"month index {index} is outside the accepted range")
    return days_from_civil(year_of_index(index), month_of_index(index), 1) * c.MILLIS_PER_DAY


def month_end_millis(index: int) -> int:
    """The last millisecond of a month index."""
    if not 0 <= index <= c.MAX_MONTH_INDEX:
        raise InvariantError(f"month index {index} is outside the accepted range")
    return month_start_millis(index + 1) - 1


def month_length_millis(index: int) -> int:
    return month_end_millis(index) - month_start_millis(index) + 1


def months_spanned(first_day: int, day_count: int) -> int:
    """How many calendar months a run of consecutive days touches.

    Used to bound a seat's 731-cycle span. It walks the two endpoints rather
    than reasoning about month lengths, because the reasoning is where the
    off-by-one lives.
    """
    if day_count < 1:
        raise InvariantError("a span touches at least one day")
    start_year, start_month, _ = civil_from_days(first_day)
    end_year, end_month, _ = civil_from_days(first_day + day_count - 1)
    return (end_year - start_year) * c.MONTHS_PER_YEAR + (end_month - start_month) + 1
