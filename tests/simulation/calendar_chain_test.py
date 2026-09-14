#!/usr/bin/env python3
"""The calendar-v1 acceptance rules and the month over a chain of heights."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.calendar import contract as c
from simulation.calendar import months, scenario
from simulation.calendar.chain import Calendar
from simulation.common.canonical import CodedError, InvariantError

# 2026-01-31T23:59:00.000Z, the scenario's genesis.
GENESIS = scenario.millis_of(scenario.GENESIS_INSTANT)


def code_of(call) -> str:
    try:
        call()
    except CodedError as error:
        return error.code
    return "ACCEPTED"


class AcceptanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.chain = Calendar(GENESIS)

    def test_a_chain_begins_at_height_one_with_genesis_as_its_predecessor(self) -> None:
        self.assertEqual(self.chain.head_height, c.GENESIS_HEIGHT)
        self.assertEqual(self.chain.next_height, c.FIRST_BLOCK_HEIGHT)
        self.assertEqual(self.chain.head_timestamp, GENESIS)

    def test_the_first_block_may_equal_genesis_and_may_not_precede_it(self) -> None:
        self.assertEqual(
            code_of(lambda: Calendar(GENESIS).accept(1, GENESIS, GENESIS)), "ACCEPTED"
        )
        self.assertEqual(
            code_of(lambda: Calendar(GENESIS).accept(1, GENESIS - 1, GENESIS - 1)),
            "TIMESTAMP_NOT_MONOTONIC",
        )

    def test_a_repeated_timestamp_is_accepted(self) -> None:
        self.chain.accept(1, GENESIS, GENESIS)
        self.assertEqual(code_of(lambda: self.chain.accept(2, GENESIS, GENESIS)), "ACCEPTED")

    def test_only_the_next_height_is_accepted(self) -> None:
        self.chain.accept(1, GENESIS, GENESIS)
        for height in (1, 3, 0, 99):
            self.assertEqual(
                code_of(lambda h=height: self.chain.accept(h, GENESIS, GENESIS)),
                "HEIGHT_NOT_NEXT",
            )

    def test_the_tolerance_is_inclusive_on_both_sides(self) -> None:
        tolerance = c.TIMESTAMP_TOLERANCE_MILLIS
        for offset, expected in (
            (tolerance, "ACCEPTED"),
            (-tolerance, "ACCEPTED"),
            (tolerance + 1, "TIMESTAMP_BEHIND_TOLERANCE"),
            (-tolerance - 1, "TIMESTAMP_AHEAD_OF_TOLERANCE"),
        ):
            chain = Calendar(GENESIS)
            self.assertEqual(
                code_of(lambda o=offset: chain.accept(1, GENESIS, GENESIS + o)), expected
            )

    def test_the_rejection_order_is_the_stated_one(self) -> None:
        self.chain.accept(1, GENESIS, GENESIS)
        tolerance = c.TIMESTAMP_TOLERANCE_MILLIS
        # A wrong height wins over an unrepresentable timestamp.
        self.assertEqual(
            code_of(lambda: self.chain.accept(99, c.MAX_TIMESTAMP_MILLIS + 1, GENESIS)),
            "HEIGHT_NOT_NEXT",
        )
        # An unrepresentable timestamp wins over a monotonicity failure, which
        # a negative value also is.
        self.assertEqual(
            code_of(lambda: self.chain.accept(2, -1, GENESIS)), "TIMESTAMP_RANGE"
        )
        # A monotonicity failure wins over a tolerance failure.
        self.assertEqual(
            code_of(
                lambda: self.chain.accept(2, GENESIS - 1, GENESIS + tolerance)
            ),
            "TIMESTAMP_NOT_MONOTONIC",
        )

    def test_a_refusal_writes_nothing(self) -> None:
        self.chain.accept(1, GENESIS, GENESIS)
        before = self.chain.state_digest()
        for height, timestamp, clock in (
            (99, GENESIS, GENESIS),
            (2, c.MAX_TIMESTAMP_MILLIS + 1, GENESIS),
            (2, GENESIS - 1, GENESIS - 1),
            (2, GENESIS + c.TIMESTAMP_TOLERANCE_MILLIS + 1, GENESIS),
        ):
            with self.assertRaises(CodedError):
                self.chain.accept(height, timestamp, clock)
        self.assertEqual(self.chain.state_digest(), before)
        self.assertEqual(self.chain.head_height, 1)

    def test_a_genesis_outside_the_range_is_a_defect_rather_than_a_refusal(self) -> None:
        with self.assertRaises(InvariantError):
            Calendar(c.MAX_TIMESTAMP_MILLIS + 1)

    def test_every_modelled_code_is_named_in_the_stated_order(self) -> None:
        self.assertEqual(
            set(c.REJECTION_ORDER), set(c.RESULT_CODES) - {"ACCEPTED"}
        )
        self.assertEqual(
            c.DETERMINISTIC_CODES | c.ADMISSION_ONLY_CODES, set(c.REJECTION_ORDER)
        )
        self.assertEqual(c.DETERMINISTIC_CODES & c.ADMISSION_ONLY_CODES, set())


class ReplayTest(unittest.TestCase):
    def test_a_replay_reaches_the_chain_the_tolerance_admitted(self) -> None:
        chain = scenario.build()
        replayed = scenario.replay(chain)
        self.assertEqual(replayed.state_digest(), chain.state_digest())
        self.assertEqual(replayed.month_indices(), chain.month_indices())

    def test_a_replay_reapplies_the_deterministic_rules(self) -> None:
        chain = Calendar(GENESIS)
        chain.replay(1, GENESIS)
        self.assertEqual(code_of(lambda: chain.replay(1, GENESIS)), "HEIGHT_NOT_NEXT")
        self.assertEqual(
            code_of(lambda: chain.replay(2, GENESIS - 1)), "TIMESTAMP_NOT_MONOTONIC"
        )
        self.assertEqual(
            code_of(lambda: chain.replay(2, c.MAX_TIMESTAMP_MILLIS + 1)),
            "TIMESTAMP_RANGE",
        )

    def test_a_replay_does_not_reapply_the_tolerance(self) -> None:
        # The whole point of the separation: a machine replaying history has no
        # clock to judge a stamp against, and must accept what was admitted.
        replay_code, admission_code = scenario.replay_ignores_the_tolerance(
            scenario.build()
        )
        self.assertEqual(replay_code, "ACCEPTED")
        self.assertEqual(admission_code, "TIMESTAMP_AHEAD_OF_TOLERANCE")


class MonthOverAChainTest(unittest.TestCase):
    def setUp(self) -> None:
        self.chain = scenario.build()

    def test_the_month_index_never_decreases_along_the_chain(self) -> None:
        indices = self.chain.month_indices()
        self.assertEqual(list(indices), sorted(indices))

    def test_the_first_block_opens_a_month_and_closes_nothing(self) -> None:
        self.assertTrue(self.chain.opens_a_month(c.FIRST_BLOCK_HEIGHT))
        self.assertEqual(self.chain.months_closed_by(c.FIRST_BLOCK_HEIGHT), ())

    def test_a_block_opening_a_month_closes_its_predecessors_month(self) -> None:
        self.assertTrue(self.chain.opens_a_month(4))
        self.assertEqual(self.chain.months_closed_by(4), (672,))

    def test_a_halt_across_two_months_closes_all_three_at_once(self) -> None:
        self.assertTrue(self.chain.opens_a_month(6))
        self.assertEqual(self.chain.months_closed_by(6), (673, 674, 675))
        self.assertEqual(self.chain.empty_months(), (674, 675))

    def test_a_block_inside_a_month_opens_and_closes_nothing(self) -> None:
        for height in (2, 3, 5, 7):
            self.assertFalse(self.chain.opens_a_month(height))
            self.assertEqual(self.chain.months_closed_by(height), ())

    def test_every_closed_month_is_closed_exactly_once(self) -> None:
        closed: list[int] = []
        for height in range(c.FIRST_BLOCK_HEIGHT, self.chain.head_height + 1):
            closed.extend(self.chain.months_closed_by(height))
        self.assertEqual(len(closed), len(set(closed)))
        self.assertEqual(closed, sorted(closed))
        # Every month the chain passed through except the one still open.
        first = self.chain.month_of_height(c.FIRST_BLOCK_HEIGHT)
        last = self.chain.month_of_height(self.chain.head_height)
        self.assertEqual(closed, list(range(first, last)))

    def test_the_height_span_of_an_occupied_month(self) -> None:
        self.assertEqual(self.chain.month_height_span(672), (1, 3))
        self.assertEqual(self.chain.month_height_span(673), (4, 5))
        self.assertEqual(self.chain.month_height_span(676), (6, 7))

    def test_an_empty_month_holds_no_heights(self) -> None:
        for index in self.chain.empty_months():
            self.assertIsNone(self.chain.month_height_span(index))

    def test_the_boundary_block_is_one_millisecond_after_its_predecessor(self) -> None:
        # The chain's February opens at the first millisecond of the month and
        # its predecessor is the last of January, so a one-millisecond error in
        # either direction would move the boundary by a whole block.
        self.assertEqual(self.chain.timestamp_of(4) - self.chain.timestamp_of(3), 1)
        self.assertEqual(
            self.chain.timestamp_of(4), months.month_start_millis(673)
        )
        self.assertEqual(self.chain.timestamp_of(3), months.month_end_millis(672))

    def test_a_height_not_in_the_chain_is_a_defect_rather_than_a_refusal(self) -> None:
        for height in (0, self.chain.head_height + 1):
            with self.assertRaises(InvariantError):
                self.chain.timestamp_of(height)

    def test_the_model_is_deterministic_across_repeated_runs(self) -> None:
        self.assertEqual(scenario.build().state_digest(), self.chain.state_digest())


if __name__ == "__main__":
    unittest.main()
