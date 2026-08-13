"""The checked-in fixture the normative vectors are taken over.

The transfer inputs are the accepted `protocol-primitives-v1` transfer's inputs,
restated here so the verifier can require this model's encoder to reproduce that
specification's recorded unsigned bytes, signed bytes, and transaction ID. A
mistyped input fails that comparison rather than passing quietly.

The economy fixtures sit on boundaries rather than round numbers: seat 0 and seat
99,999, a purchased seat that is never activated, a cycle whose winner set
excludes both a failed seat and a seat that met below the maximum. An off-by-one
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

# A stand-in for the ecosystem verifier's signature over an enrollment or
# activation message. The model never verifies it, because verification is
# Ed25519 and this model implements no cryptographic primitive; the vectors fix
# the message construction the verifier signs, which is the part that is
# consensus-visible.
BIOMETRIC_SIGNATURE = bytes.fromhex("44" * 64)
VERIFIER_KEY = bytes.fromhex("55" * 32)

BIOMETRIC_IDENTITY_HASH = bytes.fromhex("66" * 32)
PURCHASER_ACCOUNT_ID = bytes.fromhex("77" * 32)
REFERRER_ACCOUNT_ID = bytes.fromhex("88" * 32)

DECISION_ID = bytes.fromhex("11" * 32)
BENEFICIARY_ACCOUNT_ID = bytes.fromhex("22" * 32)
AUTHORIZATION = bytes.fromhex("33" * 32)

FEE_LIMIT = 1_000
VALID_UNTIL_HEIGHT = 42


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
        "purchase_referred_seat": _envelope(
            c.PURCHASE_SEAT,
            2,
            {
                "seat_id": 0,
                "biometric_identity_hash": BIOMETRIC_IDENTITY_HASH,
                "purchaser_account_id": PURCHASER_ACCOUNT_ID,
                "has_referrer": True,
                "referrer_account_id": REFERRER_ACCOUNT_ID,
                "biometric_signature": BIOMETRIC_SIGNATURE,
            },
        ),
        "purchase_unreferred_last_seat": _envelope(
            c.PURCHASE_SEAT,
            3,
            {
                "seat_id": c.MAX_SEAT_ID,
                "biometric_identity_hash": BIOMETRIC_IDENTITY_HASH,
                "purchaser_account_id": PURCHASER_ACCOUNT_ID,
                "has_referrer": False,
                "referrer_account_id": bytes(32),
                "biometric_signature": BIOMETRIC_SIGNATURE,
            },
        ),
        "activate_seat": _envelope(
            c.ACTIVATE_SEAT,
            4,
            {"seat_id": 0, "biometric_signature": BIOMETRIC_SIGNATURE},
        ),
        "mint_node": _envelope(c.MINT_NODE, 5, {"seat_id": 0}),
        "mint_referral": _envelope(c.MINT_REFERRAL, 6, {}),
        "direct_issue": _envelope(
            c.DIRECT_ISSUE,
            7,
            {
                "channel_id": 5,
                "decision_id": DECISION_ID,
                "beneficiary_account_id": BENEFICIARY_ACCOUNT_ID,
                "amount_atomic": 100_000_000,
                "authorization": AUTHORIZATION,
            },
        ),
    }


# One cycle's finalised measurement over four in-scope seats. Seat 7 failed,
# seats 0 and 4 met at the maximum, and seat 99,999 met below it, so the winner
# set must exclude both the failed seat and the lower-uptime one. Two winners
# tie at the maximum, which the constitution expects to be the ordinary case at
# a perfect cycle rather than an adversarial one.
CYCLE_WINDOW = 12
IN_SCOPE_SEATS: tuple[int, ...] = (0, 4, 7, c.MAX_SEAT_ID)
CYCLE_UPTIME: dict[int, int] = {0: 86_400, 4: 86_400, 7: 32_400, c.MAX_SEAT_ID: 64_800}
CYCLE_MET: dict[int, bool] = {0: True, 4: True, 7: False, c.MAX_SEAT_ID: True}


def cycle_winners() -> tuple[int, ...]:
    """Derived from the cycle fixture rather than restated beside it.

    A restated set would agree with the derivation until one of them was edited,
    and the fixture is the positive control every mutation is measured against.
    """
    from .winners import derive_winner_set

    return derive_winner_set(CYCLE_UPTIME, CYCLE_MET)


def cycle_assignment_entry() -> tuple[bytes, bytes]:
    """The one record the chain writes when this cycle is finalised."""
    from .state import bitmap, cycle_assignment_key, cycle_assignment_value
    from .winners import split_permission

    winners = cycle_winners()
    shares, _ = split_permission(len(winners))
    return (
        cycle_assignment_key(CYCLE_WINDOW),
        cycle_assignment_value(
            shares[c.FOUNDER_OPERATOR_CHANNEL],
            len(winners),
            len(IN_SCOPE_SEATS),
            bitmap([CYCLE_MET[seat] for seat in IN_SCOPE_SEATS]),
            bitmap([seat in winners for seat in IN_SCOPE_SEATS]),
        ),
    )


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
        verifier_key=VERIFIER_KEY,
        accounts=[],
    )


def populated_economy() -> dict[bytes, bytes]:
    """One entry of every kind, so the tree is exercised over all eight."""
    from .genesis import initial_economy_entries
    from .state import (
        direct_decision_key,
        referral_balance_key,
        referral_balance_value,
        seat_key,
        seat_value,
        typed_custody_key,
        typed_custody_value,
    )

    entries = initial_economy_entries(VERIFIER_KEY)
    # An activated seat that has minted through cycle 11, and a purchased seat
    # that has never been activated — the state nothing expires.
    entries[seat_key(0)] = seat_value(
        BIOMETRIC_IDENTITY_HASH,
        PURCHASER_ACCOUNT_ID,
        REFERRER_ACCOUNT_ID,
        activation_height=7 * c.CYCLE_BLOCKS,
        minted_through_window=11,
    )
    entries[seat_key(c.MAX_SEAT_ID)] = seat_value(
        BIOMETRIC_IDENTITY_HASH, PURCHASER_ACCOUNT_ID, None
    )
    entries[referral_balance_key(REFERRER_ACCOUNT_ID)] = referral_balance_value(
        c.REFERRAL_LEG_ATOMIC * 3, c.REFERRAL_LEG_ATOMIC
    )
    entries[direct_decision_key(DECISION_ID)] = b""
    entries[typed_custody_key(1, BENEFICIARY_ACCOUNT_ID)] = typed_custody_value(
        34_200_000_000
    )
    key, value = cycle_assignment_entry()
    entries[key] = value
    return entries
