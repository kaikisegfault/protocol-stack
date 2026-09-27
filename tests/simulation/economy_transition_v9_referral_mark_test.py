#!/usr/bin/env python3
"""A referrer's first accrual starts its accumulation mark at the window before.

`economy-transition-v3` creates a referral balance "with
`collected_through_window` set to the window before that accrual, so a referrer
is never capped before anything has been credited to them", and every version
since carries that rule unchanged. The executed models from version six onward
created it with a zero mark, which agrees with the rule only while the first
accrual lands inside the first thirty windows. ADR 0094 records the defect.

No recorded vector reaches it, because each recorded referral is minted in the
block its first accrual lands in. So this chain registers a referrer and a buyer,
sells a referred seat, activates it in window 100, and opens every window after
through the version-nine prologue itself.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v6 import messages
from simulation.economy_transition_v6.identity import escrow_id
from simulation.economy_transition_v6.ledger import (
    ConservationFailure,
    first_referral_balance,
)
from simulation.economy_transition_v6.trace import Signatures, _register
from simulation.economy_transition_v9 import contract as c
from simulation.economy_transition_v9.block import BlockOutcome, _prologue
from simulation.economy_transition_v9.execution import admit, execute
from simulation.economy_transition_v9.ledger import Ledger
from simulation.economy_transition_v9.trace import GENESIS_MILLIS, VALID_UNTIL
from simulation.economy_transition_v9.trace import build, genesis

REFERRER = (bytes.fromhex("71" * 32), bytes.fromhex("72" * 32), bytes.fromhex("73" * 32))
BUYER = (bytes.fromhex("74" * 32), bytes.fromhex("75" * 32), bytes.fromhex("76" * 32))
SEAT = 0
ACTIVATION_WINDOW = 100
LEG = c.REFERRAL_LEG_ATOMIC


def stamp(height: int) -> int:
    """Three seconds a block, so a window is one day at the commit target."""
    return GENESIS_MILLIS + height * 3_000


class Chain:
    """A version-nine ledger with a referred seat, driven a window at a time."""

    def __init__(self) -> None:
        self.signatures = Signatures()
        self.ledger = Ledger.from_genesis(genesis())
        for identity, key, signer in (REFERRER, BUYER):
            self.submit(1, _register(self.signatures, self.ledger, identity, key, signer))
        identity, key, signer = BUYER
        message = messages.purchase_message(
            self.ledger.chain_id, identity, SEAT, VALID_UNTIL
        )
        self.submit(2, build(
            self.signatures, self.ledger, c.PURCHASE_SEAT, signer, 1,
            {
                "seat_id": SEAT,
                "has_referrer": True,
                "referrer_escrow_id": escrow_id(REFERRER[0], 0),
                "hub_signature": self.signatures.sign(key, message),
            },
        ))
        self.open_through(ACTIVATION_WINDOW)
        message = messages.activation_message(
            self.ledger.chain_id, identity, SEAT, VALID_UNTIL
        )
        self.submit(ACTIVATION_WINDOW * c.CYCLE_BLOCKS + 10, build(
            self.signatures, self.ledger, c.ACTIVATE_SEAT, signer, 2,
            {"seat_id": SEAT, "hub_signature": self.signatures.sign(key, message)},
        ))
        self.window = ACTIVATION_WINDOW

    def submit(self, height: int, raw: bytes) -> None:
        self.ledger.height, self.ledger.timestamp = height, stamp(height)
        admission = admit(raw, self.ledger.chain_id, self.signatures.oracle)
        assert admission.admitted and admission.transaction is not None
        result = execute(self.ledger, admission.transaction, self.signatures.oracle)
        assert result.result == "SUCCESS", result.result

    def open_through(self, last: int) -> None:
        first = getattr(self, "window", 0) + 1
        for window in range(first, last + 1):
            height = window * c.CYCLE_BLOCKS
            self.ledger.height, self.ledger.timestamp = height, stamp(height)
            _prologue(self.ledger, BlockOutcome(height, self.ledger.timestamp, ""),
                      True, False)
            self.ledger.require_conserved()
            self.window = window

    def assigned_through(self, window: int) -> None:
        """Open windows until `window` itself has been assigned."""
        self.open_through(window + c.ASSIGNMENT_LAG_WINDOWS)

    @property
    def balance(self):
        return self.ledger.referral[REFERRER[0]]


class FirstBalanceTest(unittest.TestCase):
    def test_the_mark_is_the_window_before_the_first_accrual(self) -> None:
        self.assertEqual(first_referral_balance(1).collected_through_window, 0)
        self.assertEqual(first_referral_balance(101).collected_through_window, 100)

    def test_a_new_balance_holds_nothing_until_the_accrual_is_added(self) -> None:
        created = first_referral_balance(101)
        self.assertEqual((created.accrued_atomic, created.minted_atomic), (0, 0))

    def test_no_accrual_precedes_window_one(self) -> None:
        with self.assertRaises(ConservationFailure):
            first_referral_balance(0)


class LateReferrerTest(unittest.TestCase):
    """The referred seat's first cycle is window 101, well past the cap."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.chain = Chain()
        cls.chain.assigned_through(ACTIVATION_WINDOW + 1)
        cls.first = cls.chain.balance
        cls.chain.assigned_through(ACTIVATION_WINDOW + 2)
        cls.second = cls.chain.balance
        cls.chain.assigned_through(ACTIVATION_WINDOW + c.MINT_ACCUMULATION_CAP)
        cls.last_under = cls.chain.balance
        cls.pool_under = cls.chain.ledger.pool_accrued
        cls.chain.assigned_through(ACTIVATION_WINDOW + c.MINT_ACCUMULATION_CAP + 1)
        cls.over = cls.chain.balance
        cls.pool_over = cls.chain.ledger.pool_accrued

    def test_the_first_accrual_creates_the_balance_at_the_window_before(self) -> None:
        self.assertEqual(self.first.accrued_atomic, LEG)
        self.assertEqual(self.first.collected_through_window, ACTIVATION_WINDOW)

    def test_the_second_accrual_reaches_the_referrer(self) -> None:
        """The one a zero mark sent to the unreferred pool."""
        self.assertEqual(self.second.accrued_atomic, 2 * LEG)

    def test_thirty_windows_accrue_before_the_cap_binds(self) -> None:
        self.assertEqual(self.last_under.accrued_atomic, c.MINT_ACCUMULATION_CAP * LEG)
        self.assertEqual(self.pool_under, 0)

    def test_the_cap_still_binds_measured_from_that_mark(self) -> None:
        self.assertEqual(self.over.accrued_atomic, c.MINT_ACCUMULATION_CAP * LEG)
        self.assertEqual(self.pool_over, LEG)
        self.assertEqual(self.chain.ledger.pool_payable, LEG)

    def test_every_leg_stays_in_the_referral_channel(self) -> None:
        outstanding = self.chain.ledger.channel_outstanding[c.REFERRAL_CHANNEL]
        self.assertEqual(outstanding, (c.MINT_ACCUMULATION_CAP + 1) * LEG)


