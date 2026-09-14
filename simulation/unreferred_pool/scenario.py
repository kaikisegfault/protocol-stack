"""The recorded unreferred-pool-payout-v1 scenario.

The chain runs at the commit target from a genesis deliberately off a day
boundary, so the fixture reaches every case the rule has without contriving a
timestamp: a window that straddles a boundary, a month whose last windows are
assigned after the next month has begun, a tie, a share that does not divide,
and a halt long enough to leave months with no window at all.

**The timestamps are the calendar's, not this model's.** `timestamp_of_height`
is one multiplication and `simulation.calendar` turns it into a month, so the
two contracts are bound rather than each holding an opinion about the date.
"""

from __future__ import annotations

from simulation.calendar import contract as cal
from simulation.calendar.civil import days_from_civil
from simulation.cycle_boundary.contract import CYCLE_BLOCKS, TARGET_COMMIT_SECONDS
from simulation.unreferred_pool import contract as c
from simulation.unreferred_pool.ledger import UnreferredPool, Window, month_of_window

MILLIS_PER_BLOCK = TARGET_COMMIT_SECONDS * cal.MILLIS_PER_SECOND

# 2026-02-27T06:00:00.000Z. Genesis is deliberately **off** a day boundary, so
# windows straddle calendar days and one of them straddles a month boundary. A
# genesis at midnight would make every window exactly one calendar day and the
# straddling case would be unreachable.
GENESIS_MILLIS = (
    days_from_civil(2026, 2, 27) * cal.MILLIS_PER_DAY
    + 6 * 3_600 * cal.MILLIS_PER_SECOND
)



def timestamp_of_height(height: int) -> int:
    """The chain's timestamp at a height, at the commit target exactly."""
    return GENESIS_MILLIS + height * MILLIS_PER_BLOCK


# Seat activation heights, and therefore first cycle windows of 1, 2, and 4.
# `first_cycle_window(a) = window_of_height(a) + 1` is `cycle-boundary-v1`'s, so
# no seat is ever in scope at window 0 and the fixture starts with one.
ACTIVATIONS: dict[int, int] = {1: 0, 2: CYCLE_BLOCKS, 3: 3 * CYCLE_BLOCKS}

# The referral accrual one unreferred seat produces for one cycle, in atomic
# units: `founder-economy-manifest-v3`'s 34.2 units at eight decimals.
REFERRAL_ATOMIC_PER_CYCLE = 3_420_000_000
A = REFERRAL_ATOMIC_PER_CYCLE

FULL = c.WINDOW_UPTIME_SECONDS_MAX
HALF = FULL // 2

# At the commit target a window is exactly one day, so window w begins at
# 2026-02-27T06:00Z plus w days. February holds windows 0 and 1, March 2 to 32,
# April 33 to 62, May 63 to 93, June 94 to 123, July 124 to 154, August 155 on.
#
# window, {seat: seconds}, accrual
SEQUENCE: tuple[tuple[int, dict[int, int], int], ...] = (
    # February. Window 0 has no in-scope seat at all, and window 1 straddles the
    # month boundary — it begins on the 28th and ends on the 1st — so all of its
    # uptime is February's under the accepted rule and March's under the
    # rejected one. February accrues nothing, so it pays nothing and that is not
    # an error.
    (0, {}, 0),
    (1, {1: FULL}, 0),
    # March. This assignment closes February, and it happens on 2 March: a month
    # is paid after the next one has already begun, which is the whole reason
    # the payout does not fire at a month's opening block.
    (2, {1: FULL, 2: FULL}, 2 * A),
    (3, {1: FULL, 2: FULL}, A + 1),
    (4, {1: HALF, 2: HALF, 3: FULL}, A),
    # April. This closes March on an exact two-way tie, over a payable that is
    # odd and therefore leaves a remainder of one.
    (33, {1: FULL, 2: FULL, 3: FULL}, A),
    # May. This closes April on an exact three-way tie.
    (63, {1: 0, 2: 0, 3: 0}, A),
    # August, after a halt that leaves June and July with no window at all. It
    # closes May — where every candidate ran for zero seconds, so all three tie
    # at zero and share, which is what "whatever that figure is" means — and then
    # June and July, which have no candidate and carry.
    (155, {1: FULL, 2: 0, 3: 0}, A),
)


def windows() -> tuple[Window, ...]:
    """The sequence with each window's month derived through `calendar-v1`."""
    return tuple(
        Window(
            index=index,
            month=month_of_window(index, timestamp_of_height),
            uptime=dict(uptime),
            accrual=accrual,
        )
        for index, uptime, accrual in SEQUENCE
    )


def build() -> UnreferredPool:
    """The recorded run, assigned window by window."""
    pool = UnreferredPool(ACTIVATIONS)
    for window in windows():
        pool.assign(window)
    return pool


def months_touched() -> tuple[int, ...]:
    return tuple(sorted({window.month for window in windows()}))


def straddling_windows() -> tuple[int, ...]:
    """Windows whose first and last heights fall in different months."""
    from simulation.calendar import months as calendar_months

    straddling = []
    for index, _uptime, _accrual in SEQUENCE:
        first = month_of_window(index, timestamp_of_height)
        last = calendar_months.month_index(
            timestamp_of_height((index + 1) * CYCLE_BLOCKS - 1)
        )
        if first != last:
            straddling.append(index)
    return tuple(straddling)


def figures_under_last_height_attribution(month: int) -> dict[int, int]:
    """A month's figures had windows been attributed by their last height.

    Recorded beside the real figures so the accepted rule and the rejected one
    are distinguishable rather than merely described. Under the accepted rule a
    straddling window belongs to the month it began in; under the rejected one
    it belongs to the month it ended in.
    """
    from simulation.calendar import months as calendar_months

    totals: dict[int, int] = {}
    for index, uptime, _accrual in SEQUENCE:
        last_height = (index + 1) * CYCLE_BLOCKS - 1
        if calendar_months.month_index(timestamp_of_height(last_height)) != month:
            continue
        for seat, seconds in uptime.items():
            if seconds:
                totals[seat] = totals.get(seat, 0) + seconds
    return totals
