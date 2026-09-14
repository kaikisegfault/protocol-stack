"""Fixed calendar-v1 constants and the consistency guards they rest on.

The unit, the epoch, the accepted range, and the acceptance tolerance are fixed
by `docs/specifications/calendar-v1.md`. The commit interval is
`consensus-application-v1`'s and is an input to one derivation here — how many
blocks a boundary shift is worth — and never to a transition. Nothing in this
model reads a clock; the only clock reading in the contract is a parameter the
caller supplies to the admission check.
"""

from __future__ import annotations

from simulation.common.canonical import MAX_U64, InvariantError

STATE_SCHEMA = "protocol-stack/calendar-state/v1"
STATE_LABEL = "protocol-stack:calendar:state-v1"

MILLIS_PER_SECOND = 1_000
SECONDS_PER_DAY = 86_400
MILLIS_PER_DAY = SECONDS_PER_DAY * MILLIS_PER_SECOND

MIN_CALENDAR_YEAR = 1_970
MAX_CALENDAR_YEAR = 9_999
MONTHS_PER_YEAR = 12

# `(9999 - 1970) * 12 + 11`, the index of December 9999.
MAX_MONTH_INDEX = (MAX_CALENDAR_YEAR - MIN_CALENDAR_YEAR) * MONTHS_PER_YEAR + 11

MIN_TIMESTAMP_MILLIS = 0
# The last millisecond of 9999-12-31, derived rather than transcribed by
# `assert_range_matches_the_calendar` below.
MAX_TIMESTAMP_MILLIS = 253_402_300_799_999

TIMESTAMP_TOLERANCE_SECONDS = 60
TIMESTAMP_TOLERANCE_MILLIS = TIMESTAMP_TOLERANCE_SECONDS * MILLIS_PER_SECOND

# The pinned M1 CometBFT commit interval from consensus-application-v1. It says
# how long a tolerance is worth in blocks and decides nothing else.
TARGET_COMMIT_SECONDS = 3
MAX_BOUNDARY_SHIFT_BLOCKS = TIMESTAMP_TOLERANCE_SECONDS // TARGET_COMMIT_SECONDS

# The shortest calendar month, used only to state how small the tolerance is
# relative to a month. It is not a unit of anything.
SECONDS_PER_MONTH_MINIMUM = 28 * SECONDS_PER_DAY

# The calendar stores nothing. A height's month is a pure function of a field
# the header already carries, so there is no record to bound.
CALENDAR_STATE_BYTES = 0

# The height of the initial state in `ledger-transition-v1`. The chain's first
# block is height 1.
GENESIS_HEIGHT = 0
FIRST_BLOCK_HEIGHT = GENESIS_HEIGHT + 1

RESULT_CODES: tuple[str, ...] = (
    "ACCEPTED",
    "HEIGHT_NOT_NEXT",
    "TIMESTAMP_RANGE",
    "TIMESTAMP_NOT_MONOTONIC",
    "TIMESTAMP_AHEAD_OF_TOLERANCE",
    "TIMESTAMP_BEHIND_TOLERANCE",
)

# The rejection order the specification makes normative. A timestamp outside
# the representable range is refused before any derivation runs on it, which is
# what keeps every later rule total.
REJECTION_ORDER: tuple[str, ...] = (
    "HEIGHT_NOT_NEXT",
    "TIMESTAMP_RANGE",
    "TIMESTAMP_NOT_MONOTONIC",
    "TIMESTAMP_AHEAD_OF_TOLERANCE",
    "TIMESTAMP_BEHIND_TOLERANCE",
)

# The two rules a replaying machine re-checks, and the one it must not. C5 is
# the only rule whose input is not in the block.
DETERMINISTIC_CODES: frozenset[str] = frozenset(
    {"HEIGHT_NOT_NEXT", "TIMESTAMP_RANGE", "TIMESTAMP_NOT_MONOTONIC"}
)
ADMISSION_ONLY_CODES: frozenset[str] = frozenset(
    {"TIMESTAMP_AHEAD_OF_TOLERANCE", "TIMESTAMP_BEHIND_TOLERANCE"}
)


