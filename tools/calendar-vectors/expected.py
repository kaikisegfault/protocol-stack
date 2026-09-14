"""Independent derivation of the calendar from the founder documents.

This module imports nothing from `simulation/`. It restates the rules the
accepted documents state, in the words those documents use, and derives
everything else by a different algorithm from the model's.

**The algorithms differ on purpose.** `simulation/calendar/civil.py` uses the
closed-form era arithmetic: no table, no loop, four integer divisions. This
module builds a cumulative table of month lengths from January 1970 and finds a
month by binary search over it. Both are correct implementations of the
proleptic Gregorian calendar and neither is derived from the other, so a value
they agree on has been reached twice rather than stated twice. A single
algorithm restating itself would make the vector file unfalsifiable.

Sources restated here, and nowhere derived from the model:

- "A month is a real calendar month beginning on the 1st", derived from the
  consensus timestamp in the block header - `docs/project/founder-constitution.md`
  and ADR 0050.
- "monotonic and within tolerance of their own clocks" - ADR 0050.
- `timeout_commit = "3s"` - `docs/specifications/consensus-application-v1.md`.
- The Gregorian leap rule, the twelve month lengths, and the Unix epoch, which
  are facts about the civil calendar rather than about this project.
"""

from __future__ import annotations

from bisect import bisect_right

MILLIS_PER_SECOND = 1_000
SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24
SECONDS_PER_DAY = HOURS_PER_DAY * MINUTES_PER_HOUR * SECONDS_PER_MINUTE
MILLIS_PER_DAY = SECONDS_PER_DAY * MILLIS_PER_SECOND

MIN_CALENDAR_YEAR = 1_970
MAX_CALENDAR_YEAR = 9_999
MONTHS_PER_YEAR = 12
MAX_MONTH_INDEX = (MAX_CALENDAR_YEAR - MIN_CALENDAR_YEAR) * MONTHS_PER_YEAR + 11

TIMESTAMP_TOLERANCE_SECONDS = 60
TIMESTAMP_TOLERANCE_MILLIS = TIMESTAMP_TOLERANCE_SECONDS * MILLIS_PER_SECOND

TARGET_COMMIT_SECONDS = 3
MAX_BOUNDARY_SHIFT_BLOCKS = TIMESTAMP_TOLERANCE_SECONDS // TARGET_COMMIT_SECONDS

SECONDS_PER_MONTH_MINIMUM = 28 * SECONDS_PER_DAY

GENESIS_HEIGHT = 0
FIRST_BLOCK_HEIGHT = GENESIS_HEIGHT + 1

ISSUANCE_CYCLES_PER_SEAT = 731

