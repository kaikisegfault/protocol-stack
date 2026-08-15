"""The checked-in fixture the normative vectors are taken over.

The transfer inputs are the accepted `protocol-primitives-v1` transfer's inputs,
restated here so the verifier can require this model's encoder to reproduce that
specification's recorded unsigned bytes, signed bytes, and transaction ID. **The
recipient is a registered escrow in the fixture and an unregistered value in the
refusal case**, which is the pair of vectors the founder answer of 2026-08-15
produced: the same bytes accepted under version one and refused under version
six.

**The cycle population is version three's, unchanged.** The settlement is
imported rather than reimplemented, so the assignment record version six writes
for the same seats must be byte-identical to the one version three recorded. A
fixture that differed would hide exactly the drift the import is there to
prevent.

The registry fixture is built around the cases version five could not have: a
person holding three escrows, one of them emptied and deleted; a person who has
lost every signer and recovers by assigning a new one; an escrow with no signer
at all; postures at each end of the relaxation predicate; and a verified user
who has neglected their permission long enough to forfeit.
"""

from __future__ import annotations

from simulation.economy_transition_v3 import scenario as v3
from simulation.economy_transition_v3.settlement import SeatCycle

from . import contract as c
from .envelope import Transaction
from .genesis import Genesis
from .identity import Posture, Registry, escrow_id, signer_id

CHAIN_ID = bytes(range(32))

# The accepted version-one transfer's inputs. Under version six this key is a
# signer key rather than an account key, which is the whole narrowing: the
# derivation is unchanged and what it names moved.
SENDER_PUBLIC_KEY = bytes.fromhex(
    "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
)
UNREGISTERED_RECIPIENT = bytes(range(0x20, 0x40))

TRANSFER_SIGNATURE = bytes.fromhex(
    "4678857e9c2da9acd3796819bd151958c6497122d962b0600ba51914d0b10d3a"
    "b922b9bba415e4fdc7d120227548a7c0ec87fc66315d01b8f64165944ee82b06"
)

# Stand-ins. The model never verifies a signature, because verification is
# Ed25519 and this model implements no cryptographic primitive; the vectors fix
# the six message constructions, which is the consensus-visible part.
HUB_SIGNATURE = bytes.fromhex("44" * 64)
VERIFIER_SIGNATURE = bytes.fromhex("dd" * 64)
VERIFIER_KEY = bytes.fromhex("55" * 32)

# Three people, and the third is the one version five could not serve.
ALICE_IDENTITY = bytes.fromhex("a1" * 32)
ALICE_KEY = bytes.fromhex("a2" * 32)
ALICE_SIGNER_KEY = bytes.fromhex("a3" * 32)
ALICE_SECOND_SIGNER_KEY = bytes.fromhex("a4" * 32)

BOB_IDENTITY = bytes.fromhex("b1" * 32)
BOB_KEY = bytes.fromhex("b2" * 32)
BOB_SIGNER_KEY = bytes.fromhex("b3" * 32)

# Maria has lost every signer she held and recovers with her face alone.
MARIA_IDENTITY = bytes.fromhex("c1" * 32)
MARIA_KEY = bytes.fromhex("c2" * 32)
MARIA_LOST_SIGNER_KEY = bytes.fromhex("c3" * 32)
MARIA_NEW_SIGNER_KEY = bytes.fromhex("c4" * 32)

DECISION_ID = bytes.fromhex("11" * 32)
AUTHORIZATION = bytes.fromhex("33" * 32)

FEE_LIMIT = 1_000
VALID_UNTIL_HEIGHT = 42
REGISTRATION_HEIGHT = 5 * c.CYCLE_BLOCKS

ALICE_FIRST_ESCROW = escrow_id(ALICE_IDENTITY, 0)
ALICE_SECOND_ESCROW = escrow_id(ALICE_IDENTITY, 1)
ALICE_THIRD_ESCROW = escrow_id(ALICE_IDENTITY, 2)
BOB_ESCROW = escrow_id(BOB_IDENTITY, 0)
MARIA_ESCROW = escrow_id(MARIA_IDENTITY, 0)

# One relaxation of each kind, and one tightening, so the predicate's three
# disjuncts are each exercised alone.
STRICT_POSTURE = Posture()
RELAXED_OFF = Posture(requires_confirmation=False)
RELAXED_MINIMUM = Posture(min_amount_atomic=100_000_000)
RELAXED_WINDOW = Posture(exempt_slot_mask=0b1)
MIXED_POSTURE = Posture(min_amount_atomic=100_000_000, exempt_slot_mask=0)


def _envelope(
    kind: int, nonce: int, body: dict, authority: bytes = SENDER_PUBLIC_KEY
) -> Transaction:
    scheme = c.KIND_SCHEME[kind]
    return Transaction(
        kind=kind,
        scheme=scheme,
        chain_id=CHAIN_ID,
        authority_public_key=authority,
        nonce=nonce,
        body=body,
        fee_limit=0 if kind == c.HUB_REGISTER else FEE_LIMIT,
        valid_until_height=VALID_UNTIL_HEIGHT,
    )


