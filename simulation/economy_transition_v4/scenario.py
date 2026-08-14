"""The checked-in fixture the normative vectors are taken over.

The transfer inputs are the accepted `protocol-primitives-v1` transfer's inputs,
restated here so the verifier can require this model's encoder to reproduce that
specification's recorded unsigned bytes, signed bytes, and transaction ID.

**The cycle population is version three's, unchanged.** The settlement is
imported rather than reimplemented, so the assignment record version four writes
for the same seats must be byte-identical to the one version three recorded. A
fixture that differed would hide exactly the drift the import is there to
prevent, so the same uptimes, spans, and marks are used and the equality is a
vector.

The registry fixture is built around the cases version three could not have:
one person holding two addresses, an address removed without touching anything
else, a self-referral across two addresses of one identity, and the
constitution's per-human seat bound at its boundary.
"""

from __future__ import annotations

from simulation.economy_transition_v3 import scenario as v3
from simulation.economy_transition_v3.settlement import SeatCycle

from . import contract as c
from .envelope import Transaction
from .genesis import Genesis
from .identity import Registry

CHAIN_ID = bytes(range(32))
SENDER_PUBLIC_KEY = bytes.fromhex(
    "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
)
RECIPIENT_ACCOUNT_ID = bytes(range(0x20, 0x40))

TRANSFER_SIGNATURE = bytes.fromhex(
    "4678857e9c2da9acd3796819bd151958c6497122d962b0600ba51914d0b10d3a"
    "b922b9bba415e4fdc7d120227548a7c0ec87fc66315d01b8f64165944ee82b06"
)

# Stand-ins. The model never verifies a signature, because verification is
# Ed25519 and this model implements no cryptographic primitive; the vectors fix
# the eight message constructions, which is the consensus-visible part.
HUB_SIGNATURE = bytes.fromhex("44" * 64)
VERIFIER_SIGNATURE = bytes.fromhex("dd" * 64)
VERIFIER_KEY = bytes.fromhex("55" * 32)

# Three people. Alice holds two addresses, Bob one, and Carol's single address
# is removed, which is the case that shows removal touches nothing else.
ALICE_IDENTITY = bytes.fromhex("a1" * 32)
ALICE_KEY = bytes.fromhex("a2" * 32)
ALICE_FIRST_ADDRESS = bytes.fromhex("a3" * 32)
ALICE_SECOND_ADDRESS = bytes.fromhex("a4" * 32)

BOB_IDENTITY = bytes.fromhex("b1" * 32)
BOB_KEY = bytes.fromhex("b2" * 32)
BOB_ADDRESS = bytes.fromhex("b3" * 32)

CAROL_IDENTITY = bytes.fromhex("c1" * 32)
CAROL_KEY = bytes.fromhex("c2" * 32)
CAROL_ADDRESS = bytes.fromhex("c3" * 32)

MANAGER_ACCOUNT_ID = bytes.fromhex("aa" * 32)

DECISION_ID = bytes.fromhex("11" * 32)
BENEFICIARY_ACCOUNT_ID = bytes.fromhex("22" * 32)
AUTHORIZATION = bytes.fromhex("33" * 32)

FEE_LIMIT = 1_000
VALID_UNTIL_HEIGHT = 42
REGISTRATION_HEIGHT = 5 * c.CYCLE_BLOCKS


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
    """The accepted version-one transfer, expressed as a kind-1 version-four one."""
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
                "purchaser_account_id": ALICE_FIRST_ADDRESS,
                "has_referrer": True,
                "referrer_account_id": BOB_ADDRESS,
                "hub_signature": HUB_SIGNATURE,
            },
        ),
        "purchase_unreferred_last_seat": _envelope(
            c.PURCHASE_SEAT,
            3,
            {
                "seat_id": c.MAX_SEAT_ID,
                "purchaser_account_id": ALICE_FIRST_ADDRESS,
                "has_referrer": False,
                "referrer_account_id": bytes(32),
                "hub_signature": HUB_SIGNATURE,
            },
        ),
        "activate_seat": _envelope(
            c.ACTIVATE_SEAT, 4, {"seat_id": 0, "hub_signature": HUB_SIGNATURE}
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
            c.MINT_NODE_VERIFIED, 8, {"seat_id": 0, "hub_signature": HUB_SIGNATURE}
        ),
        "enable_mint_biometric": _envelope(
            c.SET_MINT_BIOMETRIC,
            9,
            {"seat_id": 0, "enable": True, "hub_signature": bytes(64)},
        ),
        "disable_mint_biometric": _envelope(
            c.SET_MINT_BIOMETRIC,
            10,
            {"seat_id": 0, "enable": False, "hub_signature": HUB_SIGNATURE},
        ),
        "add_manager": _envelope(
            c.ADD_MANAGER,
            11,
            {
                "seat_id": 0,
                "manager_account_id": MANAGER_ACCOUNT_ID,
                "hub_signature": HUB_SIGNATURE,
            },
        ),
        "hub_register": _envelope(
            c.HUB_REGISTER,
            12,
            {
                "hub_identity_hash": ALICE_IDENTITY,
                "hub_public_key": ALICE_KEY,
                "verifier_signature": VERIFIER_SIGNATURE,
            },
        ),
        "hub_add_address": _envelope(
            c.HUB_ADD_ADDRESS,
            13,
            {"account_id": ALICE_SECOND_ADDRESS, "hub_signature": HUB_SIGNATURE},
        ),
        "hub_remove_address": _envelope(
            c.HUB_REMOVE_ADDRESS,
            14,
            {"account_id": CAROL_ADDRESS, "hub_signature": HUB_SIGNATURE},
        ),
    }


