"""Shared economic-stress study test helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from simulation.authority.validation import load_json

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "simulation" / "economic_stress" / "fixtures"


def fixture(name: str) -> Any:
    return load_json(FIXTURES / name)


def contains_float(value: Any) -> bool:
    if type(value) is float:
        return True
    if type(value) is list:
        return any(contains_float(item) for item in value)
    if type(value) is dict:
        return any(contains_float(item) for item in value.values())
    return False
