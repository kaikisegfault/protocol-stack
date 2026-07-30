"""Strict participation-v1 JSON validation."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Callable

from .domain import (
    MAX_U64,
    Authorities,
    ContributionPolicy,
    Manifest,
    Parameters,
)

MANIFEST_SCHEMA = "protocol-stack/participation-simulation-manifest/v1"
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")


class InputError(ValueError):
    """Input does not satisfy the participation-v1 schema."""


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
            "parameters",
            "authorities",
            "contributions",
            "genesis",
        },
        "manifest",
    )
    if source["schema"] != MANIFEST_SCHEMA:
        raise InputError("unsupported manifest schema")
    if source["research_only"] is not True:
        raise InputError("research_only must be true")
    parameters = _parse_parameters(source["parameters"])
    authorities = _parse_authorities(source["authorities"])
    contributions = _parse_contributions(source["contributions"])
    genesis = _object(source["genesis"], "genesis")
    _exact_fields(genesis, {"height"}, "genesis")
    return Manifest(
        parameters=parameters,
        authorities=authorities,
        contributions=contributions,
        genesis_height=_u64(genesis["height"], "genesis.height"),
        source=copy.deepcopy(source),
    )


def _parse_parameters(value: Any) -> Parameters:
    source = _object(value, "parameters")
    fields = {
        "epoch_length",
        "activation_delay_epochs",
        "exit_delay_epochs",
        "removal_hold_epochs",
        "max_jail_epochs",
        "max_participants",
        "validator_minimum_bond",
        "max_units_per_proof",
        "max_units_per_participant_epoch",
    }
    _exact_fields(source, fields, "parameters")
    result = Parameters(
        **{key: _u64(source[key], f"parameters.{key}", nonzero=True) for key in fields}
    )
    if result.max_units_per_proof > result.max_units_per_participant_epoch:
        raise InputError("max_units_per_proof exceeds participant epoch cap")
    return result


def _parse_authorities(value: Any) -> Authorities:
    source = _object(value, "authorities")
    fields = {
        "clock",
        "registration",
        "stake",
        "lifecycle",
        "enforcement",
        "reward",
    }
    _exact_fields(source, fields, "authorities")
    return Authorities(
        **{key: _identifier(source[key], f"authorities.{key}") for key in fields}
    )


def _parse_contributions(
    value: Any,
) -> dict[str, dict[str, ContributionPolicy]]:
    source = _object(value, "contributions")
    _exact_fields(source, {"validators", "nodes"}, "contributions")
    result: dict[str, dict[str, ContributionPolicy]] = {}
    for plural_role in ("validators", "nodes"):
        policies = _object(source[plural_role], f"contributions.{plural_role}")
        if not policies:
            raise InputError(f"contributions.{plural_role} must not be empty")
        parsed: dict[str, ContributionPolicy] = {}
        for kind, value_item in policies.items():
            parsed_kind = _identifier(kind, f"contributions.{plural_role} key")
            item = _object(value_item, f"contributions.{plural_role}.{kind}")
            _exact_fields(item, {"verifier", "weight"}, f"contribution {kind}")
            parsed[parsed_kind] = ContributionPolicy(
                verifier=_identifier(item["verifier"], f"{kind}.verifier"),
                weight=_u64(item["weight"], f"{kind}.weight", nonzero=True),
            )
        result[_singular(plural_role)] = parsed
    return result


_BASE_FIELDS = {"id", "height", "kind", "actor"}
_PROOF_FIELDS = {"proof_id", "evidence_digest"}
_EVENT_FIELDS = {
    "advance_height": {"to_height"},
    "register_validator": {
        "participant",
        "owner",
        "payout_account",
        "bond_id",
    }
    | _PROOF_FIELDS,
    "register_node": {"participant", "owner", "payout_account"} | _PROOF_FIELDS,
    "confirm_bond": {"participant", "bond_id", "amount"} | _PROOF_FIELDS,
    "activate": {"participant"},
    "request_exit": {"participant"},
    "complete_exit": {"participant"},
    "jail": {"participant", "until_epoch"} | _PROOF_FIELDS,
    "request_recovery": {"participant"},
    "recover": {"participant"},
    "remove": {"participant", "reason"} | _PROOF_FIELDS,
    "attest_contribution": {
        "participant",
        "role",
        "contribution_kind",
        "epoch",
        "units",
    }
    | _PROOF_FIELDS,
    "set_reward_budget": {"epoch", "role", "amount"},
    "settle_entitlement": {"epoch", "role", "participant"},
    "finalize_budget": {"epoch", "role"},
}
_IDENTIFIER_FIELDS = {
    "id",
    "actor",
    "participant",
    "owner",
    "payout_account",
    "bond_id",
    "proof_id",
    "reason",
    "contribution_kind",
}
_U64_FIELDS = {"height", "to_height", "amount", "until_epoch", "epoch", "units"}


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
        elif key in _U64_FIELDS:
            result[key] = _u64(item, name)
        elif key == "evidence_digest":
            result[key] = _digest(item, name)
        elif key == "role":
            result[key] = _enum(item, {"validator", "node"}, name)
        elif key == "kind":
            result[key] = item
        else:
            raise InputError(f"events[{index}] has unparsed field {key}")
    return result


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


def _enum(value: Any, allowed: set[str], name: str) -> str:
    if type(value) is not str or value not in allowed:
        raise InputError(f"{name} is not one of {sorted(allowed)}")
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


def _singular(role: str) -> str:
    return "validator" if role == "validators" else "node"
