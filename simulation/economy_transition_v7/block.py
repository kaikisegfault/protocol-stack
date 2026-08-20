"""Ordered version-seven block execution: the prologue, the transactions, the root.

`ledger-transition-v1` governs, unchanged, and so does every construction version
six inherited from it: the only valid next height is `h + 1`, admission failures
are omitted from application execution and from the transaction root, every
admitted transaction appends a receipt whether it succeeds or fails, and the
block is atomic in the height and invariant sense while ordinary transaction
results never reject it. The 146-byte application block header, its schema
version field of `1`, the block-ID label, and the ordered transaction tree are
version one's and are imported from version six rather than re-versioned: version
seven re-versions genesis, the receipt, and the state root explicitly and says
nothing about either, and a version-seven header is already unmistakable because
the chain ID it carries is derived under a version-seven label.

**The cycle assignment is a prologue**, which ADR 0045 derived for version six
and version seven inherits: the last assigned window at any height `h` is
`window_of_height(h) - 2`, so at the first height of window `w + 2` window `w`'s
record must already be in state when the block's transactions run.

**Under version seven the rejected ordering is not merely expensive — it is
unconstructible.** A mint in the boundary block would walk a window whose record
is absent, collect nothing, and still advance its mark past it; the prologue
would then write that window's permissions into `outstanding` with the only seat
that could ever have claimed them already marked past it. `outstanding` would
exceed `claimable + recovery_pool`, the backing identity would fail, and the
block would be rejected whole. Version six had to argue that ordering from a
sentence about heights; version seven's own invariant refuses it.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

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

from . import contract as c
from .execution import Admission, SignatureOracle, admit, execute, receipt_for
from .ledger import ConservationFailure, Ledger
from .receipt import encode as encode_receipt
from .settlement import derive_assignment

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
    "TRANSACTION_TREE_PREFIX",
    "block_header",
    "execute_block",
    "transaction_root",
]


class BlockOutcome:
    """One executed block, and the labels the vectors record it under.

    Version six's is a dataclass whose `receipts` property encodes under version
    six's receipt version. Version seven's receipts differ in exactly those two
    octets, so this holds the same fields and encodes under its own.
    """

    def __init__(self, height: int, previous_state_root: str) -> None:
        self.height = height
        self.previous_state_root = previous_state_root
        self.resulting_state_root = ""
        self.admissions: list[Admission] = []
        self.executed: list[Executed] = []
        self.assigned_window: int | None = None
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
    uptime: dict[int, list[SeatCycle]] | None = None,
    assignment_is_prologue: bool = True,
) -> BlockOutcome:
    """Execute one block against `ledger`, advancing it to `h + 1`.

    `assignment_is_prologue` exists so the trace can run the rejected reading
    against the accepted one on identical inputs. It is not a configuration
    option a chain has; a conforming implementation writes the record first.
    """
    if len(raw_inputs) > MAX_RAW_INPUTS:
        raise InvalidBlock("more raw inputs than version one permits")
    previous_root = ledger.state_root()
    height = ledger.height + 1
    if height > c.MAX_U64:
        raise InvalidBlock("block height overflow")

    # "The block transition is atomic: an internal invariant failure, height
    # error, or resource-bound violation rejects the whole proposed block and
    # preserves the pre-block state." Ordinary transaction results never reach
    # here, because a refusal is a result rather than an exception.
    snapshot = deepcopy(ledger.__dict__)
    try:
        return _execute_block(
            ledger, raw_inputs, oracle, uptime, assignment_is_prologue,
            height, previous_root,
        )
    except (InvalidBlock, ConservationFailure):
        ledger.__dict__.clear()
        ledger.__dict__.update(snapshot)
        raise


def _execute_block(
    ledger: Ledger,
    raw_inputs: list[bytes],
    oracle: SignatureOracle,
    uptime: dict[int, list[SeatCycle]] | None,
    assignment_is_prologue: bool,
    height: int,
    previous_root: str,
) -> BlockOutcome:
    ledger.height = height

    outcome = BlockOutcome(height=height, previous_state_root=previous_root)
    if assignment_is_prologue:
        outcome.assigned_window = _write_due_assignment(ledger, uptime)

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
        receipt = receipt_for(admission.transaction_id, admission.transaction, result)
        outcome.executed.append(
            Executed(
                transaction_id=admission.transaction_id,
                kind=admission.transaction.kind,
                outcome=result,
                receipt=receipt,
            )
        )
    if len(outcome.executed) > MAX_ADMITTED:
        raise InvalidBlock("more admitted transactions than version one permits")

    if not assignment_is_prologue:
        outcome.assigned_window = _write_due_assignment(ledger, uptime)

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


def _write_due_assignment(
    ledger: Ledger, uptime: dict[int, list[SeatCycle]] | None
) -> int | None:
    """Write window `h / CYCLE_BLOCKS - 2`'s record when `h` opens a window.

    `uptime-measurement-v1` finalises window `w` at the first height of `w + 2`,
    so that is where `w`'s assignment executes and no earlier. A window with no
    finalised record — a chain with no seats in scope — writes nothing, which is
    the same fact as a record with every bit clear.

    **The pool and the seat marks are both read from the ledger**, not from the
    measurement. A `SeatCycle` bundles four fields and only three of them are
    measured: the seat, its uptime, and whether it is inside its own 731 cycles
    come from `uptime-measurement-v1`, while `minted_through_window` is chain
    state the mint will read again. Version six took all four from its caller.
    Version seven does not, because the backing identity is exact only if the
    accumulation cap is applied against the same mark the walk uses, and a caller
    able to supply a stale mark could make a cycle accrue to a seat whose mint can
    no longer reach that window. `conservation.py` states the same rule by leaving
    the mark out of `CycleSeat` altogether.
    """
    if ledger.height % c.CYCLE_BLOCKS != 0:
        return None
    window = ledger.height // c.CYCLE_BLOCKS
    if window < 2:
        return None
    due = window - 2
    measured = (uptime or {}).get(due)
    if not measured:
        return None
    seats = _in_scope(ledger, measured)
    assignment = derive_assignment(due, seats, ledger.pool)
    marks = {
        identity: entry.collected_through_window
        for identity, entry in ledger.referral.items()
    }
    accruals, unreferred = referral_accrual(due, seats, marks)
    ledger.apply_assignment(assignment, accruals, unreferred)
    return due


def _in_scope(ledger: Ledger, measured: list[SeatCycle]) -> list[SeatCycle]:
    """The measured seats with their two chain-state fields read from the chain.

    A `SeatCycle` carries five fields and the measurement establishes three: the
    seat, its uptime, and whether it is inside its own 731 issuance cycles. The
    collection mark and the recorded referrer are seat-entry fields, and both are
    read here from the seat entry rather than from the caller, so a measurement
    can decide who worked and can decide neither who is paid nor which windows a
    cycle may still accrue into.

    A measurement naming a seat no transaction ever purchased describes a machine
    the chain does not know, and there is no seat entry to read. That rejects the
    whole block rather than assigning against an invented zero.
    """
    resolved = []
    for seat in measured:
        entry = ledger.seats.get(seat.seat_id)
        if entry is None:
            raise InvalidBlock("an uptime record names a seat the chain has not sold")
        resolved.append(
            replace(
                seat,
                minted_through_window=entry.minted_through_window,
                referrer_account_id=entry.referrer_hub_identity,
            )
        )
    return resolved
