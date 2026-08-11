"""A complete 731-cycle run over a staggered Founder Seat population, v3.

The Founder Constitution gives each seat 731 eligible cycles beginning at its
own first activation. Version three derives those windows from a recorded
activation height instead of accepting whichever window an event supplied, so
the stagger is now a schedule rather than only an event order: at tick `t` the
seat activated in window `k * STAGGER` evaluates its own cycle `t - k * STAGGER`
in the shared window `t + 1`. Every seat still completes exactly 731 cycles
while three windows overlap in different phases throughout the run.

`economy_schedule_v3` holds that schedule and the record it produces;
`economy_probes_v3` holds the adversarial block appended once every window is
complete. This module is only the run.
"""

from __future__ import annotations

from typing import Any

from .economy_probes_v3 import boundary_probes
from .economy_schedule_v3 import (
    ACTIVATED_SEATS,
    ACTIVATION_REFERRERS,
    HEIGHTS,
    LAST_TICK,
    SEATS,
    accrue,
    activate,
    base,
    cycle_at,
    exercise,
    uptime_record,
)


def cycle_events(seat_id: int, cycle_index: int, tick: int) -> list[dict[str, Any]]:
    """One seat's cycle: evaluate, exercise, and accrue its referral benefit.

    The accrual is unconditional and direct-mint, so it needs no evaluation and
    no exercise. An unreferred seat's accrual is accepted and reaches the
    unreferred performance pool, which is what consumes the channel exactly.
    """
    return [
        base(seat_id, cycle_index, uptime_record(tick)),
        exercise(seat_id, cycle_index),
        accrue(seat_id, cycle_index),
    ]


def activations() -> list[dict[str, Any]]:
    """Every seat, in ascending height order.

    Version three refuses an activation height below the highest already
    recorded, because a real activation executes inside the block that includes
    it. Emitting the activations in seat order satisfies that by construction,
    since the heights are non-decreasing in seat order by definition.
    """
    return [
        activate(seat_id, ACTIVATION_REFERRERS[seat_id], HEIGHTS[seat_id])
        for seat_id in ACTIVATED_SEATS
    ]


def population_events() -> list[dict[str, Any]]:
    """The complete staggered run, without the adversarial block."""
    generated: list[dict[str, Any]] = []
    for tick in range(LAST_TICK + 1):
        for seat_id in range(SEATS):
            cycle_index = cycle_at(seat_id, tick)
            if cycle_index is not None:
                generated.extend(cycle_events(seat_id, cycle_index, tick))
    return generated


def events() -> list[dict[str, Any]]:
    """Build the complete staggered population run and its boundary probes."""
    return activations() + population_events() + boundary_probes()
