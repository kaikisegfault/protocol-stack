"""Checked integer arithmetic, RFC 8785 canonical bytes, and domain digests."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

MAX_U64 = (1 << 64) - 1
MAX_JSON_INTEGER = (1 << 53) - 1
DECIMAL_STRING = re.compile(r"^(?:0|[1-9][0-9]*)$")


class InvariantError(RuntimeError):
    """The simulator constructed or proposed an invalid state."""


class CodedError(ValueError):
    """An acceptance failure carrying one of the specified result codes."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def checked_add(left: int, right: int) -> int | None:
    if left > MAX_U64 - right:
        return None
    return left + right


def checked_sub(left: int, right: int) -> int | None:
    if right > left:
        return None
    return left - right


def checked_mul(left: int, right: int) -> int | None:
    if left != 0 and right > MAX_U64 // left:
        return None
    return left * right


def checked_sum(values: list[int]) -> int | None:
    total = 0
    for value in values:
        result = checked_add(total, value)
        if result is None:
            return None
        total = result
    return total


def required_sum(values: list[int], detail: str) -> int:
    """Sum values, treating overflow as a simulator defect rather than input."""
    total = checked_sum(values)
    if total is None:
        raise InvariantError(f"checked sum exceeds u64: {detail}")
    return total


def is_canonical_decimal(value: Any) -> bool:
    return type(value) is str and DECIMAL_STRING.fullmatch(value) is not None


def parse_atomic(value: Any) -> int | None:
    """Parse a canonical unsigned decimal string into a u64, or return None."""
    if not is_canonical_decimal(value):
        return None
    parsed = int(value)
    return parsed if parsed <= MAX_U64 else None


def format_atomic(value: int) -> str:
    if type(value) is not int or not 0 <= value <= MAX_U64:
        raise InvariantError(f"cannot format non-u64 monetary value: {value!r}")
    return str(value)


def canonical_bytes(value: Any) -> bytes:
    """Serialize a JCS-compatible value to RFC 8785 canonical UTF-8 bytes.

    Every monetary value must already be a canonical decimal string, so the
    only integers reaching this function are small exact counts whose shortest
    JSON representation is unambiguous.
    """
    _assert_canonical(value, "value")
    text = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return text.encode("utf-8")


def _assert_canonical(value: Any, name: str) -> None:
    kind = type(value)
    if kind is bool or value is None or kind is str:
        return
    if kind is int:
        if not 0 <= value <= MAX_JSON_INTEGER:
            raise InvariantError(f"{name} is an out-of-range JSON integer")
        return
    if kind is list:
        for index, item in enumerate(value):
            _assert_canonical(item, f"{name}[{index}]")
        return
    if kind is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise InvariantError(f"{name} has a non-string key")
            _assert_canonical(item, f"{name}.{key}")
        return
    raise InvariantError(f"{name} has non-canonical type {kind.__name__}")


def label_prefix(label: str) -> bytes:
    """Return D(L) = u8(byte_length(L)) || ascii(L)."""
    encoded = label.encode("ascii")
    if not 0 < len(encoded) < 256:
        raise InvariantError(f"domain label length is out of range: {label!r}")
    return bytes([len(encoded)]) + encoded


def digest(label: str, value: Any) -> str:
    return hashlib.sha256(label_prefix(label) + canonical_bytes(value)).hexdigest()