def accepted_transfer() -> Transaction:
    """The accepted version-one transfer, expressed as a kind-1 version-six one.

    Its bytes are the accepted ones. Its recipient is deliberately the value the
    accepted vectors record, which is not a registered escrow in this fixture —
    so the same transaction reproduces the accepted bytes and is refused with
    `RECIPIENT_NOT_REGISTERED`, which is exactly the boundary this version moves.
    """
    return _envelope(
        c.TRANSFER,
        1,
        {"recipient_escrow_id": UNREGISTERED_RECIPIENT, "amount_atomic": 1_000_000},
    )


def transactions() -> dict[str, Transaction]:
    """One transaction per kind, plus the boundary instances that matter."""
    return {
        "transfer": accepted_transfer(),
        "transfer_to_registered": _envelope(
            c.TRANSFER,
            2,
            {"recipient_escrow_id": BOB_ESCROW, "amount_atomic": 1_000_000},
        ),
        "transfer_verified": _envelope(
            c.TRANSFER_VERIFIED,
            3,
            {
                "recipient_escrow_id": BOB_ESCROW,
                "amount_atomic": 1_000_000,
                "hub_signature": HUB_SIGNATURE,
            },
        ),
        "purchase_referred_seat": _envelope(
            c.PURCHASE_SEAT,
            4,
            {
                "seat_id": 0,
                "has_referrer": True,
                "referrer_escrow_id": BOB_ESCROW,
                "hub_signature": HUB_SIGNATURE,
            },
        ),
        "purchase_unreferred_last_seat": _envelope(
            c.PURCHASE_SEAT,
            5,
            {
                "seat_id": c.MAX_SEAT_ID,
                "has_referrer": False,
                "referrer_escrow_id": bytes(32),
                "hub_signature": HUB_SIGNATURE,
            },
        ),
        "activate_seat": _envelope(
            c.ACTIVATE_SEAT, 6, {"seat_id": 0, "hub_signature": HUB_SIGNATURE}
        ),
        "mint_node": _envelope(
            c.MINT_NODE,
            7,
            {
                "seat_id": 0,
                "destination_escrow_id": ALICE_SECOND_ESCROW,
                "hub_signature": bytes(64),
            },
        ),
        "mint_node_confirmed": _envelope(
            c.MINT_NODE,
            8,
            {
                "seat_id": 0,
                "destination_escrow_id": ALICE_FIRST_ESCROW,
                "hub_signature": HUB_SIGNATURE,
            },
        ),
        "mint_referral": _envelope(
            c.MINT_REFERRAL,
            9,
            {"destination_escrow_id": BOB_ESCROW, "hub_signature": bytes(64)},
        ),
        "mint_verified_user": _envelope(
            c.MINT_VERIFIED_USER,
            10,
            {"destination_escrow_id": BOB_ESCROW, "hub_signature": bytes(64)},
        ),
        "direct_issue": _envelope(
            c.DIRECT_ISSUE,
            11,
            {
                "channel_id": c.DIRECT_ISSUE_CHANNELS[0],
                "decision_id": DECISION_ID,
                "beneficiary_escrow_id": BOB_ESCROW,
                "amount_atomic": 100_000_000,
                "authorization": AUTHORIZATION,
            },
        ),
        "hub_register": _envelope(
            c.HUB_REGISTER,
            0,
            {
                "hub_identity_hash": ALICE_IDENTITY,
                "first_signer_public_key": ALICE_SIGNER_KEY,
                "verifier_signature": VERIFIER_SIGNATURE,
            },
            authority=ALICE_KEY,
        ),
        "escrow_create": _envelope(
            c.ESCROW_CREATE,
            12,
            {
                "hub_identity_hash": ALICE_IDENTITY,
                "fee_escrow_id": ALICE_FIRST_ESCROW,
            },
            authority=ALICE_KEY,
        ),
        "escrow_delete": _envelope(
            c.ESCROW_DELETE,
            13,
            {
                "hub_identity_hash": ALICE_IDENTITY,
                "target_escrow_id": ALICE_THIRD_ESCROW,
                "fee_escrow_id": ALICE_FIRST_ESCROW,
            },
            authority=ALICE_KEY,
        ),
        "signer_add_recovery": _envelope(
            c.SIGNER_ADD,
            14,
            {
                "hub_identity_hash": MARIA_IDENTITY,
                "escrow_id": MARIA_ESCROW,
                "signer_public_key": MARIA_NEW_SIGNER_KEY,
            },
            authority=MARIA_KEY,
        ),
        "signer_revoke": _envelope(
            c.SIGNER_REVOKE,
            15,
            {
                "hub_identity_hash": MARIA_IDENTITY,
                "escrow_id": MARIA_ESCROW,
                "signer_id": signer_id(MARIA_LOST_SIGNER_KEY),
            },
            authority=MARIA_KEY,
        ),
        "posture_tighten": _envelope(
            c.SET_SECURITY_POSTURE,
            16,
            {
                "requires_confirmation": True,
                "min_amount_atomic": 0,
                "exempt_slot_mask": 0,
                "hub_signature": bytes(64),
            },
        ),
        "posture_relax": _envelope(
            c.SET_SECURITY_POSTURE,
            17,
            {
                "requires_confirmation": False,
                "min_amount_atomic": 0,
                "exempt_slot_mask": 0,
                "hub_signature": HUB_SIGNATURE,
            },
        ),
    }


