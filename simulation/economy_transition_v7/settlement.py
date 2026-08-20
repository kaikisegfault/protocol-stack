"""The version-seven settlement: the recovery pool replaces the carry.

Steps 1 through 4 of a cycle's assignment are version three's and are imported.
Steps 5 through 7 are this module's, and they are what ADR 0049 directs:

5. every contributing seat adds a whole base permission to `outstanding`, with
   nothing moved out;
6. a cycle with any winner absorbs 100% of the recovery pool **as it stood
   before this cycle**;
7. each leg is divided among the winners, and both remainders — the
   reallocation dust and the residual of the pool just divided — become the
   pool for the cycle after.

**Step 6 reads before step 7 writes**, so a cycle never pays itself its own
dust. That order is the difference between two self-consistent readings of ADR
0049's sentence, so it is derived once here and stated once in the
specification rather than left to each implementation.

The two seat sets are version three's and are not narrowed here. The
*contributing* set is the in-span seats, which generate permissions. The
*eligible* set is every in-scope seat that met the cycle and is under the
accumulation cap, in span or not, and it is the candidate set the winner
derivation ranks. A winner derivation filtered by span would strand the pool the
moment the last in-span machine finished, so the separation is guarded by a
vector rather than left to reading.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.economy_transition_v3.settlement import (
    Collection,
    InvalidSettlement,
    SeatCycle,
    accrues_in_window,
    last_assigned_window,
    referral_accrual,
    walk_length,
    walk_range,
)
from simulation.economy_transition_v3.winners import (
    derive_winner_set,
    met_cycle,
    require_canonical,
    split_permission,
)

from . import contract as c
from .state import (
    bit_is_set,
    bitmap,
    cycle_assignment_key,
    cycle_assignment_value,
    decode_cycle_assignment_value,
)

__all__ = [
    "Assignment",
    "Collection",
    "InvalidSettlement",
    "SeatCycle",
    "accrues_in_window",
    "assignment_entry",
    "claimable",
    "collect",
    "derive_assignment",
    "derive_winner_set",
    "empty_pool",
    "last_assigned_window",
    "met_cycle",
    "outstanding_delta",
    "referral_accrual",
    "require_canonical",
    "split_permission",
    "walk_length",
    "walk_range",
]


def empty_pool() -> dict[int, int]:
    """The recovery pool genesis writes: five legs, all zero."""
    return {channel: 0 for channel in c.RECOVERY_POOL_LEGS}


def require_pool(pool: dict[int, int]) -> dict[int, int]:
    if set(pool) != set(c.RECOVERY_POOL_LEGS):
        raise InvalidSettlement("the recovery pool carries exactly the five node legs")
    for amount in pool.values():
        if amount < 0 or amount > c.MAX_U64:
            raise InvalidSettlement("a recovery pool leg left u64")
    return dict(pool)


@dataclass(frozen=True)
class Assignment:
    """The derived outcome of one cycle, before it is encoded.

    Every pool quantity is carried separately because each answers a different
    question. `pool_before` is what the cycle found, `pool_absorbed` is what it
    took and is the only one the record commits to, `pool_share_per_channel` is
    what one winner receives from it, `pool_residual_per_channel` is what
    dividing it left behind, and `pool_after` is what the next cycle finds.
    """

    cycle_window: int
    accrued: tuple[int, ...]
    winners: tuple[int, ...]
    reallocated_count: int
    in_scope_count: int
    bitmap_bits: int
    share_per_channel: dict[int, int]
    remainder_per_channel: dict[int, int]
    dust_per_channel: dict[int, int]
    pool_before: dict[int, int]
    pool_absorbed: dict[int, int]
    pool_share_per_channel: dict[int, int]
    pool_residual_per_channel: dict[int, int]
    pool_after: dict[int, int]
    assigned_permissions: int

    @property
    def winner_count(self) -> int:
        return len(self.winners)

    @property
    def absorbed_total(self) -> int:
        return sum(self.pool_absorbed.values())


def derive_assignment(
    cycle_window: int, seats: list[SeatCycle], pool: dict[int, int]
) -> Assignment:
    """Steps 1 through 7 of the assignment, in the specified order."""
    seat_ids = [seat.seat_id for seat in seats]
    if len(set(seat_ids)) != len(seat_ids):
        raise InvalidSettlement("a seat appears twice in one cycle's in-scope set")
    before = require_pool(pool)

    uptime = {seat.seat_id: seat.uptime_seconds for seat in seats}
    met = {seat.seat_id: met_cycle(seat.uptime_seconds) for seat in seats}
    under_cap = {
        seat.seat_id: accrues_in_window(cycle_window, seat.minted_through_window)
        for seat in seats
    }

    # Step 3. Every in-scope seat is a candidate, in span or not: this is the
    # eligible set, and narrowing it to the contributing set is the regression
    # ADR 0054 decision 5 exists to prevent.
    winners = derive_winner_set(uptime, met, under_cap)
    winner_count = len(winners)

    # Step 4. The contributing set is the in-span seats, and only they accrue.
    accrued = tuple(
        sorted(
            seat.seat_id
            for seat in seats
            if seat.in_span and met[seat.seat_id] and under_cap[seat.seat_id]
        )
    )
    assigned = sum(1 for seat in seats if seat.in_span)
    reallocated = assigned - len(accrued)

    # Step 6. Absorb before dividing, so this cycle's own dust belongs to the
    # next one. A cycle with no winner absorbs nothing and leaves the pool.
    absorbed = (
        dict(before) if winner_count else {channel: 0 for channel in before}
    )

    # Step 7. Divide both, and return both remainders to the pool.
    shares, remainders = split_permission(winner_count)
    dust = {channel: remainder * reallocated for channel, remainder in remainders.items()}
    pool_shares: dict[int, int] = {}
    pool_residual: dict[int, int] = {}
    after: dict[int, int] = {}
    for channel in c.RECOVERY_POOL_LEGS:
        taken = absorbed[channel]
        share = taken // winner_count if winner_count else 0
        pool_shares[channel] = share
        pool_residual[channel] = taken - share * winner_count
        after[channel] = before[channel] - taken + pool_residual[channel] + dust[channel]

    return Assignment(
        cycle_window=cycle_window,
        accrued=accrued,
        winners=winners,
        reallocated_count=reallocated,
        in_scope_count=len(seats),
        bitmap_bits=(max(seat_ids) + 1) if seat_ids else 0,
        share_per_channel=shares,
        remainder_per_channel=remainders,
        dust_per_channel=dust,
        pool_before=before,
        pool_absorbed=absorbed,
        pool_share_per_channel=pool_shares,
        pool_residual_per_channel=pool_residual,
        pool_after=after,
        assigned_permissions=assigned,
    )


def assignment_entry(assignment: Assignment) -> tuple[bytes, bytes]:
    """The one record the chain writes when a cycle is finalised."""
    return (
        cycle_assignment_key(assignment.cycle_window),
        cycle_assignment_value(
            assignment.share_per_channel[c.FOUNDER_OPERATOR_CHANNEL],
            assignment.reallocated_count,
            assignment.winner_count,
            assignment.in_scope_count,
            assignment.bitmap_bits,
            assignment.pool_absorbed,
            bitmap(assignment.accrued, assignment.bitmap_bits),
            bitmap(assignment.winners, assignment.bitmap_bits),
        ),
    )


def outstanding_delta(assignment: Assignment) -> dict[int, int]:
    """What one cycle adds to each channel's outstanding amount.

    Version six subtracted the carried remainder here, because the carry sat
    beside `outstanding` in the identity. Version seven leaves the whole
    permission in `outstanding` and names the unclaimable part with the recovery
    pool entry instead, which is what removes the identity's third term.
    """
    return {
        channel: assignment.assigned_permissions * amount
        for channel, amount in c.BASE_PERMISSION_LEGS
    }


def collect(
    seat_id: int,
    mark: int,
    last_assigned: int | None,
    records: dict[int, bytes],
) -> Collection:
    """The mint walk. `records` maps a cycle window to its encoded value.

    Version three's walk with one term added: a winner also takes that cycle's
    pool share. A window with no record contributes nothing, so an absent record
    and a record with both bits clear are the same fact.
    """
    per_channel = {channel: 0 for channel, _ in c.BASE_PERMISSION_LEGS}
    span = walk_range(mark, last_assigned)
    if span is None:
        return Collection(per_channel, 0, (), ())

    accrued_windows: list[int] = []
    won_windows: list[int] = []
    first, last = span
    for window in range(first, last + 1):
        raw = records.get(window)
        if raw is None:
            continue
        record = decode_cycle_assignment_value(raw)
        if bit_is_set(record["accrued_bitmap"], seat_id):
            accrued_windows.append(window)
            for channel, amount in c.BASE_PERMISSION_LEGS:
                per_channel[channel] += amount
        if bit_is_set(record["winner_bitmap"], seat_id):
            won_windows.append(window)
            winner_count = record["winner_count"]
            shares, _ = split_permission(winner_count)
            for channel, _amount in c.BASE_PERMISSION_LEGS:
                per_channel[channel] += record["reallocated_count"] * shares[channel]
                per_channel[channel] += record["pool_absorbed"][channel] // winner_count
    return Collection(
        per_channel, last - first + 1, tuple(accrued_windows), tuple(won_windows)
    )


def claimable(
    marks: dict[int, int], records: dict[int, bytes]
) -> dict[int, int]:
    """What the recorded assignments still owe every seat from its own mark.

    **It is defined as what a sequence of mints would collect**, by running the
    same `collect` walk a mint runs, once per seat, against the same records. A
    second walk written beside the first would be a second implementation of the
    contract's most load-bearing derivation with nothing keeping the two equal —
    and the backing identity, which is the whole point of version seven, would
    then be checking the model against itself rather than against the mint.

    `marks` maps a seat ID to its `minted_through_window`. The last assigned
    window is the largest window with a record, which is what a mint at any
    height past that window's boundary would walk to.
    """
    owed = {channel: 0 for channel in c.RECOVERY_POOL_LEGS}
    last_assigned = max(records) if records else None
    for seat_id, mark in marks.items():
        collection = collect(seat_id, mark, last_assigned, records)
        for channel, amount in collection.per_channel.items():
            owed[channel] += amount
    return owed
