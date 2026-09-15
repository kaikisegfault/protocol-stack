"""The version-nine ledger state an execution runs against.

A version-nine state is a version-eight state with a timestamp, four entry kinds
and one widened value, so this **extends version eight's `Ledger` rather than
restating it**, exactly as version eight extends version seven's. Value movement,
the registry, the fee, the settlement's first seven steps, the recovery pool, the
mint walk, the uptime carrier and every conservation identity are inherited and
are covered by their own accepted vectors.

**Six things are overridden and they are exactly what version nine changes.**
Genesis binds a timestamp and writes sixteen entries; `apply_assignment` raises
`pool_payable` beside `pool_accrued`; the projection emits the four new kinds and
the widened pool value; the root is version nine's and commits to the timestamp;
the invariants gain the three that are about a ledger rather than an encoding;
and `advance_to` stays refused for version eight's reason.

**The four new maps are typed fields projected into entries**, which is version
six's and version seven's own pattern and not version eight's. Version eight held
its uptime evidence as one raw key-to-value map because
`uptime_transitions.Context` reads that key space directly, so binding it made the
accepted contract model's transitions *the* implementation. Nothing in version
nine reads the raw space: `settlement.py` operates on plain decoded dicts, so
typed fields are both the house style and the exact shape the settlement wants.
`require_entry_shape` runs over the projection at the root, so a field that
encoded badly fails at the commitment rather than surviving as a value nothing
reads.

**The timestamp is a field and not a parameter.** C2 compares a block's stamp
with its predecessor's, so a machine that restarted or restored must hold it, and
the root commits to it because a value two machines could hold differently
without their roots differing is a fork no gate catches.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.economy_transition_v8.ledger import (
    ConservationFailure,
    Ledger as LedgerV8,
    ReferralBalance,
    Seat,
)

from . import contract as c
from .genesis import GENESIS_WINDOW, Genesis, chain_id as genesis_chain_id, genesis_month
from .settlement import Pool
from simulation.economy_transition_v8.slots import window_of_height
from .state import (
    monthly_claim_key,
    monthly_claim_value,
    monthly_figure_key,
    monthly_figure_value,
    settlement_cursor_key,
    settlement_cursor_value,
    state_root,
    unreferred_pool_key,
    unreferred_pool_value,
    window_month_key,
    window_month_value,
)

__all__ = [
    "ConservationFailure",
    "Ledger",
    "ReferralBalance",
    "Seat",
]


@dataclass
class Ledger(LedgerV8):
    """One node's complete canonical state at a height.

    `timestamp` is the stamp of the block at `height`, or the genesis timestamp
    before any block. `accumulating_month` is the month whose figures are open.
    `window_months` holds the open window's month and its predecessor's, and no
    other. `figures` holds only seats that ran, and `claims` only seats that have
    won something.
    """

    timestamp: int = 0
    pool_payable: int = 0
    accumulating_month: int = 0
    window_months: dict[int, int] = field(default_factory=dict)
    figures: dict[tuple[int, int], int] = field(default_factory=dict)
    claims: dict[int, tuple[int, int]] = field(default_factory=dict)

    # --- construction ---------------------------------------------------

    @classmethod
    def from_genesis(cls, genesis: Genesis) -> "Ledger":
        """Sixteen economy entries under a version-nine chain identity.

        The two version nine adds both carry the genesis month. Window zero's
        opening height is height zero, which no chain ever has — a chain starts
        at height one — so genesis is its opening height, and writing its month
        here is the general rule reaching the one height that is a genesis rather
        than a block.
        """
        month = genesis_month(genesis)
        return cls(
            chain_id=genesis_chain_id(genesis),
            supply_limit=genesis.supply_limit,
            fixed_fee=genesis.fixed_transfer_fee,
            verifier_key=genesis.verifier_key,
            dispute_authority_key=genesis.dispute_authority_key,
            channel_issued={index: 0 for index in range(10)},
            channel_outstanding={index: 0 for index in range(10)},
            timestamp=genesis.genesis_timestamp,
            accumulating_month=month,
            window_months={GENESIS_WINDOW: month},
        )

    def advance_to(self, height: int, timestamp: int, uptime=None) -> int:
        """Version eight's shorthand, with the timestamp carried through it.

        **The timestamp is a required argument and not an optional one**, which
        is the one place version nine could have inherited a latent defect: a
        shorthand that advanced the height and left the stamp behind would commit
        a root naming a height the stamp does not belong to, and every later
        block would still satisfy C2 because the stale stamp is smaller. The
        failure would be a wrong root rather than a refusal, which is the
        direction that hides.

        Version eight's refusal is inherited unchanged: the shorthand is valid
        only while no seat is activated, because a version-eight block with no
        transactions still audits every in-scope seat.
        """
        skipped = super().advance_to(height, uptime)
        self.timestamp = timestamp
        return skipped

    # --- the settlement's view of this ledger ----------------------------

    def unreferred_pool(self) -> Pool:
        """The three quantities kind 12 carries, as the settlement's own type.

        Returned by value and written back through `write_pool`, so the ledger
        holds one copy of each quantity and the settlement holds none.
        """
        return Pool(
            accrued=self.pool_accrued,
            payable=self.pool_payable,
            minted=self.pool_minted,
        )

    def write_pool(self, pool: Pool) -> None:
        self.pool_accrued = pool.accrued
        self.pool_payable = pool.payable
        self.pool_minted = pool.minted

    def claim(self, seat_id: int) -> tuple[int, int]:
        """A seat's claim, or the absent pair. A zero claim is never written."""
        return self.claims.get(seat_id, (0, 0))

    # --- the assignment prologue -----------------------------------------

    def apply_assignment(self, assignment, accruals, unreferred) -> None:
        """Version seven's steps 5 through 8, with `payable` raised beside `accrued`.

        The unreferred accrual is the only place a unit enters the pool, so it is
        the only place `payable` rises. Raising them together is what makes the
        first pool identity hold at every height rather than only after a
        settlement.
        """
        super().apply_assignment(assignment, accruals, unreferred)
        self.pool_payable += unreferred

    # --- projection -------------------------------------------------------

    def economy_entries(self) -> dict[bytes, bytes]:
        """Version eight's map with kind 12 rewidened and four kinds added."""
        entries = super().economy_entries()
        entries[unreferred_pool_key()] = unreferred_pool_value(
            self.pool_accrued, self.pool_payable, self.pool_minted
        )
        entries[settlement_cursor_key()] = settlement_cursor_value(
            self.accumulating_month
        )
        for window, month in self.window_months.items():
            entries[window_month_key(window)] = window_month_value(month)
        for (month, seat_id), seconds in self.figures.items():
            entries[monthly_figure_key(month, seat_id)] = monthly_figure_value(seconds)
        for seat_id, (accrued, minted) in self.claims.items():
            entries[monthly_claim_key(seat_id)] = monthly_claim_value(accrued, minted)
        return entries

    def state_root(self) -> str:
        return state_root(
            self.chain_id,
            self.height,
            self.timestamp,
            self.supply_limit,
            self.total_supply,
            self.fee_pool,
            self.accounts(),
            self.economy_entries(),
        )

    # --- invariants -------------------------------------------------------

    def monthly_failures(self) -> list[str]:
        """The three invariants that are about a ledger rather than an encoding.

        The other five are the decoders' and fire at the projection; both pool
        identities are `Pool.assert_conserved`'s and are checked here through it.
        """
        failures: list[str] = []
        if not c.MIN_TIMESTAMP_MILLIS <= self.timestamp <= c.MAX_TIMESTAMP_MILLIS:
            failures.append("the state's timestamp is outside the accepted range")

        # Invariant 2. A window month exists for the open window and its
        # predecessor and for no other, once a window has opened at all. Before
        # the first window-opening height only genesis's entry exists.
        window = window_of_height(self.height)
        expected = {window} if window == GENESIS_WINDOW else {window, window - 1}
        if set(self.window_months) != expected:
            failures.append("a window month entry outlived its retention")

        # Invariant 6. Only one month accumulates at a time, and it is the
        # cursor's: a stale figure from another month would be counted into a
        # ranking it does not belong to.
        if any(month != self.accumulating_month for month, _seat in self.figures):
            failures.append("a monthly figure belongs to a month that is not open")

        try:
            self.unreferred_pool().assert_conserved(self.claims)
        except Exception as failure:  # InvariantError, by construction
            failures.append(str(failure))
        return failures

    def conservation_failures(self) -> list[str]:
        """Version eight's identities, and the three the settlement adds."""
        return super().conservation_failures() + self.monthly_failures()
