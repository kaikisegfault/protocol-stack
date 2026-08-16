"""The version-six ledger state an execution runs against.

A version-six state is a version-one state — chain ID, supply limit, total
supply, fixed fee, height, fee pool, and the ordered account map — plus one
ordered economy map. This module holds both halves in the shapes a transition
reads and writes, and projects them into the canonical entries `state.py`
encodes. Nothing here decides a transition; `execution.py` does that.

**The account map lives inside the registry.** An escrow's balance and nonce are
version-one account fields keyed by the escrow identifier, so `Registry.accounts`
is the version-one map and there is no second copy. That is what makes the first
structural invariant — every account is an escrow — checkable by comparing two
key sets rather than by reconciling two representations.

The conservation checks are here rather than in the transitions because they are
properties of a state rather than of a step. Every one is an equality: a bound
would admit a defect that lost a term, which is the reason version four gives for
its own two.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from simulation.economy_transition_v3.settlement import Assignment, assignment_entry

from . import contract as c
from .genesis import Genesis, chain_id as genesis_chain_id, initial_economy_entries
from .identity import Registry
from .state import (
    cycle_assignment_key,
    direct_decision_key,
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
from .state import carry_key, carry_value, channel_key, channel_value


class ConservationFailure(ValueError):
    """A state that no sequence of conforming transitions could have produced."""


@dataclass(frozen=True)
class Seat:
    """The 82-byte seat record, as a transition reads it.

    A seat is owned by an identity and carries no address of any kind, which is
    ADR 0041's decision and is why the record lost 37 octets against version
    four's.
    """

    hub_identity_hash: bytes
    referrer_hub_identity: bytes | None
    is_activated: bool = False
    activation_height: int = 0
    minted_through_window: int = 0


@dataclass(frozen=True)
class ReferralBalance:
    accrued_atomic: int = 0
    minted_atomic: int = 0
    collected_through_window: int = 0


@dataclass
class Ledger:
    """One node's complete canonical state at a height.

    `assigned_permissions` is not a state entry. It is the running count of
    base permissions the chain has assigned, which the carry identity is stated
    over, and it is derivable by summing every assignment record's `in_span`
    count. It is carried here so the identity can be checked after every block
    without re-walking the whole assignment history.
    """

    chain_id: bytes
    supply_limit: int
    fixed_fee: int
    verifier_key: bytes
    height: int = 0
    total_supply: int = 0
    fee_pool: int = 0
    registry: Registry = field(default_factory=Registry)
    channel_issued: dict[int, int] = field(default_factory=dict)
    channel_outstanding: dict[int, int] = field(default_factory=dict)
    carry: dict[int, int] = field(default_factory=dict)
    custody: dict[int, int] = field(default_factory=dict)
    seats: dict[int, Seat] = field(default_factory=dict)
    referral: dict[bytes, ReferralBalance] = field(default_factory=dict)
    pool_accrued: int = 0
    pool_minted: int = 0
    decisions: set[bytes] = field(default_factory=set)
    assignments: dict[int, bytes] = field(default_factory=dict)
    assigned_permissions: int = 0

    # --- construction ---------------------------------------------------

    @classmethod
    def from_genesis(cls, genesis: Genesis) -> Ledger:
        """Height zero, zero supply, zero accounts, and the fixed tables written.

        Genesis writes the ten channels, the ten carries, the verifier key, the
        empty unreferred pool, and the verified-user counter at zero, and nothing
        else. Every other entry arrives through a transition.
        """
        return cls(
            chain_id=genesis_chain_id(genesis),
            supply_limit=genesis.supply_limit,
            fixed_fee=genesis.fixed_transfer_fee,
            verifier_key=genesis.verifier_key,
            channel_issued={index: 0 for index in range(10)},
            channel_outstanding={index: 0 for index in range(10)},
            carry={index: 0 for index in range(10)},
        )

    def advance_to(self, height: int, uptime: dict[int, object] | None = None) -> int:
        """Stand in for a run of empty blocks between two segments of a trace.

        An empty block "still advances height and commits the empty transaction
        root", so a run of them changes height and nothing else — with one
        exception, which is why this refuses rather than assumes: a window
        boundary crossed while a finalised uptime record exists would have
        written a cycle assignment, and skipping it would silently lose state.
        Returns the number of blocks the shorthand stands for.
        """
        if height < self.height:
            raise ConservationFailure("height never decreases")
        first_window = (self.height + c.CYCLE_BLOCKS) // c.CYCLE_BLOCKS
        for window in range(max(first_window, 2), height // c.CYCLE_BLOCKS + 1):
            boundary = window * c.CYCLE_BLOCKS
            if (uptime or {}).get(window - 2):
                raise ConservationFailure(
                    f"height {boundary} would have assigned window {window - 2}"
                )
        skipped = height - self.height
        self.height = height
        return skipped

    # --- value movement --------------------------------------------------

    def credit(self, escrow: bytes, amount: int) -> None:
        balance, nonce = self.registry.accounts[escrow]
        self.registry.accounts[escrow] = (self._checked(balance + amount), nonce)

    def debit(self, escrow: bytes, amount: int) -> None:
        balance, nonce = self.registry.accounts[escrow]
        if balance < amount:
            raise ConservationFailure("a debit below zero reached the ledger")
        self.registry.accounts[escrow] = (balance - amount, nonce)

    def set_nonce(self, escrow: bytes, nonce: int) -> None:
        balance, _previous = self.registry.accounts[escrow]
        self.registry.accounts[escrow] = (balance, nonce)

    def balance(self, escrow: bytes) -> int:
        return self.registry.accounts[escrow][0]

    def nonce(self, escrow: bytes) -> int:
        return self.registry.accounts[escrow][1]

    def collect_fee(self, escrow: bytes) -> None:
        """The fixed fee the constitution applies to every accepted transition."""
        self.debit(escrow, self.fixed_fee)
        self.fee_pool = self._checked(self.fee_pool + self.fixed_fee)

    def issue(self, channel: int, amount: int) -> None:
        """Move value from a channel's outstanding into its issued total.

        Channel 8 has no accrual step, so it issues without an outstanding term;
        every other issuing channel must have accrued the amount first, and a
        transition that issued more than it accrued would be a supply defect
        rather than a transaction result.
        """
        if channel != c.VERIFIED_USER_CHANNEL:
            if self.channel_outstanding[channel] < amount:
                raise ConservationFailure("a channel issued more than it accrued")
            self.channel_outstanding[channel] -= amount
        self.channel_issued[channel] = self._checked(
            self.channel_issued[channel] + amount
        )
        self.total_supply = self._checked(self.total_supply + amount)
        if self.total_supply > self.supply_limit:
            raise ConservationFailure("issuance carried total supply past the limit")

    def fits_channel(self, channel: int, amount: int) -> bool:
        """`CHANNEL_CAP`'s predicate, over the accepted manifest's cap."""
        from simulation.founder_economy_v2 import contract as manifest

        cap = manifest.CHANNEL_CAPS[manifest.CHANNEL_IDS[channel]]
        return self.channel_issued[channel] + amount <= cap

    def _checked(self, value: int) -> int:
        if not 0 <= value <= c.MAX_U64:
            raise ConservationFailure("a monetary value left u64")
        return value

    # --- the assignment prologue -----------------------------------------

    def apply_assignment(self, assignment: Assignment, accruals: dict[bytes, int], pool: int) -> None:
        """Write one cycle's record and the accruals that go with it.

        Steps 5 through 7 of the assignment, with the carried remainder moved
        **out of** outstanding rather than added beside it, which is the
        correction version three made and the reason the carry identity is an
        equality rather than an approximation.
        """
        from simulation.economy_transition_v3.settlement import outstanding_delta

        _key, value = assignment_entry(assignment)
        if assignment.cycle_window in self.assignments:
            raise ConservationFailure("a cycle window was assigned twice")
        self.assignments[assignment.cycle_window] = value
        for channel, delta in outstanding_delta(assignment).items():
            self.channel_outstanding[channel] += delta
        for channel in dict(c.BASE_PERMISSION_LEGS):
            self.carry[channel] += assignment.carry_per_channel[channel]
        for identity, amount in accruals.items():
            entry = self.referral.get(identity, ReferralBalance())
            self.referral[identity] = replace(
                entry, accrued_atomic=entry.accrued_atomic + amount
            )
            self.channel_outstanding[c.REFERRAL_CHANNEL] += amount
        self.pool_accrued += pool
        self.channel_outstanding[c.REFERRAL_CHANNEL] += pool
        self.assigned_permissions += assignment.assigned_permissions

    # --- projection -------------------------------------------------------

    def economy_entries(self) -> dict[bytes, bytes]:
        """The canonical economy map this state commits to."""
        entries = initial_economy_entries(self.verifier_key)
        entries.update(self.registry.entries())
        for index, issued in self.channel_issued.items():
            entries[channel_key(index)] = channel_value(
                issued, self.channel_outstanding[index]
            )
        for index, amount in self.carry.items():
            entries[carry_key(index)] = carry_value(amount)
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

    def accounts(self) -> list[tuple[bytes, int, int]]:
        return self.registry.account_list()

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

    def conservation_failures(self) -> list[str]:
        """Every conservation and structural equality, checked as an equality.

        The first is version one's, extended by the typed-custody term version
        two added: value in custody has been issued and has not reached an
        account, so a check that omitted it would report a shortfall after every
        mint.
        """
        failures: list[str] = []
        held = sum(balance for balance, _ in self.registry.accounts.values())
        if held + self.fee_pool + sum(self.custody.values()) != self.total_supply:
            failures.append("balances, the fee pool, and custody do not sum to supply")
        if self.total_supply > self.supply_limit:
            failures.append("total supply exceeds the supply limit")
        for channel, leg in c.BASE_PERMISSION_LEGS:
            expected = self.assigned_permissions * leg
            actual = (
                self.channel_issued[channel]
                + self.channel_outstanding[channel]
                + self.carry[channel]
            )
            if actual != expected:
                failures.append(f"channel {channel} breaks the carry identity")
        referral_expected = self.assigned_permissions * c.REFERRAL_LEG_ATOMIC
        referral_actual = (
            self.channel_issued[c.REFERRAL_CHANNEL]
            + self.channel_outstanding[c.REFERRAL_CHANNEL]
        )
        if referral_actual != referral_expected:
            failures.append("the referral channel breaks its identity")
        owed = sum(
            entry.accrued_atomic - entry.minted_atomic for entry in self.referral.values()
        ) + (self.pool_accrued - self.pool_minted)
        if owed != self.channel_outstanding[c.REFERRAL_CHANNEL]:
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

    def _verified_user_failures(self) -> list[str]:
        """Channel 8 satisfies an inequality, and that is what forfeiture forces.

        The channel has no accrual step, so it has no outstanding term: value is
        issued when it is collected and is otherwise never represented anywhere.
        A chain whose users forfeit ends below the maximum supply rather than
        holding the difference.
        """
        failures: list[str] = []
        channel = c.VERIFIED_USER_CHANNEL
        if self.channel_outstanding[channel] != 0:
            failures.append("the verified-user channel holds an outstanding amount")
        enrolled = sum(
            entry.issued_atomic for entry in self.registry.enrollments.values()
        )
        if self.channel_issued[channel] != enrolled:
            failures.append("verified-user issuance is not what the enrollments record")
        if self.channel_issued[channel] > c.VERIFIED_USER_CHANNEL_CAP:
            failures.append("verified-user issuance exceeds its channel cap")
        return failures

    def require_conserved(self) -> None:
        failures = self.conservation_failures()
        if failures:
            raise ConservationFailure("; ".join(sorted(set(failures))))
