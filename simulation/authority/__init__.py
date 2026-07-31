"""Deterministic M2 threshold-authority research simulator."""

from .adapter import AdapterError, build_authorized_events
from .domain import action_digest, control_digest
from .engine import simulate
from .scenario import generate_scenario

__all__ = [
    "AdapterError",
    "action_digest",
    "build_authorized_events",
    "control_digest",
    "generate_scenario",
    "simulate",
]
