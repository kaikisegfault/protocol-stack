"""The recorded version-nine transition trace: a chain that settles a month.

Version nine changes no carried transaction and no settlement step version seven
fixed, so this trace does not re-record what
`test-vectors/economy-transition-v8-execution.txt` already fixes about the
measurement, the winner rule, or the mint walk. It records what version nine
changes, which is **what a month is worth**:

1. **settled** — two unreferred machines run a window the chain measures. One
   answers every audit and one answers none. When the window that opens the next
   month is assigned, the closing month is ranked on the uptime accumulated
   *during it*, the whole pool balance goes to the better machine as a claim, and
   the machine mints it with kind 22. **It is the first time in this repository
   that anything takes value out of the unreferred pool**, which has accrued
   since `economy-transition-v3` and has never paid anybody.
2. **halted** — the same chain, with its stamps jumped across three whole months
   between two window openings. One assignment closes one month and skips three,
   in a single pass, and the vectors compare the result against an explicit
   per-index loop over the same state.
3. **restart** — four heights contiguous from genesis, with every block's
   commitments recorded. It records nothing about a month; it exists for the
   layers above the kernel, which cannot replay either chain above because each
   jumps from height 2 to the activation height.

**The chain runs at ninety seconds a block and that is a fixture choice with a
reason.** At the commit target a window is exactly one day, so a month is about
thirty windows and 864,000 heights — more than a recorded trace can run. At
ninety seconds a window is exactly thirty days, so each window opens in a new
month and a settlement is reachable in three. Nothing in the contract bounds the
block rate from above, which `economy-transition-v9` states outright, and the
figure a seat accumulates is `credited_slots * SLOT_SECONDS` — a function of
**heights** — so a slower chain changes when a month closes and changes nothing
about what a machine earned.

**No signature is computed anywhere.** A stand-in is an eight-octet counter
padded to 64 octets, recorded in the oracle against the exact key and message it
authorizes, so a signature presented over any other message is simply absent from
the table.
"""

from __future__ import annotations

from simulation.calendar.civil import days_from_civil
from simulation.economy_transition_v6.trace import (
    Scenario,
    Signatures,
    Step,
    _register,
)
from simulation.economy_transition_v7.trace import (
    ALICE_ESCROW,
    ALICE_IDENTITY,
    ALICE_KEY,
    ALICE_SIGNER_KEY,
    BOB_ESCROW,
    BOB_IDENTITY,
    BOB_KEY,
    BOB_SIGNER_KEY,
)
from simulation.economy_transition_v8.trace import Responder as ResponderV8

from . import contract as c
from .block import BlockOutcome, InvalidBlock, execute_block, run_quiet_heights
from .envelope import Transaction, mint_message, signed_bytes, signing_message
from .envelope import unsigned_bytes
from .genesis import Genesis
from .ledger import Ledger

__all__ = [
    "ALICE_SEAT",
    "BOB_SEAT",
    "GENESIS_MILLIS",
    "HALT_HEIGHT",
    "HALTED_TARGET_HEIGHT",
    "HALT_MILLIS",
    "MILLIS_PER_BLOCK",
    "SETTLEMENT_HEIGHT",
    "build",
    "genesis",
    "halted_scenario",
    "restart_scenario",
    "settled_scenario",
    "timestamp_of_height",
]

SUPPLY_LIMIT = 5_699_395_010_000_000_000
FIXED_FEE = 1_000
NETWORK_ID = 9

VERIFIER_KEY = bytes.fromhex("55" * 32)
DISPUTE_AUTHORITY_KEY = bytes.fromhex("d8" * 32)

VALID_UNTIL = 10_000_000_000

ALICE_SEAT = 0
BOB_SEAT = 1

# Ninety seconds a block, so a window of 28,800 heights is exactly thirty days
# and every window opens in a new month.
MILLIS_PER_BLOCK = 90_000

# 2026-01-15T00:00:00Z. A mid-month genesis, so window 0 opens in January, window
# 1 in February, window 2 in March, and so on: each window opens in a month of
# its own, which is what makes a settlement reachable inside three windows.
GENESIS_MILLIS = days_from_civil(2026, 1, 15) * 86_400_000

# Both seats activate near the end of window 0, so window 1 is the first window
# either is in scope for.
ACTIVATION_HEIGHT = c.CYCLE_BLOCKS - 10
MEASURED_WINDOW = 1

# Window 1's assignment is due at the first height of window 3, and that is the
# block in which February closes and the pool first pays.
SETTLEMENT_HEIGHT = (MEASURED_WINDOW + c.ASSIGNMENT_LAG_WINDOWS + 1) * c.CYCLE_BLOCKS
MINT_HEIGHT = SETTLEMENT_HEIGHT + 1

