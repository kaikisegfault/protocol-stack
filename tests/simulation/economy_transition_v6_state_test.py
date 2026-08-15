#!/usr/bin/env python3
"""The state key space, the trees, the roots, and version-six genesis.

The vectors record the values. What is tested here is what makes them
load-bearing: that a retired entry kind is refused rather than merely unwritten,
that the six root constructions are separated by their labels rather than by
their inputs, and that version-six genesis refuses an account rather than
expecting none.
"""

from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v6 import contract as c
from simulation.economy_transition_v6 import genesis as genesis_module
from simulation.economy_transition_v6 import scenario, state
from simulation.economy_transition_v6.identity import Posture
from simulation.economy_transition_v6.state import InvalidStateEntry

ACCOUNTS: list[tuple[bytes, int, int]] = [
    (bytes(range(32)), 100, 0),
    (bytes(range(0x20, 0x40)), 200, 1),
    (bytes(range(0x40, 0x60)), 300, 2),
]


class EntryKindTest(unittest.TestCase):
    def test_every_assigned_kind_has_a_key_and_value_width(self) -> None:
        self.assertEqual(set(c.ENTRY_KINDS), set(c.ENTRY_KEY_BYTES))
        self.assertEqual(set(c.ENTRY_KINDS), set(c.ENTRY_VALUE_BYTES))

    def test_no_retired_kind_is_assigned(self) -> None:
        self.assertFalse(set(c.RETIRED_ENTRY_KINDS) & set(c.ENTRY_KINDS))

    def test_a_retired_entry_kind_is_refused(self) -> None:
        for kind in c.RETIRED_ENTRY_KINDS:
            with self.subTest(kind=kind), self.assertRaises(InvalidStateEntry):
                state.ordered_entries({bytes([kind]) + bytes(32): b""})

    def test_a_value_of_the_wrong_width_is_refused(self) -> None:
        with self.assertRaises(InvalidStateEntry):
            state.ordered_entries({state.seat_key(0): b"short"})

    def test_no_key_names_both_a_seat_and_a_cycle(self) -> None:
        """Derived from the key table rather than asserted as a boolean."""
        seat_keyed = {c.SEAT_ENTRY}
        cycle_keyed = {c.CYCLE_ASSIGNMENT_ENTRY}
        self.assertFalse(seat_keyed & cycle_keyed)


class EntryValueTest(unittest.TestCase):
    def test_the_seat_record_is_eighty_two_bytes(self) -> None:
        value = state.seat_value(
            scenario.ALICE_IDENTITY, scenario.BOB_IDENTITY, activation_height=7
        )
        self.assertEqual(len(value), c.ENTRY_VALUE_BYTES[c.SEAT_ENTRY])
        self.assertEqual(len(value), 82)

    def test_the_seat_record_names_no_address(self) -> None:
        """ADR 0041's consequence, expressed as a width.

        Version four's record was 119 bytes and carried a purchaser account, a
        biometric flag, and a manager count. All three went with the concepts
        they served.
        """
        self.assertEqual(c.ENTRY_VALUE_BYTES[c.SEAT_ENTRY], 82)
        self.assertLess(c.ENTRY_VALUE_BYTES[c.SEAT_ENTRY], 119)

    def test_the_identity_record_separates_the_index_from_the_count(self) -> None:
        with self.assertRaises(InvalidStateEntry):
            state.hub_identity_value(bytes(32), 1, next_escrow_index=1, escrow_count=2, seat_count=0)
        value = state.hub_identity_value(bytes(32), 1, 3, 2, 0)
        self.assertEqual(len(value), 52)

    def test_the_escrow_record_holds_no_balance(self) -> None:
        """The balance is the version-one account entry's, keyed by the same 32
        octets, which is what keeps a version-six state a version-one state plus
        an economy map."""
        value = state.escrow_value(scenario.ALICE_IDENTITY, Posture(), 1)
        self.assertEqual(len(value), 49)
        self.assertEqual(len(value), 32 + 1 + 8 + 4 + 4)

    def test_an_enrollment_cannot_exceed_its_period(self) -> None:
        maximum = c.VERIFIED_USER_CYCLES * c.VERIFIED_USER_DAILY_ATOMIC
        state.verified_user_value(1, 1, maximum)
        with self.assertRaises(InvalidStateEntry):
            state.verified_user_value(1, 1, maximum + 1)

    def test_more_enrollments_than_the_population_are_refused(self) -> None:
        state.verified_user_counter_value(c.VERIFIED_USER_POPULATION)
        with self.assertRaises(InvalidStateEntry):
            state.verified_user_counter_value(c.VERIFIED_USER_POPULATION + 1)


