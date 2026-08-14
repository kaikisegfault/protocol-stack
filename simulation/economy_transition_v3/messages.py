"""The six messages the off-chain ecosystem verifier signs.

Each binds the chain, the acting account, the exact subject, and the
transaction's own expiry, so an approval is action-bound: it cannot be replayed
onto another seat, another actor, another chain, or a later attempt.

Three of the six carry identical field shapes and are separated only by their
labels, which is what domain separation is for. A verifier approval issued for
an activation must not be presentable as an approval for a protected mint or for
removing a seat's protection, and nothing but the label distinguishes them.
"""

from __future__ import annotations

from simulation.common.canonical import label_prefix

from . import contract as c
from .envelope import MalformedTransaction, u32, u64


def enrollment_message(
    chain_id: bytes,
    seat_id: int,
    biometric_identity_hash: bytes,
    purchaser_account_id: bytes,
    valid_until_height: int,
) -> bytes:
    return (
        label_prefix(c.ENROLLMENT_LABEL)
        + _octets(chain_id, 32, "chain ID")
        + u32(seat_id)
        + _octets(biometric_identity_hash, 32, "biometric hash")
        + _octets(purchaser_account_id, 32, "purchaser")
        + u64(valid_until_height)
    )


def activation_message(
    chain_id: bytes, seat_id: int, sender_account_id: bytes, valid_until_height: int
) -> bytes:
    return _seat_action(c.ACTIVATION_LABEL, chain_id, seat_id, sender_account_id,
                        valid_until_height)


def mint_message(
    chain_id: bytes, seat_id: int, sender_account_id: bytes, valid_until_height: int
) -> bytes:
    return _seat_action(c.MINT_LABEL, chain_id, seat_id, sender_account_id,
                        valid_until_height)


def mint_biometric_disable_message(
    chain_id: bytes, seat_id: int, sender_account_id: bytes, valid_until_height: int
) -> bytes:
    return _seat_action(c.MINT_BIOMETRIC_DISABLE_LABEL, chain_id, seat_id,
                        sender_account_id, valid_until_height)


def manager_message(
    chain_id: bytes,
    seat_id: int,
    sender_account_id: bytes,
    manager_account_id: bytes,
    valid_until_height: int,
) -> bytes:
    return (
        label_prefix(c.MANAGER_LABEL)
        + _octets(chain_id, 32, "chain ID")
        + u32(seat_id)
        + _octets(sender_account_id, 32, "sender")
        + _octets(manager_account_id, 32, "manager")
        + u64(valid_until_height)
    )


def hub_message(
    chain_id: bytes,
    sender_account_id: bytes,
    hub_uniqueness_hash: bytes,
    valid_until_height: int,
) -> bytes:
    return (
        label_prefix(c.HUB_LABEL)
        + _octets(chain_id, 32, "chain ID")
        + _octets(sender_account_id, 32, "sender")
        + _octets(hub_uniqueness_hash, 32, "HUB uniqueness hash")
        + u64(valid_until_height)
    )


def _seat_action(
    label: str,
    chain_id: bytes,
    seat_id: int,
    sender_account_id: bytes,
    valid_until_height: int,
) -> bytes:
    return (
        label_prefix(label)
        + _octets(chain_id, 32, "chain ID")
        + u32(seat_id)
        + _octets(sender_account_id, 32, "sender")
        + u64(valid_until_height)
    )


def _octets(value: object, width: int, name: str) -> bytes:
    if type(value) is not bytes or len(value) != width:
        raise MalformedTransaction(f"{name} is not {width} octets")
    return value
