"""The eight messages of the HUB signature family, under version five's labels.

The field layouts are version four's, field for field. What version five moves
is the label of each message — because a version-five chain must not accept an
approval a person signed for a version-four one — and, for the address add, the
source of the account the message binds.

That last change is the correction and it does not touch a single byte of
layout. Version four's `address_add_message` took an account the transaction
named in its body; version five's takes the account that sent the transaction.
`address_add_message_for` makes the distinction structural rather than a naming
convention: it accepts one decoded transaction and derives every field from it,
so there is no argument through which a caller could supply an identity the
transaction does not carry. That was exactly how version four's defect stayed
invisible to a codec.

Seven of the eight verify against a person's own recorded public key; only the
registration verifies against the genesis-configured ecosystem verifier key.
"""

from __future__ import annotations

from simulation.common.canonical import label_prefix

from . import contract as c
from .envelope import MalformedTransaction, Transaction, sender_account_id, u32, u64


def registration_message(
    chain_id: bytes,
    hub_identity_hash: bytes,
    hub_public_key: bytes,
    sender_account_id_bytes: bytes,
    valid_until_height: int,
) -> bytes:
    return (
        label_prefix(c.REGISTRATION_LABEL)
        + _octets(chain_id, 32, "chain ID")
        + _octets(hub_identity_hash, 32, "HUB identity hash")
        + _octets(hub_public_key, 32, "HUB public key")
        + _octets(sender_account_id_bytes, 32, "sender")
        + u64(valid_until_height)
    )


def address_add_message(
    chain_id: bytes,
    hub_identity_hash: bytes,
    sender_account_id_bytes: bytes,
    valid_until_height: int,
) -> bytes:
    """The account is the sender's, which is what makes squatting unrepresentable."""
    return _account_action(
        c.ADDRESS_ADD_LABEL,
        chain_id,
        hub_identity_hash,
        sender_account_id_bytes,
        valid_until_height,
    )


def address_add_message_for(transaction: Transaction) -> bytes:
    """Every field derived from one transaction, which is the whole correction.

    A chain holding these bytes and nothing else can build this message: the
    identity is the body's 32-byte field, the account is derived from the
    sender's public key, and the chain and expiry are envelope fields. Version
    four could not, because its body carried an account where the identity had
    to be and its sender was deliberately unconstrained.
    """
    if transaction.kind != c.HUB_ADD_ADDRESS:
        raise MalformedTransaction(
            f"kind {transaction.kind} does not carry an address-add message"
        )
    return address_add_message(
        transaction.chain_id,
        transaction.body["hub_identity_hash"],
        sender_account_id(transaction),
        transaction.valid_until_height,
    )


def address_remove_message(
    chain_id: bytes,
    hub_identity_hash: bytes,
    account_id: bytes,
    valid_until_height: int,
) -> bytes:
    """Unchanged: kind 12 names the account and derives the identity from it."""
    return _account_action(
        c.ADDRESS_REMOVE_LABEL,
        chain_id,
        hub_identity_hash,
        account_id,
        valid_until_height,
    )


def purchase_message(
    chain_id: bytes,
    hub_identity_hash: bytes,
    seat_id: int,
    purchaser_account_id: bytes,
    valid_until_height: int,
) -> bytes:
    return (
        label_prefix(c.PURCHASE_LABEL)
        + _octets(chain_id, 32, "chain ID")
        + _octets(hub_identity_hash, 32, "HUB identity hash")
        + u32(seat_id)
        + _octets(purchaser_account_id, 32, "purchaser")
        + u64(valid_until_height)
    )


def activation_message(
    chain_id: bytes, hub_identity_hash: bytes, seat_id: int, valid_until_height: int
) -> bytes:
    return _seat_action(
        c.ACTIVATION_LABEL, chain_id, hub_identity_hash, seat_id, valid_until_height
    )


def mint_message(
    chain_id: bytes, hub_identity_hash: bytes, seat_id: int, valid_until_height: int
) -> bytes:
    return _seat_action(
        c.MINT_LABEL, chain_id, hub_identity_hash, seat_id, valid_until_height
    )


def mint_biometric_disable_message(
    chain_id: bytes, hub_identity_hash: bytes, seat_id: int, valid_until_height: int
) -> bytes:
    return _seat_action(
        c.MINT_BIOMETRIC_DISABLE_LABEL,
        chain_id,
        hub_identity_hash,
        seat_id,
        valid_until_height,
    )


def manager_message(
    chain_id: bytes,
    hub_identity_hash: bytes,
    seat_id: int,
    manager_account_id: bytes,
    valid_until_height: int,
) -> bytes:
    return (
        label_prefix(c.MANAGER_LABEL)
        + _octets(chain_id, 32, "chain ID")
        + _octets(hub_identity_hash, 32, "HUB identity hash")
        + u32(seat_id)
        + _octets(manager_account_id, 32, "manager")
        + u64(valid_until_height)
    )


def _seat_action(
    label: str,
    chain_id: bytes,
    hub_identity_hash: bytes,
    seat_id: int,
    valid_until_height: int,
) -> bytes:
    return (
        label_prefix(label)
        + _octets(chain_id, 32, "chain ID")
        + _octets(hub_identity_hash, 32, "HUB identity hash")
        + u32(seat_id)
        + u64(valid_until_height)
    )


def _account_action(
    label: str,
    chain_id: bytes,
    hub_identity_hash: bytes,
    account_id: bytes,
    valid_until_height: int,
) -> bytes:
    return (
        label_prefix(label)
        + _octets(chain_id, 32, "chain ID")
        + _octets(hub_identity_hash, 32, "HUB identity hash")
        + _octets(account_id, 32, "account ID")
        + u64(valid_until_height)
    )


def _octets(value: object, width: int, name: str) -> bytes:
    if type(value) is not bytes or len(value) != width:
        raise MalformedTransaction(f"{name} is not {width} octets")
    return value
