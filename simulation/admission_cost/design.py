#!/usr/bin/env python3
"""Build the reviewed admission-cost study design."""

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

DESIGN = "ADMISSION-COST(6x2x16x20x16;8+4;L1..16)-v1"


def _product(values: tuple[int, ...]) -> int:
    result = 1
    for value in values:
        checked = checked_mul(result, value)
        if checked is None:
            raise OverflowError("design count exceeds u64")
        result = checked
    return result


def build_design() -> dict:
    survivors = envelope_design()["survivor_case_ids"]
    base_count = _product((len(survivors), 2, 16, 20))
    return {
        "schema": "protocol-stack/admission-cost-design/v1",
        "design": DESIGN,
        "mechanisms": MECHANISMS,
        "survivor_case_ids": survivors,
        "roles": ["validator", "node"],
        "dominant_total_units": 16,
        "selected_weight_range": {"minimum": 1, "maximum": 16, "step": 1},
        "honest_unit_range": {"minimum": 1, "maximum": 20, "step": 1},
        "identity_count_range": {"minimum": 1, "maximum": 16, "step": 1},
        "base_coordinate_count": base_count,
        "identity_form_count": _product((base_count, 16)),
        "trajectory": {
            "budget": 100,
            "selected_weight": 1,
            "honest_units": 1,
            "contribution_epochs": 8,
            "drain_epochs": 4,
            "strategies": ["persistent", "churn"],
        },
        "post_exit_lock_range": {"minimum": 1, "maximum": 16, "step": 1},
        "cost_models": ["zero", "per_identity_operating", "capital_time"],
        "capital_time_rounding": "ceiling",
        "bond_amount_normalization": 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    text = json.dumps(build_design(), sort_keys=True, indent=2, allow_nan=False) + "\n"
    if arguments.output is None:
        sys.stdout.write(text)
    else:
        arguments.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
