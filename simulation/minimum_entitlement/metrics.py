"""Complete-support counters, witnesses, and objective summaries."""

from __future__ import annotations


def new_summary(family: str, mechanism: str) -> dict:
    return {
        "floor_family": family,
        "mechanism": mechanism,
        "point_count": 0,
        "positive_floor_point_count": 0,
        "feasible_points": 0,
        "infeasible_points": 0,
        "honest_positive_points": 0,
        "honest_zero_points": 0,
        "zero_payout_points": 0,
        "hidden_concentration_pass_points": 0,
        "same_floor_split_forms": 0,
        "positive_same_floor_split_forms": 0,
        "zero_same_floor_split_forms": 0,
        "negative_same_floor_split_forms": 0,
        "maximum_same_floor_split_gain": 0,
        "maximum_same_floor_split_gain_witness": None,
        "baseline_comparison_forms": 0,
        "positive_baseline_amplification_forms": 0,
        "zero_baseline_amplification_forms": 0,
        "negative_baseline_amplification_forms": 0,
        "maximum_baseline_amplification": 0,
        "maximum_baseline_amplification_witness": None,
        "maximum_reserve_total": 0,
        "minimum_positive_honest_payout": None,
        "maximum_honest_payout": 0,
        "coordinate_same_floor_break_even_count": 0,
        "coordinate_baseline_break_even_count": 0,
        "_same_floor_all": {floor: True for floor in range(1, 6)},
        "_baseline_all": {floor: True for floor in range(1, 6)},
    }


def witness(coordinate: dict, floor: int, identity_count: int, gain: int) -> dict:
    return {
        **coordinate,
        "floor": floor,
        "identity_count": identity_count,
        "gain": gain,
    }


def record_point(summary: dict, observation: dict, floor: int) -> None:
    summary["point_count"] += 1
    summary["positive_floor_point_count"] += int(floor > 0)
    summary["feasible_points"] += int(observation["feasible"])
    summary["infeasible_points"] += int(not observation["feasible"])
    if not observation["feasible"]:
        return
    honest = observation["honest_payout"]
    summary["honest_positive_points"] += int(honest > 0)
    summary["honest_zero_points"] += int(honest == 0)
    summary["zero_payout_points"] += int(observation["zero_payout"])
    summary["hidden_concentration_pass_points"] += int(
        observation["hidden_principal_concentration"] is True
    )
    summary["maximum_reserve_total"] = max(
        summary["maximum_reserve_total"], observation["reserve_total"]
    )
    if honest > 0:
        current = summary["minimum_positive_honest_payout"]
        summary["minimum_positive_honest_payout"] = (
            honest if current is None else min(current, honest)
        )
    summary["maximum_honest_payout"] = max(summary["maximum_honest_payout"], honest)


def record_difference(summary: dict, prefix: str, gain: int, value: dict) -> None:
    count_key = (
        f"positive_{prefix}_forms"
        if gain > 0
        else f"negative_{prefix}_forms"
        if gain < 0
        else f"zero_{prefix}_forms"
    )
    summary[count_key] += 1
    maximum_key = (
        "maximum_same_floor_split_gain"
        if prefix == "same_floor_split"
        else "maximum_baseline_amplification"
    )
    if gain > summary[maximum_key]:
        summary[maximum_key] = gain
        summary[f"{maximum_key}_witness"] = value


def finalize_summary(summary: dict, coordinate_count: int) -> dict:
    same_all = summary.pop("_same_floor_all")
    baseline_all = summary.pop("_baseline_all")
    positive = summary["positive_floor_point_count"]
    positive_family = summary["floor_family"] != "zero"
    summary["global_same_floor_break_even"] = (
        next((floor for floor, passed in same_all.items() if passed), None)
        if positive_family
        else None
    )
    summary["global_baseline_break_even"] = (
        next((floor for floor, passed in baseline_all.items() if passed), None)
        if positive_family
        else None
    )
    summary["global_joint_break_even"] = (
        next(
            (
                floor
                for floor in range(1, 6)
                if same_all[floor] and baseline_all[floor]
            ),
            None,
        )
        if positive_family
        else None
    )
    summary["objectives"] = {
        "work_invariant": True,
        "strictly_funded": summary["infeasible_points"] == 0,
        "honest_entry": positive > 0
        and summary["honest_positive_points"] >= positive,
        "nonprofitable_same_floor_split": summary[
            "positive_same_floor_split_forms"
        ]
        == 0,
        "no_baseline_amplification": summary[
            "positive_baseline_amplification_forms"
        ]
        == 0,
        "hidden_concentration": summary["hidden_concentration_pass_points"]
        + summary["zero_payout_points"]
        == summary["point_count"],
        "liveness": positive > 0 and summary["honest_positive_points"] >= positive,
        "all_coordinates_have_same_floor_break_even": summary[
            "coordinate_same_floor_break_even_count"
        ]
        == coordinate_count,
        "all_coordinates_have_baseline_break_even": summary[
            "coordinate_baseline_break_even_count"
        ]
        == coordinate_count,
    }
    return summary
