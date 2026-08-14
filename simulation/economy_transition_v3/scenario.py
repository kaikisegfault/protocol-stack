"""The checked-in fixture the normative vectors are taken over.

The transfer inputs are the accepted `protocol-primitives-v1` transfer's inputs,
restated here so the verifier can require this model's encoder to reproduce that
specification's recorded unsigned bytes, signed bytes, and transaction ID.

The economy fixtures sit on boundaries rather than round numbers, and the cycle
fixture is built around the one case version two could not have: **the highest
uptime in the cycle belongs to a seat that is over the accumulation cap.** If a
capped seat were eligible to win, the winner set would be that seat alone;
because it is not, the winners are the three seats at the next-highest figure.
A fixture in which the capped seat merely tied would not tell the two rules
apart.

The second cycle is a total outage: no seat met it, so the winner set is empty
and the whole reallocated amount carries forward, which is the founder-directed
rule for that case and the one path a busy cycle never reaches.
"""

from __future__ import annotations

from . import contract as c
from .envelope import Transaction
from .genesis import Genesis
from .settlement import SeatCycle

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

# A stand-in for the ecosystem verifier's signature. The model never verifies
# it, because verification is Ed25519 and this model implements no
# cryptographic primitive; the vectors fix the six message constructions the
# verifier signs, which is the part that is consensus-visible.
BIOMETRIC_SIGNATURE = bytes.fromhex("44" * 64)
VERIFIER_KEY = bytes.fromhex("55" * 32)

BIOMETRIC_IDENTITY_HASH = bytes.fromhex("66" * 32)
PURCHASER_ACCOUNT_ID = bytes.fromhex("77" * 32)
REFERRER_ACCOUNT_ID = bytes.fromhex("88" * 32)
CAPPED_REFERRER_ACCOUNT_ID = bytes.fromhex("99" * 32)
MANAGER_ACCOUNT_ID = bytes.fromhex("aa" * 32)
HUB_UNIQUENESS_HASH = bytes.fromhex("bb" * 32)

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
    """The accepted version-one transfer, expressed as a kind-1 version-three one."""
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
        "mint_node_verified": _envelope(
            c.MINT_NODE_VERIFIED,
            8,
            {"seat_id": 0, "biometric_signature": BIOMETRIC_SIGNATURE},
        ),
        "enable_mint_biometric": _envelope(
            c.SET_MINT_BIOMETRIC,
            9,
            {"seat_id": 0, "enable": True, "biometric_signature": bytes(64)},
        ),
        "disable_mint_biometric": _envelope(
            c.SET_MINT_BIOMETRIC,
            10,
            {"seat_id": 0, "enable": False, "biometric_signature": BIOMETRIC_SIGNATURE},
        ),
        "add_manager": _envelope(
            c.ADD_MANAGER,
            11,
            {
                "seat_id": 0,
                "manager_account_id": MANAGER_ACCOUNT_ID,
                "biometric_signature": BIOMETRIC_SIGNATURE,
            },
        ),
        "hub_verify": _envelope(
            c.HUB_VERIFY,
            12,
            {
                "hub_uniqueness_hash": HUB_UNIQUENESS_HASH,
                "biometric_signature": BIOMETRIC_SIGNATURE,
            },
        ),
    }


# The two cycles the settlement vectors are taken over. Window 200 is finalised
# at the first height of window 202 and window 201 at the first height of 203,
# so a mint at `ASSIGNMENT_HEIGHT` sees both.
CYCLE_WINDOW = 200
OUTAGE_WINDOW = 201
ASSIGNMENT_HEIGHT = (OUTAGE_WINDOW + c.ASSIGNMENT_LAG_WINDOWS) * c.CYCLE_BLOCKS

CURRENT_MARK = CYCLE_WINDOW - 1
CAPPED_MARK = CYCLE_WINDOW - 100

MAXIMUM_UPTIME = 86_400
HIGH_UPTIME = 82_800
# Exactly the founder-directed 18-hour threshold, so the boundary is met rather
# than cleared.
THRESHOLD_UPTIME = 64_800
FAILED_UPTIME = 32_400
OUTAGE_UPTIME = 3_600


