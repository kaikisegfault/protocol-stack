#!/usr/bin/env python3

"""A version-ten chain a real node will accept, stamped by the engine.

This is `version_nine_chain`'s construction over the version-ten model, and
**its two reasons carry over unchanged.** The genesis is minted at run time,
because CometBFT `v0.39.4` stamps block 1 with the genesis time and C5 refuses
that stamp once it is 60 seconds old (ADR 0088). Each block is computed from the
stamp the engine chose, because a version-ten root still commits to the head's
timestamp, and nobody knows that stamp until the block commits.

**The transactions are the model's own builders, signed with real Ed25519.**
`simulation.economy_transition_v10.fixture.Builder` makes every body approval
over the whole transaction and signs the envelope over the finished bytes. It
is handed people whose keys `Signer` derives, and a `Signer` in place of the
model's counter tokens, which `protocol-application-v10` would refuse as
`invalid_signature`. So nothing here restates what version ten signs.

**Every transaction that carries a HUB proof expires exactly one slot after the
height it is built for**, which is the boundary the lifetime rule admits. So a
transaction built for height `h` is admitted at every height from `h` to one
slot past it. The single-node run knows each landing height and builds for it,
which exercises the boundary end to end. A multi-replica run cannot know where
a transaction lands, so it builds each one for the next height the model has
not seen.

**The keys are stand-ins, labelled as such.** The launch key, the dispute
authority, and the build authority are derived from their names. They say
nothing about who holds the real keys, which is founder-reserved.

`Signer` and `engine_millis` are version nine's, restated rather than
imported, so that ADR 0104's step 7 can delete `version_nine_chain` whole.
"""

from __future__ import annotations

import copy
import pathlib
import sys
from dataclasses import dataclass, replace

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
for _entry in (
    REPOSITORY,
    REPOSITORY / "tests" / "differential",
    pathlib.Path(__file__).resolve().parent,
):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

import version_ten_snapshot  # noqa: E402
from pinned_sodium import Sodium  # noqa: E402
from simulation.economy_transition_v6.identity import signer_id  # noqa: E402
from simulation.economy_transition_v10 import contract as c  # noqa: E402
from simulation.economy_transition_v10 import genesis as g  # noqa: E402
from simulation.economy_transition_v10.block import (  # noqa: E402
    execute_block,
    run_quiet_heights,
)
from simulation.economy_transition_v10.envelope import decode_signed  # noqa: E402
from simulation.economy_transition_v10.fixture import (  # noqa: E402
    Builder,
    Person,
)
from simulation.economy_transition_v10.ledger import Ledger  # noqa: E402

# The model fixture's figures, reused rather than chosen: no allocation, no
# accounts, and a nonzero fee.
NETWORK_ID = 10
SUPPLY_LIMIT = 5_699_395_010_000_000_000
FIXED_FEE = 1_000

# A version-ten receipt's result byte, at version nine's offset. Zero is SUCCESS.
RESULT_OFFSET = 39

ALICE_IDENTITY = bytes.fromhex("a1" * 32)
BOB_IDENTITY = bytes.fromhex("b1" * 32)
TRANSFER_AMOUNT = 1_000_000

# The seat the fixture sells. Zero is the first identifier the capacity admits.
SEAT_ID = 0

LIFETIME = c.APPROVAL_LIFETIME_BLOCKS


