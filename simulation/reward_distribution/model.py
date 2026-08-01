"""Checked reward-credit accumulation and payout-cap projection."""

from __future__ import annotations

from dataclasses import dataclass
from math import gcd
from typing import Any

from simulation.participation.domain import MAX_U64, checked_add, checked_mul


@dataclass
class Bucket:
    source_epoch: int
    participant: str
    principal: str
    amount: int


def _add(left: int, right: int) -> int:
    value = checked_add(left, right)
    if value is None:
        raise OverflowError("u64 addition overflow")
    return value


def _mul(left: int, right: int) -> int:
    value = checked_mul(left, right)
    if value is None:
        raise OverflowError("u64 multiplication overflow")
    return value


def _sum(values) -> int:
    result = 0
    for value in values:
        result = _add(result, value)
    return result


def _floor_share(amount: int, part: int, total: int) -> int:
    if not 0 <= amount <= MAX_U64 or not 0 <= part <= MAX_U64 or total <= 0:
        raise ValueError("invalid floor-share input")
    quotient, remainder = divmod(amount, total)
    return _add(_mul(quotient, part), _mul(remainder, part) // total)


def credits_for_scores(budget: int, scores: dict[str, int]) -> dict[str, int]:
    _validate_budget_scores(budget, scores)
    total = _sum(scores.values())
    if total == 0:
        return {}
    return {
        participant: credit
        for participant, score in sorted(scores.items())
        if score != 0
        for credit in [_floor_share(budget, score, total)]
        if credit != 0
    }


def _validate_budget_scores(budget: int, scores: dict[str, int]) -> None:
    if type(budget) is not int or not 0 < budget <= MAX_U64:
        raise ValueError("budget must be a nonzero u64")
    if any(
        type(key) is not str
        or type(value) is not int
        or not 0 <= value <= MAX_U64
        for key, value in scores.items()
    ):
        raise ValueError("scores must map identifiers to u64 values")


def _scope_for(participant: str, participants: dict, mechanism: str) -> str:
    if mechanism == "principal_cap":
        return participants[participant]["principal"]
    return participant


def _scope_candidates(
    buckets: list[Bucket], participants: dict, mechanism: str, budget: int
) -> dict[str, int]:
    credit: dict[str, int] = {}
    for bucket in buckets:
        scope = _scope_for(bucket.participant, participants, mechanism)
        credit[scope] = _add(credit.get(scope, 0), bucket.amount)
    total = _sum(credit.values())
    if total == 0:
        return {}
    available = min(budget, total)
    return {
        scope: _floor_share(available, amount, total)
        for scope, amount in sorted(credit.items())
    }


def _apply_cap(candidates: dict[str, int]) -> dict[str, int]:
    if not candidates:
        return {}
    result = dict(candidates)
    total = _sum(result.values())
    if total == 0:
        return result
    largest = min(result, key=lambda key: (-result[key], key))
    other = total - result[largest]
    limit = _mul(3, other)
    if result[largest] > limit:
        result[largest] = limit
    return result


def _consume(
    buckets: list[Bucket],
    participants: dict,
    mechanism: str,
    allowances: dict[str, int],
) -> dict[str, int]:
    payouts: dict[str, int] = {}
    remaining = dict(allowances)
    for bucket in sorted(buckets, key=lambda item: (item.source_epoch, item.participant)):
        scope = _scope_for(bucket.participant, participants, mechanism)
        amount = min(bucket.amount, remaining.get(scope, 0))
        if amount == 0:
            continue
        bucket.amount -= amount
        remaining[scope] -= amount
        payouts[bucket.participant] = _add(payouts.get(bucket.participant, 0), amount)
    if any(remaining.values()):
        raise AssertionError("scope allowance exceeded available credit")
    buckets[:] = [bucket for bucket in buckets if bucket.amount != 0]
    return dict(sorted(payouts.items()))


def _aggregate(values: dict[str, int], participants: dict, principal: bool) -> dict:
    result: dict[str, int] = {}
    for participant, amount in values.items():
        scope = participants[participant]["principal"] if principal else participant
        result[scope] = _add(result.get(scope, 0), amount)
    return result


def concentration_pass(values: dict[str, int], participants: dict, *, principal: bool):
    scopes = _aggregate(values, participants, principal)
    total = _sum(scopes.values())
    if total == 0:
        return None
    maximum = max(scopes.values())
    return _mul(4, maximum) <= _mul(3, total)


def evaluate_point(
    budget: int,
    scores: dict[str, int],
    participants: dict[str, dict[str, str]],
    mechanism: str,
) -> dict[str, Any]:
    credits = credits_for_scores(budget, scores)
    if mechanism == "proportional":
        payouts = credits
    elif mechanism in {"participant_cap", "principal_cap"}:
        buckets = [
            Bucket(0, participant, participants[participant]["principal"], amount)
            for participant, amount in credits.items()
        ]
        payouts = _consume(
            buckets,
            participants,
            mechanism,
            _apply_cap(_scope_candidates(buckets, participants, mechanism, budget)),
        )
    else:
        raise ValueError("unsupported mechanism")
    return {
        "created_credit": _sum(credits.values()),
        "paid_credit": _sum(payouts.values()),
        "payouts": payouts,
        "zero_payout": not payouts,
        "identity_concentration": concentration_pass(
            payouts, participants, principal=False
        ),
        "principal_concentration": concentration_pass(
            payouts, participants, principal=True
        ),
    }


def run_trajectory(scenario: dict, mechanism: str, history_epochs: int) -> dict:
    participants = scenario["participants"]
    budget = scenario["budget"]
    contributions = scenario["contributions"]
    total_epochs = _add(len(contributions), history_epochs)
    buckets: list[Bucket] = []
    epochs = []
    totals = {
        "weighted_score": 0,
        "created_credit": 0,
        "paid_credit": 0,
        "expired_credit": 0,
        "retained_budget": 0,
        "maximum_pending_credit": 0,
        "zero_payout_epochs": 0,
        "payout_epochs": 0,
        "identity_concentration_pass_epochs": 0,
        "principal_concentration_pass_epochs": 0,
    }
    for epoch in range(total_epochs):
        expired = 0
        if mechanism != "proportional":
            live = []
            for bucket in buckets:
                if _add(bucket.source_epoch, history_epochs) <= epoch:
                    expired = _add(expired, bucket.amount)
                else:
                    live.append(bucket)
            buckets = live
        scores = contributions[epoch] if epoch < len(contributions) else {}
        score_total = _sum(scores.values())
        credits = credits_for_scores(budget, scores) if scores else {}
        if mechanism == "proportional":
            payouts = credits
        else:
            buckets.extend(
                Bucket(epoch, key, participants[key]["principal"], amount)
                for key, amount in credits.items()
            )
            candidates = _scope_candidates(buckets, participants, mechanism, budget)
            payouts = _consume(
                buckets, participants, mechanism, _apply_cap(candidates)
            )
        paid = _sum(payouts.values())
        pending = _sum(bucket.amount for bucket in buckets)
        identity_pass = concentration_pass(payouts, participants, principal=False)
        principal_pass = concentration_pass(payouts, participants, principal=True)
        totals["weighted_score"] = _add(totals["weighted_score"], score_total)
        totals["created_credit"] = _add(
            totals["created_credit"], _sum(credits.values())
        )
        totals["paid_credit"] = _add(totals["paid_credit"], paid)
        totals["expired_credit"] = _add(totals["expired_credit"], expired)
        totals["retained_budget"] = _add(
            totals["retained_budget"], budget - paid
        )
        totals["maximum_pending_credit"] = max(
            totals["maximum_pending_credit"], pending
        )
        if paid == 0:
            totals["zero_payout_epochs"] = _add(totals["zero_payout_epochs"], 1)
        else:
            totals["payout_epochs"] = _add(totals["payout_epochs"], 1)
            totals["identity_concentration_pass_epochs"] = _add(
                totals["identity_concentration_pass_epochs"], int(identity_pass)
            )
            totals["principal_concentration_pass_epochs"] = _add(
                totals["principal_concentration_pass_epochs"], int(principal_pass)
            )
        epochs.append(
            {
                "epoch": epoch,
                "created_credit": _sum(credits.values()),
                "expired_credit": expired,
                "payouts": payouts,
                "paid_credit": paid,
                "pending_credit": pending,
                "retained_budget": budget - paid,
                "identity_concentration": identity_pass,
                "principal_concentration": principal_pass,
            }
        )
    pending = _sum(bucket.amount for bucket in buckets)
    if mechanism != "proportional" and pending != 0:
        raise AssertionError("drain did not clear bounded credit history")
    if _add(totals["paid_credit"], totals["expired_credit"]) != totals[
        "created_credit"
    ]:
        raise AssertionError("credit conservation failure")
    created = totals["created_credit"]
    result = {
        "scenario_id": scenario["scenario_id"],
        "mechanism": mechanism,
        **totals,
        "ending_pending_credit": pending,
        "useful_credit_retention": reduced_ratio(totals["paid_credit"], created),
        "objectives": {
            "bounded_history": pending == 0,
            "bounded_liveness": totals["expired_credit"] == 0,
            "complete_retention": totals["paid_credit"] == created,
            "identity_concentration": totals[
                "identity_concentration_pass_epochs"
            ]
            == totals["payout_epochs"],
            "principal_concentration": totals[
                "principal_concentration_pass_epochs"
            ]
            == totals["payout_epochs"],
        },
        "epochs": epochs,
    }
    return result


def reduced_ratio(numerator: int, denominator: int) -> dict[str, int]:
    if denominator <= 0 or not 0 <= numerator <= MAX_U64:
        raise ValueError("invalid ratio")
    divisor = gcd(numerator, denominator)
    return {
        "numerator": numerator // divisor,
        "denominator": denominator // divisor,
    }
