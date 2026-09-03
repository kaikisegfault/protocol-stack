"""The recorded version-eight transition trace: four scenarios, executed.

Version eight changes no settlement and no carried transaction, so this trace
does not re-record what `test-vectors/economy-transition-v7-execution.txt`
already fixes about the recovery pool, the winner rule, or the mint walk. It
records what version eight changes, which is **where the measurement comes
from**:

1. **measured** — two machines audited by the chain across a whole window.
   Alice answers every challenge the chain issues her and writes no window
   record at all; Bob answers none, loses a slot at every expiry, and fails his
   cycle. Window 1's assignment is then derived from that evidence and Alice
   mints against it. It is the first time in this repository that a node reward
   is paid from uptime the chain itself measured, rather than from a schedule
   handed to `execute_block`.
2. **disputed** — the same two machines, both perfect, and six disputes against
   Alice. She keeps eighteen of twenty-four slots, which is exactly the
   founder-directed threshold, so she still meets her cycle and is no longer the
   best performer: the winner set moves from both seats to Bob alone. A seventh
   dispute is refused by the cap. The counterfactual chain — identical up to the
   dispute block, with no dispute filed — is run beside it, so "the dispute
   changed the winner set" is a comparison rather than an assertion.
3. **deadline** — the one execution ordering a chain can observe, run three ways
   on identical copies of one chain: the same response is accepted at `c + 20`,
   refused as `RESPONSE_TOO_LATE` at `c + 21` with the slot already lost, and
   refused as `CHALLENGE_NOT_ISSUED` at `c + 20` when the expiry step is moved
   ahead of the transactions — costing the seat the slot it had just proved.
4. **carried** — every version-seven kind version eight leaves alone, executed
   against a version-eight ledger. The bytes are version six's, built by version
   six's own builders; what is version eight's is the state they land in and the
   roots and receipts they commit to.

**No signature is computed anywhere.** A stand-in is an eight-octet counter
padded to 64 octets, recorded in the oracle against the exact key and message it
authorizes, so a signature presented over any other message is simply absent from
the table. That covers the dispute authority's signature too: the authority is a
recorded key like any other, and a dispute over a different window, slot, reason,
or expiry does not verify because it was never signed.

**A window is 28,800 heights and this trace runs every one of them.** Under
version eight a block with no transactions still audits every in-scope seat, so
there is no honest shorthand for the stretch between two interesting blocks;
`block.run_quiet_heights` executes it. What that costs is one digest over a
120-octet preimage per height plus one per in-scope seat, because the economy
tree under an unchanged state is recomputed only when the issue step or the
expiry step writes.
"""

from __future__ import annotations

import copy

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
)
from simulation.economy_transition_v6.trace import build as build_v6
from simulation.economy_transition_v7.trace import (
    ALICE_ESCROW,
    ALICE_IDENTITY,
    ALICE_KEY,
    ALICE_SIGNER_KEY,
    BOB_ESCROW,
    BOB_IDENTITY,
    BOB_KEY,
    BOB_SIGNER_KEY,
    FRESH_SIGNER_KEY,
)

from . import contract as c
from .block import BlockOutcome, execute_block, run_quiet_heights
from .envelope import Transaction, signed_bytes, signing_message, unsigned_bytes
from .genesis import Genesis
from .ledger import Ledger
from .schedule import derive_schedule
from .slots import slot_of_height, window_of_height
from .state import all_slots_credited, credited_slots

SUPPLY_LIMIT = 5_699_395_010_000_000_000
FIXED_FEE = 1_000
NETWORK_ID = 8

VERIFIER_KEY = bytes.fromhex("55" * 32)
# Separate from the verifier key, which is the whole point of the added genesis
# field: whoever attests HUB identities does not thereby acquire the power to
# void a machine's uptime.
DISPUTE_AUTHORITY_KEY = bytes.fromhex("d8" * 32)
FOREIGN_AUTHORITY_KEY = bytes.fromhex("ee" * 32)

VALID_UNTIL = 10_000_000_000

ALICE_SEAT = 0
BOB_SEAT = 1
# Purchased and never activated, so it is in no window's scope and the issue
# step must never audit it.
SPARE_SEAT = 2