def registry() -> Registry:
    """Alice with three escrows and two signers, Bob with one, Maria recovering.

    Alice's third escrow is created and deleted, which is what shows a deleted
    identifier is never reissued: her `next_escrow_index` stays at 3 while her
    live count falls to 2. Her second escrow has no signer at all, which is a
    reachable state because kind 13 creates an escrow and kind 15 assigns one.

    Maria's original signer is revoked and a new one assigned, both authorized by
    her identity alone. That is the recovery path, and it is the ordinary pair of
    transactions rather than anything special.
    """
    built = Registry()
    built.register(ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY, REGISTRATION_HEIGHT)
    built.create_escrow(ALICE_IDENTITY)
    built.create_escrow(ALICE_IDENTITY)
    built.delete_escrow(ALICE_IDENTITY, ALICE_THIRD_ESCROW)
    built.add_signer(ALICE_FIRST_ESCROW, ALICE_SECOND_SIGNER_KEY)

    built.register(BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY, REGISTRATION_HEIGHT + 1)

    built.register(
        MARIA_IDENTITY, MARIA_KEY, MARIA_LOST_SIGNER_KEY, REGISTRATION_HEIGHT + 2
    )
    built.add_signer(MARIA_ESCROW, MARIA_NEW_SIGNER_KEY)
    built.revoke_signer(MARIA_ESCROW, signer_id(MARIA_LOST_SIGNER_KEY))

    built.set_posture(ALICE_SECOND_ESCROW, RELAXED_MINIMUM)
    built.claim_seat(ALICE_IDENTITY)
    return built


# The settlement fixture is version three's, unchanged, so the assignment record
# must come out byte-identical. Only the referrer key is a HUB identity, which
# needs no new code because version three's referrer key is opaque bytes.
CYCLE_WINDOW = v3.CYCLE_WINDOW
OUTAGE_WINDOW = v3.OUTAGE_WINDOW
ASSIGNMENT_HEIGHT = v3.ASSIGNMENT_HEIGHT
CURRENT_MARK = v3.CURRENT_MARK
CAPPED_MARK = v3.CAPPED_MARK

REFERRER_IDENTITY = BOB_IDENTITY
CAPPED_REFERRER_IDENTITY = MARIA_IDENTITY

_IDENTITY_BY_V3_KEY: dict[bytes | None, bytes | None] = {
    v3.REFERRER_ACCOUNT_ID: REFERRER_IDENTITY,
    v3.CAPPED_REFERRER_ACCOUNT_ID: CAPPED_REFERRER_IDENTITY,
    None: None,
}


def _rekey(seats: list[SeatCycle]) -> list[SeatCycle]:
    return [
        SeatCycle(
            seat.seat_id,
            seat.uptime_seconds,
            seat.in_span,
            seat.minted_through_window,
            _IDENTITY_BY_V3_KEY[seat.referrer_account_id],
        )
        for seat in seats
    ]


def cycle_seats() -> list[SeatCycle]:
    return _rekey(v3.cycle_seats())


def outage_seats() -> list[SeatCycle]:
    return _rekey(v3.outage_seats())


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
        network_id=6,
        supply_limit=5_699_395_010_000_000_000,
        fixed_transfer_fee=0,
        manifest_digest=bytes.fromhex(c.MANIFEST_DIGEST_HEX),
        verifier_key=VERIFIER_KEY,
    )


def populated_economy() -> dict[bytes, bytes]:
    """One entry of every assigned kind, so the tree is exercised over all of them."""
    from simulation.economy_transition_v3.settlement import assignment_entry

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
    entries.update(registry().entries())
    # An activated seat owned by Alice and referred by Bob, and a purchased seat
    # that has never been activated. Neither carries an address of any kind.
    entries[seat_key(0)] = seat_value(
        ALICE_IDENTITY,
        BOB_IDENTITY,
        activation_height=7 * c.CYCLE_BLOCKS,
        minted_through_window=CURRENT_MARK,
    )
    entries[seat_key(c.MAX_SEAT_ID)] = seat_value(ALICE_IDENTITY, None)
    entries[referral_balance_key(BOB_IDENTITY)] = referral_balance_value(
        c.REFERRAL_LEG_ATOMIC * 3, c.REFERRAL_LEG_ATOMIC, CURRENT_MARK
    )
    entries[direct_decision_key(DECISION_ID)] = b""
    entries[typed_custody_key(1, c.SINGLETON_BENEFICIARY_ID)] = typed_custody_value(
        17_100_000_000
    )
    for assignment in assignments().values():
        key, value = assignment_entry(assignment)
        entries[key] = value
    return entries


def accounts() -> list[tuple[bytes, int, int]]:
    """The version-one account map. Every key is an escrow, which is the point."""
    return registry().account_list()
