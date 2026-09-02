#!/usr/bin/env python3
"""Independently derive and check the economy-transition-v8 vectors.

Every recorded value is derived twice wherever both sources can reach it: once
from `expected.py`, which imports nothing from `simulation/`, and once from a
live run of the model.

Three groups reach a third source rather than a second opinion of this file. The
manifest digest is checked against `test-vectors/founder-economy-manifest-v3.txt`.
Each predecessor root construction must differ from version eight's separately,
because distinct labels are strings rather than a chain. And the settlement
claim is checked against version *seven's* accepted model, which is the only way
"the carrier changed no settlement" can be evidence rather than an assertion.

`--emit` writes the vector file instead of checking it. It runs the same
derivations through the same agreement gate, so it can only write a value both
sources already produce alike; what it removes is the transcription step, not
the evidence.

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
from schedule_checks import (
    check_expiry,
    check_schedule,
    check_settlement_is_unchanged,
)
from selection_checks import check_exclusion, check_preimage, check_rate
from state_checks import (
    check_absent_record,
    check_entry_refusals,
    check_entry_space,
    check_kind_space,
    check_result_codes,
)
from transition_checks import check_containment, check_dispute, check_response
from version_checks import (
    check_genesis,
    check_identity,
    check_manifest_binding,
    check_non_collision,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vectors", required=True, type=Path)
    parser.add_argument(
        "--emit",
        action="store_true",
        help="write the vector file from the derivations instead of checking it",
    )
    arguments = parser.parse_args()

    recorded = {} if arguments.emit else read_vectors(arguments.vectors)
    check = Checker(recorded, emit=arguments.emit)

    accepted = REPOSITORY_ROOT / "test-vectors"

    check_identity(check)
    check_manifest_binding(check, accepted)
    check_genesis(check)
    check_non_collision(check)
    check_entry_space(check)
    check_entry_refusals(check)
    check_absent_record(check)
    check_kind_space(check)
    check_result_codes(check)
    check_preimage(check)
    check_exclusion(check)
    check_rate(check)
    check_response(check)
    check_dispute(check)
    check_containment(check)
    check_expiry(check)
    check_schedule(check)
    check_settlement_is_unchanged(check)

    check.require_full_coverage()
    if check.failures:
        for failure in check.failures:
            print(f"FAIL {failure}", file=sys.stderr)
        print(f"{len(check.failures)} vector failures", file=sys.stderr)
        return 1
    if arguments.emit:
        written = check.write(arguments.vectors)
        print(f"economy-transition-v8: {written} vectors written")
        return 0
    print(f"economy-transition-v8: {check.checked} vectors verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
