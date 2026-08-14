"""The HUB registry: identities, their address sets, and their two counts.

This is the state version four adds and the arithmetic that keeps it consistent.
It models the registry rather than the capture: what the chain holds is a public
key the ecosystem verifier attested to, a set of accounts linked to it, and two
counts. Nothing about liveness, unlinkability, or how a person's key is produced
reaches this surface, and the specification says so.

Two invariants are equalities rather than bounds, because a bound would admit a
defect that lost a count: an identity's `address_count` equals the number of
address entries naming it, and its `seat_count` equals the number of seats naming
it and never exceeds the constitution's per-human bound.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import contract as c


class InvalidRegistry(ValueError):
    """A registry operation no conforming chain could accept."""


@dataclass
class Identity:
    hub_public_key: bytes
    registered_at_height: int
    address_count: int = 1
    seat_count: int = 0


@dataclass
class Registry:
    """An in-memory HUB registry, keyed exactly as the state keys are."""

    identities: dict[bytes, Identity] = field(default_factory=dict)
    addresses: dict[bytes, bytes] = field(default_factory=dict)

    def register(
        self,
        hub_identity_hash: bytes,
        hub_public_key: bytes,
        sender_account_id: bytes,
        height: int,
    ) -> str:
        """Kind 10. The sender becomes the identity's first address."""
        if hub_identity_hash in self.identities:
            return "REPLAY"
        if sender_account_id in self.addresses:
            return "REPLAY"
        self.identities[hub_identity_hash] = Identity(
            hub_public_key=hub_public_key, registered_at_height=height
        )
        self.addresses[sender_account_id] = hub_identity_hash
        return "SUCCESS"

    def add_address(self, hub_identity_hash: bytes, account_id: bytes) -> str:
        """Kind 11. Named in the message rather than derived from the sender.

        A person recovering from total address loss has no linked sender to
        derive an identity from, which is the whole reason this transaction
        accepts any sender.
        """
        identity = self.identities.get(hub_identity_hash)
        if identity is None:
            return "NOT_HUB_VERIFIED"
        if account_id in self.addresses:
            return "REPLAY"
        if identity.address_count >= c.MAX_IDENTITY_ADDRESSES:
            return "ADDRESS_LIMIT"
        self.addresses[account_id] = hub_identity_hash
        identity.address_count += 1
        return "SUCCESS"

    def remove_address(self, account_id: bytes) -> str:
        """Kind 12. Unlinks an identity claim and moves no value."""
        hub_identity_hash = self.addresses.get(account_id)
        if hub_identity_hash is None:
            return "NOT_HUB_VERIFIED"
        del self.addresses[account_id]
        self.identities[hub_identity_hash].address_count -= 1
        return "SUCCESS"

    def identity_of(self, account_id: bytes) -> bytes | None:
        return self.addresses.get(account_id)

    def is_verified(self, account_id: bytes) -> bool:
        return account_id in self.addresses

    def claim_seat(self, hub_identity_hash: bytes) -> str:
        """The constitution's per-human bound, finally enforceable.

        Version three records that the 1,000-seat limit cannot be enforced,
        because enforcing it requires knowing that two biometric hashes belong
        to one human. With one identity per person in state, it can be.
        """
        identity = self.identities.get(hub_identity_hash)
        if identity is None:
            return "NOT_HUB_VERIFIED"
        if identity.seat_count >= c.MAX_SEATS_PER_IDENTITY:
            return "SEAT_LIMIT"
        identity.seat_count += 1
        return "SUCCESS"

    def counts_agree(self, seats_by_identity: dict[bytes, int]) -> bool:
        """Both structural invariants, checked as equalities."""
        linked: dict[bytes, int] = {}
        for identity_hash in self.addresses.values():
            linked[identity_hash] = linked.get(identity_hash, 0) + 1
        for identity_hash, identity in self.identities.items():
            if identity.address_count != linked.get(identity_hash, 0):
                return False
            if identity.seat_count != seats_by_identity.get(identity_hash, 0):
                return False
            if identity.seat_count > c.MAX_SEATS_PER_IDENTITY:
                return False
        return True

    def entries(self) -> dict[bytes, bytes]:
        """The registry as canonical state entries."""
        from .state import (
            hub_address_key,
            hub_address_value,
            hub_identity_key,
            hub_identity_value,
        )

        written: dict[bytes, bytes] = {}
        for identity_hash, identity in self.identities.items():
            written[hub_identity_key(identity_hash)] = hub_identity_value(
                identity.hub_public_key,
                identity.registered_at_height,
                identity.address_count,
                identity.seat_count,
            )
        for account_id, identity_hash in self.addresses.items():
            written[hub_address_key(account_id)] = hub_address_value(identity_hash)
        return written


def self_referral(purchaser_identity: bytes, referrer_identity: bytes | None) -> bool:
    """Version three compares accounts; version four compares people.

    A buyer could refer themselves from a second address they controlled, which
    one account comparison cannot see and one identity comparison always can.
    """
    return referrer_identity is not None and referrer_identity == purchaser_identity
