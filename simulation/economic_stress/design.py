"""Reviewed OA(27,13,3,2) construction and factor mapping."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from typing import Any

DESIGN_NAME = "OA(27,13,3,2)-GF3-v1"
DESIGN_SCHEMA = "protocol-stack/economic-stress-design/v1"

FACTORS = (
    "issuance_amount",
    "fee_volume",
    "fee_reward_parts",
    "reward_budget_per_role",
    "validator_weight",
    "node_weight",
    "validator_minimum_bond",
    "penalty_parts",
    "activation_delay_epochs",
    "exit_unbond_delay_epochs",
    "authority_threshold",
    "authority_delay_epochs",
    "correlated_shock",
)

FACTOR_LEVELS: dict[str, tuple[int | str, ...]] = {
    "issuance_amount": (100, 500, 2000),
    "fee_volume": (20, 200, 800),
    "fee_reward_parts": (0, 5, 10),
    "reward_budget_per_role": (100, 500, 1500),
    "validator_weight": (1, 4, 16),
    "node_weight": (1, 4, 16),
    "validator_minimum_bond": (100, 500, 1000),
    "penalty_parts": (0, 1, 5),
    "activation_delay_epochs": (1, 2, 4),
    "exit_unbond_delay_epochs": (1, 2, 4),
    "authority_threshold": (1, 2, 3),
    "authority_delay_epochs": (1, 2, 4),
    "correlated_shock": ("nominal", "degraded", "severe"),
}

DIRECTIONS = tuple(
    [(1, left, right) for left in range(3) for right in range(3)]
    + [(0, 1, right) for right in range(3)]
    + [(0, 0, 1)]
)

SHOCK_MEMBERS = {
    "nominal": (3, 0),
    "degraded": (2, 1),
    "severe": (1, 2),
}


@dataclass(frozen=True)
class Configuration:
    case_index: int
    case_id: str
    levels: tuple[int, ...]
    values: dict[str, int | str]
    honest_available: int
    compromised_available: int

    def report_value(self) -> dict[str, Any]:
        return {
            "case_index": self.case_index,
            "case_id": self.case_id,
            "levels": list(self.levels),
            "values": dict(self.values),
            "honest_available": self.honest_available,
            "compromised_available": self.compromised_available,
        }


def matrix() -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(
            (row[0] * direction[0]
             + row[1] * direction[1]
             + row[2] * direction[2])
            % 3
            for direction in DIRECTIONS
        )
        for row in product(range(3), repeat=3)
    )


def configurations() -> tuple[Configuration, ...]:
    result = []
    for index, levels in enumerate(matrix()):
        values = {
            factor: FACTOR_LEVELS[factor][level]
            for factor, level in zip(FACTORS, levels, strict=True)
        }
        shock = str(values["correlated_shock"])
        honest, compromised = SHOCK_MEMBERS[shock]
        result.append(
            Configuration(
                case_index=index,
                case_id=f"case_{index:02d}",
                levels=levels,
                values=values,
                honest_available=honest,
                compromised_available=compromised,
            )
        )
    return tuple(result)


def design_value() -> dict[str, Any]:
    return {
        "schema": DESIGN_SCHEMA,
        "design": DESIGN_NAME,
        "factors": list(FACTORS),
        "factor_levels": {
            factor: list(FACTOR_LEVELS[factor]) for factor in FACTORS
        },
        "directions": [list(direction) for direction in DIRECTIONS],
        "matrix": [list(row) for row in matrix()],
    }


def assert_design() -> None:
    values = matrix()
    if len(DIRECTIONS) != 13 or len(values) != 27:
        raise AssertionError("economic stress design has the wrong shape")
    if any(len(row) != 13 or any(level not in {0, 1, 2} for level in row)
           for row in values):
        raise AssertionError("economic stress design contains an invalid level")
    for column in range(13):
        counts = [sum(row[column] == level for row in values) for level in range(3)]
        if counts != [9, 9, 9]:
            raise AssertionError("economic stress factor is not balanced")
    for left, right in combinations(range(13), 2):
        counts = {
            pair: sum((row[left], row[right]) == pair for row in values)
            for pair in product(range(3), repeat=2)
        }
        if set(counts.values()) != {3}:
            raise AssertionError("economic stress factor pair is not balanced")
