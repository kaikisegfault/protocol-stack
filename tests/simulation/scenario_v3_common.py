"""Shared version-three scenario suite test inputs.

The complete 731-cycle population run is the dominant cost in this suite because
the economy simulator clones state per event. It is executed once here and
deep-copied per use, so a test module pays for it once and the escrow drain
reuses that same result rather than producing a second one. That is the
convention `uptime_measurement_common` and `founder_economy_v3_common` already
follow.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from simulation.scenarios.suite import V3, run_economy, run_escrow

ROOT = Path(__file__).resolve().parents[2]
VECTORS_PATH = ROOT / "test-vectors" / "economy-scenario-suite-v3.txt"

_ECONOMY: dict[str, Any] | None = None
_ESCROW: dict[str, Any] | None = None


def vectors(path: Path = VECTORS_PATH) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            key, _, value = stripped.partition("=")
            values[key] = value
    return values


def economy_result() -> dict[str, Any]:
    """A private copy of the population run, so a caller may mutate it."""
    global _ECONOMY
    if _ECONOMY is None:
        _ECONOMY = run_economy(V3)
    return copy.deepcopy(_ECONOMY)


def escrow_result() -> dict[str, Any]:
    global _ESCROW
    if _ESCROW is None:
        _ESCROW = run_escrow(economy_result(), V3)
    return copy.deepcopy(_ESCROW)


def records_by_id(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {record["event_id"]: record for record in result["records"]}
