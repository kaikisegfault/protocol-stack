#!/usr/bin/env python3
"""Run the exact economic solvency and concentration envelope study."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.authority.domain import domain_digest
from simulation.economic_stress.envelope_design import (
    BUDGET_MAX,
    BUDGET_MIN,
    CONCENTRATION_CELL_COUNT,
    DESIGN_NAME,
    FINANCIAL_CELL_COUNT,
    JOINT_COMBINATION_COUNT,
    WEIGHT_MAX,
    WEIGHT_MIN,
    assert_design,
    design_value,
    survivor_configurations,
)
from simulation.economic_stress.envelope_projection import (
    checked_add,
    concentration_cell,
    financial_profile,
)


def run_study() -> dict[str, Any]:
    assert_design()
    financial_profiles: list[dict[str, Any]] = []
    concentration_cells: list[dict[str, Any]] = []
    family_summaries: list[dict[str, Any]] = []
    financial_totals = {name: 0 for name in ("solvent", "mixed", "insolvent")}
    concentration_totals = {
        name: 0 for name in ("within_bound", "mixed", "concentrated")
    }

    for config in survivor_configurations():
        profiles = [
            financial_profile(config, budget)
            for budget in range(BUDGET_MIN, BUDGET_MAX + 1)
        ]
        cells = [
            concentration_cell(config, validator_weight, node_weight)
            for validator_weight in range(WEIGHT_MIN, WEIGHT_MAX + 1)
            for node_weight in range(WEIGHT_MIN, WEIGHT_MAX + 1)
        ]
        family_financial = _profile_counts(profiles)
        family_concentration = _cell_counts(cells)
        _accumulate(financial_totals, family_financial)
        _accumulate(concentration_totals, family_concentration)
        financial_profiles.extend(profiles)
        concentration_cells.extend(cells)
        family_summaries.append(
            {
                "family_id": config.case_id,
                "configuration": config.report_value(),
                "financial_classification_counts": family_financial,
                "concentration_classification_counts": family_concentration,
            }
        )

    if sum(financial_totals.values()) != FINANCIAL_CELL_COUNT:
        raise AssertionError("financial study cell count changed")
    if sum(concentration_totals.values()) != CONCENTRATION_CELL_COUNT:
        raise AssertionError("concentration study cell count changed")
    design = design_value()
    report = {
        "schema": "protocol-stack/economic-envelope-study/v1",
        "design": DESIGN_NAME,
        "design_digest": domain_digest(
            "protocol-stack:economic-envelope:design-v1",
            design,
        ),
        "family_count": len(family_summaries),
        "financial_cell_count": FINANCIAL_CELL_COUNT,
        "concentration_cell_count": CONCENTRATION_CELL_COUNT,
        "joint_combination_count": JOINT_COMBINATION_COUNT,
        "financial_classification_counts": financial_totals,
        "concentration_classification_counts": concentration_totals,
        "family_summaries": family_summaries,
        "financial_profiles": financial_profiles,
        "concentration_cells": concentration_cells,
    }
    report["study_digest"] = domain_digest(
        "protocol-stack:economic-envelope:study-v1",
        report,
    )
    return report


def _profile_counts(profiles: list[dict[str, Any]]) -> dict[str, int]:
    result = {name: 0 for name in ("solvent", "mixed", "insolvent")}
    for profile in profiles:
        _accumulate(result, profile["classification_counts"])
    return result


def _cell_counts(cells: list[dict[str, Any]]) -> dict[str, int]:
    result = {name: 0 for name in ("within_bound", "mixed", "concentrated")}
    for cell in cells:
        name = cell["classification"]
        result[name] = checked_add(result[name], 1)
    return result


def _accumulate(target: dict[str, int], source: dict[str, int]) -> None:
    for name, count in source.items():
        target[name] = checked_add(target[name], count)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_study()
    text = json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if arguments.output is None:
        sys.stdout.write(text)
    else:
        arguments.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
