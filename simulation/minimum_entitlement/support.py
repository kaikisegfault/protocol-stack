"""Complete-support minimum-entitlement comparison and exact boundaries."""

from __future__ import annotations

from simulation.reward_distribution.model import evaluate_point

from .metrics import finalize_summary, new_summary, record_difference, record_point, witness
from .model import evaluate_floor, identities, work_maps


def _check_zero_floor(
    budget: int, scores: dict, participants: dict, mechanism: str, observation: dict
) -> None:
    accepted = evaluate_point(budget, scores, participants, mechanism)
    shared = {
        key: observation[key]
        for key in (
            "created_credit",
            "paid_credit",
            "payouts",
            "zero_payout",
            "identity_concentration",
            "principal_concentration",
        )
    }
    if shared != accepted:
        raise AssertionError("zero-floor projection changed accepted reward result")


def _coordinate_results(
    design: dict, coordinate: dict, summaries: dict, break_evens: list[dict]
) -> tuple[int, bool]:
    budget = coordinate["budget"]
    mechanisms = design["mechanisms"]
    baseline = {}
    zero_checks = 0
    cap_equivalence = True
    for family in design["floor_families"]:
        floors = [0] if family == "zero" else range(0, 6)
        for floor in floors:
            forms = {mechanism: [] for mechanism in mechanisms}
            for identity_count in range(1, 17):
                participants = identities(identity_count)
                raw, scores = work_maps(identity_count, coordinate["selected_weight"])
                observations = {
                    mechanism: evaluate_floor(
                        budget, raw, scores, participants, family, floor, mechanism
                    )
                    for mechanism in mechanisms
                }
                if observations["participant_cap"]["payouts"] != observations[
                    "principal_cap"
                ]["payouts"]:
                    cap_equivalence = False
                    raise AssertionError("distinct registered scopes changed cap output")
                for mechanism, observation in observations.items():
                    forms[mechanism].append(observation)
                    record_point(summaries[(family, mechanism)], observation, floor)
                    if floor == 0 and family == "zero":
                        _check_zero_floor(budget, scores, participants, mechanism, observation)
                        zero_checks += 1
            for mechanism, observations in forms.items():
                summary = summaries[(family, mechanism)]
                if family == "zero":
                    baseline[mechanism] = observations[0]["dominant_payout"]
                floor_dominant = observations[0]["dominant_payout"]
                honest_all = all(item["honest_payout"] > 0 for item in observations)
                same_pass = honest_all
                baseline_pass = honest_all
                for identity_count, observation in enumerate(observations, 1):
                    amplification = observation["dominant_payout"] - baseline[mechanism]
                    summary["baseline_comparison_forms"] += 1
                    record_difference(
                        summary,
                        "baseline_amplification",
                        amplification,
                        witness(coordinate, floor, identity_count, amplification),
                    )
                    baseline_pass = baseline_pass and amplification <= 0
                    if identity_count == 1:
                        continue
                    gain = observation["dominant_payout"] - floor_dominant
                    summary["same_floor_split_forms"] += 1
                    record_difference(
                        summary,
                        "same_floor_split",
                        gain,
                        witness(coordinate, floor, identity_count, gain),
                    )
                    same_pass = same_pass and gain <= 0
                if floor > 0:
                    summary["_same_floor_all"][floor] &= same_pass
                    summary["_baseline_all"][floor] &= baseline_pass
        if family != "zero":
            break_evens.extend(
                _record_coordinate_break_even(
                    design, coordinate, family, summaries, baseline
                )
            )
    return zero_checks, cap_equivalence


def _floor_passes(
    design: dict, coordinate: dict, family: str, mechanism: str, baseline: int, floor: int
) -> tuple[bool, bool]:
    observations = []
    for identity_count in range(1, 17):
        raw, scores = work_maps(identity_count, coordinate["selected_weight"])
        observations.append(
            evaluate_floor(
                coordinate["budget"],
                raw,
                scores,
                identities(identity_count),
                family,
                floor,
                mechanism,
            )
        )
    honest = all(item["honest_payout"] > 0 for item in observations)
    unsplit = observations[0]["dominant_payout"]
    same = honest and all(item["dominant_payout"] <= unsplit for item in observations[1:])
    amplified = honest and all(item["dominant_payout"] <= baseline for item in observations)
    return same, amplified


def _record_coordinate_break_even(
    design: dict, coordinate: dict, family: str, summaries: dict, baseline: dict
) -> list[dict]:
    results = []
    for mechanism in design["mechanisms"]:
        passes = [
            (floor, *_floor_passes(design, coordinate, family, mechanism, baseline[mechanism], floor))
            for floor in range(1, 6)
        ]
        summary = summaries[(family, mechanism)]
        summary["coordinate_same_floor_break_even_count"] += int(
            any(same for _, same, _ in passes)
        )
        summary["coordinate_baseline_break_even_count"] += int(
            any(amplified for _, _, amplified in passes)
        )
        same = next((floor for floor, passed, _ in passes if passed), None)
        amplified = next((floor for floor, _, passed in passes if passed), None)
        joint = next(
            (
                floor
                for floor, same_pass, amplification_pass in passes
                if same_pass and amplification_pass
            ),
            None,
        )
        results.append(
            {
                **coordinate,
                "floor_family": family,
                "mechanism": mechanism,
                "same_floor_break_even": same,
                "baseline_break_even": amplified,
                "joint_break_even": joint,
            }
        )
    return results


def exact_support(design: dict) -> tuple[list[dict], list[dict], int, bool]:
    summaries = {
        (family, mechanism): new_summary(family, mechanism)
        for family in design["floor_families"]
        for mechanism in design["mechanisms"]
    }
    zero_checks = 0
    cap_equivalence = True
    break_evens = []
    for coordinate in design["retained_coordinates"]:
        count, equivalent = _coordinate_results(
            design, coordinate, summaries, break_evens
        )
        zero_checks += count
        cap_equivalence &= equivalent
    results = [
        finalize_summary(
            summaries[(family, mechanism)], design["retained_coordinate_count"]
        )
        for family in design["floor_families"]
        for mechanism in design["mechanisms"]
    ]
    if sum(item["point_count"] for item in results) != design["evaluated_form_count"]:
        raise AssertionError("complete-support form count mismatch")
    if zero_checks != design["zero_floor_cross_check_count"]:
        raise AssertionError("zero-floor cross-check count mismatch")
    if len(break_evens) != design["retained_coordinate_count"] * 2 * 3:
        raise AssertionError("coordinate break-even count mismatch")
    return results, break_evens, zero_checks, cap_equivalence