# The halt sits between window 2's opening and window 3's, so window 3 opens
# three months later than it otherwise would and its assignment closes one month
# while skipping three.
HALT_HEIGHT = 2 * c.CYCLE_BLOCKS + 1
HALT_MILLIS = 90 * 86_400_000

# The jump shows up one assignment after the window that carries it: window 3
# opens three months late, and it is *assigned* at the first height of window 5.
# The halted chain therefore runs one window past the settled one.
HALTED_TARGET_HEIGHT = SETTLEMENT_HEIGHT + c.CYCLE_BLOCKS


def timestamp_of_height(height: int) -> int:
    """The chain's stamp at a height, at ninety seconds a block."""
    return GENESIS_MILLIS + height * MILLIS_PER_BLOCK


def halted_timestamp_of_height(height: int) -> int:
    """The same chain, down for ninety days partway through window 2.

    A halt is a discontinuity in this function and nothing else. Heights stay
    consecutive, because a network that is down produces no heights at all and
    resumes at the one it stopped at; what moves is the wall.
    """
    stamp = timestamp_of_height(height)
    return stamp + HALT_MILLIS if height >= HALT_HEIGHT else stamp


def genesis() -> Genesis:
    """A Founder Economy genesis: no allocation, no accounts, a nonzero fee."""
    return Genesis(
        network_id=NETWORK_ID,
        genesis_timestamp=GENESIS_MILLIS,
        supply_limit=SUPPLY_LIMIT,
        fixed_transfer_fee=FIXED_FEE,
        manifest_digest=bytes.fromhex(c.MANIFEST_DIGEST_HEX),
        verifier_key=VERIFIER_KEY,
        dispute_authority_key=DISPUTE_AUTHORITY_KEY,
    )


def build(
    signatures: Signatures,
    ledger: Ledger,
    kind: int,
    authority: bytes,
    nonce: int,
    body: dict,
    valid_until: int = VALID_UNTIL,
    fee_limit: int = FIXED_FEE,
) -> bytes:
    """Version eight's builder over version nine's envelope, unchanged in shape."""
    exempt = kind in (c.HUB_REGISTER, c.ADDED_FEE_EXEMPT_KIND)
    transaction = Transaction(
        kind=kind,
        scheme=c.KIND_SCHEME[kind],
        chain_id=ledger.chain_id,
        authority_public_key=authority,
        nonce=nonce,
        body=body,
        fee_limit=0 if exempt else fee_limit,
        valid_until_height=valid_until,
    )
    unsigned = unsigned_bytes(transaction)
    return signed_bytes(transaction, signatures.sign(authority, signing_message(unsigned)))


# --- the builders -----------------------------------------------------------


def _purchase(
    signatures: Signatures,
    ledger: Ledger,
    identity: bytes,
    hub_key: bytes,
    signer_key: bytes,
    seat_id: int,
    nonce: int,
) -> Step:
    """An **unreferred** seat, which is the whole point of this trace.

    A referred seat routes its referral leg to its referrer; an unreferred one
    routes it to the pool. Both seats here are unreferred, so every unit the pool
    holds is one the chain created for a machine nobody referred.
    """
    from simulation.economy_transition_v6 import messages

    message = messages.purchase_message(ledger.chain_id, identity, seat_id, VALID_UNTIL)
    return Step(
        f"seat_{seat_id}_purchased",
        build(
            signatures, ledger, c.PURCHASE_SEAT, signer_key, nonce,
            {
                "seat_id": seat_id,
                "has_referrer": False,
                "referrer_escrow_id": bytes(32),
                "hub_signature": signatures.sign(hub_key, message),
            },
        ),
    )


def _activate(
    signatures: Signatures,
    ledger: Ledger,
    identity: bytes,
    hub_key: bytes,
    signer_key: bytes,
    seat_id: int,
    nonce: int,
) -> Step:
    from simulation.economy_transition_v6 import messages

    message = messages.activation_message(
        ledger.chain_id, identity, seat_id, VALID_UNTIL
    )
    return Step(
        f"seat_{seat_id}_activated",
        build(
            signatures, ledger, c.ACTIVATE_SEAT, signer_key, nonce,
            {"seat_id": seat_id, "hub_signature": signatures.sign(hub_key, message)},
        ),
    )


