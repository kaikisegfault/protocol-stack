"""Every seat's whole life, through the contract the chain executes.

`economy-scenario-suite-v3` ran a population through `founder-economy-simulator-v3`,
which still has the per-channel carry. This runs one through
`economy-transition-v9`: signed registrations, purchases, activations, and
mints, admitted and executed by the version-nine model, and every window
settled by version nine's own prologue through `block.open_window`.

**What is supplied is exactly what a window's challenges would have written:**
the kind-19 record of each seat that lost a slot or had one voided, written
once the window closes and before its assignment reads it. A seat with no
record is fully credited, as the contract reads it. Everything else is derived
by the contract: who met the cycle, who won it, what the recovery pool took,
who a referral leg reached, and which month a window belongs to.

Four claims are checked at every window rather than once at the end, because a
unit that is lost and later restored is still a defect:

- every Founder Node channel's issued plus outstanding is its leg times the
  permissions assigned;
- the referral channel's issued plus outstanding is the referral leg times the
  same count, and so is every referrer's accrual plus the unreferred pool's;
- a month's pool reaches the seats with that month's best figure;
- balances, the fee pool, and custody sum to supply, and supply to the issued
  channels.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from simulation.economy_transition_v6 import messages
from simulation.economy_transition_v6.identity import escrow_id
from simulation.economy_transition_v6.trace import Signatures, _register
from simulation.economy_transition_v7.state import decode_cycle_assignment_value
from simulation.economy_transition_v8.state import seat_window_key, seat_window_value
from simulation.economy_transition_v9 import contract as c
from simulation.economy_transition_v9.block import open_window
from simulation.economy_transition_v9.envelope import mint_message
from simulation.economy_transition_v9.execution import admit, execute
from simulation.economy_transition_v9.genesis import Genesis
from simulation.economy_transition_v9.ledger import ConservationFailure, Ledger
from simulation.economy_transition_v9.trace import (
    DISPUTE_AUTHORITY_KEY,
    FIXED_FEE,
    SUPPLY_LIMIT,
    VALID_UNTIL,
    VERIFIER_KEY,
    build,
)

from .economy_schedule_v4 import CYCLE_BLOCKS, RECORDED, Fixture

NETWORK_ID = 94
LEGS = dict(c.BASE_PERMISSION_LEGS)



def person(index: int) -> tuple[bytes, bytes, bytes]:
    """Identity, HUB key, and first signer key: three distinct 32-octet values."""
    return (
        bytes([0x40 + index]) * 32,
        bytes([0x50 + index]) * 32,
        bytes([0x60 + index]) * 32,
    )


def genesis(fixture: Fixture = RECORDED) -> Genesis:
    return Genesis(
        network_id=NETWORK_ID,
        genesis_timestamp=fixture.genesis_millis,
        supply_limit=SUPPLY_LIMIT,
        fixed_transfer_fee=FIXED_FEE,
        manifest_digest=bytes.fromhex(c.MANIFEST_DIGEST_HEX),
        verifier_key=VERIFIER_KEY,
        dispute_authority_key=DISPUTE_AUTHORITY_KEY,
    )


@dataclass
class Observed:
    """What the run saw, window by window, for the vectors and the tests."""

    results: Counter = field(default_factory=Counter)
    settlements: list = field(default_factory=list)
    roots: dict[int, str] = field(default_factory=dict)
    peak_recovery_pool: int = 0
    windows_checked: int = 0


class PopulationRun:
    """One chain, from genesis to `stop_window`, checked at every window.

    `stop_window` ends a run early without a last collection round, for restart
    equivalence: a prefix must reach the root the whole run held there. The
    fixture's own end window is where the last round happens.
    """

    def __init__(
        self, fixture: Fixture = RECORDED, stop_window: int | None = None
    ) -> None:
        self.fixture = fixture
        self.stop_window = fixture.end_window if stop_window is None else stop_window
        self.signatures = Signatures()
        self.ledger = Ledger.from_genesis(genesis(fixture))
        self.observed = Observed()

    # --- transactions ------------------------------------------------------

    def escrow(self, index: int) -> bytes:
        return escrow_id(person(index)[0], 0)

    def _submit(self, height: int, raw: bytes, label: str) -> str:
        ledger = self.ledger
        if height < ledger.height:
            raise ConservationFailure("a transaction height went backwards")
        ledger.height, ledger.timestamp = height, self.fixture.stamp(height)
        admission = admit(raw, ledger.chain_id, self.signatures.oracle)
        if not admission.admitted or admission.transaction is None:
            raise ConservationFailure(f"{label} was not admitted: {admission.code}")
        # Atomicity: a refused transaction writes nothing, so its root is
        # compared across the call.
        before = ledger.state_root()
        result = execute(ledger, admission.transaction, self.signatures.oracle)
        if not result.succeeded and ledger.state_root() != before:
            raise ConservationFailure(f"a refused {label} changed the state")
        self.observed.results[(label, result.result)] += 1
        return result.result

    def _signed(self, owner: int, kind: int, body: dict) -> bytes:
        _identity, _key, signer = person(owner)
        nonce = self.ledger.nonce(self.escrow(owner)) + 1
        return build(self.signatures, self.ledger, kind, signer, nonce, body)

    def _mint(self, owner: int, kind: int, seat_id: int, height: int, label: str) -> str:
        identity, key, _signer = person(owner)
        destination = self.escrow(owner)
        message = mint_message(
            self.ledger.chain_id, identity, kind, seat_id, destination, VALID_UNTIL
        )
        body = {
            "destination_escrow_id": destination,
            "hub_signature": self.signatures.sign(key, message),
        }
        if kind != c.MINT_REFERRAL:
            body["seat_id"] = seat_id
        return self._submit(height, self._signed(owner, kind, body), label)

    def _setup(self) -> None:
        for index in range(self.fixture.people):
            identity, key, signer = person(index)
            raw = _register(self.signatures, self.ledger, identity, key, signer)
            self._submit(1, raw, "register")
        for seat_id, (owner, referrer) in sorted(self.fixture.seats.items()):
            message = messages.purchase_message(
                self.ledger.chain_id, person(owner)[0], seat_id, VALID_UNTIL
            )
            body = {
                "seat_id": seat_id,
                "has_referrer": referrer is not None,
                "referrer_escrow_id": (
                    bytes(32) if referrer is None else self.escrow(referrer)
                ),
                "hub_signature": self.signatures.sign(person(owner)[1], message),
            }
            raw = self._signed(owner, c.PURCHASE_SEAT, body)
            self._submit(2, raw, "purchase")

    def _activate(self, seat_id: int) -> None:
        owner, _referrer = self.fixture.seats[seat_id]
        message = messages.activation_message(
            self.ledger.chain_id, person(owner)[0], seat_id, VALID_UNTIL
        )
        body = {
            "seat_id": seat_id,
            "hub_signature": self.signatures.sign(person(owner)[1], message),
        }
        raw = self._signed(owner, c.ACTIVATE_SEAT, body)
        self._submit(self.fixture.activation_height(seat_id), raw, "activate")

    def _collect(self, window: int) -> None:
        """Kind 4, then kind 22, then kind 5, each in ascending order."""
        fixture = self.fixture
        base = window * CYCLE_BLOCKS
        final = window == fixture.end_window
        seats = sorted(fixture.seats.items())
        for seat_id, (owner, _referrer) in seats:
            if final or fixture.node_mints(seat_id, window):
                self._mint(owner, c.MINT_NODE, seat_id, base + 200 + seat_id, "mint_node")
        for seat_id, (owner, _referrer) in seats:
            if final or fixture.pool_mints(seat_id, window):
                self._mint(owner, c.MINT_POOL, seat_id, base + 300 + seat_id, "mint_pool")
        for referrer in fixture.referrers:
            if final or fixture.referral_mints(referrer, window):
                self._mint(referrer, c.MINT_REFERRAL, 0, base + 400 + referrer,
                           "mint_referral")

    # --- windows -----------------------------------------------------------

    def _open(self, window: int) -> None:
        ledger = self.ledger
        height = window * CYCLE_BLOCKS
        ledger.height, ledger.timestamp = height, self.fixture.stamp(height)
        closing = {
            seat: seconds
            for (month, seat), seconds in ledger.figures.items()
            if month == ledger.accumulating_month
        }
        outcome = open_window(ledger)
        if outcome.settled is not None:
            # The closing month's last window is the assigned window's
            # predecessor, and a seat is a candidate once it is in scope there.
            last = window - c.ASSIGNMENT_LAG_WINDOWS - 1
            candidates = tuple(
                seat
                for seat in sorted(self.fixture.seats)
                if self.fixture.first_cycle_window(seat) <= last
            )
            _require_best_performers(outcome.settled, closing, candidates)
            self.observed.settlements.append((window, outcome.settled))
        self._write_records(window - 1)

    def _write_records(self, closed: int) -> None:
        """The evidence a closed window's challenges would have left behind."""
        activations = self.ledger.activations()
        for seat_id in sorted(activations):
            if self.fixture.first_cycle_window(seat_id) > closed:
                continue
            credited, disputed = self.fixture.slots(seat_id, closed)
            if (credited, disputed) == (c.SLOTS_PER_WINDOW, 0):
                continue
            key = seat_window_key(closed, seat_id)
            value = seat_window_value(*self.fixture.bitmaps(credited, disputed))
            self.ledger.uptime[key] = value

    def _check(self, window: int) -> None:
        ledger = self.ledger
        ledger.require_conserved()
        assigned = ledger.assigned_permissions
        for channel, leg in LEGS.items():
            held = ledger.channel_issued[channel] + ledger.channel_outstanding[channel]
            if held != assigned * leg:
                raise ConservationFailure(f"window {window}: channel {channel} drifted")
        referral = c.REFERRAL_LEG_ATOMIC * assigned
        channel = c.REFERRAL_CHANNEL
        if ledger.channel_issued[channel] + ledger.channel_outstanding[channel] != referral:
            raise ConservationFailure(f"window {window}: the referral channel drifted")
        accrued = sum(entry.accrued_atomic for entry in ledger.referral.values())
        if accrued + ledger.pool_accrued != referral:
            raise ConservationFailure(f"window {window}: a referral leg is unaccounted")
        issued = sum(ledger.channel_issued.values())
        if issued != ledger.total_supply:
            raise ConservationFailure(f"window {window}: supply is not what was issued")
        for index in ledger.channel_issued:
            if not ledger.fits_channel(index, 0):
                raise ConservationFailure(f"window {window}: channel {index} over cap")
        pooled = sum(ledger.pool.values())
        self.observed.peak_recovery_pool = max(self.observed.peak_recovery_pool, pooled)
        self.observed.windows_checked += 1

    def root_windows(self) -> tuple[int, ...]:
        """The windows whose root the run records, for restart equivalence.

        The first assignment, a stretch of the first seat's life, the seat
        lapse, the first seat's last cycle, the last cycle of all, and the
        drain, each where the fixture reaches it.
        """
        fixture = self.fixture
        return tuple(sorted({
            2, 100, 430, fixture.last_cycle_window(0),
            fixture.last_span_window, fixture.drain_window,
        }))

    def run(self) -> "PopulationRun":
        self._setup()
        for window in range(0, self.stop_window + 1):
            if window:
                self._open(window)
            for seat_id in sorted(self.fixture.seats):
                if self.fixture.activation_window(seat_id) == window:
                    self._activate(seat_id)
            self._collect(window)
            self._check(window)
            if window in self.root_windows() or window == self.stop_window:
                self.observed.roots[window] = self.ledger.state_root()
        return self


def _require_best_performers(
    settlement, figures: dict[int, int], candidates: tuple[int, ...]
) -> None:
    """The month's winners are exactly its candidates at the best figure.

    Ranked here from the figures the ledger held before the prologue deleted
    them and from the schedule's own candidate set, not by `close_month`, so
    the settlement is checked against the state it read rather than against
    itself. A candidate with no figure ran nothing and ranks at zero.
    """
    if settlement.candidate_count != len(candidates):
        raise ConservationFailure(f"month {settlement.month} ranked the wrong seats")
    if not candidates:
        return
    best = max(figures.get(seat, 0) for seat in candidates)
    winners = tuple(seat for seat in candidates if figures.get(seat, 0) == best)
    if settlement.best_figure != best or settlement.winners != winners:
        raise ConservationFailure(
            f"month {settlement.month} paid {settlement.winners}, not {winners}"
        )


def assignments(ledger: Ledger) -> dict[int, dict]:
    """Every assignment record, decoded, by window."""
    return {
        window: decode_cycle_assignment_value(raw)
        for window, raw in sorted(ledger.assignments.items())
    }
