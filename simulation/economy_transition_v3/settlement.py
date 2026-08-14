"""The accumulation cap, the per-cycle assignment, and the bounded mint walk.

Version three's settlement is version two's with one predicate added and one
consequence taken seriously. The predicate is the accumulation cap ADR 0033
directs; the consequence is that a mint's walk becomes a constant, which is the
cost that ADR says the cap exists to close.

The cap is measured in windows since the last collection rather than in accrued
cycles, and that is what makes the bound exact. A seat's mark changes only at a
mint, and a mint sets it to the last assigned window, so every window in
`(mark, last]` was assigned while the mark held its current value — and the
assignment applied the same bound against that same mark. No window outside
`(mark, mark + cap]` can therefore carry a bit for the seat.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import contract as c
from .state import (
    bit_is_set,
    bitmap,
    cycle_assignment_key,
    cycle_assignment_value,
    decode_cycle_assignment_value,
)
from .winners import derive_winner_set, met_cycle, split_permission


class InvalidSettlement(ValueError):
    """A settlement input no conforming chain could present."""


def accrues_in_window(cycle_window: int, mark: int) -> bool:
    """The accrual predicate, for a seat's mark or a referrer's."""
    if cycle_window < 0 or mark < 0:
        raise InvalidSettlement("windows and marks are non-negative")
    return cycle_window <= mark + c.MINT_ACCUMULATION_CAP


def last_assigned_window(height: int) -> int | None:
    """`window_of_height(h) - 2`, or nothing while the chain is younger than that.

    `uptime-measurement-v1` finalises window `w` at the first height of `w + 2`,
    so that is where `w`'s assignment executes and no earlier.
    """
    window = height // c.CYCLE_BLOCKS
    if window < c.ASSIGNMENT_LAG_WINDOWS:
        return None
    return window - c.ASSIGNMENT_LAG_WINDOWS


def walk_range(mark: int, last_assigned: int | None) -> tuple[int, int] | None:
    """The half-open window range a mint reads, or nothing when it is empty.

    Returned as `(first, last)` inclusive on both ends, so an empty walk is
    distinguishable from a one-window walk.
    """
    if mark < 0:
        raise InvalidSettlement("a mark is a window and windows are non-negative")
    if last_assigned is None or mark >= last_assigned:
        return None
    return mark + 1, min(last_assigned, mark + c.MINT_ACCUMULATION_CAP)


def walk_length(mark: int, last_assigned: int | None) -> int:
    span = walk_range(mark, last_assigned)
    return 0 if span is None else span[1] - span[0] + 1


@dataclass(frozen=True)
class SeatCycle:
    """One in-scope seat's inputs for one cycle, as the chain already holds them."""

    seat_id: int
    uptime_seconds: int
    in_span: bool
    minted_through_window: int
    referrer_account_id: bytes | None = None


@dataclass(frozen=True)
class Assignment:
    """The derived outcome of one cycle, before it is encoded."""

    cycle_window: int
    accrued: tuple[int, ...]
    winners: tuple[int, ...]
    reallocated_count: int
    in_scope_count: int
    bitmap_bits: int
    share_per_channel: dict[int, int]
    carry_per_channel: dict[int, int]
    assigned_permissions: int

    @property
    def winner_count(self) -> int:
        return len(self.winners)


