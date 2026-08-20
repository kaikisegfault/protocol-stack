"""The version-seven ledger state an execution runs against.

A version-seven state is a version-six state with the ten `carry` entries gone
and one `recovery_pool` entry in their place, so this **extends version six's
`Ledger` rather than restating it**. Value movement, the account map inside the
registry, the fee, the issuing rule, and every structural invariant are version
six's, verified by 499 recorded execution vectors, and copying them here to
change where an indivisible remainder goes is the failure mode ADR 0046 named
when it deleted version four's codec.

**Six things are overridden and they are exactly what version seven changes.**
Genesis writes fourteen entries rather than twenty-three; the assignment
prologue writes the extended record and the pool it leaves behind; the projection
emits kind 17 and no kind 7; the root is the version-seven root; the channel cap
predicate reads the version-three manifest; and the carry identity is replaced by
two identities.

**Subclassing rather than duck-typing is deliberate.** Version six's fourteen
transitions are imported unchanged and their parameter is annotated `Ledger`; a
sibling class satisfying the same attributes would make every one of those
annotations a false statement that happened to work. A subclass makes a
version-seven ledger a version-six ledger, which is what the fourteen transitions
actually require of it.

**The inherited `carry` map is required to stay empty**, rather than being left
as dead state. Version seven has no transition that writes it and no projection
that reads it, so an entry appearing there is a defect in this package, and the
cheapest place to catch it is the invariant that runs after every block.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from simulation.economy_transition_v6.ledger import (
    ConservationFailure,
    Ledger as LedgerV6,
    ReferralBalance,
    Seat,
)

from . import contract as c
from .genesis import Genesis, chain_id as genesis_chain_id, initial_economy_entries
from .settlement import Assignment, assignment_entry, claimable, empty_pool
from .settlement import outstanding_delta
from .state import (
    channel_key,
    channel_value,
    cycle_assignment_key,
    direct_decision_key,
    recovery_pool_key,
    recovery_pool_value,
    referral_balance_key,
    referral_balance_value,
    seat_key,
    seat_value,
    state_root,
    typed_custody_key,
    typed_custody_value,
    unreferred_pool_key,
    unreferred_pool_value,
)

__all__ = [
    "ConservationFailure",
    "Ledger",
    "ReferralBalance",
    "Seat",
]


@dataclass
class Ledger(LedgerV6):
    """One node's complete canonical state at a height.

    `pool` is the recovery pool's five legs and is a state entry. It is not the
    unreferred referral pool, which is `pool_accrued` and `pool_minted` and is
    version three's; the two are unrelated and the names are version six's.

    `assigned_permissions` is not a state entry, exactly as in version six: it is
    the running count of base permissions the chain has assigned, which the
    channel identity is stated over, and it is derivable by summing every
    assignment record's contributing count. It is carried so the two identities
    can be checked after every block without re-walking the whole history.
    """

    # Exactly one recovery pool entry exists on any chain, so the default is the
    # empty pool rather than an empty mapping: a ledger with no pool at all is a
    # state no genesis writes and no transition produces.
    pool: dict[int, int] = field(default_factory=empty_pool)

    # --- construction ---------------------------------------------------

    @classmethod
    def from_genesis(cls, genesis: Genesis) -> "Ledger":
        """Height zero, zero supply, zero accounts, and the fixed tables written.

        Genesis writes the ten channels, the empty recovery pool, the verifier
        key, the empty unreferred pool, and the verified-user counter at zero:
        fourteen entries where version six wrote twenty-three. Every other entry
        arrives through a transition.
        """
        return cls(
            chain_id=genesis_chain_id(genesis),
            supply_limit=genesis.supply_limit,
            fixed_fee=genesis.fixed_transfer_fee,
            verifier_key=genesis.verifier_key,
            channel_issued={index: 0 for index in range(10)},
            channel_outstanding={index: 0 for index in range(10)},
            pool=empty_pool(),
        )

    # --- value movement --------------------------------------------------

    def fits_channel(self, channel: int, amount: int) -> bool:
        """`CHANNEL_CAP`'s predicate, over the version-three manifest's cap.

        The ten caps are identical to version two's — ADR 0053's manifest renames
        one channel and moves no figure — and the binding still moves, because
        the accepted contract a version reads is part of what that version is.
        """
        from simulation.founder_economy_manifest_v3 import contract as manifest

        cap = manifest.CHANNEL_CAPS[manifest.CHANNEL_IDS[channel]]
        return self.channel_issued[channel] + amount <= cap

    # --- the assignment prologue -----------------------------------------

    def apply_assignment(
        self, assignment: Assignment, accruals: dict[bytes, int], unreferred: int
    ) -> None:
        """Write one cycle's record, the pool it leaves, and the accruals.

        Steps 5 through 7 of version seven's settlement: the whole base
        permission per contributing seat enters `outstanding` with nothing moved
        out, and the pool becomes what the cycle's own dust and the residual of
        the pool it just divided add up to. `assignment.pool_after` already holds
        that figure, derived under the specified order, so the ledger commits it
        rather than recomputing it under a second reading.

        `unreferred` is version three's referral pool accrual and is named apart
        from `pool` because the two share nothing but a word.
        """
        _key, value = assignment_entry(assignment)
        if assignment.cycle_window in self.assignments:
            raise ConservationFailure("a cycle window was assigned twice")
        self.assignments[assignment.cycle_window] = value
        for channel, delta in outstanding_delta(assignment).items():
            self.channel_outstanding[channel] += delta
        self.pool = dict(assignment.pool_after)
        for identity, amount in accruals.items():
            entry = self.referral.get(identity, ReferralBalance())
            self.referral[identity] = replace(
                entry, accrued_atomic=entry.accrued_atomic + amount
            )
            self.channel_outstanding[c.REFERRAL_CHANNEL] += amount
        self.pool_accrued += unreferred
        self.channel_outstanding[c.REFERRAL_CHANNEL] += unreferred
        self.assigned_permissions += assignment.assigned_permissions

    # --- projection -------------------------------------------------------

    def economy_entries(self) -> dict[bytes, bytes]:
        """The canonical economy map this state commits to.

        Entry kind 7 is never written here and `require_entry_shape` refuses it,
        so a projection that regressed to version six's carry would fail at the
        root rather than produce a root nothing else would ever match.
        """
        entries = initial_economy_entries(self.verifier_key)
        entries.update(self.registry.entries())
        for index, issued in self.channel_issued.items():
            entries[channel_key(index)] = channel_value(
                issued, self.channel_outstanding[index]
            )
        entries[recovery_pool_key()] = recovery_pool_value(self.pool)
        for kind, amount in self.custody.items():
            entries[typed_custody_key(kind, c.SINGLETON_BENEFICIARY_ID)] = (
                typed_custody_value(amount)
            )
        for seat_id, seat in self.seats.items():
            entries[seat_key(seat_id)] = seat_value(
                seat.hub_identity_hash,
                seat.referrer_hub_identity,
                activation_height=seat.activation_height if seat.is_activated else None,
                minted_through_window=seat.minted_through_window,
            )
        for identity, entry in self.referral.items():
            entries[referral_balance_key(identity)] = referral_balance_value(
                entry.accrued_atomic, entry.minted_atomic, entry.collected_through_window
            )
        for decision in self.decisions:
            entries[direct_decision_key(decision)] = b""
        for window, value in self.assignments.items():
            entries[cycle_assignment_key(window)] = value
        entries[unreferred_pool_key()] = unreferred_pool_value(
            self.pool_accrued, self.pool_minted
        )
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

    def marks(self) -> dict[int, int]:
        """Every seat's collection mark, which is what `claimable` is stated over.

        A seat that has never minted carries the mark its activation wrote, and an
        unactivated seat carries zero. Both are correct inputs to the walk: the
        question the backing identity asks is what the recorded assignments still
        owe, not what their holder is presently able to collect.
        """
        return {
            seat_id: seat.minted_through_window for seat_id, seat in self.seats.items()
        }

    def claimable(self) -> dict[int, int]:
        return claimable(self.marks(), self.assignments)

    def conservation_failures(self) -> list[str]:
        """Every conservation and structural equality version seven states.

        Version six's carry identity is replaced by two identities and every
        other check is version six's, stated here rather than filtered out of the
        inherited method: the inherited one indexes the carry map version seven
        never writes, and a version stating its own invariants in the module a
        reader opens is worth twenty-five lines.

        The registry's structural invariants and the verified-user inequality are
        called rather than restated, because neither has anything to do with the
        recovery pool.
        """
        failures: list[str] = []
        held = sum(balance for balance, _ in self.registry.accounts.values())
        if held + self.fee_pool + sum(self.custody.values()) != self.total_supply:
            failures.append("balances, the fee pool, and custody do not sum to supply")
        if self.total_supply > self.supply_limit:
            failures.append("total supply exceeds the supply limit")
        if self.carry:
            failures.append("version seven wrote an entry under the retired carry kind")

        owed = self.claimable()
        legs = dict(c.BASE_PERMISSION_LEGS)
        for channel in c.RECOVERY_POOL_LEGS:
            expected = self.assigned_permissions * legs[channel]
            actual = self.channel_issued[channel] + self.channel_outstanding[channel]
            if actual != expected:
                failures.append(f"channel {channel} breaks the channel identity")
            backing = owed[channel] + self.pool[channel]
            if backing != self.channel_outstanding[channel]:
                failures.append(f"channel {channel} breaks the backing identity")

        referral_expected = self.assigned_permissions * c.REFERRAL_LEG_ATOMIC
        referral_actual = (
            self.channel_issued[c.REFERRAL_CHANNEL]
            + self.channel_outstanding[c.REFERRAL_CHANNEL]
        )
        if referral_actual != referral_expected:
            failures.append("the referral channel breaks its identity")
        referral_owed = sum(
            entry.accrued_atomic - entry.minted_atomic
            for entry in self.referral.values()
        ) + (self.pool_accrued - self.pool_minted)
        if referral_owed != self.channel_outstanding[c.REFERRAL_CHANNEL]:
            failures.append("referral outstanding is not what the balances owe")

        failures.extend(self._verified_user_failures())
        failures.extend(self.registry.structural_failures())
        for seat in self.seats.values():
            if seat.hub_identity_hash not in self.registry.identities:
                failures.append("a seat names an unregistered identity")
        for identity, entry in self.registry.identities.items():
            held_seats = sum(
                1 for seat in self.seats.values() if seat.hub_identity_hash == identity
            )
            if held_seats != entry.seat_count:
                failures.append("an identity's seat count is not its seat entries")
        return failures