def engine_millis(seconds: int, nanos: int) -> int:
    """`consensus-application-v2`'s conversion, which version three inherits.

    `millis = seconds * 1000 + nanos / 1000000`, the division truncating. It is
    restated rather than taken from the bridge, because a root the model derives
    from this figure agrees with the node's only if the bridge derived the same
    one.
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
    """One block, and everything a node must reproduce about it."""

    height: int
    timestamp: int
    state_root: bytes
    block_id: bytes
    receipts: tuple[bytes, ...]


@dataclass(frozen=True)
class Step:
    """One block the fixture asks a chain for. `raw` is `None` for an empty one."""

    label: str
    raw: bytes | None


class Session:
    """A live version-ten ledger over a genesis stamped by the caller.

    The builders read the chain identity and the height they are told, and
    nothing else, so the script is fixed before the first block. `apply` and
    `apply_empty` are the only way the ledger moves.
    """

    def __init__(self, sodium: Sodium, genesis_timestamp: int) -> None:
        self._signer = Signer(sodium)
        self.launch_key = self._signer.derive("launch")
        self.dispute_authority_key = self._signer.derive("dispute-authority")
        self.build_authority_key = self._signer.derive("build-authority")
        self.alice = Person(
            ALICE_IDENTITY,
            self._signer.derive("alice-hub"),
            self._signer.derive("alice-signer"),
        )
        self.bob = Person(
            BOB_IDENTITY,
            self._signer.derive("bob-hub"),
            self._signer.derive("bob-signer"),
        )
        self.alice_machine_key = self._signer.derive("alice-machine")
        self.bob_machine_key = self._signer.derive("bob-machine")
        genesis = g.Genesis(
            network_id=NETWORK_ID,
            genesis_timestamp=genesis_timestamp,
            supply_limit=SUPPLY_LIMIT,
            fixed_transfer_fee=FIXED_FEE,
            manifest_digest=bytes.fromhex(c.MANIFEST_DIGEST_HEX),
            launch_key=self.launch_key,
            dispute_authority_key=self.dispute_authority_key,
            build_authority_key=self.build_authority_key,
        )
        self._ledger = Ledger.from_genesis(genesis)
        self._build = Builder(self._signer, self._ledger)
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

    def machine_key(self, seat_id: int) -> bytes | None:
        entry = self._ledger.machine_keys.get(seat_id)
        return None if entry is None else entry.machine_public_key

    # --- the transactions, each for the earliest height it may execute at --

    def register(self, who: Person, height: int) -> bytes:
        """Kind 10 under the launch key, which no seat holds."""
        return self._build.registration(
            who, c.LAUNCH_ATTESTER, self.launch_key, height + LIFETIME
        )

    def register_attested(self, who: Person, seat_id: int, height: int) -> bytes:
        """Kind 10 attested by `seat_id`'s machine, under the key it registered.

        The test holds every machine key it registers, so this signs for any
        keyed seat, and whether the chain accepts it is the chain's question.
        """
        machine = self.machine_key(seat_id)
        if machine is None:
            raise RuntimeError(f"seat {seat_id} has no machine key to sign with")
        return self._build.registration(who, seat_id, machine, height + LIFETIME)

    def buys_seat(
        self, who: Person, seat_id: int, nonce: int, height: int
    ) -> bytes:
        return self._build.purchase(who, seat_id, nonce, height + LIFETIME)

    def activates_seat(
        self, who: Person, seat_id: int, nonce: int, height: int
    ) -> bytes:
        return self._build.activation(who, seat_id, nonce, height + LIFETIME)

    def registers_machine(
        self, who: Person, seat_id: int, key: bytes, nonce: int, height: int
    ) -> bytes:
        """Kind 23: the build authority attests and the owner's HUB key approves."""
        return self._build.machine_registration(
            who, seat_id, key, nonce, height + LIFETIME,
            attester=self.build_authority_key,
        )

    def alice_buys_seat(self, nonce: int, height: int) -> bytes:
        return self.buys_seat(self.alice, SEAT_ID, nonce, height)

    def alice_activates_seat(self, nonce: int, height: int) -> bytes:
        return self.activates_seat(self.alice, SEAT_ID, nonce, height)

    def alice_registers_machine(self, nonce: int, height: int) -> bytes:
        return self.registers_machine(
            self.alice, SEAT_ID, self.alice_machine_key, nonce, height)

    def answers(
        self, who: Person, seat_id: int, challenge_height: int, nonce: int
    ) -> bytes:
        """Kind 20, which carries no HUB proof and so no lifetime."""
        return self._build.response(who, seat_id, challenge_height, nonce)

    def mints_seat(
        self, who: Person, seat_id: int, nonce: int, height: int
    ) -> bytes:
        """Kind 4: everything the seat has earned, into `who`'s first escrow."""
        return self._build.mint(
            who, c.MINT_NODE, nonce, height + LIFETIME, seat_id=seat_id)

    def mints_verified_user(self, who: Person, nonce: int, height: int) -> bytes:
        """Kind 18: every daily permission `who`'s enrollment has earned."""
        return self._build.mint(
            who, c.MINT_VERIFIED_USER, nonce, height + LIFETIME)

    def pays(
        self, who: Person, recipient: Person, nonce: int, height: int,
        amount: int = TRANSFER_AMOUNT,
    ) -> bytes:
        """Kind 19 from `who`'s first escrow, confirmed by its owner's HUB key."""
        return self._build.confirmed_transfer(
            who, recipient, amount, nonce, height + LIFETIME)

    def alice_pays_bob(
        self,
        nonce: int,
        height: int,
        amount: int = TRANSFER_AMOUNT,
        lifetime: int = LIFETIME,
    ) -> bytes:
        """Kind 19, confirmed by an approval of the whole transfer.

        `amount` exists for the caller that needs two transfers at one nonce:
        the same bytes twice never reach an application, because the engine's
        mempool discards a hash it has seen. `lifetime` exists for the caller
        that needs an approval to outlive its slot.
        """
        return self._build.confirmed_transfer(
            self.alice, self.bob, amount, nonce, height + lifetime
        )

    def resigned(self, raw: bytes, nonce: int) -> bytes:
        """`raw` under another nonce, its body and so its approval unchanged.

        This is the replay a network can be shown. The approval signed the
        whole transaction, nonce included, so it no longer verifies, and
        version ten refuses the transaction as `UNAUTHORIZED`.
        """
        transaction, _signature = decode_signed(raw)
        return self._build.sign(replace(transaction, nonce=nonce))

    def newcomer(self, name: str, identity: bytes) -> Person:
        """Someone the chain has not met, with keys derived from `name`."""
        return Person(
            identity,
            self._signer.derive(f"{name}-hub"),
            self._signer.derive(f"{name}-signer"),
        )

    def key(self, label: str) -> bytes:
        """Another key the test holds. The same label is the same key."""
        return self._signer.derive(label)

    # --- what an identity does with its own keys --------------------------

    def pays_from(
        self, who: Person, signer_key: bytes, recipient_escrow: bytes,
        nonce: int, height: int, amount: int = TRANSFER_AMOUNT,
    ) -> bytes:
        """Kind 19 by any signer key, confirmed by `who`'s HUB key.

        The key decides which escrow pays, because a signer belongs to one
        escrow. A key that is not, or is no longer, a signer is refused as
        `SIGNER_NOT_FOUND`.
        """
        return self._build.approved(
            replace(who, signer_key=signer_key), c.TRANSFER_VERIFIED, nonce,
            {"recipient_escrow_id": recipient_escrow, "amount_atomic": amount},
            height + LIFETIME,
        )

    def adds_signer(
        self, who: Person, escrow: bytes, signer_key: bytes, nonce: int,
        height: int, authority: bytes | None = None, lifetime: int = LIFETIME,
    ) -> bytes:
        """Kind 15, which the escrow it names pays for at that escrow's nonce.

        **This is also recovery** (ADR 0044): an identity whose every signer is
        gone adds a new one exactly this way. `authority` replaces the HUB key
        only to be refused, and `lifetime` exists for the caller that needs an
        approval to outlive its slot.
        """
        return self._signed_whole(
            c.SIGNER_ADD, authority or who.hub_key, nonce, {
                "hub_identity_hash": who.identity,
                "escrow_id": escrow,
                "signer_public_key": signer_key,
            }, height + lifetime)

    def revokes_signer(
        self, who: Person, escrow: bytes, signer_key: bytes, nonce: int,
        height: int,
    ) -> bytes:
        """Kind 16: the HUB key removes a signer, the last one included."""
        return self._signed_whole(c.SIGNER_REVOKE, who.hub_key, nonce, {
            "hub_identity_hash": who.identity,
            "escrow_id": escrow,
            "signer_id": signer_id(signer_key),
        }, height + LIFETIME)

    def creates_escrow(self, who: Person, nonce: int, height: int) -> bytes:
        """Kind 13: a keyless holding escrow, its fee paid by the first escrow."""
        return self._signed_whole(c.ESCROW_CREATE, who.hub_key, nonce, {
            "hub_identity_hash": who.identity,
            "fee_escrow_id": who.escrow,
        }, height + LIFETIME)

    def deletes_escrow(
        self, who: Person, target: bytes, nonce: int, height: int
    ) -> bytes:
        """Kind 14, which refuses an escrow still holding value."""
        return self._signed_whole(c.ESCROW_DELETE, who.hub_key, nonce, {
            "hub_identity_hash": who.identity,
            "target_escrow_id": target,
            "fee_escrow_id": who.escrow,
        }, height + LIFETIME)

    def _signed_whole(
        self, kind: int, authority: bytes, nonce: int, body: dict,
        valid_until: int,
    ) -> bytes:
        """Kinds 13 to 16 carry no body approval: the envelope is the proof."""
        return self._build.sign(
            self._build.transaction(kind, authority, nonce, body, valid_until))

    # --- the ledger -------------------------------------------------------

    def balance(self, escrow: bytes) -> int:
        return self._ledger.balance(escrow)

    def signers_of(self, escrow: bytes) -> set[bytes]:
        """The signer identifiers an escrow currently has, possibly none."""
        return {
            signer
            for signer, owner in self._ledger.registry.signers.items()
            if owner == escrow
        }

    def nonce(self, escrow: bytes) -> int:
        return self._ledger.nonce(escrow)

    def total_supply(self) -> int:
        """Every native unit issued so far, custody legs included."""
        return self._ledger.total_supply

    def machine_active(self, seat_id: int) -> bool:
        return self._ledger.machine_active(seat_id)

    def launch_retired(self) -> bool:
        return self._ledger.launch_retired_at is not None

    def founder_count(self, founder: bytes, window: int) -> int:
        return self._ledger.founder_count(founder, window)

    def seat_minted_through(self, seat_id: int) -> int:
        """The last window a seat has collected, or its activation window."""
        return self._ledger.seats[seat_id].minted_through_window

    def enrollment_minted_through(self, identity: bytes) -> int:
        return self._ledger.registry.enrollments[identity].minted_through_window

    def snapshot(self) -> bytes:
        """The head as the payload a store is seeded from (ADRs 0096 and 0108)."""
        return version_ten_snapshot.encode(self._ledger)

    def run_quiet(self, target_height: int, timestamp_of_height, respond) -> int:
        """Run the model alone to `target_height`, for a seed.

        This is the trace's fast path: a height with no input and no window
        opening is advanced without computing its root. So it is only for a
        history no network will be asked to reproduce, and it returns how many
        heights it ran.
        """
        count, _recorded = run_quiet_heights(
            self._ledger, target_height, timestamp_of_height, self._signer,
            respond,
        )
        return count

    def activations(self) -> dict[int, int]:
        """Activated seats and the heights they were activated at."""
        return self._ledger.activations()

    def apply(self, raw: bytes, timestamp: int) -> Block:
        """Execute one block holding this transaction, and require it to succeed.

        A fixture whose transaction is accidentally refused proves nothing about
        a node, so an unexpected refusal is raised here rather than recorded.
        """
        block = self._apply([raw], timestamp)
        if block.receipts[0][RESULT_OFFSET] != 0:
            raise RuntimeError(
                "fixture transaction did not succeed: result "
                f"{block.receipts[0][RESULT_OFFSET]}"
            )
        return block

    def apply_empty(self, timestamp: int) -> Block:
        """A block with no transaction, whose root depends on its stamp alone."""
        return self._apply([], timestamp)

    def apply_refused(self, raw: bytes, timestamp: int, expected: int) -> Block:
        """Execute one block whose transaction the contract must refuse by name.

        The code is passed in because two different defects both refuse, and
        only one refuses for the stated reason.
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

        The ledger is copied rather than advanced, because asking must not
        spend the height. A refused transaction writes no state and charges no
        fee, so a block whose only transaction was refused must land on exactly
        this root at the same height and stamp.
        """
        probe = copy.deepcopy(self._ledger)
        outcome = execute_block(probe, timestamp, [], self._signer)
        return self._block(outcome)

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
        return self._block(outcome)

    @staticmethod
    def _block(outcome) -> Block:
        return Block(
            height=outcome.height,
            timestamp=outcome.timestamp,
            state_root=bytes.fromhex(outcome.resulting_state_root),
            block_id=bytes.fromhex(outcome.block_id),
            receipts=tuple(outcome.receipts),
        )


