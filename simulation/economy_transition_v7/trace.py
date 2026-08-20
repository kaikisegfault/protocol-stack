"""The recorded version-seven transition trace: three scenarios, executed.

Version seven changes no transaction, so this trace does not re-record what
`test-vectors/economy-transition-v6-execution.txt` already fixes about
registration, recovery, posture, or the accepted version-one transfer. It records
what version seven changes, which is where an unclaimable remainder goes and who
is able to collect it:

1. **pool** — two seats, a cycle nobody wins whose whole contribution enters the
   recovery pool, a cycle one seat wins that absorbs the pool entire, and a real
   kind-4 mint that collects both. It ends with `outstanding` at zero and the pool
   at zero on every Founder Node channel: **100% of what the manifest promised
   for those cycles reached a beneficiary**, where version six would have left
   four base permissions in a carry nothing ever releases.
2. **boundary** — the same chain at the same height under the rejected ordering,
   where the mint runs before the assignment. Under version six that block was
   merely expensive. Under version seven it **is rejected whole**, because the
   window's permissions enter `outstanding` with the only seat that could have
   claimed them already marked past it and the backing identity fails.
3. **permanence** — a machine past its own 731 issuance cycles, contributing
   nothing and eligible for everything. A cycle with **no contributing seat at
   all** drains the pool to it, and it mints. That is the case that would strand
   the pool forever if a later reader narrowed the winner set to the contributing
   set, and it is the reason ADR 0049's rule 3 is a requirement rather than a
   remark.

**No signature is computed anywhere.** A stand-in is an eight-octet counter padded
to 64 octets, recorded in the oracle against the exact key and message it
authorizes, so a signature presented over any other message is simply absent from
the table. `Signatures`, `Step`, `Scenario`, and the two builders are version
six's, because a fixture that constructs an unchanged envelope is not a place to
keep a second copy of one.
"""

from __future__ import annotations

import copy
from dataclasses import replace

from simulation.cycle_boundary import grid
from simulation.economy_transition_v3.settlement import SeatCycle
from simulation.economy_transition_v6 import messages
from simulation.economy_transition_v6.identity import Posture, escrow_id, signer_id
from simulation.economy_transition_v6.trace import (
    ACCEPTED_RECIPIENT,
    POSTURE_MINIMUM,
    Scenario,
    Signatures,
    Step,
    _confirmed_transfer,
    _posture,
    _register,
    _verified_user_mint,
    build,
)

from . import contract as c
from .block import BlockOutcome, execute_block
from .genesis import Genesis
from .ledger import ConservationFailure, Ledger

SUPPLY_LIMIT = 5_699_395_010_000_000_000
FIXED_FEE = 1_000
NETWORK_ID = 7

VERIFIER_KEY = bytes.fromhex("55" * 32)

ALICE_IDENTITY = bytes.fromhex("a1" * 32)
ALICE_KEY = bytes.fromhex("a2" * 32)
ALICE_SIGNER_KEY = bytes.fromhex("a3" * 32)
BOB_IDENTITY = bytes.fromhex("b1" * 32)
BOB_KEY = bytes.fromhex("b2" * 32)
BOB_SIGNER_KEY = bytes.fromhex("b3" * 32)
CAROL_IDENTITY = bytes.fromhex("e1" * 32)
CAROL_KEY = bytes.fromhex("e2" * 32)
CAROL_SIGNER_KEY = bytes.fromhex("e3" * 32)

ALICE_ESCROW = escrow_id(ALICE_IDENTITY, 0)
BOB_ESCROW = escrow_id(BOB_IDENTITY, 0)
CAROL_ESCROW = escrow_id(CAROL_IDENTITY, 0)

VALID_UNTIL = 10_000_000_000
ZERO_CONFIRMATION = bytes(c.HUB_SIGNATURE_BYTES)

ALICE_SEAT = 0
BOB_SEAT = 1
CAROL_SEAT = 2

# Scenarios one and two. Window 200 is the cycle nobody wins and window 201 is
# the cycle that absorbs what window 200 left behind.
DEAD_WINDOW = 200
WON_WINDOW = DEAD_WINDOW + 1
# Scenario three, on its own chain, far enough from the first two that a reader
# cannot mistake one schedule for the other.
STRANDED_WINDOW = 300
DRAINED_WINDOW = STRANDED_WINDOW + 1

