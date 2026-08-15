"""The HUB registry, and kind 11's corrected reading of who is being linked.

The registry itself is version four's, imported rather than copied: identities,
their address sets, the two counts kept as equalities, the per-human seat
bound, and the ordered outcomes of every operation are unchanged. Version four's
defect was never in the registry — `add_address(identity, account)` was always
the right operation. It was that no conforming chain could obtain the first
argument from a kind-11 transaction.

So what version five adds here is the transition entry point rather than a
second registry. `apply_add_address` takes one decoded transaction and nothing
else: the identity is its body's 32-byte field and the account is derived from
its sender's public key. There is no parameter through which a caller can name
a third account, which is what makes address squatting unrepresentable rather
than merely refused.

`version_four_add_address` is the superseded reading, kept for one purpose: to
demonstrate what it permitted. It is not part of the version-five contract.
"""

from __future__ import annotations

from simulation.economy_transition_v4.identity import (
    Identity,
    InvalidRegistry,
    Registry,
    self_referral,
)

from . import contract as c
from .envelope import MalformedTransaction, Transaction, sender_account_id

__all__ = [
    "Identity",
    "InvalidRegistry",
    "Registry",
    "apply_add_address",
    "linked_account",
    "self_referral",
    "version_four_add_address",
]


def linked_account(transaction: Transaction) -> bytes:
    """The account kind 11 links: the sender's, always, by construction."""
    _require_add_address(transaction)
    return sender_account_id(transaction)


def apply_add_address(registry: Registry, transaction: Transaction) -> str:
    """Kind 11, in the order the specification lists its rejection conditions.

    An unregistered identity is `NOT_HUB_VERIFIED`; a sender already linked to
    any identity is `REPLAY`; an identity already holding sixteen addresses is
    `ADDRESS_LIMIT`. The fourth condition — a HUB signature that does not verify
    against the identity's recorded public key — is `UNAUTHORIZED` and is not
    reached here, because this model implements no cryptographic primitive and
    carries a signature as recorded bytes.
    """
    _require_add_address(transaction)
    return registry.add_address(
        transaction.body["hub_identity_hash"], sender_account_id(transaction)
    )


def version_four_add_address(
    registry: Registry, hub_identity_hash: bytes, named_account_id: bytes
) -> str:
    """Version four's reading, retained only to show what it permitted.

    The account came from the body and the sender was unconstrained, so anyone
    could link **another person's** address to their own identity. That person's
    own registration is then `REPLAY` forever, and they cannot call removal,
    because removal is authorized by the identity the address is linked to —
    which is the attacker's.

    Version four could not actually execute this: the transaction carried no
    identity for the first argument. The call is what the obvious repair — an
    identity field beside the account — would have made executable, and it is
    the second hole ADR 0037 records the chosen correction as closing.
    """
    return registry.add_address(hub_identity_hash, named_account_id)


def _require_add_address(transaction: Transaction) -> None:
    if transaction.kind != c.HUB_ADD_ADDRESS:
        raise MalformedTransaction(
            f"kind {transaction.kind} is not an address addition"
        )
