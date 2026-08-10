"""Shared founder-economy-simulator-v3 test inputs.

Version three's events carry an activation height and its records must cover a
window's whole in-scope set, so the builders here derive both rather than
letting a test supply a window by hand. A test that wants a wrong window asks
for one explicitly, which is what keeps an accidental mismatch from looking like
an intentional probe.

The research scenario run is executed once and copied per use, matching the
convention `uptime_measurement_common` established: the run is deterministic and
takes no input from a test, and the tests that exist to prove that determinism
build their own runs rather than calling the cached one.
"""

from __future__ import annotations

import copy
import itertools
from functools import lru_cache
from pathlib import Path
from typing import Any

from simulation.cycle_boundary.grid import first_cycle_window, window_for_cycle
from simulation.founder_economy_v2.manifest import Manifest, load_manifest_file
from simulation.founder_economy_v3 import contract as c
from simulation.founder_economy_v3.engine import simulate
from simulation.founder_economy_v3.validation import load_events_file

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "test-vectors" / "founder-economy-manifest-v2.json"
VECTORS_PATH = ROOT / "test-vectors" / "founder-economy-simulator-v3.txt"
EVENTS_PATH = (
    ROOT / "simulation" / "founder_economy_v3" / "fixtures" / "research-events-v3.json"
)

FULL_WINDOW = c.CYCLE_TARGET_SECONDS
MET_BOUNDARY = c.ACTIVITY_THRESHOLD_SECONDS
FAILED_BOUNDARY = c.ACTIVITY_THRESHOLD_SECONDS - 1
CYCLE_BLOCKS = c.CYCLE_BLOCKS

_IDS = itertools.count()


def manifest() -> Manifest:
    return load_manifest_file(MANIFEST_PATH)


def _event(kind: str, **fields: Any) -> dict[str, Any]:
    return {"id": f"e{next(_IDS):04d}", "kind": kind, **fields}


def activate(
    seat_id: int, referrer: int | None = None, height: int = 0
) -> dict[str, Any]:
    return _event(
        "activate_seat",
        seat_id=seat_id,
        referrer_seat_id=referrer,
        activation_height=str(height),
    )


def record(window: int, entries: dict[int, int]) -> dict[str, Any]:
    """Build one cycle uptime record from a seat-to-uptime mapping."""
    return {
        "cycle_window": window,
        "entries": [
            {"seat_id": seat_id, "uptime_seconds": uptime}
            for seat_id, uptime in entries.items()
        ],
    }


def evaluate(
    seat_id: int,
    cycle_index: int,
    uptime_record: dict[str, Any] | None,
) -> dict[str, Any]:
    return _event(
        "evaluate_base_permission",
        seat_id=seat_id,
        cycle_index=cycle_index,
        cycle_uptime_record=uptime_record,
    )


def window_of(height: int, cycle_index: int) -> int:
    """The window a seat activated at this height holds for this cycle."""
    return window_for_cycle(height, cycle_index)


def scoped_record(
    heights: dict[int, int],
    window: int,
    uptimes: dict[int, int],
) -> dict[str, Any]:
    """A complete record for a window, covering exactly its in-scope seats.

    Seats not named in `uptimes` are credited the full window, so a test states
    only the measurements it cares about and still produces a record version
    three accepts.
    """
    return record(
        window,
        {
            seat_id: uptimes.get(seat_id, FULL_WINDOW)
            for seat_id in sorted(heights)
            if first_cycle_window(heights[seat_id]) <= window
        },
    )


def evaluate_scoped(
    heights: dict[int, int],
    seat_id: int,
    cycle_index: int,
    uptimes: dict[int, int] | None = None,
    window: int | None = None,
) -> dict[str, Any]:
    """Evaluate a seat against a complete record for its own cycle's window.

    `window` overrides the derived one so a test can present a wrong window on
    purpose; the record still covers whatever window it names.
    """
    target = window_of(heights[seat_id], cycle_index) if window is None else window
    return evaluate(seat_id, cycle_index, scoped_record(heights, target, uptimes or {}))


def accrue(seat_id: int, cycle_index: int) -> dict[str, Any]:
    return _event("accrue_referral", seat_id=seat_id, cycle_index=cycle_index)


def exercise(seat_id: int, cycle_index: int) -> dict[str, Any]:
    return _event("exercise_permission", seat_id=seat_id, cycle_index=cycle_index)


def direct(
    channel: str = "liquidity_mining",
    amount: str = "1000000000",
    beneficiary: str = "b1",
    eligible: bool = True,
    decision: str | None = None,
    bound_amount: str | None = None,
) -> dict[str, Any]:
    decision_id = decision or f"d{next(_IDS):04d}"
    return _event(
        "direct_issue",
        channel=channel,
        decision_id=decision_id,
        beneficiary_id=beneficiary,
        amount_atomic=amount,
        eligibility_result={
            "channel": channel,
            "decision_id": decision_id,
            "beneficiary_id": beneficiary,
            "amount_atomic": bound_amount or amount,
            "eligible": eligible,
        },
    )


def run(events: list[dict[str, Any]]) -> dict[str, Any]:
    return simulate(manifest(), events)


def codes(result: dict[str, Any]) -> list[str]:
    return [item["result"] for item in result["records"]]


def custody(result: dict[str, Any], key: str) -> int:
    return int(result["final_state"]["typed_custody"].get(key, "0"))


@lru_cache(maxsize=None)
def _scenario_once() -> dict[str, Any]:
    return simulate(manifest(), load_events_file(EVENTS_PATH))


def scenario() -> dict[str, Any]:
    """The research scenario result, executed once and copied per use."""
    return copy.deepcopy(_scenario_once())


def scenario_events() -> list[dict[str, Any]]:
    return load_events_file(EVENTS_PATH)


def vectors() -> dict[str, str]:
    """Parse the normative `key=value` vector file."""
    values: dict[str, str] = {}
    for line in VECTORS_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition("=")
        if not separator:
            raise ValueError(f"malformed vector line: {line!r}")
        values[key] = value
    return values