# Both seats activate near the end of window 0, so window 1 is the first window
# either is in scope for and the trace runs exactly the windows it measures.
ACTIVATION_HEIGHT = c.CYCLE_BLOCKS - 10
MEASURED_WINDOW = 1
# The first height of window 3 is where window 1's assignment is due.
ASSIGNMENT_HEIGHT = (MEASURED_WINDOW + c.ASSIGNMENT_LAG_WINDOWS) * c.CYCLE_BLOCKS
# One height inside window 2, which is the whole of window 1's dispute window.
DISPUTE_HEIGHT = (MEASURED_WINDOW + 1) * c.CYCLE_BLOCKS + 100

TRANSFER_AMOUNT = 1_000_000
COLLECTION_HEIGHT = 40 * c.CYCLE_BLOCKS

DISPUTED_SLOTS = tuple(range(c.DISPUTE_CAP_SLOTS_PER_SEAT))
REASON_CODE = 3


def genesis() -> Genesis:
    """A Founder Economy genesis: no allocation, no accounts, a nonzero fee."""
    return Genesis(
        network_id=NETWORK_ID,
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
    """Version six's builder over version eight's envelope.

    The framing is unchanged, so this differs from version six's in exactly one
    place: the two fee-exempt kinds carry a zero fee limit rather than one. A
    registration always did; a challenge response does on the founder answer of
    2026-09-02, and offering one with a nonzero limit is refused at admission.
    """
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
    signature = signatures.sign(authority, signing_message(unsigned))
    return signed_bytes(transaction, signature)


# --- the builders version eight adds ----------------------------------------


def _response(
    signatures: Signatures,
    ledger: Ledger,
    signer_key: bytes,
    seat_id: int,
    challenge_height: int,
    nonce: int,
    answer: bytes | None = None,
) -> bytes:
    """Kind 20. Opaque under this version: an answer of the defined width."""
    return build(
        signatures, ledger, c.CHALLENGE_RESPONSE, signer_key, nonce,
        {
            "seat_id": seat_id,
            "challenge_height": challenge_height,
            "answer": answer if answer is not None else bytes(c.ANSWER_BYTES),
        },
    )


def _dispute(
    signatures: Signatures,
    ledger: Ledger,
    signer_key: bytes,
    seat_id: int,
    cycle_window: int,
    slot_index: int,
    nonce: int,
    authority_key: bytes = DISPUTE_AUTHORITY_KEY,
    reason_code: int = REASON_CODE,
) -> bytes:
    """Kind 21. The envelope's signer relays and pays; the authority signs the body.

    `authority_key` is a parameter so the trace can offer a dispute signed by a
    key the chain does not recognise. The oracle holds no signature for a message
    it was never asked to sign, so the refusal is the absence of a table entry
    rather than a comparison this model invents.
    """
    from .envelope import dispute_message

    message = dispute_message(
        ledger.chain_id, seat_id, cycle_window, slot_index, reason_code, VALID_UNTIL
    )
    return build(
        signatures, ledger, c.FILE_DISPUTE, signer_key, nonce,
        {
            "seat_id": seat_id,
            "cycle_window": cycle_window,
            "slot_index": slot_index,
            "reason_code": reason_code,
            "authority_signature": signatures.sign(authority_key, message),
        },
    )


# --- the carried builders, over a version-eight ledger ----------------------


def _purchase(
    signatures: Signatures, ledger: Ledger, identity: bytes, key: bytes,
    signer_key: bytes, seat_id: int, nonce: int, referrer: bytes | None = None,
) -> bytes:
    message = messages.purchase_message(ledger.chain_id, identity, seat_id, VALID_UNTIL)
    return build(
        signatures, ledger, c.PURCHASE_SEAT, signer_key, nonce,
        {
            "seat_id": seat_id,
            "has_referrer": referrer is not None,
            "referrer_escrow_id": referrer or bytes(32),
            "hub_signature": signatures.sign(key, message),
        },
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
    )


def _mint_node(
    signatures: Signatures, ledger: Ledger, identity: bytes, key: bytes,
    signer_key: bytes, seat_id: int, destination: bytes, nonce: int,
) -> bytes:
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
    )


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
            "hub_identity_hash": identity,
            "destination_escrow_id": destination,
            "hub_signature": signatures.sign(key, message),
        },
    )


# --- running -----------------------------------------------------------------


