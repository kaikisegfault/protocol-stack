#!/usr/bin/env python3

"""A version-nine chain a real node will accept, stamped by the engine.

Version eight's fixture froze its chain before any node ran: the genesis was
fixed, and every block's root followed from its height and its transactions.
ADR 0092 deleted it with the rest of version eight. **Neither holds at version nine, and this module exists
for the two reasons why.**

**The genesis is minted at run time.** CometBFT `v0.39.4` stamps block 1 with
the genesis time exactly, and C5 refuses that stamp once civil time is more than
60 seconds past it, in every round, for good. ADR 0088 records it. A genesis
with a recorded stamp therefore never produces a block, so `Session` takes the
stamp as an argument and its caller supplies a current one.

**Each block is computed from the stamp the engine chose.** A version-nine state
root commits to the head's timestamp, and after block 1 that timestamp is the
median of the previous height's precommit times, which nobody knows until the
block commits. So there is no frozen list of blocks here, only a live ledger that
`apply` advances with a stamp it is handed. The chain's *transactions* are fixed
in advance, because they bind the chain identity and nothing about any block.

**The signatures are real.** Every recorded version-nine vector is signed with a
stand-in that `protocol-application-v9` would refuse as `invalid_signature`,
which is version eight's reason for signing with the pinned libsodium and it
carries over unchanged. `Signer` is version eight's, restated rather than
imported, which is why ADR 0092's deletion of version eight's fixture did not
reach it.

**One transaction per block remains a requirement**, for version eight's reason:
a state root commits to the whole block, and a mempool will not put a chosen set
into one block in a chosen order.
"""

from __future__ import annotations

import copy
import pathlib
import sys
from dataclasses import dataclass

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
for _entry in (
    REPOSITORY,
    REPOSITORY / "tests" / "differential",
    pathlib.Path(__file__).resolve().parent,
):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

import version_nine_snapshot  # noqa: E402
from pinned_sodium import Sodium  # noqa: E402
from simulation.economy_transition_v6 import messages  # noqa: E402
from simulation.economy_transition_v6.identity import (  # noqa: E402
    escrow_id,
    signer_id,
)
from simulation.economy_transition_v9 import contract as c  # noqa: E402
from simulation.economy_transition_v9 import genesis as g  # noqa: E402
from simulation.economy_transition_v9.block import (  # noqa: E402
    execute_block,
    run_quiet_heights,
)
from simulation.economy_transition_v9.envelope import (  # noqa: E402
    Transaction,
    mint_message,
    signed_bytes,
    signing_message,
    unsigned_bytes,
)
from simulation.economy_transition_v9.ledger import Ledger  # noqa: E402

# The trace genesis's figures, reused rather than chosen: a Founder Economy
# genesis with no allocation, no accounts, and a nonzero fee.
NETWORK_ID = 9
SUPPLY_LIMIT = 5_699_395_010_000_000_000
FIXED_FEE = 1_000
VALID_UNTIL = 10_000_000_000

# A version-nine receipt's result byte. Zero is SUCCESS.
RESULT_OFFSET = 39

ALICE_IDENTITY = bytes.fromhex("a1" * 32)
BOB_IDENTITY = bytes.fromhex("b1" * 32)
TRANSFER_AMOUNT = 1_000_000

# Alice's first escrow, which registration creates, and the holding escrow her
# HUB key creates second. An escrow is derived from its owner and an index, so
# both are known before the chain exists.
ALICE_ESCROW = escrow_id(ALICE_IDENTITY, 0)
ALICE_HOLDING_ESCROW = escrow_id(ALICE_IDENTITY, 1)
BOB_ESCROW = escrow_id(BOB_IDENTITY, 0)

# The seat the fixture sells. Zero is the first identifier the capacity admits
# and carries no meaning beyond being inside it.
SEAT_ID = 0


def engine_millis(seconds: int, nanos: int) -> int:
    """`consensus-application-v2`'s conversion of an engine time, restated.

    `millis = seconds * 1000 + nanos / 1000000`, the division truncating. It is
    restated here rather than taken from the bridge because the bridge's
    conversion is part of what a run checks: a root the model derives from this
    figure agrees with the node's only if the bridge derived the same one.
    """
    if seconds < 0:
        raise ValueError("an engine time before the epoch has no millisecond count")
    if not 0 <= nanos <= 999_999_999:
        raise ValueError("an engine time's nanoseconds are out of range")
    return seconds * 1000 + nanos // 1_000_000


