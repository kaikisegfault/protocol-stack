"""Persistent and churn identity trajectory projection."""

from __future__ import annotations

from simulation.participation.domain import domain_digest
from simulation.reward_distribution.crosscheck import fund_trajectory
from simulation.reward_distribution.model import run_trajectory

from .model import (
    capital_lower_bound,
    hidden_concentration,
    operating_break_even,
    partition_units,
    ratio_less,
    reduced_ratio,
    sum_u64,
)


def _identity(participant: str) -> dict[str, str]:
    return {
        "principal": f"{participant}_owner",
        "payout_account": f"{participant}_payout",
    }


def build_scenario(strategy: str, identity_count: int, design: dict) -> dict:
    if strategy not in {"persistent", "churn"} or not 1 <= identity_count <= 16:
        raise ValueError("unsupported trajectory strategy")
    trajectory = design["trajectory"]
    participants = {"honest": _identity("honest")}
    contributions = []
    units = partition_units(design["dominant_total_units"], identity_count)
    for epoch in range(trajectory["contribution_epochs"]):
        values = {"honest": trajectory["honest_units"]}
        for index, amount in enumerate(units):
            participant = (
                f"dominant_{index:02d}"
                if strategy == "persistent"
                else f"dominant_e{epoch:02d}_{index:02d}"
            )
            participants.setdefault(participant, _identity(participant))
            values[participant] = amount * trajectory["selected_weight"]
        if sum_u64(value for key, value in values.items() if key != "honest") != 16:
            raise AssertionError("trajectory changed dominant work")
        contributions.append(dict(sorted(values.items())))
    return {
        "scenario_id": f"{strategy}_{identity_count:02d}",
        "strategy": strategy,
        "identity_count": identity_count,
        "role": "node",
        "budget": trajectory["budget"],
        "participants": dict(sorted(participants.items())),
        "contributions": contributions,
    }


def _selected_paid(result: dict) -> int:
    return sum_u64(
        amount
        for epoch in result["epochs"]
        for participant, amount in epoch["payouts"].items()
        if participant != "honest"
    )


def _honest_paid(result: dict) -> int:
    return sum_u64(epoch["payouts"].get("honest", 0) for epoch in result["epochs"])


def _hidden_epochs(result: dict) -> tuple[int, int]:
    payout_epochs = 0
    passes = 0
    for epoch in result["epochs"]:
        outcome = hidden_concentration(epoch["payouts"])
        if outcome is not None:
            payout_epochs += 1
            passes += int(outcome)
    return payout_epochs, passes


def _update_lower(current: dict, candidate: dict) -> dict:
    if ratio_less(current["ratio"], candidate["ratio"]):
        return candidate
    if current["ratio"] == candidate["ratio"] and not candidate["inclusive"]:
        return {"ratio": current["ratio"], "inclusive": False}
    return current


def _rate_range(lower: dict, upper: dict) -> bool:
    return ratio_less(lower["ratio"], upper) or (
        lower["ratio"] == upper and lower["inclusive"]
    )


def _duration(strategy: str, identity_count: int, lock: int) -> int:
    if strategy == "persistent":
        return identity_count * (8 + lock)
    return 8 * identity_count * (1 + lock)


def _row(scenario: dict, result: dict, baseline_paid: int) -> dict:
    selected_paid = _selected_paid(result)
    honest_paid = _honest_paid(result)
    gain = selected_paid - baseline_paid
    identities = scenario["identity_count"] * (8 if scenario["strategy"] == "churn" else 1)
    extra_identities = identities - 1
    payout_epochs, hidden_passes = _hidden_epochs(result)
    bond_boundaries = []
    for lock in range(1, 17):
        incremental = _duration(scenario["strategy"], scenario["identity_count"], lock) - (
            8 + lock
        )
        bond_boundaries.append(
            {
                "post_exit_lock_epochs": lock,
                "incremental_unit_bond_exposure": incremental,
                "deterrence_lower": capital_lower_bound(gain, incremental),
            }
        )
    funding = fund_trajectory(scenario, result)
    return {
        "scenario_id": scenario["scenario_id"],
        "strategy": scenario["strategy"],
        "identity_count_per_epoch": scenario["identity_count"],
        "distinct_dominant_identities": identities,
        "mechanism": result["mechanism"],
        "dominant_payout": selected_paid,
        "honest_payout": honest_paid,
        "zero_cost_gain": gain,
        "incremental_operating_identities": extra_identities,
        "operating_break_even": operating_break_even(gain, extra_identities),
        "created_credit": result["created_credit"],
        "paid_credit": result["paid_credit"],
        "expired_credit": result["expired_credit"],
        "zero_payout_epochs": result["zero_payout_epochs"],
        "payout_epochs": payout_epochs,
        "hidden_principal_concentration_pass_epochs": hidden_passes,
        "hidden_principal_concentration": hidden_passes == payout_epochs,
        "epoch_payouts_digest": domain_digest(
            "protocol-stack:admission-cost:trajectory-payouts-v1", result["epochs"]
        ),
        "capital_rate_boundaries": bond_boundaries,
        "native_funding": funding,
        "objectives": {
            "work_invariant": True,
            "bounded_history": result["objectives"]["bounded_history"],
            "funded": funding["native_funding_failures"] == 0,
            "hidden_concentration": hidden_passes == payout_epochs,
        },
    }