def _accepted_responses(blocks: list[BlockOutcome]) -> int:
    """How many kind-20 transactions succeeded across a run of audited heights.

    Counted from the executed rows rather than from the responder's own log,
    because the log records what was offered and this records what the chain
    accepted. A trace that offered a response the chain refused would show the
    two disagreeing, which is the only way a scenario can notice it.
    """
    return sum(
        1
        for block in blocks
        for entry in block.executed
        if entry.kind == c.CHALLENGE_RESPONSE and entry.result == "SUCCESS"
    )


def _response_fees(blocks: list[BlockOutcome]) -> int:
    """Every fee a challenge response paid. The founder answer makes it zero."""
    return sum(
        entry.outcome.fee_charged
        for block in blocks
        for entry in block.executed
        if entry.kind == c.CHALLENGE_RESPONSE
    )


def _run(
    scenario: Scenario, signatures: Signatures, steps: list[Step], **options
) -> BlockOutcome:
    block = execute_block(
        scenario.ledger, [step.raw for step in steps], signatures.oracle, **options
    )
    scenario.blocks.append(block)
    scenario.labels.append([step.label for step in steps if step.admits])
    scenario.raw_inputs.append(len(steps))
    for step, admission in zip(steps, block.admissions):
        if not step.admits:
            scenario.rejected[step.label] = admission.code
    return block


class Responder:
    """One machine answering every challenge the chain issues it, and its log.

    The log is the evidence. A trace cannot pre-compute which of its own machines
    will be audited — that unpredictability is the property the pipeline exists
    to have — so what a scenario can state afterwards is that every challenge it
    was issued was answered, and the counts are how that is checked.
    """

    def __init__(
        self,
        signatures: Signatures,
        ledger: Ledger,
        seat_id: int,
        escrow: bytes,
        signer_key: bytes,
        silent: bool = False,
    ) -> None:
        self._signatures = signatures
        self._ledger = ledger
        self._seat_id = seat_id
        self._escrow = escrow
        self._signer_key = signer_key
        self._silent = silent
        self.challenged: list[int] = []
        self.answered: list[int] = []

    def __call__(self, height: int, issued: list[int]) -> list[bytes]:
        if self._seat_id not in issued:
            return []
        self.challenged.append(height)
        if self._silent:
            # A machine that logs its audits and answers none. Its log is what
            # lets a scenario check the window record against the challenges
            # that produced it, from the other side.
            return []
        self.answered.append(height)
        return [
            _response(
                self._signatures, self._ledger, self._signer_key,
                self._seat_id, height, self._ledger.nonce(self._escrow) + 1,
            )
        ]

    def fork(self, ledger: Ledger) -> "Responder":
        """The same machine answering a second chain's audits from this height.

        **The nonce is not carried**, because it is not this object's to carry:
        it is read from whichever ledger is being answered. That is what makes a
        fork correct rather than merely convenient — a branch that filed six
        disputes from the same escrow has a different nonce sequence from one
        that filed none, and a responder holding its own counter would offer a
        stale nonce to exactly one of the two.
        """
        return Responder(
            self._signatures, ledger, self._seat_id, self._escrow, self._signer_key,
            silent=self._silent,
        )

    def slots(self) -> set[int]:
        return {slot_of_height(height) for height in self.challenged}


def _seated_chain(
    signatures: Signatures, name: str, referred: bool, spare_seat: bool = False
) -> tuple[Scenario, Responder]:
    """Register both people, sell each a seat, and activate the seats that run.

    Three blocks and one run of empty blocks. **The shorthand is used exactly
    once and only before any activation**, which is the only stretch of a
    version-eight chain where a block with no transactions really does change
    height and nothing else: no seat is in scope, so the issue step selects
    nobody. `Ledger.advance_to` refuses it everywhere else.

    `spare_seat` sells Bob a second seat and never activates it. A purchased,
    unactivated seat has no activation height, so it is in no window's scope and
    the issue step must never audit it — and a chain with no such seat cannot
    tell whether the issue step checks activation at all, because an unactivated
    seat's default activation height of zero puts it inside every window.
    """
    scenario = Scenario(name=name, ledger=Ledger.from_genesis(genesis()))
    scenario.audit_blocks = []
    ledger = scenario.ledger

    _run(scenario, signatures, [
        Step("alice_registers", _register(
            signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY)),
        Step("bob_registers", _register(
            signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY)),
    ])
    purchases = [
        Step("alice_purchases", _purchase(
            signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
            ALICE_SEAT, 1)),
        Step("bob_purchases", _purchase(
            signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY, BOB_SEAT, 1,
            referrer=ALICE_ESCROW if referred else None)),
    ]
    if spare_seat:
        purchases.append(Step("bob_purchases_a_seat_he_never_runs", _purchase(
            signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY,
            SPARE_SEAT, 2)))
    _run(scenario, signatures, purchases)
    scenario.skipped_blocks = ledger.advance_to(ACTIVATION_HEIGHT - 1)
    _run(scenario, signatures, [
        Step("alice_activates", _activate(
            signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
            ALICE_SEAT, 2)),
        Step("bob_activates", _activate(
            signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY, BOB_SEAT,
            3 if spare_seat else 2)),
    ])
    return scenario, Responder(
        signatures, ledger, ALICE_SEAT, ALICE_ESCROW, ALICE_SIGNER_KEY
    )


