"""Strict version-one simulator event parsing.

A failure here is an input-shape error that aborts the run. It is distinct from
a modelled rejection, which must produce a deterministic trace record.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .canonical import MAX_U64, parse_atomic
from .manifest import ManifestError, parse_json

IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

_BASE_FIELDS = {"id", "kind"}
_EVENT_FIELDS: dict[str, set[str]] = {
    "activate_seat": {"seat_id", "referrer_seat_id"},
    "evaluate_base_permission": {
        "seat_id",
        "cycle_index",
        "activity_result",
        "performance_allocation",
    },
    "evaluate_referral_permission": {
        "seat_id",
        "cycle_index",
        "activity_result",
        "inactive_referral_result",
    },
    "exercise_permission": {"seat_id", "cycle_index", "permission_kind"},
    "direct_issue": {
        "channel",
        "decision_id",
        "beneficiary_id",
        "amount_atomic",
        "eligibility_result",
    },
}
_RESULT_FIELDS: dict[str, set[str]] = {
    "activity_result": {"seat_id", "cycle_index", "active"},
    "performance_allocation": {"seat_id", "cycle_index", "allocations"},
    "inactive_referral_result": {"seat_id", "cycle_index", "create"},
    "eligibility_result": {
        "channel",
        "decision_id",
        "beneficiary_id",
        "amount_atomic",
        "eligible",
    },
}
_RESULT_FLAGS = {
    "activity_result": "active",
    "performance_allocation": None,
    "inactive_referral_result": "create",
    "eligibility_result": "eligible",
}


class InputError(ValueError):
    """Input does not satisfy the version-one simulator event schema."""


def load_events_file(path: str | Path) -> list[dict[str, Any]]:
    try:
        value = parse_json(Path(path).read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, ManifestError) as error:
        raise InputError(f"invalid events JSON: {error}") from error
    return parse_events(value)


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

    result: dict[str, Any] = {"kind": kind, "id": _identifier(source["id"], f"{name}.id")}
    for key in sorted(_EVENT_FIELDS[kind]):
        result[key] = _parse_field(key, source[key], f"{name}.{key}")
    return result


def _parse_field(key: str, value: Any, name: str) -> Any:
    if key in _RESULT_FIELDS:
        return None if value is None else _parse_result(key, value, name)
    if key == "referrer_seat_id":
        return None if value is None else _count(value, name)
    if key in {"seat_id", "cycle_index"}:
        return _count(value, name)
    if key == "amount_atomic":
        return _atomic(value, name)
    if key == "permission_kind":
        return _enum(value, {"base", "referral"}, name)
    return _identifier(value, name)


def _parse_result(key: str, value: Any, name: str) -> dict[str, Any]:
    source = _object(value, name)
    _exact_fields(source, _RESULT_FIELDS[key], name)
    parsed: dict[str, Any] = {}
    for field in sorted(_RESULT_FIELDS[key]):
        item = source[field]
        item_name = f"{name}.{field}"
        if field == _RESULT_FLAGS[key]:
            parsed[field] = _boolean(item, item_name)
        elif field == "allocations":
            parsed[field] = _parse_allocations(item, item_name)
        elif field in {"seat_id", "cycle_index"}:
            parsed[field] = _count(item, item_name)
        elif field == "amount_atomic":
            parsed[field] = _atomic(item, item_name)
        else:
            parsed[field] = _identifier(item, item_name)
    return parsed


def _parse_allocations(value: Any, name: str) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise InputError(f"{name} must be an array")
    entries = []
    for index, item in enumerate(value):
        entry_name = f"{name}[{index}]"
        source = _object(item, entry_name)
        _exact_fields(source, {"seat_id", "amount_atomic"}, entry_name)
        entries.append(
            {
                "seat_id": _count(source["seat_id"], f"{entry_name}.seat_id"),
                "amount_atomic": _atomic(
                    source["amount_atomic"], f"{entry_name}.amount_atomic"
                ),
            }
        )
    return entries


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


def _enum(value: Any, allowed: set[str], name: str) -> str:
    if type(value) is not str or value not in allowed:
        raise InputError(f"{name} is not one of {sorted(allowed)}")
    return value


def _boolean(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise InputError(f"{name} must be a JSON boolean")
    return value


def _count(value: Any, name: str) -> int:
    if type(value) is bool or type(value) is not int or not 0 <= value <= MAX_U64:
        raise InputError(f"{name} is not an unsigned JSON integer")
    return value


def _atomic(value: Any, name: str) -> str:
    if parse_atomic(value) is None:
        raise InputError(f"{name} is not a canonical u64 decimal string")
    return value
