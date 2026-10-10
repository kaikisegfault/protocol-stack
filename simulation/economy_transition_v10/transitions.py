"""Version ten's dispatch: two handlers of its own, and version nine's for the rest.

**Kind 10 is restated and kind 23 is new.** Every other kind runs on version
nine's own dispatch, handed an `ApprovalOracle` so that a body approval verifies
over the version-ten message and nothing else about the kind moves.

**Kind 10 is restated rather than wrapped** because its conditions change in
three places — the lifetime rule, the attester branch, and the count — and its
version-nine handler verifies the version-nine message against the launch key
before the point where version ten's machine branch begins. Its four writes are
version nine's, performed in the same order with the same values, and the count
is the one write added.

`tests/simulation/economy_transition_v10_execution_test.py` requires the carried
path to be version nine's own function object, so a copy that appeared here
later would fail a test rather than pass silently.
"""

from __future__ import annotations

from dataclasses import replace

from simulation.economy_transition_v6.identity import (
    Escrow,
    Identity,
    Posture,
    escrow_id,
    signer_id,
)
from simulation.economy_transition_v6.transitions import _charged
from simulation.economy_transition_v6.value_transitions import _require_seat
from simulation.economy_transition_v6.verified_user import enroll
from simulation.economy_transition_v8.slots import window_of_height
from simulation.economy_transition_v9 import transitions as v9

from . import contract as c
from .approval import ApprovalOracle
from .envelope import Transaction
from .execution import Outcome, Refused, SignatureOracle, require_fresh
from .ledger import Ledger
from .messages import (
    NO_SIGNATURE,
    approval_message,
    attestation_message,
    registration_message,
)
from .state import MachineKey

__all__ = [
    "VERSION_NINE_DISPATCH",
    "dispatch",
    "hub_register",
    "register_machine_key",
]

# Version nine's own dispatch, kept reachable so a test can require the carried
# path to be it rather than an equal-looking copy.
VERSION_NINE_DISPATCH = v9.dispatch


