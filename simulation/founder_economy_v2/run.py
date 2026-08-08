#!/usr/bin/env python3
"""Run a version-two Founder Economy simulation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.founder_economy_v2.engine import simulate
from simulation.founder_economy_v2.manifest import ManifestError, load_manifest_file
from simulation.founder_economy_v2.validation import InputError, load_events_file

DEFAULT_MANIFEST = (
    Path(__file__).resolve().parents[2]
    / "test-vectors"
    / "founder-economy-manifest-v2.json"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("events", type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()

    try:
        manifest = load_manifest_file(arguments.manifest)
        result = simulate(manifest, load_events_file(arguments.events))
    except (InputError, ManifestError, OSError) as error:
        parser.error(str(error))

    text = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if arguments.output is None:
        sys.stdout.write(text)
    else:
        arguments.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
