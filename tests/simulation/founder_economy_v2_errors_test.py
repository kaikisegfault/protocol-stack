#!/usr/bin/env python3
"""Ordered manifest v2 acceptance failures and their exact codes."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import MAX_U64
from simulation.founder_economy_v2 import contract as c
from simulation.founder_economy_v2.manifest import (
    ManifestError,
    accept_manifest,
    load_manifest_text,
)
from tests.simulation.founder_economy_v2_common import manifest_value, mutated


class ManifestErrorTest(unittest.TestCase):
    def reject(self, value: object, code: str) -> ManifestError:
        with self.assertRaises(ManifestError) as raised:
            accept_manifest(value)
        self.assertEqual(raised.exception.code, code, raised.exception.detail)
        return raised.exception

    def reject_text(self, raw: str, code: str) -> None:
        with self.assertRaises(ManifestError) as raised:
            load_manifest_text(raw)
        self.assertEqual(raised.exception.code, code, raised.exception.detail)


class InvalidJsonTest(ManifestErrorTest):
    def test_truncated_input(self) -> None:
        self.reject_text('{"schema":', "INVALID_JSON")

    def test_trailing_data(self) -> None:
        self.reject_text("{} {}", "INVALID_JSON")

    def test_duplicate_field(self) -> None:
        self.reject_text('{"schema": "a", "schema": "b"}', "INVALID_JSON")

    def test_floating_point_token(self) -> None:
        self.reject_text('{"amount": 3.42}', "INVALID_JSON")

    def test_non_object_root(self) -> None:
        self.reject([], "INVALID_JSON")
        self.reject("manifest", "INVALID_JSON")


class ShapeTest(ManifestErrorTest):
    def test_unknown_top_level_field(self) -> None:
        self.reject(mutated(unexpected="x"), "UNKNOWN_FIELD")

    def test_missing_top_level_field(self) -> None:
        value = manifest_value()
        del value["referral_benefit"]
        self.reject(value, "UNKNOWN_FIELD")

    def test_unknown_referral_field(self) -> None:
        value = manifest_value()
        value["referral_benefit"]["monthly_pool_cycles"] = 30
        self.reject(value, "UNKNOWN_FIELD")

    def test_wrong_channel_count(self) -> None:
        value = manifest_value()
        value["channels"].pop()
        self.reject(value, "UNKNOWN_FIELD")

    def test_wrong_leg_count(self) -> None:
        value = manifest_value()
        value["base_permission"]["legs"].pop()
        self.reject(value, "UNKNOWN_FIELD")

    def test_wrong_placeholder_count(self) -> None:
        value = manifest_value()
        value["research_placeholders"].append("activity_eligibility_result")
        self.reject(value, "UNKNOWN_FIELD")

    def test_nested_object_replaced_by_scalar(self) -> None:
        self.reject(mutated(denomination="u64"), "UNKNOWN_FIELD")
        self.reject(mutated(channels={}), "UNKNOWN_FIELD")


class SchemaTest(ManifestErrorTest):
    def test_unsupported_schema(self) -> None:
        self.reject(mutated(schema="protocol-stack/other/v2"), "SCHEMA")

    def test_the_superseded_v1_schema_is_not_accepted(self) -> None:
        self.reject(mutated(schema=c.SUPERSEDED_SCHEMA), "SCHEMA")

    def test_research_only_must_be_the_boolean_true(self) -> None:
        self.reject(mutated(research_only=False), "SCHEMA")
        self.reject(mutated(research_only="true"), "SCHEMA")
        self.reject(mutated(research_only=1), "SCHEMA")


class TypeTest(ManifestErrorTest):
    def test_monetary_value_as_json_number(self) -> None:
        value = manifest_value()
        value["denomination"]["maximum_supply_atomic"] = c.MAXIMUM_SUPPLY_ATOMIC
        self.reject(value, "TYPE")

    def test_monetary_string_with_leading_zero(self) -> None:
        value = manifest_value()
        value["referral_benefit"]["amount_atomic"] = "03420000000"
        self.reject(value, "TYPE")

    def test_negative_monetary_string(self) -> None:
        value = manifest_value()
        value["channels"][0]["cap_atomic"] = "-1"
        self.reject(value, "TYPE")

    def test_count_as_boolean(self) -> None:
        value = manifest_value()
        value["seat_schedule"]["founder_seat_capacity"] = True
        self.reject(value, "TYPE")

    def test_unconditional_must_be_a_boolean(self) -> None:
        value = manifest_value()
        value["referral_benefit"]["unconditional"] = "true"
        self.reject(value, "TYPE")

    def test_identifier_as_non_string(self) -> None:
        value = manifest_value()
        value["channels"][0]["id"] = 0
        self.reject(value, "TYPE")


class RangeTest(ManifestErrorTest):
    def test_monetary_value_above_u64(self) -> None:
        value = manifest_value()
        value["channels"][0]["cap_atomic"] = str(MAX_U64 + 1)
        self.reject(value, "RANGE")

    def test_decimal_places_above_its_limit(self) -> None:
        value = manifest_value()
        value["denomination"]["decimal_places"] = 33
        self.reject(value, "RANGE")


class FixedValueTest(ManifestErrorTest):
    def test_changed_channel_order(self) -> None:
        value = manifest_value()
        value["channels"][0], value["channels"][1] = (
            value["channels"][1],
            value["channels"][0],
        )
        self.reject(value, "MANIFEST_MISMATCH")

    def test_changed_channel_cap(self) -> None:
        value = manifest_value()
        value["channels"][0]["cap_atomic"] = "1"
        self.reject(value, "MANIFEST_MISMATCH")

    def test_referral_moved_back_to_the_base_group(self) -> None:
        value = manifest_value()
        value["channels"][7]["issuance_kind"] = c.BASE_PERMISSION
        self.reject(value, "MANIFEST_MISMATCH")

    def test_the_superseded_referral_amount_is_rejected(self) -> None:
        value = manifest_value()
        value["referral_benefit"]["amount_atomic"] = str(c.SUPERSEDED_REFERRAL_AMOUNT)
        self.reject(value, "MANIFEST_MISMATCH")

    def test_the_superseded_maximum_supply_is_rejected(self) -> None:
        value = manifest_value()
        value["denomination"]["maximum_supply_display"] = str(
            c.SUPERSEDED_MAXIMUM_SUPPLY_DISPLAY
        )
        value["denomination"]["maximum_supply_atomic"] = str(
            c.SUPERSEDED_MAXIMUM_SUPPLY_DISPLAY * c.ATOMIC_UNITS_PER_DISPLAY_UNIT
        )
        self.reject(value, "MANIFEST_MISMATCH")

    def test_a_conditional_referral_is_rejected(self) -> None:
        value = manifest_value()
        value["referral_benefit"]["unconditional"] = False
        self.reject(value, "MANIFEST_MISMATCH")

    def test_removing_the_unreferred_pool_destination_is_rejected(self) -> None:
        value = manifest_value()
        value["referral_benefit"]["unreferred_beneficiary_kind"] = "recorded_referrer"
        self.reject(value, "MANIFEST_MISMATCH")

    def test_a_retired_research_placeholder_is_rejected(self) -> None:
        for retired in (
            "activity_eligibility_result",
            "inactive_performance_allocation_result",
            "inactive_referral_eligibility_result",
        ):
            value = manifest_value()
            value["research_placeholders"][0] = retired
            self.reject(value, "MANIFEST_MISMATCH")


    def test_a_changed_base_total_is_caught_by_the_fixed_table(self) -> None:
        """The derivation stage is reachable only past this comparison.

        Its own rejections are exercised directly in the manifest tests, which
        is what proves the arithmetic is a real gate rather than a restatement
        of the table above.
        """
        value = manifest_value()
        value["base_permission"]["total_atomic"] = str(c.BASE_PERMISSION_TOTAL + 1)
        error = self.reject(value, "MANIFEST_MISMATCH")
        self.assertIn("total_atomic", error.detail)


class FailureOrderTest(ManifestErrorTest):
    """A manifest carrying two defects reports the earlier stage."""

    def test_shape_precedes_schema(self) -> None:
        self.reject(mutated(unexpected="x", schema="other"), "UNKNOWN_FIELD")

    def test_schema_precedes_type(self) -> None:
        value = mutated(schema="other")
        value["channels"][0]["cap_atomic"] = 1
        self.reject(value, "SCHEMA")

    def test_type_precedes_range(self) -> None:
        value = manifest_value()
        value["channels"][0]["cap_atomic"] = 1
        value["channels"][1]["cap_atomic"] = str(MAX_U64 + 1)
        self.reject(value, "TYPE")

    def test_range_precedes_fixed_values(self) -> None:
        value = manifest_value()
        value["denomination"]["decimal_places"] = 33
        value["channels"][0]["cap_atomic"] = "1"
        self.reject(value, "RANGE")


class NoPartialAcceptanceTest(ManifestErrorTest):
    def test_a_rejected_manifest_returns_no_identity(self) -> None:
        """Every failure raises; no caller can observe a half-accepted manifest."""
        value = manifest_value()
        value["channels"][0]["cap_atomic"] = "1"
        with self.assertRaises(ManifestError):
            accept_manifest(value)
        self.assertEqual(value["channels"][0]["cap_atomic"], "1", "loader mutated input")

    def test_acceptance_copies_the_source(self) -> None:
        value = manifest_value()
        accepted = accept_manifest(value)
        value["schema"] = "mutated-after-acceptance"
        self.assertEqual(accepted.source["schema"], c.MANIFEST_SCHEMA)


if __name__ == "__main__":
    unittest.main()
