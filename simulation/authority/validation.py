"""Strict authority-simulation-v1 JSON validation."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from .domain import MAX_U64, AuthoritySet, Manifest, Parameters

MANIFEST_SCHEMA = "protocol-stack/authority-simulation-manifest/v1"
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
CAPABILITY = re.compile(
    r"^[a-z][a-z0-9_-]{0,63}(?:/[a-z][a-z0-9_-]{0,63}){0,2}$"
)
DIGEST = re.compile(r"^[0-9a-f]{64}$")


class InputError(ValueError):
    """Input does not satisfy the authority-simulation-v1 schema."""


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_float(value: str) -> float:
    raise InputError(f"floating-point JSON value is forbidden: {value}")


def _invalid_constant(value: str) -> float:
    raise InputError(f"non-finite JSON value is forbidden: {value}")


def load_json(path: str | Path) -> Any:
    try:
        return json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_pairs_without_duplicates,
            parse_float=_invalid_float,
            parse_constant=_invalid_constant,
        )
    except json.JSONDecodeError as error:
        raise InputError(f"invalid JSON: {error}") from error


def parse_manifest(value: Any) -> Manifest:
    _reject_floats(value)
    source = _object(value, "manifest")
    _exact_fields(
        source,
        {
            "schema",
            "research_only",
            "chain_id",
            "parameters",
            "clock",
            "control_sets",
            "capabilities",
            "genesis",
        },
        "manifest",
    )
    if source["schema"] != MANIFEST_SCHEMA:
        raise InputError("unsupported manifest schema")
    if source["research_only"] is not True:
        raise InputError("research_only must be true")
    chain_id = _identifier(source["chain_id"], "chain_id")
    clock = _identifier(source["clock"], "clock")
    parameters = _parse_parameters(source["parameters"])
    containment, recovery = _parse_control_sets(
        source["control_sets"], parameters
    )
    capabilities = _parse_capabilities(source["capabilities"], parameters)
    set_ids = [containment.set_id, recovery.set_id]
    set_ids.extend(item.set_id for item in capabilities.values())
    if len(set_ids) != len(set(set_ids)):
        raise InputError("set identifiers must be globally unique")
    genesis = _object(source["genesis"], "genesis")
    _exact_fields(genesis, {"height"}, "genesis")
    return Manifest(
        chain_id=chain_id,
        parameters=parameters,
        clock=clock,
        containment=containment,
        recovery=recovery,
        capabilities=capabilities,
        genesis_height=_u64(genesis["height"], "genesis.height"),
        source=copy.deepcopy(source),
    )


def _parse_parameters(value: Any) -> Parameters:
    source = _object(value, "parameters")
    fields = {
        "epoch_length",
        "min_rotation_delay_epochs",
        "max_rotation_delay_epochs",
        "recovery_delay_epochs",
        "max_action_lifetime_epochs",
        "max_capabilities",
        "max_members_per_set",
        "max_approvals_per_result",
        "max_versions_per_capability",
    }
    _exact_fields(source, fields, "parameters")
    result = Parameters(
        **{
            key: _u64(source[key], f"parameters.{key}", nonzero=True)
            for key in fields
        }
    )
    if result.min_rotation_delay_epochs > result.max_rotation_delay_epochs:
        raise InputError("minimum rotation delay exceeds maximum")
    if result.max_members_per_set > result.max_approvals_per_result:
        raise InputError("member bound exceeds approval bound")
    return result


def _parse_control_sets(
    value: Any,
    parameters: Parameters,
) -> tuple[AuthoritySet, AuthoritySet]:
    source = _object(value, "control_sets")
    _exact_fields(source, {"containment", "recovery"}, "control_sets")
    return (
        _parse_set(source["containment"], "control_sets.containment", parameters),
        _parse_set(source["recovery"], "control_sets.recovery", parameters),
    )


def _parse_capabilities(
    value: Any,
    parameters: Parameters,
) -> dict[tuple[str, str], AuthoritySet]:
    source = _object(value, "capabilities")
    if "authority" in source:
        raise InputError("authority module cannot be a normal capability")
    result: dict[tuple[str, str], AuthoritySet] = {}
    for module, capabilities_value in source.items():
        parsed_module = _identifier(module, "capabilities module")
        capabilities = _object(capabilities_value, f"capabilities.{module}")
        if not capabilities:
            raise InputError(f"capabilities.{module} must not be empty")
        for capability, set_value in capabilities.items():
            parsed_capability = _capability(
                capability, f"capabilities.{module} capability"
            )
            result[(parsed_module, parsed_capability)] = _parse_set(
                set_value,
                f"capabilities.{module}.{capability}",
                parameters,
            )
    if not 1 <= len(result) <= parameters.max_capabilities:
        raise InputError("capability count exceeds manifest bounds")
    return result


def _parse_set(
    value: Any,
    name: str,
    parameters: Parameters,
) -> AuthoritySet:
    source = _object(value, name)
    _exact_fields(source, {"set_id", "version", "members", "threshold"}, name)
    version = _u64(source["version"], f"{name}.version", nonzero=True)
    if version != 1:
        raise InputError(f"{name}.version must equal one")
    members = _members(source["members"], f"{name}.members")
    if len(members) > parameters.max_members_per_set:
        raise InputError(f"{name}.members exceeds manifest limit")
    threshold = _u64(source["threshold"], f"{name}.threshold", nonzero=True)
    if threshold > len(members):
        raise InputError(f"{name}.threshold exceeds member count")
    return AuthoritySet(
        set_id=_identifier(source["set_id"], f"{name}.set_id"),
        version=version,
        members=tuple(members),
        threshold=threshold,
    )


_BASE_FIELDS = {"id", "height", "kind"}
_THRESHOLD_FIELDS = {
    "chain_id",
    "set_id",
    "set_version",
    "result_id",
    "action_id",
    "valid_from_epoch",
    "deadline_epoch",
    "action_digest",
    "approvals",
}
_EVENT_FIELDS = {
    "advance_height": {"actor", "to_height"},
    "authorize_action": _THRESHOLD_FIELDS | {"module", "capability"},
    "schedule_rotation": _THRESHOLD_FIELDS
    | {
        "target_module",
        "target_capability",
        "next_version",
        "next_members",
        "next_threshold",
        "activation_epoch",
    },
    "activate_rotation": {"actor", "target_module", "target_capability"},
    "pause_capability": _THRESHOLD_FIELDS
    | {"target_module", "target_capability", "reason_digest"},
    "revoke_member": _THRESHOLD_FIELDS
    | {"target_module", "target_capability", "reason_digest", "member"},
    "recover_capability": _THRESHOLD_FIELDS
    | {
        "target_module",
        "target_capability",
        "next_version",
        "next_members",
        "next_threshold",
    },
}
_IDENTIFIER_FIELDS = {
    "id",
    "actor",
    "chain_id",
    "module",
    "target_module",
    "set_id",
    "result_id",
    "action_id",
    "member",
}
_CAPABILITY_FIELDS = {"capability", "target_capability"}
_U64_FIELDS = {
    "height",
    "to_height",
    "set_version",
    "valid_from_epoch",
    "deadline_epoch",
    "next_version",
    "next_threshold",
    "activation_epoch",
}
_DIGEST_FIELDS = {"action_digest", "reason_digest"}


def parse_events(value: Any) -> list[dict[str, Any]]:
    _reject_floats(value)
    if type(value) is not list:
        raise InputError("events must be an array")
    return [_parse_event(item, index) for index, item in enumerate(value)]


def _parse_event(value: Any, index: int) -> dict[str, Any]:
    source = _object(value, f"events[{index}]")
    kind = source.get("kind")
    if type(kind) is not str or kind not in _EVENT_FIELDS:
        raise InputError(f"events[{index}].kind is unsupported")
    _exact_fields(source, _BASE_FIELDS | _EVENT_FIELDS[kind], f"events[{index}]")
    result: dict[str, Any] = {}
    for key, item in source.items():
        name = f"events[{index}].{key}"
        if key in _IDENTIFIER_FIELDS:
            result[key] = _identifier(item, name)
        elif key in _CAPABILITY_FIELDS:
            result[key] = _capability(item, name)
        elif key in _U64_FIELDS:
            result[key] = _u64(item, name)
        elif key in _DIGEST_FIELDS:
            result[key] = _digest(item, name)
        elif key == "next_members":
            result[key] = _members(item, name)
        elif key == "approvals":
            result[key] = _approvals(item, name)
        elif key == "kind":
            result[key] = item
        else:
            raise InputError(f"events[{index}] has unparsed field {key}")
    return result


def _approvals(value: Any, name: str) -> list[dict[str, str]]:
    if type(value) is not list:
        raise InputError(f"{name} must be an array")
    result: list[dict[str, str]] = []
    for index, value_item in enumerate(value):
        item = _object(value_item, f"{name}[{index}]")
        _exact_fields(
            item,
            {"member", "proof_id", "evidence_digest"},
            f"{name}[{index}]",
        )
        result.append(
            {
                "member": _identifier(item["member"], f"{name}[{index}].member"),
                "proof_id": _identifier(
                    item["proof_id"], f"{name}[{index}].proof_id"
                ),
                "evidence_digest": _digest(
                    item["evidence_digest"],
                    f"{name}[{index}].evidence_digest",
                ),
            }
        )
    return result


def _members(value: Any, name: str) -> list[str]:
    if type(value) is not list or not value:
        raise InputError(f"{name} must be a nonempty array")
    members = [
        _identifier(item, f"{name}[{index}]")
        for index, item in enumerate(value)
    ]
    if members != sorted(set(members)):
        raise InputError(f"{name} must be strictly ascending")
    return members


def _object(value: Any, name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise InputError(f"{name} must be an object")
    return value


def _exact_fields(value: dict[str, Any], expected: set[str], name: str) -> None:
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing or unknown:
        raise InputError(f"{name} fields: missing={missing}, unknown={unknown}")


def _identifier(value: Any, name: str) -> str:
    if type(value) is not str or IDENTIFIER.fullmatch(value) is None:
        raise InputError(f"{name} is not a version-one identifier")
    return value


def _capability(value: Any, name: str) -> str:
    if type(value) is not str or CAPABILITY.fullmatch(value) is None:
        raise InputError(f"{name} is not a version-one capability")
    return value


def _digest(value: Any, name: str) -> str:
    if type(value) is not str or DIGEST.fullmatch(value) is None:
        raise InputError(f"{name} is not a 32-byte lowercase hex digest")
    return value


def _u64(value: Any, name: str, *, nonzero: bool = False) -> int:
    if type(value) is not int or not 0 <= value <= MAX_U64:
        raise InputError(f"{name} is not a u64")
    if nonzero and value == 0:
        raise InputError(f"{name} must be nonzero")
    return value


def _reject_floats(value: Any, name: str = "input") -> None:
    if type(value) is float:
        raise InputError(f"{name} contains a floating-point value")
    if type(value) is list:
        for index, item in enumerate(value):
            _reject_floats(item, f"{name}[{index}]")
    if type(value) is dict:
        for key, item in value.items():
            _reject_floats(item, f"{name}.{key}")
