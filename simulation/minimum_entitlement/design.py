#!/usr/bin/env python3
"""Build the reviewed minimum-entitlement study design."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economic_stress.envelope_design import design_value as envelope_design
from simulation.participation.domain import checked_mul
from simulation.reward_distribution.design import MECHANISMS
from simulation.reward_distribution.model import credits_for_scores

DESIGN = "MINIMUM-ENTITLEMENT(80x16x3x3;m0..5)-v1"
FLOOR_FAMILIES = ["zero", "per_participant", "work_proportional"]
ROLES = ["validator", "node"]


def _product(values) -> int:
    result = 1
    for value in values:
        checked = checked_mul(result, value)
        if checked is None:
            raise OverflowError("design count exceeds u64")
        result = checked
    return result


def retained_coordinates() -> list[dict]:
    result = []
    for configuration in envelope_design()["survivor_configurations"]:
        budget = configuration["values"]["reward_budget_per_role"]
        for role in ROLES:
            for weight in range(1, 17):
                credit = credits_for_scores(
                    budget, {"dominant_00": 16 * weight, "honest": 1}
                )
                if credit.get("honest", 0) == 0:
                    result.append(
                        {
                            "case_id": configuration["case_id"],
                            "role": role,
                            "budget": budget,
                            "selected_weight": weight,
                        }
                    )
    if len(result) != 80:
        raise AssertionError("zero-entitlement coordinate count changed")
    return result


def build_design() -> dict:
    coordinates = retained_coordinates()
    coordinate_count = len(coordinates)
    zero_forms = _product((coordinate_count, 16, len(MECHANISMS)))
    family_forms = _product((zero_forms, 6))
    common_ceiling = min(item["budget"] // 17 for item in coordinates)
    if common_ceiling != 5:
        raise AssertionError("common floor ceiling changed")
    return {
        "schema": "protocol-stack/minimum-entitlement-design/v1",
        "design": DESIGN,
        "mechanisms": MECHANISMS,
        "floor_families": FLOOR_FAMILIES,
        "retained_coordinates": coordinates,
        "retained_coordinate_count": coordinate_count,
        "dominant_total_units": 16,
        "honest_units": 1,
        "identity_count_range": {"minimum": 1, "maximum": 16, "step": 1},
        "common_floor_range": {"minimum": 0, "maximum": common_ceiling, "step": 1},
        "zero_family_form_count": zero_forms,
        "positive_family_form_count": family_forms,
        "evaluated_form_count": zero_forms + 2 * family_forms,
        "zero_floor_cross_check_count": zero_forms,
        "cross_check_identity_counts": [1, 2, 16],
        "cross_check_floors": [0, 1, 5],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    text = json.dumps(
        build_design(), sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False
    ) + "\n"
    if arguments.output is None:
        sys.stdout.write(text)
    else:
        arguments.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
