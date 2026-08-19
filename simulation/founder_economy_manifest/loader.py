"""Strict Founder Economy manifest loading with the accepted failure order.

The stages, their order, and every result code are the same for every accepted
manifest version. What differs between versions is the contract table each one
compares against, so a `ManifestLoader` is constructed by binding one table and
the stages read it through that binding rather than importing a version.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..common.canonical import (
    MAX_U64,
    CodedError,
    canonical_bytes,
    digest,
    is_canonical_decimal,
)
from .derivations import DerivationError, check_derivations
from .fields import (
    COUNT_LIMITS,
    DENOMINATION_FIELDS,
    REFERRAL_FIELDS,
    SEAT_FIELDS,
    TOP_FIELDS,
    boolean_items,
    count_items,
    monetary_items,
    text_items,
)


class ManifestError(CodedError):
    """A manifest failed one of the ordered acceptance checks."""


@dataclass(frozen=True)
class Manifest:
    """An accepted manifest and its canonical identity."""

    source: dict[str, Any]
    canonical_length: int
    manifest_digest: str
    contract: Any

    @property
    def maximum_supply_atomic(self) -> int:
        return self.contract.MAXIMUM_SUPPLY_ATOMIC

    @property
    def channel_caps(self) -> dict[str, int]:
        return dict(self.contract.CHANNEL_CAPS)


def parse_json(raw: str) -> Any:
    """Parse duplicate-free I-JSON, rejecting any floating-point token."""

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ManifestError("INVALID_JSON", f"duplicate field: {key}")
            result[key] = value
        return result

    def reject_float(value: str) -> float:
        raise ManifestError("INVALID_JSON", f"floating-point token: {value}")

    try:
        return json.loads(
            raw,
            object_pairs_hook=pairs,
            parse_float=reject_float,
            parse_constant=reject_float,
        )
    except json.JSONDecodeError as error:
        raise ManifestError("INVALID_JSON", str(error)) from error


class ManifestLoader:
    """The ordered acceptance stages bound to one version's contract table."""

    def __init__(self, contract: Any) -> None:
        self.contract = contract

    def load_file(self, path: str | Path) -> Manifest:
        try:
            raw = Path(path).read_bytes().decode("utf-8")
        except UnicodeDecodeError as error:
            raise ManifestError("INVALID_JSON", f"invalid UTF-8: {error}") from error
        return self.load_text(raw)

    def load_text(self, raw: str) -> Manifest:
        return self.accept(parse_json(raw))

    def accept(self, value: Any) -> Manifest:
        c = self.contract
        if type(value) is not dict:
            _fail("INVALID_JSON", "manifest root must be a JSON object")
        self._check_shape(value)
        self._check_schema(value)
        _check_types(value)
        _check_ranges(value)
        self._check_fixed_values(value)
        try:
            check_derivations(value, c)
        except DerivationError as error:
            raise ManifestError(error.code, error.detail) from error
        encoded = canonical_bytes(value)
        return Manifest(
            source=json.loads(json.dumps(value)),
            canonical_length=len(encoded),
            manifest_digest=digest(c.MANIFEST_LABEL, value),
            contract=c,
        )

    def _check_shape(self, value: Any) -> None:
        c = self.contract
        root = _object(value, "manifest")
        _fields(root, TOP_FIELDS, "manifest")
        _fields(_object(root["denomination"], "denomination"),
                DENOMINATION_FIELDS, "denomination")
        _fields(_object(root["seat_schedule"], "seat_schedule"),
                SEAT_FIELDS, "seat_schedule")
        channels = _array(root["channels"], len(c.CHANNELS), "channels")
        for index, entry in enumerate(channels):
            _fields(_object(entry, f"channels[{index}]"),
                    {"id", "issuance_kind", "cap_atomic"}, f"channels[{index}]")
        base = _object(root["base_permission"], "base_permission")
        _fields(base, {"total_atomic", "legs"}, "base_permission")
        for index, leg in enumerate(_array(base["legs"], len(c.BASE_LEGS), "legs")):
            _fields(_object(leg, f"legs[{index}]"),
                    {"channel", "beneficiary_kind", "amount_atomic"}, f"legs[{index}]")
        _fields(_object(root["referral_benefit"], "referral_benefit"),
                REFERRAL_FIELDS, "referral_benefit")
        _array(root["research_placeholders"], len(c.RESEARCH_PLACEHOLDERS),
               "research_placeholders")

    def _check_schema(self, root: dict[str, Any]) -> None:
        if root["schema"] != self.contract.MANIFEST_SCHEMA:
            _fail("SCHEMA", "unsupported manifest schema")
        if root["research_only"] is not True:
            _fail("SCHEMA", "research_only must be the boolean true")

    def _check_fixed_values(self, root: dict[str, Any]) -> None:
        c = self.contract
        _compare(
            root["denomination"],
            {
                "storage_type": c.STORAGE_TYPE,
                "decimal_places": c.DECIMAL_PLACES,
                "atomic_units_per_display_unit": str(c.ATOMIC_UNITS_PER_DISPLAY_UNIT),
                "maximum_supply_display": str(c.MAXIMUM_SUPPLY_DISPLAY),
                "maximum_supply_atomic": str(c.MAXIMUM_SUPPLY_ATOMIC),
            },
            "denomination",
        )
        _compare(
            root["seat_schedule"],
            {
                "founder_seat_capacity": c.FOUNDER_SEAT_CAPACITY,
                "maximum_seats_per_person": c.MAXIMUM_SEATS_PER_PERSON,
                "issuance_cycles_per_seat": c.ISSUANCE_CYCLES_PER_SEAT,
            },
            "seat_schedule",
        )
        for index, (entry, expected) in enumerate(zip(root["channels"], c.CHANNELS)):
            _compare(
                entry,
                {"id": expected[0], "issuance_kind": expected[1],
                 "cap_atomic": str(expected[2])},
                f"channels[{index}]",
            )
        base = root["base_permission"]
        if base["total_atomic"] != str(c.BASE_PERMISSION_TOTAL):
            _fail("MANIFEST_MISMATCH", "base_permission.total_atomic differs")
        for index, (leg, expected) in enumerate(zip(base["legs"], c.BASE_LEGS)):
            _compare(
                leg,
                {"channel": expected[0], "beneficiary_kind": expected[1],
                 "amount_atomic": str(expected[2])},
                f"legs[{index}]",
            )
        _compare(
            root["referral_benefit"],
            {"channel": c.REFERRAL_CHANNEL,
             "amount_atomic": str(c.REFERRAL_AMOUNT),
             "unconditional": c.REFERRAL_UNCONDITIONAL,
             "referred_beneficiary_kind": c.REFERRED_BENEFICIARY_KIND,
             "unreferred_beneficiary_kind": c.UNREFERRED_BENEFICIARY_KIND},
            "referral_benefit",
        )
        if tuple(root["research_placeholders"]) != c.RESEARCH_PLACEHOLDERS:
            _fail("MANIFEST_MISMATCH", "research_placeholders differ")