def assert_exact_derivation() -> None:
    """Require every derived constant to be exact and mutually consistent.

    `MAX_BOUNDARY_SHIFT_BLOCKS` is the one figure that could be rounded, and a
    rounded figure here would understate or overstate a founder-visible bound.
    A remainder is a defect rather than an input, so it raises.
    """
    if TIMESTAMP_TOLERANCE_SECONDS % TARGET_COMMIT_SECONDS != 0:
        raise InvariantError(
            f"a {TIMESTAMP_TOLERANCE_SECONDS}s tolerance is not a whole number "
            f"of {TARGET_COMMIT_SECONDS}s blocks"
        )
    if MAX_BOUNDARY_SHIFT_BLOCKS * TARGET_COMMIT_SECONDS != TIMESTAMP_TOLERANCE_SECONDS:
        raise InvariantError("the boundary shift does not convert back to the tolerance")
    if TIMESTAMP_TOLERANCE_MILLIS != TIMESTAMP_TOLERANCE_SECONDS * MILLIS_PER_SECOND:
        raise InvariantError("the tolerance disagrees with itself across units")
    if MILLIS_PER_DAY != SECONDS_PER_DAY * MILLIS_PER_SECOND:
        raise InvariantError("the day length disagrees with itself across units")

    # The ceiling ADR 0050 requires: the tolerance must be small relative to a
    # month, because it is exactly how far a proposer can move a boundary.
    if TIMESTAMP_TOLERANCE_SECONDS * 1_000 >= SECONDS_PER_MONTH_MINIMUM:
        raise InvariantError(
            "the tolerance is not small relative to the shortest calendar month"
        )

    if MAX_TIMESTAMP_MILLIS > MAX_U64:
        raise InvariantError("the accepted range does not fit in a u64")
    if MIN_TIMESTAMP_MILLIS != 0:
        raise InvariantError("the accepted range does not begin at the epoch")


def assert_range_matches_the_calendar() -> None:
    """Require the transcribed range bound to equal the calendar's own answer.

    `MAX_TIMESTAMP_MILLIS` is the only literal here that a reader could not
    check by inspection, so it is derived from the month table and compared
    rather than trusted. A wrong bound would make the last month of the range
    partially unreachable without failing anything else.
    """
    from simulation.calendar import months

    if months.month_start_millis(MAX_MONTH_INDEX + 1) - 1 != MAX_TIMESTAMP_MILLIS:
        raise InvariantError(
            "the accepted range does not end at the last millisecond of "
            f"December {MAX_CALENDAR_YEAR}"
        )
    if months.month_index(MIN_TIMESTAMP_MILLIS) != 0:
        raise InvariantError("the epoch is not month index zero")
    if months.month_index(MAX_TIMESTAMP_MILLIS) != MAX_MONTH_INDEX:
        raise InvariantError("the range bound is not in the last month")


def assert_agrees_with_cycle_boundary() -> None:
    """Require the shared commit interval to match the accepted grid contract.

    Two tables holding the same pinned figure can drift. `cycle-boundary-v1` is
    the accepted one, so this table defers to it rather than the reverse.
    """
    from simulation.cycle_boundary import contract as grid

    if TARGET_COMMIT_SECONDS != grid.TARGET_COMMIT_SECONDS:
        raise InvariantError(
            f"TARGET_COMMIT_SECONDS is {TARGET_COMMIT_SECONDS} here and "
            f"{grid.TARGET_COMMIT_SECONDS} in cycle-boundary-v1"
        )
    if GENESIS_HEIGHT != grid.GENESIS_HEIGHT:
        raise InvariantError(
            f"GENESIS_HEIGHT is {GENESIS_HEIGHT} here and "
            f"{grid.GENESIS_HEIGHT} in cycle-boundary-v1"
        )
