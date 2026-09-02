#!/usr/bin/env python3
"""Version eight must differ from version seven exactly where it says it does.

The vector file records version eight's own surface. This module reads the
negative half of the claim off the two packages, which catches a different class
of defect: a constant that moved without any vector reaching it.

Both directions matter. A name version seven defines and version eight drops
would silently narrow the contract, and a name whose value moved without being
declared would widen it.

`contract.py` declares four sets — carried, revised, added, and version seven's
own provenance sets which every version replaces — and this module requires them
to partition version seven's public surface exactly and to say the truth about
every member.
"""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v7 import contract as v7
from simulation.economy_transition_v8 import contract as c

# The constructions the specification's version-identity table lists, plus the
# tables the three key spaces change and the two genesis figures that follow
# from the added field.
DECLARED_DIFFERENCES = frozenset(
    {
        "CHAIN_ID_LABEL",
        "STATE_ROOT_LABEL",
        "ECONOMY_TREE_PREFIX",
        "STATE_ROOT_SCHEMA_VERSION",
        "GENESIS_SCHEMA_VERSION",
        "RECEIPT_VERSION",
        "ENTRY_KINDS",
        "ENTRY_KEY_BYTES",
        "ENTRY_VALUE_BYTES",
        "TRANSACTION_KINDS",
        "BODY_BYTES",
        "KIND_SCHEME",
        "RESULT_CODES",
        "CODE_NUMBER",
        "GENESIS_PREFIX_BYTES",
        "MAX_GENESIS_ACCOUNTS",
    }
)


def public_names(module: types.ModuleType) -> set[str]:
    return {
        name
        for name in dir(module)
        if not name.startswith("_")
        and not isinstance(getattr(module, name), types.ModuleType)
        and name != "annotations"
    }


class DeclarationTest(unittest.TestCase):
    """The four sets must partition version seven's surface with nothing left."""

    def test_the_declared_sets_are_disjoint(self) -> None:
        sets = {
            "carried": set(c.CARRIED_FROM_V7),
            "revised": set(c.REVISED_IN_V8),
            "added": set(c.ADDED_IN_V8),
            "replaced": set(c.REPLACED_DECLARATIONS),
        }
        for left in sets:
            for right in sets:
                if left < right:
                    self.assertEqual(
                        sets[left] & sets[right],
                        set(),
                        f"{left} and {right} both claim a name",
                    )

    def test_the_declaration_covers_version_seven_exactly(self) -> None:
        declared = (
            set(c.CARRIED_FROM_V7)
            | set(c.REVISED_IN_V8)
            | set(c.REPLACED_DECLARATIONS)
        )
        self.assertEqual(
            declared,
            public_names(v7),
            "the carried, revised, and replaced sets must partition version "
            "seven's public surface",
        )

    def test_the_revised_set_is_the_specification_table(self) -> None:
        self.assertEqual(set(c.REVISED_IN_V8), DECLARED_DIFFERENCES)

    def test_the_declaration_covers_version_eight_exactly(self) -> None:
        """Nothing version eight exports may go unclassified.

        Without this the declaration would cover version seven's surface and say
        nothing about a name version eight added quietly, which is the same
        blind spot in the other direction.
        """
        declared = (
            set(c.CARRIED_FROM_V7)
            | set(c.REVISED_IN_V8)
            | set(c.ADDED_IN_V8)
            | set(c.DECLARATIONS)
        )
        self.assertEqual(
            public_names(c),
            declared,
            "every name version eight exports must be carried, revised, added, "
            "or a declaration",
        )

    def test_every_added_name_exists_and_is_new(self) -> None:
        for name in c.ADDED_IN_V8:
            self.assertTrue(hasattr(c, name), f"{name} is declared added and absent")
            self.assertFalse(hasattr(v7, name), f"{name} is declared added and existed")

    def test_every_replaced_declaration_is_gone_or_redefined(self) -> None:
        """Version seven's provenance sets say nothing about this pair."""
        for name in c.REPLACED_DECLARATIONS:
            if name == "DECLARATIONS":
                self.assertNotEqual(
                    c.DECLARATIONS,
                    v7.DECLARATIONS,
                    "version eight must declare its own set names",
                )
                continue
            self.assertFalse(
                hasattr(c, name),
                f"{name} describes version six and version seven, not this pair",
            )


