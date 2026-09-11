#!/usr/bin/env python3

"""A version-eight chain a real node will accept.

**Every recorded version-eight vector is signed with a stand-in.** The traces
say so outright: a signature is an eight-octet counter padded to 64 octets,
recorded in an oracle that verifies by exact-match lookup, so the model
implements no cryptography while every message-binding claim stays testable.
That is the right decision for a contract fixture and it is useless here.
`protocol-application-v8` opens its store through `open_sqlite_ledger_v8`, whose
verifier defaults to `protocol::v8::ed25519_verifier()`, so it would refuse every
recorded input as `invalid_signature`.

This module is the first version-eight fixture that **signs for real**. It is
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

**Version eight adds a genesis field and an audit no devnet can reach.** The
genesis carries `dispute_authority_key`, distinct from the verifier key, so the
two are never the same octets by accident. The uptime pipeline runs at every
height under version eight, and it audits *in-scope* seats: this chain sells and
activates one, so the seat table is written twice and the audit still evaluates
nothing, because a seat is in scope only from the window after the one it
activated in and a window is 28,800 heights. Every height a chain begun at
genesis can plausibly reach lies in window 0. ADR 0071 records that wall and why
this fixture does not build around it; `check_the_audit_is_out_of_reach` in the
sibling test derives it rather than asserting it, so a changed constant is
reported as a changed constant.
"""

from __future__ import annotations

import copy
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
from simulation.economy_transition_v8 import contract as c  # noqa: E402
from simulation.economy_transition_v8.block import execute_block  # noqa: E402
from simulation.economy_transition_v8 import genesis as g  # noqa: E402
from simulation.economy_transition_v8 import receipt as r  # noqa: E402
from simulation.economy_transition_v8.ledger import Ledger  # noqa: E402

# The trace genesis's figures, reused rather than chosen: a Founder Economy
# genesis with no allocation, no accounts, and a nonzero fee.
NETWORK_ID = 8
SUPPLY_LIMIT = 5_699_395_010_000_000_000
FIXED_FEE = 1_000
VALID_UNTIL = 10_000_000_000

# A version-eight receipt's result byte. Zero is SUCCESS.
RESULT_OFFSET = 39

ALICE_IDENTITY = bytes.fromhex("a1" * 32)
BOB_IDENTITY = bytes.fromhex("b1" * 32)
TRANSFER_AMOUNT = 1_000_000

# The seat the fixture sells. Zero is the first identifier the capacity admits
# and carries no meaning beyond being inside it.
SEAT_ID = 0


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
    """A genesis and the contiguous blocks that follow it.

    The two genesis keys are carried out so a caller can state that they are
    two keys. Nothing else in this fixture would notice if they were one.

    `activations` is the seat table's activated half at the end of the chain,
    carried out because the heights the seat transitions recorded are not
    recoverable from the frozen blocks and every question about the audit is
    asked relative to one. It is a mapping rather than a tuple of pairs because
    both callers index it, which costs this frozen record its generated
    `__hash__`; nothing hashes it.
    """

    genesis: bytes
    chain_id: bytes
    genesis_root: bytes
    verifier_key: bytes
    dispute_authority_key: bytes
    blocks: tuple[Block, ...]
    activations: dict[int, int]


