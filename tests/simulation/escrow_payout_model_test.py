#!/usr/bin/env python3
"""Scenario, binding, conservation, and determinism tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.escrow_payout import contract as c
from simulation.escrow_payout.domain import assert_invariants, initial_state
from simulation.escrow_payout.engine import apply_event, simulate
from simulation.escrow_payout.validation import parse_events
from simulation.founder_economy import contract as economy
from tests.simulation.escrow_payout_common import (
    COMMUNITY,
    DEVELOPER,
    VENTURE,
    advance,
    bind,
    codes,
    economy_state,
    grant,
    opening,
    payout,
    research_events,
    revoke,
    vectors,
)


def credited(state_value: dict, escrow: str) -> int:
    balances = state_value["recipient_balances"][escrow]
    return sum(int(value) for value in balances.values())


class ScenarioTest(unittest.TestCase):
    def setUp(self) -> None:
        self.result = simulate(research_events())
        self.recorded = vectors()

    def test_the_recorded_digests_are_reproduced(self) -> None:
        for key, field in (
            ("scenario.events_digest", "events_digest"),
            ("scenario.trace_digest", "trace_digest"),
            ("scenario.state_digest", "state_digest"),
            ("scenario.result_digest", "result_digest"),
        ):
            with self.subTest(key=key):
                self.assertEqual(self.result[field], self.recorded[key])

    def test_the_recorded_trace_codes_are_reproduced(self) -> None:
        self.assertEqual(
            len(self.result["records"]), int(self.recorded["scenario.event_count"])
        )
        for index, record in enumerate(self.result["records"]):
            with self.subTest(index=index):
                self.assertEqual(
                    record["event_id"], self.recorded[f"record{index}.event_id"]
                )
                self.assertEqual(
                    record["result"], self.recorded[f"record{index}.result"]
                )

    def test_the_recorded_escrow_positions_are_reproduced(self) -> None:
        state = self.result["final_state"]
        for index, escrow in enumerate(c.ESCROW_IDS):
            with self.subTest(escrow=escrow):
                for field in (
                    "opening_custody",
                    "available_custody",
                    "paid_out_total",
                ):
                    self.assertEqual(
                        state[field][escrow],
                        self.recorded[f"escrow{index}.{field}"],
                    )

    def test_a_repeated_run_is_byte_identical(self) -> None:
        self.assertEqual(simulate(research_events()), self.result)

    def test_the_invariant_stride_does_not_change_the_result(self) -> None:
        self.assertEqual(simulate(research_events(), invariant_stride=1), self.result)


class BindingTest(unittest.TestCase):
    def test_the_bound_custody_is_the_accepted_economy_run(self) -> None:
        digest, state_value = economy_state()
        result = simulate([bind(state_value)])
        self.assertEqual(codes(result), ["OK"])
        self.assertEqual(result["final_state"]["bound_state_digest"], digest)
        for escrow in c.ESCROW_IDS:
            with self.subTest(escrow=escrow):
                self.assertEqual(
                    result["final_state"]["opening_custody"][escrow],
                    state_value["typed_custody"].get(c.custody_key(escrow), "0"),
                )

    def test_a_tampered_state_value_is_rejected(self) -> None:
        digest, state_value = economy_state()
        tampered = dict(state_value)
        tampered["typed_custody"] = dict(state_value["typed_custody"])
        tampered["typed_custody"][c.custody_key(VENTURE)] = "1"
        self.assertEqual(
            codes(simulate([bind(tampered, digest)])), ["INVALID_RESEARCH_INPUT"]
        )

    def test_a_missing_custody_key_opens_at_zero(self) -> None:
        result = simulate([opening(venture_escrow=500)])
        state = result["final_state"]
        self.assertEqual(state["opening_custody"][VENTURE], "500")
        self.assertEqual(state["opening_custody"][COMMUNITY], "0")
        self.assertEqual(state["opening_custody"][DEVELOPER], "0")

    def test_an_empty_state_binds_with_an_empty_journal(self) -> None:
        result = simulate([opening()])
        self.assertEqual(codes(result), ["OK"])
        self.assertEqual(result["records"][0]["journal"], [])

    def test_the_escrow_caps_are_the_accepted_manifest_caps(self) -> None:
        for escrow in c.ESCROW_IDS:
            with self.subTest(escrow=escrow):
                self.assertEqual(c.ESCROW_CAPS[escrow], economy.CHANNEL_CAPS[escrow])


class ConservationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.events = [
            opening(venture_escrow=10_000, community_grants_escrow=8_000),
            grant("cap-venture", escrow=VENTURE, per_payout=4_000, envelope=9_000),
            grant("cap-community", escrow=COMMUNITY, per_payout=8_000, envelope=8_000),
            payout(4_000, payout_id="p-1", capability_id="cap-venture"),
            payout(
                3_000,
                payout_id="p-2",
                capability_id="cap-venture",
                recipient="recipient-beta",
            ),
            payout(
                8_000,
                payout_id="p-3",
                capability_id="cap-community",
                escrow=COMMUNITY,
                recipient="recipient-gamma",
            ),
        ]

    def test_each_escrow_conserves_independently(self) -> None:
        state = simulate(self.events)["final_state"]
        for escrow in c.ESCROW_IDS:
            with self.subTest(escrow=escrow):
                opening_amount = int(state["opening_custody"][escrow])
                available = int(state["available_custody"][escrow])
                paid_out = int(state["paid_out_total"][escrow])
                self.assertEqual(available + paid_out, opening_amount)
                self.assertEqual(credited(state, escrow), paid_out)

    def test_the_capability_account_matches_the_custody_account(self) -> None:
        state = simulate(self.events)["final_state"]
        for escrow in c.ESCROW_IDS:
            charged = sum(
                int(capability["spent"])
                for capability in state["capabilities"].values()
                if capability["escrow_id"] == escrow
            )
            with self.subTest(escrow=escrow):
                self.assertEqual(charged, int(state["paid_out_total"][escrow]))

    def test_conservation_holds_after_every_accepted_event(self) -> None:
        state = initial_state()
        for index, event in enumerate(parse_events(self.events)):
            apply_event(state, event, index)
            assert_invariants(state)

    def test_available_custody_never_rises_after_the_bind(self) -> None:
        state = initial_state()
        previous: dict[str, int] | None = None
        for index, event in enumerate(parse_events(research_events())):
            apply_event(state, event, index)
            if previous is not None:
                for escrow in c.ESCROW_IDS:
                    with self.subTest(index=index, escrow=escrow):
                        self.assertLessEqual(
                            state.available_custody[escrow], previous[escrow]
                        )
            if state.bound:
                previous = dict(state.available_custody)

    def test_no_accepted_event_changes_two_escrows(self) -> None:
        state = initial_state()
        for index, event in enumerate(parse_events(research_events())):
            before = dict(state.available_custody)
            record = apply_event(state, event, index)
            if not record["accepted"] or event["kind"] == "bind_opening_custody":
                continue
            changed = [
                escrow
                for escrow in c.ESCROW_IDS
                if state.available_custody[escrow] != before[escrow]
            ]
            with self.subTest(index=index):
                self.assertLessEqual(len(changed), 1)


class ContainmentTest(unittest.TestCase):
    def test_a_capability_cannot_spend_a_foreign_escrow(self) -> None:
        events = [
            opening(venture_escrow=10_000, developer_incentives_escrow=10_000),
            grant("cap-venture", escrow=VENTURE),
            payout(
                1_000,
                payout_id="p-1",
                capability_id="cap-venture",
                escrow=DEVELOPER,
            ),
        ]
        result = simulate(events)
        self.assertEqual(codes(result)[-1], "ESCROW_MISMATCH")
        state = result["final_state"]
        self.assertEqual(state["available_custody"][DEVELOPER], "10000")
        self.assertEqual(state["available_custody"][VENTURE], "10000")

    def test_value_free_transitions_emit_no_journal(self) -> None:
        events = [
            opening(venture_escrow=10_000),
            grant("cap-venture"),
            revoke("cap-venture"),
            advance(0),
        ]
        result = simulate(events)
        self.assertEqual(codes(result), ["OK"] * 4)
        for record in result["records"][1:]:
            with self.subTest(kind=record["kind"]):
                self.assertEqual(record["journal"], [])

    def test_an_expired_capability_leaves_custody_untouched(self) -> None:
        events = [
            opening(venture_escrow=10_000),
            grant("cap-venture", expiry=0),
            advance(0),
            payout(1_000, capability_id="cap-venture"),
        ]
        result = simulate(events)
        self.assertEqual(codes(result)[-1], "CAPABILITY_EXPIRED")
        self.assertEqual(result["final_state"]["available_custody"][VENTURE], "10000")

    def test_a_revoked_capability_leaves_custody_untouched(self) -> None:
        events = [
            opening(venture_escrow=10_000),
            grant("cap-venture"),
            revoke("cap-venture"),
            payout(1_000, capability_id="cap-venture"),
        ]
        result = simulate(events)
        self.assertEqual(codes(result)[-1], "CAPABILITY_REVOKED")
        self.assertEqual(result["final_state"]["available_custody"][VENTURE], "10000")


if __name__ == "__main__":
    unittest.main()
