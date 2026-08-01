#!/usr/bin/env python3
"""Run the exact reward-distribution cap and split study."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economic_stress.envelope_design import design_value as envelope_design
from simulation.participation.domain import checked_add, checked_mul, domain_digest
from simulation.reward_distribution.crosscheck import (
    cross_check_proportional,
    fund_trajectory,
)
from simulation.reward_distribution.design import build_design
from simulation.reward_distribution.model import evaluate_point, reduced_ratio, run_trajectory


def _add(left: int, right: int) -> int:
    value = checked_add(left, right)
    if value is None:
        raise OverflowError("study total exceeds u64")
    return value


def _sum(values) -> int:
    result = 0
    for value in values:
        result = _add(result, value)
    return result


def _mul(left: int, right: int) -> int:
    value = checked_mul(left, right)
    if value is None:
        raise OverflowError("study product exceeds u64")
    return value


def _identities(split: bool) -> dict[str, dict[str, str]]:
    result = {
        "baseline": {"principal": "baseline_owner", "payout_account": "baseline_owner"}
    }
    selected = ["selected_a", "selected_b"] if split else ["selected"]
    result.update(
        {
            key: {"principal": "selected_owner", "payout_account": "selected_owner"}
            for key in selected
        }
    )
    return dict(sorted(result.items()))


def _scores(units: int, baseline: int, weight: int, split: bool) -> dict[str, int]:
    if not split:
        return {"selected": _mul(units, weight), "baseline": baseline}
    first = units // 2
    second = units - first
    result = {"baseline": baseline}
    if first:
        result["selected_a"] = _mul(first, weight)
    if second:
        result["selected_b"] = _mul(second, weight)
    return result


def _selected_payout(result: dict, identities: dict) -> int:
    return _sum(
        amount
        for participant, amount in result["payouts"].items()
        if identities[participant]["principal"] == "selected_owner"
    )


def _empty_form() -> dict[str, int]:
    return {
        "point_count": 0,
        "created_credit": 0,
        "paid_credit": 0,
        "zero_payout_points": 0,
        "identity_concentration_pass_points": 0,
        "principal_concentration_pass_points": 0,
    }


def _record_form(summary: dict, result: dict) -> None:
    summary["point_count"] = _add(summary["point_count"], 1)
    summary["created_credit"] = _add(
        summary["created_credit"], result["created_credit"]
    )
    summary["paid_credit"] = _add(summary["paid_credit"], result["paid_credit"])
    summary["zero_payout_points"] = _add(
        summary["zero_payout_points"], int(result["zero_payout"])
    )
    summary["identity_concentration_pass_points"] = _add(
        summary["identity_concentration_pass_points"],
        int(result["identity_concentration"] is True),
    )
    summary["principal_concentration_pass_points"] = _add(
        summary["principal_concentration_pass_points"],
        int(result["principal_concentration"] is True),
    )


def exact_support(design: dict) -> list[dict]:
    configurations = {
        item["case_id"]: item for item in envelope_design()["survivor_configurations"]
    }
    summaries = {
        mechanism: {
            "mechanism": mechanism,
            "unsplit": _empty_form(),
            "split": _empty_form(),
            "split_advantage": {
                "positive_points": 0,
                "zero_points": 0,
                "negative_points": 0,
                "maximum_positive_amount": 0,
            },
        }
        for mechanism in design["mechanisms"]
    }
    for case_id in design["survivor_case_ids"]:
        budget = configurations[case_id]["values"]["reward_budget_per_role"]
        for _role in design["roles"]:
            for weight in range(1, 17):
                for units in range(1, 21):
                    for baseline in range(1, 21):
                        forms = {}
                        for split in (False, True):
                            identities = _identities(split)
                            scores = _scores(units, baseline, weight, split)
                            forms[split] = (identities, scores)
                        for mechanism in design["mechanisms"]:
                            unsplit = evaluate_point(
                                budget, forms[False][1], forms[False][0], mechanism
                            )
                            split = evaluate_point(
                                budget, forms[True][1], forms[True][0], mechanism
                            )
                            summary = summaries[mechanism]
                            _record_form(summary["unsplit"], unsplit)
                            _record_form(summary["split"], split)
                            advantage = _selected_payout(split, forms[True][0]) - _selected_payout(
                                unsplit, forms[False][0]
                            )
                            key = (
                                "positive_points"
                                if advantage > 0
                                else "negative_points"
                                if advantage < 0
                                else "zero_points"
                            )
                            summary["split_advantage"][key] = _add(
                                summary["split_advantage"][key], 1
                            )
                            summary["split_advantage"]["maximum_positive_amount"] = max(
                                summary["split_advantage"]["maximum_positive_amount"],
                                advantage,
                            )
    for summary in summaries.values():
        for form in (summary["unsplit"], summary["split"]):
            form["credit_realization"] = reduced_ratio(
                form["paid_credit"], form["created_credit"]
            )
        summary["objectives"] = {
            "unsplit_identity_concentration": summary["unsplit"][
                "identity_concentration_pass_points"
            ]
            + summary["unsplit"]["zero_payout_points"]
            == summary["unsplit"]["point_count"],
            "unsplit_principal_concentration": summary["unsplit"][
                "principal_concentration_pass_points"
            ]
            + summary["unsplit"]["zero_payout_points"]
            == summary["unsplit"]["point_count"],
            "split_identity_concentration": summary["split"][
                "identity_concentration_pass_points"
            ]
            + summary["split"]["zero_payout_points"]
            == summary["split"]["point_count"],
            "split_principal_concentration": summary["split"][
                "principal_concentration_pass_points"
            ]
            + summary["split"]["zero_payout_points"]
            == summary["split"]["point_count"],
            "nonprofitable_split": summary["split_advantage"]["positive_points"] == 0,
        }
    return [summaries[key] for key in design["mechanisms"]]


def _cross_checks() -> list[dict]:
    cases = [
        (
            "balanced",
            {
                "worker_a": {"principal": "alpha", "payout_account": "alpha"},
                "worker_b": {"principal": "beta", "payout_account": "beta"},
            },
            {"worker_a": 10, "worker_b": 10},
        ),
        (
            "dominant",
            {
                "dominant": {"principal": "alpha", "payout_account": "alpha"},
                "baseline": {"principal": "beta", "payout_account": "beta"},
            },
            {"dominant": 18, "baseline": 2},
        ),
        (
            "same_owner_split",
            {
                "dominant_a": {"principal": "alpha", "payout_account": "alpha"},
                "dominant_b": {"principal": "alpha", "payout_account": "alpha"},
                "baseline": {"principal": "beta", "payout_account": "beta"},
            },
            {"dominant_a": 9, "dominant_b": 9, "baseline": 2},
        ),
    ]
    return [cross_check_proportional(*case) for case in cases]


def run_study() -> dict:
    design = build_design()
    design_digest = domain_digest(
        "protocol-stack:reward-distribution:design-v1", design
    )
    trajectories = []
    for scenario in design["scenarios"]:
        for mechanism in design["mechanisms"]:
            result = run_trajectory(scenario, mechanism, design["history_epochs"])
            result.update(fund_trajectory(scenario, result))
            result["objectives"]["funded"] = result["native_funding_failures"] == 0
            trajectories.append(result)
    paired = []
    for mechanism in design["mechanisms"]:
        unsplit = next(
            item
            for item in trajectories
            if item["scenario_id"] == "dominant_unsplit" and item["mechanism"] == mechanism
        )
        split = next(
            item
            for item in trajectories
            if item["scenario_id"] == "dominant_split" and item["mechanism"] == mechanism
        )
        unsplit_paid = _sum(
            amount
            for epoch in unsplit["epochs"]
            for participant, amount in epoch["payouts"].items()
            if participant == "dominant"
        )
        split_paid = _sum(
            amount
            for epoch in split["epochs"]
            for participant, amount in epoch["payouts"].items()
            if participant in {"dominant_a", "dominant_b"}
        )
        paired.append(
            {
                "mechanism": mechanism,
                "unsplit_principal_payout": unsplit_paid,
                "split_principal_payout": split_paid,
                "split_advantage": split_paid - unsplit_paid,
                "nonprofitable_split": split_paid <= unsplit_paid,
            }
        )
    report = {
        "schema": "protocol-stack/reward-distribution-study/v1",
        "design": design["design"],
        "design_digest": design_digest,
        "support_point_count": design["support_point_count"],
        "exact_support": exact_support(design),
        "trajectory_count": len(trajectories),
        "trajectories": trajectories,
        "paired_split_comparisons": paired,
        "adapter_cross_checks": _cross_checks(),
    }
    report["study_digest"] = domain_digest(
        "protocol-stack:reward-distribution:study-v1", report
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
