"""Closed-form expectations for suite version three.

This module is the independence in the version-three verifier. It imports
nothing from `simulation/`.

The economy literals come from `expected_v2.py`, which converts the Founder
Constitution as revised on 2026-08-07 by hand, and the seat price schedule and
routing shares from `expected.py` through it. The window grid comes from
`tools/cycle-boundary-vectors/expected.py`, which converts the constitution's
durations and the pinned M1 commit interval by hand and reads no model. A third
hand-restatement of either would be a third thing to keep equal, which is the
failure the closed-form method exists to avoid.

What this module adds is version three's own consequences: the activation
heights the shared window forces, the in-scope set each window's record must
cover, and a walk of the founder-directed reallocation rule that carries an
unrewarded window's portion forward instead of assuming every failed cycle finds
a recipient in the same window.
"""

from __future__ import annotations

import importlib.util as _importlib_util
import sys
from pathlib import Path

from expected_v2 import (  # noqa: F401  (re-exported as the shared constitution)
    ATOMIC_UNITS_PER_DISPLAY_UNIT,
    BASE_PERMISSION_TOTAL,
    COMMUNITY_GRANTS_LEG,
    DECIMAL_PLACES,
    DEVELOPER_INCENTIVES_LEG,
    FOUNDER_OPERATOR_LEG,
    FOUNDER_SEAT_CAPACITY,
    INACTIVE_PERIOD,
    INACTIVE_PHASE,
    ISSUANCE_CYCLES_PER_SEAT,
    MAXIMUM_SUPPLY_ATOMIC,
    MAXIMUM_SUPPLY_DISPLAY,
    PAYOUTS_PER_ESCROW,
    REFERRAL_LEG,
    SYSTEM_CREATOR_LEG,
    VENTURE_ESCROW_LEG,
    base_permission_total,
    is_inactive,
    payout_amounts,
)

_TOOLS = Path(__file__).resolve().parents[1]


def _load(name: str, relative: str):
    """Load a sibling verifier's closed-form module under its own name.

    The cycle-boundary verifier also defines a module called `expected`, so it
    is loaded by path rather than by name; importing it normally would return
    this directory's `expected` instead.
    """
    spec = _importlib_util.spec_from_file_location(name, _TOOLS / relative)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {relative}")
    module = _importlib_util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


grid = _load("expected_cycle_boundary", "cycle-boundary-vectors/expected.py")

VERSION = "v3"

CYCLE_BLOCKS = grid.CYCLE_BLOCKS

# `economy-scenario-suite-v3` scenario 1 parameters, restated here so the
# expectations are computed from the specification rather than from the
# generator that produced the run.
POPULATION_SEATS = 3
POPULATION_REFERRED_SEATS = 2
POPULATION_UNREFERRED_SEATS = POPULATION_SEATS - POPULATION_REFERRED_SEATS
STAGGER = 61

LAST_CYCLE = ISSUANCE_CYCLES_PER_SEAT - 1
LAST_TICK = LAST_CYCLE + (POPULATION_SEATS - 1) * STAGGER

# The three probe seats. `PEER_SEAT` shares `PROBE_SEAT`'s height so that one
# accepted evaluation can bind a record in the window the probe seat holds;
# `LATE_SEAT` opens one window later so it is out of scope there.
PROBE_SEAT = 3
PEER_SEAT = 4
LATE_SEAT = 5
PROBE_SEATS = 3
ACTIVATED_SEATS = POPULATION_SEATS + PROBE_SEATS

# The peer seat evaluates, exercises, and accrues exactly one cycle.
PEER_EVALUATIONS = 1

PROBE_WINDOW = LAST_TICK + 2
PROBE_HEIGHT = (PROBE_WINDOW - 1) * CYCLE_BLOCKS
LATE_HEIGHT = PROBE_WINDOW * CYCLE_BLOCKS

ACTIVATION_HEIGHTS: dict[int, int] = {
    **{seat_id: seat_id * STAGGER * CYCLE_BLOCKS for seat_id in range(POPULATION_SEATS)},
    PROBE_SEAT: PROBE_HEIGHT,
    PEER_SEAT: PROBE_HEIGHT,
    LATE_SEAT: LATE_HEIGHT,
}
LAST_ACTIVATION_HEIGHT = max(ACTIVATION_HEIGHTS.values())

PROBES = (
    ("cycle_beyond_window", "probe-cycle-beyond-window"),
    ("base_replay", "probe-base-replay"),
    ("exercise_replay", "probe-exercise-replay"),
    ("activation_replay", "probe-activation-replay"),
    ("height_range", "probe-height-range"),
    ("height_not_monotonic", "probe-height-not-monotonic"),
    ("missing_uptime_record", "probe-missing-uptime-record"),
    ("invalid_uptime_record", "probe-invalid-uptime-record"),
    ("window_before_issuance", "probe-window-before-issuance"),
    ("window_after_issuance", "probe-window-after-issuance"),
    ("window_not_for_cycle", "probe-window-not-for-cycle"),
    ("seat_not_in_scope", "probe-seat-not-in-scope"),
    ("incomplete_uptime_record", "probe-incomplete-uptime-record"),
    ("inconsistent_uptime_record", "probe-inconsistent-uptime-record"),
    ("accrual_replay", "probe-accrual-replay"),
    ("direct_referral", "probe-direct-referral"),
)

# Accepted, not refused. They exist because version three checks a window before
# it checks the binding, so a contradictory record can only be presented inside
# a window the evaluating seat genuinely holds.
PEER_EVENTS = (
    ("peer_base", "peer-base-probe-window"),
    ("peer_exercise", "peer-exercise-probe-window"),
    ("peer_accrue", "peer-accrue-probe-window"),
)


