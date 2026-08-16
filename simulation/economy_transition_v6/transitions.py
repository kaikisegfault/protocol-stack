"""The fourteen version-six transitions, in their specified rejection orders.

Dispatch is on the kind byte, never on a body length: five kinds share a
96-octet body, which is the case version two anticipated when it stated the
rule and version three first exercised.

**Six kinds require no signer at all, and each is a recovery path.** Register,
create an escrow, delete one, assign a signer, revoke a signer — exactly the
transactions a person must be able to make holding no key. The HUB signature is
the authority and a named escrow pays, so nothing here needs a helper, a third
party, or an external funding step.

Each transition validates completely before it writes, so a refusal leaves the
state untouched without a rollback. The trace requires that: every failing
transaction must leave the state root exactly as it found it.
"""

from __future__ import annotations

from dataclasses import replace

from simulation.cycle_boundary import grid

from . import contract as c
from . import messages
from .envelope import Transaction
from .execution import Outcome, Refused, SignatureOracle, require_zero_confirmation
from .identity import Escrow, Identity, Posture, escrow_id, relaxes, signer_id, unchanged
from .ledger import Ledger
from .verified_user import enroll


def dispatch(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    from . import value_transitions

    handler = _HANDLERS.get(transaction.kind)
    if handler is not None:
        return handler(ledger, transaction, escrow, oracle)
    return value_transitions.dispatch(ledger, transaction, escrow, oracle)


def hub_register(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    """Kind 10. One transaction that creates a whole participant, atomically.

    It is fee-exempt, and the exemption is deliberate rather than the smaller of
    two equal options: the entry airdrop is bounded at 1,000,000 identities, so
    a credit-then-charge rule would refuse user 1,000,001 with
    `INSUFFICIENT_BALANCE` and close the ecosystem at exactly the point the
    bootstrap problem was supposed to stop recurring. Exemption works forever,
    and its anti-abuse bound is non-monetary and already present, because only
    the ecosystem verifier can sign a registration.
    """
    del escrow
    if transaction.valid_until_height < ledger.height:
        raise Refused("EXPIRED")
    body = transaction.body
    identity_hash = body["hub_identity_hash"]
    if identity_hash in ledger.registry.identities:
        raise Refused("REPLAY")
    first_signer = signer_id(body["first_signer_public_key"])
    if first_signer in ledger.registry.signers:
        raise Refused("REPLAY")
    message = messages.registration_message(
        ledger.chain_id,
        identity_hash,
        transaction.authority_public_key,
        body["first_signer_public_key"],
        transaction.valid_until_height,
    )
    if not oracle.verify(ledger.verifier_key, message, body["verifier_signature"]):
        raise Refused("UNAUTHORIZED")

    enrolling = ledger.registry.enrolled_count < c.VERIFIED_USER_POPULATION
    airdrop = c.VERIFIED_USER_DAILY_ATOMIC if enrolling else 0
    if airdrop and not ledger.fits_channel(c.VERIFIED_USER_CHANNEL, airdrop):
        raise Refused("CHANNEL_CAP")

    first_escrow = escrow_id(identity_hash, 0)
    ledger.registry.identities[identity_hash] = Identity(
        hub_public_key=transaction.authority_public_key,
        registered_at_height=ledger.height,
        next_escrow_index=1,
        escrow_count=1,
        seat_count=0,
    )
    ledger.registry.escrows[first_escrow] = Escrow(
        owner_hub_identity=identity_hash, posture=Posture(), signer_count=1
    )
    ledger.registry.signers[first_signer] = first_escrow
    ledger.registry.accounts[first_escrow] = (0, 0)
    if enrolling:
        ledger.registry.enrollments[identity_hash] = enroll(ledger.height)
        ledger.registry.enrolled_count += 1
        ledger.issue(c.VERIFIED_USER_CHANNEL, airdrop)
        ledger.credit(first_escrow, airdrop)
    return Outcome(result="SUCCESS", issued_atomic=airdrop, fee_charged=0)


def escrow_create(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    """Kind 13. The identity is the admin, so no signer is involved."""
    del oracle
    assert escrow is not None
    identity_hash = transaction.body["hub_identity_hash"]
    identity = ledger.registry.identities[identity_hash]
    created = escrow_id(identity_hash, identity.next_escrow_index)
    ledger.registry.escrows[created] = Escrow(
        owner_hub_identity=identity_hash, posture=Posture(), signer_count=0
    )
    ledger.registry.accounts[created] = (0, 0)
    ledger.registry.identities[identity_hash] = replace(
        identity,
        next_escrow_index=identity.next_escrow_index + 1,
        escrow_count=identity.escrow_count + 1,
    )
    return _charged(ledger, escrow)


def escrow_delete(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    """Kind 14. A deleted escrow must be empty, and its index is never reused.

    The fee escrow is named separately because an escrow with a zero balance
    cannot pay for its own deletion, and a target equal to the fee escrow is
    therefore refused rather than special-cased.
    """
    del oracle
    assert escrow is not None
    identity_hash = transaction.body["hub_identity_hash"]
    target = transaction.body["target_escrow_id"]
    ledger.registry.require_owned(target, identity_hash)
    if target == escrow:
        raise Refused("ESCROW_NOT_EMPTY")
    if ledger.balance(target) != 0:
        raise Refused("ESCROW_NOT_EMPTY")

    for identifier in [
        key for key, value in ledger.registry.signers.items() if value == target
    ]:
        del ledger.registry.signers[identifier]
    del ledger.registry.escrows[target]
    del ledger.registry.accounts[target]
    identity = ledger.registry.identities[identity_hash]
    ledger.registry.identities[identity_hash] = replace(
        identity, escrow_count=identity.escrow_count - 1
    )
    return _charged(ledger, escrow)


def signer_add(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    """Kind 15, and the recovery path — the ordinary transaction, not a special one.

    A person who has lost every signer proves their identity with their HUB key,
    names an escrow that already holds value, and assigns a fresh signer to it.
    The escrow they name pays the fee out of value it already holds, which is
    what dissolves the funding problem version five could not solve.
    """
    del oracle
    assert escrow is not None
    identifier = signer_id(transaction.body["signer_public_key"])
    if identifier in ledger.registry.signers:
        raise Refused("REPLAY")
    entry = ledger.registry.escrows[escrow]
    if entry.signer_count >= c.MAX_SIGNERS_PER_ESCROW:
        raise Refused("SIGNER_LIMIT")
    ledger.registry.signers[identifier] = escrow
    ledger.registry.escrows[escrow] = replace(entry, signer_count=entry.signer_count + 1)
    return _charged(ledger, escrow)


def signer_revoke(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    """Kind 16. Immediate and total: a revoked key authorizes nothing from here."""
    del oracle
    assert escrow is not None
    identifier = transaction.body["signer_id"]
    assigned = ledger.registry.signers.get(identifier)
    if assigned is None:
        raise Refused("SIGNER_NOT_FOUND")
    if assigned != escrow:
        raise Refused("UNAUTHORIZED")
    del ledger.registry.signers[identifier]
    entry = ledger.registry.escrows[escrow]
    ledger.registry.escrows[escrow] = replace(entry, signer_count=entry.signer_count - 1)
    return _charged(ledger, escrow)


def set_security_posture(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    """Kind 17. The direction of the change decides what must have authorized it.

    A change that tightens one field and relaxes another counts as a relaxation,
    because each disjunct is one way to shrink the set of operations needing a
    proof and the failure that matters is a stolen key weakening a protection.
    """
    assert escrow is not None
    body = transaction.body
    proposed = Posture(
        requires_confirmation=body["requires_confirmation"],
        min_amount_atomic=body["min_amount_atomic"],
        exempt_slot_mask=body["exempt_slot_mask"],
    )
    entry = ledger.registry.escrows[escrow]
    if unchanged(entry.posture, proposed):
        raise Refused("REPLAY")
    if relaxes(entry.posture, proposed):
        message = messages.posture_relax_message(
            ledger.chain_id,
            entry.owner_hub_identity,
            escrow,
            proposed,
            transaction.valid_until_height,
        )
        identity = ledger.registry.identities[entry.owner_hub_identity]
        if not oracle.verify(identity.hub_public_key, message, body["hub_signature"]):
            raise Refused("UNAUTHORIZED")
    else:
        require_zero_confirmation(body["hub_signature"])
    ledger.registry.escrows[escrow] = replace(entry, posture=proposed)
    return _charged(ledger, escrow)


def _charged(ledger: Ledger, escrow: bytes) -> Outcome:
    """The shared success tail: advance the nonce and take the fixed fee.

    A successful transaction sets the escrow's nonce to the transaction's own,
    which is version one's rule applied to the escrow rather than to a key. Two
    signers acting concurrently on one escrow therefore race for one sequence
    and the loser receives `NONCE_MISMATCH`, with no new machinery.
    """
    ledger.set_nonce(escrow, ledger.nonce(escrow) + 1)
    ledger.collect_fee(escrow)
    return Outcome(result="SUCCESS", fee_charged=ledger.fixed_fee)


def confirmation_required(ledger: Ledger, escrow: bytes, amount: int) -> bool:
    """The posture predicate at the executing height, in block heights only.

    `slot_of(h)` is derived from the executing block height and the accepted
    window grid, so two nodes agree on whether a confirmation was required
    without agreeing on what time it is.
    """
    from .identity import requires_confirmation

    return requires_confirmation(
        ledger.registry.escrows[escrow].posture, amount, ledger.height
    )


def activation_mark(activation_height: int) -> int:
    """The window before a seat's first cycle window, which is what makes the
    accumulation cap well-defined from the moment a seat activates."""
    return grid.window_of_height(activation_height)


_HANDLERS = {
    c.HUB_REGISTER: hub_register,
    c.ESCROW_CREATE: escrow_create,
    c.ESCROW_DELETE: escrow_delete,
    c.SIGNER_ADD: signer_add,
    c.SIGNER_REVOKE: signer_revoke,
    c.SET_SECURITY_POSTURE: set_security_posture,
}
