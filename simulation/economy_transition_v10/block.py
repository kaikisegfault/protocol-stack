"""Ordered version-ten block execution: version nine's, with the registry step.

```text
0. timestamp   C1 and C2 against the agreed header field
1. prologue    assign, settle the closing month, accrue, accumulate,
               the registry step, discard
2. issue       write an open challenge for every selected in-scope seat
3. transactions
4. expiry      resolve the challenges issued RESPONSE_DEADLINE_BLOCKS ago
5. conservation, the retirement's persistence, roots, header
```

**The registry step sits after the figure accumulation and before the due
window's kind-19 entries are deleted**, because it reads the uptime those
entries carry and nothing else in the chain keeps it. It reads the window's
measured seats from the same single derivation the assignment uses, which is
how every conforming implementation reads them, so the deletion cannot reach
it — but a kernel that read the records lazily would find them gone after the
deletion, and the specification's order is what keeps such a kernel correct.

**Invariant 7 is checked across every block and every opened window**: a
retirement present before must be present after with the same value. A ledger
holds one height, so the check belongs where two heights meet.

Version nine's helpers are imported for every step version ten does not touch,
and `execute_block`, `_prologue`, and the quiet run are restated only because
each names version nine's admission, execution, or prologue as a module global.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Callable

from simulation.common.canonical import CodedError
from simulation.economy_transition_v3.settlement import referral_accrual
from simulation.economy_transition_v6.block import (
    MAX_ADMITTED,
    MAX_RAW_INPUTS,
    Executed,
    InvalidBlock,
    transaction_root,
)
from simulation.economy_transition_v7.settlement import derive_assignment
from simulation.economy_transition_v8.block import (
    _delete_window_records,
    _expiry_step,
    _issue_step,
    _resolved,
)
from simulation.economy_transition_v8.schedule import MeasuredSeat, derive_schedule
from simulation.economy_transition_v8.slots import window_of_height
from simulation.economy_transition_v9.block import BlockOutcome as BlockOutcomeV9
from simulation.economy_transition_v9.header import block_header
from simulation.economy_transition_v9.header import block_id as derive_block_id
from simulation.economy_transition_v9.settlement import close_month
from simulation.economy_transition_v9.timeline import Head, month_of
from simulation.economy_transition_v9.timeline import replay as replay_timestamp

from . import contract as c
from .execution import SignatureOracle, admit, execute, receipt_for
from .ledger import ConservationFailure, Ledger
from .receipt import encode as encode_receipt
from .state import state_root_frame, state_root_from_frame

Responder = Callable[[int, list[int]], list[bytes]]

__all__ = [
    "BlockOutcome",
    "Executed",
    "InvalidBlock",
    "MAX_ADMITTED",
    "MAX_RAW_INPUTS",
    "Responder",
    "execute_block",
    "open_window",
    "registry_step",
    "require_retirement_kept",
    "run_quiet_heights",
    "transaction_root",
]


class BlockOutcome(BlockOutcomeV9):
    """Version nine's fields, with what the registry step did.

    `active_machines` is the count the step computed at an assignment height,
    and none at every other height. `retired` says the step wrote the
    retirement in this block.
    """

    def __init__(self, height: int, timestamp: int, previous_state_root: str) -> None:
        super().__init__(height, timestamp, previous_state_root)
        self.active_machines: int | None = None
        self.retired = False

    @property
    def receipts(self) -> list[bytes]:
        return [encode_receipt(entry.receipt) for entry in self.executed]


def require_retirement_kept(before: int | None, ledger: Ledger) -> None:
    """Invariant 7: once present, the retirement keeps its value at every height."""
    if before is not None and ledger.launch_retired_at != before:
        raise ConservationFailure("the launch key's retirement changed or vanished")


def execute_block(
    ledger: Ledger,
    timestamp: int,
    raw_inputs: list[bytes],
    oracle: SignatureOracle,
) -> BlockOutcome:
    """Execute one block against `ledger`, advancing it to `h + 1`."""
    if len(raw_inputs) > MAX_RAW_INPUTS:
        raise InvalidBlock("more raw inputs than version one permits")
    previous_root = ledger.state_root()
    height = ledger.height + 1
    if height > c.MAX_U64:
        raise InvalidBlock("block height overflow")

    snapshot = deepcopy(ledger.__dict__)
    retired_before = ledger.launch_retired_at
    try:
        outcome = _execute_block(
            ledger, timestamp, raw_inputs, oracle, height, previous_root
        )
        require_retirement_kept(retired_before, ledger)
        return outcome
    except (InvalidBlock, ConservationFailure):
        ledger.__dict__.clear()
        ledger.__dict__.update(snapshot)
        raise


def _execute_block(
    ledger: Ledger,
    timestamp: int,
    raw_inputs: list[bytes],
    oracle: SignatureOracle,
    height: int,
    previous_root: str,
) -> BlockOutcome:
    try:
        head = replay_timestamp(
            Head(ledger.height, ledger.timestamp), height, timestamp
        )
    except CodedError as refusal:
        raise InvalidBlock(f"{refusal.code}: {refusal}") from refusal

    ledger.height = head.height
    ledger.timestamp = head.timestamp
    outcome = BlockOutcome(height, timestamp, previous_root)

    _prologue(ledger, outcome)
    outcome.issued = _issue_step(ledger, previous_root)

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

    outcome.expired, outcome.lost_slots = _expiry_step(ledger)

    ledger.require_conserved()
    outcome.resulting_state_root = ledger.state_root()
    outcome.header = block_header(
        ledger.chain_id,
        height,
        timestamp,
        previous_root,
        outcome.transaction_root,
        outcome.resulting_state_root,
        len(outcome.executed),
    )
    outcome.block_id = derive_block_id(outcome.header)
    return outcome


# --- step 1: the prologue ---------------------------------------------------


def _prologue(ledger: Ledger, outcome: BlockOutcome) -> None:
    """Version nine's prologue, unchanged in every step but the one added."""
    if ledger.height % c.CYCLE_BLOCKS != 0:
        return
    window = window_of_height(ledger.height)
    if window >= c.ASSIGNMENT_LAG_WINDOWS:
        _assignment(ledger, outcome, window - c.ASSIGNMENT_LAG_WINDOWS)

    if window in ledger.window_months:
        raise InvalidBlock("a window opened twice")
    ledger.window_months[window] = month_of(ledger.timestamp)
    outcome.opened_window = window