MET_UPTIME_SECONDS = 72_000
FAILED_UPTIME_SECONDS = 7_200

# Thirty windows is the verified-user cap, so a collection at this height forfeits
# the ten older windows and collects the most recent thirty.
COLLECTION_HEIGHT = 40 * c.CYCLE_BLOCKS
TRANSFER_AMOUNT = 1_000_000
FRESH_SIGNER_KEY = bytes.fromhex("a4" * 32)


def boundary_height(window: int) -> int:
    """The height at which `window`'s assignment is due: the first of `w + 2`."""
    return (window + c.ASSIGNMENT_LAG_WINDOWS) * c.CYCLE_BLOCKS


def activation_height(first_window: int) -> int:
    """A height inside the window before `first_window`, so the mark is that one.

    A seat activated at height `h` takes `window_of_height(h)` as its mark, so
    activating in the window before the first assignable one is what makes that
    first cycle reachable and no earlier one.
    """
    return (first_window - 1) * c.CYCLE_BLOCKS + 10


def genesis() -> Genesis:
    """A Founder Economy genesis: no allocation, no accounts, a nonzero fee."""
    return Genesis(
        network_id=NETWORK_ID,
        supply_limit=SUPPLY_LIMIT,
        fixed_transfer_fee=FIXED_FEE,
        manifest_digest=bytes.fromhex(c.MANIFEST_DIGEST_HEX),
        verifier_key=VERIFIER_KEY,
    )


def _run(
    scenario: Scenario,
    signatures: Signatures,
    steps: list[Step],
    uptime: dict[int, list[SeatCycle]] | None = None,
    assignment_is_prologue: bool = True,
) -> BlockOutcome:
    block = execute_block(
        scenario.ledger,
        [step.raw for step in steps],
        signatures.oracle,
        uptime=uptime,
        assignment_is_prologue=assignment_is_prologue,
    )
    scenario.blocks.append(block)
    scenario.labels.append([step.label for step in steps if step.admits])
    scenario.raw_inputs.append(len(steps))
    for step, admission in zip(steps, block.admissions):
        if not step.admits:
            scenario.rejected[step.label] = admission.code
    return block


def _purchase(
    signatures: Signatures, ledger: Ledger, identity: bytes, key: bytes,
    signer_key: bytes, seat_id: int, nonce: int, referrer: bytes | None = None,
) -> bytes:
    """The referrer is named by escrow — the shareable thing — and recorded as an
    identity, so referral earnings follow the person rather than the address."""
    message = messages.purchase_message(ledger.chain_id, identity, seat_id, VALID_UNTIL)
    return build(
        signatures, ledger, c.PURCHASE_SEAT, signer_key, nonce,
        {
            "seat_id": seat_id,
            "has_referrer": referrer is not None,
            "referrer_escrow_id": referrer or bytes(32),
            "hub_signature": signatures.sign(key, message),
        },
        valid_until=VALID_UNTIL,
    )


def _activate(
    signatures: Signatures, ledger: Ledger, identity: bytes, key: bytes,
    signer_key: bytes, seat_id: int, nonce: int,
) -> bytes:
    message = messages.activation_message(
        ledger.chain_id, identity, seat_id, VALID_UNTIL
    )
    return build(
        signatures, ledger, c.ACTIVATE_SEAT, signer_key, nonce,
        {"seat_id": seat_id, "hub_signature": signatures.sign(key, message)},
        valid_until=VALID_UNTIL,
    )


def _mint_node(
    signatures: Signatures, ledger: Ledger, identity: bytes, key: bytes,
    signer_key: bytes, seat_id: int, destination: bytes, nonce: int,
) -> bytes:
    """Kind 4. The default posture requires a confirmation at every amount, so
    every mint in this trace carries a real HUB signature over the mint message."""
    message = messages.mint_message(
        ledger.chain_id, identity, c.MINT_NODE, seat_id, destination, VALID_UNTIL
    )
    return build(
        signatures, ledger, c.MINT_NODE, signer_key, nonce,
        {
            "seat_id": seat_id,
            "destination_escrow_id": destination,
            "hub_signature": signatures.sign(key, message),
        },
        valid_until=VALID_UNTIL,
    )


