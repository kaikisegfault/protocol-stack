#!/usr/bin/env python3
"""Version seven must differ from version six exactly where it says it does.

The vector file records version seven's own surface. This module reads the
negative half of the claim off the two packages, which catches a different class
of defect: a constant that moved without any vector reaching it.

Both directions matter. A name version six defines and version seven drops would
silently narrow the contract, and a name whose value moved without being
declared would widen it.

`contract.py` declares four sets — carried, rebound, revised, added — and this
module requires them to partition version six's public surface exactly and to
say the truth about every member.
"""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v6 import contract as v6
from simulation.economy_transition_v7 import contract as c

# The constructions the specification's version-identity table lists, plus the
# three tables the state key space changes and the manifest digest.
DECLARED_DIFFERENCES = frozenset(
    {
        "CHAIN_ID_LABEL",
        "STATE_ROOT_LABEL",
        "ECONOMY_TREE_PREFIX",
        "STATE_ROOT_SCHEMA_VERSION",
        "GENESIS_SCHEMA_VERSION",
        "RECEIPT_VERSION",
        "MANIFEST_DIGEST_HEX",
        "ENTRY_KINDS",
        "ENTRY_KEY_BYTES",
        "ENTRY_VALUE_BYTES",
        "RETIRED_ENTRY_KINDS",
        "CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES",
    }
)

# Version six defines these and version seven does not, because the concept is
# gone rather than renamed.
DECLARED_REMOVALS = frozenset({"CARRY_ENTRY"})


def public_names(module: types.ModuleType) -> set[str]:
    return {
        name
        for name in dir(module)
        if not name.startswith("_")
        and not isinstance(getattr(module, name), types.ModuleType)
        and name != "annotations"
    }


class DeclarationTest(unittest.TestCase):
    """The four sets must partition version six's surface with nothing left."""

    def test_the_declared_sets_are_disjoint(self) -> None:
        sets = {
            "carried": set(c.CARRIED_FROM_V6),
            "rebound": set(c.REBOUND),
            "revised": set(c.REVISED_IN_V7),
            "added": set(c.ADDED_IN_V7),
        }
        for left in sets:
            for right in sets:
                if left < right:
                    self.assertEqual(
                        sets[left] & sets[right],
                        set(),
                        f"{left} and {right} both claim a name",
                    )

    def test_the_declaration_covers_version_six_exactly(self) -> None:
        declared = (
            set(c.CARRIED_FROM_V6)
            | set(c.REBOUND)
            | set(c.REVISED_IN_V7)
            | DECLARED_REMOVALS
        )
        self.assertEqual(
            declared,
            public_names(v6),
            "the carried, rebound, revised, and removed sets must partition "
            "version six's public surface",
        )

    def test_the_revised_set_is_the_specification_table(self) -> None:
        self.assertEqual(set(c.REVISED_IN_V7), DECLARED_DIFFERENCES)

    def test_the_declaration_covers_version_seven_exactly(self) -> None:
        """Nothing version seven exports may go unclassified.

        Without this the declaration would cover version six's surface and say
        nothing about a name version seven added quietly, which is the same
        blind spot in the other direction.
        """
        declared = (
            set(c.CARRIED_FROM_V6)
            | set(c.REBOUND)
            | set(c.REVISED_IN_V7)
            | set(c.ADDED_IN_V7)
            | set(c.DECLARATIONS)
        )
        self.assertEqual(
            public_names(c),
            declared,
            "every name version seven exports must be carried, rebound, "
            "revised, added, or a declaration",
        )

    def test_every_added_name_exists_and_is_new(self) -> None:
        for name in c.ADDED_IN_V7:
            self.assertTrue(hasattr(c, name), f"{name} is declared added and absent")
            self.assertFalse(hasattr(v6, name), f"{name} is declared added and existed")


