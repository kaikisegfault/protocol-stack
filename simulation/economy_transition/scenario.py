"""The checked-in fixture the normative vectors are taken over.

The transfer inputs are the accepted `protocol-primitives-v1` transfer's inputs,
restated here so the verifier can require this model's encoder to reproduce that
specification's recorded unsigned bytes, signed bytes, and transaction ID. A
mistyped input fails that comparison rather than passing quietly.

The economy fixtures sit on boundaries rather than round numbers: seat 0 and seat
99,999, cycle 0 and cycle 730, an empty and a populated winner set. An off-by-one
in a bounded field is invisible in the middle of a range.
"""

from __future__ import annotations

from . import contract as c
from .envelope import Transaction
from .genesis import Genesis

CHAIN_ID = bytes(range(32))
SENDER_PUBLIC_KEY = bytes.fromhex(
    "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
)
RECIPIENT_ACCOUNT_ID = bytes(range(0x20, 0x40))

# The accepted version-one transfer's signature, carried rather than computed:
# this model implements no cryptographic primitive.
TRANSFER_SIGNATURE = bytes.fromhex(
    "4678857e9c2da9acd3796819bd151958c6497122d962b0600ba51914d0b10d3a"
    "b922b9bba415e4fdc7d120227548a7c0ec87fc66315d01b8f64165944ee82b06"
)

FEE_LIMIT = 1_000
VALID_UNTIL_HEIGHT = 42

DECISION_ID = bytes.fromhex("11" * 32)
BENEFICIARY_ACCOUNT_ID = bytes.fromhex("22" * 32)
AUTHORIZATION = bytes.fromhex("33" * 32)


def _envelope(kind: int, nonce: int, body: dict) -> Transaction:
    return Transaction(
        kind=kind,
        chain_id=CHAIN_ID,
        sender_public_key=SENDER_PUBLIC_KEY,
        nonce=nonce,
        body=body,
        fee_limit=FEE_LIMIT,
        valid_until_height=VALID_UNTIL_HEIGHT,
    )


def accepted_transfer() -> Transaction:
    """The accepted version-one transfer, expressed as a kind-1 version-two one."""
    return _envelope(
        c.TRANSFER,
        1,
        {"recipient_account_id": RECIPIENT_ACCOUNT_ID, "amount_atomic": 1_000_000},
    )


def transactions() -> dict[str, Transaction]:
    """One transaction per kind, plus the boundary instances that matter."""
    return {
        "transfer": accepted_transfer(),
        "activate_first_seat": _envelope(
            c.ACTIVATE_SEAT,
            2,
            {"seat_id": 0, "has_referrer": False, "referrer_seat_id": 0},
        ),
        "activate_last_seat": _envelope(
            c.ACTIVATE_SEAT,
            3,
            {"seat_id": c.MAX_SEAT_ID, "has_referrer": True, "referrer_seat_id": 0},
        ),
        "evaluate_first_cycle": _envelope(
            c.EVALUATE_BASE_PERMISSION, 4, {"seat_id": 7, "cycle_index": 0}
        ),
        "evaluate_last_cycle": _envelope(
            c.EVALUATE_BASE_PERMISSION,
            5,
            {"seat_id": 7, "cycle_index": c.MAX_CYCLE_INDEX},
        ),
        "exercise_met_cycle": _envelope(
            c.EXERCISE_PERMISSION,
            6,
            {"seat_id": 7, "cycle_index": 0, "winners": ()},
        ),
        "exercise_failed_cycle": _envelope(
            c.EXERCISE_PERMISSION,
            7,
            {"seat_id": 7, "cycle_index": 1, "winners": window_winners()},
        ),
        "accrue_referral": _envelope(
            c.ACCRUE_REFERRAL, 8, {"seat_id": c.MAX_SEAT_ID, "cycle_index": 0}
        ),
        "direct_issue": _envelope(
            c.DIRECT_ISSUE,
            9,
            {
                "channel_id": 5,
                "decision_id": DECISION_ID,
                "beneficiary_account_id": BENEFICIARY_ACCOUNT_ID,
                "amount_atomic": 100_000_000,
                "authorization": AUTHORIZATION,
            },
        ),
    }


# One window's finalised measurement over four in-scope seats. Seat 7 failed,
# seats 0 and 4 met at the maximum, and seat 99,999 met below it, so the winner
# set must exclude both the failed seat and the lower-uptime one. Two winners
# tie at the maximum, which the constitution expects to be the ordinary case at
# a perfect cycle rather than an adversarial one.
WINDOW = 12
WINDOW_UPTIME: dict[int, int] = {0: 86_400, 4: 86_400, 7: 32_400, c.MAX_SEAT_ID: 64_800}
WINDOW_MET: dict[int, bool] = {0: True, 4: True, 7: False, c.MAX_SEAT_ID: True}


def window_winners() -> tuple[int, ...]:
    """Derived from the window fixture rather than restated beside it.

    A restated set would agree with the derivation until one of them was edited,
    and the exercise fixture is the positive control the mutation cases are
    measured against, so it must not be able to drift from the commitment.
    """
    from .winners import derive_winner_set

    return derive_winner_set(WINDOW_UPTIME, WINDOW_MET)


def genesis() -> Genesis:
    """A Founder Economy genesis: no allocation, no accounts, and a zero fee.

    Every field is what the constitution forces rather than what a devnet would
    find convenient, so the three relaxations version one forbids are exercised
    together rather than one at a time.
    """
    return Genesis(
        network_id=2,
        supply_limit=5_699_395_010_000_000_000,
        total_supply=0,
        fixed_transfer_fee=0,
        initial_fee_pool=0,
        manifest_digest=bytes.fromhex(c.MANIFEST_DIGEST_HEX),
        accounts=[],
    )


def populated_economy() -> dict[bytes, bytes]:
    """One entry of every kind, so the tree is exercised over all eight."""
    from .genesis import initial_economy_entries
    from .state import (
        direct_decision_key,
        met_bitmap,
        pending_permission_key,
        pending_permission_value,
        referral_accrual_key,
        seat_key,
        seat_value,
        typed_custody_key,
        typed_custody_value,
        window_result_key,
        window_result_value,
    )
    from .winners import derive_winner_set, winner_root

    entries = initial_economy_entries()
    entries[seat_key(0)] = seat_value(0, None)
    entries[seat_key(7)] = seat_value(7 * c.CYCLE_BLOCKS, 0)
    entries[pending_permission_key(7, 1)] = pending_permission_value(c.VERDICT_FAILED)
    entries[referral_accrual_key(c.MAX_SEAT_ID, 0)] = b""
    entries[direct_decision_key(DECISION_ID)] = b""
    entries[typed_custody_key(1, BENEFICIARY_ACCOUNT_ID)] = typed_custody_value(
        34_200_000_000
    )
    winners = derive_winner_set(WINDOW_UPTIME, WINDOW_MET)
    entries[window_result_key(WINDOW)] = window_result_value(
        winner_root(winners),
        len(winners),
        3,
        met_bitmap([WINDOW_MET[seat] for seat in sorted(WINDOW_MET)]),
    )
    return entries
