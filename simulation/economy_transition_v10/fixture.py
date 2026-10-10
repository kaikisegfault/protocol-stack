"""The genesis, the people, and the transaction builders the version-ten traces use.

**Every builder signs what version ten requires and nothing else.** A body
approval is made by building the transaction with its HUB field zero, signing
`approval_message` of it with the person's HUB key, and placing that signature
in the field. The envelope is then signed over the finished bytes, so the
approval and the envelope cover the same transaction.

**A builder takes the height the transaction will execute at**, because every
transaction that carries a HUB proof must expire within one slot of it. The
default validity is exactly that bound, which is the boundary the lifetime rule
admits. A transaction with no HUB proof uses a distant validity, so a trace
shows the rule does not reach it.

**No signature is computed.** A stand-in is version six's counter token,
recorded against the exact key and message it authorizes.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from simulation.calendar.civil import days_from_civil
from simulation.economy_transition_v6 import messages as v6messages
from simulation.economy_transition_v6.identity import escrow_id
from simulation.economy_transition_v6.trace import Signatures
from simulation.economy_transition_v7.trace import (
    ALICE_IDENTITY,
    ALICE_KEY,
    ALICE_SIGNER_KEY,
    BOB_IDENTITY,
    BOB_KEY,
    BOB_SIGNER_KEY,
)

from . import contract as c
from .envelope import Transaction, signed_bytes, signing_message, unsigned_bytes
from .genesis import Genesis
from .ledger import Ledger
from .messages import NO_SIGNATURE, approval_message, attestation_message
from .messages import registration_message

__all__ = [
    "ALICE",
    "BOB",
    "BUILD_AUTHORITY_KEY",
    "BUILD_DIGEST",
    "Builder",
    "DISPUTE_AUTHORITY_KEY",
    "FAR",
    "FIXED_FEE",
    "GENESIS_MILLIS",
    "LAUNCH_KEY",
    "MILLIS_PER_BLOCK",
    "NETWORK_ID",
    "Person",
    "SUPPLY_LIMIT",
    "Signatures",
    "genesis",
    "machine_key",
    "person",
    "timestamp_of_height",
]

SUPPLY_LIMIT = 5_699_395_010_000_000_000
FIXED_FEE = 1_000
NETWORK_ID = 10

LAUNCH_KEY = bytes([0x55]) * 32
DISPUTE_AUTHORITY_KEY = bytes([0xD8]) * 32
BUILD_AUTHORITY_KEY = bytes([0xB4]) * 32
BUILD_DIGEST = bytes([0x33]) * 32

# Far beyond any height a trace reaches, for a transaction with no HUB proof.
FAR = 10_000_000_000

# Version nine's trace rate: ninety seconds a block, so a window is thirty days
# and every window opens in a month of its own, which brings a monthly
# settlement inside four windows.
MILLIS_PER_BLOCK = 90_000
GENESIS_MILLIS = days_from_civil(2026, 1, 15) * 86_400_000


def timestamp_of_height(height: int) -> int:
    return GENESIS_MILLIS + height * MILLIS_PER_BLOCK


def genesis() -> Genesis:
    """No allocation, no accounts, a nonzero fee, and three distinct keys."""
    return Genesis(
        network_id=NETWORK_ID,
        genesis_timestamp=GENESIS_MILLIS,
        supply_limit=SUPPLY_LIMIT,
        fixed_transfer_fee=FIXED_FEE,
        manifest_digest=bytes.fromhex(c.MANIFEST_DIGEST_HEX),
        launch_key=LAUNCH_KEY,
        dispute_authority_key=DISPUTE_AUTHORITY_KEY,
        build_authority_key=BUILD_AUTHORITY_KEY,
    )


@dataclass(frozen=True)
class Person:
    identity: bytes
    hub_key: bytes
    signer_key: bytes

    @property
    def escrow(self) -> bytes:
        return escrow_id(self.identity, 0)


ALICE = Person(ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY)
BOB = Person(BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY)


def person(index: int) -> Person:
    """Three distinct 32-octet values for any index a trace can reach."""
    tail = index.to_bytes(4, "big") + bytes(27)
    return Person(b"\x41" + tail, b"\x4b" + tail, b"\x53" + tail)


def machine_key(seat_id: int, generation: int = 0) -> bytes:
    """A seat's machine key. A later generation is a replacement key."""
    return bytes([0xC0 + generation]) + seat_id.to_bytes(4, "big") + bytes(27)


