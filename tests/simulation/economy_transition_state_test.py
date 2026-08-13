#!/usr/bin/env python3
"""The economy state key space, its tree, the version-two root, and genesis."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition import contract as c
from simulation.economy_transition import genesis, scenario, state


class KeySpaceTest(unittest.TestCase):
    def test_every_key_carries_its_entry_kind_and_fixed_width(self) -> None:
        keys = {
            c.SEAT_ENTRY: state.seat_key(7),
            c.CHANNEL_ENTRY: state.channel_key(0),
            c.PENDING_PERMISSION_ENTRY: state.pending_permission_key(7, 1),
            c.REFERRAL_ACCRUAL_ENTRY: state.referral_accrual_key(7, 1),
            c.DIRECT_DECISION_ENTRY: state.direct_decision_key(scenario.DECISION_ID),
            c.TYPED_CUSTODY_ENTRY: state.typed_custody_key(
                1, scenario.BENEFICIARY_ACCOUNT_ID
            ),
            c.PERFORMANCE_CARRY_ENTRY: state.performance_carry_key(),
            c.WINDOW_RESULT_ENTRY: state.window_result_key(scenario.WINDOW),
        }
        self.assertEqual(sorted(keys), sorted(c.ENTRY_KINDS))
        for kind, key in keys.items():
            with self.subTest(c.ENTRY_KINDS[kind]):
                self.assertEqual(key[0], kind)
                self.assertEqual(len(key), c.ENTRY_KEY_BYTES[kind])

    def test_no_key_is_a_prefix_of_another(self) -> None:
        """What makes unsigned lexicographic order total over mixed widths."""
        keys = sorted(scenario.populated_economy())
        for index, earlier in enumerate(keys):
            for later in keys[index + 1 :]:
                self.assertFalse(later.startswith(earlier), (earlier, later))

    def test_two_seats_and_two_cycles_never_collide(self) -> None:
        self.assertNotEqual(state.seat_key(0), state.seat_key(1))
        self.assertNotEqual(
            state.pending_permission_key(0, 1), state.pending_permission_key(1, 0)
        )
        self.assertNotEqual(
            state.pending_permission_key(7, 1), state.referral_accrual_key(7, 1)
        )

    def test_a_value_of_the_wrong_width_is_refused(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.economy_root({state.seat_key(0): b"\x00"})
        with self.assertRaises(state.InvalidStateEntry):
            state.economy_root({b"\x63\x00": b""})

    def test_the_verdict_byte_answers_both_questions(self) -> None:
        """One entry replaces the model's permission record and its replay set."""
        for verdict in (c.VERDICT_FAILED, c.VERDICT_MET, c.VERDICT_EXERCISED):
            self.assertEqual(len(state.pending_permission_value(verdict)), 1)
        with self.assertRaises(state.InvalidStateEntry):
            state.pending_permission_value(3)


class BitmapTest(unittest.TestCase):
    def test_bits_are_packed_most_significant_first_in_seat_order(self) -> None:
        self.assertEqual(state.met_bitmap([True, True, False, True]), b"\xd0")
        self.assertEqual(state.met_bitmap([]), b"")
        self.assertEqual(state.met_bitmap([False] * 8), b"\x00")
        self.assertEqual(state.met_bitmap([True] * 9), b"\xff\x80")

    def test_the_bitmap_is_one_bit_per_in_scope_seat(self) -> None:
        self.assertEqual(len(state.met_bitmap([True] * c.FOUNDER_SEAT_CAPACITY)), 12_500)


class EconomyTreeTest(unittest.TestCase):
    def test_the_empty_tree_is_a_labelled_constant(self) -> None:
        self.assertEqual(len(state.economy_root({})), 32)

    def test_the_root_tracks_every_entry(self) -> None:
        at_genesis = genesis.initial_economy_entries()
        populated = scenario.populated_economy()
        self.assertNotEqual(state.economy_root({}), state.economy_root(at_genesis))
        self.assertNotEqual(
            state.economy_root(at_genesis), state.economy_root(populated)
        )

    def test_the_root_is_independent_of_insertion_order(self) -> None:
        populated = scenario.populated_economy()
        reversed_order = dict(reversed(list(populated.items())))
        self.assertEqual(
            state.economy_root(populated), state.economy_root(reversed_order)
        )

    def test_changing_one_value_changes_the_root(self) -> None:
        populated = dict(scenario.populated_economy())
        expected = state.economy_root(populated)
        populated[state.performance_carry_key()] = state.performance_carry_value(1)
        self.assertNotEqual(state.economy_root(populated), expected)

    def test_the_leaf_preimage_length_prefixes_both_halves(self) -> None:
        """A key/value boundary inferred from the entry kind would be ambiguous."""
        leaf = state.entry_leaf(b"\x01\x02", b"\x03")
        self.assertEqual(leaf, b"\x00\x00\x00\x02\x01\x02\x00\x00\x00\x01\x03")


