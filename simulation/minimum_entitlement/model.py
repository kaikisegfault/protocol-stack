"""Checked reserve-credit and accepted-cap projection."""

from __future__ import annotations

from simulation.participation.domain import MAX_U64, checked_add, checked_mul

FLOOR_FAMILIES = {"zero", "per_participant", "work_proportional"}
MECHANISMS = {"proportional", "participant_cap", "principal_cap"}


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


def floor_share(amount: int, part: int, total: int) -> int:
    if (
        type(amount) is not int
        or type(part) is not int
        or type(total) is not int
        or not 0 <= amount <= MAX_U64
        or not 0 <= part <= MAX_U64
        or not 0 < total <= MAX_U64
    ):
        raise ValueError("invalid floor-share input")
    quotient, remainder = divmod(amount, total)
    return add(mul(quotient, part), mul(remainder, part) // total)


def partition_units(total_units: int, identity_count: int) -> list[int]:
    if (
        type(total_units) is not int
        or type(identity_count) is not int
        or not 1 <= identity_count <= total_units <= MAX_U64
    ):
        raise ValueError("identity count must fit positive work units")
    quotient, remainder = divmod(total_units, identity_count)
    result = [quotient + int(index < remainder) for index in range(identity_count)]
    if sum_u64(result) != total_units or any(value == 0 for value in result):
        raise AssertionError("work partition is not positive and lossless")
    return result


def identities(identity_count: int) -> dict[str, dict[str, str]]:
    if type(identity_count) is not int or not 1 <= identity_count <= 16:
        raise ValueError("identity count must be in 1..16")
    result = {
        "honest": {"principal": "honest_owner", "payout_account": "honest_payout"}
    }
    for index in range(identity_count):
        participant = f"dominant_{index:02d}"
        result[participant] = {
            "principal": f"{participant}_owner",
            "payout_account": f"{participant}_payout",
        }
    return dict(sorted(result.items()))


def work_maps(identity_count: int, selected_weight: int) -> tuple[dict, dict]:
    if type(selected_weight) is not int or not 1 <= selected_weight <= MAX_U64:
        raise ValueError("selected weight must be a nonzero u64")
    raw = {"honest": 1}
    for index, units in enumerate(partition_units(16, identity_count)):
        raw[f"dominant_{index:02d}"] = units
    scores = {
        participant: units if participant == "honest" else mul(units, selected_weight)
        for participant, units in raw.items()
    }
    return dict(sorted(raw.items())), dict(sorted(scores.items()))


def _validate_inputs(
    budget: int,
    raw_units: dict[str, int],
    scores: dict[str, int],
    participants: dict[str, dict[str, str]],
    family: str,
    floor: int,
    mechanism: str,
) -> list[str]:
    if type(budget) is not int or not 0 < budget <= MAX_U64:
        raise ValueError("budget must be a nonzero u64")
    if family not in FLOOR_FAMILIES or mechanism not in MECHANISMS:
        raise ValueError("unsupported floor family or mechanism")
    if type(floor) is not int or not 0 <= floor <= MAX_U64:
        raise ValueError("floor must be a u64")
    if family == "zero" and floor != 0:
        raise ValueError("zero family requires floor zero")
    if set(raw_units) != set(scores) or not set(raw_units) <= set(participants):
        raise ValueError("raw-work, score, and participant keys mismatch")
    if any(
        type(key) is not str
        or type(raw_units[key]) is not int
        or type(scores[key]) is not int
        or not 0 <= raw_units[key] <= MAX_U64
        or not 0 <= scores[key] <= MAX_U64
        or (raw_units[key] == 0) != (scores[key] == 0)
        for key in raw_units
    ):
        raise ValueError("raw work and scores must be matching u64 values")
    positive = sorted(key for key, units in raw_units.items() if units != 0)
    if not positive:
        raise ValueError("at least one positive contribution is required")
    return positive


def _reserves(raw_units: dict[str, int], positive: list[str], family: str, floor: int):
    if family == "zero":
        return {}
    if family == "per_participant":
        return {participant: floor for participant in positive if floor != 0}
    return {
        participant: reserve
        for participant in positive
        for reserve in [mul(floor, raw_units[participant])]
        if reserve != 0
    }


def _credits(
    budget: int,
    scores: dict[str, int],
    positive: list[str],
    reserves: dict[str, int],
) -> tuple[dict[str, int], int, int]:
    reserve_total = sum_u64(reserves.values())
    if reserve_total > budget:
        return {}, reserve_total, 0
    remaining = budget - reserve_total
    score_total = sum_u64(scores[key] for key in positive)
    credits = {}
    for participant in positive:
        value = add(
            reserves.get(participant, 0),
            floor_share(remaining, scores[participant], score_total),
        )
        if value != 0:
            credits[participant] = value
    return dict(sorted(credits.items())), reserve_total, remaining


def _scope(participant: str, participants: dict, mechanism: str) -> str:
    return participants[participant]["principal"] if mechanism == "principal_cap" else participant


def _capped_payouts(credits: dict, participants: dict, mechanism: str) -> dict:
    scoped = {}
    for participant, amount in credits.items():
        scope = _scope(participant, participants, mechanism)
        scoped[scope] = add(scoped.get(scope, 0), amount)
    total = sum_u64(scoped.values())
    candidates = {
        scope: floor_share(total, amount, total) for scope, amount in sorted(scoped.items())
    }
    if not candidates:
        return {}
    largest = min(candidates, key=lambda key: (-candidates[key], key))
    other = total - candidates[largest]
    candidates[largest] = min(candidates[largest], mul(3, other))
    remaining = dict(candidates)
    payouts = {}
    for participant, amount in sorted(credits.items()):
        scope = _scope(participant, participants, mechanism)
        payout = min(amount, remaining[scope])
        remaining[scope] -= payout
        if payout:
            payouts[participant] = payout
    if any(remaining.values()):
        raise AssertionError("cap allowance exceeds credit")
    return payouts


def _concentration(payouts: dict, participants: dict, principal: bool):
    scopes = {}
    for participant, amount in payouts.items():
        scope = participants[participant]["principal"] if principal else participant
        scopes[scope] = add(scopes.get(scope, 0), amount)
    total = sum_u64(scopes.values())
    if total == 0:
        return None
    return mul(4, max(scopes.values())) <= mul(3, total)


def _hidden_concentration(payouts: dict):
    dominant = sum_u64(
        amount for participant, amount in payouts.items() if participant != "honest"
    )
    honest = payouts.get("honest", 0)
    total = add(dominant, honest)
    if total == 0:
        return None
    return mul(4, max(dominant, honest)) <= mul(3, total)


def evaluate_floor(
    budget: int,
    raw_units: dict[str, int],
    scores: dict[str, int],
    participants: dict[str, dict[str, str]],
    family: str,
    floor: int,
    mechanism: str,
) -> dict:
    positive = _validate_inputs(
        budget, raw_units, scores, participants, family, floor, mechanism
    )
    credits, reserve_total, remaining = _credits(
        budget, scores, positive, _reserves(raw_units, positive, family, floor)
    )
    if reserve_total > budget:
        return {
            "feasible": False,
            "reserve_total": reserve_total,
            "remaining_budget": None,
            "credits": None,
            "payouts": None,
        }
    payouts = credits if mechanism == "proportional" else _capped_payouts(
        credits, participants, mechanism
    )
    created = sum_u64(credits.values())
    paid = sum_u64(payouts.values())
    dominant = sum_u64(
        amount for participant, amount in payouts.items() if participant != "honest"
    )
    return {
        "feasible": True,
        "reserve_total": reserve_total,
        "remaining_budget": remaining,
        "credits": credits,
        "created_credit": created,
        "paid_credit": paid,
        "retained_budget": budget - paid,
        "payouts": dict(sorted(payouts.items())),
        "dominant_payout": dominant,
        "honest_payout": payouts.get("honest", 0),
        "zero_payout": not payouts,
        "identity_concentration": _concentration(payouts, participants, False),
        "principal_concentration": _concentration(payouts, participants, True),
        "hidden_principal_concentration": _hidden_concentration(payouts),
    }


def maximum_floor(budget: int, family: str, identity_count: int) -> int:
    if type(budget) is not int or not 0 < budget <= MAX_U64:
        raise ValueError("budget must be a nonzero u64")
    if type(identity_count) is not int or not 1 <= identity_count <= 16:
        raise ValueError("identity count must be in 1..16")
    if family == "per_participant":
        return budget // (identity_count + 1)
    if family == "work_proportional":
        return budget // 17
    if family == "zero":
        return 0
    raise ValueError("unsupported floor family")


def maximum_identities(budget: int, family: str, floor: int) -> int:
    if type(budget) is not int or not 0 < budget <= MAX_U64:
        raise ValueError("budget must be a nonzero u64")
    if type(floor) is not int or not 1 <= floor <= MAX_U64:
        raise ValueError("floor must be a positive u64")
    if family == "per_participant":
        return max(0, min(16, budget // floor - 1))
    if family == "work_proportional":
        return 16 if mul(17, floor) <= budget else 0
    raise ValueError("positive floor boundary requires a reserve family")
