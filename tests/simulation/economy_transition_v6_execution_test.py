#!/usr/bin/env python3
"""The version-six executor: resolution, the shared checks, and each kind's own.

The vectors record what the trace produces. What is tested here is what makes
those values load-bearing — the orders and refusals a fixture happens not to
reach, and the three rules ADR 0045 derived from an accepted contract that
admits two readings of each.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.economy_transition_v6 import contract as c
from simulation.economy_transition_v6 import messages, trace
from simulation.economy_transition_v6.envelope import (
    Transaction,
    signed_bytes,
    signing_message,
    unsigned_bytes,
)
from simulation.economy_transition_v6.execution import (
    Refused,
    SignatureOracle,
    admit,
    execute,
    require_zero_confirmation,
)
from simulation.economy_transition_v6.identity import Posture, signer_id
from simulation.economy_transition_v6.ledger import ConservationFailure, Ledger


def _ledger(fee: int = trace.FIXED_FEE) -> Ledger:
    ledger = Ledger(
        chain_id=bytes(32),
        supply_limit=trace.SUPPLY_LIMIT,
        fixed_fee=fee,
        verifier_key=trace.VERIFIER_KEY,
        channel_issued={index: 0 for index in range(10)},
        channel_outstanding={index: 0 for index in range(10)},
        carry={index: 0 for index in range(10)},
    )
    ledger.height = 10
    return ledger


def _register(ledger: Ledger, identity: bytes, hub_key: bytes, signer_key: bytes) -> bytes:
    """Seed an identity through the registry, then account for its airdrop."""
    escrow = ledger.registry.register(identity, hub_key, signer_key, ledger.height)
    credited = ledger.balance(escrow)
    if credited:
        ledger.channel_issued[c.VERIFIED_USER_CHANNEL] += credited
        ledger.total_supply += credited
    return escrow


def _transaction(kind: int, authority: bytes, nonce: int, body: dict, **overrides):
    fields = {
        "fee_limit": 0 if kind == c.HUB_REGISTER else trace.FIXED_FEE,
        "valid_until_height": 1_000,
    }
    fields.update(overrides)
    return Transaction(
        kind=kind,
        scheme=c.KIND_SCHEME[kind],
        chain_id=bytes(32),
        authority_public_key=authority,
        nonce=nonce,
        body=body,
        **fields,
    )


class ResolutionTest(unittest.TestCase):
    def test_an_unassigned_signer_key_authorizes_nothing(self) -> None:
        ledger = _ledger()
        transaction = _transaction(
            c.TRANSFER,
            trace.ALICE_SIGNER_KEY,
            1,
            {"recipient_escrow_id": bytes(32), "amount_atomic": 1},
        )
        self.assertEqual(
            execute(ledger, transaction, SignatureOracle()).result, "SIGNER_NOT_FOUND"
        )

    def test_a_revoked_signer_authorizes_nothing_from_the_same_block(self) -> None:
        ledger = _ledger()
        escrow = _register(
            ledger, trace.ALICE_IDENTITY, trace.ALICE_KEY, trace.ALICE_SIGNER_KEY
        )
        ledger.registry.revoke_signer(escrow, signer_id(trace.ALICE_SIGNER_KEY))
        transaction = _transaction(
            c.TRANSFER,
            trace.ALICE_SIGNER_KEY,
            1,
            {"recipient_escrow_id": escrow, "amount_atomic": 1},
        )
        self.assertEqual(
            execute(ledger, transaction, SignatureOracle()).result, "SIGNER_NOT_FOUND"
        )

    def test_scheme_two_refuses_an_unregistered_identity_first(self) -> None:
        ledger = _ledger()
        transaction = _transaction(
            c.ESCROW_CREATE,
            trace.ALICE_KEY,
            1,
            {
                "hub_identity_hash": trace.ALICE_IDENTITY,
                "fee_escrow_id": trace.ALICE_ESCROW,
            },
        )
        self.assertEqual(
            execute(ledger, transaction, SignatureOracle()).result, "NOT_HUB_VERIFIED"
        )

    def test_scheme_two_refuses_a_header_key_that_is_not_the_recorded_one(self) -> None:
        ledger = _ledger()
        _register(ledger, trace.ALICE_IDENTITY, trace.ALICE_KEY, trace.ALICE_SIGNER_KEY)
        transaction = _transaction(
            c.ESCROW_CREATE,
            trace.BOB_KEY,
            1,
            {
                "hub_identity_hash": trace.ALICE_IDENTITY,
                "fee_escrow_id": trace.ALICE_ESCROW,
            },
        )
        self.assertEqual(
            execute(ledger, transaction, SignatureOracle()).result, "UNAUTHORIZED"
        )

    def test_a_fee_escrow_of_another_identity_is_refused(self) -> None:
        ledger = _ledger()
        _register(ledger, trace.ALICE_IDENTITY, trace.ALICE_KEY, trace.ALICE_SIGNER_KEY)
        bob = _register(
            ledger, trace.BOB_IDENTITY, trace.BOB_KEY, trace.BOB_SIGNER_KEY
        )
        transaction = _transaction(
            c.ESCROW_CREATE,
            trace.ALICE_KEY,
            1,
            {"hub_identity_hash": trace.ALICE_IDENTITY, "fee_escrow_id": bob},
        )
        self.assertEqual(
            execute(ledger, transaction, SignatureOracle()).result, "ESCROW_NOT_OWNED"
        )


class EnvelopeOrderTest(unittest.TestCase):
    """The shared checks run first, in version one's order, for every kind."""

    def setUp(self) -> None:
        self.ledger = _ledger()
        self.escrow = _register(
            self.ledger, trace.ALICE_IDENTITY, trace.ALICE_KEY, trace.ALICE_SIGNER_KEY
        )
        self.bob = _register(
            self.ledger, trace.BOB_IDENTITY, trace.BOB_KEY, trace.BOB_SIGNER_KEY
        )

    def _transfer(self, **overrides) -> str:
        body = {"recipient_escrow_id": self.bob, "amount_atomic": 1}
        body.update(overrides.pop("body", {}))
        transaction = _transaction(
            c.TRANSFER, trace.ALICE_SIGNER_KEY, overrides.pop("nonce", 1), body,
            **overrides,
        )
        return execute(self.ledger, transaction, SignatureOracle()).result

    def test_a_low_fee_limit_precedes_every_kind_condition(self) -> None:
        self.assertEqual(
            self._transfer(fee_limit=trace.FIXED_FEE - 1, body={"amount_atomic": 0}),
            "FEE_LIMIT_TOO_LOW",
        )

    def test_expiry_precedes_the_nonce(self) -> None:
        self.assertEqual(self._transfer(valid_until_height=1, nonce=99), "EXPIRED")

    def test_a_nonce_that_is_not_the_stored_one_plus_one_is_refused(self) -> None:
        self.assertEqual(self._transfer(nonce=2), "NONCE_MISMATCH")

    def test_an_exhausted_nonce_precedes_the_mismatch(self) -> None:
        self.ledger.set_nonce(self.escrow, (1 << 64) - 1)
        self.assertEqual(self._transfer(nonce=2), "NONCE_EXHAUSTED")

    def test_insufficient_balance_precedes_a_zero_amount(self) -> None:
        """Version one answers `ZERO_AMOUNT`; version six checks the envelope first."""
        self.ledger.registry.accounts[self.escrow] = (0, 0)
        self.assertEqual(self._transfer(body={"amount_atomic": 0}), "INSUFFICIENT_BALANCE")

    def test_an_overflowing_debit_is_reported_before_the_balance_comparison(self) -> None:
        self.ledger.registry.accounts[self.escrow] = ((1 << 64) - 1, 0)
        self.assertEqual(
            self._transfer(body={"amount_atomic": (1 << 64) - 1}), "DEBIT_OVERFLOW"
        )

    def test_a_registration_is_exempt_from_the_fee_limit_floor(self) -> None:
        """Its fee limit is required to be zero, so a floor would refuse every one."""
        signatures = trace.Signatures()
        message = messages.registration_message(
            self.ledger.chain_id,
            trace.MARIA_IDENTITY,
            trace.MARIA_KEY,
            trace.MARIA_NEW_SIGNER_KEY,
            1_000,
        )
        transaction = _transaction(
            c.HUB_REGISTER,
            trace.MARIA_KEY,
            0,
            {
                "hub_identity_hash": trace.MARIA_IDENTITY,
                "first_signer_public_key": trace.MARIA_NEW_SIGNER_KEY,
                "verifier_signature": signatures.sign(trace.VERIFIER_KEY, message),
            },
        )
        outcome = execute(self.ledger, transaction, signatures.oracle)
        self.assertEqual(outcome.result, "SUCCESS")
        self.assertEqual(outcome.fee_charged, 0)

    def test_a_registration_still_expires(self) -> None:
        transaction = _transaction(
            c.HUB_REGISTER,
            trace.MARIA_KEY,
            0,
            {
                "hub_identity_hash": trace.MARIA_IDENTITY,
                "first_signer_public_key": trace.MARIA_NEW_SIGNER_KEY,
                "verifier_signature": bytes(64),
            },
            valid_until_height=1,
        )
        self.assertEqual(
            execute(self.ledger, transaction, SignatureOracle()).result, "EXPIRED"
        )


class TransferTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = _ledger()
        self.alice = _register(
            self.ledger, trace.ALICE_IDENTITY, trace.ALICE_KEY, trace.ALICE_SIGNER_KEY
        )
        self.bob = _register(
            self.ledger, trace.BOB_IDENTITY, trace.BOB_KEY, trace.BOB_SIGNER_KEY
        )
        self.ledger.registry.set_posture(
            self.alice, Posture(requires_confirmation=False)
        )

    def test_a_transfer_never_creates_an_account(self) -> None:
        before = set(self.ledger.registry.accounts)
        transaction = _transaction(
            c.TRANSFER,
            trace.ALICE_SIGNER_KEY,
            1,
            {"recipient_escrow_id": bytes(range(32)), "amount_atomic": 1},
        )
        self.assertEqual(
            execute(self.ledger, transaction, SignatureOracle()).result,
            "RECIPIENT_NOT_REGISTERED",
        )
        self.assertEqual(set(self.ledger.registry.accounts), before)

    def test_a_self_transfer_cancels_and_still_pays_the_fee(self) -> None:
        opening = self.ledger.balance(self.alice)
        transaction = _transaction(
            c.TRANSFER,
            trace.ALICE_SIGNER_KEY,
            1,
            {"recipient_escrow_id": self.alice, "amount_atomic": 5},
        )
        self.assertEqual(
            execute(self.ledger, transaction, SignatureOracle()).result, "SUCCESS"
        )
        self.assertEqual(
            self.ledger.balance(self.alice), opening - self.ledger.fixed_fee
        )

    def test_a_refusal_advances_no_nonce_and_charges_no_fee(self) -> None:
        pool = self.ledger.fee_pool
        transaction = _transaction(
            c.TRANSFER,
            trace.ALICE_SIGNER_KEY,
            1,
            {"recipient_escrow_id": self.bob, "amount_atomic": 0},
        )
        self.assertEqual(
            execute(self.ledger, transaction, SignatureOracle()).result, "ZERO_AMOUNT"
        )
        self.assertEqual(self.ledger.nonce(self.alice), 0)
        self.assertEqual(self.ledger.fee_pool, pool)

    def test_the_recipient_check_precedes_the_posture(self) -> None:
        self.ledger.registry.set_posture(self.alice, Posture())
        transaction = _transaction(
            c.TRANSFER,
            trace.ALICE_SIGNER_KEY,
            1,
            {"recipient_escrow_id": bytes(range(32)), "amount_atomic": 1},
        )
        self.assertEqual(
            execute(self.ledger, transaction, SignatureOracle()).result,
            "RECIPIENT_NOT_REGISTERED",
        )

    def test_a_verified_transfer_needs_the_senders_own_identity_signature(self) -> None:
        signatures = trace.Signatures()
        wrong = messages.transfer_confirm_message(
            self.ledger.chain_id, trace.ALICE_IDENTITY, self.alice, self.bob, 2, 1_000
        )
        transaction = _transaction(
            c.TRANSFER_VERIFIED,
            trace.ALICE_SIGNER_KEY,
            1,
            {
                "recipient_escrow_id": self.bob,
                "amount_atomic": 1,
                "hub_signature": signatures.sign(trace.ALICE_KEY, wrong),
            },
        )
        self.assertEqual(
            execute(self.ledger, transaction, signatures.oracle).result, "UNAUTHORIZED"
        )


class EscrowAndSignerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = _ledger()
        self.alice = _register(
            self.ledger, trace.ALICE_IDENTITY, trace.ALICE_KEY, trace.ALICE_SIGNER_KEY
        )

    def _identity_transaction(self, kind: int, nonce: int, body: dict) -> str:
        transaction = _transaction(kind, trace.ALICE_KEY, nonce, body)
        return execute(self.ledger, transaction, SignatureOracle()).result

    def test_a_deleted_index_is_never_reissued(self) -> None:
        self.assertEqual(
            self._identity_transaction(
                c.ESCROW_CREATE,
                1,
                {
                    "hub_identity_hash": trace.ALICE_IDENTITY,
                    "fee_escrow_id": self.alice,
                },
            ),
            "SUCCESS",
        )
        created = [key for key in self.ledger.registry.escrows if key != self.alice][0]
        self.assertEqual(
            self._identity_transaction(
                c.ESCROW_DELETE,
                2,
                {
                    "hub_identity_hash": trace.ALICE_IDENTITY,
                    "target_escrow_id": created,
                    "fee_escrow_id": self.alice,
                },
            ),
            "SUCCESS",
        )
        self.assertEqual(
            self._identity_transaction(
                c.ESCROW_CREATE,
                3,
                {
                    "hub_identity_hash": trace.ALICE_IDENTITY,
                    "fee_escrow_id": self.alice,
                },
            ),
            "SUCCESS",
        )
        reissued = [key for key in self.ledger.registry.escrows if key != self.alice][0]
        self.assertNotEqual(reissued, created)
        identity = self.ledger.registry.identities[trace.ALICE_IDENTITY]
        self.assertEqual(identity.next_escrow_index, 3)
        self.assertEqual(identity.escrow_count, 2)

    def test_an_escrow_holding_value_cannot_be_deleted(self) -> None:
        self.assertEqual(
            self._identity_transaction(
                c.ESCROW_DELETE,
                1,
                {
                    "hub_identity_hash": trace.ALICE_IDENTITY,
                    "target_escrow_id": self.alice,
                    "fee_escrow_id": self.alice,
                },
            ),
            "ESCROW_NOT_EMPTY",
        )

    def test_a_signer_key_belongs_to_exactly_one_escrow(self) -> None:
        self.assertEqual(
            self._identity_transaction(
                c.SIGNER_ADD,
                1,
                {
                    "hub_identity_hash": trace.ALICE_IDENTITY,
                    "escrow_id": self.alice,
                    "signer_public_key": trace.ALICE_SIGNER_KEY,
                },
            ),
            "REPLAY",
        )

    def test_an_escrow_holds_at_most_sixteen_signers(self) -> None:
        for index in range(1, c.MAX_SIGNERS_PER_ESCROW):
            self.ledger.registry.add_signer(self.alice, bytes([index]) * 32)
        self.assertEqual(
            self._identity_transaction(
                c.SIGNER_ADD,
                1,
                {
                    "hub_identity_hash": trace.ALICE_IDENTITY,
                    "escrow_id": self.alice,
                    "signer_public_key": bytes([0xEE]) * 32,
                },
            ),
            "SIGNER_LIMIT",
        )

    def test_revoking_a_signer_of_another_escrow_is_unauthorized(self) -> None:
        bob = _register(
            self.ledger, trace.BOB_IDENTITY, trace.BOB_KEY, trace.BOB_SIGNER_KEY
        )
        del bob
        self.assertEqual(
            self._identity_transaction(
                c.SIGNER_REVOKE,
                1,
                {
                    "hub_identity_hash": trace.ALICE_IDENTITY,
                    "escrow_id": self.alice,
                    "signer_id": signer_id(trace.BOB_SIGNER_KEY),
                },
            ),
            "UNAUTHORIZED",
        )


