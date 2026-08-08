#!/usr/bin/env python3
"""Independently derive and check the escrow payout vectors.

Independence matters here because the vector file was produced from the model.
Every transition is therefore re-derived in `walk.py`, which shares no code with
the model: it keeps plain dictionaries, re-implements the specification's
ordered rejection conditions, recomputes the founder-economy state digest from
the accepted `D(L) || JCS(value)` rule with its own helper, and carries the
escrow caps as literals converted from the Founder Constitution rather than
imported from the model's contract module.

The binding is checked one level further. The opening custody the fixture claims
is only as good as the economy state digest it names, so this verifier runs the
founder-economy simulator of the selected version on its own accepted fixture
and requires that digest to be the one the escrow fixture binds. A fixture
carrying an invented economy state would satisfy the model, which only
recomputes consistency, and would fail here.

`--version` selects the accepted escrow contract. Version one binds
`founder-economy-simulator-v1` and version two binds
`founder-economy-simulator-v2`; both are accepted, and each must reproduce its
own vector file exactly. Running one version against the other's fixture fails
at the bind, which is the compatibility boundary ADR 0026 records.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import walk as w
from checker import Checker, read_vectors
from contract_checks import (
    check_binding_vectors,
    check_constitution_anchors,
    check_contract_agreement,
    check_schema_vectors,
)
from scenario_checks import (
    ROOT,
    check_atomicity_vectors,
    check_negative_vectors,
    check_scenario_vectors,
)

from simulation.escrow_payout import contract as c
from simulation.escrow_payout.engine import simulate

from simulation.escrow_payout.validation import load_events_file

ECONOMY: dict[str, dict[str, str]] = {
    "v1": {
        "events": "simulation/founder_economy/fixtures/research-events-v1.json",
        "manifest": "test-vectors/founder-economy-manifest-v1.json",
    },
    "v2": {
        "events": "simulation/founder_economy_v2/fixtures/research-events-v2.json",
        "manifest": "test-vectors/founder-economy-manifest-v2.json",
    },
}


def economy_binding(version: str) -> tuple[str, dict[str, int]]:
    """Run the accepted economy fixture and read its three escrow custody keys.

    The import is selected here rather than at module scope so each version
    loads only its own economy model, and neither can silently satisfy the
    other's binding.
    """
    paths = ECONOMY[version]
    if version == "v1":
        from simulation.founder_economy.engine import simulate as economy_simulate
        from simulation.founder_economy.manifest import load_manifest_file
        from simulation.founder_economy.validation import load_events_file as events
    else:
        from simulation.founder_economy_v2.engine import simulate as economy_simulate
        from simulation.founder_economy_v2.manifest import load_manifest_file
        from simulation.founder_economy_v2.validation import load_events_file as events

    economy = economy_simulate(
        load_manifest_file(ROOT / paths["manifest"]),
        events(ROOT / paths["events"]),
    )
    custody = economy["final_state"]["typed_custody"]
    opening = {
        escrow: int(custody.get(f"{escrow}:global", "0")) for escrow in w.ESCROWS
    }
    return economy["state_digest"], opening


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", choices=sorted(w.SPECS), default="v1")
    parser.add_argument("--vectors", type=Path, default=None)
    arguments = parser.parse_args()

    spec = w.SPECS[arguments.version]
    binding = c.BINDINGS[arguments.version]
    vectors = arguments.vectors or (
        ROOT / "test-vectors" / f"escrow-payout-{arguments.version}.txt"
    )

    economy_digest, opening = economy_binding(arguments.version)

    events_path = ROOT / spec.events_file
    result = simulate(load_events_file(events_path), binding=binding)
    walk = w.Walk(spec=spec)
    walk.run(w.load_events(events_path))

    check = Checker(read_vectors(vectors))
    check_schema_vectors(check, spec)
    check_constitution_anchors(check)
    compared = check_contract_agreement(binding, binding.escrow_caps, spec)
    check_binding_vectors(check, economy_digest, opening, events_path, spec)
    check_scenario_vectors(check, result, walk)
    check_negative_vectors(check, result["records"])
    check_atomicity_vectors(check, result["records"])
    check.require_full_coverage()

    for failure in check.failures:
        sys.stderr.write(f"vector mismatch: {failure}\n")
    if check.failures:
        return 1

    sys.stdout.write(
        f"derived and matched {check.checked} escrow payout {arguments.version} "
        f"vectors; the independent walk agrees with the model on all "
        f"{len(result['records'])} events, {compared} escrow caps match the "
        f"Founder Constitution, and the bound opening custody is the output of "
        f"an accepted founder-economy-simulator-{arguments.version} run\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
