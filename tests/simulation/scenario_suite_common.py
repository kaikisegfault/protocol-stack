"""Shared scenario suite test inputs.

The complete 731-cycle population run is the dominant cost in this suite
because the economy simulator clones state per event. It is cached here so a
test module executes it once, and the escrow drain reuses that same result
rather than producing a second one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from simulation.scenarios.suite import run_economy, run_escrow

ROOT = Path(__file__).resolve().parents[2]
VECTORS_PATH = ROOT / "test-vectors" / "economy-scenario-suite-v1.txt"

_ECONOMY: dict[str, Any] | None = None
_ESCROW: dict[str, Any] | None = None


def vectors() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in VECTORS_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            key, _, value = stripped.partition("=")
            values[key] = value
    return values


def economy_result() -> dict[str, Any]:
    global _ECONOMY
    if _ECONOMY is None:
        _ECONOMY = run_economy()
    return _ECONOMY


def escrow_result() -> dict[str, Any]:
    global _ESCROW
    if _ESCROW is None:
        _ESCROW = run_escrow(economy_result())
    return _ESCROW


def codes(result: dict[str, Any]) -> list[str]:
    return [record["result"] for record in result["records"]]


def rejected(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [record for record in result["records"] if not record["accepted"]]


def total(amounts: Any) -> int:
    """Sum a canonical decimal-string map's values as exact integers."""
    return sum(int(value) for value in amounts.values())
