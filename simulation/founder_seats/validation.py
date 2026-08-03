"""Strict version-one seat sale event parsing.

A failure here is an input-shape error that aborts the run. It is distinct from
a modelled rejection, which must produce a deterministic trace record.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..common.canonical import MAX_JSON_INTEGER, parse_atomic

IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

_BASE_FIELDS = {"id", "kind"}
_EVENT_FIELDS: dict[str, set[str]] = {
    "purchase_seat": {
        "purchase_id",
        "principal_id",
        "referrer_seat_id",
        "payment_result",
    },
}
_PAYMENT_FIELDS = {
    "purchase_id",
    "principal_id",
    "seat_id",
    "price_usd_cents",
    "settled",
}


class InputError(ValueError):
    """Input does not satisfy the version-one seat sale event schema."""


def load_events_file(path: str | Path) -> list[dict[str, Any]]:
    try:
        raw = Path(path).read_bytes().decode("utf-8")
        value = json.loads(raw, object_pairs_hook=_pairs, parse_float=_reject_float,
                           parse_constant=_reject_float)
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

    referrer = source["referrer_seat_id"]
    payment = source["payment_result"]
    return {
        "id": _identifier(source["id"], f"{name}.id"),
        "kind": kind,
        "purchase_id": _identifier(source["purchase_id"], f"{name}.purchase_id"),
        "principal_id": _identifier(source["principal_id"], f"{name}.principal_id"),
        "referrer_seat_id": (
            None if referrer is None
            else _count(referrer, f"{name}.referrer_seat_id")
        ),
        "payment_result": (
            None if payment is None
            else _parse_payment(payment, f"{name}.payment_result")
        ),
    }


def _parse_payment(value: Any, name: str) -> dict[str, Any]:
    source = _object(value, name)
    _exact_fields(source, _PAYMENT_FIELDS, name)
    return {
        "purchase_id": _identifier(source["purchase_id"], f"{name}.purchase_id"),
        "principal_id": _identifier(source["principal_id"], f"{name}.principal_id"),
        "seat_id": _count(source["seat_id"], f"{name}.seat_id"),
        "price_usd_cents": _cents(source["price_usd_cents"], f"{name}.price_usd_cents"),
        "settled": _boolean(source["settled"], f"{name}.settled"),
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


def _boolean(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise InputError(f"{name} must be a JSON boolean")
    return value


def _count(value: Any, name: str) -> int:
    if type(value) is bool or type(value) is not int:
        raise InputError(f"{name} is not an exact unsigned JSON integer")
    if not 0 <= value <= MAX_JSON_INTEGER:
        raise InputError(f"{name} is not an exact unsigned JSON integer")
    return value


def _cents(value: Any, name: str) -> str:
    if parse_atomic(value) is None:
        raise InputError(f"{name} is not a canonical u64 decimal string")
    return value
