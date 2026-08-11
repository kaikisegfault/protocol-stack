"""Run the four scenarios and collect their results.

The escrow drain binds the economy population run's final state, so the
economy scenario is executed once and its result is threaded into the escrow
scenario rather than recomputed. That ordering is the join: the escrows are
drained of exactly what the population run issued into them.

Three suite versions are accepted. They differ in the economy contract scenarios
one and four bind, and in the shape of the population generator that follows
from it. Scenarios two and three are shared without a parameter, because the
Founder Seat sale and revenue routing models carry no supply or channel figure
and are identical under every economy contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from ..escrow_payout import contract as escrow_contract
from ..escrow_payout.engine import simulate as escrow_simulate
from ..founder_seats.engine import simulate as seat_simulate
from ..revenue_routing.engine import simulate as routing_simulate
from . import (
    economy_population,
    economy_population_v2,
    economy_population_v3,
    escrow_drain,
    routing_population,
    seat_concentration,
)

ROOT = Path(__file__).resolve().parents[2]

SCENARIO_NAMES = (
    "economy_population",
    "seat_concentration",
    "routing_population",
    "escrow_drain",
)


@dataclass(frozen=True)
class SuiteBinding:
    """One accepted suite version and the economy contract it exercises."""

    version: str
    manifest_path: Path
    population: ModuleType
    escrow_binding: escrow_contract.Binding

    def economy_simulate(self, manifest: Any, events: Any) -> dict[str, Any]:
        if self.version == "v1":
            from ..founder_economy.engine import simulate

            return simulate(manifest, events)
        if self.version == "v2":
            from ..founder_economy_v2.engine import simulate

            return simulate(manifest, events)
        if self.version == "v3":
            from ..founder_economy_v3.engine import simulate

            return simulate(manifest, events)
        raise AssertionError(f"no economy engine for suite version {self.version}")

    def load_manifest(self) -> Any:
        if self.version == "v1":
            from ..founder_economy.manifest import load_manifest_file

            return load_manifest_file(self.manifest_path)
        # Versions two and three load the same accepted artifact through the
        # same loader. Version three re-versioned no channel, cap, leg, or
        # denomination, so a third loader for a byte-identical manifest would be
        # a third implementation of one contract with nothing keeping the three
        # equal.
        from ..founder_economy_v2.manifest import load_manifest_file

        return load_manifest_file(self.manifest_path)


V1 = SuiteBinding(
    version="v1",
    manifest_path=ROOT / "test-vectors" / "founder-economy-manifest-v1.json",
    population=economy_population,
    escrow_binding=escrow_contract.V1,
)

V2 = SuiteBinding(
    version="v2",
    manifest_path=ROOT / "test-vectors" / "founder-economy-manifest-v2.json",
    population=economy_population_v2,
    escrow_binding=escrow_contract.V2,
)

V3 = SuiteBinding(
    version="v3",
    manifest_path=ROOT / "test-vectors" / "founder-economy-manifest-v2.json",
    population=economy_population_v3,
    escrow_binding=escrow_contract.V3,
)

BINDINGS: dict[str, SuiteBinding] = {
    V1.version: V1,
    V2.version: V2,
    V3.version: V3,
}

# Retained so version one's accepted callers keep their existing import.
MANIFEST_PATH = V1.manifest_path


def run_economy(binding: SuiteBinding = V1) -> dict[str, Any]:
    return binding.economy_simulate(binding.load_manifest(), binding.population.events())


def run_seats() -> dict[str, Any]:
    return seat_simulate(seat_concentration.events())


def run_routing() -> dict[str, Any]:
    return routing_simulate(routing_population.events())


def run_escrow(
    economy_result: dict[str, Any],
    binding: SuiteBinding = V1,
) -> dict[str, Any]:
    return escrow_simulate(
        escrow_drain.events(economy_result["final_state"], binding.escrow_binding),
        binding=binding.escrow_binding,
    )


def run_suite(binding: SuiteBinding = V1) -> dict[str, dict[str, Any]]:
    """Run every scenario in the fixed order the vectors record."""
    economy = run_economy(binding)
    return {
        "economy_population": economy,
        "seat_concentration": run_seats(),
        "routing_population": run_routing(),
        "escrow_drain": run_escrow(economy, binding),
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
    "BINDINGS",
    "MANIFEST_PATH",
    "ROOT",
    "SCENARIO_NAMES",
    "SuiteBinding",
    "V1",
    "V2",
    "V3",
    "run_economy",
    "run_escrow",
    "run_routing",
    "run_seats",
    "run_suite",
    "summarize",
]
