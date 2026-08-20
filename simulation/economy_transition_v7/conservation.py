"""The settlement's accounting, and the two identities version seven states.

This is not the chain's ledger. It holds exactly what the two conservation
identities are stated over — the five Founder Node channels, the recovery pool,
the assignment records, and every seat's collection mark — so that the recovery
pool can be checked over a schedule of cycles and mints without a transaction,
an escrow, or a block. The version-seven transaction ledger is a later slice and
will state the same two identities over the same figures.

**The channel identity** says nothing was created or destroyed:

```text
issued(c) + outstanding(c) = assigned_cycle_permissions * leg(c)
```

**The backing identity** says nothing was stranded:

```text
outstanding(c) = claimable(c) + recovery_pool(c)
```

The second is the one this version exists for. `outstanding` is a single number,
so a claim that quietly disappeared would leave the channel identity holding and
simply make `outstanding` larger than anyone could ever mint. Naming both halves
turns that into an inequality against an exact figure.

`claimable` is exact rather than a bound. The accumulation cap is applied at
assignment against the same mark the walk uses, so a seat over the cap accrues no
bit and — because the winner derivation filters on the same predicate — wins no
bit. No bit can exist in a window outside the thirty a mint reaches, and the mark
advance can never step over an uncollected one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.economy_transition_v3.settlement import SeatCycle

from . import contract as c
from .settlement import (
    Assignment,
    Collection,
    InvalidSettlement,
    assignment_entry,
    claimable,
    collect,
    derive_assignment,
    empty_pool,
    outstanding_delta,
    walk_range,
)


class SettlementFailure(ValueError):
    """A settlement state no sequence of conforming cycles could have produced."""


@dataclass(frozen=True)
class CycleSeat:
    """One seat's inputs for one cycle, as the chain already holds them.

    The collection mark is deliberately absent: it lives in the ledger, and a
    caller that supplied it could hand the assignment a different mark from the
    one the mint will use, which is exactly the desynchronisation the
    accumulation cap's exactness rests on not happening.
    """

    seat_id: int
    uptime_seconds: int
    in_span: bool


@dataclass
class SettlementLedger:
    """Five channels, one pool, the assignment records, and every seat's mark."""

    channel_issued: dict[int, int] = field(
        default_factory=lambda: {channel: 0 for channel in c.RECOVERY_POOL_LEGS}
    )
    channel_outstanding: dict[int, int] = field(
        default_factory=lambda: {channel: 0 for channel in c.RECOVERY_POOL_LEGS}
    )
    pool: dict[int, int] = field(default_factory=empty_pool)
    assignments: dict[int, bytes] = field(default_factory=dict)
    marks: dict[int, int] = field(default_factory=dict)
    assigned_permissions: int = 0

    # --- the assignment prologue -----------------------------------------

    def assign(self, cycle_window: int, seats: list[CycleSeat]) -> Assignment:
        """Derive and apply one cycle, reading every mark from this ledger."""
        if cycle_window in self.assignments:
            raise SettlementFailure("a cycle window was assigned twice")
        inputs = [
            SeatCycle(
                seat_id=seat.seat_id,
                uptime_seconds=seat.uptime_seconds,
                in_span=seat.in_span,
                minted_through_window=self.marks.setdefault(seat.seat_id, 0),
            )
            for seat in seats
        ]
        assignment = derive_assignment(cycle_window, inputs, self.pool)
        _key, value = assignment_entry(assignment)
        self.assignments[cycle_window] = value
        for channel, delta in outstanding_delta(assignment).items():
            if channel in self.channel_outstanding:
                self.channel_outstanding[channel] += delta
        self.pool = dict(assignment.pool_after)
        self.assigned_permissions += assignment.assigned_permissions
        return assignment

    # --- the mint ---------------------------------------------------------

    def mint(self, seat_id: int, last_assigned: int | None) -> Collection:
        """Collect everything the walk reaches and advance the mark.

        The mark advances to the last assigned window whatever the walk found,
        which is version three's rule and is what makes the accumulation cap
        forfeit rather than defer. No node-channel value is lost by it: a seat
        over the cap neither accrues nor wins, so the windows the advance steps
        over hold no bit for it.
        """
        mark = self.marks.setdefault(seat_id, 0)
        if walk_range(mark, last_assigned) is None:
            raise SettlementFailure("nothing to mint")
        collection = collect(seat_id, mark, last_assigned, self.assignments)
        for channel, amount in collection.per_channel.items():
            if channel not in self.channel_outstanding:
                continue
            if self.channel_outstanding[channel] < amount:
                raise SettlementFailure("a channel issued more than it accrued")
            self.channel_outstanding[channel] -= amount
            self.channel_issued[channel] += amount
        assert last_assigned is not None
        self.marks[seat_id] = last_assigned
        return collection

    # --- the two identities ------------------------------------------------

    def claimable(self) -> dict[int, int]:
        """What the recorded assignments still owe every seat from its own mark.

        The walk is the settlement's, which is the walk a mint runs, so this
        derives the figure a sequence of mints would collect without performing
        them — and cannot drift from what the mint actually pays.
        """
        return claimable(self.marks, self.assignments)

    def identity_failures(self) -> list[str]:
        """Both identities, as equalities, over every Founder Node channel."""
        failures: list[str] = []
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
        return failures

    def require_conserved(self) -> None:
        failures = self.identity_failures()
        if failures:
            raise SettlementFailure("; ".join(sorted(set(failures))))

    # --- projections the vectors record ------------------------------------

    def assigned_total(self, channel: int) -> int:
        return self.assigned_permissions * dict(c.BASE_PERMISSION_LEGS)[channel]

    def pool_total(self) -> int:
        return sum(self.pool.values())

    def entries(self) -> dict[bytes, bytes]:
        """The economy entries this settlement commits to, for the root."""
        from .state import (
            channel_key,
            channel_value,
            cycle_assignment_key,
            recovery_pool_key,
            recovery_pool_value,
        )

        entries: dict[bytes, bytes] = {
            recovery_pool_key(): recovery_pool_value(self.pool),
        }
        for channel in c.RECOVERY_POOL_LEGS:
            entries[channel_key(channel)] = channel_value(
                self.channel_issued[channel], self.channel_outstanding[channel]
            )
        for window, value in self.assignments.items():
            entries[cycle_assignment_key(window)] = value
        return entries


def require_positive_schedule(windows: list[int]) -> None:
    """Cycle windows are assigned once each, in increasing order."""
    for index, window in enumerate(windows):
        if window < 0:
            raise InvalidSettlement("a cycle window is negative")
        if index and window <= windows[index - 1]:
            raise InvalidSettlement("cycle windows are not strictly increasing")
