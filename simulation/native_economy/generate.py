#!/usr/bin/env python3
"""Generate reviewable SplitMix64-v1 research inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.native_economy.scenario import generate_scenario
from simulation.native_economy.domain import MAX_U64


def _u64(text: str) -> int:
    value = int(text, 0)
    if not 0 <= value <= MAX_U64:
        raise argparse.ArgumentTypeError("seed must be a u64")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("seed", type=_u64)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("events", type=Path)
    parser.add_argument("--rounds", type=int, default=8)
    arguments = parser.parse_args()

    try:
        manifest, events = generate_scenario(arguments.seed, arguments.rounds)
    except ValueError as error:
        parser.error(str(error))
    options = {"sort_keys": True, "indent": 2, "allow_nan": False}
    arguments.manifest.write_text(
        json.dumps(manifest, **options) + "\n",
        encoding="utf-8",
    )
    arguments.events.write_text(
        json.dumps(events, **options) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
