"""Compose one authority, participation, and native-economy stress run."""

from __future__ import annotations

from typing import Any

from simulation.authority.domain import canonical_json
from simulation.authority.engine import simulate as simulate_authority
from simulation.native_economy.engine import simulate as simulate_economy
from simulation.participation.adapter import build_funding_events
from simulation.participation.engine import simulate as simulate_participation

from .authority_control import add_control_lifecycle
from .authority_flow import AuthorityBuilder, AuthorizedTarget, release_targets
from .design import Configuration
from .economy_flow import Flow as EconomyFlow
from .economy_flow import build_economy_flow
from .manifests import authority_manifest, economy_manifest, participation_manifest
from .participation_flow import Flow as ParticipationFlow
from .participation_flow import build_participation_flow
from .outcomes import report_run


def run_configuration(config: Configuration, seed: int) -> dict[str, Any]:
    participation_value = participation_manifest(config)
    economy_value = economy_manifest(config)
    authority_value = authority_manifest(config)
    participation_flow = build_participation_flow(config, seed)
    builder = AuthorityBuilder(config, seed, authority_value)
    _authorize_participation(builder, participation_flow)

    prefix_result = simulate_authority(authority_value, list(builder.events))
    prefix_participation = _simulate_released_participation(
        builder,
        prefix_result,
        authority_value,
        participation_value,
        participation_flow,
    )
    funding_events = _funding_events(
        prefix_participation,
        participation_value,
        economy_value,
    )
    economy_flow = build_economy_flow(config, funding_events)
    _authorize_economy(builder, economy_flow)
    malicious = builder.add_operational(
        "native_economy",
        "issuance",
        economy_flow.malicious_event,
        legitimate=False,
    )
    controls = add_control_lifecycle(builder)

    authority_result = simulate_authority(authority_value, builder.events)
    participation_result = _simulate_released_participation(
        builder,
        authority_result,
        authority_value,
        participation_value,
        participation_flow,
    )
    if canonical_json(prefix_participation) != canonical_json(participation_result):
        raise AssertionError("two-pass participation replay changed")
    economy_result, economy_actual = _simulate_released_economy(
        builder,
        authority_result,
        authority_value,
        economy_value,
        economy_flow,
        malicious,
    )
    return report_run(
        config,
        seed,
        builder,
        controls,
        malicious,
        participation_flow,
        participation_result,
        economy_flow,
        economy_actual,
        economy_result,
        funding_events,
        authority_result,
    )


def _authorize_participation(
    builder: AuthorityBuilder,
    flow: ParticipationFlow,
) -> None:
    for event in flow.events:
        capability = flow.privileged.get(event["id"])
        if capability is not None:
            builder.add_operational("participation", capability, event)


def _authorize_economy(builder: AuthorityBuilder, flow: EconomyFlow) -> None:
    for event in flow.events:
        capability = flow.privileged.get(event["id"])
        if capability is not None:
            builder.add_operational("native_economy", capability, event)


def _simulate_released_participation(
    builder: AuthorityBuilder,
    authority_result: dict[str, Any],
    authority_value: dict[str, Any],
    participation_value: dict[str, Any],
    flow: ParticipationFlow,
) -> dict[str, Any]:
    released = release_targets(
        authority_result,
        authority_value,
        participation_value,
        "participation",
        builder.targets,
    )
    released_ids = {event["id"] for event in released}
    actual = [
        event
        for event in flow.events
        if event["id"] not in flow.privileged or event["id"] in released_ids
    ]
    return simulate_participation(participation_value, actual)


def _funding_events(
    participation_result: dict[str, Any],
    participation_value: dict[str, Any],
    economy_value: dict[str, Any],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    budgets = sorted(
        participation_result["final_state"]["budgets"],
        key=lambda item: (item["epoch"], item["role"]),
    )
    for budget in budgets:
        if budget["finalized"]:
            events.extend(
                build_funding_events(
                    participation_result,
                    participation_value,
                    economy_value,
                    epoch=budget["epoch"],
                    role=budget["role"],
                    height=0,
                )
            )
    return events


def _simulate_released_economy(
    builder: AuthorityBuilder,
    authority_result: dict[str, Any],
    authority_value: dict[str, Any],
    economy_value: dict[str, Any],
    flow: EconomyFlow,
    malicious: AuthorizedTarget,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    released = release_targets(
        authority_result,
        authority_value,
        economy_value,
        "native_economy",
        builder.targets,
    )
    released_by_id = {event["id"]: event for event in released}
    actual: list[dict[str, Any]] = []
    for event in flow.events:
        privileged = event["id"] in flow.privileged
        if not privileged or event["id"] in released_by_id:
            actual.append(event)
        if event["kind"] == "issue" and malicious.event["id"] in released_by_id:
            actual.append(malicious.event)
    return simulate_economy(economy_value, actual), actual
