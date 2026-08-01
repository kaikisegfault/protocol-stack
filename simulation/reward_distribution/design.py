#!/usr/bin/env python3
"""Build the reviewed reward-distribution study design."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economic_stress.envelope_design import design_value as envelope_design
from simulation.participation.domain import checked_mul

DESIGN = "REWARD-CAP(6x2x16x20^2;5x8+4)-v1"
MECHANISMS = ["proportional", "participant_cap", "principal_cap"]


def _participant(principal: str) -> dict[str, str]:
    return {"principal": principal, "payout_account": principal}


def _scenario(
    scenario_id: str,
    participants: dict[str, str],
    contributions: list[dict[str, int]],
) -> dict:
    if len(contributions) != 8:
        raise AssertionError("trajectory must have eight contribution epochs")
    return {
        "scenario_id": scenario_id,
        "role": "node",
        "budget": 100,
        "participants": {
            key: _participant(value) for key, value in sorted(participants.items())
        },
        "contributions": contributions,
    }


def _scenarios() -> list[dict]:
    return [
        _scenario(
            "honest_variance",
            {"worker_a": "alpha", "worker_b": "beta"},
            [
                {"worker_a": 20, "worker_b": 20},
                {"worker_a": 20, "worker_b": 1},
                {"worker_a": 1, "worker_b": 20},
                {"worker_a": 15, "worker_b": 5},
                {"worker_a": 5, "worker_b": 15},
                {"worker_a": 13, "worker_b": 7},
                {"worker_a": 7, "worker_b": 13},
                {"worker_a": 10, "worker_b": 10},
            ],
        ),
        _scenario(
            "intermittent_availability",
            {"worker_a": "alpha", "worker_b": "beta", "worker_c": "gamma"},
            [
                {"worker_a": 20, "worker_b": 20},
                {"worker_a": 20, "worker_c": 10},
                {"worker_b": 20, "worker_c": 10},
                {"worker_a": 20},
                {"worker_b": 20},
                {"worker_c": 20},
                {"worker_a": 20, "worker_b": 20, "worker_c": 20},
                {"worker_a": 10, "worker_b": 10, "worker_c": 10},
            ],
        ),
        _scenario(
            "population_change",
            {"worker_a": "alpha", "worker_b": "beta", "worker_c": "gamma"},
            [
                {"worker_a": 15, "worker_b": 10},
                {"worker_a": 20, "worker_b": 5},
                {"worker_a": 5, "worker_b": 20},
                {"worker_a": 15, "worker_b": 10, "worker_c": 5},
                {"worker_a": 20, "worker_b": 10, "worker_c": 10},
                {"worker_a": 10, "worker_c": 20},
                {"worker_a": 5, "worker_c": 20},
                {"worker_c": 20},
            ],
        ),
        _scenario(
            "dominant_unsplit",
            {"dominant": "alpha", "baseline": "beta"},
            [{"dominant": 18, "baseline": 2} for _ in range(8)],
        ),
        _scenario(
            "dominant_split",
            {
                "dominant_a": "alpha",
                "dominant_b": "alpha",
                "baseline": "beta",
            },
            [
                {"dominant_a": 9, "dominant_b": 9, "baseline": 2}
                for _ in range(8)
            ],
        ),
    ]


def build_design() -> dict:
    survivors = envelope_design()["survivor_case_ids"]
    point_count = 1
    for factor in (len(survivors), 2, 16, 20, 20):
        result = checked_mul(point_count, factor)
        if result is None:
            raise OverflowError("support point count exceeds u64")
        point_count = result
    return {
        "schema": "protocol-stack/reward-distribution-design/v1",
        "design": DESIGN,
        "mechanisms": MECHANISMS,
        "cap_ratio": {"numerator": 3, "denominator": 4},
        "history_epochs": 4,
        "contribution_epochs": 8,
        "drain_epochs": 4,
        "survivor_case_ids": survivors,
        "roles": ["validator", "node"],
        "weight_range": {"minimum": 1, "maximum": 16, "step": 1},
        "unit_range": {"minimum": 1, "maximum": 20, "step": 1},
        "support_point_count": point_count,
        "scenarios": _scenarios(),
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
