#!/usr/bin/env python3
"""Escrow payout version-three binding, containment, and equivalence tests.

Version three changes six strings and the economy state it reads. These tests
assert both halves of that claim: that the compatibility boundary is real in
every direction, and that nothing else moved. The second half is the one worth
stating, because a rebinding that quietly altered a payout rule would still
produce a self-consistent vector file.

Containment is checked against both predecessors rather than only version two.
The three economy labels are distinct strings and not a chain, so refusing a v2
state implies nothing about refusing a v1 state.
"""

from __future__ import annotations

import itertools
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import digest
from simulation.escrow_payout import contract as c
from simulation.escrow_payout.domain import initial_state, state_digest
from simulation.escrow_payout.engine import simulate
from simulation.escrow_payout.handlers_binding import bind_opening_custody
from tests.simulation.escrow_payout_common import (
    VECTORS_V3_PATH,
    bind,
    codes,
    economy_state,
    economy_state_v2,
    economy_state_v3,
    research_events,
    vectors,
)

LABEL_FIELDS = (
    "schema",
    "events_label",
    "state_label",
    "trace_label",
    "result_label",
    "economy_state_label",
)
VERSIONS = ("v1", "v2", "v3")


class BindingTableTest(unittest.TestCase):
    def test_all_eighteen_strings_are_distinct(self) -> None:
        """Every provenance pair is disjoint, not merely the adjacent one."""
        strings = [
            getattr(c.BINDINGS[version], field)
            for version in VERSIONS
            for field in LABEL_FIELDS
        ]
        self.assertEqual(len(set(strings)), len(strings))

    def test_every_version_three_label_ends_in_v3(self) -> None:
        for name in ("schema", "events_label", "state_label", "trace_label", "result_label"):
            with self.subTest(name=name):
                self.assertTrue(getattr(c.V3, name).endswith("v3"))
        self.assertTrue(c.V3.economy_state_label.endswith("-v3"))

    def test_every_economy_contract_agrees_on_the_three_escrow_caps(self) -> None:
        """The shared cap table is licensed by this, not assumed by it."""
        self.assertTrue(c.caps_agree())
        for escrow_id in c.ESCROW_IDS:
            with self.subTest(escrow=escrow_id):
                caps = {c.BINDINGS[v].escrow_caps[escrow_id] for v in VERSIONS}
                self.assertEqual(len(caps), 1)


class CrossVersionContainmentTest(unittest.TestCase):
    """No economy state may satisfy a bind under a different version's label."""

    def setUp(self) -> None:
        self.states = {
            "v1": economy_state()[1],
            "v2": economy_state_v2()[1],
            "v3": economy_state_v3()[1],
        }

    def test_every_cross_version_bind_is_rejected(self) -> None:
        for state_version, bind_version in itertools.permutations(VERSIONS, 2):
            with self.subTest(state=state_version, bind=bind_version):
                event = bind(self.states[state_version], version=state_version)
                outcome = bind_opening_custody(
                    initial_state(), event, binding=c.BINDINGS[bind_version]
                )
                self.assertEqual(outcome.code, "INVALID_RESEARCH_INPUT")

    def test_relabelling_the_same_value_makes_the_bind_succeed(self) -> None:
        """The label caused the rejection, not the state's shape."""
        value = self.states["v2"]
        relabelled = bind(value, digest=digest(c.V3.economy_state_label, value))
        outcome = bind_opening_custody(initial_state(), relabelled, binding=c.V3)
        self.assertEqual(outcome.code, "OK")

    def test_each_version_accepts_its_own_state(self) -> None:
        for version in VERSIONS:
            with self.subTest(version=version):
                event = bind(self.states[version], version=version)
                outcome = bind_opening_custody(
                    initial_state(), event, binding=c.BINDINGS[version]
                )
                self.assertEqual(outcome.code, "OK")

    def test_a_rejected_bind_writes_nothing(self) -> None:
        state = initial_state()
        before = state_digest(state, c.V3)
        event = bind(self.states["v1"], version="v1")
        self.assertEqual(
            bind_opening_custody(state, event, binding=c.V3).code,
            "INVALID_RESEARCH_INPUT",
        )
        self.assertEqual(state_digest(state, c.V3), before)


class EquivalenceTest(unittest.TestCase):
    """Holding the scenario fixed is what makes the rebinding auditable."""

    def setUp(self) -> None:
        self.runs = {
            version: simulate(research_events(version), binding=c.BINDINGS[version])
            for version in VERSIONS
        }

    def test_all_three_runs_produce_identical_result_codes(self) -> None:
        traces = [codes(self.runs[version]) for version in VERSIONS]
        self.assertEqual(traces[0], traces[1])
        self.assertEqual(traces[1], traces[2])
        self.assertEqual(len(traces[0]), 39)

    def test_all_three_runs_keep_the_same_event_order(self) -> None:
        orders = [
            [record["event_id"] for record in self.runs[version]["records"]]
            for version in VERSIONS
        ]
        self.assertEqual(orders[0], orders[1])
        self.assertEqual(orders[1], orders[2])

    def test_any_two_final_states_differ_in_exactly_one_member(self) -> None:
        for left, right in itertools.combinations(VERSIONS, 2):
            with self.subTest(left=left, right=right):
                first = self.runs[left]["final_state"]
                second = self.runs[right]["final_state"]
                differing = sorted(
                    key
                    for key in set(first) | set(second)
                    if first.get(key) != second.get(key)
                )
                self.assertEqual(differing, ["bound_state_digest"])

    def test_the_opening_custody_coincides_while_its_source_does_not(self) -> None:
        """Recorded as evidence rather than read as continuity."""
        custody = {
            version: self.runs[version]["final_state"]["opening_custody"]
            for version in VERSIONS
        }
        self.assertEqual(custody["v1"], custody["v2"])
        self.assertEqual(custody["v2"], custody["v3"])
        digests = {
            self.runs[version]["final_state"]["bound_state_digest"] for version in VERSIONS
        }
        self.assertEqual(len(digests), 3)


class VectorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.recorded = vectors(VECTORS_V3_PATH)

    def test_the_recorded_digests_match_a_live_run(self) -> None:
        result = simulate(research_events("v3"), binding=c.V3)
        for name in ("state_digest", "trace_digest", "events_digest", "result_digest"):
            with self.subTest(name=name):
                self.assertEqual(result[name], self.recorded[f"scenario.{name}"])

    def test_containment_is_recorded_against_both_predecessors(self) -> None:
        for earlier in ("v1", "v2"):
            offered = self.recorded[f"binding.{earlier}_states_offered_to_v3"]
            rejected = self.recorded[f"binding.{earlier}_states_rejected_by_v3"]
            with self.subTest(earlier=earlier):
                self.assertEqual(offered, rejected)
                self.assertNotEqual(offered, "0")

    def test_the_cap_agreement_is_recorded(self) -> None:
        self.assertEqual(self.recorded["binding.escrow_caps_agree_with_v1"], "1")


if __name__ == "__main__":
    unittest.main()
