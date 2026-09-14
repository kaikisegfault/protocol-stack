"""Proleptic Gregorian date arithmetic in integers.

`days_from_civil` and `civil_from_days` are the standard closed-form pair: a
day index counted from 1970-01-01 converts to a year, month, and day and back
with no table, no loop, and no floating point. They are exact inverses over the
whole accepted range, which `tests/simulation/calendar_civil_test.py` walks day
by day rather than sampling.

The closed form is used here deliberately. The verifier's `expected.py`
accumulates month lengths from 1970 instead, so a recorded value is reached by
two different algorithms rather than by one algorithm stated twice.
"""

from __future__ import annotations

from simulation.common.canonical import InvariantError

# Days in the 400-year Gregorian cycle, and the offset that moves the era's
# internal 0000-03-01 origin to 1970-01-01.
DAYS_PER_ERA = 146_097
DAYS_FROM_ERA_ORIGIN_TO_EPOCH = 719_468

MONTH_LENGTHS_COMMON: tuple[int, ...] = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def is_leap_year(year: int) -> bool:
    """The Gregorian rule in full, not the abbreviation of it.

    A year divisible by 4 is a leap year unless it is divisible by 100, in
    which case it is one only if it is also divisible by 400. 2000 is a leap
    year and 2100 is not; an implementation that tested only 2024 would agree
    with the abbreviation and be wrong twice a century.
    """
    if year % 4 != 0:
        return False
    if year % 100 != 0:
        return True
    return year % 400 == 0


def days_in_month(year: int, month: int) -> int:
    if not 1 <= month <= 12:
        raise InvariantError(f"month {month} is not in 1..12")
    if month == 2 and is_leap_year(year):
        return 29
    return MONTH_LENGTHS_COMMON[month - 1]


def days_from_civil(year: int, month: int, day: int) -> int:
    """The day index of a proleptic Gregorian date, counted from 1970-01-01."""
    if not 1 <= month <= 12:
        raise InvariantError(f"month {month} is not in 1..12")
    if not 1 <= day <= days_in_month(year, month):
        raise InvariantError(f"day {day} is not in {year}-{month:02d}")

    # March-based year: February's variable length moves to the end, so the
    # day-of-year formula below needs no leap-year case at all.
    shifted_year = year - (1 if month <= 2 else 0)
    era = shifted_year // 400
    year_of_era = shifted_year - era * 400
    shifted_month = month + (-3 if month > 2 else 9)
    day_of_year = (153 * shifted_month + 2) // 5 + day - 1
    day_of_era = (
        year_of_era * 365 + year_of_era // 4 - year_of_era // 100 + day_of_year
    )
    return era * DAYS_PER_ERA + day_of_era - DAYS_FROM_ERA_ORIGIN_TO_EPOCH


def civil_from_days(day_index: int) -> tuple[int, int, int]:
    """The proleptic Gregorian date of a day index counted from 1970-01-01."""
    shifted = day_index + DAYS_FROM_ERA_ORIGIN_TO_EPOCH
    era = shifted // DAYS_PER_ERA
    day_of_era = shifted - era * DAYS_PER_ERA
    year_of_era = (
        day_of_era - day_of_era // 1_460 + day_of_era // 36_524 - day_of_era // 146_096
    ) // 365
    year = year_of_era + era * 400
    day_of_year = day_of_era - (365 * year_of_era + year_of_era // 4 - year_of_era // 100)
    shifted_month = (5 * day_of_year + 2) // 153
    day = day_of_year - (153 * shifted_month + 2) // 5 + 1
    month = shifted_month + (3 if shifted_month < 10 else -9)
    return (year + (1 if month <= 2 else 0), month, day)


def days_in_year(year: int) -> int:
    return 366 if is_leap_year(year) else 365
