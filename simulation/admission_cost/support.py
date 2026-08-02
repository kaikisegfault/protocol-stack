"""Lossless complete-support admission-cost boundary study."""

from __future__ import annotations

from simulation.economic_stress.envelope_design import design_value as envelope_design

from .model import (
    capital_lower_bound,
    identities,
    observe_point,
    operating_break_even,
    ratio_less,
    reduced_ratio,
    scores,
)


def _summary(mechanism: str, locks: range) -> dict:
    return {
        "mechanism": mechanism,
        "point_count": 0,
        "split_form_count": 0,
        "zero_payout_points": 0,
        "registered_identity_concentration_pass_points": 0,
        "registered_principal_concentration_pass_points": 0,
        "hidden_principal_concentration_pass_points": 0,
        "profitable_zero_cost_split_forms": 0,
        "zero_gain_split_forms": 0,
        "negative_gain_split_forms": 0,
        "maximum_zero_cost_gain": 0,
        "maximum_zero_cost_gain_witness": None,
        "operating_deterrence_floor": 0,
        "operating_deterrence_floor_witness": None,
        "smallest_honest_entry_ceiling": None,
        "smallest_honest_entry_witness": None,
        "zero_honest_payout_coordinates": 0,
        "_bond_lower": {
            lock: {"ratio": reduced_ratio(0, 1), "inclusive": True} for lock in locks
        },
        "_honest_upper": {lock: None for lock in locks},
    }


def _update_lower(current: dict, candidate: dict) -> dict:
    if ratio_less(current["ratio"], candidate["ratio"]):
        return candidate
    if current["ratio"] == candidate["ratio"] and not candidate["inclusive"]:
        return {"ratio": current["ratio"], "inclusive": False}
    return current


def _update_upper(current: dict | None, candidate: dict) -> dict:
    if current is None or ratio_less(candidate, current):
        return candidate
    return current


def _rate_range(lower: dict, upper: dict) -> bool:
    if ratio_less(lower["ratio"], upper):
        return True
    return lower["ratio"] == upper and lower["inclusive"]


def _record_point(summary: dict, observation: dict) -> None:
    summary["point_count"] += 1
    summary["zero_payout_points"] += int(observation["zero_payout"])
    summary["registered_identity_concentration_pass_points"] += int(
        observation["identity_concentration"] is True
    )
    summary["registered_principal_concentration_pass_points"] += int(
        observation["principal_concentration"] is True
    )
    summary["hidden_principal_concentration_pass_points"] += int(
        observation["hidden_principal_concentration"] is True
    )


def _record_gain(
    summary: dict, gain: int, identity_count: int, locks: range, witness: dict
) -> None:
    summary["split_form_count"] += 1
    key = (
        "profitable_zero_cost_split_forms"
        if gain > 0
        else "negative_gain_split_forms"
        if gain < 0
        else "zero_gain_split_forms"
    )
    summary[key] += 1
    if gain > summary["maximum_zero_cost_gain"]:
        summary["maximum_zero_cost_gain"] = gain
        summary["maximum_zero_cost_gain_witness"] = witness
    break_even = operating_break_even(gain, identity_count - 1)
    if break_even > summary["operating_deterrence_floor"]:
        summary["operating_deterrence_floor"] = break_even
        summary["operating_deterrence_floor_witness"] = witness
    for lock in locks:
        exposure = (identity_count - 1) * (1 + lock)
        candidate = capital_lower_bound(gain, exposure)
        summary["_bond_lower"][lock] = _update_lower(
            summary["_bond_lower"][lock], candidate
        )


def _record_honest(summary: dict, payout: int, locks: range, witness: dict) -> None:
    current = summary["smallest_honest_entry_ceiling"]
    if current is None or payout < current:
        summary["smallest_honest_entry_ceiling"] = payout
        summary["smallest_honest_entry_witness"] = witness
    summary["zero_honest_payout_coordinates"] += int(payout == 0)
    for lock in locks:
        candidate = reduced_ratio(payout, 1 + lock)
        summary["_honest_upper"][lock] = _update_upper(
            summary["_honest_upper"][lock], candidate
        )