class Signer:
    """The model's signature-oracle interface, backed by real Ed25519."""

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
    """One block, and everything a node must reproduce about it.

    `timestamp` is an input here rather than an output: it is the stamp the
    engine committed, converted to milliseconds, and every other field is what
    the model says that stamp produces.
    """

    height: int
    timestamp: int
    raw_inputs: tuple[bytes, ...]
    transaction_root: bytes
    state_root: bytes
    block_id: bytes
    receipts: tuple[bytes, ...]


@dataclass(frozen=True)
class Step:
    """One block the fixture asks a chain for. `raw` is `None` for an empty one."""

    label: str
    raw: bytes | None


def _genesis(
    genesis_timestamp: int, verifier_key: bytes, dispute_authority_key: bytes
) -> g.Genesis:
    """Version eight's fields, with the stamp version nine adds.

    **The two keys are distinct**, as they are in the trace, because a fixture
    that passed the same key twice would agree with an implementation that read
    the wrong one.
    """
    return g.Genesis(
        network_id=NETWORK_ID,
        genesis_timestamp=genesis_timestamp,
        supply_limit=SUPPLY_LIMIT,
        fixed_transfer_fee=FIXED_FEE,
        manifest_digest=bytes.fromhex(c.MANIFEST_DIGEST_HEX),
        verifier_key=verifier_key,
        dispute_authority_key=dispute_authority_key,
    )


def _build(
    signer: Signer,
    chain_id: bytes,
    kind: int,
    authority: bytes,
    nonce: int,
    body: dict,
) -> bytes:
    """One signed transaction. Registration and a challenge response are
    fee-exempt, and admission requires an exempt kind's fee limit to be zero;
    everything else pays."""
    exempt = kind in (c.HUB_REGISTER, c.ADDED_FEE_EXEMPT_KIND)
    transaction = Transaction(
        kind=kind,
        scheme=c.KIND_SCHEME[kind],
        chain_id=chain_id,
        authority_public_key=authority,
        nonce=nonce,
        body=body,
        fee_limit=0 if exempt else FIXED_FEE,
        valid_until_height=VALID_UNTIL,
    )
    unsigned = unsigned_bytes(transaction)
    signature = signer.sign(authority, signing_message(unsigned))
    return signed_bytes(transaction, signature)


