#!/usr/bin/env python3
"""Manifest v3 identity, the one rename, and version-separation tests."""

from __future__ import annotations

import json
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

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
MANIFEST_PATH = ROOT / "test-vectors" / "founder-economy-manifest-v3.json"
VECTORS_PATH = ROOT / "test-vectors" / "founder-economy-manifest-v3.txt"
V2_MANIFEST_PATH = ROOT / "test-vectors" / "founder-economy-manifest-v2.json"
V1_MANIFEST_PATH = ROOT / "test-vectors" / "founder-economy-manifest-v1.json"


def manifest():
    return load_manifest_file(MANIFEST_PATH)


def manifest_value() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def v2_manifest_value() -> dict:
    return json.loads(V2_MANIFEST_PATH.read_text(encoding="utf-8"))


def v1_manifest_value() -> dict:
    return json.loads(V1_MANIFEST_PATH.read_text(encoding="utf-8"))


def vectors() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in VECTORS_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, _, value = stripped.partition("=")
        values[key] = value
    return values


class ManifestIdentityTest(unittest.TestCase):
    def test_accepted_manifest_reproduces_its_canonical_identity(self) -> None:
        accepted = manifest()
        self.assertEqual(accepted.canonical_length, c.MANIFEST_CANONICAL_LENGTH)
        self.assertEqual(accepted.manifest_digest, c.MANIFEST_DIGEST)
        self.assertEqual(len(canonical_bytes(accepted.source)), 2261)

    def test_domain_label_prefix_matches_the_specification(self) -> None:
        prefix = label_prefix(c.MANIFEST_LABEL)
        self.assertEqual(len(c.MANIFEST_LABEL), 42)
        self.assertEqual(prefix[0], 0x2A)
        self.assertEqual(prefix[1:].decode("ascii"), c.MANIFEST_LABEL)

    def test_canonical_bytes_ignore_checked_in_whitespace(self) -> None:
        value = manifest_value()
        compact = json.dumps(value, separators=(",", ":"), sort_keys=False)
        indented = json.dumps(value, indent=8, sort_keys=False)
        self.assertEqual(
            load_manifest_text(compact).manifest_digest,
            load_manifest_text(indented).manifest_digest,
        )

    def test_canonical_bytes_ignore_source_field_order(self) -> None:
        """JCS sorts object properties, so a reordered source is the same bytes."""
        generator = random.Random(20260819)
        value = manifest_value()
        for _ in range(8):
            items = list(value.items())
            generator.shuffle(items)
            shuffled = json.dumps(dict(items), separators=(",", ":"))
            self.assertEqual(
                load_manifest_text(shuffled).manifest_digest, c.MANIFEST_DIGEST
            )

    def test_checked_in_manifest_carries_no_floating_point_token(self) -> None:
        """Parse the file itself, not a reserialization, with floats rejected."""

        def reject(value: str) -> float:
            raise AssertionError(f"floating-point token in the manifest: {value}")

        raw = MANIFEST_PATH.read_text(encoding="utf-8")
        json.loads(raw, parse_float=reject, parse_constant=reject)


