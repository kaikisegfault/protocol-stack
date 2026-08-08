#!/usr/bin/env python3
"""Independently derive and check the founder-economy-manifest-v2 vectors.

Every recorded value is rederived three ways before it is compared: from the
Founder Constitution literals in `expected.py`, from the checked-in manifest
JSON, and — for the failure codes — from a live run of the strict loader over a
mutated manifest. Restating a recorded value instead of deriving it would make
the vector file unfalsifiable.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Callable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import expected as e

from simulation.common.canonical import MAX_U64, label_prefix
from simulation.founder_economy_v2 import contract as c
from simulation.founder_economy_v2.derivations import DerivationError, check_derivations
from simulation.founder_economy_v2.manifest import (
    ManifestError,
    accept_manifest,
    load_manifest_file,
    load_manifest_text,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = "test-vectors/founder-economy-manifest-v2.json"


class Checker:
    def __init__(self, recorded: dict[str, str]) -> None:
        self.recorded = recorded
        self.failures: list[str] = []
        self.seen: set[str] = set()

    @property
    def checked(self) -> int:
        return len(self.seen)

    def equal(self, key: str, derived: object) -> None:
        if key not in self.recorded:
            self.failures.append(f"{key}: not recorded in the vector file")
            return
        self.seen.add(key)
        expected_value = self.recorded[key]
        if str(derived) != expected_value:
            self.failures.append(
                f"{key}: derived {derived!r}, recorded {expected_value!r}"
            )

    def agree(self, key: str, closed_form: object, from_manifest: object) -> None:
        """Record a value only when the closed form and the manifest agree."""
        if str(closed_form) != str(from_manifest):
            self.failures.append(
                f"{key}: constitution derives {closed_form!r} but the manifest "
                f"carries {from_manifest!r}"
            )
            return
        self.equal(key, closed_form)

    def require_full_coverage(self) -> None:
        """Fail closed when a recorded vector was never derived."""
        for key in sorted(set(self.recorded) - self.seen):
            self.failures.append(f"{key}: recorded but never derived")


def read_vectors(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition("=")
        if not separator or key in values:
            raise ValueError(f"{path}:{number}: malformed or duplicate vector line")
        values[key] = value
    return values


def check_identity_vectors(check: Checker, manifest, source: dict[str, Any]) -> None:
    check.equal("schema", source["schema"])
    check.equal("manifest_file", MANIFEST_PATH)
    check.equal("manifest_domain_label", c.MANIFEST_LABEL)
    check.equal("manifest_domain_label_length", len(label_prefix(c.MANIFEST_LABEL)) - 1)
    check.equal("manifest_canonical_json_length", manifest.canonical_length)
    check.equal("manifest_digest", manifest.manifest_digest)
    check.equal("research_only", json.dumps(source["research_only"]))

    check.equal("supersedes.schema", c.SUPERSEDED_SCHEMA)
    check.equal("supersedes.digest", c.SUPERSEDED_DIGEST)
    check.equal(
        "supersedes.maximum_supply_display", e.SUPERSEDED_MAXIMUM_SUPPLY_DISPLAY
    )
    check.equal("supersedes.referral_amount", e.SUPERSEDED_REFERRAL_AMOUNT)
    check.equal(
        "supersedes.referral_channel_cap",
        e.SUPERSEDED_REFERRAL_CHANNEL_DISPLAY * e.D,
    )
    check.equal("supersedes.referral_issuance_kind", "referral_permission")


def check_denomination_vectors(check: Checker, source: dict[str, Any]) -> None:
    denomination = source["denomination"]
    check.equal("u64_max", MAX_U64)
    check.agree("denomination.decimal_places", e.DECIMAL_PLACES,
                denomination["decimal_places"])
    check.agree("denomination.atomic_units_per_display_unit", e.D,
                denomination["atomic_units_per_display_unit"])
    check.agree("denomination.maximum_supply_display", e.MAXIMUM_SUPPLY_DISPLAY,
                denomination["maximum_supply_display"])
    check.agree("denomination.maximum_supply_atomic", e.MAXIMUM_SUPPLY_ATOMIC,
                denomination["maximum_supply_atomic"])
    check.equal("denomination.u64_headroom", MAX_U64 - e.MAXIMUM_SUPPLY_ATOMIC)
    check.equal(
        "denomination.maximum_decimal_multiplier", MAX_U64 // e.MAXIMUM_SUPPLY_DISPLAY
    )
    nine_decimal = e.MAXIMUM_SUPPLY_DISPLAY * 1_000_000_000
    check.equal("denomination.nine_decimal_atomic", nine_decimal)
    check.equal(
        "denomination.nine_decimal.result",
        "ARITHMETIC_OVERFLOW" if nine_decimal > MAX_U64 else "OK",
    )


def check_seat_vectors(check: Checker, source: dict[str, Any]) -> None:
    seats = source["seat_schedule"]
    check.agree("seat_schedule.founder_seat_capacity", e.FOUNDER_SEAT_CAPACITY,
                seats["founder_seat_capacity"])
    check.agree("seat_schedule.maximum_seats_per_person", e.MAXIMUM_SEATS_PER_PERSON,
                seats["maximum_seats_per_person"])
    check.agree("seat_schedule.issuance_cycles_per_seat", e.ISSUANCE_CYCLES_PER_SEAT,
                seats["issuance_cycles_per_seat"])
    population = e.SEAT_CYCLE_POPULATION
    check.equal("seat_schedule.seat_cycle_population", population)
    check.equal("seat_schedule.maximum_base_permission_count", population)
    check.equal("seat_schedule.maximum_referral_accrual_count", population)


def check_channel_vectors(check: Checker, source: dict[str, Any]) -> None:
    channels = source["channels"]
    check.agree("channels.count", len(e.CHANNEL_ORDER), len(channels))
    founder = 0
    direct = 0
    base_kinds = 0
    direct_kinds = 0
    for index, channel_id in enumerate(e.CHANNEL_ORDER):
        entry = channels[index]
        kind = e.CHANNEL_KINDS[channel_id]
        cap = e.CHANNEL_CAPS[channel_id]
        check.agree(f"channel{index}.id", channel_id, entry["id"])
        check.agree(f"channel{index}.kind", kind, entry["issuance_kind"])
        check.agree(f"channel{index}.cap", cap, entry["cap_atomic"])
        if kind == e.DIRECT_MINT_KIND:
            direct += cap
            direct_kinds += 1
        else:
            founder += cap
            base_kinds += 1
    check.equal("channels.base_permission_count", base_kinds)
    check.equal("channels.direct_mint_count", direct_kinds)
    check.agree("channels.founder_subtotal", founder, e.FOUNDER_NODE_SUBTOTAL)
    check.agree("channels.direct_subtotal", direct, e.DIRECT_MINT_SUBTOTAL)
    check.agree("channels.total", founder + direct, e.MAXIMUM_SUPPLY_ATOMIC)
    check.equal("channels.founder_subtotal_display", founder // e.D)
    check.equal("channels.direct_subtotal_display", direct // e.D)
    check.equal("channels.total_display", (founder + direct) // e.D)


def check_schedule_vectors(check: Checker, source: dict[str, Any]) -> None:
    legs = {leg["channel"]: leg for leg in source["base_permission"]["legs"]}
    base_total = 0
    per_seat_total = 0
    full_total = 0
    for channel_id, amount in e.BASE_LEGS.items():
        check.agree(f"base_permission.{channel_id}", amount,
                    legs[channel_id]["amount_atomic"])
        check.equal(f"per_seat_731.{channel_id}", e.per_seat_schedule(amount))
        check.equal(f"full_schedule.{channel_id}", e.full_schedule(amount))
        base_total += amount
        per_seat_total += e.per_seat_schedule(amount)
        full_total += e.full_schedule(amount)
    check.agree("base_permission.total", base_total,
                source["base_permission"]["total_atomic"])
    check.equal("per_seat_731.base_total", per_seat_total)
    check.equal("full_schedule.base_total", full_total)
    check.equal(
        "full_schedule.founder_subtotal_minus_base_total",
        e.FOUNDER_NODE_SUBTOTAL - full_total,
    )

    referral = e.REFERRAL_AMOUNT
    check.equal("per_seat_731.referral", e.per_seat_schedule(referral))
    check.equal("full_schedule.referral", e.full_schedule(referral))
    check.equal(
        "full_schedule.referral_channel_remainder",
        e.CHANNEL_CAPS[e.REFERRAL_CHANNEL] - e.full_schedule(referral),
    )


def check_referral_vectors(check: Checker, source: dict[str, Any]) -> None:
    referral = source["referral_benefit"]
    check.agree("referral_benefit.channel", e.REFERRAL_CHANNEL, referral["channel"])
    check.equal(
        "referral_benefit.issuance_kind", e.CHANNEL_KINDS[e.REFERRAL_CHANNEL]
    )
    check.agree("referral_benefit.amount", e.REFERRAL_AMOUNT,
                referral["amount_atomic"])
    check.equal("referral_benefit.unconditional", json.dumps(referral["unconditional"]))
    check.equal(
        "referral_benefit.referred_beneficiary_kind", referral["referred_beneficiary_kind"]
    )
    check.equal(
        "referral_benefit.unreferred_beneficiary_kind",
        referral["unreferred_beneficiary_kind"],
    )
    check.equal("referral_benefit.operator_leg_numerator", e.REFERRAL_OPERATOR_NUMERATOR)
    check.equal(
        "referral_benefit.operator_leg_denominator", e.REFERRAL_OPERATOR_DENOMINATOR
    )
    multiple, remainder = divmod(e.REFERRAL_AMOUNT, e.SUPERSEDED_REFERRAL_AMOUNT)
    check.equal("referral_benefit.increase_multiple", multiple)
    check.equal("referral_benefit.increase_remainder", remainder)


def check_supply_revision_vectors(check: Checker) -> None:
    previous = e.SUPERSEDED_MAXIMUM_SUPPLY_DISPLAY
    current = e.MAXIMUM_SUPPLY_DISPLAY
    increase = current - previous
    referral_increase = (
        e.DIRECT_MINT_CHANNELS_DISPLAY[e.REFERRAL_CHANNEL]
        - e.SUPERSEDED_REFERRAL_CHANNEL_DISPLAY
    )
    current_caps = {
        **e.FOUNDER_NODE_CHANNELS_DISPLAY,
        **e.DIRECT_MINT_CHANNELS_DISPLAY,
    }
    other_change = sum(
        abs(cap - e.SUPERSEDED_CHANNELS_DISPLAY[channel])
        for channel, cap in current_caps.items()
        if channel != e.REFERRAL_CHANNEL
    )
    check.equal("supply_revision.previous_display", previous)
    check.equal("supply_revision.current_display", current)
    check.equal("supply_revision.increase_display", increase)
    check.equal("supply_revision.referral_channel_increase_display", referral_increase)
    check.equal("supply_revision.unexplained_increase_display", increase - referral_increase)
    check.equal("supply_revision.other_channel_change_display", other_change)
    check.equal(
        "supply_revision.previous_channel_total_display",
        sum(e.SUPERSEDED_CHANNELS_DISPLAY.values()),
    )


def check_research_input_vectors(check: Checker, source: dict[str, Any]) -> None:
    placeholders = source["research_placeholders"]
    check.equal("research_placeholders.count", len(placeholders))
    for index, name in enumerate(placeholders):
        check.equal(f"research_placeholders{index}", name)
    covered = e.DIRECT_MINT_CHANNELS_DISPLAY.keys() - {e.REFERRAL_CHANNEL}
    check.equal("research_placeholders.direct_channels_covered", len(covered))
    check.equal(
        "research_placeholders.referral_channel_covered",
        1 if e.REFERRAL_CHANNEL in c.PLACEHOLDER_DIRECT_CHANNELS else 0,
    )
    check.equal(
        "research_placeholders.retired_since_v1",
        4 - len(placeholders),
    )


Mutation = Callable[[dict[str, Any]], None]


def _swap_channels(root: dict[str, Any]) -> None:
    root["channels"][0], root["channels"][1] = (
        root["channels"][1],
        root["channels"][0],
    )


def _decrement(value: str) -> str:
    return str(int(value) - 1)


TEXT_NEGATIVES: dict[str, str] = {
    "truncated_json": '{"schema":',
    "root_not_object": "[]",
    "duplicate_field": '{"schema": "a", "schema": "b"}',
    "float_token": '{"schema": 1.5}',
}

LOADER_NEGATIVES: dict[str, Mutation] = {
    "unknown_field": lambda root: root.update({"extra": "x"}),
    "missing_field": lambda root: root.pop("research_placeholders"),
    "wrong_channel_count": lambda root: root["channels"].pop(),
    "wrong_leg_count": lambda root: root["base_permission"]["legs"].pop(),
    "extra_referral_field": lambda root: root["referral_benefit"].update({"x": "y"}),
    "extra_placeholder": lambda root: root["research_placeholders"].append("x"),
    "wrong_schema": lambda root: root.update({"schema": "protocol-stack/other/v2"}),
    "v1_schema": lambda root: root.update({"schema": c.SUPERSEDED_SCHEMA}),
    "research_only_false": lambda root: root.update({"research_only": False}),
    "monetary_json_number": lambda root: root["denomination"].update(
        {"maximum_supply_atomic": 5_699_395_010_000_000_000}
    ),
    "leading_zero_amount": lambda root: root["referral_benefit"].update(
        {"amount_atomic": "03420000000"}
    ),
    "negative_amount": lambda root: root["referral_benefit"].update(
        {"amount_atomic": "-3420000000"}
    ),
    "unconditional_not_boolean": lambda root: root["referral_benefit"].update(
        {"unconditional": "true"}
    ),
    "u64_plus_one": lambda root: root["channels"][0].update(
        {"cap_atomic": str(MAX_U64 + 1)}
    ),
    "decimal_places_above_limit": lambda root: root["denomination"].update(
        {"decimal_places": 33}
    ),
    "changed_channel_order": _swap_channels,
    "changed_channel_cap": lambda root: root["channels"][0].update(
        {"cap_atomic": _decrement(root["channels"][0]["cap_atomic"])}
    ),
    "referral_kind_base_permission": lambda root: root["channels"][7].update(
        {"issuance_kind": c.BASE_PERMISSION}
    ),
    "direct_channel_marked_base": lambda root: root["channels"][5].update(
        {"issuance_kind": c.BASE_PERMISSION}
    ),
    "referral_conditional": lambda root: root["referral_benefit"].update(
        {"unconditional": False}
    ),
    "v1_referral_amount": lambda root: root["referral_benefit"].update(
        {"amount_atomic": str(e.SUPERSEDED_REFERRAL_AMOUNT)}
    ),
    "v1_maximum_supply": lambda root: root["denomination"].update(
        {
            "maximum_supply_display": str(e.SUPERSEDED_MAXIMUM_SUPPLY_DISPLAY),
            "maximum_supply_atomic": str(e.SUPERSEDED_MAXIMUM_SUPPLY_DISPLAY * e.D),
        }
    ),
    "retired_placeholder": lambda root: root["research_placeholders"].__setitem__(
        0, "activity_eligibility_result"
    ),
    "unreferred_pool_removed": lambda root: root["referral_benefit"].update(
        {"unreferred_beneficiary_kind": "recorded_referrer"}
    ),
}

DERIVATION_NEGATIVES: dict[str, Mutation] = {
    "base_leg_sum_minus_one": lambda root: root["base_permission"]["legs"][0].update(
        {"amount_atomic": _decrement(
            root["base_permission"]["legs"][0]["amount_atomic"]
        )}
    ),
    "operator_cap_minus_one": lambda root: root["channels"][0].update(
        {"cap_atomic": _decrement(root["channels"][0]["cap_atomic"])}
    ),
    "referral_cap_minus_one": lambda root: root["channels"][7].update(
        {"cap_atomic": _decrement(root["channels"][7]["cap_atomic"])}
    ),
    "direct_cap_minus_one": lambda root: root["channels"][5].update(
        {"cap_atomic": _decrement(root["channels"][5]["cap_atomic"])}
    ),
    "maximum_supply_atomic_minus_one": lambda root: root["denomination"].update(
        {"maximum_supply_atomic": _decrement(
            root["denomination"]["maximum_supply_atomic"]
        )}
    ),
    "direct_channel_marked_base": lambda root: root["channels"][5].update(
        {"issuance_kind": c.BASE_PERMISSION}
    ),
    "nine_decimal_maximum": lambda root: root["denomination"].update(
        {"atomic_units_per_display_unit": "1000000000"}
    ),
    "population_overflow": lambda root: root["seat_schedule"].update(
        {"founder_seat_capacity": MAX_U64, "issuance_cycles_per_seat": MAX_U64}
    ),
}

ORDER_NEGATIVES: dict[str, list[Mutation]] = {
    "unknown_before_schema": [
        LOADER_NEGATIVES["unknown_field"],
        LOADER_NEGATIVES["wrong_schema"],
    ],
    "schema_before_type": [
        LOADER_NEGATIVES["wrong_schema"],
        LOADER_NEGATIVES["monetary_json_number"],
    ],
    "type_before_range": [
        LOADER_NEGATIVES["monetary_json_number"],
        LOADER_NEGATIVES["u64_plus_one"],
    ],
    "range_before_mismatch": [
        LOADER_NEGATIVES["decimal_places_above_limit"],
        LOADER_NEGATIVES["changed_channel_cap"],
    ],
    "mismatch_before_supply": [
        LOADER_NEGATIVES["changed_channel_cap"],
        LOADER_NEGATIVES["v1_maximum_supply"],
    ],
}


def _loader_code(source: dict[str, Any], mutations: list[Mutation]) -> str:
    root = copy.deepcopy(source)
    for mutate in mutations:
        mutate(root)
    try:
        accept_manifest(root)
    except ManifestError as error:
        return error.code
    return "ACCEPTED"


def check_negative_vectors(check: Checker, source: dict[str, Any]) -> None:
    """Execute every recorded rejection rather than naming it.

    The loader stages run in a fixed order, so a mutation that would trip two
    stages proves nothing about the later one. Each mutation below is therefore
    minimal, and the `order.` group deliberately combines two defects to prove
    which stage reports first.
    """
    for name, raw in TEXT_NEGATIVES.items():
        try:
            load_manifest_text(raw)
            code = "ACCEPTED"
        except ManifestError as error:
            code = error.code
        check.equal(f"negative.{name}.result", code)

    for name, mutation in LOADER_NEGATIVES.items():
        check.equal(f"negative.{name}.result", _loader_code(source, [mutation]))

    for name, mutations in ORDER_NEGATIVES.items():
        check.equal(f"order.{name}.result", _loader_code(source, mutations))

    for name, mutation in DERIVATION_NEGATIVES.items():
        root = copy.deepcopy(source)
        mutation(root)
        try:
            check_derivations(root)
            code = "ACCEPTED"
        except DerivationError as error:
            code = error.code
        check.equal(f"negative.derivation.{name}.result", code)

    # A positive control: the same entry point that produced every rejection
    # above accepts the unmutated manifest, so the codes are evidence about the
    # mutations rather than about a loader that rejects everything.
    check.equal("positive.accepted_manifest.result", _loader_code(source, []))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--vectors",
        type=Path,
        default=ROOT / "test-vectors" / "founder-economy-manifest-v2.txt",
    )
    arguments = parser.parse_args()

    inconsistencies = e.check_constitution_is_self_consistent()
    for detail in inconsistencies:
        sys.stderr.write(f"constitution inconsistency: {detail}\n")
    if inconsistencies:
        return 1

    try:
        manifest = load_manifest_file(ROOT / MANIFEST_PATH)
    except ManifestError as error:
        sys.stderr.write(f"manifest rejected: {error.code}: {error.detail}\n")
        return 1
    source = manifest.source

    check = Checker(read_vectors(arguments.vectors))
    check_identity_vectors(check, manifest, source)
    check_denomination_vectors(check, source)
    check_seat_vectors(check, source)
    check_channel_vectors(check, source)
    check_schedule_vectors(check, source)
    check_referral_vectors(check, source)
    check_supply_revision_vectors(check)
    check_research_input_vectors(check, source)
    check_negative_vectors(check, source)
    check.require_full_coverage()

    for failure in check.failures:
        sys.stderr.write(f"vector mismatch: {failure}\n")
    if check.failures:
        return 1

    sys.stdout.write(
        f"derived and matched {check.checked} founder-economy-manifest-v2 vectors\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
