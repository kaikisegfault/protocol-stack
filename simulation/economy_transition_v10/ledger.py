"""The version-ten ledger state an execution runs against.

A version-ten state is a version-nine state with three entry kinds added, so this
**extends version nine's `Ledger` rather than restating it**, exactly as version
nine extends version eight's. Value movement, the identity registry, the fee,
the settlement, the monthly pool, the uptime carrier, and every conservation
identity are inherited and are covered by their own accepted vectors.

**Four things are added, and they are exactly what version ten adds to a
state:** the build authority key, the machine keys by seat, their inverse, and
the launch key's retirement. The launch key itself is version nine's
`verifier_key` field under its narrower name, because genesis writes it to the
same entry at the same offset.

**The inverse is held as its own map rather than derived from the first**, so
that invariant 2 is a comparison between two things the state holds and a probe
can break it. A derived inverse could never disagree with what it was derived
from, and the check would be vacuous.

**Invariant 7 is not here.** It is a statement about two heights, and a ledger
holds one. `block.require_retirement_kept` checks it across every block and
every window the harness opens.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.economy_transition_v8.slots import window_of_height
from simulation.economy_transition_v9.genesis import GENESIS_WINDOW, genesis_month
from simulation.economy_transition_v9.ledger import (
    ConservationFailure,
    Ledger as LedgerV9,
    ReferralBalance,
    Seat,
)

from . import contract as c
from .genesis import Genesis, chain_id as genesis_chain_id
from .state import (
    MachineKey,
    launch_retirement_key,
    launch_retirement_value,
    machine_key_key,
    machine_key_owner_key,
    machine_key_owner_value,
    machine_key_value,
    state_root,
)

__all__ = [
    "ConservationFailure",
    "Ledger",
    "MachineKey",
    "ReferralBalance",
    "Seat",
    "assigned_window",
]


def assigned_window(height: int) -> int | None:
    """The most recently assigned window at `height`, or none below the lag.

    Window `w` is assigned in the prologue of the first height of window
    `w + 2`, so at every height of window `w + 2` the latest assigned window is
    `w`.
    """
    window = window_of_height(height)
    if window < c.ASSIGNMENT_LAG_WINDOWS:
        return None
    return window - c.ASSIGNMENT_LAG_WINDOWS


@dataclass
class Ledger(LedgerV9):
    """One node's complete canonical state at a height.

    `machine_keys` holds one entry per seat that has registered a key, and
    `machine_key_owners` one per key. `launch_retired_at` is the height that
    retired the launch key, or none while it may still sign.
    """

    build_authority_key: bytes = bytes(c.BUILD_AUTHORITY_KEY_BYTES)
    machine_keys: dict[int, MachineKey] = field(default_factory=dict)
    machine_key_owners: dict[bytes, int] = field(default_factory=dict)
    launch_retired_at: int | None = None

    # --- construction ---------------------------------------------------

    @classmethod
    def from_genesis(cls, genesis: Genesis) -> "Ledger":
        """Version nine's sixteen entries under a version-ten chain identity.

        Genesis writes no machine key, no owner entry, and no retirement. The
        build authority key is bound into the chain identity and held here, as
        the dispute authority key is, and appears in no economy key.
        """
        month = genesis_month(genesis)
        return cls(
            chain_id=genesis_chain_id(genesis),
            supply_limit=genesis.supply_limit,
            fixed_fee=genesis.fixed_transfer_fee,
            verifier_key=genesis.launch_key,
            dispute_authority_key=genesis.dispute_authority_key,
            build_authority_key=genesis.build_authority_key,
            channel_issued={index: 0 for index in range(10)},
            channel_outstanding={index: 0 for index in range(10)},
            timestamp=genesis.genesis_timestamp,
            accumulating_month=month,
            window_months={GENESIS_WINDOW: month},
        )

    @property
    def launch_key(self) -> bytes:
        """Version nine's verifier key, in the narrower role version ten gives it."""
        return self.verifier_key

    # --- what kind 10 reads ---------------------------------------------

    def machine_active(self, seat_id: int) -> bool:
        """ADR 0101's answer: the seat met its most recently assigned cycle.

        A `last_met_window` of 0 means none, and is unambiguous, because no seat
        is in scope in window 0 and no window-0 assignment can mark a machine.
        """
        entry = self.machine_keys.get(seat_id)
        if entry is None or entry.last_met_window == 0:
            return False
        return entry.last_met_window == assigned_window(self.height)

    def active_machine_count(self) -> int:
        return sum(1 for seat_id in self.machine_keys if self.machine_active(seat_id))

    # --- projection -------------------------------------------------------

    def economy_entries(self) -> dict[bytes, bytes]:
        """Version nine's map with entry kinds 24, 25, and 26 added."""
        entries = super().economy_entries()
        for seat_id, entry in self.machine_keys.items():
            entries[machine_key_key(seat_id)] = machine_key_value(entry)
        for key, seat_id in self.machine_key_owners.items():
            entries[machine_key_owner_key(key)] = machine_key_owner_value(seat_id)
        if self.launch_retired_at is not None:
            entries[launch_retirement_key()] = launch_retirement_value(
                self.launch_retired_at
            )
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

    def registry_failures(self) -> list[str]:
        """Invariants 1 through 6, each checked and never assumed."""
        failures: list[str] = []
        assigned = assigned_window(self.height)
        window = window_of_height(self.height)
        for seat_id, entry in self.machine_keys.items():
            seat = self.seats.get(seat_id)
            if seat is None or not seat.is_activated:
                failures.append("a machine key names a seat that is not activated")
            if self.machine_key_owners.get(entry.machine_public_key) != seat_id:
                failures.append("a machine key has no owner entry naming its seat")
            if entry.last_met_window and (
                assigned is None or entry.last_met_window > assigned
            ):
                failures.append("a machine was marked for a window not yet assigned")
            if entry.registration_window > window:
                failures.append("a machine counted registrations for a future window")
            if entry.registrations_in_window > c.MACHINE_REGISTRATIONS_PER_WINDOW:
                failures.append("a machine signed more registrations than its limit")
        for key, seat_id in self.machine_key_owners.items():
            entry = self.machine_keys.get(seat_id)
            if entry is None or entry.machine_public_key != key:
                failures.append("an owner entry names a seat that does not hold its key")
        held = [entry.machine_public_key for entry in self.machine_keys.values()]
        if len(held) != len(set(held)):
            failures.append("two machine-key entries hold the same key")
        return failures

    def conservation_failures(self) -> list[str]:
        """Version nine's identities, and the six registry invariants."""
        return super().conservation_failures() + self.registry_failures()
