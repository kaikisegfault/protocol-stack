"""Checked work partition, utility, and capital-time boundary projection."""

from __future__ import annotations

from math import gcd

from simulation.participation.domain import MAX_U64, checked_add, checked_mul
from simulation.reward_distribution.model import evaluate_point


def add(left: int, right: int) -> int:
    value = checked_add(left, right)
    if value is None:
        raise OverflowError("u64 addition overflow")
    return value


def mul(left: int, right: int) -> int:
    value = checked_mul(left, right)
    if value is None:
        raise OverflowError("u64 multiplication overflow")
    return value


def sum_u64(values) -> int:
    result = 0
    for value in values:
        result = add(result, value)
    return result


def ceil_div(numerator: int, denominator: int) -> int:
    if not 0 <= numerator <= MAX_U64 or not 0 < denominator <= MAX_U64:
        raise ValueError("invalid ceiling-division input")
    quotient, remainder = divmod(numerator, denominator)
    return add(quotient, int(remainder != 0))


def reduced_ratio(numerator: int, denominator: int) -> dict[str, int]:
    if not 0 <= numerator <= MAX_U64 or not 0 < denominator <= MAX_U64:
        raise ValueError("invalid ratio")
    divisor = gcd(numerator, denominator)
    return {"numerator": numerator // divisor, "denominator": denominator // divisor}


def ratio_less(left: dict[str, int], right: dict[str, int]) -> bool:
    return mul(left["numerator"], right["denominator"]) < mul(
        right["numerator"], left["denominator"]
    )


def partition_units(total_units: int, identity_count: int) -> list[int]:
    if not 1 <= identity_count <= total_units <= MAX_U64:
        raise ValueError("identity count must fit positive work units")
    quotient, remainder = divmod(total_units, identity_count)
    result = [quotient + int(index < remainder) for index in range(identity_count)]
    if any(value == 0 for value in result) or sum_u64(result) != total_units:
        raise AssertionError("work partition is not positive and lossless")
    return result


def identities(identity_count: int, *, prefix: str = "dominant") -> dict:
    result = {
        "honest": {
            "principal": "honest_owner",
            "payout_account": "honest_payout",
        }
    }
    for index in range(identity_count):
        participant = f"{prefix}_{index:02d}"
        result[participant] = {
            "principal": f"{participant}_owner",
            "payout_account": f"{participant}_payout",
        }
    return dict(sorted(result.items()))


def scores(total_units: int, identity_count: int, weight: int, honest: int) -> dict:
    if not 1 <= weight <= MAX_U64 or not 1 <= honest <= MAX_U64:
        raise ValueError("weight and honest score must be positive u64")
    result = {"honest": honest}
    for index, units in enumerate(partition_units(total_units, identity_count)):
        result[f"dominant_{index:02d}"] = mul(units, weight)
    if sum_u64(value for key, value in result.items() if key != "honest") != mul(
        total_units, weight
    ):
        raise AssertionError("weighted work changed across identities")
    return dict(sorted(result.items()))


def hidden_concentration(payouts: dict[str, int]) -> bool | None:
    dominant = sum_u64(
        amount for participant, amount in payouts.items() if participant != "honest"
    )
    honest = payouts.get("honest", 0)
    total = add(dominant, honest)
    if total == 0:
        return None
    return mul(4, max(dominant, honest)) <= mul(3, total)


def observe_point(budget: int, score_map: dict, participant_map: dict, mechanism: str):
    result = evaluate_point(budget, score_map, participant_map, mechanism)
    payouts = result["payouts"]
    dominant = sum_u64(
        amount for participant, amount in payouts.items() if participant != "honest"
    )
    return {
        **result,
        "dominant_payout": dominant,
        "honest_payout": payouts.get("honest", 0),
        "hidden_principal_concentration": hidden_concentration(payouts),
    }


def operating_break_even(zero_cost_gain: int, extra_identities: int) -> int:
    if extra_identities < 0:
        raise ValueError("extra identity count must be nonnegative")
    if zero_cost_gain <= 0:
        return 0
    if extra_identities == 0:
        raise ValueError("positive gain requires an incremental identity")
    return ceil_div(zero_cost_gain, extra_identities)


def capital_lower_bound(zero_cost_gain: int, incremental_exposure: int) -> dict:
    if zero_cost_gain <= 0:
        return {"ratio": reduced_ratio(0, 1), "inclusive": True}
    if incremental_exposure <= 0:
        raise ValueError("positive gain requires incremental exposure")
    return {
        "ratio": reduced_ratio(zero_cost_gain - 1, incremental_exposure),
        "inclusive": False,
    }


def capital_cost(exposure: int, rate_numerator: int, rate_denominator: int) -> int:
    return ceil_div(mul(exposure, rate_numerator), rate_denominator)