def _seated_chain(
    signatures: Signatures,
    name: str,
    people: list[tuple[bytes, bytes, bytes, int]],
    first_window: int,
) -> Scenario:
    """Register each person, sell each a seat, and activate every seat.

    Three blocks: the registrations, the purchases, and — after a run of empty
    blocks — the activations at a height inside the window before the first
    assignable one. Every fee is paid out of the entry airdrop the registration
    itself issued, which is the property version six established and version
    seven inherits without restating it.
    """
    scenario = Scenario(name=name, ledger=Ledger.from_genesis(genesis()))
    ledger = scenario.ledger

    _run(scenario, signatures, [
        Step(f"{_name_of(identity)}_registers", _register(
            signatures, ledger, identity, key, signer_key, valid_until=VALID_UNTIL))
        for identity, key, signer_key, _seat in people
    ])
    _run(scenario, signatures, [
        Step(f"{_name_of(identity)}_purchases", _purchase(
            signatures, ledger, identity, key, signer_key, seat, 1))
        for identity, key, signer_key, seat in people
    ])
    scenario.skipped_blocks = ledger.advance_to(activation_height(first_window) - 1)
    _run(scenario, signatures, [
        Step(f"{_name_of(identity)}_activates", _activate(
            signatures, ledger, identity, key, signer_key, seat, 2))
        for identity, key, signer_key, seat in people
    ])
    return scenario


def _name_of(identity: bytes) -> str:
    return {
        ALICE_IDENTITY: "alice",
        BOB_IDENTITY: "bob",
        CAROL_IDENTITY: "carol",
    }[identity]


def _advance_to_boundary(scenario: Scenario, window: int) -> None:
    scenario.skipped_blocks += scenario.ledger.advance_to(boundary_height(window) - 1)


def _version_six_registration(signatures: Signatures, ledger: Ledger) -> bytes:
    """A registration bound to the version-six chain identity of this genesis.

    Version seven changes no transaction, so these are the bytes a version-six
    chain admits. Only the chain ID inside them differs, which is the whole
    compatibility boundary between the two: they are alternative chains rather
    than a sequence, and no version-six byte sequence executes under version-seven
    rules.
    """
    from .genesis import predecessor_chain_id

    foreign = copy.copy(ledger)
    foreign.chain_id = predecessor_chain_id(genesis(), 6)
    return _register(
        signatures, foreign, CAROL_IDENTITY, CAROL_KEY, CAROL_SIGNER_KEY,
        valid_until=VALID_UNTIL,
    )


# --- scenario one: the pool fills, drains, and is minted --------------------

POOL_UPTIME: dict[int, list[SeatCycle]] = {
    # Nobody meets the cycle. Both contributions are reallocated and, with no
    # winner to divide them, the whole of both enters the recovery pool.
    DEAD_WINDOW: [
        SeatCycle(ALICE_SEAT, FAILED_UPTIME_SECONDS, True, 0),
        SeatCycle(BOB_SEAT, FAILED_UPTIME_SECONDS, True, 0),
    ],
    # Alice meets it alone: she accrues her own permission, takes Bob's
    # reallocated one, and absorbs everything the dead cycle left.
    WON_WINDOW: [
        SeatCycle(ALICE_SEAT, MET_UPTIME_SECONDS, True, 0),
        SeatCycle(BOB_SEAT, FAILED_UPTIME_SECONDS, True, 0),
    ],
}