# --- scenario one: a window the chain measured itself -----------------------


def measured_scenario() -> tuple[Scenario, Signatures]:
    """Alice answers every audit, Bob answers none, and the chain pays Alice.

    Bob's window record is the whole point: it exists only because he lost
    challenges, it holds one cleared bit per slot he was audited in and missed,
    and nothing anywhere had to be told he was offline. Alice's record does not
    exist at all, which is the same statement in the other direction — a machine
    that answers everything writes nothing, so the storage the pipeline adds is
    proportional to failure rather than to population.
    """
    signatures = Signatures()
    scenario, alice = _seated_chain(
        signatures, "measured", referred=True, spare_seat=True
    )
    ledger = scenario.ledger

    bob = Responder(
        signatures, ledger, BOB_SEAT, BOB_ESCROW, BOB_SIGNER_KEY, silent=True
    )

    def respond(height: int, issued: list[int]) -> list[bytes]:
        return alice(height, issued) + bob(height, issued)

    heights, recorded = run_quiet_heights(
        ledger, ASSIGNMENT_HEIGHT - 1, signatures.oracle, respond=respond
    )
    scenario.skipped_blocks += heights
    scenario.audit_blocks = recorded
    scenario.notes["quiet_heights"] = heights
    scenario.notes["audit_blocks"] = len(recorded)
    scenario.notes["alice_challenges"] = len(alice.challenged)
    scenario.notes["alice_answered"] = len(alice.answered)
    scenario.notes["alice_unanswered"] = len(alice.challenged) - len(alice.answered)
    scenario.notes["responses_accepted"] = _accepted_responses(recorded)
    scenario.notes["response_fees_charged"] = _response_fees(recorded)

    records = ledger.window_records()
    bob_credited, bob_disputed = records.get(
        (MEASURED_WINDOW, BOB_SEAT), (all_slots_credited(), 0)
    )
    scenario.notes["alice_has_no_window_record"] = (
        MEASURED_WINDOW, ALICE_SEAT
    ) not in records
    scenario.notes["bob_credited_slots"] = credited_slots(bob_credited, bob_disputed)
    scenario.notes["bob_lost_slots"] = c.SLOTS_PER_WINDOW - credited_slots(
        bob_credited, bob_disputed
    )
    scenario.notes["bob_challenges"] = len(bob.challenged)
    scenario.notes["the_unactivated_seat_was_never_audited"] = not any(
        seat == SPARE_SEAT
        for _window, seat in ledger.window_records()
    ) and not any(
        seat == SPARE_SEAT for _height, seat in ledger.open_challenges()
    )
    scenario.notes["the_unactivated_seat_is_not_in_the_schedule"] = SPARE_SEAT not in {
        measured.seat_id
        for measured in derive_schedule(
            ledger.activations(), MEASURED_WINDOW, ledger.uptime
        )
    }

    # The window record read from the other side: every slot Bob lost is a slot
    # he was audited in and did not answer, derived from his own log rather than
    # from the bitmap the chain wrote.
    bob_window_slots = {
        slot_of_height(height)
        for height in bob.challenged
        if window_of_height(height) == MEASURED_WINDOW
    }
    scenario.notes["bob_lost_exactly_the_slots_he_was_audited_in"] = (
        bob_window_slots
        == {slot for slot in range(c.SLOTS_PER_WINDOW) if not bob_credited >> slot & 1}
    )
    # Selection excludes the final RESPONSE_DEADLINE_BLOCKS heights of a slot, so
    # a challenge and its expiry are always inside one slot. Checked over every
    # challenge this chain actually issued rather than argued from the exclusion.
    scenario.notes["every_challenge_expired_in_its_own_slot"] = all(
        (window_of_height(height), slot_of_height(height))
        == (
            window_of_height(height + c.RESPONSE_DEADLINE_BLOCKS),
            slot_of_height(height + c.RESPONSE_DEADLINE_BLOCKS),
        )
        for height in alice.challenged + bob.challenged
    )

    # The prologue precedes the issue step, and at the accepted lag of two
    # windows the alternative commits to the same root: a challenge issued at
    # this height belongs to window `w + 2` and the prologue deletes window `w`'s
    # records, so the two steps provably cannot touch the same entry. Recorded as
    # an equality rather than asserted, because a version that shortened the lag
    # would make it false here first.
    alternative = copy.deepcopy(ledger)
    swapped = execute_block(
        alternative, [], signatures.oracle, issue_before_prologue=True
    )

    assignment_block = _run(scenario, signatures, [])
    scenario.notes["issue_before_prologue_commits_the_same_root"] = (
        swapped.resulting_state_root == assignment_block.resulting_state_root
    )
    scenario.notes["issue_before_prologue_assigns_the_same_window"] = (
        swapped.assigned_window == assignment_block.assigned_window
    )
    scenario.notes["assigned_window"] = assignment_block.assigned_window
    record = ledger.assignments[MEASURED_WINDOW]
    scenario.notes["assignment_record_bytes"] = len(record)
    scenario.notes["window_one_records_were_deleted"] = MEASURED_WINDOW not in {
        window for window, _seat in ledger.window_records()
    }
    scenario.notes["retained_window_span"] = sorted(
        {window for window, _seat in ledger.window_records()}
    )

    alice_nonce = ledger.nonce(ALICE_ESCROW)
    _run(scenario, signatures, [
        Step("alice_mints_her_measured_cycle", _mint_node(
            signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
            ALICE_SEAT, ALICE_ESCROW, alice_nonce + 1)),
        # A machine that failed its measured cycle mints successfully and
        # receives nothing. That is what a failed cycle looks like from the
        # operator's side: the walk runs, finds no accrued bit, issues zero, and
        # advances the mark — so the second attempt has nothing left to walk.
        Step("bob_mints_and_receives_nothing", _mint_node(
            signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY,
            BOB_SEAT, BOB_ESCROW, ledger.nonce(BOB_ESCROW) + 1)),
        Step("bob_mints_again", _mint_node(
            signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY,
            BOB_SEAT, BOB_ESCROW, ledger.nonce(BOB_ESCROW) + 2)),
        Step("alice_mints_her_referral_leg", _mint_referral(
            signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY,
            ALICE_ESCROW, alice_nonce + 2)),
    ])
    scenario.notes["alice_balance"] = ledger.balance(ALICE_ESCROW)
    scenario.notes["bob_balance"] = ledger.balance(BOB_ESCROW)
    scenario.notes["pool_after_mint"] = dict(ledger.pool)
    scenario.notes["assigned_permissions"] = ledger.assigned_permissions
    return scenario, signatures


