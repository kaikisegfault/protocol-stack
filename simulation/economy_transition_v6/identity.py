"""The version-six account architecture: identities, escrows, and signers.

Three objects, each answering exactly one question. An identity says who a person
is; an escrow says where value sits and carries no key; a signer says who may act
on exactly one escrow. The identity is the admin over both of the others, which
is what makes every administrative transaction work for a person holding no key.

**The escrow identifier is derived rather than allocated**, so a wallet computes
it offline and two nodes agree without agreeing on an allocation order. The index
never decreases, so a deleted escrow's identifier is never reissued and a
transaction naming a deleted escrow can never execute against a different one.

**The signer identifier is the accepted version-one account derivation**, with
its subject moved from an account to a signer — which is what a public-key hash
is. Nothing about that construction changes, and the vectors check this
restatement against `test-vectors/protocol-primitives-v1.txt` rather than against
itself.

This module holds no cryptography beyond the accepted SHA-256 construction. A
signature is carried as recorded bytes and is judged by a supplied predicate.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from simulation.economy_transition.merkle import digest

from . import contract as c
from .envelope import MalformedTransaction, u32


class RegistryError(ValueError):
    """A registry operation refused, carrying its version-six result code."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def escrow_id(hub_identity_hash: bytes, escrow_index: int) -> bytes:
    """`H(D("protocol-stack:v6:escrow") || identity || u32(index))`."""
    if type(hub_identity_hash) is not bytes or len(hub_identity_hash) != 32:
        raise MalformedTransaction("HUB identity hash is not 32 octets")
    return digest(c.ESCROW_LABEL, hub_identity_hash + u32(escrow_index))


def signer_id(public_key: bytes) -> bytes:
    """The accepted version-one derivation, unchanged, naming a signer."""
    if type(public_key) is not bytes or len(public_key) != 32:
        raise MalformedTransaction("signer public key is not 32 octets")
    return digest(c.ACCOUNT_LABEL, b"\x01" + public_key)


@dataclass(frozen=True)
class Posture:
    """A per-escrow security posture. A new escrow takes the strict default."""

    requires_confirmation: bool = c.DEFAULT_REQUIRES_CONFIRMATION
    min_amount_atomic: int = c.DEFAULT_MIN_AMOUNT_ATOMIC
    exempt_slot_mask: int = c.DEFAULT_EXEMPT_SLOT_MASK

    def __post_init__(self) -> None:
        if not 0 <= self.min_amount_atomic <= c.MAX_U64:
            raise MalformedTransaction("minimum amount does not fit u64")
        if not 0 <= self.exempt_slot_mask <= c.MAX_EXEMPT_SLOT_MASK:
            raise MalformedTransaction("exempt slot mask sets a bit above slot 23")


def slot_of(height: int) -> int:
    """The accepted window grid's hour slot. A height, never a wall clock."""
    return (height % c.CYCLE_BLOCKS) // c.SLOT_BLOCKS


def requires_confirmation(posture: Posture, amount_atomic: int, height: int) -> bool:
    """Whether this operation needs a biometric confirmation.

    A `min_amount_atomic` of zero means every amount qualifies, because every
    amount is at least zero.
    """
    if not posture.requires_confirmation:
        return False
    if amount_atomic < posture.min_amount_atomic:
        return False
    return not (posture.exempt_slot_mask >> slot_of(height)) & 1


def relaxes(current: Posture, proposed: Posture) -> bool:
    """Whether a posture change shrinks the set of operations needing a proof.

    A chain cannot read intent, so the direction is derived from the two stored
    postures. Each disjunct is one way to shrink that set, and they are checked
    independently: a change that tightens one field and relaxes another counts
    as a relaxation, because the failure that matters is a stolen key weakening
    a protection and a change that weakens anything is a weakening.
    """
    if current.requires_confirmation and not proposed.requires_confirmation:
        return True
    if proposed.min_amount_atomic > current.min_amount_atomic:
        return True
    return bool(proposed.exempt_slot_mask & ~current.exempt_slot_mask)


def unchanged(current: Posture, proposed: Posture) -> bool:
    return current == proposed


@dataclass(frozen=True)
class Identity:
    hub_public_key: bytes
    registered_at_height: int
    next_escrow_index: int
    escrow_count: int
    seat_count: int


@dataclass(frozen=True)
class Escrow:
    owner_hub_identity: bytes
    posture: Posture
    signer_count: int


@dataclass(frozen=True)
class Enrollment:
    enrolled_at_height: int
    minted_through_window: int
    issued_atomic: int


