"""The registry across a population: the cutoff, the limit, the cap, and the span.

The launch key retires when 100 machines meet one assigned cycle, and a machine
may sign 1,000 registrations a window. No recorded chain of blocks reaches
either: every in-scope seat is audited at every height, so a hundred machines
answering their challenges for one window is millions of selections and
thousands of blocks. So these runs use version nine's evidence harness, as
`economy-scenario-suite-v4` does:

- transactions are admitted and executed by the version-ten model one at a
  time, at heights the run sets;
- each window opens through `block.open_window`, which is the prologue a block
  runs, registry step included;
- what a closed window's challenges would have written is supplied as its
  kind-19 records, and a seat with no record is fully credited, as the contract
  reads it.

**Everything the vectors claim about the registry is derived by the contract**:
who met, the count, the retirement, every refusal, and every count a
registration leaves. The harness supplies uptime and nothing else.

**A refused transaction is checked for atomicity, and a bulk success is not.**
A thousand registrations each followed by a full root would cost more than the
rest of the run together. A bulk step that does not succeed fails the run, so no
refusal is ever recorded without its root compared.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.economy_transition_v8.slots import in_scope
from simulation.economy_transition_v8.state import seat_window_key, seat_window_value

from . import contract as c
from .block import BlockOutcome, open_window
from .execution import admit, execute, receipt_for
from .fixture import (
    Builder,
    LAUNCH_KEY,
    Person,
    Signatures,
    genesis,
    machine_key,
    person,
    timestamp_of_height,
)
from .ledger import ConservationFailure, Ledger
from .receipt import encode as encode_receipt

__all__ = [
    "ACTIVATION_HEIGHT",
    "CAP_RUN_WINDOW",
    "CUTOFF_PLAN",
    "FOUNDER",
    "Harness",
    "MACHINES",
    "SPAN_RUN_WINDOW",
    "cutoff_run",
    "span_run",
]

# One founder holds every seat. Seats buy capacity, not identities, so one
# person running many machines is the ordinary case the limit exists for.
FOUNDER = person(0)
MACHINES = 101
ACTIVATION_HEIGHT = c.CYCLE_BLOCKS - 10

# Credited slots per seat in a window, where it is not all 24. Eighteen slots is
# exactly the threshold, and seventeen is one slot below it.
CUTOFF_PLAN: dict[int, dict[int, int]] = {
    1: {98: 18, 99: 17, 100: 12},
    2: {100: 6},
    3: {seat: 17 for seat in range(50, MACHINES)},
}

# The window whose opening assigns window 31, the first cycle a seat that never
# collects cannot hold, and the window whose opening assigns the first cycle
# past a seat's 731.
CAP_RUN_WINDOW = 33
SPAN_RUN_WINDOW = c.ISSUANCE_CYCLES_PER_SEAT + 3


@dataclass
class Harness:
    """One chain, driven a transaction and a window at a time."""

    signatures: Signatures = field(default_factory=Signatures)
    ledger: Ledger = field(default_factory=lambda: Ledger.from_genesis(genesis()))
    results: dict[str, str] = field(default_factory=dict)
    receipts: dict[str, bytes] = field(default_factory=dict)
    raw: dict[str, bytes] = field(default_factory=dict)
    windows: dict[int, BlockOutcome] = field(default_factory=dict)
    notes: dict[str, object] = field(default_factory=dict)

    @property
    def build(self) -> Builder:
        return Builder(self.signatures, self.ledger)

    def at(self, height: int) -> int:
        if height < self.ledger.height:
            raise ConservationFailure("a harness height went backwards")
        self.ledger.height = height
        self.ledger.timestamp = timestamp_of_height(height)
        return height

    def nonce(self, who: Person) -> int:
        return self.ledger.nonce(who.escrow) + 1

    def submit(self, label: str | None, raw: bytes) -> str:
        """Admit and execute one transaction. `label=None` is a bulk success."""
        ledger = self.ledger
        admission = admit(raw, ledger.chain_id, self.signatures.oracle)
        if not admission.admitted or admission.transaction is None:
            raise ConservationFailure(f"{label} was not admitted: {admission.code}")
        before = ledger.state_root() if label is not None else None
        outcome = execute(ledger, admission.transaction, self.signatures.oracle)
        if label is None:
            if not outcome.succeeded:
                raise ConservationFailure(f"a bulk step was refused: {outcome.result}")
            return outcome.result
        if not outcome.succeeded and ledger.state_root() != before:
            raise ConservationFailure(f"a refused {label} changed the state")
        assert admission.transaction_id is not None
        receipt = receipt_for(admission.transaction_id, admission.transaction, outcome)
        self.results[label] = outcome.result
        self.receipts[label] = encode_receipt(receipt)
        self.raw[label] = raw
        return outcome.result

    def open(self, window: int, plan: dict[int, dict[int, int]]) -> BlockOutcome:
        """Open `window`, then write the records of the window it closed."""
        self.at(window * c.CYCLE_BLOCKS)
        outcome = open_window(self.ledger)
        self.windows[window] = outcome
        closed = window - 1
        for seat_id, credited in sorted(plan.get(closed, {}).items()):
            if not in_scope(self.ledger.seats[seat_id].activation_height, closed):
                continue
            self.ledger.uptime[seat_window_key(closed, seat_id)] = seat_window_value(
                (1 << credited) - 1, 0
            )
        return outcome

    # --- the seated population -------------------------------------------

    def seat_population(self, machines: int) -> None:
        """Register the founder, sell and activate every seat, register every key."""
        build = self.build
        self.submit(
            "founder_registers",
            build.registration(FOUNDER, c.LAUNCH_ATTESTER, LAUNCH_KEY, self.at(1) + 1_200),
        )
        height = self.at(2)
        for seat_id in range(machines):
            self.submit(None, build.purchase(
                FOUNDER, seat_id, self.nonce(FOUNDER), height + 1_200))
        height = self.at(ACTIVATION_HEIGHT)
        for seat_id in range(machines):
            self.submit(None, build.activation(
                FOUNDER, seat_id, self.nonce(FOUNDER), height + 1_200))
        height = self.at(ACTIVATION_HEIGHT + 1)
        for seat_id in range(machines):
            self.submit(None, build.machine_registration(
                FOUNDER, seat_id, machine_key(seat_id), self.nonce(FOUNDER),
                height + 1_200))


def _register_many(harness: Harness, seat_id: int, first: int, count: int) -> None:
    """`count` new people, each attested by `seat_id`'s machine."""
    build = harness.build
    height = harness.ledger.height
    for index in range(first, first + count):
        harness.submit(None, build.registration(
            person(index), seat_id, machine_key(seat_id), height + 1_200))


