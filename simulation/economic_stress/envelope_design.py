"""Reviewed exact-grid design around economic-stress survivor families."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .design import Configuration, configurations

DESIGN_NAME = "EXACT-ENVELOPE(6;2401x1451;16x16;20^4)-v1"
DESIGN_SCHEMA = "protocol-stack/economic-envelope-design/v1"
SURVIVOR_INDICES = (0, 1, 9, 15, 21, 24)

ISSUANCE_MIN = 100
ISSUANCE_MAX = 2_500
BUDGET_MIN = 50
BUDGET_MAX = 1_500
WEIGHT_MIN = 1
WEIGHT_MAX = 16
UNIT_MIN = 1
UNIT_MAX = 20

ISSUANCE_COUNT = ISSUANCE_MAX - ISSUANCE_MIN + 1
BUDGET_COUNT = BUDGET_MAX - BUDGET_MIN + 1
WEIGHT_COUNT = WEIGHT_MAX - WEIGHT_MIN + 1
ROLE_COMBINATION_COUNT = (UNIT_MAX - UNIT_MIN + 1) ** 2
JOINT_COMBINATION_COUNT = ROLE_COMBINATION_COUNT ** 2
FINANCIAL_CELL_COUNT = len(SURVIVOR_INDICES) * ISSUANCE_COUNT * BUDGET_COUNT
CONCENTRATION_CELL_COUNT = len(SURVIVOR_INDICES) * WEIGHT_COUNT**2


def survivor_configurations() -> tuple[Configuration, ...]:
    broad = configurations()
    return tuple(broad[index] for index in SURVIVOR_INDICES)


def with_values(config: Configuration, **updates: int) -> Configuration:
    values = dict(config.values)
    unknown = set(updates) - set(values)
    if unknown:
        raise ValueError(f"unknown configuration values: {sorted(unknown)}")
    values.update(updates)
    return replace(config, values=values)


def _range_value(minimum: int, maximum: int) -> dict[str, int]:
    return {"minimum": minimum, "maximum": maximum, "step": 1}


def design_value() -> dict[str, Any]:
    survivors = survivor_configurations()
    return {
        "schema": DESIGN_SCHEMA,
        "design": DESIGN_NAME,
        "survivor_case_ids": [config.case_id for config in survivors],
        "survivor_configurations": [config.report_value() for config in survivors],
        "issuance_range": _range_value(ISSUANCE_MIN, ISSUANCE_MAX),
        "budget_range": _range_value(BUDGET_MIN, BUDGET_MAX),
        "weight_range": _range_value(WEIGHT_MIN, WEIGHT_MAX),
        "contribution_unit_range": _range_value(UNIT_MIN, UNIT_MAX),
        "role_combination_count": ROLE_COMBINATION_COUNT,
        "joint_combination_count": JOINT_COMBINATION_COUNT,
        "financial_cell_count": FINANCIAL_CELL_COUNT,
        "concentration_cell_count": CONCENTRATION_CELL_COUNT,
    }


def assert_design() -> None:
    survivors = survivor_configurations()
    if tuple(config.case_index for config in survivors) != SURVIVOR_INDICES:
        raise AssertionError("economic envelope survivor order changed")
    if len({config.case_id for config in survivors}) != len(SURVIVOR_INDICES):
        raise AssertionError("economic envelope survivor identifiers repeat")
    if ISSUANCE_COUNT != 2_401 or BUDGET_COUNT != 1_451:
        raise AssertionError("economic envelope financial range changed")
    if WEIGHT_COUNT != 16:
        raise AssertionError("economic envelope weight range changed")
    if ROLE_COMBINATION_COUNT != 400 or JOINT_COMBINATION_COUNT != 160_000:
        raise AssertionError("economic envelope contribution support changed")
    if FINANCIAL_CELL_COUNT != 20_903_106:
        raise AssertionError("economic envelope financial cell count changed")
    if CONCENTRATION_CELL_COUNT != 1_536:
        raise AssertionError("economic envelope concentration cell count changed")
    for config in survivors:
        threshold = int(config.values["authority_threshold"])
        if config.honest_available < threshold:
            raise AssertionError("survivor authority is unavailable")
        if config.compromised_available >= threshold:
            raise AssertionError("survivor authority is captured")
