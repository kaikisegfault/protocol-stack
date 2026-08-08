#!/usr/bin/env python3
"""Escrow payout version-two binding, containment, and equivalence tests.

Version two changes six strings and the economy state it reads. These tests
assert both halves of that claim: that the compatibility boundary is real, and
that nothing else moved. The second half is the one worth stating, because a
rebinding that quietly altered a payout rule would still produce a self
consistent vector file.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import digest
from simulation.escrow_payout import contract as c
from simulation.escrow_payout.domain import initial_state, state_digest
from simulation.escrow_payout.engine import simulate
from simulation.escrow_payout.handlers_binding import bind_opening_custody
from simulation.founder_economy import contract as economy_v1
from simulation.founder_economy_v2 import contract as economy_v2
from tests.simulation.escrow_payout_common import (
    VECTORS_V2_PATH,
    bind,
    codes,
    economy_state,
    economy_state_v2,
    research_events,
    vectors,
)


class BindingTableTest(unittest.TestCase):
    def test_every_label_differs_between_the_two_versions(self) -> None:
        fields = (
            "schema",
            "events_label",
            "state_label",
            "trace_label",
            "result_label",
            "economy_state_label",
        )
        for name in fields:
            with self.subTest(name=name):
                self.assertNotEqual(getattr(c.V1, name), getattr(c.V2, name))

    def test_every_version_two_label_ends_in_v2(self) -> None:
        for name in ("schema", "events_label", "state_label", "trace_label", "result_label"):
            with self.subTest(name=name):
                self.assertTrue(getattr(c.V2, name).endswith("v2"))

    def test_the_two_economy_contracts_agree_on_the_three_escrow_caps(self) -> None:
        """The shared cap table is licensed by this, not assumed by it."""
        self.assertTrue(c.caps_agree())
        for escrow_id in c.ESCROW_IDS:
            with self.subTest(escrow=escrow_id):
                self.assertEqual(
                    economy_v1.CHANNEL_CAPS[escrow_id],
                    economy_v2.CHANNEL_CAPS[escrow_id],
                )

    def test_the_escrow_set_is_unchanged(self) -> None:
        self.assertEqual(set(c.V1.escrow_caps), set(c.V2.escrow_caps))
        self.assertEqual(c.ESCROW_IDS, tuple(sorted(c.ESCROW_IDS, key=c.ESCROW_IDS.index)))


class CrossVersionContainmentTest(unittest.TestCase):
    """A state recorded under one economy version cannot bind under the other."""

    def test_a_version_one_state_is_rejected_by_a_version_two_bind(self) -> None:
        _, state_value = economy_state()
        outcome = bind_opening_custody(
            initial_state(), bind(state_value, version="v1"), c.V2
        )
        self.assertFalse(outcome.accepted)
        self.assertEqual(outcome.code, "INVALID_RESEARCH_INPUT")

    def test_a_version_two_state_is_rejected_by_a_version_one_bind(self) -> None:
        _, state_value = economy_state_v2()
        outcome = bind_opening_custody(
            initial_state(), bind(state_value, version="v2"), c.V1
        )
        self.assertFalse(outcome.accepted)
        self.assertEqual(outcome.code, "INVALID_RESEARCH_INPUT")

    def test_each_version_accepts_its_own_state(self) -> None:
        for binding, supplier in ((c.V1, economy_state), (c.V2, economy_state_v2)):
            with self.subTest(version=binding.version):
                _, state_value = supplier()
                outcome = bind_opening_custody(
                    initial_state(), bind(state_value, version=binding.version), binding
                )
                self.assertTrue(outcome.accepted)

    def test_the_rejection_is_the_label_and_not_the_state_shape(self) -> None:
        """Relabelling the same value under v2 makes the identical bind succeed."""
        _, state_value = economy_state()
        event = bind(state_value, digest(c.V2.economy_state_label, state_value))
        outcome = bind_opening_custody(initial_state(), event, c.V2)
        self.assertTrue(outcome.accepted)

    def test_the_two_economy_labels_give_different_digests(self) -> None:
        _, state_value = economy_state_v2()
        self.assertNotEqual(
            digest(c.V1.economy_state_label, state_value),
            digest(c.V2.economy_state_label, state_value),
        )


class TransitionEquivalenceTest(unittest.TestCase):
    """Only provenance moved: the two runs agree on every transition."""

    def setUp(self) -> None:
        self.v1 = simulate(research_events("v1"), binding=c.V1)
        self.v2 = simulate(research_events("v2"), binding=c.V2)

    def test_the_two_fixtures_produce_the_same_result_codes(self) -> None:
        self.assertEqual(codes(self.v1), codes(self.v2))

    def test_the_two_fixtures_produce_the_same_event_order(self) -> None:
        self.assertEqual(
            [record["event_id"] for record in self.v1["records"]],
            [record["event_id"] for record in self.v2["records"]],
        )

    def test_the_only_differing_state_member_is_the_bound_economy_digest(self) -> None:
        differing = [
            key
            for key in self.v1["final_state"]
            if self.v1["final_state"][key] != self.v2["final_state"][key]
        ]
        self.assertEqual(differing, ["bound_state_digest"])

    def test_the_two_fixtures_differ_only_in_their_embedded_economy_states(self) -> None:
        v1_events = research_events("v1")
        v2_events = research_events("v2")
        self.assertEqual(len(v1_events), len(v2_events))
        differing = [
            first["id"]
            for first, second in zip(v1_events, v2_events)
            if first != second
        ]
        self.assertEqual(
            differing,
            ["bind-tampered-digest", "bind-above-cap", "bind-economy-state", "bind-replay"],
        )
        for first, second in zip(v1_events, v2_events):
            if first != second:
                with self.subTest(event=first["id"]):
                    self.assertEqual(
                        {k: v for k, v in first.items() if k != "economy_state_result"},
                        {k: v for k, v in second.items() if k != "economy_state_result"},
                    )

    def test_every_recorded_digest_differs_between_the_versions(self) -> None:
        for field in ("events_digest", "trace_digest", "state_digest", "result_digest"):
            with self.subTest(field=field):
                self.assertNotEqual(self.v1[field], self.v2[field])

    def test_the_same_escrow_state_digests_differently_per_version(self) -> None:
        state = initial_state()
        self.assertNotEqual(state_digest(state, c.V1), state_digest(state, c.V2))


class RecordedVectorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.result = simulate(research_events("v2"), binding=c.V2)
        self.recorded = vectors(VECTORS_V2_PATH)

    def test_the_recorded_digests_are_reproduced(self) -> None:
        for key, field in (
            ("scenario.events_digest", "events_digest"),
            ("scenario.trace_digest", "trace_digest"),
            ("scenario.state_digest", "state_digest"),
            ("scenario.result_digest", "result_digest"),
        ):
            with self.subTest(key=key):
                self.assertEqual(self.result[field], self.recorded[key])

    def test_the_recorded_binding_is_a_live_version_two_economy_run(self) -> None:
        economy_digest, _ = economy_state_v2()
        self.assertEqual(self.recorded["binding.economy_state_digest"], economy_digest)
        self.assertEqual(
            self.recorded["binding.economy_state_label"], c.V2.economy_state_label
        )

    def test_the_recorded_schema_and_labels_are_the_version_two_binding(self) -> None:
        for key, value in (
            ("schema", c.V2.schema),
            ("events_domain_label", c.V2.events_label),
            ("state_domain_label", c.V2.state_label),
            ("trace_domain_label", c.V2.trace_label),
            ("result_domain_label", c.V2.result_label),
        ):
            with self.subTest(key=key):
                self.assertEqual(self.recorded[key], value)

    def test_the_opening_custody_is_unchanged_from_version_one(self) -> None:
        """The escrow legs are unrevised, so only the source state moved."""
        v1_recorded = vectors()
        for index in range(len(c.ESCROW_IDS)):
            key = f"binding.escrow{index}.opening_custody"
            with self.subTest(key=key):
                self.assertEqual(self.recorded[key], v1_recorded[key])


if __name__ == "__main__":
    unittest.main(verbosity=2)
