#!/usr/bin/env python3
"""The uptime-measurement model: evidence, disputes, finalisation, and records."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import CodedError, InvariantError
from simulation.cycle_boundary.model import CycleBoundary
from simulation.uptime_measurement import contract as c
from simulation.uptime_measurement.model import DutyReport, UptimeMeasurement
from simulation.uptime_measurement.scenario import AI_KEY, beacon_for, build_schedule, run
from simulation.uptime_measurement.slots import is_selected, slot_last_height, slot_of_height


def bound_model() -> UptimeMeasurement:
    schedule = build_schedule()
    model = UptimeMeasurement(ai_key=AI_KEY)
    model.bind_schedule(schedule, schedule.state_digest())
    return model


def advance(model: UptimeMeasurement, through: int) -> None:
    start = 0 if model.height is None else model.height + 1
    for height in range(start, through + 1):
        model.execute_block(height, beacon_for(height))


def code_of(action) -> str:
    try:
        action()
    except CodedError as error:
        return error.code
    return "ACCEPTED"


class BindingTest(unittest.TestCase):
    def test_a_matching_digest_binds(self) -> None:
        model = bound_model()
        self.assertIsNotNone(model.bound_schedule_digest)

    def test_a_wrong_digest_is_refused(self) -> None:
        model = UptimeMeasurement(ai_key=AI_KEY)
        self.assertEqual(
            code_of(lambda: model.bind_schedule(build_schedule(), "00" * 32)),
            "INVALID_BOUND_SCHEDULE",
        )

    def test_rebinding_is_a_replay(self) -> None:
        model = bound_model()
        schedule = build_schedule()
        self.assertEqual(
            code_of(lambda: model.bind_schedule(schedule, schedule.state_digest())), "REPLAY"
        )

    def test_an_unbound_model_executes_nothing(self) -> None:
        model = UptimeMeasurement(ai_key=AI_KEY)
        self.assertEqual(
            code_of(lambda: model.execute_block(0, beacon_for(0))), "SCHEDULE_NOT_BOUND"
        )

    def test_the_binding_proves_consistency_and_not_provenance(self) -> None:
        """An invented but self-consistent schedule binds, as the ADR records."""
        invented = CycleBoundary()
        invented.record_activation(0, 999)
        model = UptimeMeasurement(ai_key=AI_KEY)
        model.bind_schedule(invented, invented.state_digest())
        self.assertEqual(model.bound_schedule_digest, invented.state_digest())


class ScopeTest(unittest.TestCase):
    def test_a_seat_activated_inside_a_window_is_out_of_scope_there(self) -> None:
        model = bound_model()
        self.assertNotIn(3, model.in_scope(1))
        self.assertIn(3, model.in_scope(2))

    def test_genesis_seats_are_in_scope_from_the_first_full_window(self) -> None:
        model = bound_model()
        self.assertEqual(model.in_scope(0), [])
        self.assertEqual(model.in_scope(1), [0, 1, 2])


class HeightTest(unittest.TestCase):
    def test_heights_execute_in_order(self) -> None:
        model = bound_model()
        advance(model, 4)
        self.assertEqual(code_of(lambda: model.execute_block(4, beacon_for(4))), "HEIGHT_NOT_MONOTONIC")
        self.assertEqual(code_of(lambda: model.execute_block(6, beacon_for(6))), "HEIGHT_NOT_MONOTONIC")
        self.assertEqual(code_of(lambda: model.execute_block(5, beacon_for(5))), "ACCEPTED")

    def test_a_height_above_the_bound_is_refused(self) -> None:
        model = bound_model()
        self.assertEqual(
            code_of(lambda: model.execute_block(c.MAX_HEIGHT + 1, beacon_for(0))), "HEIGHT_RANGE"
        )


class DutyEvidenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.model = bound_model()
        advance(self.model, c.CYCLE_BLOCKS)

    def report(self, *reports: DutyReport) -> str:
        height = self.model.height + 1
        return code_of(lambda: self.model.execute_block(height, beacon_for(height), reports))

    def test_a_performed_duty_removes_no_credit(self) -> None:
        self.assertEqual(self.report(DutyReport(0, "VALIDATOR", True)), "ACCEPTED")
        self.assertIn(0, self.model.window_bitmaps[1][0])

    def test_a_failed_duty_clears_the_slot(self) -> None:
        self.assertEqual(self.report(DutyReport(0, "VALIDATOR", False)), "ACCEPTED")
        self.assertNotIn(0, self.model.window_bitmaps[1][0])

    def test_an_empty_assignment_is_satisfied_vacuously(self) -> None:
        """A seat outside the bounded live signing set produces no report.

        Crediting only seats that signed would fail every unselected seat in
        every slot, which contradicts the sentence bounding the signing set.
        """
        self.assertEqual(self.report(), "ACCEPTED")
        self.assertIn(0, self.model.window_bitmaps[1][0])

    def test_an_unknown_kind_is_refused(self) -> None:
        self.assertEqual(self.report(DutyReport(0, "MINING", True)), "INVALID_DUTY_KIND")

    def test_a_repeated_seat_and_kind_is_refused(self) -> None:
        self.assertEqual(
            self.report(DutyReport(0, "VALIDATOR", True), DutyReport(0, "VALIDATOR", False)),
            "DUTY_REPLAY",
        )

    def test_both_kinds_for_one_seat_are_accepted(self) -> None:
        self.assertEqual(
            self.report(DutyReport(0, "VALIDATOR", True), DutyReport(0, "SERVICING", True)),
            "ACCEPTED",
        )

    def test_a_seat_outside_the_range_is_refused(self) -> None:
        self.assertEqual(
            self.report(DutyReport(c.FOUNDER_SEAT_CAPACITY, "VALIDATOR", True)), "SEAT_RANGE"
        )

    def test_a_seat_out_of_scope_is_refused(self) -> None:
        self.assertEqual(self.report(DutyReport(3, "VALIDATOR", True)), "SEAT_NOT_IN_SCOPE")

    def test_a_rejected_block_writes_nothing(self) -> None:
        """Containment measured on one model instance, before and after.

        Comparing two separately built models would prove the model is
        deterministic rather than that a rejected block wrote nothing.
        """
        before = self.model.state_digest()
        height = self.model.height
        self.report(DutyReport(0, "MINING", True))
        self.assertEqual(self.model.state_digest(), before)
        self.assertEqual(self.model.height, height)


class ChallengeResponseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.model = bound_model()
        self.challenge = self.first_challenge(0)
        # Selection is unpredictable, so the first challenge is not necessarily
        # in slot 0. Every boundary here is taken against its own slot.
        self.slot = slot_of_height(self.challenge)
        self.slot_last = slot_last_height(1, self.slot)

    def first_challenge(self, seat_id: int) -> int:
        height = c.CYCLE_BLOCKS
        advance(self.model, height - 1)
        while True:
            self.model.execute_block(height, beacon_for(height))
            if is_selected(seat_id, height, beacon_for(height)):
                return height
            height += 1

    def test_an_issued_challenge_is_answerable(self) -> None:
        self.assertEqual(code_of(lambda: self.model.submit_response(0, self.challenge, True)), "ACCEPTED")

    def test_a_seat_cannot_answer_a_challenge_it_was_not_issued(self) -> None:
        self.assertEqual(
            code_of(lambda: self.model.submit_response(1, self.challenge, True)),
            "CHALLENGE_NOT_ISSUED",
        )

    def test_a_seat_cannot_answer_twice(self) -> None:
        self.model.submit_response(0, self.challenge, True)
        self.assertEqual(
            code_of(lambda: self.model.submit_response(0, self.challenge, True)), "RESPONSE_REPLAY"
        )

    def test_a_wrong_answer_is_refused(self) -> None:
        self.assertEqual(
            code_of(lambda: self.model.submit_response(0, self.challenge, False)), "RESPONSE_INVALID"
        )

    def test_the_deadline_boundary_is_inclusive(self) -> None:
        advance(self.model, self.challenge + c.RESPONSE_DEADLINE_BLOCKS)
        self.assertEqual(
            code_of(lambda: self.model.submit_response(0, self.challenge, True)), "ACCEPTED"
        )

    def test_one_height_past_the_deadline_is_refused(self) -> None:
        advance(self.model, self.challenge + c.RESPONSE_DEADLINE_BLOCKS + 1)
        self.assertEqual(
            code_of(lambda: self.model.submit_response(0, self.challenge, True)),
            "RESPONSE_TOO_LATE",
        )

    def test_a_challenge_from_a_closed_slot_is_refused(self) -> None:
        advance(self.model, self.slot_last + 1)
        self.assertEqual(
            code_of(lambda: self.model.submit_response(0, self.challenge, True)),
            "CHALLENGE_NOT_OPEN",
        )

    def test_an_unanswered_challenge_clears_the_slot_at_close(self) -> None:
        advance(self.model, self.slot_last + 1)
        self.assertNotIn(self.slot, self.model.window_bitmaps[1][0])

    def test_an_answered_challenge_keeps_the_slot(self) -> None:
        self.model.submit_response(0, self.challenge, True)
        for height in range(self.challenge + 1, self.slot_last + 1):
            self.model.execute_block(height, beacon_for(height))
            if is_selected(0, height, beacon_for(height)):
                self.model.submit_response(0, height, True)
        advance(self.model, self.slot_last + 1)
        self.assertIn(self.slot, self.model.window_bitmaps[1][0])

    def test_the_counters_are_discarded_at_a_slot_boundary(self) -> None:
        advance(self.model, self.slot_last + 1)
        self.assertEqual(self.model.slot_issued, {})
        self.assertEqual(self.model.slot_answered, {})


class DisputeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.model = run(windows=1, stop_height=2 * c.CYCLE_BLOCKS + 1).model

    def test_the_window_is_closed_but_not_final(self) -> None:
        self.assertIn(1, self.model.closed_windows)
        self.assertFalse(self.model.is_final(1))

    def test_only_the_ai_key_may_dispute(self) -> None:
        self.assertEqual(
            code_of(lambda: self.model.file_dispute(1, 0, 0, "STALE", "someone-else")),
            "UNAUTHORIZED_DISPUTE",
        )

    def test_a_dispute_voids_one_slot(self) -> None:
        before = self.model.credited_slots(1, 0)
        self.model.file_dispute(1, 0, 0, "STALE", AI_KEY)
        self.assertEqual(self.model.credited_slots(1, 0), before - 1)

    def test_a_dispute_cannot_add_credit(self) -> None:
        """Every dispute path can only reduce a result."""
        before = self.model.credited_slots(1, 0)
        for slot in range(c.DISPUTE_CAP_SLOTS_PER_SEAT):
            self.model.file_dispute(1, 0, slot, "STALE", AI_KEY)
            self.assertLess(self.model.credited_slots(1, 0), before)
            before = self.model.credited_slots(1, 0)

    def test_the_same_slot_cannot_be_voided_twice(self) -> None:
        self.model.file_dispute(1, 0, 0, "STALE", AI_KEY)
        self.assertEqual(
            code_of(lambda: self.model.file_dispute(1, 0, 0, "STALE", AI_KEY)), "DISPUTE_REPLAY"
        )

    def test_an_uncredited_slot_cannot_be_voided(self) -> None:
        uncredited = next(
            slot
            for slot in range(c.SLOTS_PER_WINDOW)
            if slot not in self.model.window_bitmaps[1][1]
        )
        self.assertEqual(
            code_of(lambda: self.model.file_dispute(1, 1, uncredited, "STALE", AI_KEY)),
            "DISPUTE_SLOT_NOT_CREDITED",
        )

    def test_the_cap_is_the_grace_allowance(self) -> None:
        for slot in range(c.DISPUTE_CAP_SLOTS_PER_SEAT):
            self.model.file_dispute(1, 0, slot, "STALE", AI_KEY)
        self.assertEqual(
            code_of(
                lambda: self.model.file_dispute(
                    1, 0, c.DISPUTE_CAP_SLOTS_PER_SEAT, "STALE", AI_KEY
                )
            ),
            "DISPUTE_CAP_EXCEEDED",
        )

    def test_a_perfect_seat_survives_a_maximal_dispute(self) -> None:
        """The containment theorem at its boundary.

        The AI can consume an operator's whole allowance and cannot by itself
        fail a node that was fully operational.
        """
        self.assertEqual(self.model.credited_slots(1, 0), c.SLOTS_PER_WINDOW)
        for slot in range(c.DISPUTE_CAP_SLOTS_PER_SEAT):
            self.model.file_dispute(1, 0, slot, "STALE", AI_KEY)
        self.assertEqual(self.model.credited_slots(1, 0), c.ACTIVITY_THRESHOLD_SLOTS)
        self.assertGreaterEqual(self.model.uptime_seconds(1, 0), 64_800)

    def test_a_seat_out_of_scope_cannot_be_disputed(self) -> None:
        self.assertEqual(
            code_of(lambda: self.model.file_dispute(1, 3, 0, "STALE", AI_KEY)),
            "SEAT_NOT_IN_SCOPE",
        )

    def test_a_slot_outside_the_window_is_refused(self) -> None:
        self.assertEqual(
            code_of(lambda: self.model.file_dispute(1, 0, c.SLOTS_PER_WINDOW, "STALE", AI_KEY)),
            "SLOT_RANGE",
        )

    def test_an_unclosed_window_cannot_be_disputed(self) -> None:
        self.assertEqual(
            code_of(lambda: self.model.file_dispute(7, 0, 0, "STALE", AI_KEY)),
            "WINDOW_NOT_CLOSED",
        )

    def test_a_reason_code_carries_no_protocol_effect(self) -> None:
        other = run(windows=1, stop_height=2 * c.CYCLE_BLOCKS + 1).model
        self.model.file_dispute(1, 0, 0, "STALE", AI_KEY)
        other.file_dispute(1, 0, 0, "A COMPLETELY DIFFERENT REASON", AI_KEY)
        self.assertEqual(self.model.state_digest(), other.state_digest())


class FinalisationTest(unittest.TestCase):
    def test_silence_finalises_without_a_signature(self) -> None:
        result = run(windows=1)
        self.assertTrue(result.model.is_final(1))
        self.assertEqual(result.model.disputed, {})

    def test_a_final_window_cannot_be_disputed(self) -> None:
        model = run(windows=1).model
        self.assertEqual(
            code_of(lambda: model.file_dispute(1, 0, 0, "STALE", AI_KEY)),
            "DISPUTE_WINDOW_CLOSED",
        )

    def test_a_record_before_finalisation_is_refused(self) -> None:
        model = run(windows=1, stop_height=2 * c.CYCLE_BLOCKS + 1).model
        self.assertEqual(code_of(lambda: model.emit_record(1)), "RECORD_NOT_FINAL")

    def test_a_window_with_no_seats_emits_nothing(self) -> None:
        model = run(windows=1).model
        self.assertEqual(code_of(lambda: model.emit_record(0)), "WINDOW_HAS_NO_SEATS")


class RecordTest(unittest.TestCase):
    def setUp(self) -> None:
        self.result = run(windows=2)
        self.record = self.result.model.emit_record(1)

    def test_the_seat_set_is_the_in_scope_set(self) -> None:
        self.assertEqual(
            [seat for seat, _ in self.record.entries], self.result.model.in_scope(1)
        )

    def test_an_omission_is_unrepresentable(self) -> None:
        """The set is derived from the schedule rather than supplied."""
        self.assertEqual(len(self.record.entries), 3)
        self.assertEqual([seat for seat, _ in self.record.entries], [0, 1, 2])

    def test_every_value_is_whole_slots(self) -> None:
        for _, seconds in self.record.entries:
            self.assertEqual(seconds % c.SLOT_SECONDS, 0)

    def test_no_value_exceeds_a_window(self) -> None:
        for _, seconds in self.record.entries:
            self.assertLessEqual(seconds, 86_400)

    def test_a_perfect_seat_reaches_the_full_window(self) -> None:
        self.assertEqual(dict(self.record.entries)[0], 86_400)

    def test_a_silent_seat_fails_the_cycle(self) -> None:
        """Sampling alone fails a node that answers nothing."""
        self.assertLess(dict(self.record.entries)[1], 64_800)

    def test_the_record_shape_matches_the_economy_input(self) -> None:
        supplied = self.record.as_economy_input()
        self.assertEqual(set(supplied), {"cycle_window", "entries"})
        for entry in supplied["entries"]:
            self.assertEqual(set(entry), {"seat_id", "uptime_seconds"})

    def test_the_record_carries_no_verdict(self) -> None:
        """A measurement cannot express an answer, only a measurement."""
        supplied = self.record.as_economy_input()
        for entry in supplied["entries"]:
            self.assertNotIn("active", entry)
            self.assertNotIn("winners", entry)
            self.assertNotIn("met_cycle", entry)


class DeterminismTest(unittest.TestCase):
    def test_two_runs_agree(self) -> None:
        self.assertEqual(run(windows=1).model.state_digest(), run(windows=1).model.state_digest())

    def test_a_prefix_reproduces_the_state_it_held(self) -> None:
        prefix = run(windows=1, stop_height=2 * c.CYCLE_BLOCKS + 1).model
        again = run(windows=1, stop_height=2 * c.CYCLE_BLOCKS + 1).model
        self.assertEqual(prefix.state_digest(), again.state_digest())

    def test_the_state_digest_changes_when_credit_changes(self) -> None:
        model = run(windows=1, stop_height=2 * c.CYCLE_BLOCKS + 1).model
        before = model.state_digest()
        model.file_dispute(1, 0, 0, "STALE", AI_KEY)
        self.assertNotEqual(model.state_digest(), before)


class InvariantTest(unittest.TestCase):
    def test_a_cap_that_breaks_containment_is_refused(self) -> None:
        """Invariant 5 is asserted rather than left to the cap arithmetic."""
        model = run(windows=1, stop_height=2 * c.CYCLE_BLOCKS + 1).model
        voided = model.disputed.setdefault(1, {}).setdefault(0, set())
        voided.update(range(c.GRACE_ALLOWANCE_SLOTS + 1))
        with self.assertRaises(InvariantError):
            model._assert_dispute_containment(1, 0)

    def test_uptime_never_exceeds_a_window(self) -> None:
        model = run(windows=1).model
        for seat in model.in_scope(1):
            self.assertLessEqual(model.uptime_seconds(1, seat), 86_400)

    def test_a_non_integer_input_is_an_input_shape_error(self) -> None:
        model = bound_model()
        with self.assertRaises(InvariantError):
            model.execute_block("0", beacon_for(0))


if __name__ == "__main__":
    unittest.main()
