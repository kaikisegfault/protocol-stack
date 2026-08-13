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
            c.CYCLE_ASSIGNMENT_ENTRY: state.cycle_assignment_key(scenario.CYCLE_WINDOW),
            c.REFERRAL_BALANCE_ENTRY: state.referral_balance_key(
                scenario.REFERRER_ACCOUNT_ID
            ),
            c.DIRECT_DECISION_ENTRY: state.direct_decision_key(scenario.DECISION_ID),
            c.TYPED_CUSTODY_ENTRY: state.typed_custody_key(
                1, scenario.BENEFICIARY_ACCOUNT_ID
            ),
            c.CARRY_ENTRY: state.carry_key(0),
            c.VERIFIER_KEY_ENTRY: state.verifier_key_key(),
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

    def test_keys_of_different_kinds_never_collide(self) -> None:
        self.assertNotEqual(state.seat_key(0), state.seat_key(1))
        self.assertNotEqual(state.channel_key(0), state.carry_key(0))
        self.assertNotEqual(
            state.cycle_assignment_key(0), state.cycle_assignment_key(1)
        )
        self.assertNotEqual(
            state.direct_decision_key(scenario.DECISION_ID),
            state.referral_balance_key(scenario.DECISION_ID),
        )

    def test_no_entry_is_keyed_by_seat_cycle(self) -> None:
        """A mint takes everything, so the seat-cycle population is not state.

        The superseded draft stored one verdict byte per seat-cycle, which is
        73,100,000 entries at capacity. One high-water mark per seat replaces it.
        """
        seat_cycle_width = 1 + 4 + 2
        for kind, width in c.ENTRY_KEY_BYTES.items():
            with self.subTest(c.ENTRY_KINDS[kind]):
                self.assertNotEqual(
                    (kind, width),
                    (kind, seat_cycle_width),
                    "an entry keyed by (seat, cycle) has returned",
                )

    def test_a_value_of_the_wrong_width_is_refused(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.economy_root({state.seat_key(0): b"\x00"})
        with self.assertRaises(state.InvalidStateEntry):
            state.economy_root({b"\x63\x00": b""})

    def test_the_seat_record_carries_identity_from_its_first_byte(self) -> None:
        """A seat with no biometric binding is unrepresentable, not disallowed."""
        value = state.seat_value(
            scenario.BIOMETRIC_IDENTITY_HASH, scenario.PURCHASER_ACCOUNT_ID, None
        )
        self.assertEqual(len(value), c.ENTRY_VALUE_BYTES[c.SEAT_ENTRY])
        self.assertEqual(value[0:32], scenario.BIOMETRIC_IDENTITY_HASH)
        self.assertEqual(value[32:64], scenario.PURCHASER_ACCOUNT_ID)

    def test_activation_is_a_flag_rather_than_an_inferred_sentinel(self) -> None:
        """Height zero is a real height, so "not activated" needs its own bit."""
        purchased = state.seat_value(
            scenario.BIOMETRIC_IDENTITY_HASH, scenario.PURCHASER_ACCOUNT_ID, None
        )
        at_genesis_height = state.seat_value(
            scenario.BIOMETRIC_IDENTITY_HASH,
            scenario.PURCHASER_ACCOUNT_ID,
            None,
            activation_height=0,
        )
        self.assertNotEqual(purchased, at_genesis_height)
        self.assertEqual(purchased[97], 0)
        self.assertEqual(at_genesis_height[97], 1)

    def test_a_referrer_cannot_have_minted_more_than_it_accrued(self) -> None:
        state.referral_balance_value(10, 10)
        with self.assertRaises(state.InvalidStateEntry):
            state.referral_balance_value(10, 11)


class BitmapTest(unittest.TestCase):
    def test_bits_are_packed_most_significant_first_in_seat_order(self) -> None:
        self.assertEqual(state.bitmap([True, True, False, True]), b"\xd0")
        self.assertEqual(state.bitmap([]), b"")
        self.assertEqual(state.bitmap([False] * 8), b"\x00")
        self.assertEqual(state.bitmap([True] * 9), b"\xff\x80")

    def test_the_bitmap_is_one_bit_per_in_scope_seat(self) -> None:
        self.assertEqual(len(state.bitmap([True] * c.FOUNDER_SEAT_CAPACITY)), 12_500)

    def test_reading_a_bit_inverts_writing_it(self) -> None:
        flags = [True, False, True, True, False, False, False, True, True]
        packed = state.bitmap(flags)
        for index, flag in enumerate(flags):
            with self.subTest(index):
                self.assertEqual(state.bit_is_set(packed, index), flag)

    def test_a_bit_outside_the_bitmap_is_refused(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.bit_is_set(state.bitmap([True]), 8)

    def test_the_two_bitmaps_must_cover_the_same_seat_set(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.cycle_assignment_value(1, 1, 9, state.bitmap([True]), b"")


class EconomyTreeTest(unittest.TestCase):
    def test_the_empty_tree_is_a_labelled_constant(self) -> None:
        self.assertEqual(len(state.economy_root({})), 32)

    def test_the_root_tracks_every_entry(self) -> None:
        at_genesis = genesis.initial_economy_entries(scenario.VERIFIER_KEY)
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
        populated[state.carry_key(0)] = state.carry_value(1)
        self.assertNotEqual(state.economy_root(populated), expected)

    def test_the_leaf_preimage_length_prefixes_both_halves(self) -> None:
        """A key/value boundary inferred from the entry kind would be ambiguous."""
        leaf = state.entry_leaf(b"\x01\x02", b"\x03")
        self.assertEqual(leaf, b"\x00\x00\x00\x02\x01\x02\x00\x00\x00\x01\x03")


class VersionOneRestatementTest(unittest.TestCase):
    """The version-one root restatement must be the accepted one, not a lookalike.

    The non-collision test below compares a version-two root against this
    module's version-one construction. If that construction were merely
    plausible rather than correct, "the roots differ" would be trivially true
    and would prove nothing.
    """

    def setUp(self) -> None:
        path = (
            Path(__file__).resolve().parents[2]
            / "test-vectors"
            / "protocol-primitives-v1.txt"
        )
        self.accepted = {}
        for line in path.read_text(encoding="ascii").splitlines():
            name, separator, value = line.partition("=")
            if separator:
                self.accepted[name] = value
        self.accounts = [
            (
                bytes.fromhex(entry[0:64]),
                int(entry[64:80], 16),
                int(entry[80:96], 16),
            )
            for entry in (self.accepted[f"state.account{i}"] for i in range(3))
        ]

    def test_the_accounts_tree_reproduces_the_accepted_roots(self) -> None:
        self.assertEqual(
            state.accounts_root([]).hex(), self.accepted["state.empty_tree_root"]
        )
        self.assertEqual(
            state.accounts_root(self.accounts).hex(),
            self.accepted["state.accounts_tree_root"],
        )

    def test_the_version_one_state_root_reproduces_the_accepted_root(self) -> None:
        self.assertEqual(
            state.version_one_state_root(
                chain_id=bytes.fromhex(self.accepted["chain_id"]),
                height=int(self.accepted["state.height"]),
                supply_limit=int(self.accepted["state.supply_limit"]),
                total_supply=int(self.accepted["state.total_supply"]),
                fee_pool_balance=int(self.accepted["state.fee_pool_balance"]),
                accounts=self.accounts,
            ),
            self.accepted["state.root"],
        )

    def test_the_merkle_shape_reproduces_the_accepted_transaction_root(self) -> None:
        """The same construction under other labels, checked independently."""
        from simulation.economy_transition.merkle import root as merkle_root

        items = [bytes.fromhex(self.accepted[f"tx.item{i}"]) for i in range(3)]
        self.assertEqual(
            merkle_root(items, "protocol-stack:v1:tx").hex(), self.accepted["tx.root"]
        )
        self.assertEqual(
            merkle_root([], "protocol-stack:v1:tx").hex(), self.accepted["tx.empty_root"]
        )


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
    def test_the_prefix_is_version_ones_plus_two_thirty_two_byte_fields(self) -> None:
        self.assertEqual(c.GENESIS_PREFIX_BYTES, 46 + 32 + 32)
        self.assertEqual(len(genesis.encode(scenario.genesis())), c.GENESIS_PREFIX_BYTES)

    def test_the_object_bound_admits_one_fewer_account_than_version_one(self) -> None:
        self.assertEqual(c.MAX_GENESIS_ACCOUNTS, 21_843)
        self.assertEqual((c.MAX_OBJECT_BYTES - 46) // 48, 21_844)
        accepted = c.GENESIS_PREFIX_BYTES + 48 * c.MAX_GENESIS_ACCOUNTS
        self.assertLessEqual(accepted, c.MAX_OBJECT_BYTES)
        self.assertGreater(accepted + 48, c.MAX_OBJECT_BYTES)
        # Version two adds 64 bytes and loses exactly one entry, clearing the
        # bound by two.
        self.assertEqual(c.MAX_OBJECT_BYTES - accepted, 2)

    def test_the_three_relaxations_the_constitution_forces_are_accepted(self) -> None:
        founder = scenario.genesis()
        self.assertEqual(founder.total_supply, 0)
        self.assertEqual(founder.accounts, [])
        self.assertEqual(founder.fixed_transfer_fee, 0)
        genesis.require_valid(founder)

    def test_the_manifest_digest_is_inside_chain_identity(self) -> None:
        founder = scenario.genesis()
        drifted = self.variant(founder, manifest_digest=bytes(32))
        self.assertNotEqual(genesis.chain_id(founder), genesis.chain_id(drifted))

    def test_an_unconserved_or_out_of_range_genesis_is_refused(self) -> None:
        founder = scenario.genesis()
        for changes in (
            {"supply_limit": 0},
            {"total_supply": 1},
            {"supply_limit": 10, "total_supply": 11},
        ):
            with self.subTest(changes):
                with self.assertRaises(genesis.InvalidGenesis):
                    genesis.encode(self.variant(founder, **changes))

    def test_genesis_writes_the_fixed_tables_and_nothing_else(self) -> None:
        entries = genesis.initial_economy_entries(scenario.VERIFIER_KEY)
        self.assertEqual(len(entries), 21)
        kinds = {key[0] for key in entries}
        self.assertEqual(
            kinds, {c.CHANNEL_ENTRY, c.CARRY_ENTRY, c.VERIFIER_KEY_ENTRY}
        )
        for key, value in entries.items():
            if key[0] == c.CHANNEL_ENTRY:
                self.assertEqual(value, state.channel_value(0, 0))
            if key[0] == c.CARRY_ENTRY:
                self.assertEqual(value, state.carry_value(0))

    def test_the_verifier_key_is_inside_chain_identity(self) -> None:
        """A chain trusting a different verifier is a different chain."""
        founder = scenario.genesis()
        drifted = self.variant(founder, verifier_key=bytes(32))
        self.assertNotEqual(genesis.chain_id(founder), genesis.chain_id(drifted))

    def variant(self, founder: genesis.Genesis, **changes: object) -> genesis.Genesis:
        fields = dict(
            network_id=founder.network_id,
            supply_limit=founder.supply_limit,
            total_supply=founder.total_supply,
            fixed_transfer_fee=founder.fixed_transfer_fee,
            initial_fee_pool=founder.initial_fee_pool,
            manifest_digest=founder.manifest_digest,
            verifier_key=founder.verifier_key,
            accounts=list(founder.accounts),
        )
        fields.update(changes)
        return genesis.Genesis(**fields)


if __name__ == "__main__":
    unittest.main()