class CarryoverTest(unittest.TestCase):
    def test_every_carried_name_is_identical(self) -> None:
        for name in c.CARRIED_FROM_V7:
            self.assertEqual(
                getattr(c, name),
                getattr(v7, name),
                f"{name} is declared carried and its value moved",
            )

    def test_every_revised_name_actually_moved(self) -> None:
        for name in c.REVISED_IN_V8:
            self.assertNotEqual(
                getattr(c, name),
                getattr(v7, name),
                f"{name} is declared revised and did not move",
            )

    def test_the_manifest_binding_does_not_move(self) -> None:
        """Version eight changes no founder-directed figure."""
        from simulation.founder_economy_manifest_v3 import contract as manifest

        self.assertEqual(c.MANIFEST_DIGEST_HEX, manifest.MANIFEST_DIGEST)
        self.assertEqual(c.MANIFEST_DIGEST_HEX, v7.MANIFEST_DIGEST_HEX)
        self.assertEqual(c.BASE_PERMISSION_LEGS, v7.BASE_PERMISSION_LEGS)
        self.assertEqual(c.REFERRAL_LEG_ATOMIC, v7.REFERRAL_LEG_ATOMIC)
        self.assertEqual(c.FOUNDER_SEAT_CAPACITY, manifest.FOUNDER_SEAT_CAPACITY)


class KindSpaceTest(unittest.TestCase):
    def test_the_two_kinds_take_numbers_no_version_has_assigned(self) -> None:
        for kind in (c.CHALLENGE_RESPONSE, c.FILE_DISPUTE):
            self.assertNotIn(kind, v7.TRANSACTION_KINDS)
            self.assertNotIn(kind, v7.RETIRED_KINDS)

    def test_no_retired_kind_is_reused(self) -> None:
        self.assertEqual(set(c.RETIRED_KINDS) & set(c.TRANSACTION_KINDS), set())

    def test_version_seven_s_kinds_keep_their_bodies_and_schemes(self) -> None:
        for kind in v7.TRANSACTION_KINDS:
            self.assertEqual(c.TRANSACTION_KINDS[kind], v7.TRANSACTION_KINDS[kind])
            self.assertEqual(c.BODY_BYTES[kind], v7.BODY_BYTES[kind])
            self.assertEqual(c.KIND_SCHEME[kind], v7.KIND_SCHEME[kind])

    def test_every_kind_has_a_body_width_and_a_scheme(self) -> None:
        self.assertEqual(set(c.TRANSACTION_KINDS), set(c.BODY_BYTES))
        self.assertEqual(set(c.TRANSACTION_KINDS), set(c.KIND_SCHEME))


class EntrySpaceTest(unittest.TestCase):
    def test_the_two_entries_take_numbers_no_version_has_assigned(self) -> None:
        for kind in (c.OPEN_CHALLENGE_ENTRY, c.SEAT_WINDOW_ENTRY):
            self.assertNotIn(kind, v7.ENTRY_KINDS)
            self.assertNotIn(kind, v7.RETIRED_ENTRY_KINDS)

    def test_no_retired_entry_kind_is_reused(self) -> None:
        self.assertEqual(set(c.RETIRED_ENTRY_KINDS) & set(c.ENTRY_KINDS), set())

    def test_every_other_entry_kind_keeps_its_widths(self) -> None:
        for kind in v7.ENTRY_KINDS:
            self.assertEqual(c.ENTRY_KEY_BYTES[kind], v7.ENTRY_KEY_BYTES[kind])
            self.assertEqual(c.ENTRY_VALUE_BYTES[kind], v7.ENTRY_VALUE_BYTES[kind])
            self.assertEqual(c.ENTRY_KINDS[kind], v7.ENTRY_KINDS[kind])

    def test_every_entry_kind_has_a_key_and_a_value_width(self) -> None:
        self.assertEqual(set(c.ENTRY_KINDS), set(c.ENTRY_KEY_BYTES))
        self.assertEqual(set(c.ENTRY_KINDS), set(c.ENTRY_VALUE_BYTES))


