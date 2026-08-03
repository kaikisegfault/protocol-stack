#!/usr/bin/env python3
"""Manifest identity, ordered failure codes, and derived supply tests."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.founder_economy import contract as c
from simulation.founder_economy.canonical import MAX_U64, canonical_bytes, label_prefix
from simulation.founder_economy.derivations import DerivationError, check_derivations
from simulation.founder_economy.manifest import (
    ManifestError,
    accept_manifest,
    load_manifest_text,
)
from tests.simulation.founder_economy_common import manifest, manifest_value, vectors


class ManifestIdentityTest(unittest.TestCase):
    def test_accepted_manifest_reproduces_its_canonical_identity(self) -> None:
        accepted = manifest()
        self.assertEqual(accepted.canonical_length, c.MANIFEST_CANONICAL_LENGTH)
        self.assertEqual(accepted.manifest_digest, c.MANIFEST_DIGEST)
        self.assertEqual(len(canonical_bytes(accepted.source)), 2297)

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

    def test_vector_file_agrees_with_the_loaded_manifest(self) -> None:
        recorded = vectors()
        accepted = manifest()
        self.assertEqual(recorded["schema"], c.MANIFEST_SCHEMA)
        self.assertEqual(recorded["manifest_domain_label"], c.MANIFEST_LABEL)
        self.assertEqual(int(recorded["manifest_domain_label_length"]), 42)
        self.assertEqual(
            int(recorded["manifest_canonical_json_length"]),
            accepted.canonical_length,
        )
        self.assertEqual(recorded["manifest_digest"], accepted.manifest_digest)
        self.assertEqual(int(recorded["u64_max"]), MAX_U64)


class ManifestDerivationTest(unittest.TestCase):
    def test_denomination_fits_and_nine_decimals_overflow(self) -> None:
        recorded = vectors()
        maximum = c.MAXIMUM_SUPPLY_DISPLAY * c.ATOMIC_UNITS_PER_DISPLAY_UNIT
        self.assertEqual(maximum, c.MAXIMUM_SUPPLY_ATOMIC)
        self.assertLessEqual(maximum, MAX_U64)
        self.assertEqual(int(recorded["denomination.u64_headroom"]), MAX_U64 - maximum)
        self.assertEqual(
            int(recorded["denomination.maximum_decimal_multiplier"]),
            MAX_U64 // c.MAXIMUM_SUPPLY_DISPLAY,
        )
        nine_decimal = c.MAXIMUM_SUPPLY_DISPLAY * 1_000_000_000
        self.assertEqual(int(recorded["denomination.nine_decimal_atomic"]), nine_decimal)
        self.assertGreater(nine_decimal, MAX_U64)
        self.assertEqual(recorded["denomination.nine_decimal.result"], "ARITHMETIC_OVERFLOW")

    def test_channel_caps_and_subtotals_derive_the_maximum(self) -> None:
        recorded = vectors()
        self.assertEqual(int(recorded["channels.count"]), len(c.CHANNELS))
        founder = 0
        direct = 0
        for index, (channel_id, kind, cap) in enumerate(c.CHANNELS):
            self.assertEqual(recorded[f"channel{index}.id"], channel_id)
            self.assertEqual(recorded[f"channel{index}.kind"], kind)
            self.assertEqual(int(recorded[f"channel{index}.cap"]), cap)
            if kind == c.DIRECT_MINT:
                direct += cap
            else:
                founder += cap
        self.assertEqual(founder, int(recorded["channels.founder_subtotal"]))
        self.assertEqual(direct, int(recorded["channels.direct_subtotal"]))
        self.assertEqual(founder + direct, c.MAXIMUM_SUPPLY_ATOMIC)
        self.assertEqual(founder + direct, int(recorded["channels.total"]))

    def test_per_seat_and_full_schedules_derive_every_base_cap(self) -> None:
        recorded = vectors()
        seats = c.FOUNDER_SEAT_CAPACITY
        cycles = c.ISSUANCE_CYCLES_PER_SEAT
        base_total = 0
        for channel_id, _, amount in c.BASE_LEGS:
            self.assertEqual(int(recorded[f"base_permission.{channel_id}"]), amount)
            self.assertEqual(int(recorded[f"per_seat_731.{channel_id}"]), amount * cycles)
            self.assertEqual(
                int(recorded[f"full_schedule.{channel_id}"]),
                amount * cycles * seats,
            )
            self.assertEqual(c.CHANNEL_CAPS[channel_id], amount * cycles * seats)
            base_total += amount
        self.assertEqual(base_total, c.BASE_PERMISSION_TOTAL)
        self.assertEqual(base_total, int(recorded["base_permission.total"]))
        self.assertEqual(int(recorded["per_seat_731.base_total"]), base_total * cycles)
        self.assertEqual(
            int(recorded["full_schedule.base_total"]),
            base_total * cycles * seats,
        )

    def test_referral_schedule_derives_the_referral_cap(self) -> None:
        recorded = vectors()
        seats = c.FOUNDER_SEAT_CAPACITY
        cycles = c.ISSUANCE_CYCLES_PER_SEAT
        self.assertEqual(int(recorded["referral_permission.amount"]), c.REFERRAL_AMOUNT)
        self.assertEqual(
            int(recorded["per_seat_731.referral"]),
            c.REFERRAL_AMOUNT * cycles,
        )
        self.assertEqual(
            c.CHANNEL_CAPS[c.REFERRAL_CHANNEL],
            c.REFERRAL_AMOUNT * cycles * seats,
        )
        self.assertEqual(
            int(recorded["per_seat_731.founder_total"]),
            (c.BASE_PERMISSION_TOTAL + c.REFERRAL_AMOUNT) * cycles,
        )

    def test_permission_key_ceiling_matches_the_seat_schedule(self) -> None:
        recorded = vectors()
        ceiling = c.FOUNDER_SEAT_CAPACITY * c.ISSUANCE_CYCLES_PER_SEAT
        self.assertEqual(int(recorded["seat_schedule.maximum_base_permission_count"]), ceiling)
        self.assertEqual(
            int(recorded["seat_schedule.maximum_referral_permission_count"]),
            ceiling,
        )


class ManifestFailureOrderTest(unittest.TestCase):
    def assert_code(self, value: object, expected: str) -> None:
        with self.assertRaises(ManifestError) as caught:
            accept_manifest(value)
        self.assertEqual(caught.exception.code, expected)

    def test_invalid_json_is_reported_first(self) -> None:
        for raw in ("{", "[]", '{"schema": 1.5}', '{"a":1}{"b":2}', '{"a":1,"a":2}'):
            with self.subTest(raw=raw):
                with self.assertRaises(ManifestError) as caught:
                    load_manifest_text(raw)
                self.assertEqual(caught.exception.code, "INVALID_JSON")

    def test_shape_schema_type_and_range_precede_content(self) -> None:
        cases = [
            (lambda v: v.pop("channels"), "UNKNOWN_FIELD"),
            (lambda v: v.update(extra=1), "UNKNOWN_FIELD"),
            (lambda v: v["channels"].pop(), "UNKNOWN_FIELD"),
            (lambda v: v["channels"][0].pop("issuance_kind"), "UNKNOWN_FIELD"),
            (lambda v: v["base_permission"]["legs"][0].update(extra=1), "UNKNOWN_FIELD"),
            (lambda v: v.update(schema="protocol-stack/other/v1"), "SCHEMA"),
            (lambda v: v.update(research_only=False), "SCHEMA"),
            (lambda v: v["channels"][0].update(cap_atomic=2500020000000000000), "TYPE"),
            (lambda v: v["channels"][0].update(cap_atomic="02500020000000000000"), "TYPE"),
            (lambda v: v["channels"][0].update(cap_atomic="-1"), "TYPE"),
            (lambda v: v["denomination"].update(decimal_places="8"), "TYPE"),
            (lambda v: v["channels"][0].update(cap_atomic=str(MAX_U64 + 1)), "RANGE"),
            (lambda v: v["denomination"].update(decimal_places=64), "RANGE"),
        ]
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                value = manifest_value()
                mutate(value)
                self.assert_code(value, expected)

    def test_changed_fixed_values_are_manifest_mismatches(self) -> None:
        cases = [
            lambda v: v["channels"].insert(0, v["channels"].pop(1)),
            lambda v: v["channels"][0].update(cap_atomic="2500020000000000001"),
            lambda v: v["channels"][0].update(id="other_channel"),
            lambda v: v["channels"][0].update(issuance_kind="direct_mint"),
            lambda v: v["base_permission"]["legs"][0].update(beneficiary_kind="other"),
            lambda v: v["research_placeholders"].reverse(),
            lambda v: v["denomination"].update(storage_type="u128"),
            lambda v: v["seat_schedule"].update(founder_seat_capacity=99_999),
        ]
        for index, mutate in enumerate(cases):
            with self.subTest(case=index):
                value = manifest_value()
                mutate(value)
                self.assert_code(value, "MANIFEST_MISMATCH")

    def assert_derivation_code(self, value: dict, expected: str) -> None:
        with self.assertRaises(DerivationError) as caught:
            check_derivations(value)
        self.assertEqual(caught.exception.code, expected)

    def test_accepted_manifest_passes_the_derivation_stage(self) -> None:
        check_derivations(manifest_value())

    def test_broken_derivations_are_supply_mismatches(self) -> None:
        """A self-consistent manifest with wrong arithmetic is still rejected."""
        cases = [
            lambda v: v["base_permission"].update(
                total_atomic=str(c.BASE_PERMISSION_TOTAL - 1)
            ),
            lambda v: v["channels"][9].update(
                cap_atomic=str(c.CHANNEL_CAPS["initial_mystery_box_incentives"] - 1)
            ),
            lambda v: v["channels"][0].update(
                cap_atomic=str(c.CHANNEL_CAPS["founder_operator"] - 1)
            ),
            lambda v: v["denomination"].update(maximum_supply_atomic="1"),
        ]
        for index, mutate in enumerate(cases):
            with self.subTest(case=index):
                value = manifest_value()
                mutate(value)
                self.assert_derivation_code(value, "SUPPLY_MISMATCH")

    def test_unrepresentable_derivations_are_arithmetic_overflows(self) -> None:
        cases = [
            lambda v: v["denomination"].update(
                atomic_units_per_display_unit="1000000000"
            ),
            lambda v: v["base_permission"]["legs"][0].update(
                amount_atomic=str(MAX_U64)
            ),
            lambda v: v["seat_schedule"].update(founder_seat_capacity=MAX_U64),
        ]
        for index, mutate in enumerate(cases):
            with self.subTest(case=index):
                value = manifest_value()
                mutate(value)
                self.assert_derivation_code(value, "ARITHMETIC_OVERFLOW")

    def test_fixed_comparison_precedes_derivation_in_the_ordered_loader(self) -> None:
        """The loader reports the earlier code for a manifest failing both."""
        value = manifest_value()
        value["base_permission"]["total_atomic"] = str(c.BASE_PERMISSION_TOTAL - 1)
        self.assert_derivation_code(value, "SUPPLY_MISMATCH")
        self.assert_code(value, "MANIFEST_MISMATCH")

    def test_recorded_negative_codes_are_all_modelled(self) -> None:
        modelled = {
            "INVALID_JSON",
            "UNKNOWN_FIELD",
            "SCHEMA",
            "TYPE",
            "RANGE",
            "MANIFEST_MISMATCH",
            "ARITHMETIC_OVERFLOW",
            "SUPPLY_MISMATCH",
            "CYCLE_RANGE",
            "REPLAY",
            "MISSING_RESEARCH_INPUT",
            "INVALID_RESEARCH_INPUT",
            "INVALID_PERFORMANCE_ALLOCATION",
            "CHANNEL_CAP",
            "PERMISSION_NOT_FOUND",
            "INVARIANT",
        }
        recorded = {
            value
            for key, value in vectors().items()
            if key.startswith("negative.") and key.endswith(".result")
        }
        self.assertTrue(recorded <= modelled, sorted(recorded - modelled))


if __name__ == "__main__":
    unittest.main()