def dispatch(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    if transaction.kind == c.HUB_REGISTER:
        return hub_register(ledger, transaction, escrow, oracle)
    if transaction.kind == c.REGISTER_MACHINE_KEY:
        return register_machine_key(ledger, transaction, escrow, oracle)
    return VERSION_NINE_DISPATCH(
        ledger, transaction, escrow, ApprovalOracle(oracle, transaction)
    )


# --- kind 10 -----------------------------------------------------------------


def hub_register(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    """Kind 10. An attester's signature, the replays, the limit, then the writes.

    The attester is the launch key while it is unretired, or the registered key
    of a machine that is active at this height. Each registration a machine
    signs counts against that machine, because the message binds the seat.
    """
    del escrow
    require_fresh(ledger, transaction)
    body = transaction.body
    identity_hash = body["hub_identity_hash"]
    if identity_hash in ledger.registry.identities:
        raise Refused("REPLAY")
    first_signer = signer_id(body["first_signer_public_key"])
    if first_signer in ledger.registry.signers:
        raise Refused("REPLAY")

    attester = body["attesting_seat_id"]
    message = registration_message(
        ledger.chain_id,
        attester,
        identity_hash,
        transaction.authority_public_key,
        body["first_signer_public_key"],
        transaction.valid_until_height,
    )
    counted: MachineKey | None = None
    if attester == c.LAUNCH_ATTESTER:
        if ledger.launch_retired_at is not None:
            raise Refused("LAUNCH_KEY_RETIRED")
        if not oracle.verify(ledger.launch_key, message, body["attestation_signature"]):
            raise Refused("UNAUTHORIZED")
    else:
        counted = _counted_attestation(
            ledger, attester, message, body["attestation_signature"], oracle
        )

    enrolling = ledger.registry.enrolled_count < c.VERIFIED_USER_POPULATION
    airdrop = c.VERIFIED_USER_DAILY_ATOMIC if enrolling else 0
    if airdrop and not ledger.fits_channel(c.VERIFIED_USER_CHANNEL, airdrop):
        raise Refused("CHANNEL_CAP")

    _admit_participant(ledger, transaction, first_signer, enrolling, airdrop)
    if counted is not None:
        ledger.machine_keys[attester] = counted
    return Outcome(result="SUCCESS", issued_atomic=airdrop, fee_charged=0)


def _counted_attestation(
    ledger: Ledger,
    seat_id: int,
    message: bytes,
    signature: bytes,
    oracle: SignatureOracle,
) -> MachineKey:
    """The machine branch's four conditions, and the entry its count produces.

    **The limit is checked after the signature**, so a refusal for the limit is
    only ever given for a registration that was otherwise valid. A forgery naming
    a full machine is `UNAUTHORIZED`, which is the true reason.
    """
    if seat_id > c.MAX_SEAT_ID:
        raise Refused("CYCLE_RANGE")
    entry = ledger.machine_keys.get(seat_id)
    if entry is None:
        raise Refused("MACHINE_KEY_NOT_FOUND")
    if not ledger.machine_active(seat_id):
        raise Refused("MACHINE_NOT_ACTIVE")
    if not oracle.verify(entry.machine_public_key, message, signature):
        raise Refused("UNAUTHORIZED")
    window = window_of_height(ledger.height)
    count = entry.registrations_in_window if entry.registration_window == window else 0
    if count >= c.MACHINE_REGISTRATIONS_PER_WINDOW:
        raise Refused("REGISTRATION_LIMIT")
    return replace(entry, registration_window=window, registrations_in_window=count + 1)


def _admit_participant(
    ledger: Ledger,
    transaction: Transaction,
    first_signer: bytes,
    enrolling: bool,
    airdrop: int,
) -> None:
    """Version nine's four writes, in its order and with its values."""
    identity_hash = transaction.body["hub_identity_hash"]
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


# --- kind 23 -----------------------------------------------------------------


def register_machine_key(
    ledger: Ledger,
    transaction: Transaction,
    escrow: bytes | None,
    oracle: SignatureOracle,
) -> Outcome:
    """Kind 23. Seven ordered conditions, three writes, and the fixed fee.

    **The HUB approval is always required, and the posture does not waive it.**
    Installing a key that can admit people is authority over the ecosystem, not
    movement of the founder's own value.

    **A replacement keeps the count and the mark.** Activity belongs to the
    seat's cycle, so a machine that replaces its key mid-window stays active,
    and a count that reset would let key rotation bypass the limit.
    """
    assert escrow is not None
    body = transaction.body
    seat_id = body["seat_id"]
    # Conditions 1 to 4: range, purchased, activated, and owned by the identity
    # behind the acting escrow, in version six's order for a seat.
    seat = _require_seat(ledger, seat_id, escrow, require_activated=True)

    key = body["machine_public_key"]
    if key in ledger.machine_key_owners:
        raise Refused("REPLAY")
    attestation = attestation_message(
        ledger.chain_id,
        seat_id,
        key,
        body["build_digest"],
        transaction.valid_until_height,
    )
    if not oracle.verify(
        ledger.build_authority_key, attestation, body["attestation_signature"]
    ):
        raise Refused("UNAUTHORIZED")
    if body["hub_signature"] == NO_SIGNATURE:
        raise Refused("BIOMETRIC_REQUIRED")
    hub_key = ledger.registry.identities[seat.hub_identity_hash].hub_public_key
    if not oracle.verify(hub_key, approval_message(transaction), body["hub_signature"]):
        raise Refused("UNAUTHORIZED")

    existing = ledger.machine_keys.get(seat_id)
    if existing is None:
        written = MachineKey(
            machine_public_key=key,
            build_digest=body["build_digest"],
            registered_at_height=ledger.height,
        )
    else:
        del ledger.machine_key_owners[existing.machine_public_key]
        written = replace(
            existing,
            machine_public_key=key,
            build_digest=body["build_digest"],
            registered_at_height=ledger.height,
        )
    ledger.machine_keys[seat_id] = written
    ledger.machine_key_owners[key] = seat_id
    charged = _charged(ledger, escrow)
    return Outcome(result=charged.result, fee_charged=charged.fee_charged)
