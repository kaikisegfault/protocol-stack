#!/usr/bin/env python3
"""Independently derive and check the economy scenario suite vectors.

Independence here does not come from a second walk of four models. It comes
from `expected.py`, which imports nothing from `simulation/`, carries the
Founder Constitution's tables as its own literals, and re-derives each
scenario's totals by arithmetic: three seats over 731 cycles issue
`3 x 731 x 17_100_000_000` into the venture escrow, and the complete
concentrated sale is the block schedule summed directly.

Every monetary total is required to agree with that derivation before it is
compared with the recorded file, so a vector only the model reproduces is a
failure rather than evidence. Digests and counts that depend on the supplied
research decisions are derived from the live runs and pinned by the file, as
the four model verifiers already do.

The join is checked one level further: the escrow scenario's bound digest must
be the state digest the population run itself produced, so the escrows are
proved to be drained of exactly what those three seats issued into them.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import expected as x
from checker import Checker, read_vectors
from economy_checks import check_economy
from escrow_checks import check_escrow
from market_checks import check_routing, check_seats

from simulation.scenarios.routing_population import empty_cycles
from simulation.scenarios.suite import ROOT, run_suite


def check_denomination(check: Checker) -> None:
    check.equal("denomination.decimal_places", x.DECIMAL_PLACES)
    check.equal(
        "denomination.atomic_units_per_display_unit",
        x.ATOMIC_UNITS_PER_DISPLAY_UNIT,
    )
    check.equal("maximum_supply_atomic", x.MAXIMUM_SUPPLY_ATOMIC)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--vectors",
        type=Path,
        default=ROOT / "test-vectors" / "economy-scenario-suite-v1.txt",
    )
    arguments = parser.parse_args()

    results = run_suite()
    check = Checker(read_vectors(arguments.vectors))

    check_denomination(check)
    check_economy(check, results["economy_population"])
    check_seats(check, results["seat_concentration"])
    check_routing(check, results["routing_population"], len(empty_cycles()))
    check_escrow(
        check, results["escrow_drain"], results["economy_population"]
    )
    check.require_full_coverage()

    for failure in check.failures:
        sys.stderr.write(f"vector mismatch: {failure}\n")
    if check.failures:
        return 1

    events = sum(len(result["records"]) for result in results.values())
    sys.stdout.write(
        f"derived and matched {check.checked} scenario suite vectors across "
        f"{events} events in four scenarios; every monetary total agrees with a "
        f"closed-form derivation from the Founder Constitution, and the escrow "
        f"drain is bound to the population run's own state digest\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
