#!/usr/bin/env python3
"""Derive and check the economy scenario suite's version-four vectors.

Version four is one scenario: a staggered population run over every seat's 731
cycles through `economy-transition-v9`, the contract the chain executes. The
other three scenarios of versions one to three bind models this version does
not change, and `economy-scenario-suite-v3.txt` still carries them.

Every value but the state roots must agree with `expected_v4.py`'s walk, which
imports nothing from `simulation/`, before it is compared with the file. The
file fails closed both ways: a derived key it does not carry and a recorded
key nothing derives are both failures.

`--emit` prints the vector lines instead of checking them. It refuses to print
anything while the live run and the closed form disagree, so an emitted file is
never a record of a disagreement.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import expected_v4
from checker import Checker, read_vectors
from population_checks_v4 import check_population

from simulation.scenarios.economy_population_v4 import PopulationRun

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "test-vectors" / "economy-scenario-suite-v4.txt"


class Emitter(Checker):
    """A checker that records what it would compare instead of comparing it."""

    def __init__(self) -> None:
        super().__init__({})
        self.lines: list[str] = []

    def equal(self, key: str, derived: object) -> None:
        self.lines.append(f"{key}={derived}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", type=Path, default=DEFAULT)
    parser.add_argument("--emit", action="store_true")
    arguments = parser.parse_args()

    run = PopulationRun().run()
    if arguments.emit:
        emitter = Emitter()
        check_population(emitter, expected_v4, run)
        if emitter.failures:
            for failure in emitter.failures:
                sys.stderr.write(f"disagreement: {failure}\n")
            return 1
        sys.stdout.write("\n".join(emitter.lines) + "\n")
        return 0

    check = Checker(read_vectors(arguments.vectors))
    check_population(check, expected_v4, run)
    check.require_full_coverage()
    for failure in check.failures:
        sys.stderr.write(f"vector mismatch: {failure}\n")
    if check.failures:
        return 1
    sys.stdout.write(
        f"derived and matched {check.checked} economy scenario suite v4 vectors "
        f"over {run.observed.windows_checked} windows and "
        f"{sum(run.observed.results.values())} transactions; every value but the "
        f"state roots agrees with a closed-form walk of the current contract\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
