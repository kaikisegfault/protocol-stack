"""Ordered version-eight block execution: four steps, and the run between them.

`ledger-transition-v1` governs, unchanged, and so does everything version seven
inherited from it: the only valid next height is `h + 1`, admission failures are
omitted from execution and from the transaction root, every admitted transaction
appends a receipt whether it succeeds or fails, ordinary transaction results
never reject a block, and an internal invariant failure, height error, or
resource-bound violation rejects the whole proposed block and restores the
pre-block state exactly. The 146-octet application block header, its schema
version field of `1`, the block-ID label, and the ordered transaction tree are
version one's, imported rather than re-versioned.

**Version eight adds two steps around the transactions:**

```text
1. prologue   assign the due window from state, then delete its evidence
2. issue      write an open challenge for every selected in-scope seat
3. transactions
4. expiry     resolve the challenges issued RESPONSE_DEADLINE_BLOCKS ago
5. conservation, roots, header
```

**The prologue no longer takes a schedule.** Version seven's `execute_block`
accepts an `UptimeSchedule` a caller supplies; version eight derives one from
the seat table and the window records, so a node cannot be handed a different
answer than its peers computed. The collection mark and the recorded referrer
are still read from the seat entry, which is ADR 0055's rule and survives
unchanged: `derive_schedule` returns three fields and `_in_scope` fills the other
two from the chain.

**The expiry step follows the transactions**, and that ordering is observable: a
response arriving in block `c + RESPONSE_DEADLINE_BLOCKS` is counted, and
expiring first would discard the last admissible response to every challenge and
shorten the deadline to nineteen blocks without saying so.
`expire_before_transactions` exists so a trace can run the rejected reading
against the accepted one on identical inputs. It is not a configuration option a
chain has.

**The prologue preceding the issue step is normative and, at the accepted lag of
two windows, unobservable — which is a finding rather than a defect.** A
challenge issued at height `h` belongs to `window_of_height(h)`, its expiry
clears a bit in that same window or in the one before, and the prologue deletes
records for `window_of_height(h) - ASSIGNMENT_LAG_WINDOWS`. With
`ASSIGNMENT_LAG_WINDOWS` at 2 those windows are always disjoint, so the two steps
provably cannot touch the same entry and the two orderings commit to the same
root. `issue_before_prologue` runs the alternative and the recorded vectors
require the roots to be equal, which states what the encoding makes safe rather
than claiming an order the chain could observe. A later version that shortened
the lag to one window would make the ordering load-bearing, and the vector is
where that would be noticed.

**A run of transaction-free heights is not a no-op under version eight**, which
is the one habit a version-seven reader has to unlearn. `run_quiet_heights`
replaces `Ledger.advance_to` once a seat is activated; the ledger refuses the
shorthand there rather than letting it drop evidence.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Callable

from simulation.economy_transition.merkle import digest
from simulation.economy_transition_v3.settlement import SeatCycle, referral_accrual
from simulation.economy_transition_v6.block import (
    BLOCK_HEADER_BYTES,
    BLOCK_HEADER_SCHEMA_VERSION,
    BLOCK_ID_LABEL,
    BLOCK_MAGIC,
    MAX_ADMITTED,
    MAX_RAW_INPUTS,
    TRANSACTION_TREE_PREFIX,
    Executed,
    InvalidBlock,
    block_header,
    transaction_root,
)
from simulation.economy_transition_v6.envelope import u64, u8
from simulation.economy_transition_v7.settlement import derive_assignment

from . import contract as c
from .execution import Admission, SignatureOracle, admit, execute, receipt_for
from .ledger import ConservationFailure, Ledger
from .receipt import encode as encode_receipt
from .schedule import derive_schedule
from .slots import in_scope, is_selected, window_of_height
from .state import open_challenge_parts, seat_window_key, state_root_frame
from .state import state_root_from_frame
from .uptime_transitions import expire_challenge, issue_challenge

Responder = Callable[[int, list[int]], list[bytes]]

__all__ = [
    "BLOCK_HEADER_BYTES",
    "BLOCK_HEADER_SCHEMA_VERSION",
    "BLOCK_ID_LABEL",
    "BLOCK_MAGIC",
    "BlockOutcome",
    "Executed",
    "InvalidBlock",
    "MAX_ADMITTED",
    "MAX_RAW_INPUTS",
    "Responder",
    "TRANSACTION_TREE_PREFIX",
    "block_header",
    "execute_block",
    "run_quiet_heights",
    "transaction_root",
]


class BlockOutcome:
    """One executed block, and the labels the vectors record it under.

    Version seven's fields, with the three the carrier adds: which seats were
    issued a challenge, which challenges expired, and which of those expiries
    cost a slot.
    """

    def __init__(self, height: int, previous_state_root: str) -> None:
        self.height = height
        self.previous_state_root = previous_state_root
        self.resulting_state_root = ""
        self.admissions: list[Admission] = []
        self.executed: list[Executed] = []
        self.assigned_window: int | None = None
        self.issued: list[int] = []
        self.expired: list[tuple[int, int]] = []
        self.lost_slots: list[tuple[int, int]] = []
        self.header = b""
        self.block_id = ""
        self.atomic_failures = 0

    @property
    def admitted_ids(self) -> list[bytes]:
        return [entry.transaction_id for entry in self.executed]

    @property
    def receipts(self) -> list[bytes]:
        return [encode_receipt(entry.receipt) for entry in self.executed]

    @property
    def results(self) -> list[str]:
        return [entry.result for entry in self.executed]

    @property
    def transaction_root(self) -> str:
        return transaction_root(self.admitted_ids).hex()


def execute_block(
    ledger: Ledger,
    raw_inputs: list[bytes],
    oracle: SignatureOracle,
    expire_before_transactions: bool = False,
    issue_before_prologue: bool = False,
) -> BlockOutcome:
    """Execute one block against `ledger`, advancing it to `h + 1`."""
    if len(raw_inputs) > MAX_RAW_INPUTS:
        raise InvalidBlock("more raw inputs than version one permits")
    previous_root = ledger.state_root()
    height = ledger.height + 1
    if height > c.MAX_U64:
        raise InvalidBlock("block height overflow")

    snapshot = deepcopy(ledger.__dict__)
    try:
        return _execute_block(
            ledger, raw_inputs, oracle, height, previous_root,
            expire_before_transactions, issue_before_prologue,
        )
    except (InvalidBlock, ConservationFailure):
        ledger.__dict__.clear()
        ledger.__dict__.update(snapshot)
        raise


def _execute_block(
    ledger: Ledger,
    raw_inputs: list[bytes],
    oracle: SignatureOracle,
    height: int,
    previous_root: str,
    expire_before_transactions: bool,
    issue_before_prologue: bool,
) -> BlockOutcome:
    ledger.height = height
    outcome = BlockOutcome(height=height, previous_state_root=previous_root)

    if issue_before_prologue:
        outcome.issued = _issue_step(ledger, previous_root)
        outcome.assigned_window = _prologue(ledger)
    else:
        outcome.assigned_window = _prologue(ledger)
        outcome.issued = _issue_step(ledger, previous_root)

    if expire_before_transactions:
        outcome.expired, outcome.lost_slots = _expiry_step(ledger)

    for raw in raw_inputs:
        admission = admit(raw, ledger.chain_id, oracle)
        outcome.admissions.append(admission)
        if not admission.admitted:
            continue
        assert admission.transaction is not None
        assert admission.transaction_id is not None
        before = ledger.state_root()
        result = execute(ledger, admission.transaction, oracle)
        if not result.succeeded:
            # Failed-transition atomicity, checked rather than asserted: a
            # refusal writes nothing, so the commitment over the whole state
            # must be the value it was before the transaction was offered.
            if ledger.state_root() != before:
                raise InvalidBlock("a refused transaction changed the state")
            outcome.atomic_failures += 1
        outcome.executed.append(
            Executed(
                transaction_id=admission.transaction_id,
                kind=admission.transaction.kind,
                outcome=result,
                receipt=receipt_for(
                    admission.transaction_id, admission.transaction, result
                ),
            )
        )
    if len(outcome.executed) > MAX_ADMITTED:
        raise InvalidBlock("more admitted transactions than version one permits")

    if not expire_before_transactions:
        outcome.expired, outcome.lost_slots = _expiry_step(ledger)

    ledger.require_conserved()
    outcome.resulting_state_root = ledger.state_root()
    outcome.header = block_header(
        ledger.chain_id,
        height,
        previous_root,
        outcome.transaction_root,
        outcome.resulting_state_root,
        len(outcome.executed),
    )
    outcome.block_id = digest(BLOCK_ID_LABEL, outcome.header).hex()
    return outcome


# --- step 1: the prologue ---------------------------------------------------


def _prologue(ledger: Ledger) -> int | None:
    """Assign window `h / CYCLE_BLOCKS - 2` from state, then delete its records.

    **Nothing is supplied.** The measured seats are derived from the seat table
    and the window records, so record completeness is structural: a seat cannot
    be omitted, and a seat with no record is present with a full credit rather
    than absent.

    The deletion runs whether or not an assignment was written, because a window
    with no in-scope seats has no records either and deleting nothing is the same
    fact. Running it unconditionally is what makes invariant 5 — exactly two
    windows retained at every height, including a boundary height — hold without
    a second rule about which boundary heights delete.
    """
    if ledger.height % c.CYCLE_BLOCKS != 0:
        return None
    window = ledger.height // c.CYCLE_BLOCKS
    if window < c.ASSIGNMENT_LAG_WINDOWS:
        return None
    due = window - c.ASSIGNMENT_LAG_WINDOWS

    measured = derive_schedule(ledger.activations(), due, ledger.uptime)
    assigned: int | None = None
    if measured:
        seats = _resolved(ledger, measured)
        assignment = derive_assignment(due, seats, ledger.pool)
        marks = {
            identity: entry.collected_through_window
            for identity, entry in ledger.referral.items()
        }
        accruals, unreferred = referral_accrual(due, seats, marks)
        ledger.apply_assignment(assignment, accruals, unreferred)
        assigned = due

    _delete_window_records(ledger, due)
    return assigned


def _resolved(ledger: Ledger, measured: list) -> list[SeatCycle]:
    """The derived seats with their two chain-state fields read from the chain.

    ADR 0055's rule, unchanged by the carrier and enforced by the shape of what
    it is handed: `derive_schedule` returns three fields, so the collection mark
    and the recorded referrer cannot arrive from a measurement even by accident.
    A measurement can decide who worked and can decide neither who is paid nor
    which windows a cycle may still accrue into.

    **The missing-seat refusal is unreachable under version eight**, and that is
    the carrier's whole point rather than an oversight. Version seven took its
    measurement from a caller, so a schedule could name a machine the chain had
    never sold; version eight derives the seat set from the seat table itself, so
    every seat it names is one this loop is about to find. It is kept as the
    named refusal rather than an assertion, because a later version that
    reintroduced a supplied schedule would need it back and should find it here.
    """
    resolved: list[SeatCycle] = []
    for seat in measured:
        entry = ledger.seats.get(seat.seat_id)
        if entry is None:
            raise InvalidBlock("a derived schedule names a seat the chain has not sold")
        resolved.append(
            SeatCycle(
                seat_id=seat.seat_id,
                uptime_seconds=seat.uptime_seconds,
                in_span=seat.in_span,
                minted_through_window=entry.minted_through_window,
                referrer_account_id=entry.referrer_hub_identity,
            )
        )
    return resolved


def _delete_window_records(ledger: Ledger, window: int) -> None:
    """Every kind-19 entry for one window, removed in ascending seat order.

    The order is not observable — a deletion leaves no trace of when it happened
    — and it is written this way so that a reader comparing this loop with the
    issue step and the expiry step finds the same rule in all three.
    """
    prefix = u8(c.SEAT_WINDOW_ENTRY) + u64(window)
    for key in sorted(key for key in ledger.uptime if key.startswith(prefix)):
        del ledger.uptime[key]


# --- step 2: the issue step -------------------------------------------------


def _issue_step(ledger: Ledger, previous_root: str) -> list[int]:
    """One open challenge per selected in-scope seat, in ascending seat order.

    The beacon is the block's own `previous_state_root`, which is already
    computed, read once at the height it belongs to, and never stored. A retained
    ring of past roots would be new consensus state whose only purpose is to
    re-derive something already derived.
    """
    beacon = bytes.fromhex(previous_root)
    height = ledger.height
    window = window_of_height(height)
    context = ledger.uptime_context()
    issued: list[int] = []
    for seat_id in sorted(ledger.seats):
        seat = ledger.seats[seat_id]
        if not seat.is_activated or not in_scope(seat.activation_height, window):
            continue
        if not is_selected(beacon, seat_id, height):
            continue
        try:
            issue_challenge(context, height, seat_id)
        except ValueError as collision:
            raise InvalidBlock(str(collision)) from collision
        issued.append(seat_id)
    return issued


# --- step 4: the expiry step ------------------------------------------------


def _expiry_step(ledger: Ledger) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Resolve and delete every challenge issued `RESPONSE_DEADLINE_BLOCKS` ago.

    Returns what expired and which of those cost the seat a slot. An answered
    challenge is deleted and nothing else is written; an outstanding one clears
    the seat's bit for the slot of its *challenge* height, which is the model's
    slot-close sweep made incremental and exact.
    """
    height = ledger.height
    if height <= c.RESPONSE_DEADLINE_BLOCKS:
        return [], []
    due = height - c.RESPONSE_DEADLINE_BLOCKS
    prefix = u8(c.OPEN_CHALLENGE_ENTRY) + u64(due)
    context = ledger.uptime_context()
    expired: list[tuple[int, int]] = []
    lost: list[tuple[int, int]] = []
    for key in sorted(key for key in ledger.uptime if key.startswith(prefix)):
        challenge_height, seat_id = open_challenge_parts(key)
        before = ledger.uptime.get(
            seat_window_key(window_of_height(challenge_height), seat_id)
        )
        expire_challenge(context, challenge_height, seat_id)
        after = ledger.uptime.get(
            seat_window_key(window_of_height(challenge_height), seat_id)
        )
        expired.append((challenge_height, seat_id))
        if after != before:
            lost.append((challenge_height, seat_id))
    return expired, lost


