"""Run the four scenarios and collect their results.

The escrow drain binds the economy population run's final state, so the
economy scenario is executed once and its result is threaded into the escrow
scenario rather than recomputed. That ordering is the join: the escrows are
drained of exactly what the population run issued into them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..escrow_payout.engine import simulate as escrow_simulate
from ..founder_economy.engine import simulate as economy_simulate
from ..founder_economy.manifest import load_manifest_file
from ..founder_seats.engine import simulate as seat_simulate
from ..revenue_routing.engine import simulate as routing_simulate
from . import (
    economy_population,
    escrow_drain,
    routing_population,
    seat_concentration,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "test-vectors" / "founder-economy-manifest-v1.json"

SCENARIO_NAMES = (
    "economy_population",
    "seat_concentration",
    "routing_population",
    "escrow_drain",
)


def run_economy() -> dict[str, Any]:
    return economy_simulate(
        load_manifest_file(MANIFEST_PATH), economy_population.events()
    )


def run_seats() -> dict[str, Any]:
    return seat_simulate(seat_concentration.events())


def run_routing() -> dict[str, Any]:
    return routing_simulate(routing_population.events())


def run_escrow(economy_result: dict[str, Any]) -> dict[str, Any]:
    return escrow_simulate(escrow_drain.events(economy_result["final_state"]))


def run_suite() -> dict[str, dict[str, Any]]:
    """Run every scenario in the fixed order the vectors record."""
    economy = run_economy()
    return {
        "economy_population": economy,
        "seat_concentration": run_seats(),
        "routing_population": run_routing(),
        "escrow_drain": run_escrow(economy),
    }


def summarize(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Reduce the suite to the digests and counts the vector file records."""
    summary: dict[str, Any] = {}
    for name in (name for name in SCENARIO_NAMES if name in results):
        result = results[name]
        records = result["records"]
        summary[name] = {
            "schema": result["schema"],
            "event_count": len(records),
            "accepted_count": sum(1 for record in records if record["accepted"]),
            "rejected_count": sum(1 for record in records if not record["accepted"]),
            "events_digest": result["events_digest"],
            "trace_digest": result["trace_digest"],
            "state_digest": result["state_digest"],
            "result_digest": result["result_digest"],
        }
    return summary


__all__ = [
    "MANIFEST_PATH",
    "ROOT",
    "SCENARIO_NAMES",
    "run_economy",
    "run_escrow",
    "run_routing",
    "run_seats",
    "run_suite",
    "summarize",
]
