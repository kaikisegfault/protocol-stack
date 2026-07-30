#!/usr/bin/env python3
"""Run one participation-v1 manifest and event trace."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.participation.engine import simulate
from simulation.participation.validation import load_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("events")
    parser.add_argument("--output")
    arguments = parser.parse_args()
    result = simulate(load_json(arguments.manifest), load_json(arguments.events))
    text = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        Path(arguments.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