# --- the run between two recorded blocks ------------------------------------


def run_quiet_heights(
    ledger: Ledger,
    target_height: int,
    oracle: SignatureOracle,
    respond: Responder | None = None,
) -> tuple[int, list[BlockOutcome]]:
    """Every height up to `target_height`, mostly with no transaction offered.

    **This is not `advance_to` and it does not stand in for anything.** It runs
    the issue step and the expiry step at every height, because under version
    eight a block with no transactions still audits every in-scope seat. Two
    kinds of height run the whole block transition instead — one that opens a
    window, and one a responder has raw inputs for — so the prologue, the
    conservation check, and the header are never skipped; those outcomes are
    returned so a trace can record them.

    `respond(height, issued)` is offered the seats a challenge was just issued
    to and returns the raw inputs for the *next* height. It exists because
    selection is not knowable until the block that performs it has run: a trace
    cannot pre-compute which of its own machines will be audited, which is the
    property that makes the audit unpredictable in the first place.

    The beacon is computed from `state_root_frame`, which is the same preimage
    `state_root` is defined through, with only the height field varying. Nothing
    but the issue step and the expiry step can change the state at a quiet height
    — there are no transactions — so the frame is rebuilt exactly when one of
    them writes, and the run commits the same roots as calling `execute_block`
    with no inputs at every height while costing a fraction of it.
    """
    if target_height < ledger.height:
        raise ConservationFailure("height never decreases")
    recorded: list[BlockOutcome] = []
    count = 0
    frame = _frame(ledger)
    pending: list[bytes] = []
    while ledger.height < target_height:
        height = ledger.height + 1
        if pending or height % c.CYCLE_BLOCKS == 0:
            block = execute_block(ledger, pending, oracle)
            recorded.append(block)
            issued = block.issued
            frame = _frame(ledger)
        else:
            beacon = state_root_from_frame(frame, ledger.height)
            ledger.height += 1
            issued = _issue_step(ledger, beacon)
            expired, _lost = _expiry_step(ledger)
            failures = ledger.uptime_failures()
            if failures:
                raise ConservationFailure("; ".join(sorted(set(failures))))
            if issued or expired:
                frame = _frame(ledger)
        pending = list(respond(height, issued)) if respond is not None else []
        count += 1
    if pending:
        raise ConservationFailure("a responder was left holding an unoffered input")
    return count, recorded


def _frame(ledger: Ledger) -> tuple[bytes, bytes]:
    return state_root_frame(
        ledger.chain_id,
        ledger.supply_limit,
        ledger.total_supply,
        ledger.fee_pool,
        ledger.accounts(),
        ledger.economy_entries(),
    )
