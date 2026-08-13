#!/usr/bin/env python3
"""Independently derive and check the economy-transition-v2 vectors.

Every recorded value is rederived twice wherever both sources can reach it: once
from `expected.py`, which imports nothing from `simulation/` and restates the
accepted version-one field tables and the Founder Constitution's figures by
hand, and once from a live run of the model. A value both sources agree on has
been reached from the accepted documents and from the implementation
independently.

The compatibility section goes further and compares against a third source: the
recorded bytes of `test-vectors/protocol-primitives-v1.txt`. The claim that a
version-two kind-1 transaction is the accepted version-one transfer is only
evidence if the accepted file is what it is checked against.
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
from encoding_checks import (
    check_admission,
    check_compatibility,
    check_envelope,
    check_model_mapping,
    check_receipt,
    check_result_codes,
)
from state_checks import (
    check_genesis,
    check_state_keys,
    check_state_root,
    check_storage_bounds,
    check_trees,
    check_version_one_restatement,
    check_winners,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vectors", required=True, type=Path)
    arguments = parser.parse_args()

    recorded = read_vectors(arguments.vectors)
    check = Checker(recorded)

    check_envelope(check)
    # The accepted version-one vectors are a fixed artifact of this repository,
    # not a parameter of the file under test, so they are located from the
    # verifier rather than from the input path.
    check_compatibility(check, REPOSITORY_ROOT / "test-vectors")
    check_admission(check)
    check_result_codes(check)
    check_model_mapping(check)
    check_receipt(check)
    check_state_keys(check)
    check_trees(check)
    check_version_one_restatement(check, REPOSITORY_ROOT / "test-vectors")
    check_state_root(check)
    check_genesis(check)
    check_winners(check)
    check_storage_bounds(check)

    check.require_full_coverage()
    if check.failures:
        for failure in check.failures:
            print(f"FAIL {failure}", file=sys.stderr)
        print(f"{len(check.failures)} vector failures", file=sys.stderr)
        return 1
    print(f"economy-transition-v2: {check.checked} vectors verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
