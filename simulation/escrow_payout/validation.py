"""Strict version-one escrow payout event parsing.

A failure here is an input-shape error that aborts the run. It is distinct from
a modelled rejection, which must produce a deterministic trace record. An
`escrow_id` outside the fixed set parses successfully on purpose, so the trace
records the attempt rather than aborting.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import contract as c
from ..common.canonical import MAX_JSON_INTEGER, parse_atomic

IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

_BASE_FIELDS = {"id", "kind"}
_EVENT_FIELDS: dict[str, set[str]] = {
    "bind_opening_custody": {"economy_state_result"},
    "grant_capability": {
        "capability_id",
        "escrow_id",
        "per_payout_maximum",
        "envelope_total",
        "expiry_cycle",
    },
    "execute_payout": {
        "payout_id",
        "capability_id",
        "escrow_id",
        "recipient_id",
        "amount_atomic",
        "approval_result",
    },
    "revoke_capability": {"capability_id"},
    "advance_cycle": {"cycle_index"},
}
_ECONOMY_FIELDS = {"state_digest", "state_value"}
_APPROVAL_FIELDS = {"payout_id", "decision", "evaluation_reference"}

DIGEST = re.compile(r"^[0-9a-f]{64}$")


class InputError(ValueError):
    """Input does not satisfy the version-one escrow payout event schema."""


def load_events_file(path: str | Path) -> list[dict[str, Any]]:
    try:
        raw = Path(path).read_bytes().decode("utf-8")
        value = json.loads(
            raw,
            object_pairs_hook=_pairs,
            parse_float=_reject_float,
            parse_constant=_reject_float,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InputError(f"invalid events JSON: {error}") from error
    return parse_events(value)


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise InputError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_float(value: str) -> float:
    raise InputError(f"floating-point JSON value is forbidden: {value}")


def parse_events(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise InputError("events must be an array")
    events = [_parse_event(item, index) for index, item in enumerate(value)]
    seen: set[str] = set()
    for event in events:
        if event["id"] in seen:
            raise InputError(f"duplicate event id: {event['id']}")
        seen.add(event["id"])
    return events


def _parse_event(value: Any, index: int) -> dict[str, Any]:
    name = f"events[{index}]"
    source = _object(value, name)
    kind = source.get("kind")
    if type(kind) is not str or kind not in _EVENT_FIELDS:
        raise InputError(f"{name}.kind is unsupported")
    _exact_fields(source, _BASE_FIELDS | _EVENT_FIELDS[kind], name)

    parsed: dict[str, Any] = {
        "id": _identifier(source["id"], f"{name}.id"),
        "kind": kind,
    }
    parsed.update(_PARSERS[kind](source, name))
    return parsed


def _parse_bind(source: dict[str, Any], name: str) -> dict[str, Any]:
    supplied = source["economy_state_result"]
    return {
        "economy_state_result": (
            None
            if supplied is None
            else _parse_economy_state(supplied, f"{name}.economy_state_result")
        )
    }


def _parse_economy_state(value: Any, name: str) -> dict[str, Any]:
    source = _object(value, name)
    _exact_fields(source, _ECONOMY_FIELDS, name)
    recorded = source["state_digest"]
    if type(recorded) is not str or DIGEST.fullmatch(recorded) is None:
        raise InputError(f"{name}.state_digest is not a lowercase sha-256 digest")
    if type(source["state_value"]) is not dict:
        raise InputError(f"{name}.state_value must be an object")
    return {"state_digest": recorded, "state_value": source["state_value"]}


def _parse_grant(source: dict[str, Any], name: str) -> dict[str, Any]:
    return {
        "capability_id": _identifier(
            source["capability_id"], f"{name}.capability_id"
        ),
        "escrow_id": _identifier(source["escrow_id"], f"{name}.escrow_id"),
        "per_payout_maximum": _amount(
            source["per_payout_maximum"], f"{name}.per_payout_maximum"
        ),
        "envelope_total": _amount(
            source["envelope_total"], f"{name}.envelope_total"
        ),
        "expiry_cycle": _count(source["expiry_cycle"], f"{name}.expiry_cycle"),
    }


def _parse_payout(source: dict[str, Any], name: str) -> dict[str, Any]:
    approval = source["approval_result"]
    return {
        "payout_id": _identifier(source["payout_id"], f"{name}.payout_id"),
        "capability_id": _identifier(
            source["capability_id"], f"{name}.capability_id"
        ),
        "escrow_id": _identifier(source["escrow_id"], f"{name}.escrow_id"),
        "recipient_id": _identifier(source["recipient_id"], f"{name}.recipient_id"),
        "amount_atomic": _amount(source["amount_atomic"], f"{name}.amount_atomic"),
        "approval_result": (
            None
            if approval is None
            else _parse_approval(approval, f"{name}.approval_result")
        ),
    }


def _parse_approval(value: Any, name: str) -> dict[str, Any]:
    source = _object(value, name)
    _exact_fields(source, _APPROVAL_FIELDS, name)
    decision = source["decision"]
    if type(decision) is not str or decision not in c.DECISIONS:
        raise InputError(f"{name}.decision is not an accepted decision")
    return {
        "payout_id": _identifier(source["payout_id"], f"{name}.payout_id"),
        "decision": decision,
        "evaluation_reference": _identifier(
            source["evaluation_reference"], f"{name}.evaluation_reference"
        ),
    }


def _parse_revoke(source: dict[str, Any], name: str) -> dict[str, Any]:
    return {
        "capability_id": _identifier(
            source["capability_id"], f"{name}.capability_id"
        )
    }


def _parse_advance(source: dict[str, Any], name: str) -> dict[str, Any]:
    return {"cycle_index": _count(source["cycle_index"], f"{name}.cycle_index")}


_PARSERS = {
    "bind_opening_custody": _parse_bind,
    "grant_capability": _parse_grant,
    "execute_payout": _parse_payout,
    "revoke_capability": _parse_revoke,
    "advance_cycle": _parse_advance,
}


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


def _count(value: Any, name: str) -> int:
    if type(value) is bool or type(value) is not int:
        raise InputError(f"{name} is not an exact unsigned JSON integer")
    if not 0 <= value <= MAX_JSON_INTEGER:
        raise InputError(f"{name} is not an exact unsigned JSON integer")
    return value


def _amount(value: Any, name: str) -> str:
    if parse_atomic(value) is None:
        raise InputError(f"{name} is not a canonical u64 decimal string")
    return value