def pool_scenario() -> tuple[Scenario, Signatures]:
    signatures = Signatures()
    scenario = _seated_chain(
        signatures,
        "pool",
        [
            (ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY, ALICE_SEAT),
            (BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY, BOB_SEAT),
        ],
        DEAD_WINDOW,
    )
    ledger = scenario.ledger

    _advance_to_boundary(scenario, DEAD_WINDOW)
    dead = _run(scenario, signatures, [], uptime=POOL_UPTIME)
    scenario.notes["pool_after_dead_cycle"] = dict(ledger.pool)
    scenario.notes["outstanding_after_dead_cycle"] = dict(ledger.channel_outstanding)
    scenario.notes["claimable_after_dead_cycle"] = ledger.claimable()

    _advance_to_boundary(scenario, WON_WINDOW)
    won = _run(
        scenario,
        signatures,
        [
            # Alice collects both cycles: her own accrual, Bob's reallocated
            # permission, and the whole pool the dead cycle left behind.
            Step("alice_mints", _mint_node(
                signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
                ALICE_SEAT, ALICE_ESCROW, 3)),
            # Bob generated two base permissions and met neither cycle, so his
            # mint succeeds, collects nothing, and pays a fee. The reallocation
            # is what it says it is.
            Step("bob_mints_nothing", _mint_node(
                signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY,
                BOB_SEAT, BOB_ESCROW, 3)),
            # A second mint in the same block. The mark now equals the last
            # assigned window, so the walk range is empty — which is the rule
            # ADR 0045 derived rather than the literal equality the text states.
            Step("alice_mints_again", _mint_node(
                signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
                ALICE_SEAT, ALICE_ESCROW, 4)),
            # The same registration bytes a version-six chain would admit,
            # refused at admission because every signed message binds a chain ID
            # derived under a version-seven label.
            Step("carol_registers_on_the_version_six_chain",
                 _version_six_registration(signatures, ledger), admits=False),
        ],
        uptime=POOL_UPTIME,
    )
    scenario.notes["dead_window"] = dead.assigned_window
    scenario.notes["won_window"] = won.assigned_window
    scenario.notes["pool_after_mint"] = dict(ledger.pool)
    scenario.notes["outstanding_after_mint"] = dict(ledger.channel_outstanding)
    scenario.notes["issued_after_mint"] = dict(ledger.channel_issued)
    scenario.notes["alice_mark"] = ledger.seats[ALICE_SEAT].minted_through_window
    scenario.notes["bob_mark"] = ledger.seats[BOB_SEAT].minted_through_window
    return scenario, signatures


# --- scenario two: the rejected ordering is refused by the invariant ---------


def boundary_scenario() -> tuple[Scenario, Signatures]:
    """The same block under both readings, on two copies of one state.

    The accepted reading is scenario one's. This one rebuilds the identical chain
    and offers the identical block with the assignment written **after** the
    transactions, which is the reading version six had to reject by argument.
    """
    signatures = Signatures()
    scenario = _seated_chain(
        signatures,
        "boundary",
        [
            (ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY, ALICE_SEAT),
            (BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY, BOB_SEAT),
        ],
        DEAD_WINDOW,
    )
    ledger = scenario.ledger
    _advance_to_boundary(scenario, DEAD_WINDOW)
    _run(scenario, signatures, [], uptime=POOL_UPTIME)
    _advance_to_boundary(scenario, WON_WINDOW)

    mint = Step("alice_mints", _mint_node(
        signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
        ALICE_SEAT, ALICE_ESCROW, 3))
    before_root = ledger.state_root()
    rejected = copy.deepcopy(ledger)
    refusal = None
    try:
        execute_block(
            rejected, [mint.raw], signatures.oracle,
            uptime=POOL_UPTIME, assignment_is_prologue=False,
        )
    except ConservationFailure as failure:
        refusal = str(failure)
    scenario.notes["rejected_ordering_refusal"] = refusal
    scenario.notes["rejected_ordering_preserved_state"] = (
        rejected.state_root() == before_root
    )
    scenario.notes["rejected_ordering_height"] = rejected.height

    accepted = _run(
        scenario,
        signatures,
        [
            mint,
            # The same refusal the pool scenario records, kept here so this
            # scenario's atomicity claim is about a refusal it actually saw.
            Step("alice_mints_again", _mint_node(
                signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
                ALICE_SEAT, ALICE_ESCROW, 4)),
        ],
        uptime=POOL_UPTIME,
    )
    scenario.notes["accepted_ordering_issued"] = accepted.executed[0].outcome.issued_atomic
    scenario.notes["state_root_before_the_boundary_block"] = before_root
    return scenario, signatures


