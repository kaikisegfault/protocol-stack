"""Extract exact accepted-state metrics for one composed stress run."""

from __future__ import annotations

from typing import Any

from simulation.native_economy.metrics import rational

from .authority_flow import AuthorityBuilder, AuthorizedTarget
from .economy_flow import Flow as EconomyFlow
from .participation_flow import Flow as ParticipationFlow


def build_context(
    builder: AuthorityBuilder,
    controls: dict[str, str],
    malicious: AuthorizedTarget,
    participation_flow: ParticipationFlow,
    participation_result: dict[str, Any],
    economy_flow: EconomyFlow,
    economy_result: dict[str, Any],
    funding_events: list[dict[str, Any]],
    authority_result: dict[str, Any],
) -> dict[str, Any]:
    accepted_results = {
        item["result_id"]
        for item in authority_result["final_state"]["authorization_results"]
    }
    authority_records = {
        record["event_id"]: record for record in authority_result["records"]
    }
    entitlements = participation_result["final_state"]["entitlements"]
    economy_records = {
        record["event_id"]: record for record in economy_result["records"]
    }
    entitlement_values = _entitlement_values(entitlements)
    return {
        "accepted_results": accepted_results,
        "control_records": {
            name: authority_records[event_id]
            for name, event_id in controls.items()
        },
        "legitimate": [target for target in builder.targets if target.legitimate],
        "participation_complete": _complete(
            participation_flow.events,
            participation_result,
        ),
        "economy_complete": _complete(economy_flow.events, economy_result),
        "entitlements": entitlements,
        **entitlement_values,
        "economy_records": economy_records,
        "funded_amount": sum(
            event["amount"]
            for event in funding_events
            if economy_records.get(event["id"], {}).get("accepted") is True
        ),
        "inventory": economy_result["metrics"]["inventory"],
        "malicious_result_id": malicious.result_id,
    }


def _entitlement_values(entitlements: list[dict[str, Any]]) -> dict[str, Any]:
    amounts = [item["amount"] for item in entitlements]
    role_amounts = {
        role: [
            item["amount"]
            for item in entitlements
            if item["role"] == role
        ]
        for role in ("validator", "node")
    }
    role_shares = {
        role: (
            rational(max(values, default=0), sum(values))
            if sum(values)
            else rational(0, 1)
        )
        for role, values in role_amounts.items()
    }
    return {
        "entitlement_total": sum(amounts),
        "maximum_entitlement": max(amounts, default=0),
        "maximum_share": _maximum_share(role_shares),
        "role_shares": role_shares,
        "concentration": all(
            values
            and sum(values) > 0
            and 4 * max(values) <= 3 * sum(values)
            for values in role_amounts.values()
        ),
    }


def _maximum_share(role_shares: dict[str, dict[str, int]]) -> dict[str, int]:
    validator = role_shares["validator"]
    node = role_shares["node"]
    if (
        validator["numerator"] * node["denominator"]
        >= node["numerator"] * validator["denominator"]
    ):
        return validator
    return node


def _complete(expected: list[dict[str, Any]], result: dict[str, Any]) -> bool:
    records = {record["event_id"]: record for record in result["records"]}
    return all(
        records.get(event["id"], {}).get("accepted") is True
        for event in expected
    )
