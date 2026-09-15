"""Where each of `calendar-v1`'s five rules is applied, and which one is not.

`calendar-v1`'s central rule is that C5 reads a clock and the other four do not,
and that a machine replaying history must re-check C1 and C2 and must **not**
re-check C5. Getting it wrong is silent: a machine that re-applied the tolerance
on replay would reject the chain's own past one tolerance-width after producing
it.

So this module has two entry points and they differ in exactly one respect.
`accept` takes an observed clock reading and applies every rule; `replay` takes
no clock at all and cannot reach one. A conforming implementation exposes the two
paths separately rather than as a branch inside execution, which is what the
specification requires of the binding version and what this shape makes
structural: there is no argument you could pass `replay` that would make it check
a tolerance.

**The rules are restated here over two scalars rather than driven through
`simulation.calendar.Calendar`**, because a ledger holds a head timestamp and not
a list of every block it has ever seen: the month a transition needs comes from
state, written at the window's opening height, so nothing on the version-nine
execution path ever asks what the timestamp at some past height was.
`assert_agrees_with_calendar_v1` is what keeps the restatement honest — it runs a
chain through the accepted model and through these two functions and requires
every outcome, including which condition fired, to be identical.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.calendar import months as calendar_months
from simulation.common.canonical import CodedError

from . import contract as c

__all__ = [
    "Head",
    "accept",
    "assert_agrees_with_calendar_v1",
    "month_of",
    "replay",
]


@dataclass(frozen=True)
class Head:
    """What a version-nine machine holds about where it is in time.

    Two scalars, both committed to by the state root. At genesis the height is
    zero and the timestamp is the genesis timestamp, which is what makes C2's
    genesis case the same comparison as every other height's rather than a
    special rule.
    """

    height: int
    timestamp: int


def month_of(timestamp: int) -> int:
    """`calendar-v1`'s month index, bound rather than derived.

    Nothing in version nine computes a date. This is the one place a timestamp
    becomes a month, and it is one call into the accepted model.
    """
    return calendar_months.month_index(timestamp)


def _deterministic(head: Head, height: int, timestamp: int) -> None:
    """Conditions 1 to 3, re-applied on every replay.

    The order is normative: a timestamp outside the representable range is
    refused before any derivation is attempted on it, which is what keeps
    `month_of` total.
    """
    if height != head.height + 1:
        raise CodedError(
            "HEIGHT_NOT_NEXT",
            f"height {height} is not the chain's next height {head.height + 1}",
        )
    if not calendar_months.in_range(timestamp):
        raise CodedError(
            "TIMESTAMP_RANGE",
            f"timestamp {timestamp} is outside "
            f"[{c.MIN_TIMESTAMP_MILLIS}, {c.MAX_TIMESTAMP_MILLIS}]",
        )
    if timestamp < head.timestamp:
        raise CodedError(
            "TIMESTAMP_NOT_MONOTONIC",
            f"timestamp {timestamp} is below the predecessor's {head.timestamp}",
        )


def _tolerance(timestamp: int, observed_clock: int) -> None:
    """Conditions 4 and 5, applied once at admission and never again.

    Both comparisons are guarded subtractions rather than
    `timestamp > observed_clock + TOLERANCE`. The sum is the shape that wraps
    when a clock sits near the `u64` bound, and a wrapped comparison accepts
    exactly the values it exists to refuse.
    """
    if type(observed_clock) is not int or observed_clock < 0:
        raise ValueError("an observed clock reading is a non-negative integer")
    if timestamp > observed_clock:
        if timestamp - observed_clock > c.TIMESTAMP_TOLERANCE_MILLIS:
            raise CodedError(
                "TIMESTAMP_AHEAD_OF_TOLERANCE",
                f"timestamp {timestamp} is {timestamp - observed_clock}ms ahead "
                "of the observed clock",
            )
    elif observed_clock - timestamp > c.TIMESTAMP_TOLERANCE_MILLIS:
        raise CodedError(
            "TIMESTAMP_BEHIND_TOLERANCE",
            f"timestamp {timestamp} is {observed_clock - timestamp}ms behind "
            "the observed clock",
        )


def accept(head: Head, height: int, timestamp: int, observed_clock: int) -> Head:
    """Admit a proposed height, or refuse it and advance nothing.

    This is the path a machine takes when it first validates a height, and it is
    the only path that reads a clock.
    """
    _deterministic(head, height, timestamp)
    _tolerance(timestamp, observed_clock)
    return Head(height=height, timestamp=timestamp)


def replay(head: Head, height: int, timestamp: int) -> Head:
    """Re-apply an accepted height with no clock available.

    A machine replaying history, restoring from a snapshot, or reconstructing
    state takes this path. There is no parameter here that could make it check a
    tolerance, which is the structural half of `calendar-v1`'s separation.
    """
    _deterministic(head, height, timestamp)
    return Head(height=height, timestamp=timestamp)


def assert_agrees_with_calendar_v1(
    genesis_timestamp: int, proposals: list[tuple[int, int, int]]
) -> None:
    """Require these two entry points to be the accepted model's, outcome for outcome.

    `proposals` is `(height, timestamp, observed_clock)`. The accepted
    `simulation.calendar.Calendar` is driven with the same sequence, and every
    acceptance, every refusal, and **which condition fired** must match. A
    restatement that merely accepted the same blocks would not be checked: the
    ordered conditions are the part a second implementation gets wrong.
    """
    from simulation.calendar.chain import Calendar

    reference = Calendar(genesis_timestamp)
    head = Head(height=0, timestamp=genesis_timestamp)
    for height, timestamp, clock in proposals:
        here: str | None = None
        there: str | None = None
        try:
            advanced = accept(head, height, timestamp, clock)
        except CodedError as refusal:
            here = refusal.code
            advanced = head
        try:
            reference.accept(height, timestamp, clock)
        except CodedError as refusal:
            there = refusal.code
        if here != there:
            raise AssertionError(
                f"height {height}: version nine reports {here!r} and calendar-v1 "
                f"reports {there!r}"
            )
        head = advanced
