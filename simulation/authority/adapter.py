"""All-or-nothing adapters into the accepted M2 simulators."""

from __future__ import annotations

import copy
from typing import Any

from simulation.native_economy.domain import Manifest as EconomyManifest
from simulation.native_economy.validation import (
    parse_events as parse_economy_events,
)
from simulation.native_economy.validation import (
    parse_manifest as parse_economy_manifest,
)
from simulation.participation.domain import Manifest as ParticipationManifest
from simulation.participation.validation import (
    parse_events as parse_participation_events,
)
from simulation.participation.validation import (
    parse_manifest as parse_participation_manifest,
)

from .domain import Manifest, action_digest, domain_digest
from .validation import parse_manifest


class AdapterError(ValueError):
    """An authority result cannot release the requested target event."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def build_authorized_events(
    result: dict[str, Any],
    authority_manifest: Manifest | dict[str, Any],
    target_manifest: EconomyManifest | ParticipationManifest | dict[str, Any],
    *,
    module: str,
    pairs: list[tuple[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    authority = (
        authority_manifest
        if isinstance(authority_manifest, Manifest)
        else parse_manifest(authority_manifest)
    )
    target = _parse_target_manifest(module, target_manifest)
    _validate_authority_result(result, authority)
    results = _result_map(result)
    seen_results: set[str] = set()
    seen_events: set[str] = set()
    output: list[dict[str, Any]] = []
    for pair in pairs:
        if type(pair) is not tuple or len(pair) != 2 or type(pair[0]) is not str:
            raise AdapterError("TARGET_INVALID")
        result_id, target_value = pair
        if result_id in seen_results:
            raise AdapterError("RESULT_NOT_FOUND")
        target_event = _parse_target_event(module, target_value)
        if target_event["id"] in seen_events:
            raise AdapterError("TARGET_INVALID")
        authority_result = results.get(result_id)
        if authority_result is None:
            raise AdapterError("RESULT_NOT_FOUND")
        _validate_pair(
            result,
            authority,
            target,
            module,
            authority_result,
            target_event,
        )
        seen_results.add(result_id)
        seen_events.add(target_event["id"])
        output.append(copy.deepcopy(target_event))
    return output


def _parse_target_manifest(module: str, value: Any) -> Any:
    try:
        if module == "native_economy":
            return (
                value
                if isinstance(value, EconomyManifest)
                else parse_economy_manifest(value)
            )
        if module == "participation":
            return (
                value
                if isinstance(value, ParticipationManifest)
                else parse_participation_manifest(value)
            )
    except ValueError as error:
        raise AdapterError("MANIFEST_MISMATCH") from error
    raise AdapterError("MODULE_MISMATCH")


def _parse_target_event(module: str, value: Any) -> dict[str, Any]:
    try:
        if module == "native_economy":
            return parse_economy_events([value])[0]
        if module == "participation":
            return parse_participation_events([value])[0]
    except (ValueError, IndexError, TypeError) as error:
        raise AdapterError("TARGET_INVALID") from error
    raise AdapterError("MODULE_MISMATCH")


def _validate_authority_result(result: dict[str, Any], manifest: Manifest) -> None:
    if type(result) is not dict:
        raise AdapterError("MANIFEST_MISMATCH")
    if result.get("schema") != "protocol-stack/authority-simulation-result/v1":
        raise AdapterError("MANIFEST_MISMATCH")
    expected_manifest = domain_digest(
        "protocol-stack:authority:manifest-v1",
        manifest.source,
    )
    if result.get("manifest_digest") != expected_manifest:
        raise AdapterError("MANIFEST_MISMATCH")
    records = result.get("records")
    final_state = result.get("final_state")
    if type(records) is not list or type(final_state) is not dict:
        raise AdapterError("MANIFEST_MISMATCH")
    if result.get("trace_digest") != domain_digest(
        "protocol-stack:authority:trace-v1", records
    ):
        raise AdapterError("MANIFEST_MISMATCH")
    if records:
        final_digest = domain_digest(
            "protocol-stack:authority:state-v1",
            final_state,
        )
        if records[-1].get("state_digest_after") != final_digest:
            raise AdapterError("MANIFEST_MISMATCH")


def _result_map(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values = result["final_state"].get("authorization_results")
    if type(values) is not list:
        raise AdapterError("MANIFEST_MISMATCH")
    mapped: dict[str, dict[str, Any]] = {}
    for value in values:
        if type(value) is not dict or type(value.get("result_id")) is not str:
            raise AdapterError("MANIFEST_MISMATCH")
        if value["result_id"] in mapped:
            raise AdapterError("MANIFEST_MISMATCH")
        mapped[value["result_id"]] = value
    return mapped


def _validate_pair(
    complete_result: dict[str, Any],
    authority: Manifest,
    target: Any,
    module: str,
    result: dict[str, Any],
    event: dict[str, Any],
) -> None:
    if result.get("module") != module:
        raise AdapterError("MODULE_MISMATCH")
    capability, actor = _target_policy(module, target, event)
    if result.get("capability") != capability:
        raise AdapterError("CAPABILITY_MISMATCH")
    if event.get("actor") != actor:
        raise AdapterError("ACTOR_MISMATCH")
    binding = authority.capabilities.get((module, capability))
    if binding is None:
        raise AdapterError("MANIFEST_MISMATCH")
    if result.get("set_id") != binding.set_id:
        raise AdapterError("SET_MISMATCH")
    capability_state = _capability_state(
        complete_result["final_state"], module, capability
    )
    if capability_state is None or capability_state.get("set_id") != binding.set_id:
        raise AdapterError("SET_MISMATCH")
    versions = capability_state.get("versions")
    if type(versions) is not list:
        raise AdapterError("SET_MISMATCH")
    version_ids: set[int] = set()
    for item in versions:
        if type(item) is not dict or type(item.get("version")) is not int:
            raise AdapterError("MANIFEST_MISMATCH")
        version_ids.add(item["version"])
    if result.get("set_version") not in version_ids:
        raise AdapterError("SET_MISMATCH")
    required = {
        "schema",
        "chain_id",
        "module",
        "capability",
        "set_id",
        "set_version",
        "result_id",
        "action_id",
        "valid_from_epoch",
        "deadline_epoch",
        "action_digest",
        "authorized_height",
        "authorized_epoch",
        "approvals",
    }
    if (
        set(result) != required
        or result["schema"] != "protocol-stack/authority-result/v1"
        or result["chain_id"] != authority.chain_id
    ):
        raise AdapterError("MANIFEST_MISMATCH")
    expected = action_digest(
        chain_id=result["chain_id"],
        module=result["module"],
        capability=result["capability"],
        set_id=result["set_id"],
        set_version=result["set_version"],
        result_id=result["result_id"],
        action_id=result["action_id"],
        valid_from_epoch=result["valid_from_epoch"],
        deadline_epoch=result["deadline_epoch"],
        action=event,
    )
    if result["action_digest"] != expected:
        raise AdapterError("ACTION_DIGEST_MISMATCH")


def _target_policy(module: str, manifest: Any, event: dict[str, Any]) -> tuple[str, str]:
    kind = event["kind"]
    if module == "native_economy":
        return _economy_policy(manifest, event, kind)
    if module == "participation":
        return _participation_policy(manifest, event, kind)
    raise AdapterError("MODULE_MISMATCH")


def _economy_policy(
    manifest: EconomyManifest,
    event: dict[str, Any],
    kind: str,
) -> tuple[str, str]:
    mapping = {
        "advance_height": ("clock", manifest.authorities.clock),
        "issue": ("issuance", manifest.authorities.issuance),
        "allocate_fees": ("fee_allocation", manifest.authorities.fee_allocation),
        "treasury_grant": ("treasury", manifest.authorities.treasury),
        "fund_rewards": ("treasury", manifest.authorities.treasury),
        "release_escrow": ("escrow", manifest.authorities.escrow),
        "allocate_reward": ("reward", manifest.authorities.reward),
        "penalize": ("penalty", manifest.authorities.penalty),
        "route_penalty": ("penalty", manifest.authorities.penalty),
    }
    if kind == "open_escrow" and event["source_kind"] == "treasury":
        return "treasury", manifest.authorities.treasury
    if kind not in mapping:
        raise AdapterError("TARGET_INVALID")
    return mapping[kind]


def _participation_policy(
    manifest: ParticipationManifest,
    event: dict[str, Any],
    kind: str,
) -> tuple[str, str]:
    mapping = {
        "advance_height": ("clock", manifest.authorities.clock),
        "register_validator": ("registration", manifest.authorities.registration),
        "register_node": ("registration", manifest.authorities.registration),
        "confirm_bond": ("stake", manifest.authorities.stake),
        "activate": ("lifecycle", manifest.authorities.lifecycle),
        "recover": ("lifecycle", manifest.authorities.lifecycle),
        "jail": ("enforcement", manifest.authorities.enforcement),
        "remove": ("enforcement", manifest.authorities.enforcement),
        "set_reward_budget": ("reward", manifest.authorities.reward),
        "settle_entitlement": ("reward", manifest.authorities.reward),
        "finalize_budget": ("reward", manifest.authorities.reward),
    }
    if kind == "attest_contribution":
        role = event["role"]
        policy = manifest.contributions.get(role, {}).get(
            event["contribution_kind"]
        )
        if policy is None:
            raise AdapterError("TARGET_INVALID")
        capability = f"contribution/{role}/{event['contribution_kind']}"
        return capability, policy.verifier
    if kind not in mapping:
        raise AdapterError("TARGET_INVALID")
    return mapping[kind]


def _capability_state(
    final_state: dict[str, Any],
    module: str,
    capability: str,
) -> dict[str, Any] | None:
    values = final_state.get("capabilities")
    if type(values) is not list:
        raise AdapterError("MANIFEST_MISMATCH")
    return next(
        (
            item
            for item in values
            if type(item) is dict
            and item.get("module") == module
            and item.get("capability") == capability
        ),
        None,
    )
