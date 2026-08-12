"""Shared version-two scenario suite test inputs.

The complete 731-cycle population run is the dominant cost in this suite because
the economy simulator clones state per event. It is executed once here and
deep-copied per use, so a test module pays for it once and the escrow drain
reuses that same result rather than producing a second one. That is the
convention `scenario_v3_common` and `uptime_measurement_common` already follow;
this module predates it and rebuilt the run in three separate `setUpClass`
bodies.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from simulation.scenarios.suite import V2, run_economy, run_escrow

ROOT = Path(__file__).resolve().parents[2]

_ECONOMY: dict[str, Any] | None = None
_ESCROW: dict[str, Any] | None = None


def economy_result() -> dict[str, Any]:
    """A private copy of the population run, so a caller may mutate it."""
    global _ECONOMY
    if _ECONOMY is None:
        _ECONOMY = run_economy(V2)
    return copy.deepcopy(_ECONOMY)


def escrow_result() -> dict[str, Any]:
    global _ESCROW
    if _ESCROW is None:
        _ESCROW = run_escrow(economy_result(), V2)
    return copy.deepcopy(_ESCROW)