class RenameTest(unittest.TestCase):
    """Version three's whole claim: one identifier moved and nothing else did."""

    def test_the_two_tables_agree_once_the_one_rename_is_applied(self) -> None:
        renamed = tuple(
            (c.RENAMED_CHANNEL_TO if channel == c.RENAMED_CHANNEL_FROM else channel,
             kind, cap)
            for channel, kind, cap in v2.CHANNELS
        )
        self.assertEqual(renamed, c.CHANNELS)

    def test_exactly_one_identifier_differs(self) -> None:
        differing = [
            (previous[0], current[0])
            for previous, current in zip(v2.CHANNELS, c.CHANNELS)
            if previous[0] != current[0]
        ]
        self.assertEqual(differing, [(c.RENAMED_CHANNEL_FROM, c.RENAMED_CHANNEL_TO)])

    def test_no_cap_kind_leg_or_total_moved(self) -> None:
        self.assertEqual(
            [entry[1:] for entry in c.CHANNELS], [entry[1:] for entry in v2.CHANNELS]
        )
        self.assertEqual(c.BASE_LEGS, v2.BASE_LEGS)
        self.assertEqual(c.BASE_PERMISSION_TOTAL, v2.BASE_PERMISSION_TOTAL)
        self.assertEqual(c.MAXIMUM_SUPPLY_ATOMIC, v2.MAXIMUM_SUPPLY_ATOMIC)
        self.assertEqual(c.MAXIMUM_SUPPLY_DISPLAY, v2.MAXIMUM_SUPPLY_DISPLAY)
        self.assertEqual(c.REFERRAL_AMOUNT, v2.REFERRAL_AMOUNT)
        self.assertEqual(c.FOUNDER_CHANNEL_SUBTOTAL, v2.FOUNDER_CHANNEL_SUBTOTAL)
        self.assertEqual(c.DIRECT_CHANNEL_SUBTOTAL, v2.DIRECT_CHANNEL_SUBTOTAL)

    def test_the_renamed_channel_is_at_index_nine_in_both_versions(self) -> None:
        self.assertEqual(v2.CHANNELS[9][0], c.RENAMED_CHANNEL_FROM)
        self.assertEqual(c.CHANNELS[9][0], c.RENAMED_CHANNEL_TO)
        self.assertEqual(c.CHANNELS[9][1], c.DIRECT_MINT)

    def test_the_retired_identifier_is_absent_from_the_accepted_bytes(self) -> None:
        """A rename that left the old name anywhere in the manifest is not one."""
        encoded = canonical_bytes(manifest_value())
        self.assertNotIn(c.RENAMED_CHANNEL_FROM.encode("ascii"), encoded)
        self.assertEqual(encoded.count(c.RENAMED_CHANNEL_TO.encode("ascii")), 1)

    def test_the_canonical_length_change_is_the_identifier_length_change(self) -> None:
        """The two schema strings are the same length, so nothing else may move."""
        self.assertEqual(len(c.MANIFEST_SCHEMA), len(v2.MANIFEST_SCHEMA))
        self.assertEqual(len(c.MANIFEST_LABEL), len(v2.MANIFEST_LABEL))
        self.assertEqual(
            v2.MANIFEST_CANONICAL_LENGTH - c.MANIFEST_CANONICAL_LENGTH,
            len(c.RENAMED_CHANNEL_FROM) - len(c.RENAMED_CHANNEL_TO),
        )

    def test_the_renamed_channel_still_carries_the_research_placeholder(self) -> None:
        self.assertIn(c.RENAMED_CHANNEL_TO, c.PLACEHOLDER_DIRECT_CHANNELS)
        self.assertNotIn(c.RENAMED_CHANNEL_FROM, c.PLACEHOLDER_DIRECT_CHANNELS)
        self.assertEqual(len(c.PLACEHOLDER_DIRECT_CHANNELS), 4)
        self.assertEqual(c.RESEARCH_PLACEHOLDERS, v2.RESEARCH_PLACEHOLDERS)


class VersionSeparationTest(unittest.TestCase):
    """v2 and v3 are separate accepted contracts, not one reinterpreted digest."""

    def test_v3_loader_rejects_the_v2_manifest(self) -> None:
        with self.assertRaises(ManifestError) as raised:
            accept_manifest(v2_manifest_value())
        self.assertEqual(raised.exception.code, "SCHEMA")

    def test_v2_loader_rejects_the_v3_manifest(self) -> None:
        with self.assertRaises(V2ManifestError) as raised:
            accept_v2_manifest(manifest_value())
        self.assertEqual(raised.exception.code, "SCHEMA")

    def test_v3_loader_rejects_the_v1_manifest(self) -> None:
        with self.assertRaises(ManifestError) as raised:
            accept_manifest(v1_manifest_value())
        self.assertEqual(raised.exception.code, "UNKNOWN_FIELD")

    def test_v1_loader_rejects_the_v3_manifest(self) -> None:
        with self.assertRaises(V1ManifestError) as raised:
            accept_v1_manifest(manifest_value())
        self.assertEqual(raised.exception.code, "UNKNOWN_FIELD")

    def test_the_two_versions_have_distinct_labels_and_digests(self) -> None:
        self.assertNotEqual(c.MANIFEST_LABEL, v2.MANIFEST_LABEL)
        self.assertNotEqual(c.MANIFEST_SCHEMA, v2.MANIFEST_SCHEMA)
        self.assertNotEqual(c.MANIFEST_DIGEST, v2.MANIFEST_DIGEST)
        self.assertEqual(c.SUPERSEDED_DIGEST, v2.MANIFEST_DIGEST)
        self.assertEqual(c.SUPERSEDED_SCHEMA, v2.MANIFEST_SCHEMA)

    def test_the_schema_string_alone_separates_two_same_shaped_manifests(self) -> None:
        """The shapes are identical, so the schema stage is what keeps them apart."""
        value = v2_manifest_value()
        value["schema"] = c.MANIFEST_SCHEMA
        with self.assertRaises(ManifestError) as raised:
            accept_manifest(value)
        self.assertEqual(raised.exception.code, "MANIFEST_MISMATCH")


