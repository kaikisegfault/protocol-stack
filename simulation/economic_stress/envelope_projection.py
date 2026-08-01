"""Independent exact arithmetic projection for the economic envelope."""

from __future__ import annotations

from collections import Counter
from math import gcd
from typing import Any

from simulation.native_economy.scenario import SplitMix64

from .design import Configuration
from .envelope_design import (
    BUDGET_MAX,
    BUDGET_MIN,
    ISSUANCE_COUNT,
    ISSUANCE_MAX,
    ISSUANCE_MIN,
    JOINT_COMBINATION_COUNT,
    ROLE_COMBINATION_COUNT,
    UNIT_MAX,
    UNIT_MIN,
    WEIGHT_MAX,
    WEIGHT_MIN,
)

MAX_U64 = (1 << 64) - 1


def checked_add(left: int, right: int) -> int:
    if not _u64(left) or not _u64(right) or left > MAX_U64 - right:
        raise OverflowError("u64 addition overflow")
    return left + right


def checked_mul(left: int, right: int) -> int:
    if not _u64(left) or not _u64(right):
        raise OverflowError("u64 multiplication operand invalid")
    if left and right > MAX_U64 // left:
        raise OverflowError("u64 multiplication overflow")
    return left * right


def _u64(value: object) -> bool:
    return type(value) is int and 0 <= value <= MAX_U64


def floor_share(total: int, score: int, score_total: int) -> int:
    if not _u64(total) or not _u64(score) or not _u64(score_total):
        raise ValueError("floor share requires u64 values")
    if score == 0 or score_total == 0 or score > score_total:
        raise ValueError("floor share score is invalid")
    quotient, remainder = divmod(total, score_total)
    whole = checked_mul(quotient, score)
    fraction = checked_mul(remainder, score) // score_total
    return checked_add(whole, fraction)


def role_entitlements(
    budget: int,
    selected_units: int,
    baseline_units: int,
    selected_weight: int,
) -> tuple[int, int]:
    if not UNIT_MIN <= selected_units <= UNIT_MAX:
        raise ValueError("selected units are outside the study support")
    if not UNIT_MIN <= baseline_units <= UNIT_MAX:
        raise ValueError("baseline units are outside the study support")
    if not WEIGHT_MIN <= selected_weight <= WEIGHT_MAX:
        raise ValueError("selected weight is outside the study grid")
    selected_score = checked_mul(selected_units, selected_weight)
    score_total = checked_add(selected_score, baseline_units)
    return (
        floor_share(budget, selected_score, score_total),
        floor_share(budget, baseline_units, score_total),
    )


def units_from_seed(config: Configuration, seed: int) -> tuple[int, int, int, int]:
    if not _u64(seed):
        raise ValueError("seed must be a u64")
    stream = SplitMix64(seed ^ (config.case_index << 32))
    return (
        1 + stream.bounded(20),
        1 + stream.bounded(20),
        1 + stream.bounded(20),
        1 + stream.bounded(20),
    )


def project_point(
    config: Configuration,
    units: tuple[int, int, int, int],
) -> dict[str, Any]:
    if len(units) != 4:
        raise ValueError("point projection requires four contribution units")
    values = config.values
    budget = int(values["reward_budget_per_role"])
    issuance = int(values["issuance_amount"])
    _validate_financial_coordinates(issuance, budget)
    validator = role_entitlements(
        budget,
        units[0],
        units[1],
        int(values["validator_weight"]),
    )
    node = role_entitlements(
        budget,
        units[2],
        units[3],
        int(values["node_weight"]),
    )
    entitlement_total = checked_add(
        checked_add(*validator),
        checked_add(*node),
    )
    fee_reward, fee_treasury = fee_split(config)
    requested = checked_mul(2, budget)
    treasury = checked_add(
        checked_add(500, issuance),
        fee_treasury,
    )
    treasury_funded = treasury >= requested
    available = checked_add(fee_reward, requested if treasury_funded else 0)
    return {
        "units": list(units),
        "validator_entitlements": list(validator),
        "node_entitlements": list(node),
        "entitlement_total": entitlement_total,
        "retained_remainder": checked_mul(2, budget) - entitlement_total,
        "fee_reward": fee_reward,
        "fee_treasury": fee_treasury,
        "treasury_funding_accepted": treasury_funded,
        "available_reward": available,
        "funding_complete": available >= entitlement_total,
        "concentration_within_bound": (
            within_concentration_bound(validator)
            and within_concentration_bound(node)
        ),
    }


def fee_split(config: Configuration) -> tuple[int, int]:
    volume = int(config.values["fee_volume"])
    parts = int(config.values["fee_reward_parts"])
    reward = floor_share(volume, parts, 10) if parts else 0
    return reward, volume - reward


def within_concentration_bound(entitlements: tuple[int, int]) -> bool:
    total = checked_add(*entitlements)
    return (
        bool(total)
        and checked_mul(4, max(entitlements)) <= checked_mul(3, total)
    )


