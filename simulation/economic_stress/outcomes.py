"""Exact objectives, reverse stress, and report projection for one run."""

from __future__ import annotations

from typing import Any

from .authority_flow import AuthorityBuilder, AuthorizedTarget
from .design import Configuration
from .economy_flow import Flow as EconomyFlow
from .outcome_context import build_context
from .participation_flow import Flow as ParticipationFlow


def report_run(
    config: Configuration,
    seed: int,
    builder: AuthorityBuilder,
    controls: dict[str, str],
    malicious: AuthorizedTarget,
    participation_flow: ParticipationFlow,
    participation_result: dict[str, Any],
    economy_flow: EconomyFlow,
    economy_actual: list[dict[str, Any]],
    economy_result: dict[str, Any],
    funding_events: list[dict[str, Any]],
    authority_result: dict[str, Any],
) -> dict[str, Any]:
    context = build_context(
        builder,
        controls,
        malicious,
        participation_flow,
        participation_result,
        economy_flow,
        economy_result,
        funding_events,
        authority_result,
    )
    objectives = _objectives(context)
    return {
        "case_index": config.case_index,
        "case_id": config.case_id,
        "seed": seed,
        "configuration": config.report_value(),
        "trace_digests": {
            "authority": authority_result["trace_digest"],
            "participation": participation_result["trace_digest"],
            "native_economy": economy_result["trace_digest"],
        },
        "counts": _counts(
            context,
            participation_flow,
            participation_result,
            economy_flow,
            economy_actual,
            economy_result,
        ),
        "authority_control": {
            key: value["result"]
            for key, value in sorted(context["control_records"].items())
        },
        "captured_issue": _captured_issue(context, malicious),
        "entitlements": _entitlement_metrics(context, participation_result),
        "economy_inventory": context["inventory"],
        "objectives": objectives,
        "reverse_stress": _reverse_codes(objectives),
        "classification": _classification(objectives),
    }


def _counts(
    context: dict[str, Any],
    participation_flow: ParticipationFlow,
    participation_result: dict[str, Any],
    economy_flow: EconomyFlow,
    economy_actual: list[dict[str, Any]],
    economy_result: dict[str, Any],
) -> dict[str, int]:
    return {
        "expected_authority_results": len(context["legitimate"]),
        "accepted_authority_results": sum(
            target.result_id in context["accepted_results"]
            for target in context["legitimate"]
        ),
        "expected_participation_events": len(participation_flow.events),
        "executed_participation_events": len(participation_result["records"]),
        "accepted_participation_events": sum(
            record["accepted"] for record in participation_result["records"]
        ),
        "expected_economy_events": len(economy_flow.events),
        "executed_economy_events": len(economy_actual),
        "accepted_economy_events": sum(
            record["accepted"] for record in economy_result["records"]
        ),
    }


def _objectives(context: dict[str, Any]) -> dict[str, bool]:
    controls = context["control_records"]
    return {
        "supply_conserved": _conserved(context["inventory"]),
        "authority_available": all(
            target.result_id in context["accepted_results"]
            for target in context["legitimate"]
        ),
        "rotation_available": all(
            controls[key]["accepted"] for key in ("schedule", "activate")
        ),
        "recovery_available": all(
            controls[key]["accepted"] for key in ("pause", "recover")
        ),
        "participation_complete": context["participation_complete"],
        "funding_complete": (
            context["participation_complete"]
            and context["funded_amount"] == context["entitlement_total"]
        ),
        "economy_complete": context["economy_complete"],
        "authority_uncaptured": (
            context["malicious_result_id"] not in context["accepted_results"]
        ),
        "concentration_within_bound": context["concentration"],
    }


def _captured_issue(
    context: dict[str, Any],
    malicious: AuthorizedTarget,
) -> dict[str, bool]:
    record = context["economy_records"].get(malicious.event["id"])
    return {
        "authorized": malicious.result_id in context["accepted_results"],
        "executed": record is not None,
        "accepted": False if record is None else record["accepted"],
    }


def _entitlement_metrics(
    context: dict[str, Any],
    participation_result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "count": len(context["entitlements"]),
        "requested_amount": context["entitlement_total"],
        "funded_amount": context["funded_amount"],
        "maximum_amount": context["maximum_entitlement"],
        "maximum_share": context["maximum_share"],
        "role_maximum_shares": context["role_shares"],
        "retained_remainder": sum(
            budget["remainder"] or 0
            for budget in participation_result["final_state"]["budgets"]
        ),
    }


def _conserved(inventory: dict[str, int]) -> bool:
    keys = (
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
    custody = sum(inventory[key] for key in keys)
    return (
        custody == inventory["issued_supply"]
        and inventory["issued_supply"] <= inventory["supply_limit"]
    )


def _reverse_codes(objectives: dict[str, bool]) -> list[str]:
    mapping = {
        "supply_conserved": "SUPPLY_INVARIANT",
        "authority_available": "AUTHORITY_UNAVAILABLE",
        "rotation_available": "ROTATION_UNAVAILABLE",
        "recovery_available": "RECOVERY_UNAVAILABLE",
        "participation_complete": "PARTICIPATION_INCOMPLETE",
        "funding_complete": "FUNDING_SHORTFALL",
        "economy_complete": "ECONOMY_INCOMPLETE",
        "authority_uncaptured": "AUTHORITY_CAPTURE",
        "concentration_within_bound": "REWARD_CONCENTRATION",
    }
    return sorted(code for key, code in mapping.items() if not objectives[key])


def _classification(objectives: dict[str, bool]) -> str:
    infeasible = (
        not objectives["supply_conserved"]
        or not objectives["authority_uncaptured"]
        or (
            objectives["participation_complete"]
            and not objectives["funding_complete"]
        )
    )
    if infeasible:
        return "infeasible"
    return "robust" if all(objectives.values()) else "fragile"
