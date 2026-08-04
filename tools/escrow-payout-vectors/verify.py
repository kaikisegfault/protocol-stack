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
is only as good as the economy state digest it names, so this verifier runs
`founder-economy-simulator-v1` on its own accepted fixture and requires that
digest to be the one the escrow fixture binds. A fixture carrying an invented
economy state would satisfy the model, which only recomputes consistency, and
would fail here.
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
    EVENTS_FILE,
    ROOT,
    check_atomicity_vectors,
    check_negative_vectors,
    check_scenario_vectors,
)

from simulation.escrow_payout import contract as c
from simulation.escrow_payout.engine import simulate
from simulation.escrow_payout.validation import load_events_file
from simulation.founder_economy.engine import simulate as economy_simulate
from simulation.founder_economy.manifest import load_manifest_file
from simulation.founder_economy.validation import load_events_file as economy_events

ECONOMY_EVENTS = "simulation/founder_economy/fixtures/research-events-v1.json"
ECONOMY_MANIFEST = "test-vectors/founder-economy-manifest-v1.json"


def economy_binding() -> tuple[str, dict[str, int]]:
    """Run the accepted economy fixture and read its three escrow custody keys."""
    economy = economy_simulate(
        load_manifest_file(ROOT / ECONOMY_MANIFEST),
        economy_events(ROOT / ECONOMY_EVENTS),
    )
    custody = economy["final_state"]["typed_custody"]
    opening = {
        escrow: int(custody.get(f"{escrow}:global", "0")) for escrow in w.ESCROWS
    }
    return economy["state_digest"], opening


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--vectors",
        type=Path,
        default=ROOT / "test-vectors" / "escrow-payout-v1.txt",
    )
    arguments = parser.parse_args()

    economy_digest, opening = economy_binding()

    events_path = ROOT / EVENTS_FILE
    result = simulate(load_events_file(events_path))
    walk = w.Walk()
    walk.run(w.load_events(events_path))

    check = Checker(read_vectors(arguments.vectors))
    check_schema_vectors(check)
    check_constitution_anchors(check)
    compared = check_contract_agreement(c, c.ESCROW_CAPS)
    check_binding_vectors(check, economy_digest, opening, events_path)
    check_scenario_vectors(check, result, walk)
    check_negative_vectors(check, result["records"])
    check_atomicity_vectors(check, result["records"])
    check.require_full_coverage()

    for failure in check.failures:
        sys.stderr.write(f"vector mismatch: {failure}\n")
    if check.failures:
        return 1

    sys.stdout.write(
        f"derived and matched {check.checked} escrow payout vectors; the "
        f"independent walk agrees with the model on all {len(result['records'])} "
        f"events, {compared} escrow caps match the Founder Constitution, and the "
        f"bound opening custody is the output of an accepted economy run\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
