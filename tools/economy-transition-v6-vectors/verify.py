#!/usr/bin/env python3
"""Independently derive and check the economy-transition-v6 vectors.

Every recorded value is rederived twice wherever both sources can reach it:
once from `expected.py`, which imports nothing from `simulation/`, and once from
a live run of the model.

Four sections go further and compare against a third source. The kind-1 identity
and the signer derivation are checked against
`test-vectors/protocol-primitives-v1.txt` — the second because it is the accepted
version-one account derivation with its subject moved, so a restatement that
drifted would otherwise agree only with itself. Each predecessor economy-tree
construction is required to reproduce its own version's accepted empty root
before the six-way non-collision rests on it. And the imported settlement is
required to reproduce the two assignment records
`test-vectors/economy-transition-v3.txt` already fixes.

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
from encoding_checks import (
    check_admission,
    check_compatibility,
    check_envelope,
    check_hub_messages,
    check_model_mapping,
    check_receipt,
    check_result_codes,
)
from registry_checks import (
    check_derivations,
    check_posture,
    check_registry,
    check_settlement_is_version_three,
    check_verified_user,
)
from state_checks import (
    check_genesis,
    check_predecessor_restatements,
    check_state_keys,
    check_state_root,
    check_storage_bounds,
    check_trees,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vectors", required=True, type=Path)
    arguments = parser.parse_args()

    recorded = read_vectors(arguments.vectors)
    check = Checker(recorded)

    accepted = REPOSITORY_ROOT / "test-vectors"

    check_envelope(check)
    check_compatibility(check, accepted)
    check_admission(check)
    check_hub_messages(check)
    check_result_codes(check)
    check_model_mapping(check)
    check_receipt(check)
    check_state_keys(check)
    check_trees(check)
    check_predecessor_restatements(check, accepted)
    check_state_root(check)
    check_genesis(check)
    check_derivations(check, accepted)
    check_registry(check)
    check_posture(check)
    check_verified_user(check)
    check_settlement_is_version_three(check, accepted)
    check_storage_bounds(check)

    check.require_full_coverage()
    if check.failures:
        for failure in check.failures:
            print(f"FAIL {failure}", file=sys.stderr)
        print(f"{len(check.failures)} vector failures", file=sys.stderr)
        return 1
    print(f"economy-transition-v6: {check.checked} vectors verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
