"""Channel 8: the entry airdrop and the daily verified-user permission.

ADR 0042 supplied the population and the period — the first 1,000,000 verified
users, daily, for two years — and the accepted manifest supplies the cap. Those
three determine the fourth exactly, which is why the rate is derived rather than
chosen and why this module checks the derivation rather than restating a figure.

**Day one is the entry airdrop** written by the registration, and it is what
makes a brand-new account able to transact at all. **Days two through 731 are
ordinary mint permissions.**

**The thirty-window cap is applied at the mint rather than at assignment**, and
that is the one place this channel's mechanism differs from a seat's. A seat's
cap is applied when the chain writes the cycle-assignment record, where a capped
seat's permission moves to that day's best performers; no per-window record for a
million identities is affordable at 25 kB a window, so a collection here covers
the most recent thirty windows and the mark advances past everything older. The
rule is the same and the mechanism differs.

**The walk is arithmetic rather than iteration**, because every window in the
period pays the same amount unconditionally, so a mint is `O(1)` whatever the gap.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.cycle_boundary import grid

from . import contract as c
from .identity import Enrollment


def derived_daily_atomic() -> int:
    """The rate the three founder-supplied figures determine, with no remainder.

    Deriving it here rather than importing the constant is what makes a drifted
    constant a failure instead of a value: the accepted channel cap, the
    population, and the period are three independent sources.
    """
    per_user = c.VERIFIED_USER_CHANNEL_CAP // c.VERIFIED_USER_POPULATION
    if per_user * c.VERIFIED_USER_POPULATION != c.VERIFIED_USER_CHANNEL_CAP:
        raise ValueError("the channel cap does not divide by the population")
    daily = per_user // c.VERIFIED_USER_CYCLES
    if daily * c.VERIFIED_USER_CYCLES != per_user:
        raise ValueError("the per-user allocation does not divide by the period")
    return daily


def enroll(height: int) -> Enrollment:
    """Registration's enrollment. Day one is paid immediately as the airdrop."""
    return Enrollment(
        enrolled_at_height=height,
        minted_through_window=grid.window_of_height(height),
        issued_atomic=c.VERIFIED_USER_DAILY_ATOMIC,
    )


def last_window(enrollment: Enrollment) -> int:
    """The final window of this identity's 731-window period."""
    return (
        grid.window_of_height(enrollment.enrolled_at_height)
        + c.VERIFIED_USER_CYCLES
        - 1
    )


@dataclass(frozen=True)
class Collection:
    window_start: int
    collectable_end: int
    count: int
    amount_atomic: int
    forfeited_windows: int


def collect(enrollment: Enrollment, height: int) -> Collection:
    """What a kind-18 mint at `height` collects, and what it forfeits.

    `window_start` is where the cap forfeits: a person who has not collected for
    forty windows collects the most recent thirty and the older ten are never
    issued. The mark then advances to `collectable_end` rather than to the walk's
    end, which is what makes the forfeiture permanent rather than deferred.
    """
    last_completed = grid.window_of_height(height) - 1
    collectable_end = min(last_completed, last_window(enrollment))
    mark = enrollment.minted_through_window
    if collectable_end <= mark:
        return Collection(mark, mark, 0, 0, 0)
    window_start = max(mark, collectable_end - c.MINT_ACCUMULATION_CAP)
    count = collectable_end - window_start
    return Collection(
        window_start=window_start,
        collectable_end=collectable_end,
        count=count,
        amount_atomic=count * c.VERIFIED_USER_DAILY_ATOMIC,
        forfeited_windows=window_start - mark,
    )


def applied(enrollment: Enrollment, collection: Collection) -> Enrollment:
    return Enrollment(
        enrolled_at_height=enrollment.enrolled_at_height,
        minted_through_window=collection.collectable_end,
        issued_atomic=enrollment.issued_atomic + collection.amount_atomic,
    )


def maximum_issuance_per_identity() -> int:
    return c.VERIFIED_USER_CYCLES * c.VERIFIED_USER_DAILY_ATOMIC
