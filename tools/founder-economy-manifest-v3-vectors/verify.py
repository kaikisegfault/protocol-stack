#!/usr/bin/env python3
"""Independently derive and check the founder-economy-manifest-v3 vectors.

Every recorded value is rederived from at least two sources before it is
compared: from the Founder Constitution literals in `expected.py`, from the
checked-in manifest JSON, and — for the failure codes — from a live run of the
strict loader over a mutated manifest. Restating a recorded value instead of
deriving it would make the vector file unfalsifiable.

Version three's whole claim is that one channel identifier moved and nothing
else did, so the `rename.` group is where this verifier does work version two's
did not. It accounts for the difference between the two accepted manifests in
both directions: no cap, kind, leg, or total changed, and the entire change in
canonical byte length is the identifier's own change in length.
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
from checker import Checker, read_vectors

from simulation.common.canonical import MAX_U64, canonical_bytes, label_prefix
from simulation.founder_economy.manifest import (
    ManifestError as V1ManifestError,
    accept_manifest as accept_v1_manifest,
)
from simulation.founder_economy_manifest_v3 import contract as c
from simulation.founder_economy_manifest_v3.derivations import (
    DerivationError,
    check_derivations,
)
from simulation.founder_economy_manifest_v3.manifest import (
    ManifestError,
    accept_manifest,
    load_manifest_file,
    load_manifest_text,
)
from simulation.founder_economy_v2 import contract as v2
from simulation.founder_economy_v2.manifest import (
    ManifestError as V2ManifestError,
    accept_manifest as accept_v2_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = "test-vectors/founder-economy-manifest-v3.json"
V2_MANIFEST_PATH = ROOT / "test-vectors" / "founder-economy-manifest-v2.json"
V1_MANIFEST_PATH = ROOT / "test-vectors" / "founder-economy-manifest-v1.json"

V2_TABLE = "the retained v2 contract table"


def check_identity_vectors(check: Checker, manifest, source: dict[str, Any]) -> None:
    check.agree("schema", e.SCHEMA, source["schema"])
    check.equal("manifest_file", MANIFEST_PATH)
    check.agree("manifest_domain_label", e.LABEL, c.MANIFEST_LABEL, "the v3 contract")
    check.equal("manifest_domain_label_length", len(label_prefix(c.MANIFEST_LABEL)) - 1)
    check.equal("manifest_canonical_json_length", manifest.canonical_length)
    check.equal("manifest_digest", manifest.manifest_digest)
    check.equal("research_only", json.dumps(source["research_only"]))

    # Every superseded value is read from the retained v2 contract table and
    # required to agree with this tool's hand-converted literal, so an edit to
    # the v2 artifacts these vectors describe as unchanged fails here.
    check.agree("supersedes.schema", e.SUPERSEDED_SCHEMA, v2.MANIFEST_SCHEMA, V2_TABLE)
    check.agree("supersedes.label", e.SUPERSEDED_LABEL, v2.MANIFEST_LABEL, V2_TABLE)
    check.equal("supersedes.digest", v2.MANIFEST_DIGEST)
    check.equal("supersedes.canonical_json_length", v2.MANIFEST_CANONICAL_LENGTH)
    check.agree(
        "supersedes.maximum_supply_display",
        e.SUPERSEDED_MAXIMUM_SUPPLY_DISPLAY,
        v2.MAXIMUM_SUPPLY_DISPLAY,
        V2_TABLE,
    )
    check.agree(
        "supersedes.channel9_id",
        e.RENAMED_CHANNEL_FROM,
        v2.CHANNELS[e.RENAMED_CHANNEL_INDEX][0],
        V2_TABLE,
    )


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
    check.agree(
        "referral_benefit.referred_beneficiary_kind",
        e.REFERRED_BENEFICIARY_KIND,
        referral["referred_beneficiary_kind"],
    )
    check.agree(
        "referral_benefit.unreferred_beneficiary_kind",
        e.UNREFERRED_BENEFICIARY_KIND,
        referral["unreferred_beneficiary_kind"],
    )
    check.equal("referral_benefit.operator_leg_numerator", e.REFERRAL_OPERATOR_NUMERATOR)
    check.equal(
        "referral_benefit.operator_leg_denominator", e.REFERRAL_OPERATOR_DENOMINATOR
    )


def check_rename_vectors(check: Checker, manifest, encoded: bytes) -> None:
    """Account for the whole difference between the two accepted manifests.

    Version three's claim is not that its own arithmetic holds — version two's
    did too — but that exactly one identifier moved. That is checked in both
    directions here: nothing but the identifier differs, and the identifier
    does differ, so a version three that silently carried version two's table
    would fail as loudly as one that moved a cap.
    """
    check.agree(
        "rename.previous_id",
        e.RENAMED_CHANNEL_FROM,
        v2.CHANNELS[e.RENAMED_CHANNEL_INDEX][0],
        V2_TABLE,
    )
    check.agree(
        "rename.current_id",
        e.RENAMED_CHANNEL_TO,
        c.CHANNELS[e.RENAMED_CHANNEL_INDEX][0],
        "the v3 contract",
    )
    check.equal("rename.channel_index", e.RENAMED_CHANNEL_INDEX)

    previous = {channel: (kind, cap) for channel, kind, cap in v2.CHANNELS}
    current = {channel: (kind, cap) for channel, kind, cap in c.CHANNELS}
    mapped = {e.renamed(channel): value for channel, value in previous.items()}

    check.equal(
        "rename.changed_identifier_count",
        sum(1 for index, entry in enumerate(v2.CHANNELS)
            if entry[0] != c.CHANNELS[index][0]),
    )
    check.equal(
        "rename.changed_cap_count",
        sum(1 for channel, (_, cap) in current.items() if mapped[channel][1] != cap),
    )
    check.equal(
        "rename.changed_kind_count",
        sum(1 for channel, (kind, _) in current.items() if mapped[channel][0] != kind),
    )
    check.equal(
        "rename.channel_cap_change_atomic",
        sum(abs(mapped[channel][1] - cap) for channel, (_, cap) in current.items()),
    )
    check.equal(
        "rename.changed_leg_count",
        sum(1 for index, leg in enumerate(c.BASE_LEGS) if leg != v2.BASE_LEGS[index]),
    )
    check.equal(
        "rename.maximum_supply_change_atomic",
        abs(c.MAXIMUM_SUPPLY_ATOMIC - v2.MAXIMUM_SUPPLY_ATOMIC),
    )
    check.equal(
        "rename.referral_amount_change_atomic",
        abs(c.REFERRAL_AMOUNT - v2.REFERRAL_AMOUNT),
    )

    # The identity that makes "and nothing else" checkable in bytes rather than
    # in a table read: the two schema strings are the same length, so the whole
    # canonical-length difference must be the identifier's own.
    check.equal("rename.previous_id_length", len(e.RENAMED_CHANNEL_FROM))
    check.equal("rename.current_id_length", len(e.RENAMED_CHANNEL_TO))
    check.equal(
        "rename.schema_length_change",
        abs(len(e.SCHEMA) - len(e.SUPERSEDED_SCHEMA)),
    )
    check.equal(
        "rename.label_length_change",
        abs(len(e.LABEL) - len(e.SUPERSEDED_LABEL)),
    )
    check.agree(
        "rename.canonical_length_shrinkage",
        len(e.RENAMED_CHANNEL_FROM) - len(e.RENAMED_CHANNEL_TO),
        v2.MANIFEST_CANONICAL_LENGTH - manifest.canonical_length,
        "the two accepted canonical lengths",
    )
    check.equal(
        "rename.retired_id_occurrences",
        encoded.count(e.RENAMED_CHANNEL_FROM.encode("ascii")),
    )
    check.equal(
        "rename.current_id_occurrences",
        encoded.count(e.RENAMED_CHANNEL_TO.encode("ascii")),
    )


def check_separation_vectors(check: Checker, source: dict[str, Any]) -> None:
    """Neither loader accepts the other version's manifest."""
    v2_source = json.loads(V2_MANIFEST_PATH.read_text(encoding="utf-8"))
    v1_source = json.loads(V1_MANIFEST_PATH.read_text(encoding="utf-8"))

    try:
        accept_v2_manifest(copy.deepcopy(source))
        code = "ACCEPTED"
    except V2ManifestError as error:
        code = error.code
    check.equal("separation.v2_loader_on_v3_manifest.result", code)

    try:
        accept_manifest(copy.deepcopy(v2_source))
        code = "ACCEPTED"
    except ManifestError as error:
        code = error.code
    check.equal("separation.v3_loader_on_v2_manifest.result", code)

    try:
        accept_manifest(copy.deepcopy(v1_source))
        code = "ACCEPTED"
    except ManifestError as error:
        code = error.code
    check.equal("separation.v3_loader_on_v1_manifest.result", code)

    try:
        accept_v1_manifest(copy.deepcopy(source))
        code = "ACCEPTED"
    except V1ManifestError as error:
        code = error.code
    check.equal("separation.v1_loader_on_v3_manifest.result", code)

    check.equal("separation.labels_differ", int(c.MANIFEST_LABEL != v2.MANIFEST_LABEL))
    check.equal("separation.schemas_differ", int(c.MANIFEST_SCHEMA != v2.MANIFEST_SCHEMA))
    check.equal("separation.digests_differ", int(c.MANIFEST_DIGEST != v2.MANIFEST_DIGEST))


