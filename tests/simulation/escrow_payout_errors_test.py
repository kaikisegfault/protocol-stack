#!/usr/bin/env python3
"""Negative, boundary, replay, overflow, and atomicity tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import MAX_U64
from simulation.escrow_payout import contract as c
from simulation.escrow_payout.domain import (
    Capability,
    initial_state,
    state_digest,
)
from simulation.escrow_payout.engine import apply_event, simulate
from simulation.escrow_payout.handlers_payout import execute_payout
from simulation.escrow_payout.operations import INCREASE, Outcome, entry
from simulation.escrow_payout.validation import InputError, parse_events
from tests.simulation.escrow_payout_common import (
    COMMUNITY,
    DEVELOPER,
    VENTURE,
    advance,
    approval,
    bind,
    codes,
    economy_state,
    grant,
    opening,
    payout,
    research_events,
    revoke,
    synthetic_state,
)

OPEN = 10_000


def opened(*events: dict) -> list[dict]:
    """A bound venture escrow holding OPEN units, then the supplied events."""
    return [opening(venture_escrow=OPEN), *events]


class BindingErrorTest(unittest.TestCase):
    def test_a_missing_research_input_is_rejected(self) -> None:
        self.assertEqual(codes(simulate([bind(None)])), ["MISSING_RESEARCH_INPUT"])

    def test_a_second_bind_is_rejected(self) -> None:
        _, state_value = economy_state()
        events = [bind(state_value), bind(state_value, event_id="bind-0002")]
        self.assertEqual(codes(simulate(events)), ["OK", "ALREADY_BOUND"])

    def test_a_wrong_digest_is_rejected(self) -> None:
        digest, state_value = economy_state()
        wrong = digest[:-1] + ("0" if digest[-1] != "0" else "1")
        self.assertEqual(
            codes(simulate([bind(state_value, wrong)])), ["INVALID_RESEARCH_INPUT"]
        )

    def test_a_non_decimal_custody_amount_is_rejected(self) -> None:
        state_value = synthetic_state({c.custody_key(VENTURE): "0x10"})
        self.assertEqual(
            codes(simulate([bind(state_value)])), ["INVALID_RESEARCH_INPUT"]
        )

    def test_custody_at_the_manifest_cap_is_accepted(self) -> None:
        cap = c.ESCROW_CAPS[VENTURE]
        result = simulate([opening(venture_escrow=cap)])
        self.assertEqual(codes(result), ["OK"])
        self.assertEqual(result["final_state"]["opening_custody"][VENTURE], str(cap))

    def test_custody_one_unit_above_the_manifest_cap_is_rejected(self) -> None:
        for escrow in c.ESCROW_IDS:
            with self.subTest(escrow=escrow):
                events = [opening(**{escrow: c.ESCROW_CAPS[escrow] + 1})]
                self.assertEqual(codes(simulate(events)), ["CUSTODY_ABOVE_CAP"])

    def test_a_grant_before_binding_is_rejected(self) -> None:
        self.assertEqual(codes(simulate([grant("cap-0001")])), ["NOT_BOUND"])

    def test_a_payout_before_binding_finds_no_capability(self) -> None:
        self.assertEqual(codes(simulate([payout(1)])), ["UNKNOWN_CAPABILITY"])


class GrantErrorTest(unittest.TestCase):
    def test_an_unknown_escrow_is_rejected(self) -> None:
        events = opened(grant("cap-0001", escrow="treasury-escrow"))
        self.assertEqual(codes(simulate(events))[-1], "UNKNOWN_ESCROW")

    def test_a_zero_bound_is_rejected(self) -> None:
        for per_payout, envelope in ((0, 10), (10, 0)):
            with self.subTest(per_payout=per_payout, envelope=envelope):
                events = opened(
                    grant("cap-0001", per_payout=per_payout, envelope=envelope)
                )
                self.assertEqual(codes(simulate(events))[-1], "ZERO_AMOUNT")

    def test_a_per_payout_bound_above_the_envelope_is_rejected(self) -> None:
        events = opened(grant("cap-0001", per_payout=11, envelope=10))
        self.assertEqual(codes(simulate(events))[-1], "INVALID_CAPABILITY")

    def test_a_per_payout_bound_equal_to_the_envelope_is_accepted(self) -> None:
        events = opened(grant("cap-0001", per_payout=10, envelope=10))
        self.assertEqual(codes(simulate(events))[-1], "OK")

    def test_a_duplicate_capability_is_rejected(self) -> None:
        events = opened(grant("cap-0001"), grant("cap-0001", event_id="grant-again"))
        self.assertEqual(codes(simulate(events))[-1], "REPLAY")

    def test_a_grant_already_expired_is_rejected(self) -> None:
        events = opened(advance(0), grant("cap-0001", expiry=0))
        self.assertEqual(codes(simulate(events))[-1], "CAPABILITY_EXPIRED")

    def test_an_envelope_above_available_custody_is_accepted(self) -> None:
        """Delegation is bounded authority, not a reservation."""
        events = opened(grant("cap-0001", per_payout=OPEN * 2, envelope=OPEN * 10))
        self.assertEqual(codes(simulate(events))[-1], "OK")


class PayoutBoundaryTest(unittest.TestCase):
    def test_a_payout_at_the_per_payout_bound_is_accepted(self) -> None:
        events = opened(
            grant("cap-0001", per_payout=1_000, envelope=5_000), payout(1_000)
        )
        self.assertEqual(codes(simulate(events))[-1], "OK")

    def test_a_payout_one_unit_above_the_per_payout_bound_is_rejected(self) -> None:
        events = opened(
            grant("cap-0001", per_payout=1_000, envelope=5_000), payout(1_001)
        )
        self.assertEqual(codes(simulate(events))[-1], "PAYOUT_LIMIT_EXCEEDED")

    def test_an_envelope_exhausted_exactly_then_exceeded(self) -> None:
        events = opened(
            grant("cap-0001", per_payout=1_000, envelope=2_000),
            payout(1_000, payout_id="p-1"),
            payout(1_000, payout_id="p-2"),
            payout(1, payout_id="p-3"),
        )
        self.assertEqual(
            codes(simulate(events))[-3:], ["OK", "OK", "ENVELOPE_EXCEEDED"]
        )

    def test_a_payout_of_exactly_the_available_custody_is_accepted(self) -> None:
        events = opened(
            grant("cap-0001", per_payout=OPEN, envelope=OPEN * 2), payout(OPEN)
        )
        result = simulate(events)
        self.assertEqual(codes(result)[-1], "OK")
        self.assertEqual(result["final_state"]["available_custody"][VENTURE], "0")

    def test_a_payout_one_unit_above_the_available_custody_is_rejected(self) -> None:
        events = opened(
            grant("cap-0001", per_payout=OPEN * 2, envelope=OPEN * 2), payout(OPEN + 1)
        )
        self.assertEqual(codes(simulate(events))[-1], "INSUFFICIENT_CUSTODY")

    def test_a_drained_escrow_rejects_while_the_envelope_still_has_room(self) -> None:
        events = opened(
            grant("cap-0001", per_payout=OPEN, envelope=OPEN * 2),
            payout(OPEN, payout_id="p-1"),
            payout(1, payout_id="p-2"),
        )
        self.assertEqual(codes(simulate(events))[-1], "INSUFFICIENT_CUSTODY")

    def test_a_zero_payout_is_rejected(self) -> None:
        events = opened(grant("cap-0001"), payout(0))
        self.assertEqual(codes(simulate(events))[-1], "ZERO_AMOUNT")

    def test_a_replayed_payout_is_rejected(self) -> None:
        events = opened(
            grant("cap-0001"),
            payout(100, payout_id="p-1"),
            payout(100, payout_id="p-1", event_id="p-1-replay"),
        )
        self.assertEqual(codes(simulate(events))[-1], "REPLAY")

    def test_an_unknown_capability_is_rejected(self) -> None:
        events = opened(grant("cap-0001"), payout(100, capability_id="cap-absent"))
        self.assertEqual(codes(simulate(events))[-1], "UNKNOWN_CAPABILITY")


class ApprovalTest(unittest.TestCase):
    def test_a_missing_approval_is_rejected(self) -> None:
        events = opened(grant("cap-0001"), payout(100, approve=None))
        self.assertEqual(codes(simulate(events))[-1], "MISSING_RESEARCH_INPUT")

    def test_an_approval_bound_to_another_payout_is_rejected(self) -> None:
        events = opened(
            grant("cap-0001"),
            payout(100, payout_id="p-1", approve=approval("p-2")),
        )
        self.assertEqual(codes(simulate(events))[-1], "INVALID_RESEARCH_INPUT")

    def test_a_withheld_approval_is_rejected(self) -> None:
        events = opened(
            grant("cap-0001"),
            payout(100, payout_id="p-1", approve=approval("p-1", decision="rejected")),
        )
        self.assertEqual(codes(simulate(events))[-1], "APPROVAL_WITHHELD")

    def test_an_unknown_decision_is_an_input_error(self) -> None:
        events = opened(
            grant("cap-0001"),
            payout(100, payout_id="p-1", approve=approval("p-1", decision="maybe")),
        )
        with self.assertRaises(InputError):
            simulate(events)


class RevokeAndCycleTest(unittest.TestCase):
    def test_revoking_an_unknown_capability_is_rejected(self) -> None:
        self.assertEqual(codes(simulate(opened(revoke("cap-absent"))))[-1],
                         "UNKNOWN_CAPABILITY")

    def test_revoking_twice_is_rejected(self) -> None:
        events = opened(
            grant("cap-0001"), revoke("cap-0001"),
            revoke("cap-0001", event_id="revoke-again"),
        )
        self.assertEqual(codes(simulate(events))[-1], "ALREADY_REVOKED")

    def test_a_skipped_or_replayed_cycle_is_rejected(self) -> None:
        """After advancing, cycle 2 skips ahead and cycle 0 replays a passed one."""
        for index in (2, 0):
            with self.subTest(index=index):
                events = opened(advance(0), advance(index, event_id="advance-again"))
                self.assertEqual(codes(simulate(events))[-1], "CYCLE_MISMATCH")

    def test_a_capability_is_usable_in_its_expiry_cycle(self) -> None:
        events = opened(grant("cap-0001", expiry=1), advance(0), payout(100))
        self.assertEqual(codes(simulate(events))[-1], "OK")


class OverflowTest(unittest.TestCase):
    """The manifest cap makes overflow unreachable through events.

    The checked arithmetic is still exercised directly, so the guard is proved
    present rather than assumed, and the cap invariant is what keeps it dead.
    """

    def test_a_paid_out_total_near_u64_maximum_overflows(self) -> None:
        state = initial_state()
        state.bound_state_digest = "0" * 64
        state.opening_custody[VENTURE] = MAX_U64
        state.available_custody[VENTURE] = MAX_U64
        state.paid_out_total[VENTURE] = MAX_U64
        state.capabilities["cap-0001"] = Capability(
            escrow_id=VENTURE,
            per_payout_maximum=MAX_U64,
            envelope_total=MAX_U64,
            expiry_cycle=MAX_U64,
        )
        event = parse_events([payout(10, capability_id="cap-0001")])[0]
        self.assertEqual(execute_payout(state, event).code, "ARITHMETIC_OVERFLOW")

    def test_a_cycle_counter_at_u64_maximum_overflows(self) -> None:
        state = initial_state()
        state.current_cycle = MAX_U64
        event = parse_events([advance(0)])[0]
        event["cycle_index"] = MAX_U64
        outcome = apply_event(state, event, 0)
        self.assertEqual(outcome["result"], "ARITHMETIC_OVERFLOW")


class AtomicityTest(unittest.TestCase):
    def test_every_rejection_leaves_the_state_digest_unchanged(self) -> None:
        state = initial_state()
        rejections = 0
        for index, event in enumerate(parse_events(research_events())):
            before = state_digest(state)
            record = apply_event(state, event, index)
            if record["accepted"]:
                continue
            rejections += 1
            with self.subTest(event_id=record["event_id"]):
                self.assertEqual(state_digest(state), before)
                self.assertEqual(record["journal"], [])
        self.assertEqual(rejections, 27)

    def test_a_rejection_consumes_no_payout_identifier(self) -> None:
        events = opened(
            grant("cap-0001", per_payout=100, envelope=100),
            payout(101, payout_id="p-1"),
            payout(100, payout_id="p-1", event_id="p-1-retry"),
        )
        result = simulate(events)
        self.assertEqual(codes(result)[-2:], ["PAYOUT_LIMIT_EXCEEDED", "OK"])
        self.assertEqual(result["final_state"]["accepted_payout_ids"], ["p-1"])

    def test_an_unbalanced_journal_is_an_invariant_failure(self) -> None:
        def broken(state, event):
            return Outcome(code="OK", journal=[entry("custody:venture", INCREASE, 1)])

        state = initial_state()
        event = parse_events([advance(0)])[0]
        with patch.dict("simulation.escrow_payout.engine.HANDLERS",
                        {"advance_cycle": broken}):
            record = apply_event(state, event, 0)
        self.assertEqual(record["result"], "INVARIANT")
        self.assertEqual(state.current_cycle, 0)


class IndependenceTest(unittest.TestCase):
    def test_draining_one_escrow_leaves_the_others_untouched(self) -> None:
        events = [
            opening(
                venture_escrow=1_000,
                community_grants_escrow=2_000,
                developer_incentives_escrow=3_000,
            ),
            grant("cap-venture", escrow=VENTURE, per_payout=1_000, envelope=1_000),
            payout(1_000, payout_id="p-1", capability_id="cap-venture"),
        ]
        state = simulate(events)["final_state"]
        self.assertEqual(state["available_custody"][VENTURE], "0")
        self.assertEqual(state["available_custody"][COMMUNITY], "2000")
        self.assertEqual(state["available_custody"][DEVELOPER], "3000")
        self.assertEqual(state["paid_out_total"][COMMUNITY], "0")
        self.assertEqual(state["paid_out_total"][DEVELOPER], "0")


if __name__ == "__main__":
    unittest.main()
