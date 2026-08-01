"""Accepted participation-adapter and native-funding cross-checks."""

from __future__ import annotations

from typing import Any

from simulation.native_economy.engine import simulate as simulate_economy
from simulation.participation.adapter import build_funding_events
from simulation.participation.domain import checked_add, checked_mul, domain_digest
from simulation.participation.engine import simulate as simulate_participation

from .model import evaluate_point


def _sum(values) -> int:
    result = 0
    for value in values:
        checked = checked_add(result, value)
        if checked is None:
            raise OverflowError("cross-check total exceeds u64")
        result = checked
    return result


def _digest(label: str) -> str:
    return domain_digest("protocol-stack:reward-distribution:evidence-v1", label)


def _participation_manifest(max_participants: int) -> dict[str, Any]:
    return {
        "schema": "protocol-stack/participation-simulation-manifest/v1",
        "research_only": True,
        "parameters": {
            "epoch_length": 1,
            "activation_delay_epochs": 1,
            "exit_delay_epochs": 1,
            "removal_hold_epochs": 1,
            "max_jail_epochs": 2,
            "max_participants": max_participants,
            "validator_minimum_bond": 1,
            "max_units_per_proof": 100,
            "max_units_per_participant_epoch": 100,
        },
        "authorities": {
            "clock": "clock",
            "registration": "registrar",
            "stake": "stake_verifier",
            "lifecycle": "lifecycle",
            "enforcement": "enforcement",
            "reward": "reward",
        },
        "contributions": {
            "validators": {"vote": {"verifier": "vote_verifier", "weight": 1}},
            "nodes": {
                "storage": {"verifier": "storage_verifier", "weight": 1}
            },
        },
        "genesis": {"height": 0},
    }


def _event(event_id: str, height: int, kind: str, actor: str, **fields) -> dict:
    return {"id": event_id, "height": height, "kind": kind, "actor": actor, **fields}


def _participation_events(participants: dict, scores: dict[str, int], budget: int):
    events = []
    for index, (participant, identity) in enumerate(sorted(participants.items())):
        events.append(
            _event(
                f"register_{index}",
                0,
                "register_node",
                "registrar",
                participant=participant,
                owner=identity["principal"],
                payout_account=identity["payout_account"],
                proof_id=f"registration_proof_{index}",
                evidence_digest=_digest(f"register:{participant}"),
            )
        )
    events.append(_event("advance_1", 0, "advance_height", "clock", to_height=1))
    for index, participant in enumerate(sorted(participants)):
        events.append(
            _event(f"activate_{index}", 1, "activate", "lifecycle", participant=participant)
        )
    for index, (participant, units) in enumerate(sorted(scores.items())):
        if units == 0:
            continue
        events.append(
            _event(
                f"contribute_{index}",
                1,
                "attest_contribution",
                "storage_verifier",
                participant=participant,
                role="node",
                contribution_kind="storage",
                epoch=1,
                units=units,
                proof_id=f"contribution_proof_{index}",
                evidence_digest=_digest(f"contribute:{participant}"),
            )
        )
    events.append(_event("advance_2", 1, "advance_height", "clock", to_height=2))
    events.append(
        _event("set_budget", 2, "set_reward_budget", "reward", epoch=1, role="node", amount=budget)
    )
    for index, participant in enumerate(sorted(key for key, value in scores.items() if value)):
        events.append(
            _event(
                f"settle_{index}",
                2,
                "settle_entitlement",
                "reward",
                epoch=1,
                role="node",
                participant=participant,
            )
        )
    events.append(
        _event("finalize_budget", 2, "finalize_budget", "reward", epoch=1, role="node")
    )
    return events


def economy_manifest(participants: dict, reward_pool: int) -> dict[str, Any]:
    accounts = sorted({value["payout_account"] for value in participants.values()})
    return {
        "schema": "protocol-stack/native-economy-simulation-manifest/v1",
        "research_only": True,
        "parameters": {
            "supply_limit": reward_pool,
            "epoch_length": 1,
            "unbonding_epochs": 1,
            "fee_split_denominator": 1,
            "fee_reward_parts": 0,
        },
        "authorities": {
            "clock": "clock",
            "issuance": "issuer",
            "fee_allocation": "fee_allocator",
            "treasury": "treasury",
            "escrow": "escrow",
            "reward": "reward",
            "penalty": "penalty",
        },
        "participants": {
            "validators": {},
            "nodes": {
                key: value["payout_account"] for key, value in participants.items()
            },
        },
        "genesis": {
            "height": 0,
            "issued_supply": reward_pool,
            "accounts": {account: 0 for account in accounts},
            "fee_pool": 0,
            "treasury": 0,
            "reward_pool": reward_pool,
            "penalty_pool": 0,
        },
    }


def cross_check_proportional(
    case_id: str,
    participants: dict[str, dict[str, str]],
    scores: dict[str, int],
    budget: int = 100,
) -> dict[str, Any]:
    participation_manifest = _participation_manifest(len(participants))
    result = simulate_participation(
        participation_manifest,
        _participation_events(participants, scores, budget),
    )
    if not all(record["accepted"] for record in result["records"]):
        raise AssertionError("participation adapter cross-check event failed")
    economy = economy_manifest(participants, budget)
    funding_events = build_funding_events(
        result,
        participation_manifest,
        economy,
        epoch=1,
        role="node",
        height=0,
    )
    projected = evaluate_point(budget, scores, participants, "proportional")["payouts"]
    actual = {event["participant"]: event["amount"] for event in funding_events}
    if actual != projected:
        raise AssertionError("participation adapter entitlement mismatch")
    economy_result = simulate_economy(economy, funding_events)
    if not all(record["accepted"] for record in economy_result["records"]):
        raise AssertionError("native funding cross-check event failed")
    return {
        "case_id": case_id,
        "participant_count": len(participants),
        "funding_event_count": len(funding_events),
        "funded_amount": _sum(actual.values()),
        "participation_trace_digest": result["trace_digest"],
        "economy_trace_digest": economy_result["trace_digest"],
    }


def fund_trajectory(scenario: dict, trajectory: dict) -> dict[str, int | bool]:
    epoch_count = len(trajectory["epochs"])
    initial_pool = checked_mul(scenario["budget"], epoch_count)
    if initial_pool is None:
        raise OverflowError("trajectory funding exceeds u64")
    manifest = economy_manifest(scenario["participants"], initial_pool)
    events = []
    for epoch in trajectory["epochs"]:
        for participant, amount in sorted(epoch["payouts"].items()):
            if amount == 0:
                continue
            events.append(
                _event(
                    f"pay_{epoch['epoch']}_{participant}",
                    0,
                    "allocate_reward",
                    "reward",
                    role="node",
                    participant=participant,
                    amount=amount,
                )
            )
    result = simulate_economy(manifest, events)
    failures = _sum(int(not record["accepted"]) for record in result["records"])
    state = result["final_state"]
    claim_total = _sum(state["node_claims"].values())
    conserved = _sum((state["reward_pool"], claim_total)) == initial_pool
    if failures or not conserved or claim_total != trajectory["paid_credit"]:
        raise AssertionError("trajectory native funding mismatch")
    return {
        "native_funding_event_count": len(events),
        "native_funding_failures": failures,
        "native_claim_amount": claim_total,
        "native_funding_conserved": conserved,
    }
