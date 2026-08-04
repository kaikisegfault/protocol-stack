#!/usr/bin/env python3
"""Independently derive and check the revenue routing vectors.

Independence matters here because the vector file was produced from the model.
Every share is therefore rederived with the naive `numerator * amount / 100`
form in `walk.py`, which shares no code with the contract module's
overflow-free decomposition, and the whole scenario is replayed against plain
dictionaries. The recorded file, the independent walk, and the model must all
agree, and the split percentages are checked against literals taken from the
Founder Constitution rather than from either implementation.
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
    check_anchor_vectors,
    check_constitution_anchors,
    check_contract_vectors,
    check_share_agreement,
    scan_remainders,
)
from scenario_checks import (
    EVENTS_FILE,
    ROOT,
    check_negative_vectors,
    check_scenario_vectors,
)

from simulation.revenue_routing.engine import simulate
from simulation.revenue_routing.validation import load_events_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--vectors",
        type=Path,
        default=ROOT / "test-vectors" / "revenue-routing-v1.txt",
    )
    arguments = parser.parse_args()

    events = w.load_events(ROOT / EVENTS_FILE)
    result = simulate(load_events_file(ROOT / EVENTS_FILE))

    check = Checker(read_vectors(arguments.vectors))
    check_constitution_anchors(check)
    compared = check_share_agreement(check)
    check_contract_vectors(check, scan_remainders())
    check_anchor_vectors(check)
    check_scenario_vectors(check, result, events)
    check_negative_vectors(check)
    check.require_full_coverage()

    for failure in check.failures:
        sys.stderr.write(f"vector mismatch: {failure}\n")
    if check.failures:
        return 1

    sys.stdout.write(
        f"derived and matched {check.checked} revenue routing vectors; "
        f"the independent walk agrees with the model and with {compared} "
        f"contract share computations\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
