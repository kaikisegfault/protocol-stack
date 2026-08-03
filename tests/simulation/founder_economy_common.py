"""Shared Founder Economy simulator test inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from simulation.founder_economy.manifest import Manifest, load_manifest_file

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "test-vectors" / "founder-economy-manifest-v1.json"
VECTORS_PATH = ROOT / "test-vectors" / "founder-economy-manifest-v1.txt"
FIXTURES = ROOT / "simulation" / "founder_economy" / "fixtures"


def manifest() -> Manifest:
    return load_manifest_file(MANIFEST_PATH)


def manifest_value() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def research_events() -> list[dict[str, Any]]:
    return json.loads((FIXTURES / "research-events-v1.json").read_text(encoding="utf-8"))


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


def activate(seat_id: int, referrer: int | None = None, **fields: Any) -> dict[str, Any]:
    return {
        "id": fields.pop("id", f"activate-{seat_id}"),
        "kind": "activate_seat",
        "seat_id": seat_id,
        "referrer_seat_id": referrer,
    }


def activity(seat_id: int, cycle_index: int, active: bool = True) -> dict[str, Any]:
    return {"seat_id": seat_id, "cycle_index": cycle_index, "active": active}


def allocation(
    seat_id: int,
    cycle_index: int,
    entries: list[tuple[int, int]],
) -> dict[str, Any]:
    return {
        "seat_id": seat_id,
        "cycle_index": cycle_index,
        "allocations": [
            {"seat_id": recipient, "amount_atomic": str(amount)}
            for recipient, amount in entries
        ],
    }


def evaluate_base(
    seat_id: int,
    cycle_index: int,
    *,
    active: bool = True,
    performance: dict[str, Any] | None = None,
    activity_result: dict[str, Any] | None = ...,  # type: ignore[assignment]
    event_id: str | None = None,
) -> dict[str, Any]:
    result = activity(seat_id, cycle_index, active) if activity_result is ... else activity_result
    return {
        "id": event_id or f"base-{seat_id}-{cycle_index}",
        "kind": "evaluate_base_permission",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
        "activity_result": result,
        "performance_allocation": performance,
    }


def evaluate_referral(
    seat_id: int,
    cycle_index: int,
    *,
    active: bool = True,
    inactive_result: dict[str, Any] | None = None,
    activity_result: dict[str, Any] | None = ...,  # type: ignore[assignment]
    event_id: str | None = None,
) -> dict[str, Any]:
    result = activity(seat_id, cycle_index, active) if activity_result is ... else activity_result
    return {
        "id": event_id or f"referral-{seat_id}-{cycle_index}",
        "kind": "evaluate_referral_permission",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
        "activity_result": result,
        "inactive_referral_result": inactive_result,
    }


def exercise(
    seat_id: int,
    cycle_index: int,
    kind: str = "base",
    *,
    event_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": event_id or f"exercise-{seat_id}-{cycle_index}-{kind}",
        "kind": "exercise_permission",
        "seat_id": seat_id,
        "cycle_index": cycle_index,
        "permission_kind": kind,
    }


def direct(
    channel: str,
    decision_id: str,
    beneficiary_id: str,
    amount: int,
    *,
    eligible: bool | None = True,
    binding: dict[str, Any] | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] | None = None
    if eligible is not None:
        result = {
            "channel": channel,
            "decision_id": decision_id,
            "beneficiary_id": beneficiary_id,
            "amount_atomic": str(amount),
            "eligible": eligible,
        }
        result.update(binding or {})
    return {
        "id": event_id or decision_id,
        "kind": "direct_issue",
        "channel": channel,
        "decision_id": decision_id,
        "beneficiary_id": beneficiary_id,
        "amount_atomic": str(amount),
        "eligibility_result": result,
    }