def _assignment(ledger: Ledger, outcome: BlockOutcome, due: int) -> None:
    """Version nine's steps in version nine's order, with the registry step
    between the accumulation and the deletion."""
    due_month = ledger.window_months.get(due)
    if due_month is None:
        raise InvalidBlock(f"window {due} is assigned with no recorded month")
    outcome.due_month = due_month

    measured = derive_schedule(ledger.activations(), due, ledger.uptime)
    seats = _resolved(ledger, measured) if measured else []

    assignment = None
    accruals: dict[bytes, int] = {}
    unreferred = 0
    if seats:
        assignment = derive_assignment(due, seats, ledger.pool)
        marks = {
            identity: entry.collected_through_window
            for identity, entry in ledger.referral.items()
        }
        accruals, unreferred = referral_accrual(due, seats, marks)

    # Settle the closing month, then accrue, for version nine's reason.
    pool = ledger.unreferred_pool()
    settled, skipped = close_month(
        ledger.accumulating_month,
        due_month,
        ledger.activations(),
        due - 1,
        pool,
        ledger.claims,
        ledger.figures,
    )
    ledger.write_pool(pool)
    ledger.accumulating_month = due_month
    outcome.settled = settled
    outcome.skipped_months = skipped
    if assignment is not None:
        ledger.apply_assignment(assignment, accruals, unreferred)
        outcome.assigned_window = due

    for seat in seats:
        if seat.uptime_seconds:
            key = (due_month, seat.seat_id)
            ledger.figures[key] = ledger.figures.get(key, 0) + seat.uptime_seconds

    outcome.active_machines, outcome.retired = registry_step(ledger, due, measured)

    _delete_window_records(ledger, due)
    ledger.window_months.pop(due, None)


