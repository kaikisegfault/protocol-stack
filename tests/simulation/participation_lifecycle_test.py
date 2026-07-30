#!/usr/bin/env python3
"""Participation replay, activation, jail, removal, and exit tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.participation import simulate
from tests.simulation.participation_common import (
    ParticipationTestCase,
    active_setup,
    base_manifest,
    event,
    proof,
)


class ParticipationLifecycleTest(ParticipationTestCase):
    def test_common_replay_and_failed_identifier_reuse(self) -> None:
        registration = event(
            "register_node",
            "registrar",
            id="shared_event",
            participant="node_x",
            owner="alice",
            payout_account="alice",
            **proof(1),
        )
        wrong_height = {**registration, "height": 1}
        result = simulate(base_manifest(), [registration, wrong_height])
        self.assertEqual(result["records"][1]["result"], "WRONG_HEIGHT")
        duplicate_proof = event(
            "register_node",
            "registrar",
            id="other_event",
            participant="node_y",
            owner="bob",
            payout_account="bob",
            **proof(1),
        )
        self.assert_failure([registration, duplicate_proof], "PROOF_REPLAY")
        denied = event(
            "register_node",
            "alice",
            id="retry_event",
            participant="node_z",
            owner="carol",
            payout_account="carol",
            **proof(2),
        )
        retry = {**denied, "actor": "registrar"}
        result = simulate(base_manifest(), [denied, retry])
        self.assertEqual(
            [record["result"] for record in result["records"]],
            ["UNAUTHORIZED", "OK"],
        )

    def test_activation_requires_delay_and_validator_bond(self) -> None:
        registration = event(
            "register_validator",
            "registrar",
            id="register",
            participant="validator_x",
            owner="alice",
            payout_account="alice",
            bond_id="bond_x",
            **proof(10),
        )
        early = event(
            "activate",
            "lifecycle",
            id="activate_early",
            participant="validator_x",
        )
        self.assert_failure([registration, early], "TOO_EARLY")
        advance = [
            event("advance_height", "clock", id="advance_1", to_height=1),
            event(
                "advance_height",
                "clock",
                id="advance_2",
                height=1,
                to_height=2,
            ),
        ]
        no_bond = event(
            "activate",
            "lifecycle",
            id="activate_no_bond",
            height=2,
            participant="validator_x",
        )
        self.assert_failure([registration, *advance, no_bond], "BOND_REQUIRED")

    def test_jail_recovery_and_terminal_removal(self) -> None:
        jail = event(
            "jail",
            "enforcement",
            id="jail",
            height=2,
            participant="validator_a",
            until_epoch=2,
            **proof(20),
        )
        contribution = event(
            "attest_contribution",
            "consensus_verifier",
            id="jailed_contribution",
            height=2,
            participant="validator_a",
            role="validator",
            contribution_kind="vote",
            epoch=1,
            units=1,
            **proof(21),
        )
        self.assert_failure(
            [*active_setup(), jail, contribution],
            "NOT_ELIGIBLE",
        )
        early = event(
            "request_recovery",
            "alice",
            id="recover_early",
            height=2,
            participant="validator_a",
        )
        self.assert_failure([*active_setup(), jail, early], "TOO_EARLY")
        advance = [
            event(
                "advance_height",
                "clock",
                id="jail_advance_3",
                height=2,
                to_height=3,
            ),
            event(
                "advance_height",
                "clock",
                id="jail_advance_4",
                height=3,
                to_height=4,
            ),
        ]
        request = event(
            "request_recovery",
            "alice",
            id="recovery_request",
            height=4,
            participant="validator_a",
        )
        recover = event(
            "recover",
            "lifecycle",
            id="recover",
            height=4,
            participant="validator_a",
        )
        remove = event(
            "remove",
            "enforcement",
            id="remove",
            height=4,
            participant="validator_a",
            reason="safety_fault",
            **proof(22),
        )
        complete = [*active_setup(), jail, *advance, request, recover, remove]
        result = simulate(base_manifest(), complete)
        participant = result["final_state"]["participants"]["validator_a"]
        self.assertEqual(participant["phase"], "removed")
        self.assertEqual(participant["removed_epoch"], 2)
        self.assertEqual(participant["unbond_ready_epoch"], 4)
        after_remove = event(
            "request_exit",
            "alice",
            id="after_remove",
            height=4,
            participant="validator_a",
        )
        self.assert_failure([*complete, after_remove], "INVALID_STATUS")

    def test_exit_epoch_ends_eligibility_before_completion(self) -> None:
        request = event(
            "request_exit",
            "alice",
            id="exit_request",
            height=2,
            participant="validator_a",
        )
        at_epoch_one = event(
            "attest_contribution",
            "consensus_verifier",
            id="before_exit",
            height=2,
            participant="validator_a",
            role="validator",
            contribution_kind="vote",
            epoch=1,
            units=1,
            **proof(30),
        )
        advance = [
            event(
                "advance_height",
                "clock",
                id="exit_advance_3",
                height=2,
                to_height=3,
            ),
            event(
                "advance_height",
                "clock",
                id="exit_advance_4",
                height=3,
                to_height=4,
            ),
        ]
        at_epoch_two = {
            **at_epoch_one,
            "id": "after_exit",
            "height": 4,
            "epoch": 2,
            **proof(31),
        }
        result = self.assert_failure(
            [*active_setup(), request, at_epoch_one, *advance, at_epoch_two],
            "NOT_ELIGIBLE",
        )
        self.assertTrue(result["records"][-4]["accepted"])


if __name__ == "__main__":
    unittest.main()
