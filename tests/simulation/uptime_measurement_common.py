"""Shared uptime-measurement-v1 test fixtures.

The scenario runs dominate the cost of testing this model: a window is 28,800
blocks with a selection digest per in-scope seat at every height, and most
fixtures use one run for a single assertion. Each shape is therefore executed
once and copied per use.

Copying is sound because a run is deterministic and takes no input from the
test. The tests that exist to prove that determinism build their own runs rather
than calling `scenario`.
"""

from __future__ import annotations

import copy
from functools import lru_cache

from simulation.common.canonical import CodedError
from simulation.uptime_measurement import contract as c
from simulation.uptime_measurement.model import UptimeMeasurement
from simulation.uptime_measurement.scenario import (
    AI_KEY,
    ScenarioResult,
    beacon_for,
    build_schedule,
    run,
)

__all__ = [
    "AI_KEY",
    "advance",
    "beacon_for",
    "bound_model",
    "build_schedule",
    "code_of",
    "open_dispute_window",
    "scenario",
]


@lru_cache(maxsize=None)
def _run_once(windows: int, stop_height: int | None) -> ScenarioResult:
    return run(windows=windows, stop_height=stop_height)


def scenario(windows: int = 1, stop_height: int | None = None) -> ScenarioResult:
    """A deterministic scenario run, executed once per shape and copied per use."""
    return copy.deepcopy(_run_once(windows, stop_height))


def open_dispute_window() -> UptimeMeasurement:
    """A run whose window 1 has closed and whose dispute window is still open.

    The only state a dispute may be filed in, and the one the containment
    assertions are taken against.
    """
    return scenario(windows=1, stop_height=2 * c.CYCLE_BLOCKS + 1).model


def bound_model() -> UptimeMeasurement:
    """A model bound to the scenario's activation schedule, with no blocks run."""
    schedule = build_schedule()
    model = UptimeMeasurement(ai_key=AI_KEY)
    model.bind_schedule(schedule, schedule.state_digest())
    return model


def advance(model: UptimeMeasurement, through: int) -> None:
    start = 0 if model.height is None else model.height + 1
    for height in range(start, through + 1):
        model.execute_block(height, beacon_for(height))


def code_of(action) -> str:
    """The result code an action produces, or ACCEPTED when it does not reject."""
    try:
        action()
    except CodedError as error:
        return error.code
    return "ACCEPTED"
