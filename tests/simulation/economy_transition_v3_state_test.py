#!/usr/bin/env python3
"""The version-three economy state: keys, values, the tree, roots, and genesis."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v3 import contract as c
from simulation.economy_transition_v3 import genesis, scenario, state

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VECTORS = REPOSITORY_ROOT / "test-vectors"


def recorded(path: Path, key: str) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if separator and name == key:
            return value
    raise AssertionError(f"{key} is not recorded in {path.name}")


class KeySpaceTest(unittest.TestCase):
    def test_every_entry_kind_has_a_fixed_key_width(self) -> None:
        self.assertEqual(sorted(c.ENTRY_KINDS), list(range(1, 12)))
        for kind in c.ENTRY_KINDS:
            with self.subTest(kind):
                self.assertIn(kind, c.ENTRY_KEY_BYTES)
                self.assertIn(kind, c.ENTRY_VALUE_BYTES)

    def test_no_key_is_a_prefix_of_another(self) -> None:
        keys = sorted(scenario.populated_economy())
        for index, earlier in enumerate(keys):
            for later in keys[index + 1 :]:
                with self.subTest(earlier=earlier.hex(), later=later.hex()):
                    self.assertFalse(later.startswith(earlier))

    def test_the_populated_fixture_covers_every_entry_kind(self) -> None:
        present = {key[0] for key in scenario.populated_economy()}
        self.assertEqual(present, set(c.ENTRY_KINDS))

    def test_no_key_names_a_seat_and_a_cycle_at_once(self) -> None:
        """A per-seat-cycle entry would have to, and none does."""
        seat_keyed = {c.SEAT_ENTRY, c.SEAT_MANAGER_ENTRY}
        cycle_keyed = {c.CYCLE_ASSIGNMENT_ENTRY}
        self.assertEqual(seat_keyed & cycle_keyed, set())

    def test_entries_are_ordered_and_validated(self) -> None:
        entries = scenario.populated_economy()
        ordered = state.ordered_entries(entries)
        self.assertEqual([key for key, _ in ordered], sorted(entries))

    def test_an_unknown_entry_kind_is_refused(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.ordered_entries({b"\x0c\x00": b""})

    def test_a_value_of_the_wrong_width_is_refused(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.ordered_entries({state.channel_key(0): b"\x00"})


class SeatRecordTest(unittest.TestCase):
    def test_the_record_is_one_hundred_and_nineteen_bytes(self) -> None:
        value = state.seat_value(
            scenario.BIOMETRIC_IDENTITY_HASH, scenario.PURCHASER_ACCOUNT_ID, None
        )
        self.assertEqual(len(value), 119)
        self.assertEqual(len(value), c.ENTRY_VALUE_BYTES[c.SEAT_ENTRY])

    def test_an_unactivated_seat_carries_height_zero_and_a_clear_flag(self) -> None:
        value = state.seat_value(
            scenario.BIOMETRIC_IDENTITY_HASH, scenario.PURCHASER_ACCOUNT_ID, None
        )
        self.assertEqual(value[96], 0)
        self.assertEqual(value[97:105], bytes(8))

    def test_protection_is_off_by_default(self) -> None:
        value = state.seat_value(
            scenario.BIOMETRIC_IDENTITY_HASH, scenario.PURCHASER_ACCOUNT_ID, None
        )
        self.assertEqual(value[113], 0)

    def test_the_manager_count_is_bounded_in_both_directions(self) -> None:
        for count in (0, c.MAX_SEAT_MANAGERS + 1):
            with self.subTest(count):
                with self.assertRaises(state.InvalidStateEntry):
                    state.seat_value(
                        scenario.BIOMETRIC_IDENTITY_HASH,
                        scenario.PURCHASER_ACCOUNT_ID,
                        None,
                        manager_count=count,
                    )
        state.seat_value(
            scenario.BIOMETRIC_IDENTITY_HASH,
            scenario.PURCHASER_ACCOUNT_ID,
            None,
            manager_count=c.MAX_SEAT_MANAGERS,
        )

    def test_a_manager_entry_carries_nothing_but_its_presence(self) -> None:
        self.assertEqual(state.seat_manager_value(), b"")
        self.assertEqual(
            len(state.seat_manager_key(0, scenario.MANAGER_ACCOUNT_ID)),
            c.ENTRY_KEY_BYTES[c.SEAT_MANAGER_ENTRY],
        )


class BeneficiaryTest(unittest.TestCase):
    def test_a_singleton_beneficiary_takes_a_zero_identifier(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.typed_custody_key(
                c.VENTURE_ESCROW_BENEFICIARY, scenario.BENEFICIARY_ACCOUNT_ID
            )
        state.typed_custody_key(
            c.VENTURE_ESCROW_BENEFICIARY, c.SINGLETON_BENEFICIARY_ID
        )

    def test_a_named_beneficiary_is_only_the_direct_kind(self) -> None:
        state.typed_custody_key(
            c.DIRECT_BENEFICIARY, scenario.BENEFICIARY_ACCOUNT_ID
        )

    def test_an_unknown_beneficiary_kind_is_refused(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.typed_custody_key(6, bytes(32))

    def test_a_founder_seat_is_not_a_beneficiary_kind(self) -> None:
        """Minted value lands in an account balance, not in typed custody."""
        self.assertNotIn("founder_seat", c.BENEFICIARY_KINDS.values())
        self.assertNotIn("recorded_referrer", c.BENEFICIARY_KINDS.values())
        self.assertIsNone(c.LEG_BENEFICIARY_KIND[c.FOUNDER_OPERATOR_CHANNEL])


class ReferralBalanceTest(unittest.TestCase):
    def test_the_balance_carries_its_own_accumulation_mark(self) -> None:
        value = state.referral_balance_value(10, 4, 77)
        self.assertEqual(len(value), 24)
        self.assertEqual(int.from_bytes(value[16:24], "big"), 77)

    def test_minting_more_than_accrued_is_refused(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.referral_balance_value(1, 2, 0)
        with self.assertRaises(state.InvalidStateEntry):
            state.unreferred_pool_value(1, 2)


class CycleAssignmentValueTest(unittest.TestCase):
    def test_the_value_length_follows_from_the_bit_count(self) -> None:
        for bits in (0, 1, 8, 9, 24, 100_000):
            with self.subTest(bits):
                width = state.bitmap_bytes(bits)
                value = state.cycle_assignment_value(
                    1, 2, 3, 4, bits, bytes(width), bytes(width)
                )
                self.assertEqual(len(value), 24 + 2 * width)

    def test_a_bitmap_of_the_wrong_width_is_refused(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.cycle_assignment_value(1, 2, 3, 4, 24, bytes(3), bytes(2))

    def test_a_length_disagreeing_with_its_bit_count_is_refused(self) -> None:
        value = bytearray(
            state.cycle_assignment_value(1, 2, 3, 4, 24, bytes(3), bytes(3))
        )
        value[20:24] = (25).to_bytes(4, "big")
        with self.assertRaises(state.InvalidStateEntry):
            state.decode_cycle_assignment_value(bytes(value))

    def test_bits_are_addressed_by_seat_identifier(self) -> None:
        packed = state.bitmap([0, 7, 8, 23], 24)
        self.assertEqual(packed.hex(), "818001")
        for seat in (0, 7, 8, 23):
            self.assertTrue(state.bit_is_set(packed, seat))
        for seat in (1, 6, 9, 22):
            self.assertFalse(state.bit_is_set(packed, seat))

    def test_a_seat_beyond_the_bitmap_reads_clear(self) -> None:
        packed = state.bitmap([0], 8)
        self.assertFalse(state.bit_is_set(packed, 8))
        self.assertFalse(state.bit_is_set(packed, 100_000))

    def test_a_seat_outside_the_bitmap_cannot_be_set(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.bitmap([8], 8)

    def test_the_record_round_trips(self) -> None:
        from simulation.economy_transition_v3 import settlement

        assignment = settlement.derive_assignment(
            scenario.CYCLE_WINDOW, scenario.cycle_seats()
        )
        _, value = settlement.assignment_entry(assignment)
        decoded = state.decode_cycle_assignment_value(value)
        self.assertEqual(decoded["winner_count"], assignment.winner_count)
        self.assertEqual(
            decoded["reallocated_count"], assignment.reallocated_count
        )
        self.assertEqual(decoded["bitmap_bits"], assignment.bitmap_bits)


class TreeAndRootTest(unittest.TestCase):
    def setUp(self) -> None:
        self.accounts = [
            (bytes([index]) * 32, 1_000 * (index + 1), 0) for index in range(3)
        ]
        self.common = dict(
            chain_id=scenario.CHAIN_ID,
            height=7,
            supply_limit=5_699_395_010_000_000_000,
            total_supply=6_000,
            fee_pool_balance=0,
            accounts=self.accounts,
        )

    def test_all_three_state_roots_differ_on_identical_accounts(self) -> None:
        """Distinct labels are strings rather than a chain, so both are proved."""
        three = state.state_root(**self.common, economy={})
        two = state.version_two_state_root(**self.common)
        one = state.version_one_state_root(**self.common)
        self.assertEqual(len({one, two, three}), 3)

    def test_the_version_one_restatement_matches_the_accepted_vectors(self) -> None:
        path = VECTORS / "protocol-primitives-v1.txt"
        entries = [recorded(path, f"state.account{index}") for index in range(3)]
        accounts = [
            (bytes.fromhex(e[0:64]), int(e[64:80], 16), int(e[80:96], 16))
            for e in entries
        ]
        self.assertEqual(
            state.accounts_root(accounts).hex(), recorded(path, "state.accounts_tree_root")
        )
        self.assertEqual(
            state.version_one_state_root(
                chain_id=bytes.fromhex(recorded(path, "chain_id")),
                height=int(recorded(path, "state.height")),
                supply_limit=int(recorded(path, "state.supply_limit")),
                total_supply=int(recorded(path, "state.total_supply")),
                fee_pool_balance=int(recorded(path, "state.fee_pool_balance")),
                accounts=accounts,
            ),
            recorded(path, "state.root"),
        )

    def test_the_version_two_restatement_matches_the_accepted_vectors(self) -> None:
        """A non-collision claim is worthless if the predecessor is a lookalike."""
        path = VECTORS / "economy-transition-v2.txt"
        self.assertEqual(
            state.version_two_state_root(**self.common),
            recorded(path, "state.root_empty_economy"),
        )

    def test_the_economy_root_tracks_its_entries(self) -> None:
        empty = state.economy_root({})
        at_genesis = state.economy_root(
            genesis.initial_economy_entries(scenario.VERIFIER_KEY)
        )
        populated = state.economy_root(scenario.populated_economy())
        self.assertEqual(len({empty, at_genesis, populated}), 3)

    def test_the_root_tracks_the_economy(self) -> None:
        self.assertNotEqual(
            state.state_root(**self.common, economy={}),
            state.state_root(**self.common, economy=scenario.populated_economy()),
        )


class GenesisTest(unittest.TestCase):
    def setUp(self) -> None:
        self.founder = scenario.genesis()

    def test_the_prefix_and_account_bound_are_version_twos(self) -> None:
        self.assertEqual(c.GENESIS_PREFIX_BYTES, 110)
        self.assertEqual(c.MAX_GENESIS_ACCOUNTS, 21_843)
        accepted = (
            c.GENESIS_PREFIX_BYTES + c.ACCOUNT_ENTRY_BYTES * c.MAX_GENESIS_ACCOUNTS
        )
        self.assertLessEqual(accepted, c.MAX_OBJECT_BYTES)
        self.assertGreater(accepted + c.ACCOUNT_ENTRY_BYTES, c.MAX_OBJECT_BYTES)

    def test_the_three_forced_relaxations_are_accepted_together(self) -> None:
        self.assertEqual(self.founder.total_supply, 0)
        self.assertEqual(self.founder.accounts, [])
        self.assertEqual(self.founder.fixed_transfer_fee, 0)
        genesis.encode(self.founder)

    def test_the_chain_id_differs_from_a_version_two_chain(self) -> None:
        """The same fields under two schemas are two chains, not one."""
        self.assertNotEqual(
            genesis.chain_id(self.founder),
            genesis.version_two_chain_id(self.founder),
        )

    def test_the_verifier_key_and_manifest_digest_are_inside_the_chain_id(self) -> None:
        for change in ({"verifier_key": bytes(32)}, {"manifest_digest": bytes(32)}):
            with self.subTest(change):
                fields = dict(
                    network_id=self.founder.network_id,
                    supply_limit=self.founder.supply_limit,
                    total_supply=self.founder.total_supply,
                    fixed_transfer_fee=self.founder.fixed_transfer_fee,
                    initial_fee_pool=self.founder.initial_fee_pool,
                    manifest_digest=self.founder.manifest_digest,
                    verifier_key=self.founder.verifier_key,
                    accounts=[],
                )
                fields.update(change)
                self.assertNotEqual(
                    genesis.chain_id(genesis.Genesis(**fields)),
                    genesis.chain_id(self.founder),
                )

    def test_genesis_writes_the_fixed_tables_and_nothing_else(self) -> None:
        entries = genesis.initial_economy_entries(scenario.VERIFIER_KEY)
        kinds = {key[0] for key in entries}
        self.assertEqual(
            kinds, {c.CHANNEL_ENTRY, c.CARRY_ENTRY, c.VERIFIER_KEY_ENTRY,
                    c.UNREFERRED_POOL_ENTRY}
        )
        self.assertEqual(len(entries), 22)

    def test_invalid_genesis_is_refused(self) -> None:
        def variant(**changes: object) -> genesis.Genesis:
            fields = dict(
                network_id=self.founder.network_id,
                supply_limit=self.founder.supply_limit,
                total_supply=self.founder.total_supply,
                fixed_transfer_fee=self.founder.fixed_transfer_fee,
                initial_fee_pool=self.founder.initial_fee_pool,
                manifest_digest=self.founder.manifest_digest,
                verifier_key=self.founder.verifier_key,
                accounts=[],
            )
            fields.update(changes)
            return genesis.Genesis(**fields)  # type: ignore[arg-type]

        cases = {
            "zero_supply_limit": variant(supply_limit=0),
            "supply_above_limit": variant(supply_limit=10, total_supply=11),
            "unconserved_supply": variant(total_supply=1),
            "zero_balance": variant(accounts=[(bytes(32), 0, 0)]),
        }
        for name, candidate in cases.items():
            with self.subTest(name):
                with self.assertRaises(genesis.InvalidGenesis):
                    genesis.encode(candidate)


if __name__ == "__main__":
    unittest.main()