def exact_support(design: dict) -> tuple[list[dict], bool]:
    configurations = {
        item["case_id"]: item for item in envelope_design()["survivor_configurations"]
    }
    locks = range(1, 17)
    summaries = {key: _summary(key, locks) for key in design["mechanisms"]}
    cap_equivalence = True
    for case_id in design["survivor_case_ids"]:
        budget = configurations[case_id]["values"]["reward_budget_per_role"]
        for role in design["roles"]:
            for weight in range(1, 17):
                for honest_units in range(1, 21):
                    forms: dict[str, list[dict]] = {key: [] for key in design["mechanisms"]}
                    for identity_count in range(1, 17):
                        participant_map = identities(identity_count)
                        score_map = scores(
                            design["dominant_total_units"], identity_count, weight, honest_units
                        )
                        observations = {
                            mechanism: observe_point(
                                budget, score_map, participant_map, mechanism
                            )
                            for mechanism in design["mechanisms"]
                        }
                        if observations["participant_cap"]["payouts"] != observations[
                            "principal_cap"
                        ]["payouts"]:
                            cap_equivalence = False
                            raise AssertionError("distinct registered scopes changed cap output")
                        for mechanism, observation in observations.items():
                            forms[mechanism].append(observation)
                            _record_point(summaries[mechanism], observation)
                    for mechanism, observations in forms.items():
                        baseline = observations[0]["dominant_payout"]
                        if honest_units == 1:
                            _record_honest(
                                summaries[mechanism],
                                observations[0]["honest_payout"],
                                locks,
                                {
                                    "case_id": case_id,
                                    "role": role,
                                    "budget": budget,
                                    "selected_weight": weight,
                                    "honest_units": honest_units,
                                    "honest_payout": observations[0]["honest_payout"],
                                },
                            )
                        for identity_count, observation in enumerate(observations[1:], 2):
                            gain = observation["dominant_payout"] - baseline
                            _record_gain(
                                summaries[mechanism],
                                gain,
                                identity_count,
                                locks,
                                {
                                    "case_id": case_id,
                                    "role": role,
                                    "budget": budget,
                                    "selected_weight": weight,
                                    "honest_units": honest_units,
                                    "identity_count": identity_count,
                                    "unsplit_dominant_payout": baseline,
                                    "split_dominant_payout": observation[
                                        "dominant_payout"
                                    ],
                                    "zero_cost_gain": gain,
                                },
                            )
    results = [
        _finalize(item, design["identity_form_count"]) for item in summaries.values()
    ]
    return results, cap_equivalence


def _finalize(summary: dict, expected_points: int) -> dict:
    if summary["point_count"] != expected_points:
        raise AssertionError("complete-support point count mismatch")
    lowers = summary.pop("_bond_lower")
    uppers = summary.pop("_honest_upper")
    floor = summary["operating_deterrence_floor"]
    ceiling = summary["smallest_honest_entry_ceiling"]
    summary["operating_cost_interval"] = {
        "minimum": floor,
        "maximum": ceiling,
        "feasible": floor <= ceiling,
    }
    summary["capital_rate_boundaries"] = [
        {
            "post_exit_lock_epochs": lock,
            "unit_bond_deterrence_lower": lowers[lock],
            "unit_bond_honest_entry_upper": {
                "ratio": uppers[lock],
                "inclusive": True,
            },
            "joint_rate_range": _rate_range(lowers[lock], uppers[lock]),
        }
        for lock in sorted(lowers)
    ]
    summary["objectives"] = {
        "work_invariant": True,
        "nonprofitable_split_at_floor": True,
        "hidden_concentration": summary["hidden_principal_concentration_pass_points"]
        + summary["zero_payout_points"]
        == summary["point_count"],
        "honest_entry_at_floor": floor <= ceiling,
        "joint_cost_range": floor <= ceiling,
    }
    return summary
