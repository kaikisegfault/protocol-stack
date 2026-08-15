#!/usr/bin/env python3
"""Independently derive and check the economy-transition-v5 vectors.

Every recorded value is rederived twice wherever both sources can reach it:
once from `expected.py`, which imports nothing from `simulation/`, and once
from a live run of the model.

Four sections go further and compare against a third source. The kind-1
identity is checked against `test-vectors/protocol-primitives-v1.txt`. Each of
the four predecessor root constructions is required to reproduce its own
version's accepted vectors before the five-way non-collision rests on it. The
settlement — imported from version three through version four — is required to
reproduce the values `test-vectors/economy-transition-v3.txt` records. And the
whole file is read a second time against
`test-vectors/economy-transition-v4.txt`, which is what turns version five's
central negative claim into a check: everything not classified as revised must
hold version four's exact value.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(REPOSITORY_ROOT))

from carryover import check_carryover
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
    check_registry,
    check_seat_bound,
    check_self_referral,
    check_settlement_is_version_three,
    check_state_entries,
)
from revision_checks import (
    check_add_address_body,
    check_add_address_message,
    check_message_layouts_are_version_four,
    check_recovery,
    check_squatting,
    check_version_four_separation,
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
    check_registry(check)
    check_state_entries(check)
    check_seat_bound(check)
    check_self_referral(check)
    check_settlement_is_version_three(check, accepted)
    check_storage_bounds(check)
    check_add_address_body(check, accepted)
    check_add_address_message(check)
    check_message_layouts_are_version_four(check)
    check_squatting(check)
    check_recovery(check)
    check_version_four_separation(check, accepted)
    check_carryover(check, accepted, arguments.vectors)

    check.require_full_coverage()
    if check.failures:
        for failure in check.failures:
            print(f"FAIL {failure}", file=sys.stderr)
        print(f"{len(check.failures)} vector failures", file=sys.stderr)
        return 1
    print(f"economy-transition-v5: {check.checked} vectors verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