class ResultCodeTest(unittest.TestCase):
    def test_the_space_is_contiguous_from_zero(self) -> None:
        self.assertEqual(sorted(c.RESULT_CODES), list(range(45)))

    def test_version_seven_s_codes_keep_their_numbers_and_names(self) -> None:
        for number, name in v7.RESULT_CODES.items():
            self.assertEqual(c.RESULT_CODES[number], name)

    def test_the_added_codes_are_exactly_the_new_numbers(self) -> None:
        self.assertEqual(
            set(c.ADDED_IN_V8_RESULT_CODES),
            set(c.RESULT_CODES) - set(v7.RESULT_CODES),
        )
        self.assertEqual(sorted(c.ADDED_IN_V8_RESULT_CODES), list(range(33, 45)))

    def test_no_name_is_reused(self) -> None:
        self.assertEqual(len(c.CODE_NUMBER), len(c.RESULT_CODES))

    def test_the_frozen_unreachable_codes_are_inherited(self) -> None:
        self.assertEqual(c.UNREACHABLE_RESULT_CODES, v7.UNREACHABLE_RESULT_CODES)

    def test_no_absent_model_code_is_encoded(self) -> None:
        """A code no path produces claims coverage the vectors cannot show."""
        for name in c.ABSENT_MODEL_CODES:
            self.assertNotIn(name, c.CODE_NUMBER, f"{name} is declared absent")

    def test_every_absent_model_code_carries_a_reason(self) -> None:
        for name, reason in c.ABSENT_MODEL_CODES.items():
            self.assertTrue(reason.strip(), f"{name} is absent without a reason")


class MeasurementBindingTest(unittest.TestCase):
    """Every figure below is `uptime-measurement-v1`'s, not a new choice."""

    def test_the_challenge_period_is_the_slot(self) -> None:
        self.assertEqual(c.CHALLENGE_PERIOD_BLOCKS, c.SLOT_BLOCKS)

    def test_the_challengeable_heights_exclude_the_deadline(self) -> None:
        self.assertEqual(
            c.CHALLENGEABLE_HEIGHTS_PER_SLOT,
            c.SLOT_BLOCKS - c.RESPONSE_DEADLINE_BLOCKS,
        )
        self.assertEqual(c.CHALLENGEABLE_HEIGHTS_PER_SLOT, 1_180)

    def test_a_slot_is_one_hour(self) -> None:
        self.assertEqual(c.SLOT_BLOCKS * c.SLOTS_PER_WINDOW, c.CYCLE_BLOCKS)
        self.assertEqual(c.SLOT_SECONDS * c.SLOTS_PER_WINDOW, 86_400)

    def test_the_dispute_cap_leaves_a_perfect_seat_meeting_its_cycle(self) -> None:
        """Invariant 6: the containment theorem, over the encoded state."""
        remaining = c.SLOTS_PER_WINDOW - c.DISPUTE_CAP_SLOTS_PER_SEAT
        self.assertEqual(remaining * c.SLOT_SECONDS, 64_800)

    def test_the_retained_windows_are_the_assignment_lag(self) -> None:
        self.assertEqual(c.RETAINED_WINDOWS, c.ASSIGNMENT_LAG_WINDOWS)


class GenesisFigureTest(unittest.TestCase):
    def test_the_prefix_grows_by_one_key(self) -> None:
        self.assertEqual(
            c.GENESIS_PREFIX_BYTES,
            v7.GENESIS_PREFIX_BYTES + c.DISPUTE_AUTHORITY_KEY_BYTES,
        )
        self.assertEqual(c.GENESIS_PREFIX_BYTES, 142)

    def test_the_account_bound_falls_and_stays_unreachable(self) -> None:
        self.assertLess(c.MAX_GENESIS_ACCOUNTS, v7.MAX_GENESIS_ACCOUNTS)
        self.assertEqual(c.MAX_GENESIS_ACCOUNTS, 21_842)


class LabelTest(unittest.TestCase):
    def test_the_two_new_labels_are_version_eight_s(self) -> None:
        for label in c.UPTIME_LABELS:
            self.assertTrue(label.startswith("protocol-stack:v8:"))

    def test_every_other_label_keeps_the_version_that_accepted_it(self) -> None:
        self.assertEqual(c.ACCOUNT_LABEL, v7.ACCOUNT_LABEL)
        self.assertEqual(c.ESCROW_LABEL, v7.ESCROW_LABEL)
        self.assertEqual(c.SIGN_LABEL, v7.SIGN_LABEL)
        self.assertEqual(c.TX_ID_LABEL, v7.TX_ID_LABEL)
        self.assertEqual(c.HUB_MESSAGE_LABELS, v7.HUB_MESSAGE_LABELS)

    def test_the_re_versioned_labels_all_moved(self) -> None:
        for label in (c.CHAIN_ID_LABEL, c.STATE_ROOT_LABEL, c.ECONOMY_TREE_PREFIX):
            self.assertIn(":v8:", label)

    def test_no_two_labels_collide(self) -> None:
        labels = (
            c.CHAIN_ID_LABEL,
            c.STATE_ROOT_LABEL,
            c.ECONOMY_TREE_PREFIX,
            *c.UPTIME_LABELS,
        )
        self.assertEqual(len(set(labels)), len(labels))


if __name__ == "__main__":
    unittest.main()