# --- scenario three: a machine past its own 731 cycles ----------------------

PERMANENCE_UPTIME: dict[int, list[SeatCycle]] = {
    # Alice is in span and fails the cycle; Carol is past her own 731 cycles and
    # also fails it. Nobody wins, so Alice's whole contribution enters the pool.
    STRANDED_WINDOW: [
        SeatCycle(ALICE_SEAT, FAILED_UPTIME_SECONDS, True, 0),
        SeatCycle(CAROL_SEAT, FAILED_UPTIME_SECONDS, False, 0),
    ],
    # Alice's machine is out of scope entirely, so the contributing set is empty
    # and nothing is assigned. Carol is still eligible and still wins, and the
    # pool drains to her — the case that would strand it forever if the winner
    # set were ever narrowed to the contributing set.
    DRAINED_WINDOW: [
        SeatCycle(CAROL_SEAT, MET_UPTIME_SECONDS, False, 0),
    ],
}


def permanence_scenario() -> tuple[Scenario, Signatures]:
    signatures = Signatures()
    scenario = _seated_chain(
        signatures,
        "permanence",
        [
            (ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY, ALICE_SEAT),
            (CAROL_IDENTITY, CAROL_KEY, CAROL_SIGNER_KEY, CAROL_SEAT),
        ],
        STRANDED_WINDOW,
    )
    ledger = scenario.ledger

    _advance_to_boundary(scenario, STRANDED_WINDOW)
    stranded = _run(scenario, signatures, [], uptime=PERMANENCE_UPTIME)
    scenario.notes["pool_after_stranded_cycle"] = dict(ledger.pool)
    scenario.notes["assigned_after_stranded_cycle"] = ledger.assigned_permissions

    _advance_to_boundary(scenario, DRAINED_WINDOW)
    drained = _run(
        scenario,
        signatures,
        [
            Step("carol_mints", _mint_node(
                signatures, ledger, CAROL_IDENTITY, CAROL_KEY, CAROL_SIGNER_KEY,
                CAROL_SEAT, CAROL_ESCROW, 3)),
            Step("carol_mints_again", _mint_node(
                signatures, ledger, CAROL_IDENTITY, CAROL_KEY, CAROL_SIGNER_KEY,
                CAROL_SEAT, CAROL_ESCROW, 4)),
        ],
        uptime=PERMANENCE_UPTIME,
    )
    scenario.notes["stranded_window"] = stranded.assigned_window
    scenario.notes["drained_window"] = drained.assigned_window
    scenario.notes["assigned_after_drained_cycle"] = ledger.assigned_permissions
    scenario.notes["pool_after_mint"] = dict(ledger.pool)
    scenario.notes["outstanding_after_mint"] = dict(ledger.channel_outstanding)
    scenario.notes["issued_after_mint"] = dict(ledger.channel_issued)
    scenario.notes["carol_issued"] = drained.executed[0].outcome.issued_atomic
    scenario.notes["alice_never_accrued"] = ledger.seats[ALICE_SEAT].minted_through_window
    return scenario, signatures


# --- scenario four: the ten kinds version seven does not change -------------


