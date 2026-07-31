#!/usr/bin/env python3
"""Run a deterministic range of adversarial authority scenarios."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.authority.adapter import build_authorized_events
from simulation.authority.domain import MAX_U64, domain_digest
from simulation.authority.engine import simulate
from simulation.authority.scenario import generate_scenario, scenario_targets
from simulation.native_economy.engine import simulate as simulate_economy
from simulation.participation.engine import simulate as simulate_participation


def run_study(seed_start: int, seed_count: int) -> dict:
    _validate_bounds(seed_start, seed_count)
    runs = []
    all_codes: set[str] = set()
    for seed in range(seed_start, seed_start + seed_count):
        manifest, events = generate_scenario(seed)
        result = simulate(manifest, events)
        codes = sorted({record["result"] for record in result["records"]})
        all_codes.update(codes)
        targets = scenario_targets(seed)
        economy_events = build_authorized_events(
            result,
            manifest,
            _economy_manifest(),
            module="native_economy",
            pairs=[("result_issue", targets["result_issue"])],
        )
        participation_events = build_authorized_events(
            result,
            manifest,
            _participation_manifest(),
            module="participation",
            pairs=[("result_register", targets["result_register"])],
        )
        economy_result = simulate_economy(_economy_manifest(), economy_events)
        participation_result = simulate_participation(
            _participation_manifest(), participation_events
        )
        runs.append(
            {
                "seed": seed,
                "event_count": len(events),
                "accepted_count": sum(
                    record["accepted"] for record in result["records"]
                ),
                "rejected_count": sum(
                    not record["accepted"] for record in result["records"]
                ),
                "accepted_proofs": len(
                    result["final_state"]["accepted_proof_ids"]
                ),
                "authorization_results": len(
                    result["final_state"]["authorization_results"]
                ),
                "trace_digest": result["trace_digest"],
                "result_codes": codes,
                "inventory": result["metrics"]["inventory"],
                "rotations_activated": result["metrics"]["rotations_activated"],
                "recoveries": result["metrics"]["recoveries"],
                "native_event_accepted": economy_result["records"][0]["accepted"],
                "participation_event_accepted": participation_result["records"][0][
                    "accepted"
                ],
            }
        )
    report = {
        "schema": "protocol-stack/authority-study/v1",
        "generator": "SplitMix64-v1",
        "seed_start": seed_start,
        "seed_count": seed_count,
        "all_adapter_events_accepted": all(
            run["native_event_accepted"] and run["participation_event_accepted"]
            for run in runs
        ),
        "observed_result_codes": sorted(all_codes),
        "runs": runs,
    }
    report["study_digest"] = domain_digest(
        "protocol-stack:authority:study-v1",
        report,
    )
    return report


def _economy_manifest() -> dict:
    return {
        "schema": "protocol-stack/native-economy-simulation-manifest/v1",
        "research_only": True,
        "parameters": {
            "supply_limit": 1000,
            "epoch_length": 10,
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
        "participants": {"validators": {}, "nodes": {"node_a": "alice"}},
        "genesis": {
            "height": 0,
            "issued_supply": 1,
            "accounts": {"alice": 0},
            "fee_pool": 0,
            "treasury": 1,
            "reward_pool": 0,
            "penalty_pool": 0,
        },
    }


def _participation_manifest() -> dict:
    return {
        "schema": "protocol-stack/participation-simulation-manifest/v1",
        "research_only": True,
        "parameters": {
            "epoch_length": 10,
            "activation_delay_epochs": 1,
            "exit_delay_epochs": 1,
            "removal_hold_epochs": 1,
            "max_jail_epochs": 2,
            "max_participants": 8,
            "validator_minimum_bond": 1,
            "max_units_per_proof": 10,
            "max_units_per_participant_epoch": 20,
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
            "validators": {
                "vote": {"verifier": "vote_verifier", "weight": 1}
            },
            "nodes": {
                "storage": {"verifier": "storage_verifier", "weight": 1}
            },
        },
        "genesis": {"height": 0},
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
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    try:
        report = run_study(arguments.seed_start, arguments.seed_count)
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
