"""Shared native-economy simulator test inputs."""

from __future__ import annotations

import copy
from pathlib import Path

from simulation.native_economy.validation import load_json

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "simulation" / "native_economy" / "fixtures"


def fixture() -> tuple[dict, list[dict]]:
    return (
        load_json(FIXTURES / "research-manifest-v1.json"),
        load_json(FIXTURES / "research-events-v1.json"),
    )


def base_manifest() -> dict:
    manifest, _ = fixture()
    return manifest


def event(kind: str, actor: str, **fields) -> dict:
    return {
        "id": fields.pop("id", "test_event"),
        "height": fields.pop("height", 0),
        "kind": kind,
        "actor": actor,
        **fields,
    }


def changed(value: dict) -> dict:
    return copy.deepcopy(value)