def _mint_pool(
    signatures: Signatures,
    ledger: Ledger,
    identity: bytes,
    hub_key: bytes,
    signer_key: bytes,
    seat_id: int,
    destination: bytes,
    nonce: int,
    label: str = "winner_mints_the_pool",
    confirm: bool = True,
) -> Step:
    """Kind 22, with the destination's posture confirmation it requires.

    A default posture requires a confirmation above its minimum amount, and a
    month's pool is far above it, so this mint carries a real HUB signature over
    version six's `mint-confirm` message — the same message kinds 4, 5 and 18
    carry, separated from theirs by the kind byte it binds.

    `confirm=False` presents the 64 zero octets instead, which is the shape a
    mint takes when no confirmation is required. Against a posture that requires
    one it is `BIOMETRIC_REQUIRED`, and the scenario records both on the same
    nonce so the refusal is shown to write nothing.
    """
    signature = bytes(64)
    if confirm:
        signature = signatures.sign(
            hub_key,
            mint_message(
                ledger.chain_id, identity, c.MINT_POOL, seat_id, destination,
                VALID_UNTIL,
            ),
        )
    return Step(
        label,
        build(
            signatures, ledger, c.MINT_POOL, signer_key, nonce,
            {
                "seat_id": seat_id,
                "destination_escrow_id": destination,
                "hub_signature": signature,
            },
        ),
    )


# --- running -----------------------------------------------------------------


def _run(
    scenario: Scenario,
    signatures: Signatures,
    steps: list[Step],
    timestamp: int,
    **options,
) -> BlockOutcome:
    block = execute_block(
        scenario.ledger, timestamp, [step.raw for step in steps],
        signatures.oracle, **options,
    )
    scenario.blocks.append(block)
    scenario.labels.append([step.label for step in steps if step.admits])
    scenario.raw_inputs.append(len(steps))
    for step, admission in zip(steps, block.admissions):
        if not step.admits:
            scenario.rejected[step.label] = admission.code
    return block


class Responder(ResponderV8):
    """Version eight's responder over a version-nine ledger.

    Subclassed rather than rewritten because a responder answers challenges and
    version nine changes nothing about a challenge. What it needs is version
    nine's builder for the response body, which is the one method overridden.
    """

    def __call__(self, height: int, issued: list[int]) -> list[bytes]:
        if self._seat_id not in issued:
            return []
        self.challenged.append(height)
        if self._silent:
            return []
        self.answered.append(height)
        return [
            build(
                self._signatures, self._ledger, c.CHALLENGE_RESPONSE,
                self._signer_key, self._ledger.nonce(self._escrow) + 1,
                {
                    "seat_id": self._seat_id,
                    "challenge_height": height,
                    "answer": bytes(c.ANSWER_BYTES),
                },
            )
        ]


def _seated_chain(
    signatures: Signatures, name: str, stamp
) -> tuple[Scenario, Responder, Responder]:
    """Register both people, sell each an unreferred seat, and activate both.

    The shorthand `advance_to` is used exactly once and only before any
    activation, which is the only stretch of a version-nine chain where a block
    with no transactions really does change height and nothing else.
    """
    scenario = Scenario(name=name, ledger=Ledger.from_genesis(genesis()))
    ledger = scenario.ledger

    _run(scenario, signatures, [
        Step("alice_registers", _register(
            signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY)),
        Step("bob_registers", _register(
            signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY)),
    ], stamp(ledger.height + 1))
    _run(scenario, signatures, [
        _purchase(signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
                  ALICE_SEAT, 1),
        _purchase(signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY,
                  BOB_SEAT, 1),
    ], stamp(ledger.height + 1))
    scenario.skipped_blocks = ledger.advance_to(
        ACTIVATION_HEIGHT - 1, stamp(ACTIVATION_HEIGHT - 1)
    )
    # The root the shorthand leaves behind, read before the next block consumes
    # it. It is the only observable consequence of `advance_to` carrying the
    # timestamp or not: the block that follows sets its own stamp, so a
    # shorthand that dropped it would differ here and nowhere else.
    scenario.notes["root_after_the_shorthand"] = ledger.state_root()
    scenario.notes["timestamp_after_the_shorthand"] = ledger.timestamp
    _run(scenario, signatures, [
        _activate(signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
                  ALICE_SEAT, 2),
        _activate(signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY,
                  BOB_SEAT, 2),
    ], stamp(ledger.height + 1))
    alice = Responder(
        signatures, ledger, ALICE_SEAT, ALICE_ESCROW, ALICE_SIGNER_KEY
    )
    bob = Responder(
        signatures, ledger, BOB_SEAT, BOB_ESCROW, BOB_SIGNER_KEY, silent=True
    )
    return scenario, alice, bob


def _both(alice: Responder, bob: Responder):
    """One responder driving two machines, because `run_quiet_heights` takes one."""

    def respond(height: int, issued: list[int]) -> list[bytes]:
        return list(alice(height, issued)) + list(bob(height, issued))

    return respond


