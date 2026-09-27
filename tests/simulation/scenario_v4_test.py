#!/usr/bin/env python3
"""Version-four suite tests: every seat's whole life through the current contract.

The verifier compares the recorded run with its closed form. These test what a
comparison cannot:

- the schedule is the one the specification describes;
- the per-window checks catch the defects they exist for;
- a replayed prefix reaches the root the whole run held there;
- the ADR 0094 repair is exercised at population scale.
"""

from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "tools" / "scenario-suite-vectors")
)

import expected_v4 as x
import verify_v4
from checker import Checker, read_vectors
from population_checks_v4 import check_population

from simulation.calendar.civil import days_from_civil
from simulation.economy_transition_v6.ledger import ReferralBalance
from simulation.economy_transition_v9 import contract as c
from simulation.economy_transition_v9.ledger import ConservationFailure
from simulation.economy_transition_v9.settlement import Settlement
from simulation.scenarios import economy_population_v4 as population
from simulation.scenarios.economy_schedule_v4 import RECORDED

ROOT = Path(__file__).resolve().parents[2]
VECTORS = ROOT / "test-vectors" / "economy-scenario-suite-v4.txt"

_RUN: list[population.PopulationRun] = []


def recorded_run() -> population.PopulationRun:
    """The whole run takes about two seconds, so it is run once and shared."""
    if not _RUN:
        _RUN.append(population.PopulationRun().run())
    return _RUN[0]


def zero_mark_run() -> population.PopulationRun:
    """The recorded population with ADR 0094's defect restored in the model."""
    if len(_RUN) < 2:
        recorded_run()
        zero = mock.patch(
            "simulation.economy_transition_v7.ledger.first_referral_balance",
            lambda _window: ReferralBalance(),
        )
        with zero:
            _RUN.append(population.PopulationRun().run())
    return _RUN[1]


class ScheduleTest(unittest.TestCase):
    def test_every_seat_runs_all_731_cycles_before_the_end(self) -> None:
        for seat in RECORDED.seats:
            self.assertLess(RECORDED.last_cycle_window(seat), RECORDED.end_window - 2)
        self.assertEqual(recorded_run().ledger.assigned_permissions,
                         len(RECORDED.seats) * c.ISSUANCE_CYCLES_PER_SEAT)

    def test_every_referrer_is_first_credited_after_the_cap(self) -> None:
        """The case ADR 0094 repaired, for every referrer in the population."""
        for referrer in RECORDED.referrers:
            first = min(
                RECORDED.first_cycle_window(seat)
                for seat, (_owner, by) in RECORDED.seats.items()
                if by == referrer
            )
            self.assertGreater(first, c.MINT_ACCUMULATION_CAP)

    def test_the_run_crosses_a_leap_day(self) -> None:
        # Window w opens at the start of day w after genesis.
        leap_window = days_from_civil(2028, 2, 29) - days_from_civil(2027, 1, 1)
        self.assertLess(leap_window, RECORDED.end_window)
        february = [
            window for window in range(RECORDED.end_window)
            if RECORDED.window_month(window) == RECORDED.window_month(leap_window)
        ]
        self.assertEqual(len(february), 29)

    def test_one_window_is_one_day_at_the_commit_target(self) -> None:
        self.assertEqual(
            RECORDED.stamp(c.CYCLE_BLOCKS) - RECORDED.stamp(0), 86_400_000
        )

    def test_each_lapse_really_exceeds_the_cap(self) -> None:
        seat, first, last = RECORDED.seat_lapse
        mints = [w for w in range(RECORDED.end_window) if RECORDED.node_mints(seat, w)]
        gap = min(w for w in mints if w >= last) - max(w for w in mints if w < first)
        self.assertGreater(gap, c.MINT_ACCUMULATION_CAP + c.ASSIGNMENT_LAG_WINDOWS)
        person, first, last = RECORDED.referrer_lapse
        mints = [w for w in range(RECORDED.end_window)
                 if RECORDED.referral_mints(person, w)]
        gap = min(w for w in mints if w >= last) - max(w for w in mints if w < first)
        self.assertGreater(gap, c.MINT_ACCUMULATION_CAP + c.ASSIGNMENT_LAG_WINDOWS)