def carried_scenario() -> tuple[Scenario, Signatures]:
    """Every transaction version seven leaves alone, executed under version seven.

    **The bytes are version six's and the commitments are not.** A registration
    under version seven is byte-for-byte a registration under version six, and it
    lands in a version-seven state and produces a version-seven receipt. Version
    six's 512 execution vectors record neither of those, because they record
    version-six roots and version-six receipts, so nothing anywhere fixed what
    these ten kinds commit to under version seven until this scenario did.

    Every step builder is version six's, imported rather than restated: what is
    version seven's here is the ledger they run against and the roots they commit.
    """
    signatures = Signatures()
    scenario = Scenario(name="carried", ledger=Ledger.from_genesis(genesis()))
    ledger = scenario.ledger

    _run(scenario, signatures, [
        Step("alice_registers", _register(
            signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
            valid_until=VALID_UNTIL)),
        Step("bob_registers", _register(
            signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY,
            valid_until=VALID_UNTIL)),
    ])

    # Kinds 1, 19, and 6. The default posture requires a confirmation at every
    # amount, so the unconfirmed transfer is refused and the confirmed one is not;
    # a refusal advances no nonce, which is why the confirmed transfer reuses 1.
    _run(scenario, signatures, [
        Step("alice_transfers_unconfirmed", build(
            signatures, ledger, c.TRANSFER, ALICE_SIGNER_KEY, 1,
            {"recipient_escrow_id": BOB_ESCROW, "amount_atomic": TRANSFER_AMOUNT},
            valid_until=VALID_UNTIL)),
        Step("alice_transfers_confirmed", _confirmed_transfer(
            signatures, ledger, 1, BOB_ESCROW, TRANSFER_AMOUNT)),
        Step("alice_transfers_to_an_unregistered_recipient", _confirmed_transfer(
            signatures, ledger, 2, ACCEPTED_RECIPIENT, TRANSFER_AMOUNT)),
        Step("alice_attempts_a_direct_issue", build(
            signatures, ledger, c.DIRECT_ISSUE, ALICE_SIGNER_KEY, 2,
            {
                "channel_id": 5,
                "decision_id": bytes(32),
                "beneficiary_escrow_id": ALICE_ESCROW,
                "amount_atomic": 1,
                "authorization": bytes(32),
            },
            valid_until=VALID_UNTIL)),
    ])

    # Kinds 13, 14, 15, and 16 — the four an identity performs with no signer at
    # all, which is the recovery architecture ADR 0040 exists for.
    second_escrow = escrow_id(ALICE_IDENTITY, 1)
    _run(scenario, signatures, [
        Step("alice_creates_a_second_escrow", build(
            signatures, ledger, c.ESCROW_CREATE, ALICE_KEY, 2,
            {"hub_identity_hash": ALICE_IDENTITY, "fee_escrow_id": ALICE_ESCROW},
            valid_until=VALID_UNTIL)),
        Step("alice_deletes_the_second_escrow", build(
            signatures, ledger, c.ESCROW_DELETE, ALICE_KEY, 3,
            {
                "hub_identity_hash": ALICE_IDENTITY,
                "fee_escrow_id": ALICE_ESCROW,
                "target_escrow_id": second_escrow,
            },
            valid_until=VALID_UNTIL)),
        Step("alice_assigns_a_fresh_signer", build(
            signatures, ledger, c.SIGNER_ADD, ALICE_KEY, 4,
            {
                "hub_identity_hash": ALICE_IDENTITY,
                "escrow_id": ALICE_ESCROW,
                "signer_public_key": FRESH_SIGNER_KEY,
            },
            valid_until=VALID_UNTIL)),
        Step("alice_revokes_the_fresh_signer", build(
            signatures, ledger, c.SIGNER_REVOKE, ALICE_KEY, 5,
            {
                "hub_identity_hash": ALICE_IDENTITY,
                "escrow_id": ALICE_ESCROW,
                "signer_id": signer_id(FRESH_SIGNER_KEY),
            },
            valid_until=VALID_UNTIL)),
    ])

    # Kind 17, in both directions. The opening posture is the strictest one the
    # contract admits, so the first change can only be a relaxation — and a
    # relaxation is exactly what the HUB signature is required for.
    relaxed = Posture(requires_confirmation=True, min_amount_atomic=POSTURE_MINIMUM)
    tightened = Posture(requires_confirmation=True, min_amount_atomic=0)
    _run(scenario, signatures, [
        Step("alice_relaxes_without_a_signature",
             _posture(signatures, ledger, 6, relaxed, signed=False)),
        Step("alice_relaxes_her_posture",
             _posture(signatures, ledger, 6, relaxed, signed=True)),
        Step("alice_tightens_her_posture",
             _posture(signatures, ledger, 7, tightened, signed=False)),
        Step("alice_repeats_the_posture_she_holds",
             _posture(signatures, ledger, 8, tightened, signed=False)),
    ])

    # Kind 18, forty windows after enrolment: thirty are collectable and the ten
    # older ones are forfeited, which is the cap doing what it is for.
    scenario.skipped_blocks += ledger.advance_to(COLLECTION_HEIGHT - 1)
    _run(scenario, signatures, [
        Step("alice_collects_thirty_windows", _verified_user_mint(
            signatures, ledger, ALICE_IDENTITY, 8, ALICE_ESCROW)),
        Step("alice_collects_again_immediately", _verified_user_mint(
            signatures, ledger, ALICE_IDENTITY, 9, ALICE_ESCROW)),
    ])
    scenario.notes["collection_height"] = COLLECTION_HEIGHT
    scenario.notes["alice_balance"] = ledger.balance(ALICE_ESCROW)
    scenario.notes["bob_balance"] = ledger.balance(BOB_ESCROW)
    scenario.notes["verified_user_issued"] = ledger.channel_issued[
        c.VERIFIED_USER_CHANNEL
    ]
    return scenario, signatures


