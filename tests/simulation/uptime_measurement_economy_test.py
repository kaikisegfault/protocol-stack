#!/usr/bin/env python3
"""The join: a record this pipeline emits is accepted by economy v2 unchanged.

This is the claim that decided the slice order. If the pipeline's output needed
any adjustment to be an economy input, the record's shape would change twice and
M3.6 would cost two economy contract versions instead of one. Nothing here edits
an accepted artifact; it runs the accepted model on this model's output.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.founder_economy_v2 import contract as ec
from simulation.founder_economy_v2.engine import simulate
from simulation.uptime_measurement import contract as c
from tests.simulation.uptime_measurement_common import AI_KEY, beacon_for, scenario
from tests.simulation.founder_economy_v2_common import (
    activate,
    codes,
    evaluate,
    manifest,
)


class RecordAcceptedByEconomyTest(unittest.TestCase):
    """The emitted record drives a real economy evaluation."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.result = scenario(windows=2)
        cls.record = cls.result.model.emit_record(1).as_economy_input()

    def economy_run(self, seat_id: int, cycle_index: int = 0) -> dict:
        events = [activate(seat) for seat in self.result.model.in_scope(1)]
        events.append(evaluate(seat_id, cycle_index, self.record))
        return simulate(manifest(), events)

    def test_the_economy_accepts_the_emitted_record(self) -> None:
        result = self.economy_run(0)
        self.assertEqual(codes(result)[-1], "OK")

    def test_no_uptime_record_code_is_reached(self) -> None:
        """The three record failures exist for a malformed input, not for ours."""
        result = self.economy_run(0)
        for code in ("MISSING_UPTIME_RECORD", "INVALID_UPTIME_RECORD", "INCONSISTENT_UPTIME_RECORD"):
            self.assertNotIn(code, codes(result))

    def test_every_in_scope_seat_evaluates(self) -> None:
        for seat_id in self.result.model.in_scope(1):
            self.assertEqual(codes(self.economy_run(seat_id))[-1], "OK")

    def test_the_denominations_agree(self) -> None:
        """Whole slots are a strict subset of the range economy v2 validates."""
        self.assertEqual(c.SLOT_SECONDS * c.SLOTS_PER_WINDOW, ec.CYCLE_TARGET_SECONDS)
        self.assertEqual(
            c.ACTIVITY_THRESHOLD_SLOTS * c.SLOT_SECONDS, ec.ACTIVITY_THRESHOLD_SECONDS
        )
        for entry in self.record["entries"]:
            self.assertLessEqual(entry["uptime_seconds"], ec.CYCLE_TARGET_SECONDS)
            self.assertEqual(entry["uptime_seconds"] % c.SLOT_SECONDS, 0)

    def test_the_activity_verdicts_agree(self) -> None:
        """Both models decide the same seats met the cycle, from one measurement."""
        for entry in self.record["entries"]:
            measured = entry["uptime_seconds"] >= ec.ACTIVITY_THRESHOLD_SECONDS
            slots = self.result.model.credited_slots(1, entry["seat_id"])
            self.assertEqual(measured, slots >= c.ACTIVITY_THRESHOLD_SLOTS)

    def test_the_record_reaches_a_real_reallocation(self) -> None:
        """The silent seat fails, so its Founder portion is reallocated.

        The winner set is derived by the economy model from this pipeline's
        measurements rather than supplied, which is the whole point of both.
        """
        silent = 1
        self.assertLess(dict(
            (entry["seat_id"], entry["uptime_seconds"]) for entry in self.record["entries"]
        )[silent], ec.ACTIVITY_THRESHOLD_SECONDS)
        result = self.economy_run(silent)
        self.assertEqual(codes(result)[-1], "OK")


class CompletenessTest(unittest.TestCase):
    """What the economy model cannot detect, and what this pipeline prevents."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.result = scenario(windows=2)
        cls.record = cls.result.model.emit_record(1).as_economy_input()

    def test_the_economy_accepts_a_record_missing_seats(self) -> None:
        """The gap being closed, demonstrated rather than described.

        A truncated record is still valid to the economy model, which is why
        completeness has to be established where the record is produced.
        """
        truncated = {
            "cycle_window": self.record["cycle_window"],
            "entries": [self.record["entries"][0]],
        }
        events = [activate(seat) for seat in self.result.model.in_scope(1)]
        events.append(evaluate(0, 0, truncated))
        self.assertEqual(codes(simulate(manifest(), events))[-1], "OK")

    def test_the_pipeline_cannot_emit_that_record(self) -> None:
        """The seat set is derived from the schedule, so an omission has no form."""
        emitted = [entry["seat_id"] for entry in self.record["entries"]]
        self.assertEqual(emitted, self.result.model.in_scope(1))
        self.assertEqual(len(emitted), 3)


class DisputeReachesTheEconomyTest(unittest.TestCase):
    """A bounded dispute changes a measurement and nothing else."""

    def test_a_maximal_dispute_leaves_a_perfect_seat_meeting_its_cycle(self) -> None:
        """Filed in the open dispute window, then finalised by expiry.

        The whole path runs: the window closes, the AI consumes the entire cap
        against a seat credited for every slot, silence finalises the result,
        and the economy model still evaluates that seat as having met its cycle.
        """
        model = scenario(windows=1, stop_height=2 * c.CYCLE_BLOCKS + 1).model
        self.assertEqual(model.credited_slots(1, 0), c.SLOTS_PER_WINDOW)
        for slot in range(c.DISPUTE_CAP_SLOTS_PER_SEAT):
            model.file_dispute(1, 0, slot, "STALE", AI_KEY)

        for height in range(model.height + 1, 3 * c.CYCLE_BLOCKS + 1):
            model.execute_block(height, beacon_for(height))
        self.assertTrue(model.is_final(1))

        record = model.emit_record(1).as_economy_input()
        disputed = {
            entry["seat_id"]: entry["uptime_seconds"] for entry in record["entries"]
        }[0]
        self.assertEqual(disputed, ec.ACTIVITY_THRESHOLD_SECONDS)

        events = [activate(seat) for seat in model.in_scope(1)]
        events.append(evaluate(0, 0, record))
        self.assertEqual(codes(simulate(manifest(), events))[-1], "OK")


if __name__ == "__main__":
    unittest.main()
