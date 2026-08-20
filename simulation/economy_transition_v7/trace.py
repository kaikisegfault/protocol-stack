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
from simulation.economy_transition_v6.identity import escrow_id
from simulation.economy_transition_v6.trace import (
    Scenario,
    Signatures,
    Step,
    _register,
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
    signer_key: bytes, seat_id: int, nonce: int,
) -> bytes:
    message = messages.purchase_message(ledger.chain_id, identity, seat_id, VALID_UNTIL)
    return build(
        signatures, ledger, c.PURCHASE_SEAT, signer_key, nonce,
        {
            "seat_id": seat_id,
            "has_referrer": False,
            "referrer_escrow_id": bytes(32),
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
        Step(f"{label}_registers", _register(
            signatures, ledger, identity, key, signer_key, valid_until=VALID_UNTIL))
        for identity, key, signer_key, _seat in people
        for label in [_name_of(identity)]
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


SCENARIOS = (pool_scenario, boundary_scenario, permanence_scenario)
