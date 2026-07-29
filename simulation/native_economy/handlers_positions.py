"""Staking, reward, and penalty operations."""

from __future__ import annotations

from typing import Any

from .operations import Outcome, credit_account, failure, success
from .types import (
    Bond,
    Manifest,
    State,
    Unbonding,
    checked_add,
    current_epoch,
)


def bond(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    owner = event["owner"]
    if event["actor"] != owner:
        return failure("UNAUTHORIZED")
    amount = event["amount"]
    if amount == 0:
        return failure("ZERO_AMOUNT")
    if event["validator"] not in manifest.participants.validators:
        return failure("NOT_FOUND")
    bond_id = event["bond_id"]
    if bond_id in state.bonds:
        return failure("ALREADY_EXISTS")
    if owner not in state.accounts:
        return failure("NOT_FOUND")
    if state.accounts[owner] < amount:
        return failure("INSUFFICIENT_FUNDS")
    state.accounts[owner] -= amount
    state.bonds[bond_id] = Bond(
        owner=owner,
        validator=event["validator"],
        amount=amount,
    )
    return success(
        (f"account:{owner}", -amount),
        (f"bond:{bond_id}", amount),
    )


def begin_unbond(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    bond_id = event["bond_id"]
    position = state.bonds.get(bond_id)
    if position is None:
        return failure("NOT_FOUND")
    if event["actor"] != position.owner:
        return failure("UNAUTHORIZED")
    amount = event["amount"]
    if amount == 0:
        return failure("ZERO_AMOUNT")
    unbonding_id = event["unbonding_id"]
    if unbonding_id in state.unbondings:
        return failure("ALREADY_EXISTS")
    if position.amount < amount:
        return failure("INSUFFICIENT_FUNDS")
    release_epoch = checked_add(
        current_epoch(state, manifest),
        manifest.parameters.unbonding_epochs,
    )
    if release_epoch is None:
        return failure("OVERFLOW")

    position.amount -= amount
    if position.amount == 0:
        del state.bonds[bond_id]
    state.unbondings[unbonding_id] = Unbonding(
        owner=position.owner,
        validator=position.validator,
        amount=amount,
        release_epoch=release_epoch,
    )
    return success(
        (f"bond:{bond_id}", -amount),
        (f"unbonding:{unbonding_id}", amount),
    )


def complete_unbond(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    unbonding_id = event["unbonding_id"]
    position = state.unbondings.get(unbonding_id)
    if position is None:
        return failure("NOT_FOUND")
    if event["actor"] != position.owner:
        return failure("UNAUTHORIZED")
    if current_epoch(state, manifest) < position.release_epoch:
        return failure("TOO_EARLY")
    if checked_add(state.accounts.get(position.owner, 0), position.amount) is None:
        return failure("OVERFLOW")
    del state.unbondings[unbonding_id]
    if not credit_account(state, position.owner, position.amount):
        raise AssertionError("prechecked owner overflow")
    return success(
        (f"unbonding:{unbonding_id}", -position.amount),
        (f"account:{position.owner}", position.amount),
    )


def allocate_reward(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    if event["actor"] != manifest.authorities.reward:
        return failure("UNAUTHORIZED")
    amount = event["amount"]
    if amount == 0:
        return failure("ZERO_AMOUNT")
    claims, participants, bucket_prefix = _role_maps(state, manifest, event["role"])
    participant = event["participant"]
    if participant not in participants:
        return failure("NOT_FOUND")
    if state.reward_pool < amount:
        return failure("INSUFFICIENT_FUNDS")
    claim = checked_add(claims.get(participant, 0), amount)
    if claim is None:
        return failure("OVERFLOW")
    state.reward_pool -= amount
    claims[participant] = claim
    return success(
        ("reward_pool", -amount),
        (f"{bucket_prefix}:{participant}", amount),
    )


def claim_reward(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    claims, participants, bucket_prefix = _role_maps(state, manifest, event["role"])
    participant = event["participant"]
    payout_account = participants.get(participant)
    if payout_account is None:
        return failure("NOT_FOUND")
    if event["actor"] != payout_account:
        return failure("UNAUTHORIZED")
    amount = event["amount"]
    if amount == 0:
        return failure("ZERO_AMOUNT")
    claim = claims.get(participant)
    if claim is None:
        return failure("NOT_FOUND")
    if claim < amount:
        return failure("INSUFFICIENT_FUNDS")
    if checked_add(state.accounts.get(payout_account, 0), amount) is None:
        return failure("OVERFLOW")

    remaining = claim - amount
    if remaining == 0:
        del claims[participant]
    else:
        claims[participant] = remaining
    if not credit_account(state, payout_account, amount):
        raise AssertionError("prechecked payout overflow")
    return success(
        (f"{bucket_prefix}:{participant}", -amount),
        (f"account:{payout_account}", amount),
    )


def penalize(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    if event["actor"] != manifest.authorities.penalty:
        return failure("UNAUTHORIZED")
    amount = event["amount"]
    if amount == 0:
        return failure("ZERO_AMOUNT")
    positions = state.bonds if event["source_kind"] == "bond" else state.unbondings
    position = positions.get(event["position_id"])
    if position is None:
        return failure("NOT_FOUND")
    if position.amount < amount:
        return failure("INSUFFICIENT_FUNDS")
    penalty_pool = checked_add(state.penalty_pool, amount)
    if penalty_pool is None:
        return failure("OVERFLOW")

    position.amount -= amount
    if position.amount == 0:
        del positions[event["position_id"]]
    state.penalty_pool = penalty_pool
    bucket = f"{event['source_kind']}:{event['position_id']}"
    return success((bucket, -amount), ("penalty_pool", amount))


def route_penalty(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    if event["actor"] != manifest.authorities.penalty:
        return failure("UNAUTHORIZED")
    amount = event["amount"]
    if amount == 0:
        return failure("ZERO_AMOUNT")
    if state.penalty_pool < amount:
        return failure("INSUFFICIENT_FUNDS")
    treasury = checked_add(state.treasury, amount)
    if treasury is None:
        return failure("OVERFLOW")
    state.penalty_pool -= amount
    state.treasury = treasury
    return success(("penalty_pool", -amount), ("treasury", amount))


def _role_maps(
    state: State,
    manifest: Manifest,
    role: str,
) -> tuple[dict[str, int], dict[str, str], str]:
    if role == "validator":
        return (
            state.validator_claims,
            manifest.participants.validators,
            "validator_claim",
        )
    return state.node_claims, manifest.participants.nodes, "node_claim"


HANDLERS = {
    "bond": bond,
    "begin_unbond": begin_unbond,
    "complete_unbond": complete_unbond,
    "allocate_reward": allocate_reward,
    "claim_reward": claim_reward,
    "penalize": penalize,
    "route_penalty": route_penalty,
}
