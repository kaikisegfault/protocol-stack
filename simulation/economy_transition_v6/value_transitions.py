"""The eight version-six transitions that move or issue value.

The transfers, the two seat transactions, the three mints, and the refused
direct issue. The settlement they read — the accumulation cap, the
cycle-assignment record, and the bounded mint walk — is version three's and is
**imported rather than copied**, because a second implementation of one accepted
contract has nothing keeping the two equal.

**One rejection condition had to be derived, and it decides whether a mark can
move backwards.** Kinds 4 and 5 refuse with `NOTHING_TO_MINT` when the mark
"already equals the last assigned window". Taken literally that leaves a seat
activated in window `W` — whose mark is `W` while the last assigned window is
`W - 2` — outside the condition, so the mint would succeed, collect nothing, and
set the mark to `W - 2`. A mark that decreases breaks the exactness argument the
whole accumulation cap rests on, so the condition is the empty walk range:
`mark >= last_assigned`, of which "already equal" is one case and "no window
assigned yet" is the other. ADR 0045 records it.
"""

from __future__ import annotations

from dataclasses import replace

from simulation.economy_transition_v3.settlement import (
    collect,
    last_assigned_window,
    walk_range,
)

from . import contract as c
from . import messages, verified_user
from .envelope import Transaction
from .execution import Outcome, Refused, SignatureOracle, require_zero_confirmation
from .ledger import Ledger, ReferralBalance, Seat
from .transitions import _charged, activation_mark, confirmation_required

ZERO_CONFIRMATION = bytes(c.HUB_SIGNATURE_BYTES)