class ClaimsTest(unittest.TestCase):
    """The audit's four claims, read off the finished run."""

    def test_the_recovery_pool_drains_once_the_drain_window_is_won(self) -> None:
        run = recorded_run()
        self.assertGreater(run.observed.peak_recovery_pool, 0)
        self.assertEqual(sum(run.ledger.pool.values()), 0)

    def test_nothing_is_left_outstanding(self) -> None:
        self.assertEqual(sum(recorded_run().ledger.channel_outstanding.values()), 0)

    def test_every_month_settled_and_every_claim_was_collected(self) -> None:
        run = recorded_run()
        self.assertEqual(len(run.observed.settlements), 35)
        for seat, (accrued, minted) in run.ledger.claims.items():
            with self.subTest(seat=seat):
                self.assertEqual(accrued, minted)

    def test_the_hoarder_collected_every_month_at_once(self) -> None:
        run = recorded_run()
        accrued, minted = run.ledger.claim(RECORDED.pool_hoarder)
        winning_months = sum(
            1 for _w, settled in run.observed.settlements
            if RECORDED.pool_hoarder in settled.winners and settled.share
        )
        self.assertGreater(winning_months, 1)
        self.assertEqual(accrued, minted)

    def test_a_settlement_paying_the_wrong_seat_is_refused(self) -> None:
        wrong = Settlement(700, 2, 10, (1,), 100, 100, 0, 100)
        with self.assertRaises(ConservationFailure):
            population._require_best_performers(wrong, {0: 10, 1: 5}, (0, 1))

    def test_a_settlement_ignoring_a_candidate_that_ran_nothing_is_refused(self) -> None:
        wrong = Settlement(700, 1, 0, (0,), 100, 100, 0, 100)
        with self.assertRaises(ConservationFailure):
            population._require_best_performers(wrong, {}, (0, 1))


class RestartTest(unittest.TestCase):
    def test_a_replayed_prefix_reaches_the_root_the_whole_run_held(self) -> None:
        run = recorded_run()
        for window in (100, 430, RECORDED.last_cycle_window(0)):
            with self.subTest(window=window):
                prefix = population.PopulationRun(stop_window=window).run()
                self.assertEqual(prefix.observed.roots[window], run.observed.roots[window])

    def test_two_runs_reach_the_same_final_root(self) -> None:
        again = population.PopulationRun().run()
        end = RECORDED.end_window
        self.assertEqual(again.observed.roots[end], recorded_run().observed.roots[end])


class FailsClosedTest(unittest.TestCase):
    """The verifier's refusals, each against the unmutated run as control."""

    def verify(self, run, recorded: dict[str, str], p=None) -> list[str]:
        check = Checker(recorded)
        check_population(check, x, run, p)
        check.require_full_coverage()
        return check.failures

    def test_the_recorded_file_passes(self) -> None:
        self.assertEqual(self.verify(recorded_run(), read_vectors(VECTORS)), [])

    def test_a_tampered_value_fails(self) -> None:
        recorded = read_vectors(VECTORS)
        recorded["referral.5.accrued"] = str(int(recorded["referral.5.accrued"]) + 1)
        self.assertTrue(any("referral.5.accrued" in f for f in
                            self.verify(recorded_run(), recorded)))

    def test_a_key_nothing_derives_fails(self) -> None:
        recorded = read_vectors(VECTORS) | {"channel.9.issued": "0"}
        self.assertIn("channel.9.issued: recorded but never derived",
                      self.verify(recorded_run(), recorded))

    def test_a_derived_key_the_file_lacks_fails(self) -> None:
        recorded = read_vectors(VECTORS)
        del recorded["recovery_pool.peak"]
        self.assertIn("recovery_pool.peak: not recorded in the vector file",
                      self.verify(recorded_run(), recorded))

    def test_the_version_three_file_fails(self) -> None:
        recorded = read_vectors(ROOT / "test-vectors" / "economy-scenario-suite-v3.txt")
        self.assertTrue(self.verify(recorded_run(), recorded))

    def test_the_zero_referral_mark_fails_against_the_closed_form(self) -> None:
        """ADR 0094's defect, restored in the model, is refused by the walk."""
        failures = self.verify(zero_mark_run(), read_vectors(VECTORS))
        self.assertTrue(any(f.startswith("referral.forfeited_legs") for f in failures))
        self.assertTrue(any(f.startswith("referral.0.accrued") for f in failures))

    def test_emitting_refuses_to_record_a_disagreement(self) -> None:
        emitter = verify_v4.Emitter()
        check_population(emitter, x, zero_mark_run())
        self.assertTrue(emitter.failures)
        control = verify_v4.Emitter()
        check_population(control, x, recorded_run())
        self.assertEqual(control.failures, [])
        self.assertEqual(len(control.lines), len(read_vectors(VECTORS)))

    def test_a_walk_without_the_cap_fails_where_totals_cannot_see_it(self) -> None:
        """Every channel total survives ignoring the cap; the counts do not."""
        # A copy of the recorded fixture, so the walk is not the cached one.
        uncapped = replace(x.RECORDED)
        with mock.patch.object(x, "MINT_ACCUMULATION_CAP", 10**9):
            failures = self._walk_failures(uncapped)
        self.assertTrue(any("over_cap_seat_windows" in f for f in failures))
        self.assertFalse(any(".promised" in f for f in failures))

    def _walk_failures(self, p) -> list[str]:
        check = Checker(read_vectors(VECTORS))
        check_population(check, x, recorded_run(), p)
        return check.failures


if __name__ == "__main__":
    unittest.main()