class DerivedRuleTest(unittest.TestCase):
    """The three readings ADR 0045 settled, tested where they bite."""

    def test_the_result_code_space_has_no_malformed_transaction(self) -> None:
        self.assertNotIn("MALFORMED_TRANSACTION", c.CODE_NUMBER)
        self.assertEqual(c.ADMISSION_CODES[1], "MALFORMED_TRANSACTION")
        self.assertEqual(c.RESULT_CODES[1], "ZERO_AMOUNT")

    def test_an_unrequested_confirmation_is_refused_with_unauthorized(self) -> None:
        with self.assertRaises(Refused) as refusal:
            require_zero_confirmation(bytes([1]) + bytes(63))
        self.assertEqual(refusal.exception.result, "UNAUTHORIZED")
        require_zero_confirmation(bytes(64))

    def test_direct_issue_is_refused_for_every_acting_key(self) -> None:
        ledger = _ledger()
        _register(ledger, trace.ALICE_IDENTITY, trace.ALICE_KEY, trace.ALICE_SIGNER_KEY)
        transaction = _transaction(
            c.DIRECT_ISSUE,
            trace.ALICE_SIGNER_KEY,
            1,
            {
                "channel_id": c.DIRECT_ISSUE_CHANNELS[0],
                "decision_id": bytes(32),
                "beneficiary_escrow_id": trace.ALICE_ESCROW,
                "amount_atomic": 1,
                "authorization": bytes(32),
            },
        )
        self.assertEqual(
            execute(ledger, transaction, SignatureOracle()).result, "UNAUTHORIZED"
        )