# --- scenario two: a dispute that moves the winner set ----------------------


def disputed_scenario() -> tuple[Scenario, Signatures]:
    """Two perfect machines, six voided slots, and a winner set that moves.

    The counterfactual is run from a copy of the very ledger the dispute block
    executed against, so the two chains are identical up to that block by
    construction rather than by a fixture stated twice.
    """
    signatures = Signatures()
    scenario, alice = _seated_chain(signatures, "disputed", referred=False)
    ledger = scenario.ledger
    bob = Responder(signatures, ledger, BOB_SEAT, BOB_ESCROW, BOB_SIGNER_KEY)

    def respond(height: int, issued: list[int]) -> list[bytes]:
        return alice(height, issued) + bob(height, issued)

    heights, recorded = run_quiet_heights(
        ledger, DISPUTE_HEIGHT - 1, signatures.oracle, respond=respond
    )
    scenario.skipped_blocks += heights
    scenario.audit_blocks = list(recorded)
    scenario.notes["alice_challenges"] = len(alice.challenged)
    scenario.notes["bob_challenges"] = len(bob.challenged)
    scenario.notes["responses_accepted"] = _accepted_responses(recorded)
    scenario.notes["response_fees_charged"] = _response_fees(recorded)
    scenario.notes["no_window_records_before_the_dispute"] = not ledger.window_records()

    counterfactual = copy.deepcopy(ledger)
    nonce = ledger.nonce(BOB_ESCROW)
    steps = [
        Step(f"dispute_voids_alice_slot_{slot}", _dispute(
            signatures, ledger, BOB_SIGNER_KEY, ALICE_SEAT, MEASURED_WINDOW,
            slot, nonce + offset))
        for offset, slot in enumerate(DISPUTED_SLOTS, start=1)
    ]
    steps.append(Step("dispute_past_the_cap", _dispute(
        signatures, ledger, BOB_SIGNER_KEY, ALICE_SEAT, MEASURED_WINDOW,
        c.DISPUTE_CAP_SLOTS_PER_SEAT, nonce + len(DISPUTED_SLOTS) + 1)))
    steps.append(Step("dispute_replayed_on_a_voided_slot", _dispute(
        signatures, ledger, BOB_SIGNER_KEY, ALICE_SEAT, MEASURED_WINDOW,
        DISPUTED_SLOTS[0], nonce + len(DISPUTED_SLOTS) + 1)))
    steps.append(Step("dispute_from_an_unrecognised_authority", _dispute(
        signatures, ledger, BOB_SIGNER_KEY, ALICE_SEAT, MEASURED_WINDOW,
        c.DISPUTE_CAP_SLOTS_PER_SEAT, nonce + len(DISPUTED_SLOTS) + 1,
        authority_key=FOREIGN_AUTHORITY_KEY)))
    steps.append(Step("dispute_of_a_window_still_open", _dispute(
        signatures, ledger, BOB_SIGNER_KEY, ALICE_SEAT, MEASURED_WINDOW + 1,
        0, nonce + len(DISPUTED_SLOTS) + 1)))
    dispute_block = _run(scenario, signatures, steps)
    scenario.notes["dispute_results"] = dispute_block.results

    credited, disputed = ledger.window_records()[(MEASURED_WINDOW, ALICE_SEAT)]
    scenario.notes["alice_credited_bits"] = bin(credited).count("1")
    scenario.notes["alice_disputed_bits"] = bin(disputed).count("1")
    scenario.notes["alice_final_slots"] = credited_slots(credited, disputed)
    scenario.notes["alice_uptime_seconds"] = (
        credited_slots(credited, disputed) * c.SLOT_SECONDS
    )

    disputed_assignment = _finish_window(scenario, signatures, ledger, alice, bob)
    scenario.notes["winners_with_the_dispute"] = list(disputed_assignment)

    quiet = Scenario(name="counterfactual", ledger=counterfactual)
    quiet.audit_blocks = []
    intact = _finish_window(
        quiet, signatures, counterfactual,
        alice.fork(counterfactual), bob.fork(counterfactual),
    )
    scenario.notes["winners_without_the_dispute"] = list(intact)
    scenario.notes["counterfactual_blocks"] = len(quiet.blocks)
    scenario.notes["alice_meets_her_cycle_after_a_maximal_dispute"] = (
        credited_slots(credited, disputed) * c.SLOT_SECONDS
        >= (c.SLOTS_PER_WINDOW - c.DISPUTE_CAP_SLOTS_PER_SEAT) * c.SLOT_SECONDS
    )
    return scenario, signatures