class SupplyDerivationTest(unittest.TestCase):
    def test_channel_caps_sum_to_the_maximum_supply(self) -> None:
        founder = sum(cap for _, kind, cap in c.CHANNELS if kind != c.DIRECT_MINT)
        direct = sum(cap for _, kind, cap in c.CHANNELS if kind == c.DIRECT_MINT)
        self.assertEqual(founder, c.FOUNDER_CHANNEL_SUBTOTAL)
        self.assertEqual(direct, c.DIRECT_CHANNEL_SUBTOTAL)
        self.assertEqual(founder + direct, c.MAXIMUM_SUPPLY_ATOMIC)
        self.assertEqual(
            c.MAXIMUM_SUPPLY_DISPLAY * c.ATOMIC_UNITS_PER_DISPLAY_UNIT,
            c.MAXIMUM_SUPPLY_ATOMIC,
        )
        self.assertEqual(c.MAXIMUM_SUPPLY_DISPLAY, 56_993_950_100)

    def test_every_base_channel_cap_is_its_complete_schedule(self) -> None:
        for channel, _, amount in c.BASE_LEGS:
            self.assertEqual(
                amount * c.SEAT_CYCLE_POPULATION, c.CHANNEL_CAPS[channel]
            )
        self.assertEqual(
            c.BASE_PERMISSION_TOTAL * c.SEAT_CYCLE_POPULATION,
            c.FOUNDER_CHANNEL_SUBTOTAL,
        )

    def test_the_referral_channel_is_consumed_with_no_remainder(self) -> None:
        self.assertEqual(
            c.REFERRAL_AMOUNT * c.FOUNDER_SEAT_CAPACITY * c.ISSUANCE_CYCLES_PER_SEAT,
            c.CHANNEL_CAPS[c.REFERRAL_CHANNEL],
        )

    def test_the_renamed_channel_keeps_its_founder_directed_cap(self) -> None:
        self.assertEqual(
            c.CHANNEL_CAPS[c.RENAMED_CHANNEL_TO] // c.ATOMIC_UNITS_PER_DISPLAY_UNIT,
            12_500_100,
        )
        self.assertNotIn(c.RENAMED_CHANNEL_FROM, c.CHANNEL_CAPS)

    def test_the_atomic_maximum_stays_far_inside_u64(self) -> None:
        self.assertLess(c.MAXIMUM_SUPPLY_ATOMIC, MAX_U64)
        self.assertGreater(MAX_U64 - c.MAXIMUM_SUPPLY_ATOMIC, c.MAXIMUM_SUPPLY_ATOMIC)

    def test_nine_decimal_places_would_overflow_u64(self) -> None:
        self.assertGreater(c.MAXIMUM_SUPPLY_DISPLAY * 1_000_000_000, MAX_U64)


