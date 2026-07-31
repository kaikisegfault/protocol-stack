"""Nominal native-economy targets for one stress run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .design import Configuration


@dataclass(frozen=True)
class Flow:
    events: list[dict[str, Any]]
    privileged: dict[str, str]
    malicious_event: dict[str, Any]


def build_economy_flow(
    config: Configuration,
    funding_events: list[dict[str, Any]],
) -> Flow:
    events: list[dict[str, Any]] = []
    privileged: dict[str, str] = {}
    height = 0
    sequence = 0

    def append(kind: str, actor: str, capability: str | None, **fields: Any) -> None:
        nonlocal sequence
        sequence += 1
        event = {
            "id": f"e_event_{sequence:04d}",
            "height": height,
            "kind": kind,
            "actor": actor,
            **fields,
        }
        events.append(event)
        if capability is not None:
            privileged[event["id"]] = capability

    append(
        "issue",
        "issuer",
        "issuance",
        amount=config.values["issuance_amount"],
    )
    append(
        "charge_fee",
        "alice",
        None,
        account="alice",
        amount=config.values["fee_volume"],
    )
    append(
        "allocate_fees",
        "fee_allocator",
        "fee_allocation",
        amount=config.values["fee_volume"],
    )
    append(
        "fund_rewards",
        "treasury",
        "treasury",
        amount=2 * int(config.values["reward_budget_per_role"]),
    )
    bond = int(config.values["validator_minimum_bond"])
    for suffix, owner, validator in (
        ("a", "alice", "validator_a"),
        ("b", "bob", "validator_b"),
    ):
        append(
            "bond",
            owner,
            None,
            bond_id=f"bond_{suffix}",
            owner=owner,
            validator=validator,
            amount=bond,
        )
    penalty = bond * int(config.values["penalty_parts"]) // 10
    if penalty:
        append(
            "penalize",
            "penalty",
            "penalty",
            source_kind="bond",
            position_id="bond_a",
            amount=penalty,
        )
        append(
            "route_penalty",
            "penalty",
            "penalty",
            amount=penalty,
        )

    for event in funding_events:
        events.append(dict(event))
        privileged[event["id"]] = "reward"
    for event in funding_events:
        payout = {
            "validator_a": "alice",
            "validator_b": "bob",
            "node_a": "carol",
            "node_b": "dave",
        }[event["participant"]]
        append(
            "claim_reward",
            payout,
            None,
            role=event["role"],
            participant=event["participant"],
            amount=event["amount"],
        )

    append(
        "begin_unbond",
        "bob",
        None,
        bond_id="bond_b",
        unbonding_id="unbonding_b",
        amount=bond // 2,
    )
    delay = int(config.values["exit_unbond_delay_epochs"])
    target = height + delay
    while height < target:
        append("advance_height", "clock", "clock", to_height=height + 1)
        height += 1
    append(
        "complete_unbond",
        "bob",
        None,
        unbonding_id="unbonding_b",
    )
    malicious = {
        "id": "malicious_issue",
        "height": 0,
        "kind": "issue",
        "actor": "issuer",
        "amount": 2_000,
    }
    return Flow(events, privileged, malicious)