def _finish_window(
    scenario: Scenario,
    signatures: Signatures,
    ledger: Ledger,
    alice: Responder,
    bob: Responder,
) -> tuple[int, ...]:
    """Run to the assignment height and return window 1's winner set.

    Each branch gets responders bound to its own ledger, which is what `fork`
    exists for: a responder answers the challenge it is handed at the height it
    is handed one, and it reads its nonce from the ledger it is answering. The
    branch that filed six disputes from Bob's escrow has a different nonce
    sequence from the branch that filed none, so a responder carrying its own
    counter would offer a stale nonce to exactly one of the two.
    """
    def respond(height: int, issued: list[int]) -> list[bytes]:
        return alice(height, issued) + bob(height, issued)

    heights, recorded = run_quiet_heights(
        ledger, ASSIGNMENT_HEIGHT - 1, signatures.oracle, respond=respond
    )
    scenario.skipped_blocks += heights
    scenario.audit_blocks = scenario.audit_blocks + recorded
    _run(scenario, signatures, [])
    return ledger.winners_of(MEASURED_WINDOW)


# --- scenario three: the deadline, from both sides of it --------------------


def deadline_scenario() -> tuple[Scenario, Signatures]:
    """The one execution ordering a chain can observe, run three ways.

    The expiry step follows the transactions, so a response arriving in block
    `c + RESPONSE_DEADLINE_BLOCKS` is the last admissible one. This scenario
    waits for a real challenge — selection is not knowable in advance, which is
    the point of it — copies the chain at that height, and runs the same response
    under three conditions:

    * at `c + 20` under the accepted order: **accepted**;
    * at `c + 21`: `RESPONSE_TOO_LATE`, and the entry is already gone, which is
      why condition 7 precedes condition 8;
    * at `c + 20` with the expiry step moved ahead of the transactions:
      `CHALLENGE_NOT_ISSUED`, **and the seat loses the slot it had just proved**.

    The third is what "expiring first would shorten the deadline to nineteen
    blocks without saying so" costs, stated as a result code and a cleared bit
    rather than as a sentence.
    """
    signatures = Signatures()
    scenario, alice = _seated_chain(signatures, "deadline", referred=False)
    ledger = scenario.ledger

    watcher = Responder(
        signatures, ledger, ALICE_SEAT, ALICE_ESCROW, ALICE_SIGNER_KEY, silent=True
    )
    while not watcher.challenged:
        run_quiet_heights(ledger, ledger.height + 1, signatures.oracle, respond=watcher)
    challenge_height = watcher.challenged[0]
    scenario.notes["challenge_height"] = challenge_height
    scenario.notes["challenge_slot"] = slot_of_height(challenge_height)
    scenario.notes["heights_waited_for_a_challenge"] = (
        challenge_height - ACTIVATION_HEIGHT
    )

    # Offered in the very block that issued it. Condition 6 precedes condition 8,
    # so the report is that the challenge is not open rather than that it was
    # never issued — which it was, in this same block, one step earlier.
    same_block = _run(scenario, signatures, [
        Step("response_in_the_issuing_block", _response(
            signatures, ledger, ALICE_SIGNER_KEY, ALICE_SEAT,
            ledger.height + 1, ledger.nonce(ALICE_ESCROW) + 1)),
    ])
    scenario.notes["same_block_result"] = same_block.results[0]

    deadline = challenge_height + c.RESPONSE_DEADLINE_BLOCKS
    on_time = _branch(signatures, ledger, challenge_height, deadline - 1, deadline)
    scenario.notes["response_at_the_deadline"] = on_time

    late = _branch(signatures, ledger, challenge_height, deadline, deadline + 1)
    scenario.notes["response_one_height_late"] = late

    rejected = _branch(
        signatures, ledger, challenge_height, deadline - 1, deadline,
        expire_first=True,
    )
    scenario.notes["response_under_the_rejected_order"] = rejected
    return scenario, signatures