class Builder:
    """Signed version-ten transactions against one ledger's chain identity."""

    def __init__(self, signatures: Signatures, ledger: Ledger) -> None:
        self.signatures = signatures
        self.ledger = ledger

    # --- framing ---------------------------------------------------------

    def transaction(
        self,
        kind: int,
        authority: bytes,
        nonce: int,
        body: dict,
        valid_until: int,
    ) -> Transaction:
        exempt = kind in (c.HUB_REGISTER, c.ADDED_FEE_EXEMPT_KIND)
        return Transaction(
            kind=kind,
            scheme=c.KIND_SCHEME[kind],
            chain_id=self.ledger.chain_id,
            authority_public_key=authority,
            nonce=nonce,
            body=body,
            fee_limit=0 if exempt else FIXED_FEE,
            valid_until_height=valid_until,
        )

    def sign(self, transaction: Transaction) -> bytes:
        message = signing_message(unsigned_bytes(transaction))
        signature = self.signatures.sign(transaction.authority_public_key, message)
        return signed_bytes(transaction, signature)

    def approve(self, transaction: Transaction, hub_key: bytes) -> Transaction:
        """The version-ten approval: the whole transaction, its HUB field zero."""
        blank = replace(
            transaction, body=dict(transaction.body) | {"hub_signature": NO_SIGNATURE}
        )
        signature = self.signatures.sign(hub_key, approval_message(blank))
        return replace(blank, body=dict(blank.body) | {"hub_signature": signature})

    def approved(
        self,
        who: Person,
        kind: int,
        nonce: int,
        body: dict,
        valid_until: int,
        hub_key: bytes | None = None,
    ) -> bytes:
        """A signer-signed body-carried kind with a whole-transaction approval."""
        draft = self.transaction(
            kind, who.signer_key, nonce, body | {"hub_signature": NO_SIGNATURE},
            valid_until,
        )
        return self.sign(self.approve(draft, hub_key or who.hub_key))

    # --- kind 10 ---------------------------------------------------------

    def registration(
        self,
        who: Person,
        attester_seat: int,
        attester_key: bytes,
        valid_until: int,
        signed_seat: int | None = None,
    ) -> bytes:
        """`signed_seat` is the seat the attester's message names, when a trace
        presents a signature made for one seat under another's identifier."""
        message = registration_message(
            self.ledger.chain_id,
            attester_seat if signed_seat is None else signed_seat,
            who.identity, who.hub_key, who.signer_key, valid_until,
        )
        body = {
            "hub_identity_hash": who.identity,
            "first_signer_public_key": who.signer_key,
            "attesting_seat_id": attester_seat,
            "attestation_signature": self.signatures.sign(attester_key, message),
        }
        return self.sign(
            self.transaction(c.HUB_REGISTER, who.hub_key, 0, body, valid_until)
        )

    # --- the seat ---------------------------------------------------------

    def purchase(
        self,
        who: Person,
        seat_id: int,
        nonce: int,
        valid_until: int,
        referrer: Person | None = None,
    ) -> bytes:
        return self.approved(who, c.PURCHASE_SEAT, nonce, {
            "seat_id": seat_id,
            "has_referrer": referrer is not None,
            "referrer_escrow_id": bytes(32) if referrer is None else referrer.escrow,
        }, valid_until)

    def version_nine_purchase(
        self, who: Person, seat_id: int, nonce: int, valid_until: int
    ) -> bytes:
        """A purchase approved the way version nine approved one."""
        message = v6messages.purchase_message(
            self.ledger.chain_id, who.identity, seat_id, valid_until
        )
        body = {
            "seat_id": seat_id,
            "has_referrer": False,
            "referrer_escrow_id": bytes(32),
            "hub_signature": self.signatures.sign(who.hub_key, message),
        }
        return self.sign(
            self.transaction(c.PURCHASE_SEAT, who.signer_key, nonce, body, valid_until)
        )

    def activation(
        self, who: Person, seat_id: int, nonce: int, valid_until: int
    ) -> bytes:
        return self.approved(
            who, c.ACTIVATE_SEAT, nonce, {"seat_id": seat_id}, valid_until
        )

    # --- kind 23 ---------------------------------------------------------

    def machine_registration(
        self,
        who: Person,
        seat_id: int,
        key: bytes,
        nonce: int,
        valid_until: int,
        attester: bytes = BUILD_AUTHORITY_KEY,
        hub_key: bytes | None = None,
        approve: bool = True,
    ) -> bytes:
        attestation = attestation_message(
            self.ledger.chain_id, seat_id, key, BUILD_DIGEST, valid_until
        )
        body = {
            "seat_id": seat_id,
            "machine_public_key": key,
            "build_digest": BUILD_DIGEST,
            "attestation_signature": self.signatures.sign(attester, attestation),
            "hub_signature": NO_SIGNATURE,
        }
        draft = self.transaction(
            c.REGISTER_MACHINE_KEY, who.signer_key, nonce, body, valid_until
        )
        if approve:
            draft = self.approve(draft, hub_key or who.hub_key)
        return self.sign(draft)

    # --- posture, transfers, signers --------------------------------------

    def posture(
        self,
        who: Person,
        nonce: int,
        requires_confirmation: bool,
        valid_until: int,
        approve: bool,
    ) -> bytes:
        body = {
            "requires_confirmation": requires_confirmation,
            "min_amount_atomic": c.DEFAULT_MIN_AMOUNT_ATOMIC,
            "exempt_slot_mask": c.DEFAULT_EXEMPT_SLOT_MASK,
            "hub_signature": NO_SIGNATURE,
        }
        draft = self.transaction(
            c.SET_SECURITY_POSTURE, who.signer_key, nonce, body, valid_until
        )
        return self.sign(self.approve(draft, who.hub_key) if approve else draft)

    def transfer(
        self, who: Person, recipient: Person, amount: int, nonce: int
    ) -> bytes:
        body = {"recipient_escrow_id": recipient.escrow, "amount_atomic": amount}
        return self.sign(self.transaction(c.TRANSFER, who.signer_key, nonce, body, FAR))

    def confirmed_transfer(
        self,
        who: Person,
        recipient: Person,
        amount: int,
        nonce: int,
        valid_until: int,
        hub_signature: bytes | None = None,
    ) -> bytes:
        """Kind 19. `hub_signature` reuses an approval made for another one."""
        body = {"recipient_escrow_id": recipient.escrow, "amount_atomic": amount}
        if hub_signature is None:
            return self.approved(who, c.TRANSFER_VERIFIED, nonce, body, valid_until)
        body["hub_signature"] = hub_signature
        return self.sign(
            self.transaction(c.TRANSFER_VERIFIED, who.signer_key, nonce, body, valid_until)
        )

    def signer_add(
        self, who: Person, signer_key: bytes, nonce: int, valid_until: int
    ) -> bytes:
        """Kind 15, signed whole by the HUB key: always governed by the lifetime."""
        body = {
            "hub_identity_hash": who.identity,
            "escrow_id": who.escrow,
            "signer_public_key": signer_key,
        }
        return self.sign(
            self.transaction(c.SIGNER_ADD, who.hub_key, nonce, body, valid_until)
        )

    # --- mints and audits ---------------------------------------------------

    def mint(
        self,
        who: Person,
        kind: int,
        nonce: int,
        valid_until: int,
        seat_id: int | None = None,
    ) -> bytes:
        body: dict = {"destination_escrow_id": who.escrow}
        if seat_id is not None:
            body["seat_id"] = seat_id
        return self.approved(who, kind, nonce, body, valid_until)

    def response(
        self, who: Person, seat_id: int, challenge_height: int, nonce: int
    ) -> bytes:
        body = {
            "seat_id": seat_id,
            "challenge_height": challenge_height,
            "answer": bytes(c.ANSWER_BYTES),
        }
        return self.sign(
            self.transaction(c.CHALLENGE_RESPONSE, who.signer_key, nonce, body, FAR)
        )
