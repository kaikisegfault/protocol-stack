"""Deterministic adversarial threshold-authority scenario generation."""

from __future__ import annotations

from typing import Any

from .scenario_control import add_control_lifecycle
from .scenario_operational import add_operational_attacks
from .scenario_support import Builder, SplitMix64


def generate_scenario(seed: int) -> tuple[dict, list[dict]]:
    builder = _build(seed)
    return builder.manifest_value, builder.events


def scenario_targets(seed: int) -> dict[str, dict[str, Any]]:
    return _build(seed).targets


def _build(seed: int) -> Builder:
    builder = Builder(seed)
    issue_target, register_target = add_operational_attacks(builder)
    add_control_lifecycle(builder, issue_target, register_target)
    return builder


__all__ = ["SplitMix64", "generate_scenario", "scenario_targets"]
