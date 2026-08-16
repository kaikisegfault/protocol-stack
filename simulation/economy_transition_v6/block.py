"""Ordered version-six block execution: the prologue, the transactions, the root.

`ledger-transition-v1` governs, unchanged: the only valid next height is `h + 1`,
admission failures are omitted from application execution and from the
transaction root, every admitted transaction appends a receipt whether it
succeeds or fails, and the block is atomic in the height and invariant sense
while ordinary transaction results never reject it.

**Two constructions are inherited rather than re-versioned, and both follow from
the same clause.** The version-six specification extends `protocol-primitives-v1`
and states that definitions there govern unless it imposes a narrower rule. It
re-versions genesis, the receipt, and the state root explicitly and says nothing
about the ordered transaction tree or the 146-byte application block header, so
both stay exactly as version one defines them — including the header's schema
version field of `1`. A version-six header is already unmistakable without a new
number, because the chain ID it carries is derived under a version-six label and
both state roots it carries are version-six constructions.

**The cycle assignment is a prologue, and that is derived rather than chosen.**
The specification says the last assigned window at any height `h` is
`window_of_height(h) - 2`. That sentence is a statement about every transaction
executing at `h`, so at the first height of window `w + 2` window `w`'s record
must already be in state when the block's transactions run. Writing it after the
transactions would make the sentence false for every transaction in the boundary
block — and worse than false: a mint in that block would walk a window whose
record is absent, collect nothing, and still advance its mark to `w`, forfeiting
that day permanently. ADR 0045 records the derivation and the trace exercises
both readings.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from simulation.economy_transition.merkle import digest, root
from simulation.economy_transition_v3.settlement import (
    SeatCycle,
    derive_assignment,
    referral_accrual,
)

from . import contract as c
from .envelope import u16, u32, u64
from .execution import Admission, Outcome, SignatureOracle, admit, execute, receipt_for
from .ledger import ConservationFailure, Ledger
from .receipt import Receipt, encode as encode_receipt

BLOCK_MAGIC = b"PSBL"
BLOCK_HEADER_BYTES = 146
BLOCK_HEADER_SCHEMA_VERSION = 1
BLOCK_ID_LABEL = "protocol-stack:v1:block-id"
TRANSACTION_TREE_PREFIX = "protocol-stack:v1:tx"
MAX_RAW_INPUTS = 65_535
MAX_ADMITTED = 65_535


class InvalidBlock(ValueError):
    """A proposed block the height, resource, or invariant rules reject whole."""


@dataclass(frozen=True)
class Executed:
    """One admitted transaction's place in the block."""

    transaction_id: bytes
    kind: int
    outcome: Outcome
    receipt: Receipt

    @property
    def result(self) -> str:
        return self.outcome.result


@dataclass
class BlockOutcome:
    height: int
    previous_state_root: str
    resulting_state_root: str
    admissions: list[Admission] = field(default_factory=list)
    executed: list[Executed] = field(default_factory=list)
    assigned_window: int | None = None
    header: bytes = b""
    block_id: str = ""
    atomic_failures: int = 0

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


def transaction_root(admitted_ids: list[bytes]) -> bytes:
    """Version one's ordered transaction tree, duplicates included."""
    return root(list(admitted_ids), TRANSACTION_TREE_PREFIX)


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

    outcome = BlockOutcome(
        height=height,
        previous_state_root=previous_root,
        resulting_state_root="",
    )
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
    """
    if ledger.height % c.CYCLE_BLOCKS != 0:
        return None
    window = ledger.height // c.CYCLE_BLOCKS
    if window < 2:
        return None
    due = window - 2
    seats = (uptime or {}).get(due)
    if not seats:
        return None
    assignment = derive_assignment(due, seats)
    marks = {
        identity: entry.collected_through_window
        for identity, entry in ledger.referral.items()
    }
    accruals, pool = referral_accrual(due, seats, marks)
    ledger.apply_assignment(assignment, accruals, pool)
    return due


def block_header(
    chain_id: bytes,
    height: int,
    previous_state_root: str,
    transaction_root_hex: str,
    resulting_state_root: str,
    transaction_count: int,
) -> bytes:
    raw = (
        BLOCK_MAGIC
        + u16(BLOCK_HEADER_SCHEMA_VERSION)
        + chain_id
        + u64(height)
        + bytes.fromhex(previous_state_root)
        + bytes.fromhex(transaction_root_hex)
        + bytes.fromhex(resulting_state_root)
        + u32(transaction_count)
    )
    if len(raw) != BLOCK_HEADER_BYTES:
        raise InvalidBlock("application block header is not 146 octets")
    return raw
