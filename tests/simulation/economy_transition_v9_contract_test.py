#!/usr/bin/env python3
"""Version nine's contract half: the clock, the state surface, and the settlement.

The recorded vectors cover one scenario twice. These cover the properties a
scenario cannot: that the two calendar paths differ in exactly one respect, that
the single pass and the loop agree over inputs the fixture does not contain, that
every refusal a decoder owes is reachable, and that each binding to an accepted
model is the model's answer rather than a lookalike.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.common.canonical import CodedError, InvariantError
from simulation.economy_transition_v8 import contract as v8c
from simulation.economy_transition_v8 import state as v8state
from simulation.economy_transition_v9 import contract as c
from simulation.economy_transition_v9 import (
    envelope,
    genesis,
    header,
    scenario,
    settlement,
    state,
    timeline,
)


class CarryoverTest(unittest.TestCase):
    def test_the_classification_partitions_version_eights_surface(self) -> None:
        surface = {
            name for name in dir(v8c) if name.isupper() and not name.startswith("_")
        }
        classified = (
            set(c.CARRIED_FROM_V8)
            | set(c.REVISED_IN_V9)
            | set(c.REPLACED_DECLARATIONS)
        )
        self.assertEqual(classified, surface)

    def test_every_carried_constant_is_version_eights_own_object(self) -> None:
        for name in c.CARRIED_FROM_V8:
            self.assertIs(getattr(c, name), getattr(v8c, name), name)

    def test_the_account_bound_survives_the_wider_prefix(self) -> None:
        c.assert_account_bound_unchanged()
        self.assertEqual(c.GENESIS_PREFIX_BYTES, v8c.GENESIS_PREFIX_BYTES + 8)

    def test_version_nine_adds_no_result_code(self) -> None:
        self.assertEqual(c.RESULT_CODES, v8c.RESULT_CODES)
        self.assertEqual(len(c.RESULT_CODES), 45)

    def test_no_timestamp_condition_is_a_transaction_result(self) -> None:
        self.assertEqual(set(c.TIMESTAMP_CONDITIONS) & set(c.CODE_NUMBER), set())


class TimelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.head = timeline.Head(height=10, timestamp=1_000_000)

    def test_replay_cannot_reach_a_clock(self) -> None:
        """The structural half of `calendar-v1`'s separation.

        There is no argument that makes `replay` check a tolerance, which is
        what a rule stated as two entry points buys over a rule stated as a flag.
        """
        import inspect

        self.assertNotIn(
            "observed_clock", inspect.signature(timeline.replay).parameters
        )
        self.assertIn("observed_clock", inspect.signature(timeline.accept).parameters)

    def test_a_stamp_a_tolerance_behind_replays_but_would_not_re_admit(self) -> None:
        stamp = self.head.timestamp + 5
        clock = stamp + c.TIMESTAMP_TOLERANCE_MILLIS + 1
        with self.assertRaises(CodedError) as refusal:
            timeline.accept(self.head, 11, stamp, clock)
        self.assertEqual(refusal.exception.code, "TIMESTAMP_BEHIND_TOLERANCE")
        self.assertEqual(timeline.replay(self.head, 11, stamp).timestamp, stamp)

    def test_equal_timestamps_are_accepted(self) -> None:
        """C2 is non-decreasing, not strictly increasing.

        A chain catching up after a halt produces blocks faster than one a
        second, so a strict rule would be a liveness hazard exactly when a
        network is already in trouble.
        """
        head = timeline.accept(self.head, 11, self.head.timestamp, self.head.timestamp)
        self.assertEqual(head.timestamp, self.head.timestamp)

    def test_each_condition_fires_on_its_own(self) -> None:
        cases = {
            "HEIGHT_NOT_NEXT": (12, self.head.timestamp, self.head.timestamp),
            "TIMESTAMP_RANGE": (11, c.MAX_TIMESTAMP_MILLIS + 1, self.head.timestamp),
            "TIMESTAMP_NOT_MONOTONIC": (
                11,
                self.head.timestamp - 1,
                self.head.timestamp,
            ),
            "TIMESTAMP_AHEAD_OF_TOLERANCE": (
                11,
                self.head.timestamp + c.TIMESTAMP_TOLERANCE_MILLIS + 1,
                self.head.timestamp,
            ),
            "TIMESTAMP_BEHIND_TOLERANCE": (
                11,
                self.head.timestamp,
                self.head.timestamp + c.TIMESTAMP_TOLERANCE_MILLIS + 1,
            ),
        }
        for code, (height, stamp, clock) in cases.items():
            with self.subTest(code=code), self.assertRaises(CodedError) as refusal:
                timeline.accept(self.head, height, stamp, clock)
            self.assertEqual(refusal.exception.code, code)

    def test_the_tolerance_comparison_does_not_wrap(self) -> None:
        """Both sides are guarded subtractions rather than sums.

        A sum is the shape that wraps when a clock sits near the `u64` bound,
        and a wrapped comparison accepts exactly the values it exists to refuse.
        """
        high = timeline.Head(height=1, timestamp=c.MAX_TIMESTAMP_MILLIS - 1)
        with self.assertRaises(CodedError) as refusal:
            timeline.accept(high, 2, c.MAX_TIMESTAMP_MILLIS, 0)
        self.assertEqual(refusal.exception.code, "TIMESTAMP_AHEAD_OF_TOLERANCE")

    def test_it_agrees_with_the_accepted_calendar_model(self) -> None:
        timeline.assert_agrees_with_calendar_v1(
            scenario.GENESIS_MILLIS,
            [(h, t, cl) for h, t, cl, _ in scenario.proposals()],
        )


class StateSurfaceTest(unittest.TestCase):
    def test_a_zero_is_absence_in_both_values_that_are_balances(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.monthly_figure_value(0)
        with self.assertRaises(state.InvalidStateEntry):
            state.monthly_claim_value(0, 0)

    def test_a_month_above_the_calendar_bound_is_refused_everywhere(self) -> None:
        beyond = c.MAX_MONTH_INDEX + 1
        for call in (
            lambda: state.window_month_value(beyond),
            lambda: state.settlement_cursor_value(beyond),
            lambda: state.monthly_figure_key(beyond, 1),
            lambda: state.decode_window_month_value(beyond.to_bytes(4, "big")),
        ):
            with self.subTest(call=call), self.assertRaises(state.InvalidStateEntry):
                call()

    def test_the_pool_value_states_both_identities_over_one_entry(self) -> None:
        with self.assertRaises(state.InvalidStateEntry):
            state.unreferred_pool_value(1, 2, 0)
        with self.assertRaises(state.InvalidStateEntry):
            state.unreferred_pool_value(10, 5, 6)
        self.assertEqual(
            state.decode_unreferred_pool_value(state.unreferred_pool_value(10, 5, 5)),
            (10, 5, 5),
        )

    def test_version_eight_refuses_every_version_nine_entry(self) -> None:
        entries = (
            (state.window_month_key(4), state.window_month_value(674)),
            (state.monthly_figure_key(674, 2), state.monthly_figure_value(1)),
            (state.monthly_claim_key(2), state.monthly_claim_value(1, 0)),
            (state.settlement_cursor_key(), state.settlement_cursor_value(674)),
            (state.unreferred_pool_key(), state.unreferred_pool_value(1, 1, 0)),
        )
        for key, value in entries:
            with self.subTest(kind=key[0]), self.assertRaises(
                v8state.InvalidStateEntry
            ):
                v8state.require_entry_shape(key, value)

    def test_the_root_commits_to_the_timestamp(self) -> None:
        frame = state.state_root_frame(bytes(32), 1, 0, 0, [], {})
        first = state.state_root_from_frame(frame, 5, 1_000)
        second = state.state_root_from_frame(frame, 5, 1_001)
        self.assertNotEqual(first, second)

    def test_no_version_nine_root_equals_a_predecessors(self) -> None:
        arguments = (bytes(32), 5, 1, 0, 0, [], {})
        mine = state.state_root(
            arguments[0], arguments[1], 1_000, *arguments[2:]
        )
        for version in range(1, 9):
            with self.subTest(version=version):
                self.assertNotEqual(
                    mine, state.predecessor_state_root(version, *arguments)
                )


class HeaderTest(unittest.TestCase):
    def build(self, timestamp: int = 1_000) -> bytes:
        return header.block_header(
            bytes(32), 4, timestamp, "aa" * 32, "bb" * 32, "cc" * 32, 2
        )

    def test_the_header_is_one_hundred_and_fifty_four_octets(self) -> None:
        self.assertEqual(len(self.build()), 154)
        self.assertEqual(c.BLOCK_HEADER_BYTES, 154)

    def test_the_timestamp_sits_after_the_height(self) -> None:
        raw = self.build(1_234)
        self.assertEqual(int.from_bytes(raw[38:46], "big"), 4)
        self.assertEqual(int.from_bytes(raw[46:54], "big"), 1_234)

    def test_the_identifier_is_re_versioned(self) -> None:
        raw = self.build()
        self.assertNotEqual(header.block_id(raw), header.predecessor_block_id(raw))

    def test_a_timestamp_outside_the_range_is_refused(self) -> None:
        with self.assertRaises(Exception):
            self.build(c.MAX_TIMESTAMP_MILLIS + 1)


class GenesisTest(unittest.TestCase):
    def test_the_prefix_is_one_hundred_and_fifty_octets(self) -> None:
        self.assertEqual(len(genesis.encode(scenario.genesis())), 150)

    def test_it_writes_sixteen_economy_entries(self) -> None:
        entries = genesis.initial_economy_entries(scenario.genesis())
        self.assertEqual(len(entries), 16)
        month = genesis.genesis_month(scenario.genesis())
        self.assertEqual(
            entries[state.settlement_cursor_key()],
            state.settlement_cursor_value(month),
        )
        self.assertEqual(
            entries[state.window_month_key(genesis.GENESIS_WINDOW)],
            state.window_month_value(month),
        )

    def test_validation_reads_no_clock(self) -> None:
        """A genesis far in the future is well-formed, and that is forced.

        The chain identity is a hash of the genesis bytes, so a validity rule
        that read a clock would make two machines disagree about a chain's own
        identifier. Such a chain simply cannot produce its first block until
        civil time reaches it, and the refusal it reports there is
        `TIMESTAMP_NOT_MONOTONIC`.
        """
        distant = genesis.Genesis(
            network_id=scenario.NETWORK_ID,
            genesis_timestamp=c.MAX_TIMESTAMP_MILLIS - 1,
            supply_limit=scenario.SUPPLY_LIMIT,
            fixed_transfer_fee=scenario.FIXED_TRANSFER_FEE,
            manifest_digest=scenario.MANIFEST_DIGEST,
            verifier_key=scenario.VERIFIER_KEY,
            dispute_authority_key=scenario.DISPUTE_AUTHORITY_KEY,
        )
        self.assertEqual(len(genesis.encode(distant)), 150)
        head = timeline.Head(height=0, timestamp=distant.genesis_timestamp)
        with self.assertRaises(CodedError) as refusal:
            timeline.accept(head, 1, 1_000_000, 1_000_000)
        self.assertEqual(refusal.exception.code, "TIMESTAMP_NOT_MONOTONIC")

    def test_no_chain_identity_equals_a_predecessors(self) -> None:
        fixture = scenario.genesis()
        for version in (2, 3, 4, 5, 6, 7, 8):
            with self.subTest(version=version):
                self.assertNotEqual(
                    genesis.chain_id(fixture),
                    genesis.predecessor_chain_id(fixture, version),
                )


class SettlementTest(unittest.TestCase):
    ACTIVATIONS = {1: 0, 2: 0, 3: 0}

    def test_a_single_best_seat_takes_the_whole_balance(self) -> None:
        result = settlement.settle_month(1, (1, 2), {1: 100, 2: 50}, 999)
        self.assertEqual(result.winners, (1,))
        self.assertEqual(result.share, 999)
        self.assertEqual(result.remainder, 0)

    def test_an_exact_tie_shares_and_leaves_the_remainder(self) -> None:
        result = settlement.settle_month(1, (1, 2, 3), {1: 9, 2: 9, 3: 9}, 100)
        self.assertEqual(result.winners, (1, 2, 3))
        self.assertEqual(result.share, 33)
        self.assertEqual(result.remainder, 1)

    def test_a_zero_best_month_pays_every_candidate(self) -> None:
        result = settlement.settle_month(1, (1, 2, 3), {}, 90)
        self.assertEqual(result.winners, (1, 2, 3))
        self.assertEqual(result.best_figure, 0)

    def test_a_zero_share_writes_no_claim(self) -> None:
        result = settlement.settle_month(1, (1, 2, 3), {}, 2)
        pool = settlement.Pool(accrued=2, payable=2)
        claims: dict[int, tuple[int, int]] = {}
        settlement.apply_settlement(result, pool, claims, {})
        self.assertEqual(claims, {})
        self.assertEqual(pool.payable, 2)

    def test_a_month_that_accumulated_with_no_candidate_is_an_invariant_failure(
        self,
    ) -> None:
        """The accrual theorem, checked rather than asserted.

        In-span implies in-scope and in-scope never expires, so a month that
        accumulated uptime always has a candidate. A later change that made
        in-scope expire fails here instead of quietly turning a safety net into
        a policy.
        """
        with self.assertRaises(InvariantError):
            settlement.settle_month(1, (), {1: 100}, 50)

    def test_a_month_with_no_candidate_and_no_figure_carries(self) -> None:
        result = settlement.settle_month(1, (), {}, 50)
        self.assertEqual(result.remainder, 50)
        self.assertTrue(result.carried)

    def test_the_single_pass_equals_the_loop_over_a_long_halt(self) -> None:
        settlement.assert_single_pass_equals_loop(
            100,
            140,
            self.ACTIVATIONS,
            30,
            settlement.Pool(accrued=7, payable=7),
            {},
            {(100, 1): 5},
        )

    def test_the_single_pass_equals_the_loop_when_nothing_closes(self) -> None:
        settlement.assert_single_pass_equals_loop(
            100, 100, self.ACTIVATIONS, 30, settlement.Pool(), {}, {}
        )

    def test_a_month_behind_the_cursor_is_refused(self) -> None:
        with self.assertRaises(InvariantError):
            settlement.close_month(
                5, 4, self.ACTIVATIONS, 30, settlement.Pool(), {}, {}
            )

    def test_it_agrees_with_the_accepted_payout_model(self) -> None:
        for figures, payable in (
            ({1: 100}, 999),
            ({1: 9, 2: 9}, 101),
            ({}, 90),
            ({}, 2),
        ):
            with self.subTest(figures=figures):
                settlement.assert_agrees_with_unreferred_pool(
                    1, self.ACTIVATIONS, 30, figures, payable
                )

    def test_the_recorded_run_conserves_every_unit(self) -> None:
        run = scenario.run()
        run["pool"].assert_conserved(run["claims"])


class MintMessageTest(unittest.TestCase):
    def test_it_is_version_sixs_construction(self) -> None:
        envelope.assert_agrees_with_version_six()

    def test_the_four_confirmable_mints_differ_on_identical_fields(self) -> None:
        messages = {
            kind: envelope.mint_message(
                bytes(32), bytes(32), kind, 7, bytes(32), 99
            )
            for kind in sorted(c.CONFIRMABLE_MINTS)
        }
        self.assertEqual(len(set(messages.values())), 4)

    def test_a_kind_that_is_not_a_confirmable_mint_is_refused(self) -> None:
        with self.assertRaises(envelope.MalformedTransaction):
            envelope.mint_message(bytes(32), bytes(32), c.TRANSFER, 0, bytes(32), 1)


if __name__ == "__main__":
    unittest.main()