def cutoff_run(through_window: int = CAP_RUN_WINDOW) -> Harness:
    """101 machines, the count at 99 and then 100, the limit, and the cap."""
    harness = Harness()
    harness.seat_population(MACHINES)
    build = harness.build
    for window in range(1, through_window + 1):
        harness.open(window, CUTOFF_PLAN)
        base = window * c.CYCLE_BLOCKS
        if window == 3:
            _window_three(harness, build, base)
        elif window == 4:
            height = harness.at(base + 1)
            harness.submit("launch.refused_once_retired", build.registration(
                person(9_001), c.LAUNCH_ATTESTER, LAUNCH_KEY, height + 1_200))
            harness.submit("limit.the_count_restarts_in_the_next_window",
                           build.registration(person(9_002), 0, machine_key(0),
                                              height + 1_200))
        elif window == 5:
            height = harness.at(base + 1)
            harness.submit("launch.not_revived_when_the_count_falls",
                           build.registration(person(9_003), c.LAUNCH_ATTESTER,
                                              LAUNCH_KEY, height + 1_200))
    return harness


def _window_three(harness: Harness, build: Builder, base: int) -> None:
    """The cutoff at 99, two machines' signatures crossed, and the limit."""
    height = harness.at(base + 1)
    harness.submit("launch.still_signs_at_ninety_nine", build.registration(
        person(1), c.LAUNCH_ATTESTER, LAUNCH_KEY, height + 1_200))
    harness.submit("crossed.a_key_signing_for_another_seat", build.registration(
        person(2), 2, machine_key(1), height + 1_200))
    harness.submit("crossed.a_genuine_signature_under_another_seat", build.registration(
        person(2), 2, machine_key(1), height + 1_200, signed_seat=1))
    harness.submit("limit.the_first", build.registration(
        person(10), 0, machine_key(0), height + 1_200))
    _register_many(harness, 0, 11, c.MACHINE_REGISTRATIONS_PER_WINDOW - 2)
    last = 11 + c.MACHINE_REGISTRATIONS_PER_WINDOW - 2
    harness.submit("limit.the_thousandth", build.registration(
        person(last), 0, machine_key(0), height + 1_200))
    harness.notes["count_after_the_thousandth"] = (
        harness.ledger.machine_keys[0].registrations_in_window
    )
    harness.submit("limit.a_forgery_naming_a_full_machine", build.registration(
        person(last + 1), 0, machine_key(1), height + 1_200))
    harness.submit("limit.the_thousand_and_first", build.registration(
        person(last + 1), 0, machine_key(0), height + 1_200))
    harness.submit("limit.another_machine_still_signs", build.registration(
        person(last + 1), 1, machine_key(1), height + 1_200))


# A span run collects this often, so the accumulation cap never decides a cycle
# and the end of the span is the only thing that does.
SPAN_COLLECTION_WINDOWS = 20


def span_run(through_window: int = SPAN_RUN_WINDOW) -> Harness:
    """One machine, every slot credited, past the end of its seat's 731 cycles."""
    harness = Harness()
    harness.seat_population(1)
    build = harness.build
    for window in range(1, through_window + 1):
        harness.open(window, {})
        if window % SPAN_COLLECTION_WINDOWS == 0:
            height = harness.at(window * c.CYCLE_BLOCKS + 1)
            harness.submit(None, build.mint(
                FOUNDER, c.MINT_NODE, harness.nonce(FOUNDER), height + 1_200,
                seat_id=0))
    return harness
