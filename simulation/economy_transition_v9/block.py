"""Ordered version-nine block execution: a clock, six prologue steps, and the rest.

`ledger-transition-v1` governs, unchanged, and so does everything version eight
inherited from it. **Version nine adds a rule before the prologue and two steps
inside it:**

```text
0. timestamp   C1 and C2 against the agreed header field
1. prologue    assign, settle the closing month, accrue, accumulate, discard
2. issue       write an open challenge for every selected in-scope seat
3. transactions
4. expiry      resolve the challenges issued RESPONSE_DEADLINE_BLOCKS ago
5. conservation, roots, header
```

**The timestamp rules run before anything reads the field**, which is what keeps
every derivation total: a value outside the accepted range has no month, and no
step should ever be handed one. They are block-level conditions and produce no
transaction result, exactly as `ledger-transition-v1`'s height rule does.

**C5 is not here and cannot be reached from here.** `timeline.replay` is what
this module calls, and it takes no clock. A machine admitting a proposal calls
`timeline.accept` instead, before it ever executes the block; that separation is
`calendar-v1`'s and getting it wrong is silent, because a machine that re-applied
the tolerance on replay would reject the chain's own past one tolerance-width
after producing it.

**The prologue's order is normative and two of its six steps are new.** The
settlement runs between version seven's step 7 and its step 8, which makes
"the payout precedes the accrual" an adjacency rather than a rule stated at a
distance; and the figure accumulation runs after step 8 and before the deletion,
because the figures are computed from the very kind-19 records the deletion
removes. Version eight deleted them immediately after the assignment; version
nine moves the deletion to the end of the prologue and changes nothing else about
it.

**`settle_before_accrual` and `delete_before_accumulate` run the rejected
orders**, so a trace can put the accepted reading and the rejected one on
identical inputs. Neither is a configuration option a chain has.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Callable

from simulation.economy_transition.merkle import digest
from simulation.economy_transition_v3.settlement import SeatCycle, referral_accrual
from simulation.economy_transition_v6.block import (
    MAX_ADMITTED,
    MAX_RAW_INPUTS,
    TRANSACTION_TREE_PREFIX,
    Executed,
    InvalidBlock,
    transaction_root,
)
from simulation.economy_transition_v6.envelope import u64, u8
from simulation.economy_transition_v7.settlement import derive_assignment
from simulation.economy_transition_v8.block import (
    _delete_window_records,
    _expiry_step,
    _issue_step,
    _resolved,
)
from simulation.economy_transition_v8.schedule import derive_schedule
from simulation.economy_transition_v8.slots import window_of_height
from simulation.economy_transition_v8.state import seat_window_key
from simulation.common.canonical import CodedError

from . import contract as c
from .execution import Admission, SignatureOracle, admit, execute, receipt_for
from .header import BLOCK_MAGIC, block_header, block_id as derive_block_id
from .ledger import ConservationFailure, Ledger
from .receipt import encode as encode_receipt
from .settlement import close_month
from .state import state_root_frame, state_root_from_frame
from .timeline import Head, replay as replay_timestamp

Responder = Callable[[int, list[int]], list[bytes]]

__all__ = [
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

    Version eight's fields, with the three the settlement adds: the timestamp the
    block carried, the month it settled if any, and the empty month indices the
    single pass jumped.
    """

    def __init__(self, height: int, timestamp: int, previous_state_root: str) -> None:
        self.height = height
        self.timestamp = timestamp
        self.previous_state_root = previous_state_root
        self.resulting_state_root = ""
        self.admissions: list[Admission] = []
        self.executed: list[Executed] = []
        self.assigned_window: int | None = None
        self.issued: list[int] = []
        self.expired: list[tuple[int, int]] = []
        self.lost_slots: list[tuple[int, int]] = []
        self.settled = None
        self.skipped_months: tuple[int, ...] = ()
        self.opened_window: int | None = None
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
    timestamp: int,
    raw_inputs: list[bytes],
    oracle: SignatureOracle,
    settle_before_accrual: bool = True,
    delete_before_accumulate: bool = False,
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
            ledger, timestamp, raw_inputs, oracle, height, previous_root,
            settle_before_accrual, delete_before_accumulate,
        )
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
    settle_before_accrual: bool,
    delete_before_accumulate: bool,
) -> BlockOutcome:
    # Step 0. A timestamp failure rejects the whole block and restores the
    # pre-block state exactly, which is what `execute_block`'s snapshot does.
    try:
        head = replay_timestamp(
            Head(ledger.height, ledger.timestamp), height, timestamp
        )
    except CodedError as refusal:
        raise InvalidBlock(f"{refusal.code}: {refusal}") from refusal

    ledger.height = head.height
    ledger.timestamp = head.timestamp
    outcome = BlockOutcome(height, timestamp, previous_root)

    _prologue(ledger, outcome, settle_before_accrual, delete_before_accumulate)
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