@dataclass
class Registry:
    """Identities, escrows, signers, enrollments, and the account map.

    The account map is version one's: an escrow's balance and nonce live there
    and nowhere else, which is what makes a version-six state a version-one
    state plus an economy map. Every key in it is an escrow, which is the
    structural invariant this whole version exists to establish.
    """

    identities: dict[bytes, Identity] = field(default_factory=dict)
    escrows: dict[bytes, Escrow] = field(default_factory=dict)
    signers: dict[bytes, bytes] = field(default_factory=dict)
    enrollments: dict[bytes, Enrollment] = field(default_factory=dict)
    accounts: dict[bytes, tuple[int, int]] = field(default_factory=dict)
    enrolled_count: int = 0

    # --- resolution -----------------------------------------------------

    def escrow_of_signer(self, public_key: bytes) -> bytes:
        """Scheme 1's resolution. A key with no entry authorizes nothing."""
        identifier = signer_id(public_key)
        if identifier not in self.signers:
            raise RegistryError("SIGNER_NOT_FOUND", "no signer entry for this key")
        return self.signers[identifier]

    def identity_of_escrow(self, escrow: bytes) -> bytes:
        if escrow not in self.escrows:
            raise RegistryError("ESCROW_NOT_FOUND", "no escrow entry")
        return self.escrows[escrow].owner_hub_identity

    def require_identity(self, hub_identity_hash: bytes, header_key: bytes) -> Identity:
        """Scheme 2's resolution: the body names the identity, the header the key."""
        identity = self.identities.get(hub_identity_hash)
        if identity is None:
            raise RegistryError("NOT_HUB_VERIFIED", "unregistered HUB identity")
        if identity.hub_public_key != header_key:
            raise RegistryError(
                "UNAUTHORIZED", "header key is not this identity's recorded key"
            )
        return identity

    def require_owned(self, escrow: bytes, hub_identity_hash: bytes) -> Escrow:
        entry = self.escrows.get(escrow)
        if entry is None:
            raise RegistryError("ESCROW_NOT_FOUND", "no escrow entry")
        if entry.owner_hub_identity != hub_identity_hash:
            raise RegistryError("ESCROW_NOT_OWNED", "escrow belongs to another identity")
        return entry

    # --- transitions ----------------------------------------------------

    def register(
        self,
        hub_identity_hash: bytes,
        hub_public_key: bytes,
        first_signer_public_key: bytes,
        height: int,
    ) -> bytes:
        """Kind 10. One atomic execution that creates a whole participant.

        Returns the new escrow's identifier. The airdrop is credited here when
        the enrollment population is not exhausted, and it is what makes the new
        account able to transact at all.
        """
        if hub_identity_hash in self.identities:
            raise RegistryError("REPLAY", "identity already registered")
        first_signer = signer_id(first_signer_public_key)
        if first_signer in self.signers:
            raise RegistryError("REPLAY", "signer key already assigned to an escrow")

        escrow = escrow_id(hub_identity_hash, 0)
        credit = 0
        if self.enrolled_count < c.VERIFIED_USER_POPULATION:
            credit = c.VERIFIED_USER_DAILY_ATOMIC

        self.identities[hub_identity_hash] = Identity(
            hub_public_key=hub_public_key,
            registered_at_height=height,
            next_escrow_index=1,
            escrow_count=1,
            seat_count=0,
        )
        self.escrows[escrow] = Escrow(
            owner_hub_identity=hub_identity_hash, posture=Posture(), signer_count=1
        )
        self.signers[first_signer] = escrow
        self.accounts[escrow] = (credit, 0)
        if credit:
            from .verified_user import enroll

            self.enrollments[hub_identity_hash] = enroll(height)
            self.enrolled_count += 1
        return escrow

    def create_escrow(self, hub_identity_hash: bytes) -> bytes:
        """Kind 13. The index is the identity's own and never decreases."""
        identity = self.identities[hub_identity_hash]
        escrow = escrow_id(hub_identity_hash, identity.next_escrow_index)
        self.escrows[escrow] = Escrow(
            owner_hub_identity=hub_identity_hash, posture=Posture(), signer_count=0
        )
        self.accounts[escrow] = (0, 0)
        self.identities[hub_identity_hash] = replace(
            identity,
            next_escrow_index=identity.next_escrow_index + 1,
            escrow_count=identity.escrow_count + 1,
        )
        return escrow

    def delete_escrow(self, hub_identity_hash: bytes, escrow: bytes) -> None:
        """Kind 14. A deleted escrow must be empty, and its index is not reused."""
        balance, _nonce = self.accounts[escrow]
        if balance != 0:
            raise RegistryError("ESCROW_NOT_EMPTY", "escrow holds value")
        for identifier in [k for k, v in self.signers.items() if v == escrow]:
            del self.signers[identifier]
        del self.escrows[escrow]
        del self.accounts[escrow]
        identity = self.identities[hub_identity_hash]
        self.identities[hub_identity_hash] = replace(
            identity, escrow_count=identity.escrow_count - 1
        )

    def add_signer(self, escrow: bytes, public_key: bytes) -> bytes:
        """Kind 15, and the recovery path. Ordinary rather than special."""
        identifier = signer_id(public_key)
        if identifier in self.signers:
            raise RegistryError("REPLAY", "signer key already assigned to an escrow")
        entry = self.escrows[escrow]
        if entry.signer_count >= c.MAX_SIGNERS_PER_ESCROW:
            raise RegistryError("SIGNER_LIMIT", "escrow already holds 16 signers")
        self.signers[identifier] = escrow
        self.escrows[escrow] = replace(entry, signer_count=entry.signer_count + 1)
        return identifier

    def revoke_signer(self, escrow: bytes, identifier: bytes) -> None:
        """Kind 16. Immediate and total: a revoked key authorizes nothing."""
        assigned = self.signers.get(identifier)
        if assigned is None:
            raise RegistryError("SIGNER_NOT_FOUND", "no signer entry")
        if assigned != escrow:
            raise RegistryError("UNAUTHORIZED", "signer is assigned to another escrow")
        del self.signers[identifier]
        entry = self.escrows[escrow]
        self.escrows[escrow] = replace(entry, signer_count=entry.signer_count - 1)

    def set_posture(self, escrow: bytes, posture: Posture) -> None:
        """Kind 17. The direction of the change decides what authorized it."""
        entry = self.escrows[escrow]
        if unchanged(entry.posture, posture):
            raise RegistryError("REPLAY", "posture already equals the proposal")
        self.escrows[escrow] = replace(entry, posture=posture)

    # --- encoding -------------------------------------------------------

    def entries(self) -> dict[bytes, bytes]:
        """The registry as economy entries, in the canonical encodings."""
        from .state import (
            escrow_key,
            escrow_value,
            hub_identity_key,
            hub_identity_value,
            signer_key,
            signer_value,
            verified_user_counter_key,
            verified_user_counter_value,
            verified_user_key,
            verified_user_value,
        )

        entries: dict[bytes, bytes] = {}
        for hub_identity_hash, entry in self.identities.items():
            entries[hub_identity_key(hub_identity_hash)] = hub_identity_value(
                entry.hub_public_key,
                entry.registered_at_height,
                entry.next_escrow_index,
                entry.escrow_count,
                entry.seat_count,
            )
        for escrow, entry in self.escrows.items():
            entries[escrow_key(escrow)] = escrow_value(
                entry.owner_hub_identity, entry.posture, entry.signer_count
            )
        for identifier, escrow in self.signers.items():
            entries[signer_key(identifier)] = signer_value(escrow)
        for hub_identity_hash, enrollment in self.enrollments.items():
            entries[verified_user_key(hub_identity_hash)] = verified_user_value(
                enrollment.enrolled_at_height,
                enrollment.minted_through_window,
                enrollment.issued_atomic,
            )
        entries[verified_user_counter_key()] = verified_user_counter_value(
            self.enrolled_count
        )
        return entries

    def account_list(self) -> list[tuple[bytes, int, int]]:
        """The version-one account map, ordered as the accounts tree requires."""
        return [
            (escrow, balance, nonce)
            for escrow, (balance, nonce) in sorted(self.accounts.items())
        ]

    def claim_seat(self, hub_identity_hash: bytes) -> None:
        identity = self.identities[hub_identity_hash]
        if identity.seat_count >= c.MAX_SEATS_PER_IDENTITY:
            raise RegistryError("SEAT_LIMIT", "identity already holds 1,000 seats")
        self.identities[hub_identity_hash] = replace(
            identity, seat_count=identity.seat_count + 1
        )

    # --- invariants -----------------------------------------------------

    def structural_failures(self) -> list[str]:
        """The four invariants version six adds, checked as equalities.

        A bound rather than an equality would admit a defect that lost a count,
        which is the reason version four gives for its two.
        """
        failures: list[str] = []
        if set(self.accounts) != set(self.escrows):
            failures.append("the account map and the escrow set have different keys")
        for escrow, entry in self.escrows.items():
            if entry.owner_hub_identity not in self.identities:
                failures.append("an escrow names an unregistered identity")
            assigned = sum(1 for target in self.signers.values() if target == escrow)
            if assigned != entry.signer_count:
                failures.append("an escrow's signer count is not its signer entries")
            if entry.signer_count > c.MAX_SIGNERS_PER_ESCROW:
                failures.append("an escrow holds more than sixteen signers")
        for target in self.signers.values():
            if target not in self.escrows:
                failures.append("a signer names an escrow that does not exist")
        for hub_identity_hash, identity in self.identities.items():
            live = sum(
                1
                for entry in self.escrows.values()
                if entry.owner_hub_identity == hub_identity_hash
            )
            if live != identity.escrow_count:
                failures.append("an identity's escrow count is not its escrow entries")
            if identity.next_escrow_index < identity.escrow_count:
                failures.append("an identity's next index is below its live count")
            if identity.seat_count > c.MAX_SEATS_PER_IDENTITY:
                failures.append("an identity holds more than one thousand seats")
        return failures