def dispatch(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    assert escrow is not None
    return _HANDLERS[transaction.kind](ledger, transaction, escrow, oracle)


def native_transfer(
    ledger: Ledger, transaction: Transaction, escrow: bytes, oracle: SignatureOracle
) -> Outcome:
    """Kinds 1 and 19. **It never creates an account.**

    That is the one execution change to the accepted version-one bytes in five
    contract revisions: a recipient with no escrow entry is refused rather than
    created, which withdraws the last way an account could come into existence
    with no identity behind it.

    A self-transfer needs no special case here. Version one gives it one because
    it must not credit an account it is about to debit; the escrow's amount
    cancels when the same key is debited and credited, and the envelope check
    already required the balance to cover `amount + fee`.
    """
    body = transaction.body
    amount = body["amount_atomic"]
    if amount == 0:
        raise Refused("ZERO_AMOUNT")
    recipient = body["recipient_escrow_id"]
    if recipient not in ledger.registry.escrows:
        raise Refused("RECIPIENT_NOT_REGISTERED")
    identity = ledger.registry.escrows[escrow].owner_hub_identity
    if transaction.kind == c.TRANSFER:
        if confirmation_required(ledger, escrow, amount):
            raise Refused("BIOMETRIC_REQUIRED")
    else:
        message = messages.transfer_confirm_message(
            ledger.chain_id,
            identity,
            escrow,
            recipient,
            amount,
            transaction.valid_until_height,
        )
        _require_hub_signature(ledger, identity, message, body["hub_signature"], oracle)
    ledger.debit(escrow, amount)
    ledger.credit(recipient, amount)
    return _charged(ledger, escrow)


def purchase_seat(
    ledger: Ledger, transaction: Transaction, escrow: bytes, oracle: SignatureOracle
) -> Outcome:
    """Kind 2. The purchaser is the identity that signed, and no account is named.

    Self-referral is refused across every escrow a person holds, because the
    comparison is between two identities and one person has exactly one. The
    referrer is named by escrow — which is the shareable thing — and recorded as
    an identity, so referral earnings follow the person.
    """
    body = transaction.body
    seat_id = body["seat_id"]
    if not 0 <= seat_id <= c.MAX_SEAT_ID:
        raise Refused("CYCLE_RANGE")
    if seat_id in ledger.seats:
        raise Refused("REPLAY")
    identity = ledger.registry.escrows[escrow].owner_hub_identity
    referrer_identity: bytes | None = None
    if body["has_referrer"]:
        referrer_escrow = body["referrer_escrow_id"]
        if referrer_escrow not in ledger.registry.escrows:
            raise Refused("RECIPIENT_NOT_REGISTERED")
        referrer_identity = ledger.registry.escrows[referrer_escrow].owner_hub_identity
        if referrer_identity == identity:
            raise Refused("INVALID_REFERRER")
    entry = ledger.registry.identities[identity]
    if entry.seat_count >= c.MAX_SEATS_PER_IDENTITY:
        raise Refused("SEAT_LIMIT")
    message = messages.purchase_message(
        ledger.chain_id, identity, seat_id, transaction.valid_until_height
    )
    _require_hub_signature(ledger, identity, message, body["hub_signature"], oracle)

    ledger.seats[seat_id] = Seat(
        hub_identity_hash=identity, referrer_hub_identity=referrer_identity
    )
    ledger.registry.identities[identity] = replace(
        entry, seat_count=entry.seat_count + 1
    )
    return _charged(ledger, escrow)


def activate_seat(
    ledger: Ledger, transaction: Transaction, escrow: bytes, oracle: SignatureOracle
) -> Outcome:
    """Kind 3. One-time and permanent, and it issues nothing."""
    body = transaction.body
    seat = _require_seat(ledger, body["seat_id"], escrow)
    if seat.is_activated:
        raise Refused("REPLAY")
    message = messages.activation_message(
        ledger.chain_id,
        seat.hub_identity_hash,
        body["seat_id"],
        transaction.valid_until_height,
    )
    _require_hub_signature(
        ledger, seat.hub_identity_hash, message, body["hub_signature"], oracle
    )
    ledger.seats[body["seat_id"]] = replace(
        seat,
        is_activated=True,
        activation_height=ledger.height,
        minted_through_window=activation_mark(ledger.height),
    )
    return _charged(ledger, escrow)


def mint_node(
    ledger: Ledger, transaction: Transaction, escrow: bytes, oracle: SignatureOracle
) -> Outcome:
    """Kind 4. One button, everything, no quantity — and the walk is bounded.

    The Founder operator leg credits the named destination escrow; the four
    institutional legs credit typed custody. The mark then advances to the last
    assigned window whatever the walk found, which is what makes the
    accumulation cap forfeit rather than defer.
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


def mint_referral(
    ledger: Ledger, transaction: Transaction, escrow: bytes, oracle: SignatureOracle
) -> Outcome:
    """Kind 5. Any escrow of the person may receive it: the balance is the
    identity's, so a referrer who changes escrows keeps everything accrued."""
    body = transaction.body
    identity = ledger.registry.escrows[escrow].owner_hub_identity
    destination = _require_destination(ledger, body["destination_escrow_id"], identity)
    entry = ledger.referral.get(identity)
    if entry is None:
        raise Refused("NOTHING_TO_MINT")
    last_assigned = last_assigned_window(ledger.height)
    settled = entry.accrued_atomic == entry.minted_atomic
    if settled and (
        last_assigned is None or entry.collected_through_window >= last_assigned
    ):
        raise Refused("NOTHING_TO_MINT")
    assert last_assigned is not None
    amount = entry.accrued_atomic - entry.minted_atomic
    _require_confirmation(
        ledger,
        destination,
        amount,
        identity,
        messages.mint_message(
            ledger.chain_id,
            identity,
            c.MINT_REFERRAL,
            0,
            destination,
            transaction.valid_until_height,
        ),
        body["hub_signature"],
        oracle,
    )
    if not ledger.fits_channel(c.REFERRAL_CHANNEL, amount):
        raise Refused("CHANNEL_CAP")

    ledger.credit(destination, amount)
    ledger.referral[identity] = ReferralBalance(
        accrued_atomic=entry.accrued_atomic,
        minted_atomic=entry.accrued_atomic,
        collected_through_window=last_assigned,
    )
    ledger.issue(c.REFERRAL_CHANNEL, amount)
    return replace(_charged(ledger, escrow), issued_atomic=amount)


def mint_verified_user(
    ledger: Ledger, transaction: Transaction, escrow: bytes, oracle: SignatureOracle
) -> Outcome:
    """Kind 18. The walk is arithmetic rather than iteration, so it is `O(1)`.

    Every window in the period pays the same amount unconditionally, which is
    why no per-window record exists for a million identities and why the cap is
    applied here rather than at assignment.
    """
    body = transaction.body
    identity = ledger.registry.escrows[escrow].owner_hub_identity
    destination = _require_destination(ledger, body["destination_escrow_id"], identity)
    enrollment = ledger.registry.enrollments.get(identity)
    if enrollment is None:
        raise Refused("NOT_ENROLLED")
    collection = verified_user.collect(enrollment, ledger.height)
    if collection.count == 0:
        raise Refused("NOTHING_TO_MINT")
    _require_confirmation(
        ledger,
        destination,
        collection.amount_atomic,
        identity,
        messages.mint_message(
            ledger.chain_id,
            identity,
            c.MINT_VERIFIED_USER,
            0,
            destination,
            transaction.valid_until_height,
        ),
        body["hub_signature"],
        oracle,
    )
    if not ledger.fits_channel(c.VERIFIED_USER_CHANNEL, collection.amount_atomic):
        raise Refused("CHANNEL_CAP")

    ledger.credit(destination, collection.amount_atomic)
    ledger.registry.enrollments[identity] = verified_user.applied(enrollment, collection)
    ledger.issue(c.VERIFIED_USER_CHANNEL, collection.amount_atomic)
    return replace(_charged(ledger, escrow), issued_atomic=collection.amount_atomic)


def direct_issue(
    ledger: Ledger, transaction: Transaction, escrow: bytes, oracle: SignatureOracle
) -> Outcome:
    """Kind 6. Refused for every acting key while the predicate is undecided.

    Conditions 2 through 7 are unreachable in a conforming implementation
    because this one refuses first, which is why the channel, amount, decision,
    beneficiary, and cap conditions are specified and never exercised.
    """
    del ledger, transaction, escrow, oracle
    raise Refused("UNAUTHORIZED")


def _require_seat(
    ledger: Ledger, seat_id: int, escrow: bytes, require_activated: bool = False
) -> Seat:
    if not 0 <= seat_id <= c.MAX_SEAT_ID:
        raise Refused("CYCLE_RANGE")
    seat = ledger.seats.get(seat_id)
    if seat is None:
        raise Refused("SEAT_NOT_PURCHASED")
    if require_activated and not seat.is_activated:
        raise Refused("SEAT_NOT_ACTIVATED")
    if seat.hub_identity_hash != ledger.registry.escrows[escrow].owner_hub_identity:
        raise Refused("UNAUTHORIZED")
    return seat


def _require_destination(ledger: Ledger, destination: bytes, identity: bytes) -> bytes:
    """A mint names its destination and the chain checks it belongs to the
    minting identity, because a person holds many escrows and none is
    privileged."""
    entry = ledger.registry.escrows.get(destination)
    if entry is None:
        raise Refused("ESCROW_NOT_FOUND")
    if entry.owner_hub_identity != identity:
        raise Refused("ESCROW_NOT_OWNED")
    return destination


def _require_confirmation(
    ledger: Ledger,
    destination: bytes,
    amount: int,
    identity: bytes,
    message: bytes,
    field: bytes,
    oracle: SignatureOracle,
) -> None:
    """The destination's posture applied to the total the mint would credit.

    The total is computed before any write, so a mint that needs a confirmation
    and carries 64 zero octets is refused with nothing written.
    """
    if confirmation_required(ledger, destination, amount):
        if field == ZERO_CONFIRMATION:
            raise Refused("BIOMETRIC_REQUIRED")
        _require_hub_signature(ledger, identity, message, field, oracle)
        return
    require_zero_confirmation(field)


def _require_hub_signature(
    ledger: Ledger,
    identity: bytes,
    message: bytes,
    signature: bytes,
    oracle: SignatureOracle,
) -> None:
    """Every HUB message binds the identity, so a signature made by one person's
    key cannot be presented as another's even where the other fields coincide."""
    key = ledger.registry.identities[identity].hub_public_key
    if not oracle.verify(key, message, signature):
        raise Refused("UNAUTHORIZED")


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
