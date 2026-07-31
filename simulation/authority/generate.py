#!/usr/bin/env python3
"""Generate one deterministic authority research scenario."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.authority.domain import MAX_U64
from simulation.authority.scenario import generate_scenario


def _u64(text: str) -> int:
    value = int(text, 0)
    if not 0 <= value <= MAX_U64:
        raise argparse.ArgumentTypeError("seed must be a u64")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=_u64, default=0)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    arguments = parser.parse_args()
    manifest, events = generate_scenario(arguments.seed)
    arguments.manifest.write_text(
        json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    arguments.events.write_text(
        json.dumps(events, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
