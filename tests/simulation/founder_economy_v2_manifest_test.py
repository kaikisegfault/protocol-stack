#!/usr/bin/env python3
"""Manifest v2 identity, derived supply, and version-separation tests."""

from __future__ import annotations

import json
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import MAX_U64, canonical_bytes, label_prefix
from simulation.founder_economy import contract as v1
from simulation.founder_economy.manifest import (
    ManifestError as V1ManifestError,
    accept_manifest as accept_v1_manifest,
)
from simulation.founder_economy_v2 import contract as c
from simulation.founder_economy_v2.derivations import DerivationError, check_derivations
from simulation.founder_economy_v2.manifest import (
    ManifestError,
    accept_manifest,
    load_manifest_text,
)
from tests.simulation.founder_economy_v2_common import (
    MANIFEST_PATH,
    manifest,
    manifest_value,
    v1_manifest_value,
    vectors,
)


class ManifestIdentityTest(unittest.TestCase):
    def test_accepted_manifest_reproduces_its_canonical_identity(self) -> None:
        accepted = manifest()
        self.assertEqual(accepted.canonical_length, c.MANIFEST_CANONICAL_LENGTH)
        self.assertEqual(accepted.manifest_digest, c.MANIFEST_DIGEST)
        self.assertEqual(len(canonical_bytes(accepted.source)), 2267)

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
        generator = random.Random(20260808)
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


class VersionSeparationTest(unittest.TestCase):
    """v1 and v2 are separate accepted contracts, not one reinterpreted digest."""

    def test_v2_loader_rejects_the_v1_manifest(self) -> None:
        with self.assertRaises(ManifestError) as raised:
            accept_manifest(v1_manifest_value())
        self.assertEqual(raised.exception.code, "UNKNOWN_FIELD")

    def test_v1_loader_rejects_the_v2_manifest(self) -> None:
        with self.assertRaises(V1ManifestError) as raised:
            accept_v1_manifest(manifest_value())
        self.assertEqual(raised.exception.code, "UNKNOWN_FIELD")

    def test_the_two_versions_have_distinct_labels_and_digests(self) -> None:
        self.assertNotEqual(c.MANIFEST_LABEL, v1.MANIFEST_LABEL)
        self.assertNotEqual(c.MANIFEST_SCHEMA, v1.MANIFEST_SCHEMA)
        self.assertNotEqual(c.MANIFEST_DIGEST, v1.MANIFEST_DIGEST)
        self.assertEqual(c.SUPERSEDED_DIGEST, v1.MANIFEST_DIGEST)
        self.assertEqual(c.SUPERSEDED_SCHEMA, v1.MANIFEST_SCHEMA)

    def test_the_v1_evidence_values_are_recorded_unchanged(self) -> None:
        self.assertEqual(
            c.SUPERSEDED_MAXIMUM_SUPPLY_DISPLAY, v1.MAXIMUM_SUPPLY_DISPLAY
        )
        self.assertEqual(c.SUPERSEDED_REFERRAL_AMOUNT, v1.REFERRAL_AMOUNT)


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
        """Every seat contributes to exactly one of the two destinations."""
        self.assertEqual(
            c.REFERRAL_AMOUNT * c.FOUNDER_SEAT_CAPACITY * c.ISSUANCE_CYCLES_PER_SEAT,
            c.CHANNEL_CAPS[c.REFERRAL_CHANNEL],
        )
        self.assertEqual(
            c.CHANNEL_CAPS[c.REFERRAL_CHANNEL] // c.ATOMIC_UNITS_PER_DISPLAY_UNIT,
            2_500_020_000,
        )

    def test_the_referral_benefit_is_one_tenth_of_the_operator_leg(self) -> None:
        self.assertEqual(
            c.REFERRAL_AMOUNT * c.REFERRAL_OPERATOR_DENOMINATOR,
            c.FOUNDER_OPERATOR_LEG * c.REFERRAL_OPERATOR_NUMERATOR,
        )
        self.assertEqual(c.REFERRAL_AMOUNT, 2 * c.SUPERSEDED_REFERRAL_AMOUNT)

    def test_the_maximum_rose_only_by_the_referral_channel_increase(self) -> None:
        increase = c.MAXIMUM_SUPPLY_DISPLAY - c.SUPERSEDED_MAXIMUM_SUPPLY_DISPLAY
        referral_increase = (
            c.CHANNEL_CAPS[c.REFERRAL_CHANNEL] // c.ATOMIC_UNITS_PER_DISPLAY_UNIT
            - v1.CHANNEL_CAPS[c.REFERRAL_CHANNEL] // c.ATOMIC_UNITS_PER_DISPLAY_UNIT
        )
        self.assertEqual(increase, referral_increase)
        for channel, cap in c.CHANNEL_CAPS.items():
            if channel != c.REFERRAL_CHANNEL:
                self.assertEqual(cap, v1.CHANNEL_CAPS[channel])

    def test_the_atomic_maximum_stays_far_inside_u64(self) -> None:
        self.assertLess(c.MAXIMUM_SUPPLY_ATOMIC, MAX_U64)
        self.assertGreater(MAX_U64 - c.MAXIMUM_SUPPLY_ATOMIC, c.MAXIMUM_SUPPLY_ATOMIC)

    def test_nine_decimal_places_would_overflow_u64(self) -> None:
        self.assertGreater(c.MAXIMUM_SUPPLY_DISPLAY * 1_000_000_000, MAX_U64)

    def test_the_referral_channel_is_a_direct_mint_channel(self) -> None:
        kinds = {channel: kind for channel, kind, _ in c.CHANNELS}
        self.assertEqual(kinds[c.REFERRAL_CHANNEL], c.DIRECT_MINT)
        self.assertNotIn(
            "referral_permission", set(kinds.values()),
            "v2 has no referral permission kind",
        )
        self.assertIn(c.REFERRAL_CHANNEL, c.DIRECT_CHANNEL_IDS)
        self.assertNotIn(c.REFERRAL_CHANNEL, c.PLACEHOLDER_DIRECT_CHANNELS)
        self.assertEqual(len(c.PLACEHOLDER_DIRECT_CHANNELS), 4)


class DerivationStageTest(unittest.TestCase):
    """The arithmetic stage rejects a manifest the fixed table would accept."""

    def test_the_accepted_manifest_passes_the_derivation_stage_alone(self) -> None:
        check_derivations(manifest_value())

    def test_a_wrong_referral_cap_fails_the_derivation_stage(self) -> None:
        value = manifest_value()
        value["channels"][7]["cap_atomic"] = str(
            c.CHANNEL_CAPS[c.REFERRAL_CHANNEL] + c.REFERRAL_AMOUNT
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
            key: value
            for key, value in vectors().items()
            if key.endswith(".result")
        }
        self.assertGreater(len(results), 40)
        for key, value in results.items():
            self.assertIn(value, specified, key)


if __name__ == "__main__":
    unittest.main()