class CarryoverTest(unittest.TestCase):
    def test_every_carried_name_is_identical(self) -> None:
        for name in c.CARRIED_FROM_V6:
            self.assertEqual(
                getattr(c, name),
                getattr(v6, name),
                f"{name} is declared carried and its value moved",
            )

    def test_every_rebound_name_holds_version_six_s_value(self) -> None:
        """The version-three manifest renames one channel and moves no figure."""
        for name in c.REBOUND:
            self.assertEqual(
                getattr(c, name),
                getattr(v6, name),
                f"{name} is read from a different manifest and its value moved",
            )

    def test_every_rebound_name_is_read_from_the_version_three_manifest(self) -> None:
        from simulation.founder_economy_manifest_v3 import contract as manifest

        self.assertEqual(c.FOUNDER_SEAT_CAPACITY, manifest.FOUNDER_SEAT_CAPACITY)
        self.assertEqual(
            c.ISSUANCE_CYCLES_PER_SEAT, manifest.ISSUANCE_CYCLES_PER_SEAT
        )
        self.assertEqual(c.MAX_SEATS_PER_IDENTITY, manifest.MAXIMUM_SEATS_PER_PERSON)
        self.assertEqual(
            c.VERIFIED_USER_CHANNEL_CAP,
            manifest.CHANNEL_CAPS["hub_verified_user_incentives"],
        )
        self.assertEqual(c.MANIFEST_DIGEST_HEX, manifest.MANIFEST_DIGEST)

    def test_every_revised_name_actually_moved(self) -> None:
        for name in c.REVISED_IN_V7:
            self.assertNotEqual(
                getattr(c, name),
                getattr(v6, name),
                f"{name} is declared revised and did not move",
            )

    def test_every_removed_name_is_gone(self) -> None:
        for name in DECLARED_REMOVALS:
            self.assertFalse(
                hasattr(c, name), f"{name} is declared removed and is still defined"
            )


class RetirementTest(unittest.TestCase):
    def test_kind_seven_joins_the_retired_set(self) -> None:
        self.assertIn(v6.CARRY_ENTRY, c.RETIRED_ENTRY_KINDS)
        self.assertNotIn(v6.CARRY_ENTRY, c.ENTRY_KINDS)
        self.assertNotIn(v6.CARRY_ENTRY, c.ENTRY_KEY_BYTES)
        self.assertNotIn(v6.CARRY_ENTRY, c.ENTRY_VALUE_BYTES)

    def test_version_six_s_retirements_are_inherited(self) -> None:
        for kind in v6.RETIRED_ENTRY_KINDS:
            self.assertIn(kind, c.RETIRED_ENTRY_KINDS)

    def test_no_retired_kind_is_reused(self) -> None:
        self.assertEqual(set(c.RETIRED_ENTRY_KINDS) & set(c.ENTRY_KINDS), set())

    def test_the_pool_takes_a_number_no_version_has_assigned(self) -> None:
        self.assertNotIn(c.RECOVERY_POOL_ENTRY, v6.ENTRY_KINDS)
        self.assertNotIn(c.RECOVERY_POOL_ENTRY, v6.RETIRED_ENTRY_KINDS)

    def test_every_other_entry_kind_keeps_its_widths(self) -> None:
        for kind in v6.ENTRY_KINDS:
            if kind == v6.CARRY_ENTRY:
                continue
            self.assertEqual(c.ENTRY_KEY_BYTES[kind], v6.ENTRY_KEY_BYTES[kind])
            self.assertEqual(c.ENTRY_VALUE_BYTES[kind], v6.ENTRY_VALUE_BYTES[kind])
            self.assertEqual(c.ENTRY_KINDS[kind], v6.ENTRY_KINDS[kind])


class TransactionSurfaceTest(unittest.TestCase):
    """Version seven changes no transaction, so these must be identical."""

    def test_the_kind_table_is_unchanged(self) -> None:
        self.assertEqual(c.TRANSACTION_KINDS, v6.TRANSACTION_KINDS)
        self.assertEqual(c.RETIRED_KINDS, v6.RETIRED_KINDS)
        self.assertEqual(c.BODY_BYTES, v6.BODY_BYTES)
        self.assertEqual(c.KIND_SCHEME, v6.KIND_SCHEME)

    def test_the_result_code_space_is_unchanged(self) -> None:
        self.assertEqual(c.RESULT_CODES, v6.RESULT_CODES)
        self.assertEqual(c.UNREACHABLE_RESULT_CODES, v6.UNREACHABLE_RESULT_CODES)

    def test_the_hub_messages_are_unchanged(self) -> None:
        self.assertEqual(c.HUB_MESSAGE_LABELS, v6.HUB_MESSAGE_LABELS)
        self.assertEqual(c.VERIFIER_SIGNED_LABELS, v6.VERIFIER_SIGNED_LABELS)

    def test_the_settlement_constants_are_unchanged(self) -> None:
        self.assertEqual(c.MINT_ACCUMULATION_CAP, v6.MINT_ACCUMULATION_CAP)
        self.assertEqual(c.ASSIGNMENT_LAG_WINDOWS, v6.ASSIGNMENT_LAG_WINDOWS)
        self.assertEqual(c.BASE_PERMISSION_LEGS, v6.BASE_PERMISSION_LEGS)
        self.assertEqual(c.REFERRAL_LEG_ATOMIC, v6.REFERRAL_LEG_ATOMIC)


if __name__ == "__main__":
    unittest.main()
