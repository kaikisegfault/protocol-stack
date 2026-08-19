#!/usr/bin/env python3
"""Independently derive and check the economy-transition-v7 vectors.

Every recorded value is rederived twice wherever both sources can reach it:
once from `expected.py`, which imports nothing from `simulation/`, and once from
a live run of the model.

Four groups reach a third source rather than a second opinion of this file. The
manifest digest, the renamed channel identifier, and the five base permission
legs are checked against `test-vectors/founder-economy-manifest-v3.txt`. Each
predecessor economy-tree construction is required to reproduce its own version's
accepted empty root before the six-way non-collision rests on it.

`docs/engineering/verification.md`'s three rules apply: a boolean vector may only
be true, a name asserts no more than its value establishes, and a claim is
checked against something other than itself.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(REPOSITORY_ROOT))

from checker import Checker, read_vectors
from settlement_checks import (
    check_accumulation_cap,
    check_collection,
    check_conservation,
    check_cycles,
    check_two_sets,
)
from state_checks import (
    check_cycle_assignment,
    check_entry_kinds,
    check_entry_shape,
    check_genesis,
    check_recovery_pool,
    check_storage_bounds,
)
from version_checks import (
    check_identity,
    check_manifest_binding,
    check_non_collision,
    check_predecessor_restatements,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vectors", required=True, type=Path)
    arguments = parser.parse_args()

    recorded = read_vectors(arguments.vectors)
    check = Checker(recorded)

    accepted = REPOSITORY_ROOT / "test-vectors"

    check_identity(check)
    check_manifest_binding(check, accepted)
    check_predecessor_restatements(check, accepted)
    check_non_collision(check)
    check_entry_kinds(check)
    check_recovery_pool(check)
    check_cycle_assignment(check)
    check_entry_shape(check)
    check_genesis(check)
    check_storage_bounds(check)
    check_cycles(check)
    check_two_sets(check)
    check_collection(check)
    check_conservation(check)
    check_accumulation_cap(check)

    check.require_full_coverage()
    if check.failures:
        for failure in check.failures:
            print(f"FAIL {failure}", file=sys.stderr)
        print(f"{len(check.failures)} vector failures", file=sys.stderr)
        return 1
    print(f"economy-transition-v7: {check.checked} vectors verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
