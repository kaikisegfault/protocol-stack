"""Version-three accounting: reallocation, carry, referral, and containment.

The rules exercised here are version two's and are unchanged. They are re-proved
against version three because the state they run over changed shape, not because
the rules did.
"""

from __future__ import annotations

import unittest

from simulation.common.canonical import MAX_U64
from simulation.founder_economy_v2.domain import STATE_LABEL as V2_STATE_LABEL
from simulation.founder_economy_v2.uptime import RECORD_LABEL as V2_RECORD_LABEL
from simulation.founder_economy_v3 import contract as c
from simulation.founder_economy_v3.domain import (
    STATE_LABEL,
    Channel,
    Leg,
    PendingPermission,
    Seat,
    initial_state,
)
from simulation.founder_economy_v3.engine import (
    EVENTS_LABEL,
    RESULT_LABEL,
    RESULT_SCHEMA,
    TRACE_LABEL,
)
from simulation.founder_economy_v3.handlers_issuance import exercise_permission
from simulation.founder_economy_v3.uptime import RECORD_LABEL, reallocate

from .founder_economy_v3_common import (
    FAILED_BOUNDARY,
    FULL_WINDOW,
    MET_BOUNDARY,
    accrue,
    activate,
    codes,
    custody,
    direct,
    evaluate_scoped,
    exercise,
    run,
    window_of,
)

# Three seats opening in the same window, so every record covers all three and
# reallocation has a population to rank.
HEIGHTS = {0: 0, 1: 0, 2: 0}
POPULATION = [activate(0), activate(1, referrer=0), activate(2, referrer=0)]
WINDOW_0 = window_of(0, 0)


def population(*events: dict) -> list[dict]:
    return [*POPULATION, *events]


class ActivityTest(unittest.TestCase):
    def test_exactly_the_threshold_meets_the_cycle(self) -> None:
        """ADR 0023 resolves the boundary in the operator's favour."""
        events = population(
            evaluate_scoped(HEIGHTS, 0, 0, {0: MET_BOUNDARY}), exercise(0, 0)
        )
        result = run(events)
        self.assertEqual(codes(result)[-2:], ["OK", "OK"])
        self.assertEqual(
            custody(result, "founder_seat:00000"), c.FOUNDER_OPERATOR_LEG
        )

    def test_one_second_below_the_threshold_fails_the_cycle(self) -> None:
        events = population(evaluate_scoped(HEIGHTS, 0, 0, {0: FAILED_BOUNDARY}))
        result = run(events)
        permission = result["final_state"]["pending_permissions"]["00000:000"]
        self.assertFalse(permission["met_cycle"])


class ReallocationTest(unittest.TestCase):
    def test_a_tie_splits_equally_and_carries_the_remainder(self) -> None:
        events = population(evaluate_scoped(HEIGHTS, 0, 0, {0: 3_600}))
        result = run(events)
        share, remainder = divmod(c.FOUNDER_OPERATOR_LEG, 2)
        permission = result["final_state"]["pending_permissions"]["00000:000"]
        founder_legs = [
            leg for leg in permission["legs"] if leg["channel"] == "founder_operator"
        ]
        self.assertEqual([leg["amount_atomic"] for leg in founder_legs], [str(share)] * 2)
        self.assertEqual(
            result["final_state"]["performance_carry_atomic"], str(remainder)
        )

    def test_a_failed_seat_never_rewards_another_failed_seat(self) -> None:
        events = population(
            evaluate_scoped(HEIGHTS, 0, 0, {0: 3_600, 1: 3_600, 2: FULL_WINDOW})
        )
        permission = run(events)["final_state"]["pending_permissions"]["00000:000"]
        winners = [
            leg["custody_key"]
            for leg in permission["legs"]
            if leg["channel"] == "founder_operator"
        ]
        self.assertEqual(winners, ["founder_seat:00002"])

    def test_an_empty_winner_set_carries_the_whole_portion(self) -> None:
        events = population(
            evaluate_scoped(HEIGHTS, 0, 0, {0: 3_600, 1: 3_600, 2: 3_600})
        )
        result = run(events)
        permission = result["final_state"]["pending_permissions"]["00000:000"]
        self.assertEqual(
            [leg for leg in permission["legs"] if leg["channel"] == "founder_operator"],
            [],
        )
        self.assertEqual(
            result["final_state"]["performance_carry_atomic"],
            str(c.FOUNDER_OPERATOR_LEG),
        )

    def test_the_carry_conservation_identity_holds_across_paths(self) -> None:
        """Issued plus outstanding plus carried equals one portion per key."""
        events = population(
            evaluate_scoped(HEIGHTS, 0, 0, {0: 3_600}),
            evaluate_scoped(HEIGHTS, 1, 0, {1: FULL_WINDOW}),
            evaluate_scoped(HEIGHTS, 2, 0, {0: 3_600, 1: 3_600, 2: 3_600}, window=WINDOW_0),
            exercise(1, 0),
        )
        result = run(events)
        metrics = result["metrics"]
        self.assertEqual(
            int(metrics["founder_accounted_atomic"]),
            metrics["evaluated_permission_key_count"] * c.FOUNDER_OPERATOR_LEG,
        )


