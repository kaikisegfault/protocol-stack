"""Strict version-one JSON validation."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Callable

from .types import (
    MAX_U64,
    Authorities,
    Genesis,
    Manifest,
    Parameters,
    Participants,
    checked_add,
)

MANIFEST_SCHEMA = "protocol-stack/native-economy-simulation-manifest/v1"
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


class InputError(ValueError):
    """Input does not satisfy the version-one schema."""


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


def _object(value: Any, name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise InputError(f"{name} must be an object")
    return value


def _exact_fields(value: dict[str, Any], expected: set[str], name: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        raise InputError(f"{name} fields: missing={missing}, unknown={unknown}")


def _identifier(value: Any, name: str) -> str:
    if type(value) is not str or IDENTIFIER.fullmatch(value) is None:
        raise InputError(f"{name} is not a version-one identifier")
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


def _identifier_map(value: Any, name: str, parse_value: Callable[[Any, str], Any]) -> dict:
    source = _object(value, name)
    result = {}
    for key, item in source.items():
        parsed_key = _identifier(key, f"{name} key")
        result[parsed_key] = parse_value(item, f"{name}.{key}")
    return result


def _reject_floats(value: Any, name: str = "input") -> None:
    if type(value) is float:
        raise InputError(f"{name} contains a floating-point value")
    if type(value) is list:
        for index, item in enumerate(value):
            _reject_floats(item, f"{name}[{index}]")
    if type(value) is dict:
        for key, item in value.items():
            _reject_floats(item, f"{name}.{key}")


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
            "participants",
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
    participants = _parse_participants(source["participants"])
    genesis = _parse_genesis(source["genesis"])
    _validate_genesis(genesis, parameters)
    return Manifest(
        parameters=parameters,
        authorities=authorities,
        participants=participants,
        genesis=genesis,
        source=copy.deepcopy(source),
    )


def _parse_parameters(value: Any) -> Parameters:
    source = _object(value, "parameters")
    fields = {
        "supply_limit",
        "epoch_length",
        "unbonding_epochs",
        "fee_split_denominator",
        "fee_reward_parts",
    }
    _exact_fields(source, fields, "parameters")
    result = Parameters(
        supply_limit=_u64(source["supply_limit"], "supply_limit", nonzero=True),
        epoch_length=_u64(source["epoch_length"], "epoch_length", nonzero=True),
        unbonding_epochs=_u64(
            source["unbonding_epochs"],
            "unbonding_epochs",
            nonzero=True,
        ),
        fee_split_denominator=_u64(
            source["fee_split_denominator"],
            "fee_split_denominator",
            nonzero=True,
        ),
        fee_reward_parts=_u64(source["fee_reward_parts"], "fee_reward_parts"),
    )
    if result.fee_reward_parts > result.fee_split_denominator:
        raise InputError("fee_reward_parts exceeds denominator")
    return result


def _parse_authorities(value: Any) -> Authorities:
    source = _object(value, "authorities")
    fields = {
        "clock",
        "issuance",
        "fee_allocation",
        "treasury",
        "escrow",
        "reward",
        "penalty",
    }
    _exact_fields(source, fields, "authorities")
    return Authorities(
        **{key: _identifier(source[key], f"authorities.{key}") for key in fields}
    )


def _parse_participants(value: Any) -> Participants:
    source = _object(value, "participants")
    _exact_fields(source, {"validators", "nodes"}, "participants")
    validators = _identifier_map(source["validators"], "validators", _identifier)
    nodes = _identifier_map(source["nodes"], "nodes", _identifier)
    overlap = sorted(set(validators) & set(nodes))
    if overlap:
        raise InputError(f"participant role overlap: {overlap}")
    return Participants(validators=validators, nodes=nodes)


def _parse_genesis(value: Any) -> Genesis:
    source = _object(value, "genesis")
    fields = {
        "height",
        "issued_supply",
        "accounts",
        "fee_pool",
        "treasury",
        "reward_pool",
        "penalty_pool",
    }
    _exact_fields(source, fields, "genesis")
    accounts = _identifier_map(
        source["accounts"],
        "accounts",
        lambda item, name: _u64(item, name),
    )
    return Genesis(
        height=_u64(source["height"], "genesis.height"),
        issued_supply=_u64(
            source["issued_supply"],
            "genesis.issued_supply",
            nonzero=True,
        ),
        accounts=accounts,
        fee_pool=_u64(source["fee_pool"], "genesis.fee_pool"),
        treasury=_u64(source["treasury"], "genesis.treasury"),
        reward_pool=_u64(source["reward_pool"], "genesis.reward_pool"),
        penalty_pool=_u64(source["penalty_pool"], "genesis.penalty_pool"),
    )


def _validate_genesis(genesis: Genesis, parameters: Parameters) -> None:
    total = 0
    values = list(genesis.accounts.values())
    values.extend(
        [
            genesis.fee_pool,
            genesis.treasury,
            genesis.reward_pool,
            genesis.penalty_pool,
        ]
    )
    for value in values:
        result = checked_add(total, value)
        if result is None:
            raise InputError("genesis custody exceeds u64")
        total = result
    if total != genesis.issued_supply:
        raise InputError("genesis custody does not equal issued_supply")
    if genesis.issued_supply > parameters.supply_limit:
        raise InputError("genesis issued_supply exceeds supply_limit")


_BASE_FIELDS = {"id", "height", "kind", "actor"}
_EVENT_FIELDS = {
    "advance_height": {"to_height"},
    "issue": {"amount"},
    "transfer": {"source", "destination", "amount"},
    "charge_fee": {"account", "amount"},
    "allocate_fees": {"amount"},
    "treasury_grant": {"recipient", "amount"},
    "fund_rewards": {"amount"},
    "open_escrow": {
        "escrow_id",
        "escrow_kind",
        "source_kind",
        "source",
        "beneficiary",
        "unlock_epoch",
        "amount",
    },
    "release_escrow": {"escrow_id"},
    "bond": {"bond_id", "owner", "validator", "amount"},
    "begin_unbond": {"bond_id", "unbonding_id", "amount"},
    "complete_unbond": {"unbonding_id"},
    "allocate_reward": {"role", "participant", "amount"},
    "claim_reward": {"role", "participant", "amount"},
    "penalize": {"source_kind", "position_id", "amount"},
    "route_penalty": {"amount"},
}
_IDENTIFIER_FIELDS = {
    "id",
    "actor",
    "source",
    "destination",
    "account",
    "recipient",
    "escrow_id",
    "beneficiary",
    "bond_id",
    "owner",
    "validator",
    "unbonding_id",
    "participant",
    "position_id",
}
_U64_FIELDS = {"height", "to_height", "unlock_epoch", "amount"}


def parse_events(value: Any) -> list[dict[str, Any]]:
    _reject_floats(value)
    if type(value) is not list:
        raise InputError("events must be an array")
    return [_parse_event(item, index) for index, item in enumerate(value)]


def _parse_event(value: Any, index: int) -> dict[str, Any]:
    source = _object(value, f"events[{index}]")
    if type(source.get("kind")) is not str or source["kind"] not in _EVENT_FIELDS:
        raise InputError(f"events[{index}].kind is unsupported")
    expected = _BASE_FIELDS | _EVENT_FIELDS[source["kind"]]
    _exact_fields(source, expected, f"events[{index}]")

    result: dict[str, Any] = {}
    for key, item in source.items():
        name = f"events[{index}].{key}"
        if key in _IDENTIFIER_FIELDS:
            result[key] = _identifier(item, name)
        elif key in _U64_FIELDS:
            result[key] = _u64(item, name)
        elif key == "kind":
            result[key] = item
        elif key == "role":
            result[key] = _enum(item, {"validator", "node"}, name)
        elif key == "escrow_kind":
            result[key] = _enum(item, {"general", "venture"}, name)
        elif key == "source_kind" and source["kind"] == "open_escrow":
            result[key] = _enum(item, {"account", "treasury"}, name)
        elif key == "source_kind":
            result[key] = _enum(item, {"bond", "unbonding"}, name)
        else:
            raise InputError(f"events[{index}] has unparsed field {key}")
    return result
