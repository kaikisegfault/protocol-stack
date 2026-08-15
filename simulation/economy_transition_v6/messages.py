"""The six domain-separated HUB messages of version six.

Five verify against the acting identity's recorded `hub_public_key`; only the
registration verifies against the genesis-configured ecosystem verifier key,
which is the one judgement no chain can make.

Every message binds the identity, so a signature made by one person's key cannot
be presented as another's even where the remaining fields coincide. The mint
message additionally binds the kind and the destination, which is what stops a
confirmation obtained for one mint being replayed onto a different one, and the
posture message binds the exact posture it approves, so an approval to raise a
minimum cannot be presented as an approval to turn confirmation off.

Version four needed eight messages and version six needs six: address add,
address remove, and the seat-manager message lost their kinds, and the mint and
posture messages replace the two the per-seat flag needed.
"""

from __future__ import annotations

from simulation.common.canonical import label_prefix

from . import contract as c
from .envelope import MalformedTransaction, u8, u32, u64
from .identity import Posture


def _identity(value: bytes) -> bytes:
    if type(value) is not bytes or len(value) != 32:
        raise MalformedTransaction("HUB identity hash is not 32 octets")
    return value


def _chain(value: bytes) -> bytes:
    if type(value) is not bytes or len(value) != 32:
        raise MalformedTransaction("chain ID is not 32 octets")
    return value


def registration_message(
    chain_id: bytes,
    hub_identity_hash: bytes,
    hub_public_key: bytes,
    first_signer_public_key: bytes,
    valid_until_height: int,
) -> bytes:
    """The verifier's attestation, and the only thing it ever signs.

    It binds the identity to the key, which is what stops anyone registering
    their own key against another person's identity hash.
    """
    return (
        label_prefix(c.REGISTRATION_LABEL)
        + _chain(chain_id)
        + _identity(hub_identity_hash)
        + _identity(hub_public_key)
        + _identity(first_signer_public_key)
        + u64(valid_until_height)
    )


def purchase_message(
    chain_id: bytes, hub_identity_hash: bytes, seat_id: int, valid_until_height: int
) -> bytes:
    return (
        label_prefix(c.PURCHASE_LABEL)
        + _chain(chain_id)
        + _identity(hub_identity_hash)
        + u32(seat_id)
        + u64(valid_until_height)
    )


def activation_message(
    chain_id: bytes, hub_identity_hash: bytes, seat_id: int, valid_until_height: int
) -> bytes:
    return (
        label_prefix(c.ACTIVATION_LABEL)
        + _chain(chain_id)
        + _identity(hub_identity_hash)
        + u32(seat_id)
        + u64(valid_until_height)
    )


def mint_message(
    chain_id: bytes,
    hub_identity_hash: bytes,
    kind: int,
    seat_id: int,
    destination_escrow_id: bytes,
    valid_until_height: int,
) -> bytes:
    """One message for all three mints, separated by the kind byte it binds.

    Kinds 5 and 18 carry no seat, so their `seat_id` term is `u32(0)` and the
    kind byte is what separates them.
    """
    if kind not in c.CONFIRMABLE_MINTS:
        raise MalformedTransaction(f"kind {kind} is not a confirmable mint")
    return (
        label_prefix(c.MINT_CONFIRM_LABEL)
        + _chain(chain_id)
        + _identity(hub_identity_hash)
        + u8(kind)
        + u32(seat_id)
        + _identity(destination_escrow_id)
        + u64(valid_until_height)
    )


def posture_relax_message(
    chain_id: bytes,
    hub_identity_hash: bytes,
    escrow_id: bytes,
    posture: Posture,
    valid_until_height: int,
) -> bytes:
    return (
        label_prefix(c.POSTURE_RELAX_LABEL)
        + _chain(chain_id)
        + _identity(hub_identity_hash)
        + _identity(escrow_id)
        + u8(1 if posture.requires_confirmation else 0)
        + u64(posture.min_amount_atomic)
        + u32(posture.exempt_slot_mask)
        + u64(valid_until_height)
    )


def transfer_confirm_message(
    chain_id: bytes,
    hub_identity_hash: bytes,
    escrow_id: bytes,
    recipient_escrow_id: bytes,
    amount_atomic: int,
    valid_until_height: int,
) -> bytes:
    return (
        label_prefix(c.TRANSFER_CONFIRM_LABEL)
        + _chain(chain_id)
        + _identity(hub_identity_hash)
        + _identity(escrow_id)
        + _identity(recipient_escrow_id)
        + u64(amount_atomic)
        + u64(valid_until_height)
    )