MONTH_LENGTHS_COMMON = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def is_leap_year(year: int) -> bool:
    """Divisible by 4, except centuries, except every fourth century."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def month_length_days(year: int, month: int) -> int:
    if month == 2 and is_leap_year(year):
        return 29
    return MONTH_LENGTHS_COMMON[month - 1]


def _accumulate_month_starts() -> tuple[int, ...]:
    """Day index of the 1st of every month from 1970-01 through 10000-01.

    One entry past `MAX_MONTH_INDEX`, because the last month's final
    millisecond is one before the next month's first.
    """
    starts = [0]
    day = 0
    for year in range(MIN_CALENDAR_YEAR, MAX_CALENDAR_YEAR + 1):
        for month in range(1, MONTHS_PER_YEAR + 1):
            day += month_length_days(year, month)
            starts.append(day)
    return tuple(starts)


MONTH_START_DAYS = _accumulate_month_starts()

MIN_TIMESTAMP_MILLIS = 0
MAX_TIMESTAMP_MILLIS = MONTH_START_DAYS[MAX_MONTH_INDEX + 1] * MILLIS_PER_DAY - 1
DAY_COUNT = MONTH_START_DAYS[MAX_MONTH_INDEX + 1]


def in_range(timestamp: int) -> bool:
    return MIN_TIMESTAMP_MILLIS <= timestamp <= MAX_TIMESTAMP_MILLIS


def day_index(timestamp: int) -> int:
    return timestamp // MILLIS_PER_DAY


def month_index(timestamp: int) -> int:
    """The month a timestamp falls in, by binary search over the day table."""
    return bisect_right(MONTH_START_DAYS, day_index(timestamp)) - 1


def year_of_index(index: int) -> int:
    return MIN_CALENDAR_YEAR + index // MONTHS_PER_YEAR


def month_of_index(index: int) -> int:
    return index % MONTHS_PER_YEAR + 1


def year_month_of(timestamp: int) -> tuple[int, int]:
    index = month_index(timestamp)
    return (year_of_index(index), month_of_index(index))


def month_start_millis(index: int) -> int:
    return MONTH_START_DAYS[index] * MILLIS_PER_DAY


def month_end_millis(index: int) -> int:
    return month_start_millis(index + 1) - 1


def month_length_millis(index: int) -> int:
    return month_end_millis(index) - month_start_millis(index) + 1


def days_from_civil(year: int, month: int, day: int) -> int:
    index = (year - MIN_CALENDAR_YEAR) * MONTHS_PER_YEAR + (month - 1)
    return MONTH_START_DAYS[index] + day - 1


def civil_from_days(day: int) -> tuple[int, int, int]:
    index = bisect_right(MONTH_START_DAYS, day) - 1
    return (
        year_of_index(index),
        month_of_index(index),
        day - MONTH_START_DAYS[index] + 1,
    )


def millis_of(instant: tuple[int, int, int, int, int, int, int]) -> int:
    year, month, day, hour, minute, second, milli = instant
    days = days_from_civil(year, month, day)
    seconds = (hour * MINUTES_PER_HOUR + minute) * SECONDS_PER_MINUTE + second
    return (days * SECONDS_PER_DAY + seconds) * MILLIS_PER_SECOND + milli


def months_spanned(first_day: int, day_count: int) -> int:
    first = bisect_right(MONTH_START_DAYS, first_day) - 1
    last = bisect_right(MONTH_START_DAYS, first_day + day_count - 1) - 1
    return last - first + 1


def longest_seat_span_months() -> int:
    """The most calendar months a 731-day seat span can touch.

    Walked over every start day in a four-century window rather than reasoned
    about from month lengths, because the reasoning is where the off-by-one
    lives. Four centuries covers every Gregorian leap pattern.
    """
    window = 400 * 366
    return max(
        months_spanned(first_day, ISSUANCE_CYCLES_PER_SEAT)
        for first_day in range(window)
    )


# --- the ordered acceptance rules, restated -----------------------------------


def acceptance_code(
    next_height: int,
    head_timestamp: int,
    height: int,
    timestamp: int,
    observed_clock: int,
) -> str:
    """The first condition that fires, in the order the specification states.

    Written as a flat chain of independent tests rather than by calling the
    model's, so the order is restated here and compared rather than borrowed.
    """
    if height != next_height:
        return "HEIGHT_NOT_NEXT"
    if not in_range(timestamp):
        return "TIMESTAMP_RANGE"
    if timestamp < head_timestamp:
        return "TIMESTAMP_NOT_MONOTONIC"
    if timestamp - observed_clock > TIMESTAMP_TOLERANCE_MILLIS:
        return "TIMESTAMP_AHEAD_OF_TOLERANCE"
    if observed_clock - timestamp > TIMESTAMP_TOLERANCE_MILLIS:
        return "TIMESTAMP_BEHIND_TOLERANCE"
    return "ACCEPTED"


def opens_a_month(previous_timestamp: int | None, timestamp: int) -> bool:
    if previous_timestamp is None:
        return True
    return month_index(timestamp) > month_index(previous_timestamp)


def months_closed_by(previous_timestamp: int | None, timestamp: int) -> tuple[int, ...]:
    if previous_timestamp is None:
        return ()
    return tuple(range(month_index(previous_timestamp), month_index(timestamp)))
