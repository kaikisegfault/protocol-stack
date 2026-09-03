"""The version-eight ledger state an execution runs against.

A version-eight state is a version-seven state with two entry kinds added and
nothing removed, so this **extends version seven's `Ledger` rather than
restating it**, exactly as version seven extends version six's. Value movement,
the registry, the fee, the settlement, the recovery pool, the mint walk, and both
conservation identities are version seven's, verified by 590 recorded execution
vectors, and copying them here to add an audit trail is the failure mode ADR 0046
named when it deleted version four's codec.

**Four things are overridden and they are exactly what version eight changes.**
Genesis binds a dispute authority key; the projection emits the two new entry
kinds; the root is the version-eight root; and the invariants gain the six the
specification adds.

**The uptime evidence is one raw key-to-value map and not a pair of typed
dictionaries**, which is deliberate and is the opposite of how every other
surface on this ledger is held. `uptime_transitions.Context` reads and writes the
same key space the state root commits to, so binding that map directly makes the
accepted contract model's two transitions *the* implementation rather than a
sibling of one. A typed shadow would be a second encoding of the same entries
with nothing keeping the two equal.

**`advance_to` is refused once any seat is activated**, which is the one place
a version-seven habit would silently corrupt a version-eight trace. Version six's
shorthand stands in for a run of empty blocks on the argument that such a block
"changes height and nothing else". Under version eight that argument fails: the
issue step and the expiry step run at every height, so a run of transaction-free
blocks issues challenges, expires them, and clears slot bits. It is still exactly
true while no seat is in scope, and no seat is in scope until one is activated,
so the shorthand is kept for the setup segment and refused everywhere else.
`block.run_quiet_heights` is what replaces it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.economy_transition_v3.contract import ACTIVITY_THRESHOLD_SECONDS
from simulation.economy_transition_v3.state import bit_is_set
from simulation.economy_transition_v7.ledger import (
    ConservationFailure,
    Ledger as LedgerV7,
    ReferralBalance,
    Seat,
)

from . import contract as c
from .genesis import Genesis, chain_id as genesis_chain_id
from .slots import window_of_height
from .state import (
    credited_slots,
    decode_cycle_assignment_value,
    decode_open_challenge_value,
    decode_seat_window_value,
    open_challenge_parts,
    seat_window_parts,
    state_root,
)
from .uptime_transitions import Context
from .uptime_transitions import Seat as MeasuredSeatEntry

__all__ = [
    "ConservationFailure",
    "Ledger",
    "ReferralBalance",
    "Seat",
]


@dataclass
class Ledger(LedgerV7):
    """One node's complete canonical state at a height.

    `uptime` holds every kind-18 and kind-19 entry and nothing else, so the
    projection can add it to version seven's map without filtering and the two
    transitions can be handed it without copying.

    `dispute_authority_key` is a genesis field bound into the chain identity
    rather than a state entry, exactly as `supply_limit` and `verifier_key` are,
    so it lives beside them here and appears in no economy key.
    """

    uptime: dict[bytes, bytes] = field(default_factory=dict)
    dispute_authority_key: bytes = bytes(c.DISPUTE_AUTHORITY_KEY_BYTES)

    # --- construction ---------------------------------------------------

    @classmethod
    def from_genesis(cls, genesis: Genesis) -> "Ledger":
        """Version seven's fourteen entries under a version-eight chain identity.

        Version eight writes no open challenge and no seat window record at
        genesis: a challenge is issued by a block, and a window record exists
        only once a seat has lost or had a slot voided.
        """
        return cls(
            chain_id=genesis_chain_id(genesis),
            supply_limit=genesis.supply_limit,
            fixed_fee=genesis.fixed_transfer_fee,
            verifier_key=genesis.verifier_key,
            dispute_authority_key=genesis.dispute_authority_key,
            channel_issued={index: 0 for index in range(10)},
            channel_outstanding={index: 0 for index in range(10)},
        )

    def advance_to(self, height: int, uptime: dict[int, object] | None = None) -> int:
        """Version seven's shorthand, valid only while no seat is activated.

        The refusal is the point. A version-eight block with no transactions
        still issues and expires challenges for every in-scope seat, so standing
        in for one would drop evidence the chain is required to have recorded.
        No seat is in scope before it is activated, so the setup segment of a
        trace is the one place the shorthand remains exactly true.
        """
        if any(seat.is_activated for seat in self.seats.values()):
            raise ConservationFailure(
                "version eight cannot skip a height at which a seat is in scope"
            )
        return super().advance_to(height, uptime)

    # --- what the two new transitions read -------------------------------

    def uptime_context(self) -> Context:
        """The contract model's `Context`, over this ledger's own state.

        `economy` is the live map rather than a copy, so an accepted response or
        dispute writes into the state the root commits to. The two lookup tables
        are rebuilt per call, which is `O(seats + escrows)` and is the model
        paying for exactness: a table built once per block would answer a
        question about the block's first height for a transaction at its last.
        """
        return Context(
            chain_id=self.chain_id,
            height=self.height,
            dispute_authority_key=self.dispute_authority_key,
            seats={
                seat_id: MeasuredSeatEntry(
                    hub_identity_hash=seat.hub_identity_hash,
                    activation_height=seat.activation_height,
                    is_activated=seat.is_activated,
                )
                for seat_id, seat in self.seats.items()
            },
            escrow_owner={
                escrow: entry.owner_hub_identity
                for escrow, entry in self.registry.escrows.items()
            },
            economy=self.uptime,
        )

    def activations(self) -> dict[int, int]:
        """Every activated seat's recorded activation height, for the prologue.

        An unactivated seat is absent rather than present with a zero height,
        because zero is a real height and a purchased seat has never run.
        """
        return {
            seat_id: seat.activation_height
            for seat_id, seat in self.seats.items()
            if seat.is_activated
        }

    # --- projection -------------------------------------------------------

    def economy_entries(self) -> dict[bytes, bytes]:
        """Version seven's map with the uptime evidence added.

        `require_entry_shape` runs over the result at the root, so an entry this
        map should not hold fails at the commitment rather than surviving as a
        value nothing reads.
        """
        entries = super().economy_entries()
        entries.update(self.uptime)
        return entries

    def state_root(self) -> str:
        return state_root(
            self.chain_id,
            self.height,
            self.supply_limit,
            self.total_supply,
            self.fee_pool,
            self.accounts(),
            self.economy_entries(),
        )

    # --- invariants -------------------------------------------------------

    def uptime_failures(self) -> list[str]:
        """The six invariants version eight adds, each checked rather than assumed.

        Invariants 1 and 3 are the decoders' and are obtained by decoding every
        entry, so a value written past them fails here as well as at the root.
        """
        failures: list[str] = []
        window = window_of_height(self.height)
        for key, value in self.uptime.items():
            if key[0] == c.OPEN_CHALLENGE_ENTRY:
                failures.extend(self._challenge_failures(key, value))
            elif key[0] == c.SEAT_WINDOW_ENTRY:
                failures.extend(self._record_failures(key, value, window))
            else:
                failures.append("the uptime map holds an entry of another kind")
        return failures

    def _challenge_failures(self, key: bytes, value: bytes) -> list[str]:
        try:
            decode_open_challenge_value(value)
        except ValueError:
            return ["an open challenge state is not 0 or 1"]
        challenge_height, _seat = open_challenge_parts(key)
        # Invariant 2. The deadline is inclusive, so the oldest live challenge at
        # height `h` is the one issued at `h - RESPONSE_DEADLINE_BLOCKS + 1`: the
        # expiry step of this very block has already deleted the one before it.
        oldest = self.height - c.RESPONSE_DEADLINE_BLOCKS + 1
        if not oldest <= challenge_height <= self.height:
            return ["an open challenge outlived its deadline"]
        return []

    def _record_failures(self, key: bytes, value: bytes, window: int) -> list[str]:
        try:
            credited, disputed = decode_seat_window_value(value)
        except ValueError:
            return ["a seat window record is not a pair of clean bitmaps"]
        failures: list[str] = []
        recorded_window, _seat = seat_window_parts(key)
        # Invariant 5. Exactly two windows are retained, because the prologue
        # deletes the due window's records before anything in that block can
        # write to the window that just opened.
        if recorded_window not in (window, window - 1):
            failures.append("a seat window record outlived its retention")
        # Invariant 4.
        if bin(disputed).count("1") > c.DISPUTE_CAP_SLOTS_PER_SEAT:
            failures.append("a disputed bitmap exceeds the dispute cap")
        # Invariant 6, instantiated on the record rather than argued from the
        # cap: a seat its own evidence credits for every slot still meets the
        # founder-directed threshold after whatever disputes it carries.
        if credited == (1 << c.SLOTS_PER_WINDOW) - 1:
            if credited_slots(credited, disputed) * c.SLOT_SECONDS < (
                ACTIVITY_THRESHOLD_SECONDS
            ):
                failures.append("a maximal dispute failed a fully credited seat")
        return failures

    def conservation_failures(self) -> list[str]:
        """Version seven's identities, and the six the carrier adds."""
        return super().conservation_failures() + self.uptime_failures()

    # --- derived views the trace and the vectors read ---------------------

    def open_challenges(self) -> dict[tuple[int, int], int]:
        """Every live challenge as `(challenge_height, seat) -> state`."""
        return {
            open_challenge_parts(key): decode_open_challenge_value(value)
            for key, value in self.uptime.items()
            if key[0] == c.OPEN_CHALLENGE_ENTRY
        }

    def window_records(self) -> dict[tuple[int, int], tuple[int, int]]:
        """Every retained record as `(window, seat) -> (credited, disputed)`."""
        return {
            seat_window_parts(key): decode_seat_window_value(value)
            for key, value in self.uptime.items()
            if key[0] == c.SEAT_WINDOW_ENTRY
        }

    def winners_of(self, window: int) -> tuple[int, ...]:
        """The winner set a recorded assignment commits to, read back from state.

        Read out of the record rather than kept beside it, because the record is
        what the state root commits to and a parallel copy would be the second
        source of the same fact that every carrier in this version avoids.
        """
        decoded = decode_cycle_assignment_value(self.assignments[window])
        packed = decoded["winner_bitmap"]
        return tuple(
            seat for seat in range(decoded["bitmap_bits"]) if bit_is_set(packed, seat)
        )