def derive_assignment(cycle_window: int, seats: list[SeatCycle]) -> Assignment:
    """Steps 1 through 6 of the assignment, in the specified order."""
    seat_ids = [seat.seat_id for seat in seats]
    if len(set(seat_ids)) != len(seat_ids):
        raise InvalidSettlement("a seat appears twice in one cycle's in-scope set")

    uptime = {seat.seat_id: seat.uptime_seconds for seat in seats}
    met = {seat.seat_id: met_cycle(seat.uptime_seconds) for seat in seats}
    under_cap = {
        seat.seat_id: accrues_in_window(cycle_window, seat.minted_through_window)
        for seat in seats
    }

    winners = derive_winner_set(uptime, met, under_cap)
    accrued = tuple(
        sorted(
            seat.seat_id
            for seat in seats
            if seat.in_span and met[seat.seat_id] and under_cap[seat.seat_id]
        )
    )
    assigned = sum(1 for seat in seats if seat.in_span)
    reallocated = assigned - len(accrued)

    shares, remainders = split_permission(len(winners))
    carries = {
        channel: remainder * reallocated for channel, remainder in remainders.items()
    }
    return Assignment(
        cycle_window=cycle_window,
        accrued=accrued,
        winners=winners,
        reallocated_count=reallocated,
        in_scope_count=len(seats),
        bitmap_bits=(max(seat_ids) + 1) if seat_ids else 0,
        share_per_channel=shares,
        carry_per_channel=carries,
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
            bitmap(assignment.accrued, assignment.bitmap_bits),
            bitmap(assignment.winners, assignment.bitmap_bits),
        ),
    )


def outstanding_delta(assignment: Assignment) -> dict[int, int]:
    """What one cycle adds to each channel's outstanding amount.

    The carried remainder is moved *out of* outstanding rather than added
    beside it. Adding it beside would count the same value twice, and the carry
    identity version two states as an equality would not hold.
    """
    return {
        channel: assignment.assigned_permissions * amount
        - assignment.carry_per_channel[channel]
        for channel, amount in c.BASE_PERMISSION_LEGS
    }


@dataclass(frozen=True)
class Collection:
    """What one mint takes, before it is written."""

    per_channel: dict[int, int]
    windows_walked: int
    accrued_windows: tuple[int, ...]
    won_windows: tuple[int, ...]

    @property
    def total_atomic(self) -> int:
        return sum(self.per_channel.values())

    @property
    def operator_atomic(self) -> int:
        """The leg that credits the signing manager's own account balance."""
        return self.per_channel[c.FOUNDER_OPERATOR_CHANNEL]

    @property
    def custody_atomic(self) -> dict[int, int]:
        """The four institutional legs, keyed by typed-custody beneficiary kind."""
        return {
            c.LEG_BENEFICIARY_KIND[channel]: amount
            for channel, amount in self.per_channel.items()
            if c.LEG_BENEFICIARY_KIND[channel] is not None
        }


def collect(
    seat_id: int,
    mark: int,
    last_assigned: int | None,
    records: dict[int, bytes],
) -> Collection:
    """The mint walk. `records` maps a cycle window to its encoded value.

    A window with no record contributes nothing, so an absent record and a
    record with both bits clear are the same fact.
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
            shares, _ = split_permission(record["winner_count"])
            for channel, _ in c.BASE_PERMISSION_LEGS:
                per_channel[channel] += record["reallocated_count"] * shares[channel]
    return Collection(
        per_channel, last - first + 1, tuple(accrued_windows), tuple(won_windows)
    )


def referral_accrual(
    cycle_window: int,
    seats: list[SeatCycle],
    referrer_marks: dict[bytes, int],
) -> tuple[dict[bytes, int], int]:
    """Step 7. Returns per-referrer accruals and the unreferred pool's share.

    A referrer with no recorded mark has never accrued, so its entry is created
    at this accrual with the window before this one and the accrual always
    succeeds. A referrer over the cap forfeits, and the forfeited value stays
    inside the `founder_referral` channel and routes to the unreferred pool,
    which the constitution already defines as that channel's second destination.
    """
    accruals: dict[bytes, int] = {}
    pool = 0
    for seat in seats:
        if not seat.in_span:
            continue
        referrer = seat.referrer_account_id
        if referrer is None:
            pool += c.REFERRAL_LEG_ATOMIC
            continue
        mark = referrer_marks.get(referrer)
        if mark is not None and not accrues_in_window(cycle_window, mark):
            pool += c.REFERRAL_LEG_ATOMIC
            continue
        accruals[referrer] = accruals.get(referrer, 0) + c.REFERRAL_LEG_ATOMIC
    return accruals, pool
