#!/usr/bin/env python3
"""The unreferred pool's monthly ranking, payout, carry, and conservation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import InvariantError
from simulation.cycle_boundary.contract import CYCLE_BLOCKS
from simulation.unreferred_pool import contract as c
from simulation.unreferred_pool import scenario
from simulation.unreferred_pool.ledger import UnreferredPool, Window

FULL = c.WINDOW_UPTIME_SECONDS_MAX


def pool_with(*seats: int) -> UnreferredPool:
    """A pool whose seats are all in scope from window 1."""
    return UnreferredPool({seat: 0 for seat in seats})


class ContractTest(unittest.TestCase):
    def test_the_derivation_is_exact(self) -> None:
        c.assert_exact_derivation()
        self.assertEqual(c.WINDOW_UPTIME_SECONDS_MAX, 86_400)

    def test_a_full_window_is_a_cycle(self) -> None:
        c.assert_agrees_with_cycle_boundary()

    def test_the_slot_figures_are_the_measurement_contract_s(self) -> None:
        c.assert_agrees_with_uptime_measurement()


class RankingTest(unittest.TestCase):
    def test_a_single_best_seat_takes_the_whole_balance(self) -> None:
        pool = pool_with(1, 2)
        pool.assign(Window(1, 10, {1: FULL, 2: FULL // 2}, 100))
        pool.assign(Window(2, 11, {}, 0))
        payout = pool.payouts[0]
        self.assertEqual(payout.winners, (1,))
        self.assertEqual(payout.share, 100)
        self.assertEqual(payout.remainder, 0)

    def test_an_exact_tie_shares_equally(self) -> None:
        pool = pool_with(1, 2)
        pool.assign(Window(1, 10, {1: FULL, 2: FULL}, 100))
        pool.assign(Window(2, 11, {}, 0))
        payout = pool.payouts[0]
        self.assertEqual(payout.winners, (1, 2))
        self.assertEqual(payout.share, 50)
        self.assertEqual(payout.remainder, 0)

    def test_a_share_that_does_not_divide_leaves_a_remainder_in_the_pool(self) -> None:
        pool = pool_with(1, 2, 3)
        pool.assign(Window(1, 10, {1: FULL, 2: FULL, 3: FULL}, 100))
        pool.assign(Window(2, 11, {}, 0))
        payout = pool.payouts[0]
        self.assertEqual(payout.share, 33)
        self.assertEqual(payout.remainder, 1)
        self.assertEqual(pool.payable, 1)
        self.assertLess(payout.remainder, len(payout.winners))

    def test_the_remainder_is_distributed_with_the_next_month_that_pays(self) -> None:
        pool = pool_with(1, 2, 3)
        pool.assign(Window(1, 10, {1: FULL, 2: FULL, 3: FULL}, 100))
        pool.assign(Window(2, 11, {1: FULL}, 2))
        pool.assign(Window(3, 12, {}, 0))
        # Month 11 pays the carried remainder of 1 plus its own accrual of 2.
        self.assertEqual(pool.payouts[1].payable_before, 3)
        self.assertEqual(pool.payouts[1].winners, (1,))

    def test_a_month_where_every_candidate_ran_zero_still_pays(self) -> None:
        # "Where several seats stand at exactly the same top figure - whatever
        # that figure is - they share it equally."
        pool = pool_with(1, 2)
        pool.assign(Window(1, 10, {1: 0, 2: 0}, 100))
        pool.assign(Window(2, 11, {}, 0))
        payout = pool.payouts[0]
        self.assertEqual(payout.best_figure, 0)
        self.assertEqual(payout.winners, (1, 2))
        self.assertEqual(payout.share, 50)

    def test_a_month_with_candidates_and_no_accrual_pays_nothing(self) -> None:
        pool = pool_with(1)
        pool.assign(Window(1, 10, {1: FULL}, 0))
        pool.assign(Window(2, 11, {}, 0))
        payout = pool.payouts[0]
        self.assertEqual(payout.winners, (1,))
        self.assertEqual(payout.share, 0)
        self.assertEqual(pool.claims, {})

    def test_a_zero_share_writes_no_claim(self) -> None:
        pool = pool_with(1)
        pool.assign(Window(1, 10, {1: FULL}, 0))
        pool.assign(Window(2, 11, {}, 0))
        self.assertEqual(pool.claims, {})


class CandidateTest(unittest.TestCase):
    def test_a_seat_that_ran_nothing_is_still_a_candidate(self) -> None:
        pool = pool_with(1, 2)
        pool.assign(Window(1, 10, {1: FULL}, 100))
        self.assertEqual(pool.candidates(10), (1, 2))
        self.assertEqual(pool.figure(10, 2), 0)

    def test_a_seat_joins_at_its_first_cycle_and_never_leaves(self) -> None:
        pool = UnreferredPool({1: 0, 2: 3 * CYCLE_BLOCKS})
        # Seat 2's first cycle window is 4.
        self.assertFalse(pool.in_scope(2, 3))
        self.assertTrue(pool.in_scope(2, 4))
        self.assertTrue(pool.in_scope(2, 10_000_000))

    def test_uptime_from_a_seat_not_yet_in_scope_is_a_defect(self) -> None:
        pool = UnreferredPool({1: 0, 2: 3 * CYCLE_BLOCKS})
        with self.assertRaises(InvariantError):
            pool.assign(Window(1, 10, {2: FULL}, 0))

    def test_a_window_cannot_report_more_than_a_full_window(self) -> None:
        pool = pool_with(1)
        with self.assertRaises(InvariantError):
            pool.assign(Window(1, 10, {1: FULL + 1}, 0))


class CarryTest(unittest.TestCase):
    def test_a_month_with_no_candidate_pays_nothing_and_keeps_the_balance(self) -> None:
        # Month 10 holds a window; month 11 holds none, so nothing closes into
        # it and it has no candidate when month 12 closes it.
        pool = pool_with(1)
        pool.assign(Window(1, 10, {1: FULL}, 100))
        pool.assign(Window(2, 12, {1: FULL}, 0))
        carried = [p for p in pool.payouts if p.carried]
        self.assertEqual([p.month for p in carried], [11])
        self.assertEqual(pool.payable, 0)

    def test_several_months_close_in_ascending_order(self) -> None:
        pool = pool_with(1)
        pool.assign(Window(1, 10, {1: FULL}, 100))
        pool.assign(Window(2, 13, {1: FULL}, 0))
        self.assertEqual([p.month for p in pool.payouts], [10, 11, 12])

    def test_a_carried_month_that_held_accrual_is_a_defect(self) -> None:
        # The theorem: in-span is a subset of in-scope, so a month that accrued
        # has a candidate. A model reaching the contrary has a broken
        # derivation rather than a working carry.
        pool = UnreferredPool({1: 10 * CYCLE_BLOCKS})
        pool.assign(Window(1, 10, {}, 0))
        pool.figures[(11, 1)] = FULL
        with self.assertRaises(InvariantError):
            pool.assign(Window(2, 12, {}, 0))


class SequenceTest(unittest.TestCase):
    def test_windows_are_assigned_in_ascending_order(self) -> None:
        pool = pool_with(1)
        pool.assign(Window(2, 10, {1: FULL}, 0))
        for index in (2, 1, 0):
            with self.assertRaises(InvariantError):
                pool.assign(Window(index, 10, {}, 0))

    def test_a_month_may_not_go_backwards(self) -> None:
        pool = pool_with(1)
        pool.assign(Window(1, 10, {1: FULL}, 0))
        with self.assertRaises(InvariantError):
            pool.assign(Window(2, 9, {}, 0))

    def test_only_one_month_ever_accumulates(self) -> None:
        pool = UnreferredPool(scenario.ACTIVATIONS)
        for window in scenario.windows():
            pool.assign(window)
            self.assertLessEqual(len({month for month, _seat in pool.figures}), 1)


class ConservationTest(unittest.TestCase):
    def test_the_recorded_run_conserves_after_every_assignment(self) -> None:
        pool = UnreferredPool(scenario.ACTIVATIONS)
        for window in scenario.windows():
            pool.assign(window)
            pool.assert_conserved()

    def test_the_recorded_run_is_deterministic(self) -> None:
        self.assertEqual(scenario.build().state_digest(), scenario.build().state_digest())

    def test_accrued_equals_payable_plus_assigned(self) -> None:
        pool = scenario.build()
        self.assertEqual(pool.accrued, pool.payable + pool.assigned)

    def test_a_broken_balance_is_caught(self) -> None:
        pool = scenario.build()
        pool.payable += 1
        with self.assertRaises(InvariantError):
            pool.assert_conserved()

    def test_assign_checks_conservation_itself(self) -> None:
        # Without this the guard inside `assign` has no test that can fail it:
        # every other check calls `assert_conserved` directly, so deleting the
        # call would pass the whole suite. The state is corrupted between two
        # assignments and the next one must refuse.
        pool = pool_with(1)
        pool.assign(Window(1, 10, {1: FULL}, 100))
        pool.payable += 7
        with self.assertRaises(InvariantError):
            pool.assign(Window(2, 10, {1: FULL}, 0))


class AttributionTest(unittest.TestCase):
    def test_the_fixture_has_a_window_that_straddles_a_month_boundary(self) -> None:
        self.assertEqual(scenario.straddling_windows(), (1,))

    def test_a_straddling_window_belongs_to_the_month_it_began_in(self) -> None:
        first_month = scenario.months_touched()[0]
        straddler = scenario.windows()[1]
        self.assertEqual(straddler.index, 1)
        self.assertEqual(straddler.month, first_month)

    def test_the_rejected_rule_would_give_a_different_answer(self) -> None:
        first_month = scenario.months_touched()[0]
        pool = scenario.build()
        under_rejected = scenario.figures_under_last_height_attribution(first_month)
        self.assertNotEqual(under_rejected, {1: FULL})
        self.assertEqual(pool.payouts[0].best_figure, FULL)


if __name__ == "__main__":
    unittest.main()
