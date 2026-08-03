"""Manifest field inventory used by the ordered type and range stages.

These functions enumerate every value the loader must classify, so a field
added to the manifest schema without a corresponding check cannot be silently
skipped by the type or range stage.
"""

from __future__ import annotations

from typing import Any

from .canonical import MAX_U64

DENOMINATION_FIELDS = {
    "storage_type",
    "decimal_places",
    "atomic_units_per_display_unit",
    "maximum_supply_display",
    "maximum_supply_atomic",
}
SEAT_FIELDS = {
    "founder_seat_capacity",
    "maximum_seats_per_person",
    "issuance_cycles_per_seat",
}
TOP_FIELDS = {
    "schema",
    "research_only",
    "denomination",
    "seat_schedule",
    "channels",
    "base_permission",
    "referral_permission",
    "research_placeholders",
}
MONETARY_STRINGS = (
    "atomic_units_per_display_unit",
    "maximum_supply_display",
    "maximum_supply_atomic",
)
COUNT_LIMITS = {
    "decimal_places": 32,
    "founder_seat_capacity": MAX_U64,
    "maximum_seats_per_person": MAX_U64,
    "issuance_cycles_per_seat": MAX_U64,
}


def monetary_items(root: dict[str, Any]) -> list[tuple[str, Any]]:
    items = [
        (f"denomination.{name}", root["denomination"][name])
        for name in MONETARY_STRINGS
    ]
    items += [
        (f"channels[{index}].cap_atomic", entry["cap_atomic"])
        for index, entry in enumerate(root["channels"])
    ]
    items.append(("base_permission.total_atomic", root["base_permission"]["total_atomic"]))
    items += [
        (f"legs[{index}].amount_atomic", leg["amount_atomic"])
        for index, leg in enumerate(root["base_permission"]["legs"])
    ]
    items.append(
        ("referral_permission.amount_atomic", root["referral_permission"]["amount_atomic"])
    )
    return items


def count_items(root: dict[str, Any]) -> list[tuple[str, Any]]:
    items = [("denomination.decimal_places", root["denomination"]["decimal_places"])]
    items += [
        (f"seat_schedule.{name}", root["seat_schedule"][name])
        for name in sorted(SEAT_FIELDS)
    ]
    return items


def text_items(root: dict[str, Any]) -> list[tuple[str, Any]]:
    items = [
        ("schema", root["schema"]),
        ("denomination.storage_type", root["denomination"]["storage_type"]),
    ]
    for index, entry in enumerate(root["channels"]):
        items += [
            (f"channels[{index}].id", entry["id"]),
            (f"channels[{index}].issuance_kind", entry["issuance_kind"]),
        ]
    for index, leg in enumerate(root["base_permission"]["legs"]):
        items += [
            (f"legs[{index}].channel", leg["channel"]),
            (f"legs[{index}].beneficiary_kind", leg["beneficiary_kind"]),
        ]
    referral = root["referral_permission"]
    items += [
        ("referral_permission.channel", referral["channel"]),
        ("referral_permission.beneficiary_kind", referral["beneficiary_kind"]),
    ]
    items += [
        (f"research_placeholders[{index}]", item)
        for index, item in enumerate(root["research_placeholders"])
    ]
    return items