def role_total_histogram(budget: int, weight: int) -> Counter[int]:
    histogram: Counter[int] = Counter()
    for selected in range(UNIT_MIN, UNIT_MAX + 1):
        for baseline in range(UNIT_MIN, UNIT_MAX + 1):
            total = checked_add(
                *role_entitlements(budget, selected, baseline, weight)
            )
            histogram[total] = checked_add(histogram[total], 1)
    if sum(histogram.values()) != ROLE_COMBINATION_COUNT:
        raise AssertionError("role entitlement histogram has the wrong size")
    return histogram


def joint_total_histogram(config: Configuration, budget: int) -> Counter[int]:
    validator = role_total_histogram(budget, int(config.values["validator_weight"]))
    node = role_total_histogram(budget, int(config.values["node_weight"]))
    joint: Counter[int] = Counter()
    for validator_total, validator_count in validator.items():
        for node_total, node_count in node.items():
            total = checked_add(validator_total, node_total)
            pair_count = checked_mul(
                validator_count,
                node_count,
            )
            joint[total] = checked_add(joint[total], pair_count)
    if sum(joint.values()) != JOINT_COMBINATION_COUNT:
        raise AssertionError("joint entitlement histogram has the wrong size")
    return joint


def financial_profile(config: Configuration, budget: int) -> dict[str, Any]:
    _validate_financial_coordinates(ISSUANCE_MIN, budget)
    totals = joint_total_histogram(config, budget)
    fee_reward, fee_treasury = fee_split(config)
    requested = checked_mul(2, budget)
    base_treasury = checked_add(500, fee_treasury)
    required = 0 if requested <= base_treasury else requested - base_treasury
    minimum_issuance = max(ISSUANCE_MIN, required)
    if minimum_issuance > ISSUANCE_MAX:
        minimum_issuance_value: int | None = None
        below_count = ISSUANCE_COUNT
    else:
        minimum_issuance_value = minimum_issuance
        below_count = minimum_issuance - ISSUANCE_MIN
    funded_fallback = 0
    for total, count in totals.items():
        if total <= fee_reward:
            funded_fallback = checked_add(funded_fallback, count)
    fallback = _classify(funded_fallback, JOINT_COMBINATION_COUNT)
    at_or_above = ISSUANCE_COUNT - below_count
    classification_counts = {
        "solvent": checked_add(
            at_or_above,
            below_count if fallback == "solvent" else 0,
        ),
        "mixed": below_count if fallback == "mixed" else 0,
        "insolvent": below_count if fallback == "insolvent" else 0,
    }
    if sum(classification_counts.values()) != ISSUANCE_COUNT:
        raise AssertionError("financial profile lost issuance cells")
    return {
        "family_id": config.case_id,
        "reward_budget_per_role": budget,
        "minimum_entitlement_total": min(totals),
        "maximum_entitlement_total": max(totals),
        "fee_reward": fee_reward,
        "fee_treasury": fee_treasury,
        "minimum_issuance_for_treasury_funding": minimum_issuance_value,
        "fallback_funded_combination_count": funded_fallback,
        "fallback_classification": fallback,
        "classification_counts": classification_counts,
    }


def concentration_cell(
    config: Configuration,
    validator_weight: int,
    node_weight: int,
) -> dict[str, Any]:
    budget = int(config.values["reward_budget_per_role"])
    validator_count = role_concentration_count(budget, validator_weight)
    node_count = role_concentration_count(budget, node_weight)
    joint_count = checked_mul(validator_count, node_count)
    return {
        "family_id": config.case_id,
        "validator_weight": validator_weight,
        "node_weight": node_weight,
        "validator_passing_pair_count": validator_count,
        "node_passing_pair_count": node_count,
        "passing_combination_count": joint_count,
        "passing_ratio": rational(joint_count, JOINT_COMBINATION_COUNT),
        "classification": _classify_concentration(joint_count),
    }


def role_concentration_count(budget: int, weight: int) -> int:
    result = 0
    for selected in range(UNIT_MIN, UNIT_MAX + 1):
        for baseline in range(UNIT_MIN, UNIT_MAX + 1):
            if within_concentration_bound(
                role_entitlements(budget, selected, baseline, weight)
            ):
                result = checked_add(result, 1)
    return result


def rational(numerator: int, denominator: int) -> dict[str, int]:
    if not _u64(numerator) or not _u64(denominator) or denominator == 0:
        raise ValueError("invalid rational")
    divisor = gcd(numerator, denominator)
    return {"numerator": numerator // divisor, "denominator": denominator // divisor}


def _classify(count: int, total: int) -> str:
    if not _u64(count) or not _u64(total) or count > total:
        raise ValueError("classification count is invalid")
    if count == total:
        return "solvent"
    return "insolvent" if count == 0 else "mixed"


def _classify_concentration(count: int) -> str:
    if count == JOINT_COMBINATION_COUNT:
        return "within_bound"
    return "concentrated" if count == 0 else "mixed"


def _validate_financial_coordinates(issuance: int, budget: int) -> None:
    if not ISSUANCE_MIN <= issuance <= ISSUANCE_MAX:
        raise ValueError("issuance is outside the study grid")
    if not BUDGET_MIN <= budget <= BUDGET_MAX:
        raise ValueError("budget is outside the study grid")
