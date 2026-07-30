#!/usr/bin/env python3
"""Generate deterministic participation-v1 research inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.participation.scenario import generate_scenario


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("seed", type=lambda text: int(text, 0))
    parser.add_argument("manifest", type=Path)
    parser.add_argument("events", type=Path)
    parser.add_argument("--rounds", type=int, default=4)
    arguments = parser.parse_args()
    manifest, events = generate_scenario(arguments.seed, arguments.rounds)
    arguments.manifest.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    arguments.events.write_text(
        json.dumps(events, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