def run_trajectories(design: dict) -> tuple[list[dict], list[dict], bool]:
    rows = []
    summaries = []
    capped: dict[tuple[str, int], list[dict]] = {}
    for mechanism in design["mechanisms"]:
        raw = {}
        for strategy in design["trajectory"]["strategies"]:
            for identity_count in range(1, 17):
                scenario = build_scenario(strategy, identity_count, design)
                raw[(strategy, identity_count)] = (
                    scenario,
                    run_trajectory(scenario, mechanism, design["trajectory"]["drain_epochs"]),
                )
        baseline_paid = _selected_paid(raw[("persistent", 1)][1])
        mechanism_rows = [
            _row(scenario, result, baseline_paid) for scenario, result in raw.values()
        ]
        rows.extend(mechanism_rows)
        if mechanism in {"participant_cap", "principal_cap"}:
            for key, (_scenario, result) in raw.items():
                capped.setdefault(key, []).append(result["epochs"])
        summaries.append(_summarize(mechanism, mechanism_rows))
    cap_equivalence = all(len(values) == 2 and values[0] == values[1] for values in capped.values())
    if not cap_equivalence:
        raise AssertionError("distinct-scope cap trajectories diverged")
    return rows, summaries, cap_equivalence


def _summarize(mechanism: str, rows: list[dict]) -> dict:
    floor = max(row["operating_break_even"] for row in rows)
    baseline = next(row for row in rows if row["scenario_id"] == "persistent_01")
    ceiling = baseline["honest_payout"]
    boundaries = []
    for lock in range(1, 17):
        lower = {"ratio": reduced_ratio(0, 1), "inclusive": True}
        for row in rows:
            candidate = row["capital_rate_boundaries"][lock - 1]["deterrence_lower"]
            lower = _update_lower(lower, candidate)
        upper = reduced_ratio(ceiling, 8 + lock)
        boundaries.append(
            {
                "post_exit_lock_epochs": lock,
                "unit_bond_deterrence_lower": lower,
                "unit_bond_honest_entry_upper": {"ratio": upper, "inclusive": True},
                "joint_rate_range": _rate_range(lower, upper),
            }
        )
    return {
        "mechanism": mechanism,
        "trajectory_count": len(rows),
        "profitable_zero_cost_strategies": sum(row["zero_cost_gain"] > 0 for row in rows),
        "maximum_zero_cost_gain": max(row["zero_cost_gain"] for row in rows),
        "operating_deterrence_floor": floor,
        "smallest_honest_entry_ceiling": ceiling,
        "operating_cost_interval": {
            "minimum": floor,
            "maximum": ceiling,
            "feasible": floor <= ceiling,
        },
        "capital_rate_boundaries": boundaries,
        "native_funding_failures": sum(
            row["native_funding"]["native_funding_failures"] for row in rows
        ),
        "hidden_concentration_strategies": sum(
            row["hidden_principal_concentration"] for row in rows
        ),
        "objectives": {
            "work_invariant": all(row["objectives"]["work_invariant"] for row in rows),
            "funded": all(row["objectives"]["funded"] for row in rows),
            "churn_deterred_at_floor": True,
            "hidden_concentration": all(
                row["objectives"]["hidden_concentration"] for row in rows
            ),
            "honest_entry_at_floor": floor <= ceiling,
            "joint_cost_range": floor <= ceiling,
        },
    }
