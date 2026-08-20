"""The eight value transitions: seven carried, and `mint_node` rebound.

**Kind 4 is the only transition in the whole contract that reads a surface
version seven moved.** A winner's collection gained one term — the cycle's pool
share — and that term lives inside the settlement's `collect`. Everything else
kind 4 does is unchanged, so this module rebinds one call and imports the four
helpers that surround it rather than restating a transition whose rejection order
is accepted.

The two transfers, both seat transactions, the referral mint, the verified-user
mint, and the refused direct issue are version six's function objects. A seat past
its own 731 cycles minting only reallocation and pool shares needs no rule here,
because kind 4 has never been gated on span in any version — version seven states
that as a requirement so a later reader does not add the gate as an optimisation.
"""

from __future__ import annotations

from dataclasses import replace

from simulation.economy_transition_v3.settlement import (
    last_assigned_window,
    walk_range,
)
from simulation.economy_transition_v6 import messages
from simulation.economy_transition_v6 import value_transitions as v6
from simulation.economy_transition_v6.envelope import Transaction
from simulation.economy_transition_v6.transitions import _charged
from simulation.economy_transition_v6.value_transitions import (
    activate_seat,
    direct_issue,
    mint_referral,
    mint_verified_user,
    native_transfer,
    purchase_seat,
    _require_confirmation,
    _require_destination,
    _require_seat,
)

from . import contract as c
from .execution import Outcome, Refused, SignatureOracle
from .ledger import Ledger
from .settlement import collect

__all__ = [
    "VERSION_SIX_HANDLERS",
    "activate_seat",
    "direct_issue",
    "dispatch",
    "mint_node",
    "mint_referral",
    "mint_verified_user",
    "native_transfer",
    "purchase_seat",
]


def dispatch(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    assert escrow is not None
    return _HANDLERS[transaction.kind](ledger, transaction, escrow, oracle)


def mint_node(
    ledger: Ledger, transaction: Transaction, escrow: bytes, oracle: SignatureOracle
) -> Outcome:
    """Kind 4. One button, everything, no quantity — now including the pool.

    The walk is version three's range and version seven's per-window read: an
    accrued bit still pays one base permission, and a winner bit now pays the
    reallocation share **and** the cycle's pool share. The Founder operator leg
    credits the named destination escrow, the four institutional legs credit
    typed custody, and the mark advances to the last assigned window whatever the
    walk found, which is what makes the accumulation cap forfeit rather than
    defer.

    Nothing here reads the recovery pool entry. A mint takes what the records it
    walks say the cycle absorbed, which is why the record commits to the absorbed
    amount at all: the pool's balance at a window is a function of every earlier
    cycle and deriving it would replay the whole assignment history inside a
    transition that must stay `O(cap)`.
    """
    body = transaction.body
    seat_id = body["seat_id"]
    seat = _require_seat(ledger, seat_id, escrow, require_activated=True)
    identity = seat.hub_identity_hash
    destination = _require_destination(ledger, body["destination_escrow_id"], identity)

    last_assigned = last_assigned_window(ledger.height)
    if walk_range(seat.minted_through_window, last_assigned) is None:
        raise Refused("NOTHING_TO_MINT")
    collection = collect(
        seat_id, seat.minted_through_window, last_assigned, ledger.assignments
    )
    total = collection.total_atomic
    _require_confirmation(
        ledger,
        destination,
        total,
        identity,
        messages.mint_message(
            ledger.chain_id,
            identity,
            c.MINT_NODE,
            seat_id,
            destination,
            transaction.valid_until_height,
        ),
        body["hub_signature"],
        oracle,
    )
    for channel, amount in collection.per_channel.items():
        if not ledger.fits_channel(channel, amount):
            raise Refused("CHANNEL_CAP")

    ledger.credit(destination, collection.operator_atomic)
    for beneficiary, amount in collection.custody_atomic.items():
        ledger.custody[beneficiary] = ledger.custody.get(beneficiary, 0) + amount
    for channel, amount in collection.per_channel.items():
        ledger.issue(channel, amount)
    ledger.seats[seat_id] = replace(seat, minted_through_window=last_assigned)
    return replace(_charged(ledger, escrow), issued_atomic=total)


_HANDLERS = {
    c.TRANSFER: native_transfer,
    c.TRANSFER_VERIFIED: native_transfer,
    c.PURCHASE_SEAT: purchase_seat,
    c.ACTIVATE_SEAT: activate_seat,
    c.MINT_NODE: mint_node,
    c.MINT_REFERRAL: mint_referral,
    c.MINT_VERIFIED_USER: mint_verified_user,
    c.DIRECT_ISSUE: direct_issue,
}

# Version six's own table, kept reachable so a test can require this one to be it
# for every kind except 4.
VERSION_SIX_HANDLERS = v6._HANDLERS
