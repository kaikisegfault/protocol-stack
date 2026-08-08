"""Shared founder-economy-manifest-v2 and simulator-v2 test inputs."""

from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path
from typing import Any

from simulation.founder_economy_v2.manifest import Manifest, load_manifest_file

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "test-vectors" / "founder-economy-manifest-v2.json"
VECTORS_PATH = ROOT / "test-vectors" / "founder-economy-manifest-v2.txt"
SIMULATOR_VECTORS_PATH = ROOT / "test-vectors" / "founder-economy-simulator-v2.txt"
EVENTS_PATH = (
    ROOT / "simulation" / "founder_economy_v2" / "fixtures" / "research-events-v2.json"
)
V1_MANIFEST_PATH = ROOT / "test-vectors" / "founder-economy-manifest-v1.json"

FULL_WINDOW = 86_400
MET_BOUNDARY = 64_800
FAILED_BOUNDARY = 64_799


def manifest() -> Manifest:
    return load_manifest_file(MANIFEST_PATH)


def manifest_value() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def v1_manifest_value() -> dict[str, Any]:
    return json.loads(V1_MANIFEST_PATH.read_text(encoding="utf-8"))


def mutated(**changes: Any) -> dict[str, Any]:
    """Return the accepted manifest with top-level fields replaced."""
    value = manifest_value()
    value.update(copy.deepcopy(changes))
    return value


_IDS = itertools.count()


def _event(kind: str, **fields: Any) -> dict[str, Any]:
    return {"id": f"e{next(_IDS):04d}", "kind": kind, **fields}


def activate(seat_id: int, referrer: int | None = None) -> dict[str, Any]:
    return _event("activate_seat", seat_id=seat_id, referrer_seat_id=referrer)


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


def evaluate_alone(seat_id: int, cycle_index: int, uptime: int = FULL_WINDOW,
                   window: int | None = None) -> dict[str, Any]:
    """Evaluate a seat against a record naming only that seat."""
    return evaluate(
        seat_id,
        cycle_index,
        record(cycle_index if window is None else window, {seat_id: uptime}),
    )


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


def codes(result: dict[str, Any]) -> list[str]:
    return [item["result"] for item in result["records"]]


def custody(result: dict[str, Any], key: str) -> int:
    return int(result["final_state"]["typed_custody"].get(key, "0"))


def simulator_vectors() -> dict[str, str]:
    return _read_vectors(SIMULATOR_VECTORS_PATH)


def vectors() -> dict[str, str]:
    """Parse the normative `key=value` vector file."""
    return _read_vectors(VECTORS_PATH)


def _read_vectors(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition("=")
        if not separator:
            raise ValueError(f"malformed vector line: {line!r}")
        values[key] = value
    return values
