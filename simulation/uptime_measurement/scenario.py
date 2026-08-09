"""A deterministic scenario exercising the pipeline end to end.

Four seats over two complete windows plus the finalising window. The population
is chosen so every credit path is reached: a seat that answers everything, a
seat that misses challenges, a seat that fails an assigned duty, and a seat
activated too late to be in scope for the first window.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.cycle_boundary.model import CycleBoundary

from . import contract as c
from .model import DutyReport, UptimeMeasurement
from .slots import is_selected

AI_KEY = "ecosystem-ai-key-v1"

# Seat 0 activates at genesis and is in scope from window 1. Seat 3 activates
# inside window 1, so it is out of scope there and in scope from window 2.
ACTIVATIONS: tuple[tuple[int, int], ...] = (
    (0, 0),
    (1, 10),
    (2, 11),
    (3, c.CYCLE_BLOCKS + 5),
)

PERFECT_SEAT = 0
SILENT_SEAT = 1
DUTY_FAILING_SEAT = 2
LATE_SEAT = 3

# The slot seat 2's assigned duty fails in, during window 1.
DUTY_FAILURE_SLOT = 3


def build_schedule() -> CycleBoundary:
    schedule = CycleBoundary()
    for seat_id, height in ACTIVATIONS:
        schedule.record_activation(seat_id, height)
    return schedule


def beacon_for(height: int) -> str:
    """A stand-in for the canonical state root at `height - 1`.

    The model treats the beacon as opaque, so a deterministic fixture value is
    enough to exercise selection. What the beacon must be on a real chain is
    fixed by the specification, not by this scenario.
    """
    return f"{height:064x}"


@dataclass
class ScenarioResult:
    model: UptimeMeasurement
    schedule: CycleBoundary
    windows_run: tuple[int, ...]


def run(windows: int = 2, stop_height: int | None = None) -> ScenarioResult:
    """Execute `windows` complete windows plus enough of the next to finalise.

    Seat 0 answers every challenge. Seat 1 answers none. Seat 2 answers every
    challenge but fails an assigned validator duty in one slot. Seat 3 joins in
    window 2.

    `stop_height` halts the run early. A height inside window 2 leaves window 1
    closed but not final, which is the only state a dispute may be filed in and
    is therefore what the containment vectors are taken against.
    """
    schedule = build_schedule()
    model = UptimeMeasurement(ai_key=AI_KEY)
    model.bind_schedule(schedule, schedule.state_digest())

    last_height = (windows + c.DISPUTE_WINDOW_WINDOWS + 1) * c.CYCLE_BLOCKS
    if stop_height is not None:
        last_height = stop_height
    for height in range(0, last_height + 1):
        window = height // c.CYCLE_BLOCKS
        beacon = beacon_for(height)
        scope = set(model.in_scope(window))

        reports: list[DutyReport] = []
        if DUTY_FAILING_SEAT in scope and window == 1:
            slot = (height % c.CYCLE_BLOCKS) // c.SLOT_BLOCKS
            if slot == DUTY_FAILURE_SLOT and height % c.SLOT_BLOCKS == 0:
                reports.append(DutyReport(DUTY_FAILING_SEAT, "VALIDATOR", False))

        model.execute_block(height, beacon, tuple(reports))

        for seat_id in sorted(scope):
            if seat_id == SILENT_SEAT:
                continue
            if is_selected(seat_id, height, beacon):
                model.submit_response(seat_id, height, True)

    return ScenarioResult(model, schedule, tuple(range(1, windows + 1)))