def _branch(
    signatures: Signatures,
    ledger: Ledger,
    challenge_height: int,
    quiet_until: int,
    respond_at: int,
    expire_first: bool = False,
) -> dict[str, object]:
    """Answer one challenge on a copy of the chain, and report what happened.

    The copy is the point: all three readings run against the identical state,
    so the only thing that differs between them is the height the response is
    offered at and the order the block runs its steps in.
    """
    branch = copy.deepcopy(ledger)
    run_quiet_heights(branch, quiet_until, signatures.oracle)
    before = branch.window_records().get(
        (window_of_height(challenge_height), ALICE_SEAT), (all_slots_credited(), 0)
    )
    raw = _response(
        signatures, branch, ALICE_SIGNER_KEY, ALICE_SEAT, challenge_height,
        branch.nonce(ALICE_ESCROW) + 1,
    )
    block = execute_block(
        branch, [raw], signatures.oracle, expire_before_transactions=expire_first
    )
    after = branch.window_records().get(
        (window_of_height(challenge_height), ALICE_SEAT), (all_slots_credited(), 0)
    )
    assert block.height == respond_at
    return {
        "height": block.height,
        "result": block.results[0],
        "credited_slots_before": credited_slots(*before),
        "credited_slots_after": credited_slots(*after),
        "challenge_survives": (challenge_height, ALICE_SEAT) in branch.open_challenges(),
    }


# --- scenario four: the kinds version eight does not change -----------------


