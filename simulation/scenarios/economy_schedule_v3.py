"""The staggered population's schedule, its records, and its event shapes.

Version three enforces what versions one and two only recorded, and both
enforcements reach this scenario.

A seat now carries the activation height its 731-window schedule is derived
from, and a base permission is rejected unless its `cycle_window` is the window
the accepted grid assigns to its `cycle_index`. The tick is therefore no longer
a free parameter: keeping it the shared window — the property this scenario
exists to demonstrate — forces `k * STAGGER * CYCLE_BLOCKS` as seat `k`'s
activation height, which puts its cycle `t - k * STAGGER` in window `t + 1`.

An uptime record must also cover exactly its window's in-scope seat set, so
version two's habit of listing every seat in every window is now rejected. A
seat enters the record at the tick its own schedule opens.

Every set below is derived from `cycle-boundary-v1`'s grid rather than restated
as a comparison on ticks, so a generator that drifted from the schedule the
model enforces would produce rejections instead of quietly disagreeing.
"""

from __future__ import annotations

from typing import Any

from ..cycle_boundary.grid import first_cycle_window
from ..founder_economy_v3 import contract as c

SEATS = 3
# Seat 0 refers both other seats, so one referrer accumulates the referral
# benefit of two seats across the whole multi-year window. Seat 0 is itself
# unreferred, so its own accruals reach the unreferred performance pool and the
# run exercises both destinations of the channel.
REFERRERS: dict[int, int | None] = {0: None, 1: 0, 2: 0}

# Ticks between consecutive activations. Prime, and far below the 731-cycle
# window, so every pair of windows overlaps for most of the run.
STAGGER = 61

# A seat is inactive when `(cycle + INACTIVE_PHASE * seat) % INACTIVE_PERIOD`
# is zero. The phase shift keeps the three seats' inactive cycles disjoint in
# every window, which `failing_seat` asserts rather than assumes.
INACTIVE_PERIOD = 73
INACTIVE_PHASE = 7

# Uptime in whole seconds. A failed cycle is far below the threshold; the
# intended winner is at the full cycle target; every other seat sits exactly on
# the 64,800-second threshold, so the boundary is exercised in every window that
# reallocates rather than only in a dedicated test.
FAILED_UPTIME = 3_600
WINNER_UPTIME = c.CYCLE_TARGET_SECONDS
THRESHOLD_UPTIME = c.ACTIVITY_THRESHOLD_SECONDS

LAST_CYCLE = c.ISSUANCE_CYCLES_PER_SEAT - 1
LAST_TICK = LAST_CYCLE + (SEATS - 1) * STAGGER

# The three probe seats. Their heights, not the event order, are what keeps them
# out of every population record: each opens after the run's last window, so
# `in_scope_at` excludes them throughout even though all six seats are activated
# before the first cycle. Listing a probe seat early would enlarge every record
# and make it a possible reallocation winner, which would change what the
# reallocation vectors mean.
PROBE_SEAT = 3
# Shares `PROBE_SEAT`'s window so one accepted evaluation can bind a record
# there. Version three checks the window before the binding, so a contradictory
# record can only be reached inside a window the probe seat genuinely holds.
PEER_SEAT = 4
# One window later, so it is out of scope at `PROBE_WINDOW` by exactly one
# window rather than by a wide margin.
LATE_SEAT = 5
# Never activated. The two activation probes name it so that neither can be
# mistaken for a replay of an existing seat.
UNKNOWN_SEAT = 6

# The window the uptime and boundary probes evaluate against: the first one
# after the population run's last.
PROBE_WINDOW = LAST_TICK + 2
PROBE_HEIGHT = (PROBE_WINDOW - 1) * c.CYCLE_BLOCKS
LATE_HEIGHT = PROBE_WINDOW * c.CYCLE_BLOCKS

HEIGHTS: dict[int, int] = {
    **{seat_id: seat_id * STAGGER * c.CYCLE_BLOCKS for seat_id in range(SEATS)},
    PROBE_SEAT: PROBE_HEIGHT,
    PEER_SEAT: PROBE_HEIGHT,
    LATE_SEAT: LATE_HEIGHT,
}
ACTIVATED_SEATS = tuple(sorted(HEIGHTS))
ACTIVATION_REFERRERS: dict[int, int | None] = {
    **REFERRERS,
    PROBE_SEAT: None,
    PEER_SEAT: None,
    LATE_SEAT: None,
}


def window_at(tick: int) -> int:
    """The shared cycle window every seat evaluating at this tick presents."""
    return tick + 1


def cycle_at(seat_id: int, tick: int) -> int | None:
    """The seat's own cycle index at this tick, or None when out of window."""
    cycle_index = tick - seat_id * STAGGER
    if 0 <= cycle_index < c.ISSUANCE_CYCLES_PER_SEAT:
        return cycle_index
    return None