class StateRootTest(unittest.TestCase):
    def setUp(self) -> None:
        self.accounts = [(bytes([index]) * 32, 1_000 * (index + 1), 0) for index in range(3)]
        self.common = dict(
            chain_id=scenario.CHAIN_ID,
            height=7,
            supply_limit=5_699_395_010_000_000_000,
            total_supply=6_000,
            fee_pool_balance=0,
            accounts=self.accounts,
        )

    def test_a_version_one_and_a_version_two_root_never_collide(self) -> None:
        """A collision would be a version-one root reinterpreted as version two."""
        self.assertNotEqual(
            state.version_one_state_root(**self.common),
            state.state_root(**self.common, economy={}),
        )

    def test_the_root_tracks_the_economy(self) -> None:
        self.assertNotEqual(
            state.state_root(**self.common, economy={}),
            state.state_root(**self.common, economy=scenario.populated_economy()),
        )

    def test_unordered_accounts_are_refused(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.accounts_root(list(reversed(self.accounts)))


class GenesisTest(unittest.TestCase):
    def test_the_prefix_is_version_ones_plus_the_manifest_digest(self) -> None:
        self.assertEqual(c.GENESIS_PREFIX_BYTES, 46 + 32)
        self.assertEqual(len(genesis.encode(scenario.genesis())), c.GENESIS_PREFIX_BYTES)

    def test_the_object_bound_admits_one_fewer_account_than_version_one(self) -> None:
        self.assertEqual(c.MAX_GENESIS_ACCOUNTS, 21_843)
        self.assertEqual((c.MAX_OBJECT_BYTES - 46) // 48, 21_844)
        accepted = c.GENESIS_PREFIX_BYTES + 48 * c.MAX_GENESIS_ACCOUNTS
        self.assertLessEqual(accepted, c.MAX_OBJECT_BYTES)
        self.assertGreater(accepted + 48, c.MAX_OBJECT_BYTES)

    def test_the_three_relaxations_the_constitution_forces_are_accepted(self) -> None:
        founder = scenario.genesis()
        self.assertEqual(founder.total_supply, 0)
        self.assertEqual(founder.accounts, [])
        self.assertEqual(founder.fixed_transfer_fee, 0)
        genesis.require_valid(founder)

    def test_the_manifest_digest_is_inside_chain_identity(self) -> None:
        founder = scenario.genesis()
        drifted = genesis.Genesis(
            network_id=founder.network_id,
            supply_limit=founder.supply_limit,
            total_supply=founder.total_supply,
            fixed_transfer_fee=founder.fixed_transfer_fee,
            initial_fee_pool=founder.initial_fee_pool,
            manifest_digest=bytes(32),
            accounts=[],
        )
        self.assertNotEqual(genesis.chain_id(founder), genesis.chain_id(drifted))

    def test_an_unconserved_or_out_of_range_genesis_is_refused(self) -> None:
        founder = scenario.genesis()
        for changes in (
            {"supply_limit": 0},
            {"total_supply": 1},
            {"supply_limit": 10, "total_supply": 11},
        ):
            with self.subTest(changes):
                fields = dict(
                    network_id=founder.network_id,
                    supply_limit=founder.supply_limit,
                    total_supply=founder.total_supply,
                    fixed_transfer_fee=founder.fixed_transfer_fee,
                    initial_fee_pool=founder.initial_fee_pool,
                    manifest_digest=founder.manifest_digest,
                    accounts=[],
                )
                fields.update(changes)
                with self.assertRaises(genesis.InvalidGenesis):
                    genesis.encode(genesis.Genesis(**fields))

    def test_genesis_writes_the_channel_table_and_nothing_else(self) -> None:
        entries = genesis.initial_economy_entries()
        self.assertEqual(len(entries), 11)
        kinds = {key[0] for key in entries}
        self.assertEqual(kinds, {c.CHANNEL_ENTRY, c.PERFORMANCE_CARRY_ENTRY})
        for key, value in entries.items():
            if key[0] == c.CHANNEL_ENTRY:
                self.assertEqual(value, state.channel_value(0, 0))


if __name__ == "__main__":
    unittest.main()