def _prologue(
    ledger: Ledger,
    outcome: BlockOutcome,
    settle_before_accrual: bool,
    delete_before_accumulate: bool,
) -> None:
    """Six ordered steps at an assignment height, and one at every window open.

    The window-month write runs at **every** window-opening height, including
    those below the assignment lag, because a window's month is fixed by the
    timestamp of its first height and that height is not reachable two windows
    later.
    """
    if ledger.height % c.CYCLE_BLOCKS != 0:
        return
    window = window_of_height(ledger.height)
    if window >= c.ASSIGNMENT_LAG_WINDOWS:
        _assignment(
            ledger, outcome, window - c.ASSIGNMENT_LAG_WINDOWS,
            settle_before_accrual, delete_before_accumulate,
        )

    if window in ledger.window_months:
        raise InvalidBlock("a window opened twice")
    ledger.window_months[window] = _month_of(ledger.timestamp)
    outcome.opened_window = window


def _assignment(
    ledger: Ledger,
    outcome: BlockOutcome,
    due: int,
    settle_before_accrual: bool,
    delete_before_accumulate: bool,
) -> None:
    due_month = ledger.window_months.get(due)
    if due_month is None:
        raise InvalidBlock(f"window {due} is assigned with no recorded month")

    measured = derive_schedule(ledger.activations(), due, ledger.uptime)
    seats = _resolved(ledger, measured) if measured else []

    # Steps 1 and 2: version eight's derivation and version seven's settlement
    # steps 1 through 7, applied together by `apply_assignment`.
    accruals: dict[bytes, int] = {}
    unreferred = 0
    assignment = None
    if seats:
        assignment = derive_assignment(due, seats, ledger.pool)
        marks = {
            identity: entry.collected_through_window
            for identity, entry in ledger.referral.items()
        }
        accruals, unreferred = referral_accrual(due, seats, marks)

    def settle() -> None:
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

    def accrue() -> None:
        if assignment is not None:
            ledger.apply_assignment(assignment, accruals, unreferred)
            outcome.assigned_window = due

    # Step 3 then step 4. The payout precedes the accrual because the window
    # being assigned belongs to the new month, so its accrual is the new month's:
    # letting it land first would pay the closing month one window of its
    # successor's accrual, every month, by a day.
    if settle_before_accrual:
        settle()
        accrue()
    else:
        accrue()
        settle()

    # Steps 5 and 6. The deletion must follow the accumulation, because the
    # figures are computed from the records it removes.
    def accumulate() -> None:
        for seat in seats:
            if seat.uptime_seconds:
                key = (due_month, seat.seat_id)
                ledger.figures[key] = ledger.figures.get(key, 0) + seat.uptime_seconds

    def discard() -> None:
        _delete_window_records(ledger, due)
        ledger.window_months.pop(due, None)

    if delete_before_accumulate:
        discard()
        accumulate()
    else:
        accumulate()
        discard()


def _month_of(timestamp: int) -> int:
    from .timeline import month_of

    return month_of(timestamp)


# --- the run between two recorded blocks ------------------------------------


def run_quiet_heights(
    ledger: Ledger,
    target_height: int,
    timestamp_of_height: Callable[[int], int],
    oracle: SignatureOracle,
    respond: Responder | None = None,
) -> tuple[int, list[BlockOutcome]]:
    """Version eight's fast path, with the timestamp carried through it.

    `timestamp_of_height` is the chain's own stamp for a height, supplied rather
    than derived: this module owns no clock and no block rate. It is the one
    place a trace decides how fast its chain runs, and it is what makes a halt
    expressible — a fixture that jumps its stamps across a month boundary is a
    network that was down, and nothing else in this module has to know.

    The beacon is computed from `state_root_frame`, which is the same preimage
    `state_root` is defined through, with only the height and the timestamp
    varying. Version eight split the frame around the height alone; version nine
    carries both, because the timestamp moves at every height too.
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
            failures = ledger.uptime_failures() + ledger.monthly_failures()
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
