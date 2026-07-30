"""Exact integer participation metrics."""

from __future__ import annotations

from typing import Any

from .domain import Manifest, State


def build_metrics(
    state: State,
    manifest: Manifest,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    phases = {
        role: {
            phase: sum(
                participant.role == role and participant.phase == phase
                for participant in state.participants.values()
            )
            for phase in ("pending", "active", "exit_pending", "exited", "removed")
        }
        for role in ("validator", "node")
    }
    for role in phases:
        phases[role]["jailed"] = sum(
            participant.role == role and participant.jailed_until_epoch is not None
            for participant in state.participants.values()
        )

    accepted_counts: dict[str, int] = {}
    proof_counts: dict[str, int] = {}
    for record in records:
        if not record["accepted"]:
            continue
        kind = record["kind"]
        accepted_counts[kind] = accepted_counts.get(kind, 0) + 1
        if record["accepted_proof_id"] is not None:
            proof_counts[kind] = proof_counts.get(kind, 0) + 1

    contribution_metrics: dict[str, dict[str, dict[str, int]]] = {
        "validator": {},
        "node": {},
    }
    for (_, role, _, kind), contribution in state.contributions.items():
        values = contribution_metrics[role].setdefault(
            kind,
            {"raw_units": 0, "weighted_units": 0},
        )
        values["raw_units"] += contribution.units
        values["weighted_units"] += contribution.weighted_units

    budget_metrics = {
        role: {
            "budget_count": 0,
            "budget_amount": 0,
            "allocated": 0,
            "retained_remainder": 0,
            "zero_entitlements": 0,
        }
        for role in ("validator", "node")
    }
    for (_, role), budget in state.budgets.items():
        values = budget_metrics[role]
        values["budget_count"] += 1
        values["budget_amount"] += budget.amount
        values["allocated"] += budget.allocated
        values["retained_remainder"] += (
            0 if budget.remainder is None else budget.remainder
        )
    for (_, role, _), entitlement in state.entitlements.items():
        budget_metrics[role]["zero_entitlements"] += entitlement.amount == 0

    activation_wait = 0
    exit_wait = 0
    removal_hold = 0
    for participant in state.participants.values():
        if participant.activated_epoch is not None:
            activation_wait += participant.activated_epoch - participant.registered_epoch
        if participant.exit_epoch is not None:
            exit_wait += manifest.parameters.exit_delay_epochs
        if participant.removed_epoch is not None and participant.unbond_ready_epoch is not None:
            removal_hold += participant.unbond_ready_epoch - participant.removed_epoch

    return {
        "participants": phases,
        "accepted_events": dict(sorted(accepted_counts.items())),
        "accepted_proofs": dict(sorted(proof_counts.items())),
        "contributions": {
            role: dict(sorted(values.items()))
            for role, values in contribution_metrics.items()
        },
        "budgets": budget_metrics,
        "wait_epochs": {
            "activation_total": activation_wait,
            "exit_total": exit_wait,
            "removal_hold_total": removal_hold,
        },
    }