class Session:
    """A live version-nine ledger over a genesis stamped by the caller.

    The builders read the chain identity and nothing else, so a transaction is
    the same octets whatever block it lands in. `apply` and `apply_empty` are the
    only way the ledger moves, and both require the stamp the block carried.
    """

    def __init__(self, sodium: Sodium, genesis_timestamp: int) -> None:
        self._signer = Signer(sodium)
        self.verifier_key = self._signer.derive("verifier")
        self.dispute_authority_key = self._signer.derive("dispute-authority")
        self.alice_hub = self._signer.derive("alice-hub")
        self.alice_signer = self._signer.derive("alice-signer")
        self.bob_hub = self._signer.derive("bob-hub")
        self.bob_signer = self._signer.derive("bob-signer")
        # The keys a Founder's lifecycle adds and loses. None of them is ever a
        # registration key, so the chains the other runs build are unchanged.
        self.alice_second_signer = self._signer.derive("alice-second-signer")
        self.alice_holding_signer = self._signer.derive("alice-holding-signer")
        self.alice_recovered_signer = self._signer.derive("alice-recovered-signer")
        genesis = _genesis(
            genesis_timestamp, self.verifier_key, self.dispute_authority_key
        )
        self._ledger = Ledger.from_genesis(genesis)
        self.genesis_timestamp = genesis_timestamp
        self.genesis = g.encode(genesis)
        self.chain_id = g.chain_id(genesis)
        self.genesis_root = bytes.fromhex(self._ledger.state_root())

    @property
    def height(self) -> int:
        return self._ledger.height

    @property
    def timestamp(self) -> int:
        """The head's stamp: the last block's, or the genesis stamp before one."""
        return self._ledger.timestamp

    def state_root(self) -> bytes:
        return bytes.fromhex(self._ledger.state_root())

    def snapshot(self) -> bytes:
        """The head as the payload a store is seeded from (ADR 0096)."""
        return version_nine_snapshot.encode(self._ledger)

    # --- the transactions -------------------------------------------------

    def _register(self, identity: bytes, hub_key: bytes, signer_key: bytes) -> bytes:
        """A HUB registration, which pays the entry airdrop and charges no fee."""
        message = messages.registration_message(
            self.chain_id, identity, hub_key, signer_key, VALID_UNTIL
        )
        return _build(
            self._signer, self.chain_id, c.HUB_REGISTER, hub_key, 0,
            {
                "hub_identity_hash": identity,
                "first_signer_public_key": signer_key,
                "verifier_signature": self._signer.sign(self.verifier_key, message),
            },
        )

    def register_alice(self) -> bytes:
        return self._register(ALICE_IDENTITY, self.alice_hub, self.alice_signer)

    def register_bob(self) -> bytes:
        return self._register(BOB_IDENTITY, self.bob_hub, self.bob_signer)

    def alice_buys_seat(self, nonce: int) -> bytes:
        """Kind 2, unreferred: the signer pays and the HUB key approves the seat."""
        message = messages.purchase_message(
            self.chain_id, ALICE_IDENTITY, SEAT_ID, VALID_UNTIL
        )
        return _build(
            self._signer, self.chain_id, c.PURCHASE_SEAT, self.alice_signer, nonce,
            {
                "seat_id": SEAT_ID,
                "has_referrer": False,
                "referrer_escrow_id": bytes(32),
                "hub_signature": self._signer.sign(self.alice_hub, message),
            },
        )

    def alice_activates_seat(self, nonce: int) -> bytes:
        """Kind 3, which records the height the engine chose for it."""
        message = messages.activation_message(
            self.chain_id, ALICE_IDENTITY, SEAT_ID, VALID_UNTIL
        )
        return _build(
            self._signer, self.chain_id, c.ACTIVATE_SEAT, self.alice_signer, nonce,
            {
                "seat_id": SEAT_ID,
                "hub_signature": self._signer.sign(self.alice_hub, message),
            },
        )

    def alice_pays_bob(self, nonce: int, amount: int = TRANSFER_AMOUNT) -> bytes:
        """A confirmed transfer: the signer authorizes, the HUB key confirms.

        `amount` exists for the one caller that needs two transfers at one
        nonce: the same bytes twice never reach an application, because the
        engine's mempool discards a hash it has seen, so a stale nonce the
        kernel refuses has to be a *different* transaction.
        """
        return self.alice_pays(
            self.alice_signer, ALICE_ESCROW, BOB_ESCROW, nonce, amount
        )

    def alice_pays(
        self,
        signer_key: bytes,
        source: bytes,
        recipient: bytes,
        nonce: int,
        amount: int = TRANSFER_AMOUNT,
    ) -> bytes:
        """A confirmed transfer from any of Alice's escrows, by any signer key.

        The signer key decides which escrow pays, because a signer belongs to
        one escrow; `source` is what the HUB confirmation binds. A key that is
        not, or is no longer, a signer is refused as `SIGNER_NOT_FOUND`.
        """
        message = messages.transfer_confirm_message(
            self.chain_id, ALICE_IDENTITY, source, recipient, amount, VALID_UNTIL,
        )
        return _build(
            self._signer, self.chain_id, c.TRANSFER_VERIFIED, signer_key, nonce,
            {
                "recipient_escrow_id": recipient,
                "amount_atomic": amount,
                "hub_signature": self._signer.sign(self.alice_hub, message),
            },
        )

    # --- what an identity does with its own keys --------------------------

    def alice_adds_signer(
        self,
        escrow: bytes,
        signer_key: bytes,
        nonce: int,
        authority: bytes | None = None,
    ) -> bytes:
        """Kind 15: an identity admits a signer to one of its escrows.

        It is authorized by the identity's HUB key, never by a signer, and the
        escrow it names pays the fee at that escrow's nonce. **This is also
        recovery** (ADR 0044): an identity whose every signer is gone adds a new
        one exactly this way. `authority` replaces the HUB key only to be refused.
        """
        return _build(
            self._signer, self.chain_id, c.SIGNER_ADD, authority or self.alice_hub,
            nonce,
            {
                "hub_identity_hash": ALICE_IDENTITY,
                "escrow_id": escrow,
                "signer_public_key": signer_key,
            },
        )

    def alice_revokes_signer(
        self, escrow: bytes, signer_key: bytes, nonce: int
    ) -> bytes:
        """Kind 16: the HUB key removes a signer, the last one included."""
        return _build(
            self._signer, self.chain_id, c.SIGNER_REVOKE, self.alice_hub, nonce,
            {
                "hub_identity_hash": ALICE_IDENTITY,
                "escrow_id": escrow,
                "signer_id": signer_id(signer_key),
            },
        )

    def alice_creates_escrow(self, nonce: int) -> bytes:
        """Kind 13: a keyless holding escrow, its fee paid by the first escrow."""
        return _build(
            self._signer, self.chain_id, c.ESCROW_CREATE, self.alice_hub, nonce,
            {"hub_identity_hash": ALICE_IDENTITY, "fee_escrow_id": ALICE_ESCROW},
        )

    def alice_deletes_escrow(self, target: bytes, nonce: int) -> bytes:
        """Kind 14, which refuses an escrow still holding value."""
        return _build(
            self._signer, self.chain_id, c.ESCROW_DELETE, self.alice_hub, nonce,
            {
                "hub_identity_hash": ALICE_IDENTITY,
                "target_escrow_id": target,
                "fee_escrow_id": ALICE_ESCROW,
            },
        )

    # --- what a seat and an identity earn --------------------------------

    def alice_answers(self, challenge_height: int, nonce: int) -> bytes:
        """Kind 20: seat 0's machine answers one audit, at no fee.

        The answer is the trace's, 32 zero octets. A response advances the
        escrow's nonce, so a machine that answers is also moving the nonce its
        owner's next transaction must carry.
        """
        return _build(
            self._signer, self.chain_id, c.CHALLENGE_RESPONSE, self.alice_signer,
            nonce,
            {
                "seat_id": SEAT_ID,
                "challenge_height": challenge_height,
                "answer": bytes(c.ANSWER_BYTES),
            },
        )

    def mints_seat(
        self, identity: bytes, hub_key: bytes, signer_key: bytes,
        destination: bytes, nonce: int,
    ) -> bytes:
        """Kind 4: everything seat 0 has earned, into `destination`.

        The HUB confirmation is always carried, because a default posture
        requires one for every amount in every slot. The person minting is
        named in full so that someone other than the seat's owner can be
        refused.
        """
        message = mint_message(
            self.chain_id, identity, c.MINT_NODE, SEAT_ID, destination,
            VALID_UNTIL,
        )
        return _build(
            self._signer, self.chain_id, c.MINT_NODE, signer_key, nonce,
            {
                "seat_id": SEAT_ID,
                "destination_escrow_id": destination,
                "hub_signature": self._signer.sign(hub_key, message),
            },
        )

    def alice_mints_seat(self, nonce: int) -> bytes:
        return self.mints_seat(
            ALICE_IDENTITY, self.alice_hub, self.alice_signer, ALICE_ESCROW, nonce)

    def bob_mints_alices_seat(self, nonce: int) -> bytes:
        """Bob, with his own keys and his own escrow, minting seat 0."""
        return self.mints_seat(
            BOB_IDENTITY, self.bob_hub, self.bob_signer, BOB_ESCROW, nonce)

    def alice_mints_verified_user(self, nonce: int) -> bytes:
        """Kind 18: every daily permission her enrollment has earned."""
        message = mint_message(
            self.chain_id, ALICE_IDENTITY, c.MINT_VERIFIED_USER, 0, ALICE_ESCROW,
            VALID_UNTIL,
        )
        return _build(
            self._signer, self.chain_id, c.MINT_VERIFIED_USER, self.alice_signer,
            nonce,
            {
                "destination_escrow_id": ALICE_ESCROW,
                "hub_signature": self._signer.sign(self.alice_hub, message),
            },
        )

    # --- the ledger -------------------------------------------------------

    def nonce(self, escrow: bytes) -> int:
        return self._ledger.nonce(escrow)

    def seat_minted_through(self) -> int:
        """The last window seat 0 has collected, or its activation window."""
        return self._ledger.seats[SEAT_ID].minted_through_window

    def enrollment_minted_through(self, identity: bytes) -> int:
        return self._ledger.registry.enrollments[identity].minted_through_window

    def run_quiet(self, target_height: int, timestamp_of_height, respond) -> int:
        """Run the model alone to `target_height`, for a seed (ADR 0096).

        This is `run_quiet_heights`, the trace's fast path: a height with no
        input and no window opening is advanced without computing its root.
        So it is only for a history no network will be asked to reproduce, and
        it returns how many heights it ran.
        """
        count, _recorded = run_quiet_heights(
            self._ledger, target_height, timestamp_of_height, self._signer,
            respond,
        )
        return count

    def seats(self) -> dict[int, bool]:
        """Every seat sold, and whether it has been activated."""
        return {
            seat_id: seat.is_activated
            for seat_id, seat in self._ledger.seats.items()
        }

    def activations(self) -> dict[int, int]:
        """Activated seats and the heights they were activated at."""
        return self._ledger.activations()

    def balance(self, escrow: bytes) -> int:
        return self._ledger.balance(escrow)

    def signers_of(self, escrow: bytes) -> set[bytes]:
        """The signer identifiers an escrow currently has, possibly none."""
        return {
            signer
            for signer, owner in self._ledger.registry.signers.items()
            if owner == escrow
        }

    def apply(self, raw: bytes, timestamp: int) -> Block:
        """Execute one block holding this transaction, and require it to succeed.

        A fixture whose transaction is *accidentally* refused proves nothing
        about a node, so an unexpected refusal is raised here rather than
        recorded.
        """
        block = self._apply([raw], timestamp)
        if block.receipts[0][RESULT_OFFSET] != 0:
            raise RuntimeError("fixture transaction did not succeed")
        return block

    def apply_empty(self, timestamp: int) -> Block:
        """Close a block with no transaction, which moves the root regardless.

        A version-nine root commits to the height and the stamp, so an empty
        block's root is a function of those two and the state before it, and of
        nothing else. That makes it the sharpest end-to-end check of the stamp
        conversion there is: no transaction can be blamed for a difference.
        """
        return self._apply([], timestamp)

    def apply_refused(self, raw: bytes, timestamp: int, expected: int) -> Block:
        """Execute one block whose transaction the contract must refuse by name.

        A refusal is admitted, not dropped: only three things fail admission,
        all readable from the bytes, so everything a running network can be made
        to refuse arrives here with a receipt. The code is passed in because two
        different defects both refuse, and only one refuses for the stated
        reason.
        """
        block = self._apply([raw], timestamp)
        actual = block.receipts[0][RESULT_OFFSET]
        if actual != expected or actual == 0:
            raise RuntimeError(
                f"fixture transaction produced result {actual}, expected "
                f"{expected}"
            )
        return block

    def block_if_empty(self, timestamp: int) -> Block:
        """The block the next height would be with no transaction at `timestamp`.

        The ledger is deep-copied rather than advanced, because asking the
        question must not spend the height. A refused transaction writes no
        state and charges no fee, so a block whose only transaction was refused
        must land on exactly this root at the same height and stamp.
        """
        probe = copy.deepcopy(self._ledger)
        outcome = execute_block(probe, timestamp, [], self._signer)
        return self._block(outcome, [])

    def _apply(self, raw_inputs: list[bytes], timestamp: int) -> Block:
        outcome = execute_block(self._ledger, timestamp, raw_inputs, self._signer)
        if len(outcome.admissions) != len(raw_inputs):
            raise RuntimeError("the model dropped a raw input")
        for admission in outcome.admissions:
            if admission.code is not None:
                raise RuntimeError(
                    "fixture transaction was refused at admission: "
                    f"{admission.code}"
                )
        return self._block(outcome, raw_inputs)

    @staticmethod
    def _block(outcome, raw_inputs: list[bytes]) -> Block:
        return Block(
            height=outcome.height,
            timestamp=outcome.timestamp,
            raw_inputs=tuple(raw_inputs),
            transaction_root=bytes.fromhex(outcome.transaction_root),
            state_root=bytes.fromhex(outcome.resulting_state_root),
            block_id=bytes.fromhex(outcome.block_id),
            receipts=tuple(outcome.receipts),
        )


def script(session: Session) -> tuple[Step, ...]:
    """Six blocks: two registrations, an empty block, a seat, and a transfer.

    Two registrations because a transfer to an unregistered recipient is
    refused. **An empty block third**, because under version nine it is the one
    block whose root depends on nothing but its height and its stamp, and the
    engine closes one on its own three seconds after any block that moved the
    root. A purchase and an activation because they are the two transitions that
    write the seat table, and a transfer last because it moves value and charges
    the fee.

    **The order is the only one the contract admits.** A seat cannot be activated
    before it is bought, and both are refused before their owner is registered.
    Alice's transfer carries nonce 3 because a nonce is per signer and
    consecutive, and the two seat transactions are hers.
    """
    return (
        Step("alice registers", session.register_alice()),
        Step("bob registers", session.register_bob()),
        Step("an empty block", None),
        Step("alice buys a seat", session.alice_buys_seat(1)),
        Step("alice activates the seat", session.alice_activates_seat(2)),
        Step("alice pays bob", session.alice_pays_bob(3)),
    )


# The script is committed in two runs of one process each. The restart falls
# after the empty block, so the first block after it is a seat purchase that
# reads a registry entry recovered from SQLite rather than one held in memory.
BLOCKS_BEFORE_RESTART = 3
