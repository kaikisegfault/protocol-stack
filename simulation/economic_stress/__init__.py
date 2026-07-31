"""Deterministic cross-simulator M2 economic stress study."""

from .design import configurations, design_value
from .study import run_study

__all__ = ["configurations", "design_value", "run_study"]
