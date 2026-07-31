#!/usr/bin/env python3
"""Replay a strict authority simulation manifest and event list."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.authority.engine import simulate
from simulation.authority.validation import InputError, load_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("events", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    try:
        result = simulate(
            load_json(arguments.manifest),
            load_json(arguments.events),
        )
    except InputError as error:
        parser.error(str(error))
    text = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if arguments.output is None:
        sys.stdout.write(text)
    else:
        arguments.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