def cycle_seats() -> list[SeatCycle]:
    """Six in-scope seats, each reaching a different path through the rule.

    Seat 11 holds the maximum uptime in the cycle and is over the cap, so it
    neither accrues nor wins and its permission is reallocated. Seat 15 sits
    exactly on the activity threshold, so it accrues its own permission and wins
    nothing. Seat 23 is past its own 731 cycles, so it has no permission of its
    own and still wins a share of someone else's — the case the in-scope set
    exists to cover. Between them, accruing and winning are shown to be
    independent facts in both directions.
    """
    return [
        SeatCycle(0, HIGH_UPTIME, True, CURRENT_MARK, REFERRER_ACCOUNT_ID),
        SeatCycle(4, HIGH_UPTIME, True, CURRENT_MARK, None),
        SeatCycle(7, FAILED_UPTIME, True, CURRENT_MARK, CAPPED_REFERRER_ACCOUNT_ID),
        SeatCycle(11, MAXIMUM_UPTIME, True, CAPPED_MARK, REFERRER_ACCOUNT_ID),
        SeatCycle(15, THRESHOLD_UPTIME, True, CURRENT_MARK, None),
        SeatCycle(23, HIGH_UPTIME, False, CURRENT_MARK, None),
    ]


def outage_seats() -> list[SeatCycle]:
    """The same population through a cycle no seat met."""
    return [
        SeatCycle(seat.seat_id, OUTAGE_UPTIME, seat.in_span, seat.minted_through_window,
                  seat.referrer_account_id)
        for seat in cycle_seats()
    ]


REFERRER_MARKS: dict[bytes, int] = {
    REFERRER_ACCOUNT_ID: CURRENT_MARK,
    CAPPED_REFERRER_ACCOUNT_ID: CAPPED_MARK,
}


def assignments() -> dict[int, object]:
    """Both cycles' derived assignments, keyed by window."""
    from .settlement import derive_assignment

    return {
        CYCLE_WINDOW: derive_assignment(CYCLE_WINDOW, cycle_seats()),
        OUTAGE_WINDOW: derive_assignment(OUTAGE_WINDOW, outage_seats()),
    }


def assignment_records() -> dict[int, bytes]:
    """The encoded records a mint walks."""
    from .settlement import assignment_entry

    return {
        window: assignment_entry(assignment)[1]
        for window, assignment in assignments().items()
    }


def genesis() -> Genesis:
    """A Founder Economy genesis: no allocation, no accounts, and a zero fee.

    Every field is what the constitution forces rather than what a devnet would
    find convenient, so the three relaxations version one forbids are exercised
    together rather than one at a time.
    """
    return Genesis(
        network_id=3,
        supply_limit=5_699_395_010_000_000_000,
        total_supply=0,
        fixed_transfer_fee=0,
        initial_fee_pool=0,
        manifest_digest=bytes.fromhex(c.MANIFEST_DIGEST_HEX),
        verifier_key=VERIFIER_KEY,
        accounts=[],
    )


def populated_economy() -> dict[bytes, bytes]:
    """One entry of every kind, so the tree is exercised over all eleven."""
    from .genesis import initial_economy_entries
    from .settlement import assignment_entry
    from .state import (
        direct_decision_key,
        hub_registration_key,
        hub_registration_value,
        referral_balance_key,
        referral_balance_value,
        seat_key,
        seat_manager_key,
        seat_manager_value,
        seat_value,
        typed_custody_key,
        typed_custody_value,
    )

    entries = initial_economy_entries(VERIFIER_KEY)
    # An activated seat with two managers and no protection, and a purchased
    # seat that has never been activated and has switched protection on before
    # it ever earns anything.
    entries[seat_key(0)] = seat_value(
        BIOMETRIC_IDENTITY_HASH,
        PURCHASER_ACCOUNT_ID,
        REFERRER_ACCOUNT_ID,
        activation_height=7 * c.CYCLE_BLOCKS,
        minted_through_window=CURRENT_MARK,
        mint_requires_biometric=False,
        manager_count=2,
    )
    entries[seat_key(c.MAX_SEAT_ID)] = seat_value(
        BIOMETRIC_IDENTITY_HASH,
        PURCHASER_ACCOUNT_ID,
        None,
        mint_requires_biometric=True,
    )
    entries[seat_manager_key(0, PURCHASER_ACCOUNT_ID)] = seat_manager_value()
    entries[seat_manager_key(0, MANAGER_ACCOUNT_ID)] = seat_manager_value()
    entries[referral_balance_key(REFERRER_ACCOUNT_ID)] = referral_balance_value(
        c.REFERRAL_LEG_ATOMIC * 3, c.REFERRAL_LEG_ATOMIC, CURRENT_MARK
    )
    entries[hub_registration_key(REFERRER_ACCOUNT_ID)] = hub_registration_value(
        HUB_UNIQUENESS_HASH, 5 * c.CYCLE_BLOCKS
    )
    entries[direct_decision_key(DECISION_ID)] = b""
    entries[typed_custody_key(
        c.VENTURE_ESCROW_BENEFICIARY, c.SINGLETON_BENEFICIARY_ID
    )] = typed_custody_value(17_100_000_000)
    for assignment in assignments().values():
        key, value = assignment_entry(assignment)
        entries[key] = value
    return entries
