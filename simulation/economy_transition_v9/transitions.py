"""Version nine's dispatch table: sixteen carried handlers and one new one.

Version eight's table is sixteen kinds, fourteen of them delegated to version
seven's own dispatch. Version nine does not touch it: `dispatch` delegates every
carried kind to `simulation.economy_transition_v8.transitions.dispatch` and adds
exactly one row, so the table a reader audits is one delegation and one handler
rather than a seventeen-row copy.

**Kind 22 is kind 4 with a different balance.** The body, the signature scheme,
the authority — any escrow the seat's identity owns may act — the destination
rule, the posture confirmation and the fixed fee are all kind 4's, and what
differs is which balance is collected and which channel it leaves. That is why
version nine adds no result code: every refusal kind 22 can produce already has
a number.

`tests/simulation/economy_transition_v9_execution_test.py` requires the carried
delegation to be version eight's own function object, so a seventeen-row copy
that appeared here later would fail a test rather than pass silently.
"""

from __future__ import annotations

from simulation.economy_transition_v6.execution import Refused
from simulation.economy_transition_v6.transitions import _charged
from simulation.economy_transition_v6.value_transitions import (
    _require_confirmation,
    _require_destination,
)
from simulation.economy_transition_v8 import transitions as v8

from . import contract as c
from .envelope import Transaction, mint_message
from .execution import Outcome, SignatureOracle
from .ledger import Ledger

__all__ = [
    "VERSION_EIGHT_DISPATCH",
    "dispatch",
    "mint_monthly_pool",
]

# Version eight's own dispatch, kept reachable so a test can require this
# module's carried path to be it rather than an equal-looking copy.
VERSION_EIGHT_DISPATCH = v8.dispatch


def dispatch(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    if transaction.kind == c.MINT_POOL:
        return mint_monthly_pool(ledger, transaction, escrow, oracle)
    return VERSION_EIGHT_DISPATCH(ledger, transaction, escrow, oracle)


def mint_monthly_pool(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    """Kind 22. Nine ordered conditions, one balance emptied, and the fixed fee.

    **One button, everything, no quantity.** The whole outstanding difference is
    taken, which is the founder-directed mint shape kinds 4, 5 and 18 all
    implement and the reason a claim is a running balance rather than a per-month
    award: a mint that can take a chosen amount must record what it took.
    """
    assert escrow is not None
    body = transaction.body
    seat_id = body["seat_id"]

    if seat_id > c.MAX_SEAT_ID:
        raise Refused("CYCLE_RANGE")
    seat = ledger.seats.get(seat_id)
    if seat is None:
        raise Refused("SEAT_NOT_PURCHASED")
    if not seat.is_activated:
        # Reachable, and kept even though condition 7 would catch it: a refusal
        # that says NOTHING_TO_MINT about a seat nobody ever switched on is true
        # and useless.
        raise Refused("SEAT_NOT_ACTIVATED")

    identity = ledger.registry.escrows[escrow].owner_hub_identity
    if seat.hub_identity_hash != identity:
        raise Refused("UNAUTHORIZED")

    destination = _require_destination(ledger, body["destination_escrow_id"], identity)

    accrued, minted = ledger.claim(seat_id)
    if accrued == minted:
        raise Refused("NOTHING_TO_MINT")
    amount = accrued - minted

    _require_confirmation(
        ledger,
        destination,
        amount,
        identity,
        mint_message(
            ledger.chain_id,
            identity,
            c.MINT_POOL,
            seat_id,
            destination,
            transaction.valid_until_height,
        ),
        body["hub_signature"],
        oracle,
    )

    # Structurally unreachable: the units were counted into the referral
    # channel's outstanding when they accrued, and this moves them to issued
    # without creating any, so the channel identity forbids the overflow. It is
    # checked because an invariant that cannot fail is cheaper to check than to
    # argue about.
    if not ledger.fits_channel(c.REFERRAL_CHANNEL, amount):
        raise Refused("CHANNEL_CAP")

    ledger.credit(destination, amount)
    ledger.claims[seat_id] = (accrued, accrued)
    ledger.pool_minted += amount
    ledger.issue(c.REFERRAL_CHANNEL, amount)
    charged = _charged(ledger, escrow)
    return Outcome(
        result=charged.result, fee_charged=charged.fee_charged, issued_atomic=amount
    )
