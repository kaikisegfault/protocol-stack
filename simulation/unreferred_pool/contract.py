"""Fixed unreferred-pool-payout-v1 constants and the guards they rest on.

Every figure here is imported from an accepted contract rather than restated:
the window grid is `cycle-boundary-v1`'s, the slot arithmetic is
`uptime-measurement-v1`'s as `economy-transition-v8` applies it, and the seat
capacity and issuance span are the Founder Constitution's. The guards below
require this table to agree with those documents rather than hold a second
opinion.
"""

from __future__ import annotations

from simulation.common.canonical import MAX_U64, InvariantError

STATE_SCHEMA = "protocol-stack/unreferred-pool-payout-state/v1"
STATE_LABEL = "protocol-stack:unreferred-pool-payout:state-v1"

# `uptime-measurement-v1`, as `economy-transition-v8` applies it.
SLOT_SECONDS = 3_600
SLOTS_PER_WINDOW = 24
WINDOW_UPTIME_SECONDS_MAX = SLOTS_PER_WINDOW * SLOT_SECONDS

# `economy-transition-v7`: a window is assigned this many windows after it
# opens, which is the whole reason the payout does not fire at a month's
# opening block.
ASSIGNMENT_LAG_WINDOWS = 2

MAX_FIGURE_SECONDS = MAX_U64


def assert_exact_derivation() -> None:
    """Require the derived window bound to be exact and self-consistent."""
    if WINDOW_UPTIME_SECONDS_MAX != SLOTS_PER_WINDOW * SLOT_SECONDS:
        raise InvariantError("the window uptime bound disagrees with itself")
    if ASSIGNMENT_LAG_WINDOWS < 1:
        raise InvariantError(
            "a lag below one window would assign a window before it closed"
        )


def assert_agrees_with_cycle_boundary() -> None:
    """Require a window's maximal uptime to equal the accepted cycle target.

    A window that could hold more or less uptime than a cycle is worth would
    mean this model and `cycle-boundary-v1` disagree about how long a day is,
    and the monthly figure would be denominated in neither document's units.
    """
    from simulation.cycle_boundary import contract as grid

    if WINDOW_UPTIME_SECONDS_MAX != grid.CYCLE_TARGET_SECONDS:
        raise InvariantError(
            f"a full window is {WINDOW_UPTIME_SECONDS_MAX}s here and a cycle is "
            f"{grid.CYCLE_TARGET_SECONDS}s in cycle-boundary-v1"
        )
    if SLOT_SECONDS * SLOTS_PER_WINDOW % grid.TARGET_COMMIT_SECONDS != 0:
        raise InvariantError("a full window is not a whole number of blocks")


def assert_agrees_with_uptime_measurement() -> None:
    """Require the slot figures to match the accepted measurement contract."""
    from simulation.uptime_measurement import contract as measurement

    for name, here, there in (
        ("SLOT_SECONDS", SLOT_SECONDS, measurement.SLOT_SECONDS),
        ("SLOTS_PER_WINDOW", SLOTS_PER_WINDOW, measurement.SLOTS_PER_WINDOW),
    ):
        if here != there:
            raise InvariantError(
                f"{name} is {here} here and {there} in uptime-measurement-v1"
            )
