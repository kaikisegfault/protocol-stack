"""The eight messages the HUB signature family covers.

Seven verify against a person's own recorded public key. Only the registration
verifies against the genesis-configured ecosystem verifier key, because
asserting that a live, distinct human stands behind an identity is the one
judgement no chain can make — and once made, nothing else needs the verifier.

Every message names the identity, so a signature made by one person's key cannot
be presented as another's even where the remaining fields coincide. Three carry
identical field shapes and are separated only by their labels, which is what
domain separation is for: an approval to activate a seat must not be presentable
as an approval to mint from it or to remove its protection.
"""

from __future__ import annotations

from simulation.common.canonical import label_prefix

from . import contract as c
from .envelope import MalformedTransaction, u32, u64


def registration_message(
    chain_id: bytes,
    hub_identity_hash: bytes,
    hub_public_key: bytes,
    sender_account_id: bytes,
    valid_until_height: int,
) -> bytes:
    return (
        label_prefix(c.REGISTRATION_LABEL)
        + _octets(chain_id, 32, "chain ID")
        + _octets(hub_identity_hash, 32, "HUB identity hash")
        + _octets(hub_public_key, 32, "HUB public key")
        + _octets(sender_account_id, 32, "sender")
        + u64(valid_until_height)
    )


def address_add_message(
    chain_id: bytes,
    hub_identity_hash: bytes,
    account_id: bytes,
    valid_until_height: int,
) -> bytes:
    return _account_action(
        c.ADDRESS_ADD_LABEL, chain_id, hub_identity_hash, account_id,
        valid_until_height
    )


def address_remove_message(
    chain_id: bytes,
    hub_identity_hash: bytes,
    account_id: bytes,
    valid_until_height: int,
) -> bytes:
    return _account_action(
        c.ADDRESS_REMOVE_LABEL, chain_id, hub_identity_hash, account_id,
        valid_until_height
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
        c.MINT_BIOMETRIC_DISABLE_LABEL, chain_id, hub_identity_hash, seat_id,
        valid_until_height
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
