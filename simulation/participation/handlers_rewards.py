"""Contribution appraisal and entitlement settlement operations."""

from __future__ import annotations

from typing import Any

from .domain import (
    Budget,
    Contribution,
    Entitlement,
    Manifest,
    Participant,
    ParticipantTotal,
    RoleTotal,
    State,
    checked_add,
    checked_mul,
    current_epoch,
)
from .operations import Outcome, failure, success


def attest_contribution(
    state: State,
    manifest: Manifest,
    event: dict[str, Any],
) -> Outcome:
    policy = manifest.contributions[event["role"]].get(event["contribution_kind"])
    if policy is None:
        return failure("INVALID_ROLE")
    if event["actor"] != policy.verifier:
        return failure("UNAUTHORIZED")
    if event["proof_id"] in state.accepted_proof_ids:
        return failure("PROOF_REPLAY")
    participant = state.participants.get(event["participant"])
    if participant is None:
        return failure("NOT_FOUND")
    if participant.role != event["role"]:
        return failure("INVALID_ROLE")
    epoch = current_epoch(state, manifest)
    if event["epoch"] != epoch:
        return failure("INVALID_TARGET")
    if not _eligible(participant, epoch):
        return failure("NOT_ELIGIBLE")
    units = event["units"]
    if units == 0:
        return failure("ZERO_AMOUNT")
    parameters = manifest.parameters
    if units > parameters.max_units_per_proof:
        return failure("LIMIT")
    update, error = _prepare_contribution(state, manifest, event, policy.weight)
    if error is not None:
        return failure(error)
    _store_contribution(state, update)
    return success()


def _prepare_contribution(
    state: State,
    manifest: Manifest,
    event: dict[str, Any],
    weight: int,
) -> tuple[dict[str, Any], str | None]:
    epoch = event["epoch"]
    participant_key = (epoch, event["role"], event["participant"])
    participant_total = state.participant_totals.get(participant_key)
    old_raw = 0 if participant_total is None else participant_total.raw_units
    raw_total = checked_add(old_raw, event["units"])
    if raw_total is None:
        return {}, "OVERFLOW"
    if raw_total > manifest.parameters.max_units_per_participant_epoch:
        return {}, "LIMIT"
    weighted = checked_mul(event["units"], weight)
    if weighted is None:
        return {}, "OVERFLOW"
    old_weighted = 0 if participant_total is None else participant_total.weighted_units
    participant_weighted = checked_add(old_weighted, weighted)
    if participant_weighted is None:
        return {}, "OVERFLOW"
    role_key = (epoch, event["role"])
    role_total = state.role_totals.get(role_key)
    old_role_weight = 0 if role_total is None else role_total.weighted_units
    role_weighted = checked_add(old_role_weight, weighted)
    if role_weighted is None:
        return {}, "OVERFLOW"
    role_count = checked_add(
        0 if role_total is None else role_total.participant_count,
        1 if participant_total is None else 0,
    )
    if role_count is None:
        return {}, "OVERFLOW"
    contribution_key = participant_key + (event["contribution_kind"],)
    contribution = state.contributions.get(contribution_key)
    old_kind_units = 0 if contribution is None else contribution.units
    old_kind_weight = 0 if contribution is None else contribution.weighted_units
    kind_units = checked_add(old_kind_units, event["units"])
    kind_weighted = checked_add(old_kind_weight, weighted)
    if kind_units is None or kind_weighted is None:
        return {}, "OVERFLOW"
    return {
        "participant_key": participant_key,
        "role_key": role_key,
        "contribution_key": contribution_key,
        "raw_total": raw_total,
        "participant_weighted": participant_weighted,
        "role_weighted": role_weighted,
        "role_count": role_count,
        "kind_units": kind_units,
        "kind_weighted": kind_weighted,
    }, None


def _store_contribution(
    state: State,
    update: dict[str, Any],
) -> None:
    state.contributions[update["contribution_key"]] = Contribution(
        update["kind_units"],
        update["kind_weighted"],
    )
    state.participant_totals[update["participant_key"]] = ParticipantTotal(
        update["raw_total"],
        update["participant_weighted"],
    )
    state.role_totals[update["role_key"]] = RoleTotal(
        update["role_weighted"],
        update["role_count"],
    )


def set_reward_budget(
    state: State,
    manifest: Manifest,
    event: dict[str, Any],
) -> Outcome:
    if event["actor"] != manifest.authorities.reward:
        return failure("UNAUTHORIZED")
    epoch = current_epoch(state, manifest)
    if event["epoch"] >= epoch:
        return failure("TOO_EARLY")
    key = (event["epoch"], event["role"])
    role_total = state.role_totals.get(key)
    if role_total is None or role_total.weighted_units == 0:
        return failure("NOT_FOUND")
    if key in state.budgets:
        return failure("ALREADY_EXISTS")
    if event["amount"] == 0:
        return failure("ZERO_AMOUNT")
    state.budgets[key] = Budget(
        amount=event["amount"],
        total_weight=role_total.weighted_units,
        participant_count=role_total.participant_count,
    )
    return success()


def settle_entitlement(
    state: State,
    manifest: Manifest,
    event: dict[str, Any],
) -> Outcome:
    if event["actor"] != manifest.authorities.reward:
        return failure("UNAUTHORIZED")
    budget_key = (event["epoch"], event["role"])
    budget = state.budgets.get(budget_key)
    if budget is None:
        return failure("NOT_FOUND")
    participant_key = budget_key + (event["participant"],)
    contribution = state.participant_totals.get(participant_key)
    if contribution is None:
        return failure("NOT_ELIGIBLE")
    if participant_key in state.entitlements:
        return failure("ALREADY_EXISTS")

    quotient, remainder = divmod(budget.amount, budget.total_weight)
    whole = checked_mul(quotient, contribution.weighted_units)
    fraction = checked_mul(remainder, contribution.weighted_units)
    if whole is None or fraction is None:
        return failure("OVERFLOW")
    amount = checked_add(whole, fraction // budget.total_weight)
    allocated = None if amount is None else checked_add(budget.allocated, amount)
    settled_count = checked_add(budget.settled_count, 1)
    if amount is None or allocated is None or settled_count is None:
        return failure("OVERFLOW")
    state.entitlements[participant_key] = Entitlement(
        participant_weight=contribution.weighted_units,
        amount=amount,
    )
    budget.allocated = allocated
    budget.settled_count = settled_count
    return success()


def finalize_budget(
    state: State,
    manifest: Manifest,
    event: dict[str, Any],
) -> Outcome:
    if event["actor"] != manifest.authorities.reward:
        return failure("UNAUTHORIZED")
    budget = state.budgets.get((event["epoch"], event["role"]))
    if budget is None:
        return failure("NOT_FOUND")
    if budget.finalized:
        return failure("ALREADY_EXISTS")
    if budget.settled_count != budget.participant_count:
        return failure("TOO_EARLY")
    budget.finalized = True
    budget.remainder = budget.amount - budget.allocated
    return success()


def _eligible(participant: Participant, epoch: int) -> bool:
    if participant.phase not in {"active", "exit_pending"}:
        return False
    if participant.jailed_until_epoch is not None:
        return False
    return participant.phase == "active" or epoch < participant.exit_epoch


HANDLERS = {
    "attest_contribution": attest_contribution,
    "set_reward_budget": set_reward_budget,
    "settle_entitlement": settle_entitlement,
    "finalize_budget": finalize_budget,
}
