#!/usr/bin/env python3

"""A version-seven chain a real node will accept.

**Every recorded version-seven vector is signed with a stand-in.** The traces
say so outright: a signature is an eight-octet counter padded to 64 octets,
recorded in an oracle that verifies by exact-match lookup, so the model
implements no cryptography while every message-binding claim stays testable.
That is the right decision for a contract fixture and it is useless here.
`protocol-application-v7` opens its store through `open_sqlite_ledger_v7`, whose
verifier defaults to `protocol::v7::ed25519_verifier()`, so it would refuse every
recorded input as `invalid_signature`.

This module is the first version-seven fixture that **signs for real**. It is
version one's `tests/differential/cases.py` shape: derive keys from fixed seeds
through the pinned libsodium, build the transactions, and run the same octets
through the independent Python model to learn what each block produces. The
model needs no change for it — `execute_block` takes the signature oracle as an
argument and only ever calls `verify(public_key, message, signature)`, so a
libsodium-backed object is a drop-in for the recorded table.

**One transaction per block is a requirement, not a simplification.** A state
root commits to the whole block, so a fixture whose block holds four
transactions can only be reproduced by getting all four into one block in one
order, which broadcasting through a mempool does not give you.
"""

from __future__ import annotations

import pathlib
import sys
from dataclasses import dataclass

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
for _entry in (REPOSITORY, REPOSITORY / "tests" / "differential"):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

from pinned_sodium import Sodium  # noqa: E402
from simulation.economy_transition_v6 import messages  # noqa: E402
from simulation.economy_transition_v6.envelope import (  # noqa: E402
    Transaction,
    signed_bytes,
    signing_message,
    unsigned_bytes,
)
from simulation.economy_transition_v6.identity import escrow_id  # noqa: E402
from simulation.economy_transition_v7 import contract as c  # noqa: E402
from simulation.economy_transition_v7.block import execute_block  # noqa: E402
from simulation.economy_transition_v7 import genesis as g  # noqa: E402
from simulation.economy_transition_v7 import receipt as r  # noqa: E402
from simulation.economy_transition_v7.ledger import Ledger  # noqa: E402

# The trace genesis's figures, reused rather than chosen: a Founder Economy
# genesis with no allocation, no accounts, and a nonzero fee.
NETWORK_ID = 7
SUPPLY_LIMIT = 5_699_395_010_000_000_000
FIXED_FEE = 1_000
VALID_UNTIL = 10_000_000_000

ALICE_IDENTITY = bytes.fromhex("a1" * 32)
BOB_IDENTITY = bytes.fromhex("b1" * 32)
TRANSFER_AMOUNT = 1_000_000


class Signer:
    """The model's signature-oracle interface, backed by real Ed25519.

    `verify` is the only method the model calls. `sign` is this fixture's own,
    and it looks the seed up by public key so the builders below can ask for a
    signature the way the recorded traces ask their table for a stand-in.
    """

    def __init__(self, sodium: Sodium) -> None:
        self._sodium = sodium
        self._seeds: dict[bytes, bytes] = {}

    def derive(self, label: str) -> bytes:
        """A keypair from a label, so a fixture key is legible in a hex dump."""
        seed = label.encode("ascii").ljust(32, b"\x00")
        if len(seed) != 32:
            raise ValueError(f"key label {label!r} exceeds a 32-octet seed")
        public_key, _ = self._sodium.keypair(seed)
        self._seeds[public_key] = seed
        return public_key

    def sign(self, public_key: bytes, message: bytes) -> bytes:
        return self._sodium.sign(self._seeds[public_key], message)

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        return self._sodium.verify(public_key, message, signature)


@dataclass(frozen=True)
class Block:
    """One block, and everything a node must reproduce about it."""

    height: int
    raw_inputs: tuple[bytes, ...]
    transaction_root: bytes
    state_root: bytes
    block_id: bytes
    receipts: tuple[bytes, ...]


@dataclass(frozen=True)
class Chain:
    """A genesis and the contiguous blocks that follow it."""

    genesis: bytes
    chain_id: bytes
    genesis_root: bytes
    blocks: tuple[Block, ...]


def _genesis(verifier_key: bytes) -> g.Genesis:
    return g.Genesis(
        network_id=NETWORK_ID,
        supply_limit=SUPPLY_LIMIT,
        fixed_transfer_fee=FIXED_FEE,
        manifest_digest=bytes.fromhex(c.MANIFEST_DIGEST_HEX),
        verifier_key=verifier_key,
    )


