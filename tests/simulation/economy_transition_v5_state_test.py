#!/usr/bin/env python3
"""The version-five state roots, genesis identity, and separation from version four.

The key space itself is version four's and is exercised by that version's own
tests; what this module checks is the three places a chain is separated from
another, and that each predecessor construction restated here is the real one
rather than a lookalike.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v4 import genesis as v4_genesis
from simulation.economy_transition_v4 import state as v4_state
from simulation.economy_transition_v5 import contract as c
from simulation.economy_transition_v5 import genesis, scenario, state

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

ACCOUNTS = [(bytes([index]) * 32, 1_000 * (index + 1), 0) for index in range(3)]
COMMON = dict(
    chain_id=scenario.CHAIN_ID,
    height=7,
    supply_limit=5_699_395_010_000_000_000,
    total_supply=6_000,
    fee_pool_balance=0,
    accounts=ACCOUNTS,
)


def accepted(name: str) -> dict[str, str]:
    values: dict[str, str] = {}
    path = REPOSITORY_ROOT / "test-vectors" / name
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            key, _, value = stripped.partition("=")
            values[key] = value
    return values


class StateRootTest(unittest.TestCase):
    def test_all_five_roots_differ_over_identical_inputs(self) -> None:
        roots = {state.state_root(**COMMON, economy={})}
        for version in (1, 2, 3, 4):
            roots.add(state.predecessor_state_root(version, **COMMON))
        self.assertEqual(len(roots), 5)

    def test_the_version_four_restatement_is_the_accepted_construction(self) -> None:
        """A lookalike would make "the roots differ" trivially true."""
        four = accepted("economy-transition-v4.txt")
        self.assertEqual(
            state.predecessor_state_root(4, **COMMON), four["state.root_empty_economy"]
        )
        self.assertEqual(
            state.predecessor_state_root(4, **COMMON),
            v4_state.state_root(**COMMON, economy={}),
        )

    def test_the_earlier_restatements_are_the_accepted_constructions(self) -> None:
        for version, name in (
            (2, "economy-transition-v2.txt"),
            (3, "economy-transition-v3.txt"),
        ):
            with self.subTest(version):
                self.assertEqual(
                    state.predecessor_state_root(version, **COMMON),
                    accepted(name)["state.root_empty_economy"],
                )

    def test_the_version_one_root_is_the_accepted_one(self) -> None:
        primitives = accepted("protocol-primitives-v1.txt")
        entries = [primitives[f"state.account{index}"] for index in range(3)]
        accounts = [
            (bytes.fromhex(v[0:64]), int(v[64:80], 16), int(v[80:96], 16))
            for v in entries
        ]
        self.assertEqual(
            state.predecessor_state_root(
                1,
                chain_id=bytes.fromhex(primitives["chain_id"]),
                height=int(primitives["state.height"]),
                supply_limit=int(primitives["state.supply_limit"]),
                total_supply=int(primitives["state.total_supply"]),
                fee_pool_balance=int(primitives["state.fee_pool_balance"]),
                accounts=accounts,
            ),
            primitives["state.root"],
        )

    def test_an_unknown_predecessor_is_refused(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.predecessor_state_root(5, **COMMON)

    def test_the_root_tracks_the_economy(self) -> None:
        self.assertNotEqual(
            state.state_root(**COMMON, economy=scenario.populated_economy()),
            state.state_root(**COMMON, economy={}),
        )


class EconomyTreeTest(unittest.TestCase):
    def test_the_prefix_separates_all_four_economy_trees(self) -> None:
        entries = scenario.populated_economy()
        roots = {state.economy_root(entries), v4_state.economy_root(entries)}
        self.assertEqual(len(roots), 2)

    def test_the_version_four_tree_is_the_accepted_one(self) -> None:
        self.assertEqual(
            v4_state.economy_root(scenario.populated_economy()).hex(),
            accepted("economy-transition-v4.txt")["state.economy_root_populated"],
        )

    def test_the_entries_are_identical_and_only_the_prefix_is_not(self) -> None:
        from simulation.economy_transition_v4 import scenario as v4_scenario

        self.assertEqual(scenario.populated_economy(), v4_scenario.populated_economy())
        self.assertNotEqual(c.ECONOMY_TREE_PREFIX, "protocol-stack:v4:economy")


class GenesisTest(unittest.TestCase):
    def setUp(self) -> None:
        self.founder = scenario.genesis()

    def test_the_fields_are_version_fours(self) -> None:
        from simulation.economy_transition_v4 import scenario as v4_scenario

        self.assertEqual(self.founder, v4_scenario.genesis())

    def test_the_encoding_differs_in_the_schema_version_alone(self) -> None:
        five = genesis.encode(self.founder)
        four = v4_genesis.encode(self.founder)
        self.assertEqual(len(five), len(four))
        self.assertEqual(sum(1 for a, b in zip(five, four) if a != b), 1)
        self.assertEqual(int.from_bytes(five[4:6], "big"), 5)
        self.assertEqual(five[:4], four[:4])
        self.assertEqual(five[6:], four[6:])

    def test_the_chain_identifiers_are_all_distinct(self) -> None:
        identifiers = {genesis.chain_id(self.founder).hex()}
        for version in (2, 3, 4):
            identifiers.add(genesis.predecessor_chain_id(self.founder, version).hex())
        self.assertEqual(len(identifiers), 4)

    def test_the_version_four_chain_id_is_the_accepted_one(self) -> None:
        self.assertEqual(
            genesis.predecessor_chain_id(self.founder, 4).hex(),
            accepted("economy-transition-v4.txt")["genesis.chain_id"],
        )

    def test_an_unknown_predecessor_chain_is_refused(self) -> None:
        with self.assertRaises(genesis.InvalidGenesis):
            genesis.predecessor_chain_id(self.founder, 5)

    def test_a_founder_economy_genesis_opens_empty(self) -> None:
        self.assertEqual(self.founder.total_supply, 0)
        self.assertEqual(self.founder.accounts, [])
        self.assertEqual(self.founder.fixed_transfer_fee, 0)

    def test_genesis_writes_only_the_fixed_tables(self) -> None:
        entries = genesis.initial_economy_entries(scenario.VERIFIER_KEY)
        self.assertEqual(
            {key[0] for key in entries},
            {
                c.CHANNEL_ENTRY,
                c.CARRY_ENTRY,
                c.VERIFIER_KEY_ENTRY,
                c.UNREFERRED_POOL_ENTRY,
            },
        )


if __name__ == "__main__":
    unittest.main()