def script(session: Session) -> tuple[Step, ...]:
    """Seven blocks: version nine's six, with a machine key before the transfer.

    **Two registrations under the launch key**, because a transfer to an
    unregistered recipient is refused and a version-ten registration needs an
    attester. **An empty block third**, whose root depends on nothing but its
    height and its stamp. A purchase and an activation, which write the seat
    table, then **kind 23**, which only an activated seat admits, and a transfer
    last, which moves value and charges the fee.

    Alice's nonces run from 1, because a registration's is zero and every later
    transaction of hers is signed by the one signer her escrow has.
    """
    return (
        Step("alice registers", session.register(session.alice, 1)),
        Step("bob registers", session.register(session.bob, 2)),
        Step("an empty block", None),
        Step("alice buys a seat", session.alice_buys_seat(1, 4)),
        Step("alice activates the seat", session.alice_activates_seat(2, 5)),
        Step("alice registers a machine key",
             session.alice_registers_machine(3, 6)),
        Step("alice pays bob", session.alice_pays_bob(4, 7)),
    )


# The restart falls after the empty block. The first block after it reads a
# registry entry recovered from SQLite, and the sixth verifies an attestation
# against the build authority key, which no root commits to: a store that
# reopened without it would commit the first five blocks and refuse that one.
BLOCKS_BEFORE_RESTART = 3