def settled_scenario() -> tuple[Scenario, Signatures]:
    """February closes, Alice wins the pool, and she mints it."""
    signatures = Signatures()
    scenario, alice, bob = _seated_chain(signatures, "settled", timestamp_of_height)
    ledger = scenario.ledger

    quiet, recorded = run_quiet_heights(
        ledger, SETTLEMENT_HEIGHT, timestamp_of_height, signatures.oracle,
        _both(alice, bob),
    )
    scenario.notes["quiet_heights"] = quiet
    scenario.notes["audit_blocks"] = recorded
    scenario.notes["alice_challenged"] = len(alice.challenged)
    scenario.notes["alice_answered"] = len(alice.answered)
    scenario.notes["bob_challenged"] = len(bob.challenged)
    scenario.notes["bob_answered"] = len(bob.answered)
    scenario.notes["settlement_block"] = recorded[-1]

    winner = recorded[-1].settled.winners[0]
    nonce = ledger.nonce(ALICE_ESCROW) + 1
    # Both on the same nonce and in the same block: the refusal writes nothing,
    # so the mint that follows it is offered the sequence number the refusal did
    # not consume.
    _run(scenario, signatures, [
        _mint_pool(
            signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
            winner, ALICE_ESCROW, nonce,
            label="an_unconfirmed_mint_is_refused", confirm=False,
        ),
        _mint_pool(
            signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
            winner, ALICE_ESCROW, nonce,
        ),
    ], timestamp_of_height(ledger.height + 1))
    _run(scenario, signatures, [
        _mint_pool(
            signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
            winner, ALICE_ESCROW, ledger.nonce(ALICE_ESCROW) + 1,
            label="a_second_mint_collects_nothing",
        ),
        _mint_pool(
            signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY,
            ALICE_SEAT, BOB_ESCROW, ledger.nonce(BOB_ESCROW) + 1,
            label="a_stranger_cannot_mint_another_seats_award",
        ),
    ], timestamp_of_height(ledger.height + 1))
    scenario.notes["winner"] = winner
    return scenario, signatures


def halted_scenario() -> tuple[Scenario, Signatures]:
    """The same chain, down for ninety days, closing one month and skipping three."""
    signatures = Signatures()
    scenario, alice, bob = _seated_chain(
        signatures, "halted", halted_timestamp_of_height
    )
    ledger = scenario.ledger

    quiet, recorded = run_quiet_heights(
        ledger, HALTED_TARGET_HEIGHT, halted_timestamp_of_height, signatures.oracle,
        _both(alice, bob),
    )
    scenario.notes["quiet_heights"] = quiet
    scenario.notes["audit_blocks"] = recorded
    scenario.notes["settlement_block"] = recorded[-1]
    return scenario, signatures


def restart_scenario() -> tuple[Scenario, Signatures]:
    """Four contiguous heights from genesis, for a layer that replays blocks.

    **Every other recorded chain uses `advance_to`**, which a store, an
    application, or a transport cannot follow: each commits one height at a
    time, and a height it never executed is a height it cannot vouch for. This
    run is the settled chain's first two blocks, then a block with no inputs,
    then the two activations — so a layer replaying it block by block is
    compared against figures from a model that knows nothing about that layer.

    **The third block repeats its predecessor's stamp**, which C2 admits because
    the rule is non-decreasing, and is offered one a millisecond below it first,
    which C2 refuses. The predecessor's stamp is the value a restarted layer must
    have restored to answer both correctly: a layer that reopened with a stale,
    smaller stamp would admit both, and every later block would still satisfy C2.
    """
    signatures = Signatures()
    scenario = Scenario(name="restart", ledger=Ledger.from_genesis(genesis()))
    ledger = scenario.ledger

    _run(scenario, signatures, [
        Step("alice_registers", _register(
            signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY)),
        Step("bob_registers", _register(
            signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY)),
    ], timestamp_of_height(1))
    _run(scenario, signatures, [
        _purchase(signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
                  ALICE_SEAT, 1),
        _purchase(signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY,
                  BOB_SEAT, 1),
    ], timestamp_of_height(2))
    # Height 3 is offered a stamp one millisecond below its predecessor's
    # first. C2 refuses it and the block is rejected whole, so the ledger is
    # exactly where block 2 left it — which is the sequence a restarted layer
    # performs against the stamp it restored.
    scenario.notes["refused_below_the_predecessor"] = None
    try:
        execute_block(ledger, timestamp_of_height(2) - 1, [], signatures.oracle)
    except InvalidBlock as refusal:
        cause = refusal.__cause__
        scenario.notes["refused_below_the_predecessor"] = getattr(cause, "code", None)
    scenario.notes["root_after_the_refusal"] = ledger.state_root()
    _run(scenario, signatures, [], timestamp_of_height(2))
    _run(scenario, signatures, [
        _activate(signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
                  ALICE_SEAT, 2),
        _activate(signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY,
                  BOB_SEAT, 2),
    ], timestamp_of_height(4))
    return scenario, signatures