def registry() -> Registry:
    """Alice with two addresses, Bob with one, Carol registered and unlinked."""
    built = Registry()
    built.register(ALICE_IDENTITY, ALICE_KEY, ALICE_FIRST_ADDRESS, REGISTRATION_HEIGHT)
    built.add_address(ALICE_IDENTITY, ALICE_SECOND_ADDRESS)
    built.register(BOB_IDENTITY, BOB_KEY, BOB_ADDRESS, REGISTRATION_HEIGHT + 1)
    built.register(CAROL_IDENTITY, CAROL_KEY, CAROL_ADDRESS, REGISTRATION_HEIGHT + 2)
    built.remove_address(CAROL_ADDRESS)
    built.claim_seat(ALICE_IDENTITY)
    return built


# The settlement fixture is version three's, unchanged, so the assignment record
# must come out byte-identical. Only the referrer key is re-keyed from an
# account to a HUB identity — which needs no new code, because version three's
# referrer key is opaque bytes, and that is itself evidence the settlement did
# not move.
CYCLE_WINDOW = v3.CYCLE_WINDOW
OUTAGE_WINDOW = v3.OUTAGE_WINDOW
ASSIGNMENT_HEIGHT = v3.ASSIGNMENT_HEIGHT
CURRENT_MARK = v3.CURRENT_MARK
CAPPED_MARK = v3.CAPPED_MARK

REFERRER_IDENTITY = BOB_IDENTITY
CAPPED_REFERRER_IDENTITY = CAROL_IDENTITY

_IDENTITY_BY_V3_KEY: dict[bytes | None, bytes | None] = {
    v3.REFERRER_ACCOUNT_ID: REFERRER_IDENTITY,
    v3.CAPPED_REFERRER_ACCOUNT_ID: CAPPED_REFERRER_IDENTITY,
    None: None,
}


def cycle_seats() -> list[SeatCycle]:
    return [
        SeatCycle(
            seat.seat_id,
            seat.uptime_seconds,
            seat.in_span,
            seat.minted_through_window,
            _IDENTITY_BY_V3_KEY[seat.referrer_account_id],
        )
        for seat in v3.cycle_seats()
    ]


def outage_seats() -> list[SeatCycle]:
    return [
        SeatCycle(
            seat.seat_id,
            seat.uptime_seconds,
            seat.in_span,
            seat.minted_through_window,
            _IDENTITY_BY_V3_KEY[seat.referrer_account_id],
        )
        for seat in v3.outage_seats()
    ]


REFERRER_MARKS: dict[bytes, int] = {
    REFERRER_IDENTITY: CURRENT_MARK,
    CAPPED_REFERRER_IDENTITY: CAPPED_MARK,
}


def assignments() -> dict[int, object]:
    from simulation.economy_transition_v3.settlement import derive_assignment

    return {
        CYCLE_WINDOW: derive_assignment(CYCLE_WINDOW, cycle_seats()),
        OUTAGE_WINDOW: derive_assignment(OUTAGE_WINDOW, outage_seats()),
    }


def assignment_records() -> dict[int, bytes]:
    from simulation.economy_transition_v3.settlement import assignment_entry

    return {
        window: assignment_entry(assignment)[1]
        for window, assignment in assignments().items()
    }


def genesis() -> Genesis:
    """A Founder Economy genesis: no allocation, no accounts, and a zero fee."""
    return Genesis(
        network_id=4,
        supply_limit=5_699_395_010_000_000_000,
        total_supply=0,
        fixed_transfer_fee=0,
        initial_fee_pool=0,
        manifest_digest=bytes.fromhex(c.MANIFEST_DIGEST_HEX),
        verifier_key=VERIFIER_KEY,
        accounts=[],
    )


def populated_economy() -> dict[bytes, bytes]:
    """One entry of every kind, so the tree is exercised over all twelve."""
    from simulation.economy_transition_v3.settlement import assignment_entry

    from .genesis import initial_economy_entries
    from .state import (
        direct_decision_key,
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
    entries.update(registry().entries())
    # An activated seat owned by Alice and referred by Bob, with two managers and
    # no protection; and a purchased seat that has never been activated and has
    # switched protection on before it ever earns anything.
    entries[seat_key(0)] = seat_value(
        ALICE_IDENTITY,
        ALICE_FIRST_ADDRESS,
        BOB_IDENTITY,
        activation_height=7 * c.CYCLE_BLOCKS,
        minted_through_window=CURRENT_MARK,
        mint_requires_biometric=False,
        manager_count=2,
    )
    entries[seat_key(c.MAX_SEAT_ID)] = seat_value(
        ALICE_IDENTITY, ALICE_FIRST_ADDRESS, None, mint_requires_biometric=True
    )
    entries[seat_manager_key(0, ALICE_FIRST_ADDRESS)] = seat_manager_value()
    entries[seat_manager_key(0, MANAGER_ACCOUNT_ID)] = seat_manager_value()
    entries[referral_balance_key(BOB_IDENTITY)] = referral_balance_value(
        c.REFERRAL_LEG_ATOMIC * 3, c.REFERRAL_LEG_ATOMIC, CURRENT_MARK
    )
    entries[direct_decision_key(DECISION_ID)] = b""
    entries[
        typed_custody_key(c.VENTURE_ESCROW_BENEFICIARY, c.SINGLETON_BENEFICIARY_ID)
    ] = typed_custody_value(17_100_000_000)
    for assignment in assignments().values():
        key, value = assignment_entry(assignment)
        entries[key] = value
    return entries