def check_research_input_vectors(check: Checker, source: dict[str, Any]) -> None:
    placeholders = source["research_placeholders"]
    check.agree("research_placeholders.count", len(e.RESEARCH_PLACEHOLDERS),
                len(placeholders))
    for index, name in enumerate(placeholders):
        check.agree(f"research_placeholders{index}", e.RESEARCH_PLACEHOLDERS[index], name)
    covered = e.DIRECT_MINT_CHANNELS_DISPLAY.keys() - {e.REFERRAL_CHANNEL}
    check.agree(
        "research_placeholders.direct_channels_covered",
        len(covered),
        len(c.PLACEHOLDER_DIRECT_CHANNELS),
        "the v3 contract",
    )
    check.equal(
        "research_placeholders.referral_channel_covered",
        1 if e.REFERRAL_CHANNEL in c.PLACEHOLDER_DIRECT_CHANNELS else 0,
    )
    check.equal(
        "research_placeholders.renamed_channel_covered",
        1 if e.RENAMED_CHANNEL_TO in c.PLACEHOLDER_DIRECT_CHANNELS else 0,
    )
    check.equal(
        "research_placeholders.retired_since_v2",
        len(v2.RESEARCH_PLACEHOLDERS) - len(placeholders),
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
    "wrong_schema": lambda root: root.update({"schema": "protocol-stack/other/v3"}),
    "v2_schema": lambda root: root.update({"schema": e.SUPERSEDED_SCHEMA}),
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
    # The rename's own negative: the retired identifier is not a synonym.
    "retired_channel_id": lambda root: root["channels"][
        e.RENAMED_CHANNEL_INDEX
    ].update({"id": e.RENAMED_CHANNEL_FROM}),
    "renamed_channel_cap": lambda root: root["channels"][
        e.RENAMED_CHANNEL_INDEX
    ].update(
        {"cap_atomic": _decrement(
            root["channels"][e.RENAMED_CHANNEL_INDEX]["cap_atomic"]
        )}
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
    "halved_referral_amount": lambda root: root["referral_benefit"].update(
        {"amount_atomic": str(e.REFERRAL_AMOUNT // 2)}
    ),
    "changed_maximum_supply": lambda root: root["denomination"].update(
        {
            "maximum_supply_display": "55743940100",
            "maximum_supply_atomic": str(55_743_940_100 * e.D),
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
    "renamed_cap_minus_one": lambda root: root["channels"][
        e.RENAMED_CHANNEL_INDEX
    ].update(
        {"cap_atomic": _decrement(
            root["channels"][e.RENAMED_CHANNEL_INDEX]["cap_atomic"]
        )}
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
        LOADER_NEGATIVES["retired_channel_id"],
    ],
    "mismatch_before_supply": [
        LOADER_NEGATIVES["retired_channel_id"],
        LOADER_NEGATIVES["changed_maximum_supply"],
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
        default=ROOT / "test-vectors" / "founder-economy-manifest-v3.txt",
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
    encoded = canonical_bytes(source)

    check = Checker(read_vectors(arguments.vectors))
    check_identity_vectors(check, manifest, source)
    check_denomination_vectors(check, source)
    check_seat_vectors(check, source)
    check_channel_vectors(check, source)
    check_schedule_vectors(check, source)
    check_referral_vectors(check, source)
    check_rename_vectors(check, manifest, encoded)
    check_separation_vectors(check, source)
    check_research_input_vectors(check, source)
    check_negative_vectors(check, source)
    check.require_full_coverage()

    for failure in check.failures:
        sys.stderr.write(f"vector mismatch: {failure}\n")
    if check.failures:
        return 1

    sys.stdout.write(
        f"derived and matched {check.checked} founder-economy-manifest-v3 vectors\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