class RootTest(unittest.TestCase):
    def setUp(self) -> None:
        self.arguments = dict(
            chain_id=scenario.CHAIN_ID,
            height=9,
            supply_limit=5_699_395_010_000_000_000,
            total_supply=1_000,
            fee_pool_balance=7,
            accounts=ACCOUNTS,
        )

    def test_all_six_roots_differ_over_identical_inputs(self) -> None:
        """Distinct labels are strings rather than a chain, so each separation
        is required rather than inferred from the one before it."""
        roots = {6: state.state_root(economy={}, **self.arguments)}
        for version in (1, 2, 3, 4, 5):
            roots[version] = state.predecessor_state_root(
                version=version, **self.arguments
            )
        self.assertEqual(len(set(roots.values())), 6)

    def test_the_accounts_tree_is_the_accepted_construction(self) -> None:
        recorded = {}
        path = Path(__file__).resolve().parents[2] / "test-vectors"
        for line in (path / "protocol-primitives-v1.txt").read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, value = line.strip().partition("=")
                recorded[key] = value
        accounts = [
            (
                bytes.fromhex(recorded[f"state.account{index}"][:64]),
                int(recorded[f"state.account{index}"][64:80], 16),
                int(recorded[f"state.account{index}"][80:96], 16),
            )
            for index in range(3)
        ]
        self.assertEqual(
            state.accounts_root(accounts).hex(), recorded["state.accounts_tree_root"]
        )

    def test_the_economy_changes_the_root(self) -> None:
        empty = state.state_root(economy={}, **self.arguments)
        populated = state.state_root(
            economy=scenario.populated_economy(), **self.arguments
        )
        self.assertNotEqual(empty, populated)

    def test_account_ids_must_strictly_increase(self) -> None:
        with self.assertRaises(InvalidStateEntry):
            state.accounts_root([ACCOUNTS[1], ACCOUNTS[0]])


class GenesisTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = scenario.genesis()

    def test_the_prefix_is_one_hundred_and_ten_octets(self) -> None:
        self.assertEqual(len(genesis_module.encode(self.fixture)), 110)

    def test_an_account_entry_is_refused(self) -> None:
        """Version six requires zero accounts rather than expecting none: an
        account with no escrow entry has no identity behind it."""
        with self.assertRaises(genesis_module.InvalidGenesis):
            genesis_module.encode(
                replace(self.fixture, accounts=[(bytes(32), 1, 0)])
            )

    def test_a_nonzero_supply_or_fee_pool_is_refused(self) -> None:
        with self.assertRaises(genesis_module.InvalidGenesis):
            genesis_module.encode(replace(self.fixture, total_supply=1))
        with self.assertRaises(genesis_module.InvalidGenesis):
            genesis_module.encode(replace(self.fixture, initial_fee_pool=1))

    def test_a_zero_fee_is_permitted(self) -> None:
        self.assertEqual(self.fixture.fixed_transfer_fee, 0)
        genesis_module.encode(self.fixture)

    def test_the_chain_id_differs_from_every_predecessor(self) -> None:
        six = genesis_module.chain_id(self.fixture)
        others = {
            genesis_module.predecessor_chain_id(self.fixture, version)
            for version in (2, 3, 4, 5)
        }
        self.assertNotIn(six, others)
        self.assertEqual(len(others), 4)

    def test_genesis_writes_the_verified_user_counter_at_zero(self) -> None:
        entries = genesis_module.initial_economy_entries(scenario.VERIFIER_KEY)
        self.assertEqual(
            entries[state.verified_user_counter_key()],
            state.verified_user_counter_value(0),
        )

    def test_genesis_writes_no_identity_escrow_or_signer(self) -> None:
        entries = genesis_module.initial_economy_entries(scenario.VERIFIER_KEY)
        written = {key[0] for key in entries}
        self.assertFalse(
            written
            & {
                c.SEAT_ENTRY,
                c.HUB_IDENTITY_ENTRY,
                c.ESCROW_ENTRY,
                c.SIGNER_ENTRY,
                c.VERIFIED_USER_ENTRY,
            }
        )

    def test_the_object_bound_is_inherited_and_unreachable(self) -> None:
        admitted, within, beyond = genesis_module.maximum_accounts_bound()
        self.assertEqual(admitted, 21_843)
        self.assertLessEqual(within, c.MAX_OBJECT_BYTES)
        self.assertGreater(beyond, c.MAX_OBJECT_BYTES)
        with self.assertRaises(genesis_module.InvalidGenesis):
            genesis_module.encode(replace(self.fixture, accounts=[(bytes(32), 1, 0)]))


class PopulatedEconomyTest(unittest.TestCase):
    def test_every_assigned_entry_kind_is_present(self) -> None:
        entries = scenario.populated_economy()
        self.assertEqual({key[0] for key in entries}, set(c.ENTRY_KINDS))

    def test_the_settlement_record_is_version_threes(self) -> None:
        """Imported rather than copied, so a copy could not drift from it."""
        recorded = {}
        path = Path(__file__).resolve().parents[2] / "test-vectors"
        for line in (path / "economy-transition-v3.txt").read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, value = line.strip().partition("=")
                recorded[key] = value
        records = scenario.assignment_records()
        self.assertEqual(
            records[scenario.CYCLE_WINDOW].hex(), recorded["cycle.assignment_value_hex"]
        )
        self.assertEqual(
            records[scenario.OUTAGE_WINDOW].hex(),
            recorded["outage.assignment_value_hex"],
        )


if __name__ == "__main__":
    unittest.main()