class AdmissionTest(unittest.TestCase):
    def test_a_wrong_chain_is_refused_after_the_shape_and_before_the_signature(
        self,
    ) -> None:
        signatures = trace.Signatures()
        transaction = _transaction(
            c.TRANSFER,
            trace.ALICE_SIGNER_KEY,
            1,
            {"recipient_escrow_id": bytes(32), "amount_atomic": 1},
        )
        unsigned = unsigned_bytes(transaction)
        raw = signed_bytes(
            transaction,
            signatures.sign(trace.ALICE_SIGNER_KEY, signing_message(unsigned)),
        )
        self.assertEqual(
            admit(raw, bytes(range(32)), signatures.oracle).code,
            2,
        )
        self.assertTrue(admit(raw, bytes(32), signatures.oracle).admitted)

    def test_an_unrecorded_signature_is_an_invalid_signature(self) -> None:
        signatures = trace.Signatures()
        transaction = _transaction(
            c.TRANSFER,
            trace.ALICE_SIGNER_KEY,
            1,
            {"recipient_escrow_id": bytes(32), "amount_atomic": 1},
        )
        raw = signed_bytes(transaction, bytes(64))
        self.assertEqual(admit(raw, bytes(32), signatures.oracle).code, 3)

    def test_a_retired_kind_is_malformed(self) -> None:
        raw = bytearray(
            signed_bytes(
                _transaction(
                    c.TRANSFER,
                    trace.ALICE_SIGNER_KEY,
                    1,
                    {"recipient_escrow_id": bytes(32), "amount_atomic": 1},
                ),
                bytes(64),
            )
        )
        raw[6] = 9
        self.assertEqual(admit(bytes(raw), bytes(32), SignatureOracle()).code, 1)


class ConservationTest(unittest.TestCase):
    def test_a_debit_below_zero_is_an_invariant_failure_not_a_result(self) -> None:
        ledger = _ledger()
        escrow = _register(
            ledger, trace.ALICE_IDENTITY, trace.ALICE_KEY, trace.ALICE_SIGNER_KEY
        )
        with self.assertRaises(ConservationFailure):
            ledger.debit(escrow, ledger.balance(escrow) + 1)

    def test_the_verified_user_channel_holds_no_outstanding_amount(self) -> None:
        ledger = _ledger()
        _register(ledger, trace.ALICE_IDENTITY, trace.ALICE_KEY, trace.ALICE_SIGNER_KEY)
        self.assertEqual(ledger.channel_outstanding[c.VERIFIED_USER_CHANNEL], 0)
        self.assertEqual(ledger.conservation_failures(), [])

    def test_advancing_past_a_due_assignment_is_refused(self) -> None:
        ledger = _ledger()
        with self.assertRaises(ConservationFailure):
            ledger.advance_to(4 * c.CYCLE_BLOCKS, {2: ["a record"]})


if __name__ == "__main__":
    unittest.main()