def in_scope_at_window(window: int) -> tuple[int, ...]:
    """The seats a window's record must cover, derived from the grid.

    This is `uptime-measurement-v1`'s rule applied to the activation table, read
    from `cycle-boundary-v1` rather than restated, so the generator and the
    model cannot disagree about a boundary.
    """
    return tuple(
        seat_id
        for seat_id in ACTIVATED_SEATS
        if first_cycle_window(HEIGHTS[seat_id]) <= window
    )


def in_scope_at(tick: int) -> tuple[int, ...]:
    return in_scope_at_window(window_at(tick))


def is_inactive(seat_id: int, cycle_index: int) -> bool:
    return (cycle_index + INACTIVE_PHASE * seat_id) % INACTIVE_PERIOD == 0


def inactive_cycles(seat_id: int) -> list[int]:
    return [
        cycle
        for cycle in range(c.ISSUANCE_CYCLES_PER_SEAT)
        if is_inactive(seat_id, cycle)
    ]


def failing_seat(tick: int) -> int | None:
    """The one seat whose evaluated cycle fails in this window, if any.

    The phase shift makes the three seats' inactive cycles disjoint in every
    window. That is asserted here rather than assumed, because two failures in
    one window would make the winner set depend on evaluation order and would
    quietly change what the recorded totals mean.
    """
    failing = [
        seat_id
        for seat_id in range(SEATS)
        if (cycle := cycle_at(seat_id, tick)) is not None
        and is_inactive(seat_id, cycle)
    ]
    if len(failing) > 1:
        raise AssertionError(f"tick {tick}: {len(failing)} seats fail in one window")
    return failing[0] if failing else None


def performance_winner(seat_id: int) -> int:
    """The deterministic intended recipient of a failed seat's 342-unit leg."""
    return (seat_id + 1) % SEATS


def rewarded_winner(tick: int) -> int | None:
    """The intended winner, when its own schedule has already opened.

    A seat outside the window's in-scope set is absent from the record, so the
    model can derive no winner from it. Returning None here is what makes the
    empty winner set a derived count rather than a discovery.
    """
    failing = failing_seat(tick)
    if failing is None:
        return None
    winner = performance_winner(failing)
    return winner if winner in in_scope_at(tick) else None


def unrewarded_ticks() -> tuple[int, ...]:
    """The failed cycles whose portion no seat in scope is able to receive."""
    return tuple(
        tick
        for tick in range(LAST_TICK + 1)
        if failing_seat(tick) is not None and rewarded_winner(tick) is None
    )


def record_over(window: int, uptimes: dict[int, int]) -> dict[str, Any]:
    """One cycle uptime record, ordered by seat and carrying counts only."""
    return {
        "cycle_window": window,
        "entries": [
            {"seat_id": seat_id, "uptime_seconds": uptimes[seat_id]}
            for seat_id in sorted(uptimes)
        ],
    }


def uptime_record(tick: int) -> dict[str, Any]:
    """The window's measurements, identical for every seat evaluating in it.

    A record is bound by digest on first reference, so every seat evaluating in
    this window must present exactly this value. Building it as a pure function
    of the tick is what guarantees that.
    """
    failing = failing_seat(tick)
    winner = None if failing is None else performance_winner(failing)
    return record_over(
        window_at(tick),
        {seat_id: _uptime(seat_id, failing, winner) for seat_id in in_scope_at(tick)},
    )


def _uptime(seat_id: int, failing: int | None, winner: int | None) -> int:
    if seat_id == failing:
        return FAILED_UPTIME
    if failing is None or seat_id == winner:
        return WINNER_UPTIME
    return THRESHOLD_UPTIME


def activate(seat_id: int, referrer: int | None, height: int) -> dict[str, Any]:
    """A seat activation. The height is a decimal string, because it is a u64."""
    return {
        "id": f"activate-{seat_id:05d}",
        "kind": "activate_seat",
        "seat_id": seat_id,
        "referrer_seat_id": referrer,
        "activation_height": str(height),
    }


def base(
    seat_id: int,
    cycle_index: int,
    record: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "id": f"base-{seat_id:05d}-{cycle_index:03d}",
        "kind": "evaluate_base_permission",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
        "cycle_uptime_record": record,
    }


def exercise(seat_id: int, cycle_index: int) -> dict[str, Any]:
    return {
        "id": f"exercise-{seat_id:05d}-{cycle_index:03d}",
        "kind": "exercise_permission",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
    }


def accrue(seat_id: int, cycle_index: int) -> dict[str, Any]:
    return {
        "id": f"accrue-{seat_id:05d}-{cycle_index:03d}",
        "kind": "accrue_referral",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
    }
