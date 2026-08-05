#!/usr/bin/env python3
"""Multi-year population, escrow drain, and restart-equivalence tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.escrow_payout import contract as escrow_contract
from simulation.founder_economy import contract as c
from simulation.founder_economy.engine import simulate as economy_simulate
from simulation.founder_economy.manifest import load_manifest_file
from simulation.scenarios import economy_population as population
from simulation.scenarios import escrow_drain
from simulation.scenarios.suite import MANIFEST_PATH
from tests.simulation.scenario_suite_common import (
    economy_result,
    escrow_result,
    rejected,
    total,
    vectors,
)

# Prefixes spanning the first event, the activations, one seat's window before
# the others open, and the overlap of all three. A prefix costs time quadratic
# in its length, because the economy simulator clones state per event, so the
# end of the run is covered by the recorded final digest instead.
RESTART_PREFIXES = (1, 7, 500, 3_000)


class PopulationRunTest(unittest.TestCase):
    def setUp(self) -> None:
        self.result = economy_result()
        self.recorded = vectors()

    def test_every_seat_completes_its_whole_issuance_window(self) -> None:
        accepted = {
            (record["event_id"].split("-")[1], record["event_id"].split("-")[2])
            for record in self.result["records"]
            if record["accepted"] and record["kind"] == "evaluate_base_permission"
        }
        self.assertEqual(
            len(accepted), population.SEATS * c.ISSUANCE_CYCLES_PER_SEAT
        )
        for seat_id in range(population.SEATS):
            cycles = {
                int(cycle)
                for seat, cycle in accepted
                if int(seat) == seat_id
            }
            with self.subTest(seat=seat_id):
                self.assertEqual(cycles, set(range(c.ISSUANCE_CYCLES_PER_SEAT)))

    def test_channel_totals_equal_their_closed_form(self) -> None:
        channels = self.result["metrics"]["channels"]
        per_seat = population.SEATS * c.ISSUANCE_CYCLES_PER_SEAT
        for channel, _, _ in c.CHANNELS:
            if channel in c.DIRECT_CHANNEL_IDS:
                with self.subTest(channel=channel):
                    self.assertEqual(channels[channel]["issued_atomic"], "0")

        expected = {
            channel: amount * per_seat
            for channel, _, amount in c.BASE_LEGS
        }
        expected[c.REFERRAL_CHANNEL] = (
            population.referral_permissions_created() * c.REFERRAL_AMOUNT
        )
        for channel, amount in expected.items():
            with self.subTest(channel=channel):
                self.assertEqual(channels[channel]["issued_atomic"], str(amount))

    def test_reallocation_moves_a_beneficiary_and_not_an_amount(self) -> None:
        """Inactivity must not change the Founder operator channel total."""
        inactive = sum(
            len(population.inactive_cycles(seat))
            for seat in range(population.SEATS)
        )
        self.assertGreater(inactive, 0)
        channels = self.result["metrics"]["channels"]
        self.assertEqual(
            channels["founder_operator"]["issued_atomic"],
            str(
                population.SEATS
                * c.ISSUANCE_CYCLES_PER_SEAT
                * c.FOUNDER_OPERATOR_LEG
            ),
        )

    def test_custody_equals_issued_supply(self) -> None:
        metrics = self.result["metrics"]
        custody = self.result["final_state"]["typed_custody"]
        self.assertEqual(total(custody), int(metrics["issued_supply_atomic"]))
        self.assertEqual(metrics["outstanding_permissions_atomic"], "0")

    def test_supply_stays_inside_the_maximum(self) -> None:
        metrics = self.result["metrics"]
        issued = int(metrics["issued_supply_atomic"])
        outstanding = int(metrics["outstanding_permissions_atomic"])
        remaining = int(metrics["remaining_capacity_atomic"])
        self.assertEqual(
            issued + outstanding + remaining, c.MAXIMUM_SUPPLY_ATOMIC
        )
        for channel, _, cap in c.CHANNELS:
            entry = metrics["channels"][channel]
            with self.subTest(channel=channel):
                self.assertLessEqual(
                    int(entry["issued_atomic"])
                    + int(entry["outstanding_atomic"]),
                    cap,
                )

    def test_boundary_probes_are_still_refused_after_the_long_run(self) -> None:
        codes = {
            record["event_id"]: record["result"]
            for record in self.result["records"]
        }
        for name, event_id in (
            ("cycle_beyond_window", "probe-cycle-beyond-window"),
            ("base_replay", "probe-base-replay"),
            ("exercise_replay", "probe-exercise-replay"),
            ("activation_replay", "probe-activation-replay"),
            ("unreferred_referral", "probe-unreferred-referral"),
        ):
            with self.subTest(probe=name):
                self.assertEqual(
                    codes[event_id], self.recorded[f"economy.probe.{name}"]
                )

    def test_no_rejection_writes_or_journals(self) -> None:
        for record in rejected(self.result):
            with self.subTest(event=record["event_id"]):
                self.assertEqual(record["journal"], [])
                self.assertEqual(
                    record["state_digest_before"], record["state_digest_after"]
                )


class RestartEquivalenceTest(unittest.TestCase):
    """A run stopped after k events must reach the digest the full run had."""

    def setUp(self) -> None:
        self.events = population.events()
        self.result = economy_result()
        self.manifest = load_manifest_file(MANIFEST_PATH)

    def test_a_replayed_prefix_reaches_the_recorded_digest(self) -> None:
        for length in RESTART_PREFIXES:
            with self.subTest(prefix=length):
                replayed = economy_simulate(
                    self.manifest, self.events[:length]
                )
                self.assertEqual(
                    replayed["state_digest"],
                    self.result["records"][length - 1]["state_digest_after"],
                )

    def test_the_full_run_ends_at_its_last_recorded_digest(self) -> None:
        self.assertEqual(
            self.result["records"][-1]["state_digest_after"],
            self.result["state_digest"],
        )


class EscrowDrainTest(unittest.TestCase):
    def setUp(self) -> None:
        self.economy = economy_result()
        self.result = escrow_result()

    def test_the_drain_binds_the_population_run(self) -> None:
        self.assertEqual(
            self.result["final_state"]["bound_state_digest"],
            self.economy["state_digest"],
        )

    def test_every_escrow_opens_at_what_the_population_run_issued(self) -> None:
        opening = self.result["final_state"]["opening_custody"]
        channels = self.economy["metrics"]["channels"]
        for escrow_id in escrow_contract.ESCROW_IDS:
            with self.subTest(escrow=escrow_id):
                self.assertEqual(
                    opening[escrow_id], channels[escrow_id]["issued_atomic"]
                )

    def test_every_escrow_is_drained_and_conserved(self) -> None:
        state = self.result["final_state"]
        for escrow_id in escrow_contract.ESCROW_IDS:
            opening = int(state["opening_custody"][escrow_id])
            paid = int(state["paid_out_total"][escrow_id])
            available = int(state["available_custody"][escrow_id])
            charged = sum(
                int(capability["spent"])
                for capability in state["capabilities"].values()
                if capability["escrow_id"] == escrow_id
            )
            with self.subTest(escrow=escrow_id):
                self.assertEqual(available, 0)
                self.assertEqual(available + paid, opening)
                self.assertEqual(
                    total(state["recipient_balances"][escrow_id]), opening
                )
                self.assertEqual(charged, opening)

    def test_exhausted_authority_and_an_empty_escrow_differ(self) -> None:
        codes = {
            record["event_id"]: record["result"]
            for record in self.result["records"]
        }
        for index in range(len(escrow_contract.ESCROW_IDS)):
            with self.subTest(escrow=index):
                self.assertEqual(
                    codes[f"probe-{index}-envelope"], "ENVELOPE_EXCEEDED"
                )
                self.assertEqual(
                    codes[f"probe-{index}-custody"], "INSUFFICIENT_CUSTODY"
                )

    def test_seven_payouts_drain_each_escrow_with_a_remainder(self) -> None:
        opening = self.result["final_state"]["opening_custody"]
        for escrow_id in escrow_contract.ESCROW_IDS:
            amounts = escrow_drain.payout_amounts(int(opening[escrow_id]))
            with self.subTest(escrow=escrow_id):
                self.assertEqual(len(amounts), escrow_drain.PAYOUTS_PER_ESCROW)
                self.assertEqual(sum(amounts), int(opening[escrow_id]))
                self.assertLess(amounts[-1], amounts[0])


if __name__ == "__main__":
    unittest.main()
