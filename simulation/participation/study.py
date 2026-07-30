#!/usr/bin/env python3
"""Run a deterministic range of participation and claim-funding scenarios."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.native_economy.engine import simulate as simulate_economy
from simulation.participation.adapter import build_funding_events
from simulation.participation.domain import MAX_U64, domain_digest
from simulation.participation.engine import simulate
from simulation.participation.scenario import generate_scenario


def run_study(seed_start: int, seed_count: int, rounds: int) -> dict:
    _validate_bounds(seed_start, seed_count)
    runs = []
    funded_total = 0
    retained_total = 0
    for seed in range(seed_start, seed_start + seed_count):
        manifest, events = generate_scenario(seed, rounds)
        result = simulate(manifest, events)
        budget_amount = sum(
            budget["amount"] for budget in result["final_state"]["budgets"]
        )
        economy_manifest = _economy_manifest(result, budget_amount)
        funding_events = []
        for budget in result["final_state"]["budgets"]:
            funding_events.extend(
                build_funding_events(
                    result,
                    manifest,
                    economy_manifest,
                    epoch=budget["epoch"],
                    role=budget["role"],
                    height=0,
                )
            )
        economy_result = simulate_economy(economy_manifest, funding_events)
        funded = sum(event["amount"] for event in funding_events)
        retained = economy_result["final_state"]["reward_pool"]
        funded_total += funded
        retained_total += retained
        runs.append(
            {
                "seed": seed,
                "event_count": len(events),
                "accepted_count": sum(
                    record["accepted"] for record in result["records"]
                ),
                "accepted_proofs": len(
                    result["final_state"]["accepted_proof_ids"]
                ),
                "trace_digest": result["trace_digest"],
                "participants": result["metrics"]["participants"],
                "contributions": result["metrics"]["contributions"],
                "budgets": result["metrics"]["budgets"],
                "wait_epochs": result["metrics"]["wait_epochs"],
                "funding_event_count": len(funding_events),
                "funded_amount": funded,
                "retained_reward_pool": retained,
                "all_claims_funded": all(
                    record["accepted"] for record in economy_result["records"]
                ),
            }
        )
    report = {
        "schema": "protocol-stack/participation-study/v1",
        "generator": "SplitMix64-v1",
        "seed_start": seed_start,
        "seed_count": seed_count,
        "rounds": rounds,
        "all_events_accepted": all(
            run["event_count"] == run["accepted_count"] for run in runs
        ),
        "all_claims_funded": all(run["all_claims_funded"] for run in runs),
        "funded_amount": funded_total,
        "retained_reward_pool": retained_total,
        "runs": runs,
    }
    report["study_digest"] = domain_digest(
        "protocol-stack:participation:study-v1",
        report,
    )
    return report


def _economy_manifest(result: dict, reward_pool: int) -> dict:
    participants = result["final_state"]["participants"]
    validators = {
        key: value["payout_account"]
        for key, value in participants.items()
        if value["role"] == "validator"
    }
    nodes = {
        key: value["payout_account"]
        for key, value in participants.items()
        if value["role"] == "node"
    }
    accounts = {value: 0 for value in [*validators.values(), *nodes.values()]}
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
        "participants": {"validators": validators, "nodes": nodes},
        "genesis": {
            "height": 0,
            "issued_supply": reward_pool,
            "accounts": accounts,
            "fee_pool": 0,
            "treasury": 0,
            "reward_pool": reward_pool,
            "penalty_pool": 0,
        },
    }


def _validate_bounds(seed_start: int, seed_count: int) -> None:
    if type(seed_start) is not int or not 0 <= seed_start <= MAX_U64:
        raise ValueError("seed_start must be a u64")
    if type(seed_count) is not int or not 1 <= seed_count <= 256:
        raise ValueError("seed_count must be in 1..256")
    if seed_start > MAX_U64 - (seed_count - 1):
        raise ValueError("seed range exceeds u64")


def _u64(text: str) -> int:
    value = int(text, 0)
    if not 0 <= value <= MAX_U64:
        raise argparse.ArgumentTypeError("value must be a u64")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-start", type=_u64, default=0)
    parser.add_argument("--seed-count", type=int, default=24)
    parser.add_argument("--rounds", type=int, default=4)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    try:
        report = run_study(
            arguments.seed_start,
            arguments.seed_count,
            arguments.rounds,
        )
    except ValueError as error:
        parser.error(str(error))
    text = json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if arguments.output is None:
        sys.stdout.write(text)
    else:
        arguments.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
