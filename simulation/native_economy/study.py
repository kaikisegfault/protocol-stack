#!/usr/bin/env python3
"""Run a deterministic range of native-economy research scenarios."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.native_economy.engine import simulate
from simulation.native_economy.scenario import generate_scenario
from simulation.native_economy.types import MAX_U64, domain_digest


def run_study(seed_start: int, seed_count: int, rounds: int) -> dict:
    if type(seed_start) is not int or not 0 <= seed_start <= MAX_U64:
        raise ValueError("seed_start must be a u64")
    if type(seed_count) is not int or not 1 <= seed_count <= 256:
        raise ValueError("seed_count must be in 1..256")
    if seed_start > MAX_U64 - (seed_count - 1):
        raise ValueError("seed range exceeds u64")

    runs = []
    flow_totals: dict[str, int] = {}
    for seed in range(seed_start, seed_start + seed_count):
        manifest, events = generate_scenario(seed, rounds)
        result = simulate(manifest, events)
        metrics = result["metrics"]
        for key, value in metrics["flows"].items():
            flow_totals[key] = flow_totals.get(key, 0) + value
        runs.append(
            {
                "seed": seed,
                "event_count": len(events),
                "accepted_count": sum(
                    record["accepted"] for record in result["records"]
                ),
                "trace_digest": result["trace_digest"],
                "final_state_digest": result["records"][-1]["state_digest_after"],
                "inventory": metrics["inventory"],
                "exposure": metrics["exposure"],
                "account_distribution": metrics["account_distribution"],
                "flows": metrics["flows"],
            }
        )

    report = {
        "schema": "protocol-stack/native-economy-study/v1",
        "generator": "SplitMix64-v1",
        "seed_start": seed_start,
        "seed_count": seed_count,
        "rounds": rounds,
        "all_events_accepted": all(
            run["accepted_count"] == run["event_count"] for run in runs
        ),
        "all_runs_conserved": all(_conserved(run["inventory"]) for run in runs),
        "flow_totals": flow_totals,
        "runs": runs,
    }
    report["study_digest"] = domain_digest(
        "protocol-stack:native-economy:study-v1",
        report,
    )
    return report


def _conserved(inventory: dict[str, int]) -> bool:
    custody = sum(
        inventory[key]
        for key in (
            "accounts",
            "fee_pool",
            "treasury",
            "escrows",
            "bonded",
            "unbonding",
            "reward_pool",
            "validator_claims",
            "node_claims",
            "penalty_pool",
        )
    )
    return (
        custody == inventory["issued_supply"]
        and inventory["issued_supply"] + inventory["issuance_capacity"]
        == inventory["supply_limit"]
    )


def _u64(text: str) -> int:
    value = int(text, 0)
    if not 0 <= value <= MAX_U64:
        raise argparse.ArgumentTypeError("value must be a u64")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
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