# --- scenario five: the referral leg ----------------------------------------

REFERRED_WINDOW = 400

REFERRAL_UPTIME: dict[int, list[SeatCycle]] = {
    REFERRED_WINDOW: [SeatCycle(BOB_SEAT, MET_UPTIME_SECONDS, True, 0)],
}


def _mint_referral(
    signatures: Signatures, ledger: Ledger, identity: bytes, key: bytes,
    signer_key: bytes, destination: bytes, nonce: int,
) -> bytes:
    message = messages.mint_message(
        ledger.chain_id, identity, c.MINT_REFERRAL, 0, destination, VALID_UNTIL
    )
    return build(
        signatures, ledger, c.MINT_REFERRAL, signer_key, nonce,
        {
            "destination_escrow_id": destination,
            "hub_signature": signatures.sign(key, message),
        },
        valid_until=VALID_UNTIL,
    )


def referral_scenario() -> tuple[Scenario, Signatures]:
    """Kind 5, the last kind version seven admits that nothing else here reaches.

    Bob buys a seat naming Alice's escrow as his referrer. The assignment prologue
    accrues the referral leg to Alice's **identity**, and Alice mints it in the
    same block the prologue wrote it in. The referral channel keeps version six's
    identity unchanged, including the unreferred pool term, because the referral
    leg has no winner split and therefore no remainder — which is why the recovery
    pool has five legs rather than six.
    """
    signatures = Signatures()
    scenario = Scenario(name="referral", ledger=Ledger.from_genesis(genesis()))
    ledger = scenario.ledger

    _run(scenario, signatures, [
        Step("alice_registers", _register(
            signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
            valid_until=VALID_UNTIL)),
        Step("bob_registers", _register(
            signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY,
            valid_until=VALID_UNTIL)),
    ])
    _run(scenario, signatures, [
        Step("bob_purchases_a_seat_referring_alice", _purchase(
            signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY,
            BOB_SEAT, 1, referrer=ALICE_ESCROW)),
    ])
    scenario.skipped_blocks = ledger.advance_to(
        activation_height(REFERRED_WINDOW) - 1
    )
    _run(scenario, signatures, [
        Step("bob_activates", _activate(
            signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY, BOB_SEAT, 2)),
    ])

    _advance_to_boundary(scenario, REFERRED_WINDOW)
    assigned = _run(
        scenario,
        signatures,
        [
            Step("alice_mints_her_referral", _mint_referral(
                signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
                ALICE_ESCROW, 1)),
            Step("alice_mints_it_again", _mint_referral(
                signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
                ALICE_ESCROW, 2)),
            Step("bob_mints_a_referral_he_has_never_earned", _mint_referral(
                signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY,
                BOB_ESCROW, 3)),
        ],
        uptime=REFERRAL_UPTIME,
    )
    scenario.notes["referred_window"] = assigned.assigned_window
    scenario.notes["referral_issued"] = ledger.channel_issued[c.REFERRAL_CHANNEL]
    scenario.notes["referral_outstanding"] = ledger.channel_outstanding[
        c.REFERRAL_CHANNEL
    ]
    scenario.notes["unreferred_pool_accrued"] = ledger.pool_accrued
    scenario.notes["alice_balance"] = ledger.balance(ALICE_ESCROW)
    return scenario, signatures


SCENARIOS = (pool_scenario, boundary_scenario, permanence_scenario,
             carried_scenario, referral_scenario)

