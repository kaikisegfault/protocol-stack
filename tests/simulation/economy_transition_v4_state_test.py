#!/usr/bin/env python3
"""The version-four state: keys, values, the tree, four-way roots, and genesis."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v4 import contract as c
from simulation.economy_transition_v4 import genesis, scenario, state

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VECTORS = REPOSITORY_ROOT / "test-vectors"


def recorded(path: Path, key: str) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if separator and name == key:
            return value
    raise AssertionError(f"{key} is not recorded in {path.name}")


ACCOUNTS = [(bytes([index]) * 32, 1_000 * (index + 1), 0) for index in range(3)]
COMMON = dict(
    chain_id=scenario.CHAIN_ID,
    height=7,
    supply_limit=5_699_395_010_000_000_000,
    total_supply=6_000,
    fee_pool_balance=0,
    accounts=ACCOUNTS,
)


class KeySpaceTest(unittest.TestCase):
    def test_there_are_twelve_entry_kinds(self) -> None:
        self.assertEqual(sorted(c.ENTRY_KINDS), list(range(1, 13)))

    def test_the_populated_fixture_covers_every_entry_kind(self) -> None:
        present = {key[0] for key in scenario.populated_economy()}
        self.assertEqual(present, set(c.ENTRY_KINDS))

    def test_no_key_is_a_prefix_of_another(self) -> None:
        keys = sorted(scenario.populated_economy())
        for index, earlier in enumerate(keys):
            for later in keys[index + 1 :]:
                with self.subTest(earlier=earlier.hex()):
                    self.assertFalse(later.startswith(earlier))

    def test_an_unknown_entry_kind_is_refused(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.ordered_entries({b"\x0d\x00": b""})

    def test_a_value_of_the_wrong_width_is_refused(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.ordered_entries({state.channel_key(0): b"\x00"})

    def test_the_seat_record_is_still_one_hundred_and_nineteen_bytes(self) -> None:
        value = state.seat_value(
            scenario.ALICE_IDENTITY, scenario.ALICE_FIRST_ADDRESS, None
        )
        self.assertEqual(len(value), 119)
        self.assertEqual(value[0:32], scenario.ALICE_IDENTITY)

    def test_the_seat_records_a_referrer_identity(self) -> None:
        value = state.seat_value(
            scenario.ALICE_IDENTITY, scenario.ALICE_FIRST_ADDRESS, scenario.BOB_IDENTITY
        )
        self.assertEqual(value[64], 1)
        self.assertEqual(value[65:97], scenario.BOB_IDENTITY)

    def test_a_singleton_beneficiary_takes_a_zero_identifier(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.typed_custody_key(
                c.VENTURE_ESCROW_BENEFICIARY, scenario.BENEFICIARY_ACCOUNT_ID
            )
        state.typed_custody_key(c.VENTURE_ESCROW_BENEFICIARY, c.SINGLETON_BENEFICIARY_ID)


class TreeAndRootTest(unittest.TestCase):
    def test_all_four_state_roots_differ_on_identical_accounts(self) -> None:
        """Distinct labels are strings rather than a chain, so all three are proved."""
        four = state.state_root(**COMMON, economy={})
        roots = {four}
        for version in (1, 2, 3):
            roots.add(state.predecessor_state_root(version, **COMMON))
        self.assertEqual(len(roots), 4)

    def test_each_predecessor_restatement_matches_its_accepted_vectors(self) -> None:
        primitives = VECTORS / "protocol-primitives-v1.txt"
        entries = [recorded(primitives, f"state.account{i}") for i in range(3)]
        accounts = [
            (bytes.fromhex(v[0:64]), int(v[64:80], 16), int(v[80:96], 16))
            for v in entries
        ]
        self.assertEqual(
            state.predecessor_state_root(
                1,
                chain_id=bytes.fromhex(recorded(primitives, "chain_id")),
                height=int(recorded(primitives, "state.height")),
                supply_limit=int(recorded(primitives, "state.supply_limit")),
                total_supply=int(recorded(primitives, "state.total_supply")),
                fee_pool_balance=int(recorded(primitives, "state.fee_pool_balance")),
                accounts=accounts,
            ),
            recorded(primitives, "state.root"),
        )
        for version, name in ((2, "economy-transition-v2.txt"), (3, "economy-transition-v3.txt")):
            with self.subTest(version):
                self.assertEqual(
                    state.predecessor_state_root(version, **COMMON),
                    recorded(VECTORS / name, "state.root_empty_economy"),
                )

    def test_the_economy_root_tracks_its_entries(self) -> None:
        empty = state.economy_root({})
        at_genesis = state.economy_root(
            genesis.initial_economy_entries(scenario.VERIFIER_KEY)
        )
        populated = state.economy_root(scenario.populated_economy())
        self.assertEqual(len({empty, at_genesis, populated}), 3)

    def test_the_tree_prefix_separates_versions(self) -> None:
        self.assertEqual(c.ECONOMY_TREE_PREFIX, "protocol-stack:v4:economy")

    def test_no_predecessor_construction_exists_beyond_three(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.predecessor_state_root(4, **COMMON)


class GenesisTest(unittest.TestCase):
    def setUp(self) -> None:
        self.founder = scenario.genesis()

    def test_the_prefix_and_account_bound_are_unchanged(self) -> None:
        self.assertEqual(c.GENESIS_PREFIX_BYTES, 110)
        self.assertEqual(c.MAX_GENESIS_ACCOUNTS, 21_843)

    def test_the_three_forced_relaxations_are_accepted_together(self) -> None:
        self.assertEqual(self.founder.total_supply, 0)
        self.assertEqual(self.founder.accounts, [])
        self.assertEqual(self.founder.fixed_transfer_fee, 0)
        genesis.encode(self.founder)

    def test_the_chain_id_differs_from_both_predecessors(self) -> None:
        identifiers = {genesis.chain_id(self.founder)}
        for version in (2, 3):
            identifiers.add(genesis.predecessor_chain_id(self.founder, version))
        self.assertEqual(len(identifiers), 3)

    def test_genesis_writes_no_identity_and_no_address(self) -> None:
        entries = genesis.initial_economy_entries(scenario.VERIFIER_KEY)
        kinds = {key[0] for key in entries}
        self.assertEqual(
            kinds,
            {
                c.CHANNEL_ENTRY,
                c.CARRY_ENTRY,
                c.VERIFIER_KEY_ENTRY,
                c.UNREFERRED_POOL_ENTRY,
            },
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

        for name, candidate in {
            "zero_supply_limit": variant(supply_limit=0),
            "supply_above_limit": variant(supply_limit=10, total_supply=11),
            "unconserved_supply": variant(total_supply=1),
        }.items():
            with self.subTest(name):
                with self.assertRaises(genesis.InvalidGenesis):
                    genesis.encode(candidate)


class SettlementIsVersionThreeTest(unittest.TestCase):
    """The imported settlement must write what version three recorded."""

    def test_the_assignment_record_is_byte_identical(self) -> None:
        from simulation.economy_transition_v3 import scenario as v3s
        from simulation.economy_transition_v3.settlement import assignment_entry

        path = VECTORS / "economy-transition-v3.txt"
        for name, window in (
            ("cycle", scenario.CYCLE_WINDOW),
            ("outage", scenario.OUTAGE_WINDOW),
        ):
            with self.subTest(name):
                _, value = assignment_entry(scenario.assignments()[window])
                self.assertEqual(
                    value.hex(), recorded(path, f"{name}.assignment_value_hex")
                )
                _, mirror = assignment_entry(v3s.assignments()[window])
                self.assertEqual(value, mirror)

    def test_the_cap_figure_is_unchanged(self) -> None:
        path = VECTORS / "economy-transition-v3.txt"
        self.assertEqual(str(c.MINT_ACCUMULATION_CAP), recorded(path, "cap.windows"))

    def test_the_cycle_record_is_the_same_width(self) -> None:
        from simulation.economy_transition_v3.settlement import assignment_entry

        key, value = assignment_entry(scenario.assignments()[scenario.CYCLE_WINDOW])
        self.assertEqual(len(key), c.ENTRY_KEY_BYTES[c.CYCLE_ASSIGNMENT_ENTRY])
        self.assertGreaterEqual(len(value), c.CYCLE_ASSIGNMENT_FIXED_VALUE_BYTES)


if __name__ == "__main__":
    unittest.main()