class CollectingReferrerTest(unittest.TestCase):
    """A mint moves the mark exactly as before, so collecting keeps accruing."""

    def test_a_mint_after_the_first_accrual_takes_it_and_advances_the_mark(self) -> None:
        chain = Chain()
        chain.assigned_through(ACTIVATION_WINDOW + 1)
        identity, key, signer = REFERRER
        destination = escrow_id(identity, 0)
        message = messages.mint_message(
            chain.ledger.chain_id, identity, c.MINT_REFERRAL, 0, destination,
            VALID_UNTIL,
        )
        chain.submit(chain.ledger.height + 1, build(
            chain.signatures, chain.ledger, c.MINT_REFERRAL, signer, 1,
            {
                "destination_escrow_id": destination,
                "hub_signature": chain.signatures.sign(key, message),
            },
        ))
        self.assertEqual(chain.balance.minted_atomic, LEG)
        self.assertEqual(chain.balance.collected_through_window, ACTIVATION_WINDOW + 1)
        chain.assigned_through(ACTIVATION_WINDOW + 1 + c.MINT_ACCUMULATION_CAP)
        self.assertEqual(
            chain.balance.accrued_atomic, (1 + c.MINT_ACCUMULATION_CAP) * LEG
        )
        self.assertEqual(chain.ledger.pool_accrued, 0)
        chain.ledger.require_conserved()


if __name__ == "__main__":
    unittest.main()