def registry_step(
    ledger: Ledger, due: int, measured: list[MeasuredSeat]
) -> tuple[int, bool]:
    """Mark the machines whose seats met `due`, count them, and maybe retire.

    1. Every machine-key entry, in ascending seat order, whose seat is in scope
       for `due` with at least `ACTIVITY_THRESHOLD_SECONDS` of uptime, gets
       `last_met_window = due`.
    2. The count is the entries whose mark is nonzero and equals `due`. It is
       computed, never stored, because every machine it counts has just been
       marked.
    3. With no retirement present and the count at the cutoff, the retirement
       is written at this height, and never removed.

    **The count excludes a mark of 0** (ADR 0103). Zero means none, so at the
    window-0 assignment, where no seat is in scope and nothing can be marked,
    every unmarked key would otherwise be counted as having met window 0, and a
    hundred keys registered in the first two windows would retire the launch
    key before any machine had met a cycle.

    "Met" is the uptime test, whatever the accumulation cap or the seat's span
    says, because ADR 0101 reads the answer as the uptime record.
    """
    met = {
        seat.seat_id
        for seat in measured
        if seat.uptime_seconds >= c.ACTIVITY_THRESHOLD_SECONDS
    }
    for seat_id in sorted(ledger.machine_keys):
        if seat_id in met:
            entry = ledger.machine_keys[seat_id]
            ledger.machine_keys[seat_id] = replace(entry, last_met_window=due)
    count = sum(
        1
        for entry in ledger.machine_keys.values()
        if entry.last_met_window != 0 and entry.last_met_window == due
    )
    retire = (
        ledger.launch_retired_at is None
        and count >= c.LAUNCH_RETIREMENT_ACTIVE_MACHINES
    )
    if retire:
        ledger.launch_retired_at = ledger.height
    return count, retire


def open_window(ledger: Ledger) -> BlockOutcome:
    """The prologue alone, at a window-opening height the caller has set.

    Version nine's evidence harness, for a population a chain of blocks cannot
    reach in a recorded run: the caller owns the height, the stamp, and the
    kind-19 records a window's challenges would have written. `execute_block`
    remains the only thing a chain runs. Invariant 7 and the conservation
    identities are checked here as a block would check them.
    """
    if ledger.height % c.CYCLE_BLOCKS != 0:
        raise InvalidBlock("a window opens only at a window-opening height")
    if not c.MIN_TIMESTAMP_MILLIS <= ledger.timestamp <= c.MAX_TIMESTAMP_MILLIS:
        raise InvalidBlock("the stamp is outside calendar-v1's range")
    retired_before = ledger.launch_retired_at
    outcome = BlockOutcome(ledger.height, ledger.timestamp, "")
    _prologue(ledger, outcome)
    require_retirement_kept(retired_before, ledger)
    ledger.require_conserved()
    return outcome


# --- the run between two recorded blocks ------------------------------------


def run_quiet_heights(
    ledger: Ledger,
    target_height: int,
    timestamp_of_height: Callable[[int], int],
    oracle: SignatureOracle,
    respond: Responder | None = None,
) -> tuple[int, list[BlockOutcome]]:
    """Version nine's fast path over a version-ten ledger.

    A height that opens a window or carries an input is a full block. Every
    other height only issues and expires challenges, which writes no registry
    entry and cannot touch the retirement, and its beacon is the root computed
    from the same frame `state_root` is defined through.
    """
    if target_height < ledger.height:
        raise ConservationFailure("height never decreases")
    recorded: list[BlockOutcome] = []
    count = 0
    frame = _frame(ledger)
    pending: list[bytes] = []
    while ledger.height < target_height:
        height = ledger.height + 1
        timestamp = timestamp_of_height(height)
        if pending or height % c.CYCLE_BLOCKS == 0:
            block = execute_block(ledger, timestamp, pending, oracle)
            recorded.append(block)
            issued = block.issued
            frame = _frame(ledger)
        else:
            beacon = state_root_from_frame(frame, ledger.height, ledger.timestamp)
            head = replay_timestamp(
                Head(ledger.height, ledger.timestamp), height, timestamp
            )
            ledger.height, ledger.timestamp = head.height, head.timestamp
            issued = _issue_step(ledger, beacon)
            expired, _lost = _expiry_step(ledger)
            failures = (
                ledger.uptime_failures()
                + ledger.monthly_failures()
                + ledger.registry_failures()
            )
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
