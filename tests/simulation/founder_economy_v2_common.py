"""Shared founder-economy-manifest-v2 test inputs."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from simulation.founder_economy_v2.manifest import Manifest, load_manifest_file

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "test-vectors" / "founder-economy-manifest-v2.json"
VECTORS_PATH = ROOT / "test-vectors" / "founder-economy-manifest-v2.txt"
V1_MANIFEST_PATH = ROOT / "test-vectors" / "founder-economy-manifest-v1.json"


def manifest() -> Manifest:
    return load_manifest_file(MANIFEST_PATH)


def manifest_value() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def v1_manifest_value() -> dict[str, Any]:
    return json.loads(V1_MANIFEST_PATH.read_text(encoding="utf-8"))


def mutated(**changes: Any) -> dict[str, Any]:
    """Return the accepted manifest with top-level fields replaced."""
    value = manifest_value()
    value.update(copy.deepcopy(changes))
    return value


def vectors() -> dict[str, str]:
    """Parse the normative `key=value` vector file."""
    values: dict[str, str] = {}
    for line in VECTORS_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition("=")
        if not separator:
            raise ValueError(f"malformed vector line: {line!r}")
        values[key] = value
    return values