class ReferralTest(unittest.TestCase):
    def test_a_referred_seat_credits_its_referrer(self) -> None:
        result = run(population(accrue(1, 0)))
        self.assertEqual(custody(result, "founder_seat:00000"), c.REFERRAL_AMOUNT)

    def test_an_unreferred_seat_credits_the_pool(self) -> None:
        result = run(population(accrue(0, 0)))
        self.assertEqual(
            custody(result, "unreferred_performance_pool:global"), c.REFERRAL_AMOUNT
        )

    def test_the_referral_channel_is_closed_to_direct_issuance(self) -> None:
        """A supplied fixture must not mint outside the per-seat-cycle accounting."""
        result = run(population(direct(channel=c.REFERRAL_CHANNEL)))
        self.assertEqual(codes(result)[-1], "INVALID_CHANNEL")


class LabelTest(unittest.TestCase):
    def test_every_domain_label_is_version_three(self) -> None:
        for label in (EVENTS_LABEL, STATE_LABEL, TRACE_LABEL, RESULT_LABEL, RECORD_LABEL):
            self.assertTrue(label.endswith("-v3"), label)
        self.assertTrue(RESULT_SCHEMA.endswith("/v3"))

    def test_the_state_and_record_labels_differ_from_version_two(self) -> None:
        """No digest computed under version two can be replayed as version three."""
        self.assertNotEqual(STATE_LABEL, V2_STATE_LABEL)
        self.assertNotEqual(RECORD_LABEL, V2_RECORD_LABEL)

    def test_the_manifest_label_is_inherited_unchanged(self) -> None:
        """The manifest is the same accepted artifact, so it keeps its name."""
        self.assertTrue(c.MANIFEST_LABEL.endswith("-v2"))


class GuardTest(unittest.TestCase):
    """The two codes no event array reaches, proved present rather than deleted."""

    def test_an_overflowing_pot_is_refused_and_moves_nothing(self) -> None:
        code, legs, carry = reallocate(MAX_U64, (0,))
        self.assertEqual(code, "ARITHMETIC_OVERFLOW")
        self.assertEqual(legs, ())
        self.assertEqual(carry, MAX_U64)

    def test_a_permission_whose_legs_do_not_sum_is_refused(self) -> None:
        state = initial_state()
        state.seats[0] = Seat(referrer_seat_id=None, activation_height=0)
        state.channels[c.FOUNDER_CHANNEL] = Channel()
        state.pending_permissions["00000:000"] = PendingPermission(
            seat_id=0,
            cycle_index=0,
            cycle_window=1,
            met_cycle=True,
            total_atomic=c.FOUNDER_OPERATOR_LEG + 1,
            legs=(
                Leg(
                    channel=c.FOUNDER_CHANNEL,
                    custody_key="founder_seat:00000",
                    amount_atomic=c.FOUNDER_OPERATOR_LEG,
                ),
            ),
        )
        outcome = exercise_permission(state, {"seat_id": 0, "cycle_index": 0})
        self.assertEqual(outcome.code, "INVARIANT")


class BindingTest(unittest.TestCase):
    def test_the_bound_contracts_are_re_proved_before_a_run(self) -> None:
        """A drifted binding must stop a run rather than change what a window means."""
        c.assert_agrees_with_bindings()

    def test_the_manifest_layer_is_read_and_not_restated(self) -> None:
        from simulation.founder_economy_v2 import contract as economy_v2

        self.assertEqual(c.CHANNEL_CAPS, economy_v2.CHANNEL_CAPS)
        self.assertEqual(c.BASE_LEGS, economy_v2.BASE_LEGS)
        self.assertEqual(c.MAXIMUM_SUPPLY_ATOMIC, economy_v2.MAXIMUM_SUPPLY_ATOMIC)


if __name__ == "__main__":
    unittest.main()
