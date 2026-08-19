#!/usr/bin/env python3
"""Version seven's state surface: the pool entry, the extended record, refusals.

The vector file fixes the widths and one encoded value of each. This module
covers what a fixed vector cannot: the shapes the encoders must refuse, the
orderings the tree must produce, and the entries version seven inherits
untouched.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v6 import state as v6_state
from simulation.economy_transition_v7 import contract as c
from simulation.economy_transition_v7 import genesis as g
from simulation.economy_transition_v7 import settlement as t
from simulation.economy_transition_v7 import state as s

LEGS = c.RECOVERY_POOL_LEGS


def pool(**overrides: int) -> dict[int, int]:
    values = {channel: 0 for channel in LEGS}
    values.update({int(key[2:]): amount for key, amount in overrides.items()})
    return values


class RecoveryPoolEntryTest(unittest.TestCase):
    def test_the_key_is_one_octet(self) -> None:
        self.assertEqual(s.recovery_pool_key(), bytes([c.RECOVERY_POOL_ENTRY]))
        self.assertEqual(c.ENTRY_KEY_BYTES[c.RECOVERY_POOL_ENTRY], 1)

    def test_the_value_is_five_big_endian_legs_in_channel_order(self) -> None:
        values = {channel: 1000 + channel for channel in LEGS}
        encoded = s.recovery_pool_value(values)
        self.assertEqual(len(encoded), 40)
        for index, channel in enumerate(LEGS):
            self.assertEqual(
                int.from_bytes(encoded[8 * index : 8 * index + 8], "big"),
                values[channel],
            )

    def test_decoding_round_trips(self) -> None:
        values = {channel: (channel + 1) * 7 for channel in LEGS}
        self.assertEqual(
            s.decode_recovery_pool_value(s.recovery_pool_value(values)), values
        )

    def test_a_leg_at_the_u64_maximum_encodes(self) -> None:
        values = {channel: c.MAX_U64 for channel in LEGS}
        self.assertEqual(
            s.decode_recovery_pool_value(s.recovery_pool_value(values)), values
        )

    def test_a_leg_above_u64_is_refused(self) -> None:
        values = {channel: 0 for channel in LEGS}
        values[0] = c.MAX_U64 + 1
        with self.assertRaises(Exception):
            s.recovery_pool_value(values)

    def test_a_negative_leg_is_refused(self) -> None:
        values = {channel: 0 for channel in LEGS}
        values[2] = -1
        with self.assertRaises(Exception):
            s.recovery_pool_value(values)

    def test_a_missing_or_extra_leg_is_refused(self) -> None:
        with self.assertRaises(s.InvalidStateEntry):
            s.recovery_pool_value({0: 0, 1: 0})
        with self.assertRaises(s.InvalidStateEntry):
            s.recovery_pool_value({channel: 0 for channel in LEGS} | {9: 0})

    def test_a_value_of_the_wrong_width_is_refused(self) -> None:
        for width in (0, 39, 41, 48):
            with self.assertRaises(s.InvalidStateEntry):
                s.decode_recovery_pool_value(bytes(width))


class CycleAssignmentRecordTest(unittest.TestCase):
    def test_the_fixed_part_grew_by_exactly_five_legs(self) -> None:
        from simulation.economy_transition_v6 import contract as v6

        self.assertEqual(
            c.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES,
            v6.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES + 8 * len(LEGS),
        )

    def test_the_absorbed_amounts_sit_after_the_bit_count(self) -> None:
        absorbed = {channel: channel + 1 for channel in LEGS}
        value = s.cycle_assignment_value(1, 1, 2, 3, 8, absorbed, b"\x80", b"\x40")
        self.assertEqual(int.from_bytes(value[20:24], "big"), 8)
        for index, channel in enumerate(LEGS):
            self.assertEqual(
                int.from_bytes(value[24 + 8 * index : 32 + 8 * index], "big"),
                absorbed[channel],
            )

    def test_the_bitmaps_follow_the_fixed_part(self) -> None:
        absorbed = {channel: 0 for channel in LEGS}
        value = s.cycle_assignment_value(0, 0, 1, 1, 16, absorbed, b"\x80\x01", b"\x40\x02")
        fixed = c.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES
        self.assertEqual(value[fixed : fixed + 2], b"\x80\x01")
        self.assertEqual(value[fixed + 2 : fixed + 4], b"\x40\x02")

    def test_round_tripping_recovers_every_field(self) -> None:
        absorbed = {channel: 9 * (channel + 1) for channel in LEGS}
        value = s.cycle_assignment_value(5, 6, 7, 8, 24, absorbed, bytes(3), bytes(3))
        decoded = s.decode_cycle_assignment_value(value)
        self.assertEqual(decoded["share_per_winner_atomic"], 5)
        self.assertEqual(decoded["reallocated_count"], 6)
        self.assertEqual(decoded["winner_count"], 7)
        self.assertEqual(decoded["in_scope_count"], 8)
        self.assertEqual(decoded["bitmap_bits"], 24)
        self.assertEqual(decoded["pool_absorbed"], absorbed)

    def test_a_zero_winner_record_may_not_absorb(self) -> None:
        absorbed = {channel: 0 for channel in LEGS}
        absorbed[0] = 1
        with self.assertRaises(s.InvalidStateEntry):
            s.cycle_assignment_value(0, 1, 0, 1, 8, absorbed, bytes(1), bytes(1))

    def test_a_zero_winner_record_with_no_absorption_is_accepted(self) -> None:
        absorbed = {channel: 0 for channel in LEGS}
        value = s.cycle_assignment_value(0, 1, 0, 1, 8, absorbed, bytes(1), bytes(1))
        self.assertEqual(s.decode_cycle_assignment_value(value)["winner_count"], 0)

    def test_a_decoded_zero_winner_absorption_is_refused(self) -> None:
        absorbed = {channel: 3 for channel in LEGS}
        value = s.cycle_assignment_value(1, 1, 4, 1, 8, absorbed, bytes(1), bytes(1))
        tampered = value[:12] + (0).to_bytes(4, "big") + value[16:]
        with self.assertRaises(s.InvalidStateEntry):
            s.decode_cycle_assignment_value(tampered)

    def test_a_length_that_disagrees_with_the_bit_count_is_refused(self) -> None:
        absorbed = {channel: 0 for channel in LEGS}
        value = s.cycle_assignment_value(0, 0, 0, 0, 8, absorbed, bytes(1), bytes(1))
        with self.assertRaises(s.InvalidStateEntry):
            s.decode_cycle_assignment_value(value + b"\x00")
        with self.assertRaises(s.InvalidStateEntry):
            s.decode_cycle_assignment_value(value[:-1])

    def test_a_version_six_record_is_too_short(self) -> None:
        """A version-six record is 40 octets short in its fixed part."""
        six = v6_state.cycle_assignment_value(0, 0, 0, 0, 8, bytes(1), bytes(1))
        self.assertEqual(len(six), 24 + 2)
        with self.assertRaises(s.InvalidStateEntry):
            s.decode_cycle_assignment_value(six)


class EntryShapeTest(unittest.TestCase):
    def test_a_retired_kind_is_refused(self) -> None:
        for kind in c.RETIRED_ENTRY_KINDS:
            with self.assertRaises(s.InvalidStateEntry):
                s.ordered_entries({bytes([kind, 0]): bytes(8)})

    def test_an_unassigned_kind_is_refused(self) -> None:
        for kind in (0, 18, 200, 255):
            with self.assertRaises(s.InvalidStateEntry):
                s.ordered_entries({bytes([kind]): b""})

    def test_an_empty_key_is_refused(self) -> None:
        with self.assertRaises(s.InvalidStateEntry):
            s.ordered_entries({b"": b""})

    def test_entries_are_ordered_by_unsigned_key(self) -> None:
        entries = g.initial_economy_entries(bytes(32))
        keys = [key for key, _value in s.ordered_entries(entries)]
        self.assertEqual(keys, sorted(keys))

    def test_the_pool_key_sorts_after_every_other_genesis_key(self) -> None:
        entries = g.initial_economy_entries(bytes(32))
        keys = [key for key, _value in s.ordered_entries(entries)]
        self.assertEqual(keys[-1], s.recovery_pool_key())


class GenesisTest(unittest.TestCase):
    def setUp(self) -> None:
        self.genesis = g.Genesis(
            network_id=7,
            supply_limit=5_699_395_010_000_000_000,
            fixed_transfer_fee=100_000,
            manifest_digest=bytes.fromhex(c.MANIFEST_DIGEST_HEX),
            verifier_key=bytes(range(32)),
        )

    def test_it_writes_fourteen_economy_entries(self) -> None:
        entries = g.initial_economy_entries(self.genesis.verifier_key)
        self.assertEqual(len(entries), 14)

    def test_the_recovery_pool_opens_empty(self) -> None:
        entries = g.initial_economy_entries(self.genesis.verifier_key)
        self.assertEqual(
            s.decode_recovery_pool_value(entries[s.recovery_pool_key()]),
            t.empty_pool(),
        )

    def test_it_writes_no_carry_entry(self) -> None:
        entries = g.initial_economy_entries(self.genesis.verifier_key)
        self.assertFalse(any(key[0] == 7 for key in entries))

    def test_the_prefix_is_unchanged_at_110_octets(self) -> None:
        self.assertEqual(len(g.encode(self.genesis)), 110)

    def test_the_schema_version_is_seven(self) -> None:
        raw = g.encode(self.genesis)
        self.assertEqual(int.from_bytes(raw[4:6], "big"), 7)

    def test_the_chain_id_differs_from_every_predecessor(self) -> None:
        current = g.chain_id(self.genesis)
        for version in (2, 3, 4, 5, 6):
            self.assertNotEqual(g.predecessor_chain_id(self.genesis, version), current)

    def test_a_genesis_account_is_refused(self) -> None:
        from dataclasses import replace

        with self.assertRaises(Exception):
            g.encode(replace(self.genesis, accounts=[(bytes(32), 0, 0)]))

    def test_a_nonzero_fee_pool_is_refused(self) -> None:
        from dataclasses import replace

        with self.assertRaises(g.InvalidGenesis):
            g.encode(replace(self.genesis, initial_fee_pool=1))


class StateRootTest(unittest.TestCase):
    def setUp(self) -> None:
        self.chain_id = bytes(range(32))
        self.entries = g.initial_economy_entries(bytes(32))

    def test_it_differs_from_every_predecessor_over_identical_input(self) -> None:
        current = s.state_root(self.chain_id, 0, 1, 0, 0, [], self.entries)
        for version in (1, 2, 3, 4, 5, 6):
            self.assertNotEqual(
                s.predecessor_state_root(
                    version, self.chain_id, 0, 1, 0, 0, [], self.entries
                ),
                current,
            )

    def test_the_pool_balance_reaches_the_root(self) -> None:
        moved = dict(self.entries)
        moved[s.recovery_pool_key()] = s.recovery_pool_value(pool(ch4=1))
        self.assertNotEqual(
            s.state_root(self.chain_id, 0, 1, 0, 0, [], self.entries),
            s.state_root(self.chain_id, 0, 1, 0, 0, [], moved),
        )

    def test_transposed_pool_legs_reach_the_root(self) -> None:
        left = dict(self.entries)
        right = dict(self.entries)
        left[s.recovery_pool_key()] = s.recovery_pool_value(pool(ch0=1, ch1=2))
        right[s.recovery_pool_key()] = s.recovery_pool_value(pool(ch0=2, ch1=1))
        self.assertNotEqual(
            s.state_root(self.chain_id, 0, 1, 0, 0, [], left),
            s.state_root(self.chain_id, 0, 1, 0, 0, [], right),
        )


if __name__ == "__main__":
    unittest.main()
