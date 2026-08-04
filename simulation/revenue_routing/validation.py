"""Strict version-one routing event parsing.

A failure here is an input-shape error that aborts the run. It is distinct from
a modelled rejection, which must produce a deterministic trace record.
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
    "route_commercial_payment": {
        "payment_id",
        "amount_atomic",
        "project_creator_id",
        "product_creator_id",
    },
    "route_transaction_fee": {"fee_id", "amount_atomic"},
    "close_cycle": {"cycle_index", "active_seats_result"},
}
_SNAPSHOT_FIELDS = {"cycle_index", "seat_ids"}


class InputError(ValueError):
    """Input does not satisfy the version-one routing event schema."""


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

    parsed: dict[str, Any] = {
        "id": _identifier(source["id"], f"{name}.id"),
        "kind": kind,
    }
    if kind == "route_commercial_payment":
        parsed.update(_parse_payment(source, name))
    elif kind == "route_transaction_fee":
        parsed.update(
            {
                "fee_id": _identifier(source["fee_id"], f"{name}.fee_id"),
                "amount_atomic": _amount(source["amount_atomic"], f"{name}.amount_atomic"),
            }
        )
    else:
        parsed.update(_parse_close(source, name))
    return parsed


def _parse_payment(source: dict[str, Any], name: str) -> dict[str, Any]:
    product = source["product_creator_id"]
    return {
        "payment_id": _identifier(source["payment_id"], f"{name}.payment_id"),
        "amount_atomic": _amount(source["amount_atomic"], f"{name}.amount_atomic"),
        "project_creator_id": _identifier(
            source["project_creator_id"], f"{name}.project_creator_id"
        ),
        "product_creator_id": (
            None if product is None
            else _identifier(product, f"{name}.product_creator_id")
        ),
    }


def _parse_close(source: dict[str, Any], name: str) -> dict[str, Any]:
    snapshot = source["active_seats_result"]
    return {
        "cycle_index": _count(source["cycle_index"], f"{name}.cycle_index"),
        "active_seats_result": (
            None if snapshot is None
            else _parse_snapshot(snapshot, f"{name}.active_seats_result")
        ),
    }


def _parse_snapshot(value: Any, name: str) -> dict[str, Any]:
    source = _object(value, name)
    _exact_fields(source, _SNAPSHOT_FIELDS, name)
    raw_seats = source["seat_ids"]
    if type(raw_seats) is not list:
        raise InputError(f"{name}.seat_ids must be an array")
    if len(raw_seats) > c.FOUNDER_SEAT_CAPACITY:
        raise InputError(f"{name}.seat_ids exceeds the founder seat capacity")

    seats = [
        _count(seat, f"{name}.seat_ids[{index}]")
        for index, seat in enumerate(raw_seats)
    ]
    for seat in seats:
        if seat >= c.FOUNDER_SEAT_CAPACITY:
            raise InputError(f"{name}.seat_ids contains a seat beyond the capacity")
    if any(later <= earlier for earlier, later in zip(seats, seats[1:])):
        raise InputError(f"{name}.seat_ids is not strictly ascending")
    return {
        "cycle_index": _count(source["cycle_index"], f"{name}.cycle_index"),
        "seat_ids": seats,
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