def _build(
    signer: Signer,
    ledger: Ledger,
    kind: int,
    authority: bytes,
    nonce: int,
    body: dict,
) -> bytes:
    """One signed transaction. Registration is fee-exempt; everything else pays."""
    transaction = Transaction(
        kind=kind,
        scheme=c.KIND_SCHEME[kind],
        chain_id=ledger.chain_id,
        authority_public_key=authority,
        nonce=nonce,
        body=body,
        fee_limit=0 if kind == c.HUB_REGISTER else FIXED_FEE,
        valid_until_height=VALID_UNTIL,
    )
    unsigned = unsigned_bytes(transaction)
    signature = signer.sign(authority, signing_message(unsigned))
    return signed_bytes(transaction, signature)


def _register(
    signer: Signer,
    ledger: Ledger,
    identity: bytes,
    hub_key: bytes,
    signer_key: bytes,
    verifier_key: bytes,
) -> bytes:
    """A HUB registration, which pays the entry airdrop and charges no fee."""
    message = messages.registration_message(
        ledger.chain_id, identity, hub_key, signer_key, VALID_UNTIL
    )
    return _build(
        signer,
        ledger,
        c.HUB_REGISTER,
        hub_key,
        0,
        {
            "hub_identity_hash": identity,
            "first_signer_public_key": signer_key,
            "verifier_signature": signer.sign(verifier_key, message),
        },
    )


def _confirmed_transfer(
    signer: Signer,
    ledger: Ledger,
    identity: bytes,
    hub_key: bytes,
    signer_key: bytes,
    nonce: int,
    recipient: bytes,
    amount: int,
) -> bytes:
    """A confirmed transfer: the signer authorizes, the HUB key confirms."""
    escrow = escrow_id(identity, 0)
    message = messages.transfer_confirm_message(
        ledger.chain_id, identity, escrow, recipient, amount, VALID_UNTIL
    )
    return _build(
        signer,
        ledger,
        c.TRANSFER_VERIFIED,
        signer_key,
        nonce,
        {
            "recipient_escrow_id": recipient,
            "amount_atomic": amount,
            "hub_signature": signer.sign(hub_key, message),
        },
    )


def _run(ledger: Ledger, signer: Signer, raw: bytes) -> Block:
    """Execute one block holding exactly one transaction, and require it to succeed.

    A fixture whose transaction is refused is a fixture that proves nothing about
    a node, so the refusal is raised here rather than recorded.
    """
    outcome = execute_block(ledger, [raw], signer)
    if len(outcome.admissions) != 1 or outcome.admissions[0].code is not None:
        raise RuntimeError(
            f"fixture transaction was refused at admission: "
            f"{outcome.admissions[0].code}"
        )
    if (len(outcome.executed) != 1
            or outcome.executed[0].outcome.result != "SUCCESS"):
        raise RuntimeError(
            f"fixture transaction did not succeed: "
            f"{outcome.executed[0].outcome.result}"
        )
    return Block(
        height=outcome.height,
        raw_inputs=(raw,),
        transaction_root=bytes.fromhex(outcome.transaction_root),
        state_root=bytes.fromhex(outcome.resulting_state_root),
        block_id=bytes.fromhex(outcome.block_id),
        receipts=(r.encode(outcome.executed[0].receipt),),
    )


def build_chain(sodium: Sodium) -> Chain:
    """Three contiguous blocks: two registrations and a confirmed transfer.

    Two registrations because a transfer to an unregistered recipient is refused,
    and a transfer because it is the first block that moves value and charges the
    fee, so a node that agreed to the first two and not the third would be caught.
    """
    signer = Signer(sodium)
    verifier_key = signer.derive("verifier")
    alice_hub = signer.derive("alice-hub")
    alice_signer = signer.derive("alice-signer")
    bob_hub = signer.derive("bob-hub")
    bob_signer = signer.derive("bob-signer")

    genesis = _genesis(verifier_key)
    ledger = Ledger.from_genesis(genesis)
    genesis_root = bytes.fromhex(ledger.state_root())

    blocks = [
        _run(
            ledger,
            signer,
            _register(
                signer, ledger, ALICE_IDENTITY, alice_hub, alice_signer,
                verifier_key),
        ),
        _run(
            ledger,
            signer,
            _register(
                signer, ledger, BOB_IDENTITY, bob_hub, bob_signer, verifier_key),
        ),
        _run(
            ledger,
            signer,
            _confirmed_transfer(
                signer, ledger, ALICE_IDENTITY, alice_hub, alice_signer, 1,
                escrow_id(BOB_IDENTITY, 0), TRANSFER_AMOUNT),
        ),
    ]
    return Chain(
        genesis=g.encode(genesis),
        chain_id=g.chain_id(genesis),
        genesis_root=genesis_root,
        blocks=tuple(blocks),
    )