def window_at(tick: int) -> int:
    """The shared window. Every seat's cycle at this tick lands here."""
    return tick + 1


def cycle_at(seat_id: int, tick: int) -> int | None:
    cycle_index = tick - seat_id * STAGGER
    if 0 <= cycle_index < ISSUANCE_CYCLES_PER_SEAT:
        return cycle_index
    return None


def in_scope_at_window(window: int) -> tuple[int, ...]:
    """`uptime-measurement-v1`'s rule applied to the activation table."""
    return tuple(
        seat_id
        for seat_id in sorted(ACTIVATION_HEIGHTS)
        if grid.first_cycle_window(ACTIVATION_HEIGHTS[seat_id]) <= window
    )


def full_scope_window() -> int:
    """The first window covering the whole population, so records stop growing."""
    return grid.first_cycle_window(ACTIVATION_HEIGHTS[POPULATION_SEATS - 1])


def bound_window_count() -> int:
    """One record per population window, plus the one the peer seat binds."""
    return (LAST_TICK + 1) + PEER_EVALUATIONS


def inactive_cycle_count(seat_id: int) -> int:
    return sum(
        1
        for cycle in range(ISSUANCE_CYCLES_PER_SEAT)
        if is_inactive(seat_id, cycle)
    )


def failing_seat(tick: int) -> int | None:
    failing = [
        seat_id
        for seat_id in range(POPULATION_SEATS)
        if (cycle := cycle_at(seat_id, tick)) is not None
        and is_inactive(seat_id, cycle)
    ]
    if len(failing) > 1:
        raise AssertionError(f"tick {tick}: {len(failing)} seats fail in one window")
    return failing[0] if failing else None


def performance_winner(seat_id: int) -> int:
    return (seat_id + 1) % POPULATION_SEATS


def rewarded_winner(tick: int) -> int | None:
    """The intended winner, when its own schedule has already opened."""
    failing = failing_seat(tick)
    if failing is None:
        return None
    winner = performance_winner(failing)
    return winner if winner in in_scope_at_window(window_at(tick)) else None


def reallocation() -> tuple[dict[int, int], int, int]:
    """Walk the founder-directed rule: legs received, carried, and unrewarded.

    Version two could assume every failed cycle paid a seat in the same window,
    because its records listed the whole population from the first tick. Version
    three cannot: a seat outside a window's in-scope set is absent from its
    record, so an early failure may find no candidate at all. The rule then
    carries the whole portion forward to the next window that does, which is
    what this walk derives rather than assumes.
    """
    received = {seat_id: 0 for seat_id in range(POPULATION_SEATS)}
    carried = 0
    unrewarded = 0
    for tick in range(LAST_TICK + 1):
        if failing_seat(tick) is None:
            continue
        winner = rewarded_winner(tick)
        if winner is None:
            carried += 1
            unrewarded += 1
            continue
        received[winner] += 1 + carried
        carried = 0
    return received, carried, unrewarded


def unrewarded_window_count() -> int:
    return reallocation()[2]


def performance_carry() -> int:
    """The carry the run must end at, in atomic units."""
    return reallocation()[1] * FOUNDER_OPERATOR_LEG


def evaluated_permission_keys() -> int:
    """The population's cycles, plus the peer seat's single one."""
    return POPULATION_SEATS * ISSUANCE_CYCLES_PER_SEAT + PEER_EVALUATIONS


def referral_accruals_created() -> int:
    """One unconditional accrual per evaluated seat-cycle."""
    return POPULATION_SEATS * ISSUANCE_CYCLES_PER_SEAT + PEER_EVALUATIONS


def unreferred_accruals() -> int:
    """The accruals with no recorded referrer, which reach the pool instead."""
    return POPULATION_UNREFERRED_SEATS * ISSUANCE_CYCLES_PER_SEAT + PEER_EVALUATIONS


def unreferred_pool_custody() -> int:
    return unreferred_accruals() * REFERRAL_LEG


def economy_channel_totals() -> dict[str, int]:
    """Each channel's issued total over the complete population run.

    The Founder operator total is independent of inactivity: a reallocation
    changes the beneficiary of the 342-unit leg, never its amount, and an
    unrewarded window changes only when it is delivered.
    """
    evaluations = evaluated_permission_keys()
    return {
        "founder_operator": evaluations * FOUNDER_OPERATOR_LEG,
        "venture_escrow": evaluations * VENTURE_ESCROW_LEG,
        "community_grants_escrow": evaluations * COMMUNITY_GRANTS_LEG,
        "developer_incentives_escrow": evaluations * DEVELOPER_INCENTIVES_LEG,
        "system_creator_issuance_royalty": evaluations * SYSTEM_CREATOR_LEG,
        "founder_referral": referral_accruals_created() * REFERRAL_LEG,
    }


def economy_seat_custody() -> dict[int, int]:
    """Each seat's custody: its own met cycles, plus what it was allocated."""
    received, _, _ = reallocation()
    custody: dict[int, int] = {}
    for seat_id in range(POPULATION_SEATS):
        met = ISSUANCE_CYCLES_PER_SEAT - inactive_cycle_count(seat_id)
        custody[seat_id] = (met + received[seat_id]) * FOUNDER_OPERATOR_LEG
    custody[0] += POPULATION_REFERRED_SEATS * ISSUANCE_CYCLES_PER_SEAT * REFERRAL_LEG
    custody[PEER_SEAT] = PEER_EVALUATIONS * FOUNDER_OPERATOR_LEG
    return custody