class DerivationStageTest(unittest.TestCase):
    """The arithmetic stage rejects a manifest the fixed table would accept."""

    def test_the_accepted_manifest_passes_the_derivation_stage_alone(self) -> None:
        check_derivations(manifest_value())

    def test_a_wrong_renamed_channel_cap_fails_the_derivation_stage(self) -> None:
        value = manifest_value()
        value["channels"][9]["cap_atomic"] = str(
            c.CHANNEL_CAPS[c.RENAMED_CHANNEL_TO] + c.ATOMIC_UNITS_PER_DISPLAY_UNIT
        )
        with self.assertRaises(DerivationError) as raised:
            check_derivations(value)
        self.assertEqual(raised.exception.code, "SUPPLY_MISMATCH")

    def test_moving_a_direct_channel_into_the_base_group_is_rejected(self) -> None:
        """The kind partition carries the Founder Node subtotal identity."""
        value = manifest_value()
        value["channels"][5]["issuance_kind"] = c.BASE_PERMISSION
        with self.assertRaises(DerivationError) as raised:
            check_derivations(value)
        self.assertEqual(raised.exception.code, "SUPPLY_MISMATCH")

    def test_an_unrepresentable_population_is_an_overflow(self) -> None:
        value = manifest_value()
        value["seat_schedule"]["founder_seat_capacity"] = MAX_U64
        value["seat_schedule"]["issuance_cycles_per_seat"] = MAX_U64
        with self.assertRaises(DerivationError) as raised:
            check_derivations(value)
        self.assertEqual(raised.exception.code, "ARITHMETIC_OVERFLOW")


class VectorAgreementTest(unittest.TestCase):
    def test_vector_file_agrees_with_the_loaded_manifest(self) -> None:
        recorded = vectors()
        accepted = manifest()
        self.assertEqual(recorded["schema"], c.MANIFEST_SCHEMA)
        self.assertEqual(recorded["manifest_domain_label"], c.MANIFEST_LABEL)
        self.assertEqual(int(recorded["manifest_domain_label_length"]), 42)
        self.assertEqual(
            int(recorded["manifest_canonical_json_length"]), accepted.canonical_length
        )
        self.assertEqual(recorded["manifest_digest"], accepted.manifest_digest)
        self.assertEqual(recorded["supersedes.digest"], c.SUPERSEDED_DIGEST)
        self.assertEqual(
            int(recorded["denomination.maximum_supply_atomic"]),
            accepted.maximum_supply_atomic,
        )
        for index, (channel_id, kind, cap) in enumerate(c.CHANNELS):
            self.assertEqual(recorded[f"channel{index}.id"], channel_id)
            self.assertEqual(recorded[f"channel{index}.kind"], kind)
            self.assertEqual(int(recorded[f"channel{index}.cap"]), cap)
        self.assertEqual(accepted.channel_caps, c.CHANNEL_CAPS)

    def test_the_rename_group_records_no_change_other_than_the_identifier(self) -> None:
        recorded = vectors()
        self.assertEqual(recorded["rename.previous_id"], c.RENAMED_CHANNEL_FROM)
        self.assertEqual(recorded["rename.current_id"], c.RENAMED_CHANNEL_TO)
        self.assertEqual(int(recorded["rename.changed_identifier_count"]), 1)
        for key in (
            "rename.changed_cap_count",
            "rename.changed_kind_count",
            "rename.changed_leg_count",
            "rename.channel_cap_change_atomic",
            "rename.maximum_supply_change_atomic",
            "rename.referral_amount_change_atomic",
            "rename.retired_id_occurrences",
            "rename.schema_length_change",
            "rename.label_length_change",
        ):
            self.assertEqual(int(recorded[key]), 0, key)

    def test_every_recorded_result_names_a_specified_code(self) -> None:
        specified = {
            "ACCEPTED",
            "INVALID_JSON",
            "UNKNOWN_FIELD",
            "SCHEMA",
            "TYPE",
            "RANGE",
            "MANIFEST_MISMATCH",
            "ARITHMETIC_OVERFLOW",
            "SUPPLY_MISMATCH",
        }
        results = {
            key: value for key, value in vectors().items() if key.endswith(".result")
        }
        self.assertGreater(len(results), 40)
        for key, value in results.items():
            self.assertIn(value, specified, key)


if __name__ == "__main__":
    unittest.main()