def _fail(code: str, detail: str) -> None:
    raise ManifestError(code, detail)


def _object(value: Any, name: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail("UNKNOWN_FIELD", f"{name} must be an object")
    return value


def _fields(value: dict[str, Any], expected: set[str], name: str) -> None:
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing or unknown:
        _fail("UNKNOWN_FIELD", f"{name} missing={missing} unknown={unknown}")


def _array(value: Any, length: int, name: str) -> list[Any]:
    if type(value) is not list:
        _fail("UNKNOWN_FIELD", f"{name} must be an array")
    if len(value) != length:
        _fail("UNKNOWN_FIELD", f"{name} must have exactly {length} entries")
    return value


def _check_types(root: dict[str, Any]) -> None:
    for name, item in boolean_items(root):
        if type(item) is not bool:
            _fail("TYPE", f"{name} is not a JSON boolean")
    for name, item in monetary_items(root):
        if not is_canonical_decimal(item):
            _fail("TYPE", f"{name} is not a canonical unsigned decimal string")
    for name, item in count_items(root):
        if type(item) is not int or type(item) is bool or item < 0:
            _fail("TYPE", f"{name} is not an unsigned JSON integer")
    for name, item in text_items(root):
        if type(item) is not str:
            _fail("TYPE", f"{name} is not a string")


def _check_ranges(root: dict[str, Any]) -> None:
    for name, item in monetary_items(root):
        if int(item) > MAX_U64:
            _fail("RANGE", f"{name} exceeds u64 maximum")
    for name, item in count_items(root):
        limit = COUNT_LIMITS[name.rsplit(".", 1)[-1]]
        if item > limit:
            _fail("RANGE", f"{name} exceeds its allowed range")


def _compare(actual: dict[str, Any], expected: dict[str, Any], name: str) -> None:
    for key, value in expected.items():
        if actual[key] != value:
            _fail("MANIFEST_MISMATCH", f"{name}.{key} differs")