def carried_scenario() -> tuple[Scenario, Signatures]:
    """Every transaction version eight leaves alone, executed under version eight.

    **The bytes are version six's and the commitments are not.** A registration
    under version eight is byte-for-byte a registration under version six, and it
    lands in a version-eight state and produces a version-eight receipt. Version
    seven's own execution vectors record neither, because they record
    version-seven roots and version-seven receipts, and version eight re-versions
    both.

    Every step builder here is version six's, imported rather than restated: what
    is version eight's is the ledger they run against and the roots they commit.
    """
    signatures = Signatures()
    scenario = Scenario(name="carried", ledger=Ledger.from_genesis(genesis()))
    scenario.audit_blocks = []
    ledger = scenario.ledger

    _run(scenario, signatures, [
        Step("alice_registers", _register(
            signatures, ledger, ALICE_IDENTITY, ALICE_KEY, ALICE_SIGNER_KEY)),
        Step("bob_registers", _register(
            signatures, ledger, BOB_IDENTITY, BOB_KEY, BOB_SIGNER_KEY)),
    ])

    # Kinds 1, 19, and 6. The default posture requires a confirmation at every
    # amount, so the unconfirmed transfer is refused and the confirmed one is not;
    # a refusal advances no nonce, which is why the confirmed transfer reuses 1.
    _run(scenario, signatures, [
        Step("alice_transfers_unconfirmed", build_v6(
            signatures, ledger, c.TRANSFER, ALICE_SIGNER_KEY, 1,
            {"recipient_escrow_id": BOB_ESCROW, "amount_atomic": TRANSFER_AMOUNT})),
        Step("alice_transfers_confirmed", _confirmed_transfer(
            signatures, ledger, 1, BOB_ESCROW, TRANSFER_AMOUNT)),
        Step("alice_transfers_to_an_unregistered_recipient", _confirmed_transfer(
            signatures, ledger, 2, ACCEPTED_RECIPIENT, TRANSFER_AMOUNT)),
        Step("alice_attempts_a_direct_issue", build_v6(
            signatures, ledger, c.DIRECT_ISSUE, ALICE_SIGNER_KEY, 2,
            {
                "channel_id": 5,
                "decision_id": bytes(32),
                "beneficiary_escrow_id": ALICE_ESCROW,
                "amount_atomic": 1,
                "authorization": bytes(32),
            })),
    ])

    # Kinds 13, 14, 15, and 16 — the four an identity performs with no signer at
    # all, which is the recovery architecture ADR 0040 exists for.
    second_escrow = escrow_id(ALICE_IDENTITY, 1)
    _run(scenario, signatures, [
        Step("alice_creates_a_second_escrow", build_v6(
            signatures, ledger, c.ESCROW_CREATE, ALICE_KEY, 2,
            {"hub_identity_hash": ALICE_IDENTITY, "fee_escrow_id": ALICE_ESCROW})),
        Step("alice_deletes_the_second_escrow", build_v6(
            signatures, ledger, c.ESCROW_DELETE, ALICE_KEY, 3,
            {
                "hub_identity_hash": ALICE_IDENTITY,
                "fee_escrow_id": ALICE_ESCROW,
                "target_escrow_id": second_escrow,
            })),
        Step("alice_assigns_a_fresh_signer", build_v6(
            signatures, ledger, c.SIGNER_ADD, ALICE_KEY, 4,
            {
                "hub_identity_hash": ALICE_IDENTITY,
                "escrow_id": ALICE_ESCROW,
                "signer_public_key": FRESH_SIGNER_KEY,
            })),
        Step("alice_revokes_the_fresh_signer", build_v6(
            signatures, ledger, c.SIGNER_REVOKE, ALICE_KEY, 5,
            {
                "hub_identity_hash": ALICE_IDENTITY,
                "escrow_id": ALICE_ESCROW,
                "signer_id": signer_id(FRESH_SIGNER_KEY),
            })),
    ])

    # Kind 17, in both directions.
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

    # Kind 18, forty windows after enrolment. No seat is activated on this chain,
    # so the shorthand is exact here for the same reason it is in the setup of
    # the other two: the issue step has nobody in scope to select.
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
    scenario.notes["no_uptime_state_was_written"] = not ledger.uptime
    return scenario, signatures


SCENARIOS = (
    measured_scenario,
    disputed_scenario,
    deadline_scenario,
    carried_scenario,
)
