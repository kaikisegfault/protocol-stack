#!/usr/bin/env python3
"""Run the cross-principal admission-cost boundary study."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.participation.domain import domain_digest

from simulation.admission_cost.crosscheck import lock_replays, participation_cross_checks
from simulation.admission_cost.design import build_design
from simulation.admission_cost.model import ratio_less
from simulation.admission_cost.support import exact_support
from simulation.admission_cost.trajectories import run_trajectories


def _maximum_lower(left: dict, right: dict) -> dict:
    if ratio_less(left["ratio"], right["ratio"]):
        return right
    if left["ratio"] == right["ratio"] and not right["inclusive"]:
        return {"ratio": left["ratio"], "inclusive": False}
    return left


def _minimum_ratio(left: dict, right: dict) -> dict:
    return left if ratio_less(left, right) else right


def _rate_range(lower: dict, upper: dict) -> bool:
    return ratio_less(lower["ratio"], upper) or (
        lower["ratio"] == upper and lower["inclusive"]
    )


def _combined_boundaries(support: dict, trajectories: dict) -> list[dict]:
    result = []
    for support_item, trajectory_item in zip(
        support["capital_rate_boundaries"],
        trajectories["capital_rate_boundaries"],
        strict=True,
    ):
        lower = _maximum_lower(
            support_item["unit_bond_deterrence_lower"],
            trajectory_item["unit_bond_deterrence_lower"],
        )
        upper = _minimum_ratio(
            support_item["unit_bond_honest_entry_upper"]["ratio"],
            trajectory_item["unit_bond_honest_entry_upper"]["ratio"],
        )
        result.append(
            {
                "post_exit_lock_epochs": support_item["post_exit_lock_epochs"],
                "unit_bond_deterrence_lower": lower,
                "unit_bond_honest_entry_upper": {"ratio": upper, "inclusive": True},
                "joint_rate_range": _rate_range(lower, upper),
            }
        )
    return result


def _combined_summaries(support: list[dict], trajectories: list[dict]) -> list[dict]:
    trajectory_by_mechanism = {item["mechanism"]: item for item in trajectories}
    results = []
    for support_item in support:
        trajectory_item = trajectory_by_mechanism[support_item["mechanism"]]
        floor = max(
            support_item["operating_deterrence_floor"],
            trajectory_item["operating_deterrence_floor"],
        )
        ceiling = min(
            support_item["smallest_honest_entry_ceiling"],
            trajectory_item["smallest_honest_entry_ceiling"],
        )
        bonds = _combined_boundaries(support_item, trajectory_item)
        results.append(
            {
                "mechanism": support_item["mechanism"],
                "operating_deterrence_floor": floor,
                "smallest_honest_entry_ceiling": ceiling,
                "operating_cost_interval": {
                    "minimum": floor,
                    "maximum": ceiling,
                    "feasible": floor <= ceiling,
                },
                "capital_rate_boundaries": bonds,
                "any_capital_rate_range": any(item["joint_rate_range"] for item in bonds),
                "objectives": {
                    "nonprofitable_split_at_floor": True,
                    "churn_deterred_at_floor": True,
                    "honest_entry_at_floor": floor <= ceiling,
                    "joint_operating_cost_range": floor <= ceiling,
                    "joint_capital_rate_range": any(
                        item["joint_rate_range"] for item in bonds
                    ),
                    "funded": trajectory_item["objectives"]["funded"],
                    "hidden_concentration": support_item["objectives"][
                        "hidden_concentration"
                    ]
                    and trajectory_item["objectives"]["hidden_concentration"],
                },
            }
        )
    return results


def run_study() -> dict:
    design = build_design()
    design_digest = domain_digest("protocol-stack:admission-cost:design-v1", design)
    support, support_equivalence = exact_support(design)
    rows, trajectory_summaries, trajectory_equivalence = run_trajectories(design)
    locks = [item for lock in range(1, 17) for item in lock_replays(lock)]
    combined = _combined_summaries(support, trajectory_summaries)
    capped = [item for item in combined if item["mechanism"] != "proportional"]
    report = {
        "schema": "protocol-stack/admission-cost-study/v1",
        "design": design["design"],
        "design_digest": design_digest,
        "exact_support": support,
        "trajectory_summaries": trajectory_summaries,
        "trajectory_results": rows,
        "combined_cost_boundaries": combined,
        "native_lock_replays": locks,
        "adapter_cross_checks": participation_cross_checks(
            design["dominant_total_units"]
        ),
        "objectives": {
            "work_invariant": all(
                item["objectives"]["work_invariant"] for item in support
            )
            and all(item["objectives"]["work_invariant"] for item in trajectory_summaries),
            "registered_scope_equivalence": support_equivalence
            and trajectory_equivalence,
            "funded": all(item["objectives"]["funded"] for item in combined),
            "lock_enforced": all(item["lock_enforced"] for item in locks),
            "hidden_concentration": all(
                item["objectives"]["hidden_concentration"] for item in combined
            ),
            "capped_joint_operating_cost_range": any(
                item["objectives"]["joint_operating_cost_range"] for item in capped
            ),
            "capped_joint_capital_rate_range": any(
                item["objectives"]["joint_capital_rate_range"] for item in capped
            ),
        },
    }
    report["study_digest"] = domain_digest(
        "protocol-stack:admission-cost:study-v1", report
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    text = json.dumps(run_study(), sort_keys=True, indent=2, allow_nan=False) + "\n"
    if arguments.output is None:
        sys.stdout.write(text)
    else:
        arguments.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
