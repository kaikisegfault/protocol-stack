#!/usr/bin/env python3
"""Run the multi-year and adversarial scenario suite."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.scenarios.suite import SCENARIO_NAMES, run_suite, summarize


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=SCENARIO_NAMES)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--full",
        action="store_true",
        help="emit complete results instead of the recorded summary",
    )
    arguments = parser.parse_args()

    results = run_suite()
    if arguments.scenario is not None:
        results = {arguments.scenario: results[arguments.scenario]}

    value = results if arguments.full else summarize(results)
    text = json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if arguments.output is None:
        sys.stdout.write(text)
    else:
        arguments.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
