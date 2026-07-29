"""Exact integer and rational simulation metrics."""

from __future__ import annotations

import math
from typing import Any

from .domain import Manifest, State

_FLOW_KEYS = {
    "issuance": 0,
    "fees_charged": 0,
    "fees_allocated": 0,
    "fee_to_rewards": 0,
    "fee_to_treasury": 0,
    "treasury_grants": 0,
    "reward_funding": 0,
    "escrow_opened": 0,
    "escrow_released": 0,
    "stake_bonded": 0,
    "unbonding_begun": 0,
    "unbonding_completed": 0,
    "validator_rewards_allocated": 0,
    "node_rewards_allocated": 0,
    "validator_rewards_claimed": 0,
    "node_rewards_claimed": 0,
    "penalties_assessed": 0,
    "penalties_routed": 0,
}


def rational(numerator: int, denominator: int) -> dict[str, int]:
    if denominator <= 0:
        raise ValueError("rational denominator must be positive")
    if numerator == 0:
        return {"numerator": 0, "denominator": 1}
    divisor = math.gcd(numerator, denominator)
    return {
        "numerator": numerator // divisor,
        "denominator": denominator // divisor,
    }


def build_metrics(
    state: State,
    manifest: Manifest,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    accounts = list(state.accounts.values())
    account_total = sum(accounts)
    escrow_total = sum(record.amount for record in state.escrows.values())
    bonded_total = sum(record.amount for record in state.bonds.values())
    unbonding_total = sum(record.amount for record in state.unbondings.values())
    validator_claims = sum(state.validator_claims.values())
    node_claims = sum(state.node_claims.values())
    locked = escrow_total + bonded_total + unbonding_total
    protocol_owned = (
        state.fee_pool + state.treasury + state.reward_pool + state.penalty_pool
    )
    return {
        "inventory": {
            "supply_limit": manifest.parameters.supply_limit,
            "issued_supply": state.issued_supply,
            "issuance_capacity": (
                manifest.parameters.supply_limit - state.issued_supply
            ),
            "accounts": account_total,
            "fee_pool": state.fee_pool,
            "treasury": state.treasury,
            "escrows": escrow_total,
            "bonded": bonded_total,
            "unbonding": unbonding_total,
            "reward_pool": state.reward_pool,
            "validator_claims": validator_claims,
            "node_claims": node_claims,
            "penalty_pool": state.penalty_pool,
        },
        "exposure": {
            "locked_value": locked,
            "locked_fraction": rational(locked, state.issued_supply),
            "claimable_rewards": validator_claims + node_claims,
            "protocol_owned": protocol_owned,
        },
        "account_distribution": _distribution(accounts),
        "flows": _flows(records),
    }


def _distribution(values: list[int]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "sum": 0,
            "minimum": 0,
            "maximum": 0,
            "mean": rational(0, 1),
            "gini": rational(0, 1),
        }
    ordered = sorted(values)
    total = sum(ordered)
    count = len(ordered)
    numerator = sum(
        (2 * index - count - 1) * value
        for index, value in enumerate(ordered, start=1)
    )
    return {
        "count": count,
        "sum": total,
        "minimum": ordered[0],
        "maximum": ordered[-1],
        "mean": rational(total, count),
        "gini": rational(numerator, count * total) if total else rational(0, 1),
    }


def _flows(records: list[dict[str, Any]]) -> dict[str, int]:
    flows = dict(_FLOW_KEYS)
    for record in records:
        if not record["accepted"]:
            continue
        kind = record["kind"]
        journal = record["journal"]
        positives = {
            entry["bucket"]: entry["delta"]
            for entry in journal
            if entry["delta"] > 0
        }
        negatives = {
            entry["bucket"]: -entry["delta"]
            for entry in journal
            if entry["delta"] < 0
        }
        if kind == "issue":
            flows["issuance"] += positives.get("treasury", 0)
        elif kind == "charge_fee":
            flows["fees_charged"] += positives.get("fee_pool", 0)
        elif kind == "allocate_fees":
            flows["fees_allocated"] += negatives.get("fee_pool", 0)
            flows["fee_to_rewards"] += positives.get("reward_pool", 0)
            flows["fee_to_treasury"] += positives.get("treasury", 0)
        elif kind == "treasury_grant":
            flows["treasury_grants"] += negatives.get("treasury", 0)
        elif kind == "fund_rewards":
            flows["reward_funding"] += positives.get("reward_pool", 0)
        elif kind == "open_escrow":
            flows["escrow_opened"] += _prefix_total(positives, "escrow:")
        elif kind == "release_escrow":
            flows["escrow_released"] += _prefix_total(negatives, "escrow:")
        elif kind == "bond":
            flows["stake_bonded"] += _prefix_total(positives, "bond:")
        elif kind == "begin_unbond":
            flows["unbonding_begun"] += _prefix_total(positives, "unbonding:")
        elif kind == "complete_unbond":
            flows["unbonding_completed"] += _prefix_total(negatives, "unbonding:")
        elif kind == "allocate_reward":
            role = "validator" if _has_prefix(positives, "validator_claim:") else "node"
            flows[f"{role}_rewards_allocated"] += _claim_total(positives)
        elif kind == "claim_reward":
            role = "validator" if _has_prefix(negatives, "validator_claim:") else "node"
            flows[f"{role}_rewards_claimed"] += _claim_total(negatives)
        elif kind == "penalize":
            flows["penalties_assessed"] += positives.get("penalty_pool", 0)
        elif kind == "route_penalty":
            flows["penalties_routed"] += negatives.get("penalty_pool", 0)
    return flows


def _prefix_total(entries: dict[str, int], prefix: str) -> int:
    return sum(value for key, value in entries.items() if key.startswith(prefix))


def _has_prefix(entries: dict[str, int], prefix: str) -> bool:
    return any(key.startswith(prefix) for key in entries)


def _claim_total(entries: dict[str, int]) -> int:
    return _prefix_total(entries, "validator_claim:") + _prefix_total(
        entries,
        "node_claim:",
    )
