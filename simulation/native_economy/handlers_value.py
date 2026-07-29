"""Height, issuance, fee, treasury, and escrow operations."""

from __future__ import annotations

from typing import Any

from .operations import Outcome, credit_account, failure, success
from .types import (
    MAX_U64,
    Escrow,
    Manifest,
    State,
    checked_add,
    checked_mul,
    current_epoch,
)


def advance_height(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    if event["actor"] != manifest.authorities.clock:
        return failure("UNAUTHORIZED")
    if state.height == MAX_U64:
        return failure("OVERFLOW")
    if event["to_height"] != state.height + 1:
        return failure("INVALID_TARGET")
    state.height = event["to_height"]
    return success()


def issue(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    if event["actor"] != manifest.authorities.issuance:
        return failure("UNAUTHORIZED")
    amount = event["amount"]
    if amount == 0:
        return failure("ZERO_AMOUNT")
    capacity = manifest.parameters.supply_limit - state.issued_supply
    if amount > capacity:
        return failure("SUPPLY_LIMIT")
    treasury = checked_add(state.treasury, amount)
    issued_supply = checked_add(state.issued_supply, amount)
    if treasury is None or issued_supply is None:
        return failure("OVERFLOW")
    state.treasury = treasury
    state.issued_supply = issued_supply
    return success(("issuance_capacity", -amount), ("treasury", amount))


def transfer(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    del manifest
    source = event["source"]
    destination = event["destination"]
    if event["actor"] != source:
        return failure("UNAUTHORIZED")
    amount = event["amount"]
    if amount == 0:
        return failure("ZERO_AMOUNT")
    if source == destination:
        return failure("INVALID_TARGET")
    if source not in state.accounts:
        return failure("NOT_FOUND")
    if state.accounts[source] < amount:
        return failure("INSUFFICIENT_FUNDS")
    if checked_add(state.accounts.get(destination, 0), amount) is None:
        return failure("OVERFLOW")
    state.accounts[source] -= amount
    if not credit_account(state, destination, amount):
        raise AssertionError("prechecked destination overflow")
    return success(
        (f"account:{source}", -amount),
        (f"account:{destination}", amount),
    )


def charge_fee(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    del manifest
    account = event["account"]
    if event["actor"] != account:
        return failure("UNAUTHORIZED")
    amount = event["amount"]
    if amount == 0:
        return failure("ZERO_AMOUNT")
    if account not in state.accounts:
        return failure("NOT_FOUND")
    if state.accounts[account] < amount:
        return failure("INSUFFICIENT_FUNDS")
    fee_pool = checked_add(state.fee_pool, amount)
    if fee_pool is None:
        return failure("OVERFLOW")
    state.accounts[account] -= amount
    state.fee_pool = fee_pool
    return success((f"account:{account}", -amount), ("fee_pool", amount))


def allocate_fees(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    if event["actor"] != manifest.authorities.fee_allocation:
        return failure("UNAUTHORIZED")
    amount = event["amount"]
    if amount == 0:
        return failure("ZERO_AMOUNT")
    if state.fee_pool < amount:
        return failure("INSUFFICIENT_FUNDS")

    denominator = manifest.parameters.fee_split_denominator
    parts = manifest.parameters.fee_reward_parts
    quotient, remainder = divmod(amount, denominator)
    whole = checked_mul(quotient, parts)
    fraction_product = checked_mul(remainder, parts)
    if whole is None or fraction_product is None:
        return failure("OVERFLOW")
    reward = checked_add(whole, fraction_product // denominator)
    if reward is None:
        return failure("OVERFLOW")
    treasury_credit = amount - reward
    reward_pool = checked_add(state.reward_pool, reward)
    treasury = checked_add(state.treasury, treasury_credit)
    if reward_pool is None or treasury is None:
        return failure("OVERFLOW")

    state.fee_pool -= amount
    state.reward_pool = reward_pool
    state.treasury = treasury
    return success(
        ("fee_pool", -amount),
        ("reward_pool", reward),
        ("treasury", treasury_credit),
    )


def treasury_grant(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    if event["actor"] != manifest.authorities.treasury:
        return failure("UNAUTHORIZED")
    amount = event["amount"]
    if amount == 0:
        return failure("ZERO_AMOUNT")
    if state.treasury < amount:
        return failure("INSUFFICIENT_FUNDS")
    if checked_add(state.accounts.get(event["recipient"], 0), amount) is None:
        return failure("OVERFLOW")
    state.treasury -= amount
    if not credit_account(state, event["recipient"], amount):
        raise AssertionError("prechecked recipient overflow")
    return success(
        ("treasury", -amount),
        (f"account:{event['recipient']}", amount),
    )


def fund_rewards(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    if event["actor"] != manifest.authorities.treasury:
        return failure("UNAUTHORIZED")
    amount = event["amount"]
    if amount == 0:
        return failure("ZERO_AMOUNT")
    if state.treasury < amount:
        return failure("INSUFFICIENT_FUNDS")
    reward_pool = checked_add(state.reward_pool, amount)
    if reward_pool is None:
        return failure("OVERFLOW")
    state.treasury -= amount
    state.reward_pool = reward_pool
    return success(("treasury", -amount), ("reward_pool", amount))


def open_escrow(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    if event["source_kind"] == "account":
        if event["actor"] != event["source"]:
            return failure("UNAUTHORIZED")
    elif event["actor"] != manifest.authorities.treasury:
        return failure("UNAUTHORIZED")

    amount = event["amount"]
    if amount == 0:
        return failure("ZERO_AMOUNT")
    escrow_id = event["escrow_id"]
    if escrow_id in state.escrows:
        return failure("ALREADY_EXISTS")
    if event["unlock_epoch"] <= current_epoch(state, manifest):
        return failure("INVALID_TARGET")

    if event["source_kind"] == "account":
        source = event["source"]
        if source not in state.accounts:
            return failure("NOT_FOUND")
        if state.accounts[source] < amount:
            return failure("INSUFFICIENT_FUNDS")
        source_bucket = f"account:{source}"
    else:
        if event["source"] != "treasury":
            return failure("INVALID_TARGET")
        if state.treasury < amount:
            return failure("INSUFFICIENT_FUNDS")
        source_bucket = "treasury"

    if event["source_kind"] == "account":
        state.accounts[event["source"]] -= amount
    else:
        state.treasury -= amount
    state.escrows[escrow_id] = Escrow(
        escrow_kind=event["escrow_kind"],
        beneficiary=event["beneficiary"],
        amount=amount,
        unlock_epoch=event["unlock_epoch"],
    )
    return success(
        (source_bucket, -amount),
        (f"escrow:{escrow_id}", amount),
    )


def release_escrow(state: State, manifest: Manifest, event: dict[str, Any]) -> Outcome:
    if event["actor"] != manifest.authorities.escrow:
        return failure("UNAUTHORIZED")
    escrow_id = event["escrow_id"]
    escrow = state.escrows.get(escrow_id)
    if escrow is None:
        return failure("NOT_FOUND")
    if current_epoch(state, manifest) < escrow.unlock_epoch:
        return failure("TOO_EARLY")
    if checked_add(state.accounts.get(escrow.beneficiary, 0), escrow.amount) is None:
        return failure("OVERFLOW")
    del state.escrows[escrow_id]
    if not credit_account(state, escrow.beneficiary, escrow.amount):
        raise AssertionError("prechecked beneficiary overflow")
    return success(
        (f"escrow:{escrow_id}", -escrow.amount),
        (f"account:{escrow.beneficiary}", escrow.amount),
    )


HANDLERS = {
    "advance_height": advance_height,
    "issue": issue,
    "transfer": transfer,
    "charge_fee": charge_fee,
    "allocate_fees": allocate_fees,
    "treasury_grant": treasury_grant,
    "fund_rewards": fund_rewards,
    "open_escrow": open_escrow,
    "release_escrow": release_escrow,
}
