"""Strict version-three simulator event parsing.

A failure here is an input-shape error that aborts the run. It is distinct from
a modelled rejection, which must produce a deterministic trace record.

Version three adds one field, `activation_height`. It is a canonical unsigned
decimal string rather than a JSON number, because a u64 height can exceed the
largest integer a conforming JSON stack represents exactly. A cycle window is a
height divided by 28,800 and cannot, so windows stay JSON numbers and the uptime
record's shape is version two's unchanged.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..common.canonical import MAX_JSON_INTEGER, parse_atomic
from ..founder_economy_v2.manifest import ManifestError, parse_json

IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

_BASE_FIELDS = {"id", "kind"}
_EVENT_FIELDS: dict[str, set[str]] = {
    "activate_seat": {"seat_id", "referrer_seat_id", "activation_height"},
    "evaluate_base_permission": {"seat_id", "cycle_index", "cycle_uptime_record"},
    "accrue_referral": {"seat_id", "cycle_index"},
    "exercise_permission": {"seat_id", "cycle_index"},
    "direct_issue": {
        "channel",
        "decision_id",
        "beneficiary_id",
        "amount_atomic",
        "eligibility_result",
    },
}
_ELIGIBILITY_FIELDS = {
    "channel",
    "decision_id",
    "beneficiary_id",
    "amount_atomic",
    "eligible",
}
_RECORD_FIELDS = {"cycle_window", "entries"}
_ENTRY_FIELDS = {"seat_id", "uptime_seconds"}
_COUNT_FIELDS = {"seat_id", "cycle_index", "cycle_window", "uptime_seconds"}
# Rendered as canonical decimal strings because each is a u64: a monetary
# amount by the accepted denomination, and a height by the cycle-boundary rule.
_DECIMAL_STRING_FIELDS = {"amount_atomic", "activation_height"}


class InputError(ValueError):
    """Input does not satisfy the version-three simulator event schema."""


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
    if key == "eligibility_result":
        return None if value is None else _parse_eligibility(value, name)
    if key == "cycle_uptime_record":
        return None if value is None else _parse_record(value, name)
    if key == "referrer_seat_id":
        return None if value is None else _count(value, name)
    if key in _COUNT_FIELDS:
        return _count(value, name)
    if key in _DECIMAL_STRING_FIELDS:
        return _decimal_string(value, name)
    return _identifier(value, name)


def _parse_eligibility(value: Any, name: str) -> dict[str, Any]:
    source = _object(value, name)
    _exact_fields(source, _ELIGIBILITY_FIELDS, name)
    parsed: dict[str, Any] = {}
    for field in sorted(_ELIGIBILITY_FIELDS):
        item = source[field]
        item_name = f"{name}.{field}"
        if field == "eligible":
            parsed[field] = _boolean(item, item_name)
        elif field == "amount_atomic":
            parsed[field] = _decimal_string(item, item_name)
        else:
            parsed[field] = _identifier(item, item_name)
    return parsed


def _parse_record(value: Any, name: str) -> dict[str, Any]:
    """Parse one cycle uptime record.

    Every field is a count, so no verdict, ranking, or amount is expressible.
    Semantic validity — bounds, duplicates, activation, and the presence of the
    evaluated seat — is a modelled rejection and is checked in `uptime.py`.
    """
    source = _object(value, name)
    _exact_fields(source, _RECORD_FIELDS, name)
    entries = source["entries"]
    if type(entries) is not list:
        raise InputError(f"{name}.entries must be an array")
    return {
        "cycle_window": _count(source["cycle_window"], f"{name}.cycle_window"),
        "entries": [
            _parse_entry(item, f"{name}.entries[{index}]")
            for index, item in enumerate(entries)
        ],
    }


def _parse_entry(value: Any, name: str) -> dict[str, Any]:
    source = _object(value, name)
    _exact_fields(source, _ENTRY_FIELDS, name)
    return {
        "seat_id": _count(source["seat_id"], f"{name}.seat_id"),
        "uptime_seconds": _count(source["uptime_seconds"], f"{name}.uptime_seconds"),
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
        raise InputError(f"{name} is not a version-three identifier")
    return value


def _boolean(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise InputError(f"{name} must be a JSON boolean")
    return value


def _count(value: Any, name: str) -> int:
    """Parse a small exact count.

    The bound is the largest integer a conforming JSON stack represents
    exactly, not `u64`. Counts are serialized as JSON numbers in digest
    preimages, so a larger value could not be canonicalized and must be
    rejected as input rather than reaching a digest.
    """
    if type(value) is bool or type(value) is not int or not 0 <= value <= MAX_JSON_INTEGER:
        raise InputError(f"{name} is not an exact unsigned JSON integer")
    return value


def _decimal_string(value: Any, name: str) -> str:
    """Parse a u64 rendered as a canonical unsigned decimal string.

    A value above u64 is an input-shape error rather than a modelled rejection,
    so `HEIGHT_RANGE` is reserved for a representable height whose 731-window
    span is not.
    """
    if parse_atomic(value) is None:
        raise InputError(f"{name} is not a canonical u64 decimal string")
    return value