def _genesis(verifier_key: bytes, dispute_authority_key: bytes) -> g.Genesis:
    """The eight version-seven fields and the one version eight adds.

    **The two keys are distinct here as they are in the trace**, because a
    fixture that passed the same key twice would agree with an implementation
    that read the wrong one.
    """
    return g.Genesis(
        network_id=NETWORK_ID,
        supply_limit=SUPPLY_LIMIT,
        fixed_transfer_fee=FIXED_FEE,
        manifest_digest=bytes.fromhex(c.MANIFEST_DIGEST_HEX),
        verifier_key=verifier_key,
        dispute_authority_key=dispute_authority_key,
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


def _purchase(
    signer: Signer,
    ledger: Ledger,
    identity: bytes,
    hub_key: bytes,
    signer_key: bytes,
    seat_id: int,
    nonce: int,
) -> bytes:
    """Kind 2, unreferred: the signer pays, the HUB key approves the seat.

    `has_referrer` is false and `referrer_escrow_id` is 32 zero octets, which is
    the encoding rather than a convention — the field is fixed-width and present
    either way, so a decoder that read it when it should not would be caught by
    the root rather than by a shorter transaction.
    """
    message = messages.purchase_message(
        ledger.chain_id, identity, seat_id, VALID_UNTIL
    )
    return _build(
        signer,
        ledger,
        c.PURCHASE_SEAT,
        signer_key,
        nonce,
        {
            "seat_id": seat_id,
            "has_referrer": False,
            "referrer_escrow_id": bytes(32),
            "hub_signature": signer.sign(hub_key, message),
        },
    )


def _activate(
    signer: Signer,
    ledger: Ledger,
    identity: bytes,
    hub_key: bytes,
    signer_key: bytes,
    seat_id: int,
    nonce: int,
) -> bytes:
    """Kind 3, which records the height and is the only way into the audit.

    Activation is what puts a seat in a window's scope, so the height this lands
    at is the one every later uptime question is asked relative to. A consensus
    engine chooses it, which is exactly why the fixture reads it back out of the
    ledger rather than predicting it.
    """
    message = messages.activation_message(
        ledger.chain_id, identity, seat_id, VALID_UNTIL
    )
    return _build(
        signer,
        ledger,
        c.ACTIVATE_SEAT,
        signer_key,
        nonce,
        {"seat_id": seat_id, "hub_signature": signer.sign(hub_key, message)},
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


class Session:
    """A live version-eight ledger, advanced one block at a time.

    A consensus engine decides how many blocks a chain has, not this fixture. A
    frozen list of blocks is enough for a single node driven one transaction at
    a time, and it is not enough for a network that may close a block this
    fixture did not ask for: **an empty version-eight block still moves the
    state root**, because the root commits to the height. So the ledger stays
    live and the caller advances it to whatever the chain did.
    """

    def __init__(self, sodium: Sodium) -> None:
        self._signer = Signer(sodium)
        self.verifier_key = self._signer.derive("verifier")
        self.dispute_authority_key = self._signer.derive("dispute-authority")
        self.alice_hub = self._signer.derive("alice-hub")
        self.alice_signer = self._signer.derive("alice-signer")
        self.bob_hub = self._signer.derive("bob-hub")
        self.bob_signer = self._signer.derive("bob-signer")
        genesis = _genesis(self.verifier_key, self.dispute_authority_key)
        self._ledger = Ledger.from_genesis(genesis)
        self.genesis = g.encode(genesis)
        self.chain_id = g.chain_id(genesis)
        self.genesis_root = bytes.fromhex(self._ledger.state_root())

    @property
    def height(self) -> int:
        return self._ledger.height

    def state_root(self) -> bytes:
        return bytes.fromhex(self._ledger.state_root())

    def register_alice(self) -> bytes:
        return _register(
            self._signer, self._ledger, ALICE_IDENTITY, self.alice_hub,
            self.alice_signer, self.verifier_key)

    def register_bob(self) -> bytes:
        return _register(
            self._signer, self._ledger, BOB_IDENTITY, self.bob_hub,
            self.bob_signer, self.verifier_key)

    def alice_buys_seat(self, nonce: int, seat_id: int = SEAT_ID) -> bytes:
        return _purchase(
            self._signer, self._ledger, ALICE_IDENTITY, self.alice_hub,
            self.alice_signer, seat_id, nonce)

    def alice_activates_seat(self, nonce: int, seat_id: int = SEAT_ID) -> bytes:
        return _activate(
            self._signer, self._ledger, ALICE_IDENTITY, self.alice_hub,
            self.alice_signer, seat_id, nonce)

    def alice_pays_bob(self, nonce: int, amount: int = TRANSFER_AMOUNT) -> bytes:
        return _confirmed_transfer(
            self._signer, self._ledger, ALICE_IDENTITY, self.alice_hub,
            self.alice_signer, nonce, escrow_id(BOB_IDENTITY, 0), amount)

    def seats(self) -> dict[int, bool]:
        """Every seat the chain has sold, and whether it has been activated.

        A caller that wants to state "the purchase wrote a seat and the
        activation did not write a second one" needs the table rather than the
        roots, and the roots alone cannot say which of the two happened.
        """
        return {
            seat_id: seat.is_activated
            for seat_id, seat in self._ledger.seats.items()
        }

    def activations(self) -> dict[int, int]:
        """Activated seats and the heights they were activated at.

        This is the model's own accessor, the one `derive_schedule` is handed at
        every height, so a caller asking what the audit will measure is asking
        the audit's own input rather than a parallel record of it.
        """
        return self._ledger.activations()

    def apply_empty(self) -> Block:
        """Close a block the fixture did not fill, which a chain may do."""
        return self._apply([])

    def apply(self, raw: bytes) -> Block:
        """Execute one block holding this transaction, and require it to succeed.

        A fixture whose transaction is *accidentally* refused proves nothing
        about a node, so an unexpected refusal is raised here rather than
        recorded. `apply_refused` is the deliberate case.
        """
        block = self._apply([raw])
        if block.receipts[0][RESULT_OFFSET] != 0:
            raise RuntimeError("fixture transaction did not succeed")
        return block

    def apply_refused(self, raw: bytes, expected: int) -> Block:
        """Execute one block whose transaction the contract must refuse by name.

        **A refusal is admitted, not dropped.** `ledger-transition-v1` omits an
        admission failure from execution and from the transaction root
        entirely — it produces no receipt at all — while every *admitted*
        transaction appends a receipt whether it succeeded or failed. Only three
        things fail admission, all readable from the bytes without touching
        state, so everything a running network can be made to refuse arrives
        here with a receipt. This method requires that: admitted, and refused
        with the exact code asked for.

        The code is passed in rather than merely asserted nonzero because "it
        was refused" is not the claim worth making. Two different defects both
        refuse; only one of them refuses *for the stated reason*, and a test
        that accepts any nonzero code would pass while the kernel refused for
        the wrong one.
        """
        block = self._apply([raw])
        actual = block.receipts[0][RESULT_OFFSET]
        if actual != expected:
            raise RuntimeError(
                f"fixture transaction produced result {actual}, expected "
                f"{expected}"
            )
        if actual == 0:
            raise RuntimeError("a refusal cannot be SUCCESS")
        return block

    def root_if_empty(self) -> bytes:
        """The state root the *next* height would produce with no transaction.

        This exists for one claim and it is the sharpest one a refusal can make.
        Every non-success result writes no state and charges no fee, so a block
        whose only transaction was refused must leave the chain in the state an
        empty block would have — the root moves, because it commits to the
        height, and it must move to exactly that value and no other.

        The live ledger is deep-copied rather than advanced, because asking the
        question must not answer it: a session that closed a block to find out
        what the block would be has already spent the height.
        """
        probe = copy.deepcopy(self._ledger)
        outcome = execute_block(probe, [], self._signer)
        return bytes.fromhex(outcome.resulting_state_root)

    def _apply(self, raw_inputs: list[bytes]) -> Block:
        outcome = execute_block(self._ledger, raw_inputs, self._signer)
        if len(outcome.admissions) != len(raw_inputs):
            raise RuntimeError("the model dropped a raw input")
        for admission in outcome.admissions:
            if admission.code is not None:
                raise RuntimeError(
                    "fixture transaction was refused at admission: "
                    f"{admission.code}"
                )
        return Block(
            height=outcome.height,
            raw_inputs=tuple(raw_inputs),
            transaction_root=bytes.fromhex(outcome.transaction_root),
            state_root=bytes.fromhex(outcome.resulting_state_root),
            block_id=bytes.fromhex(outcome.block_id),
            receipts=tuple(
                r.encode(executed.receipt) for executed in outcome.executed
            ),
        )


def build_chain(sodium: Sodium) -> Chain:
    """Five contiguous blocks: two registrations, a seat, and a transfer.

    Two registrations because a transfer to an unregistered recipient is
    refused. A purchase and an activation because they are the two transitions
    that write the seat table, and until this fixture grew them no consensus
    engine in this repository had ever executed either one: they existed in the
    C++ kernel, in the Python model, and in recorded vectors, and nowhere in
    between. And a transfer last because it is the block that moves value and
    charges the fee, so a node that agreed to the first four and not the fifth
    would still be caught.

    **The order is not arbitrary.** A seat cannot be activated before it is
    bought, and both are refused before its owner is registered, so the sequence
    is the only one the contract admits. Alice's transfer therefore carries
    nonce 3 rather than nonce 1: a nonce is per-signer and consecutive, and the
    two seat transactions are hers.
    """
    session = Session(sodium)
    blocks = (
        session.apply(session.register_alice()),
        session.apply(session.register_bob()),
        session.apply(session.alice_buys_seat(1)),
        session.apply(session.alice_activates_seat(2)),
        session.apply(session.alice_pays_bob(3)),
    )
    return Chain(
        genesis=session.genesis,
        chain_id=session.chain_id,
        genesis_root=session.genesis_root,
        verifier_key=session.verifier_key,
        dispute_authority_key=session.dispute_authority_key,
        blocks=blocks,
        activations=session.activations(),
    )
