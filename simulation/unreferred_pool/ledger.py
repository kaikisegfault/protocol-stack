"""The monthly ranking and the payout, driven by the window-assignment sequence.

The machine is small: windows are assigned in ascending order, each carries the
uptime its seats accumulated and the referral accrual it produced, and a window
whose month exceeds the previous one's closes every month between them.

**It binds `calendar-v1` rather than restating it.** A window's month arrives
from `simulation.calendar`, derived from the timestamp of the window's first
height. Nothing here computes a date, and nothing here reads a clock.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.calendar import months as calendar_months
from simulation.common.canonical import InvariantError, checked_add, digest
from simulation.cycle_boundary.contract import CYCLE_BLOCKS
from simulation.cycle_boundary.grid import first_cycle_window
from simulation.unreferred_pool import contract as c


def month_of_window(window: int, timestamp_of_height) -> int:
    """The month of the window's first height, through `calendar-v1`.

    `timestamp_of_height` is the chain's, supplied rather than derived: this
    model binds the calendar and owns no clock, no block rate, and no opinion
    about how long a window takes in the world.
    """
    return calendar_months.month_index(timestamp_of_height(window * CYCLE_BLOCKS))


@dataclass(frozen=True)
class Payout:
    """One month's settlement, recorded whether or not it paid."""

    month: int
    candidate_count: int
    best_figure: int
    winners: tuple[int, ...]
    payable_before: int
    share: int
    remainder: int
    paid: int

    @property
    def carried(self) -> bool:
        return not self.winners


@dataclass
class Window:
    """One assigned window: its month, its uptime, and its accrual."""

    index: int
    month: int
    uptime: dict[int, int] = field(default_factory=dict)
    accrual: int = 0


class UnreferredPool:
    """The pool's balance, the monthly figures, and the claims a payout writes."""

    def __init__(self, activation_heights: dict[int, int]) -> None:
        self.activation_heights = dict(activation_heights)
        self.accrued = 0
        self.payable = 0
        # (month, seat) -> accumulated seconds. Nonzero entries only: a
        # candidate with no entry has a figure of zero by absence, which is what
        # makes the accumulation cost the seats that ran rather than every seat.
        self.figures: dict[tuple[int, int], int] = {}
        # month -> the last window attributed to it, which is what the candidate
        # set is read against.
        self.month_last_window: dict[int, int] = {}
        self.claims: dict[tuple[int, int], int] = {}
        self.payouts: list[Payout] = []
        self.last_assigned_window: int | None = None
        self.last_assigned_month: int | None = None

    # -- derivation -------------------------------------------------------

    def first_window(self, seat: int) -> int:
        return first_cycle_window(self.activation_heights[seat])

    def in_scope(self, seat: int, window: int) -> bool:
        """`economy-transition-v8`'s rule, with no upper bound.

        In scope is permanent once a seat's first cycle arrives. That is ADR
        0049's rule 3 and it is what makes the carry unreachable.
        """
        return seat in self.activation_heights and self.first_window(seat) <= window

    def candidates(self, month: int) -> tuple[int, ...]:
        """Every seat in scope at any point in the month, in ascending order.

        Derived from the seat table rather than from the accumulated figures,
        because `in_scope` is monotone in the window: a seat is a candidate for
        a month exactly when it was in scope at that month's last window. A seat
        that ran not at all is therefore still a candidate, without anything
        having written a zero for it.
        """
        last = self.month_last_window.get(month)
        if last is None:
            return ()
        return tuple(
            seat for seat in sorted(self.activation_heights) if self.in_scope(seat, last)
        )

    def figure(self, month: int, seat: int) -> int:
        return self.figures.get((month, seat), 0)

    # -- the sequence -----------------------------------------------------

    def assign(self, window: Window) -> tuple[Payout, ...]:
        """Assign one window: pay what it closes, accumulate, then accrue.

        The order is normative and is the specification's. The payout runs
        before this window's accrual because this window belongs to the new
        month, so its accrual is the new month's and must not be paid to the
        month that is closing.
        """
        if self.last_assigned_window is not None and window.index <= self.last_assigned_window:
            raise InvariantError(
                f"window {window.index} does not follow {self.last_assigned_window}"
            )
        if self.last_assigned_month is not None and window.month < self.last_assigned_month:
            raise InvariantError(
                f"window {window.index} is in month {window.month}, behind "
                f"{self.last_assigned_month}"
            )

        settled: list[Payout] = []
        if self.last_assigned_month is not None and window.month > self.last_assigned_month:
            for month in range(self.last_assigned_month, window.month):
                settled.append(self._settle(month))

        for seat, seconds in sorted(window.uptime.items()):
            if seconds < 0 or seconds > c.WINDOW_UPTIME_SECONDS_MAX:
                raise InvariantError(
                    f"seat {seat} reports {seconds}s in one window, which is "
                    f"outside 0..{c.WINDOW_UPTIME_SECONDS_MAX}"
                )
            if not self.in_scope(seat, window.index):
                raise InvariantError(
                    f"seat {seat} is not in scope at window {window.index}"
                )
            if seconds == 0:
                continue
            key = (window.month, seat)
            total = checked_add(self.figures.get(key, 0), seconds)
            if total is None:
                raise InvariantError(f"the figure for {key} exceeds u64")
            self.figures[key] = total

        self.month_last_window[window.month] = window.index

        accrued = checked_add(self.accrued, window.accrual)
        payable = checked_add(self.payable, window.accrual)
        if accrued is None or payable is None:
            raise InvariantError("the pool's balance exceeds u64")
        self.accrued, self.payable = accrued, payable

        self.last_assigned_window = window.index
        self.last_assigned_month = window.month
        self.payouts.extend(settled)
        self.assert_conserved()
        return tuple(settled)

    def _settle(self, month: int) -> Payout:
        """Rank one completed month and pay it, or carry it and pay nothing."""
        candidates = self.candidates(month)
        payable_before = self.payable

        if not candidates:
            # The theorem: accrual in a month implies a candidate in it,
            # because in-span is a subset of in-scope. A month that accrued and
            # has nobody to pay would mean the derivation is broken, not that
            # the carry is doing its job.
            if any(m == month for m, _ in self.figures):
                raise InvariantError(
                    f"month {month} accumulated uptime and has no candidate"
                )
            return Payout(month, 0, 0, (), payable_before, 0, 0, 0)

        best = max(self.figure(month, seat) for seat in candidates)
        winners = tuple(seat for seat in candidates if self.figure(month, seat) == best)
        share = payable_before // len(winners)
        paid = share * len(winners)
        remainder = payable_before - paid

        # A zero share writes no claim. A claim is a balance and a zero balance
        # is absence, so a month that paid nothing leaves no entry behind. The
        # winners are still named in the payout record.
        if share:
            for seat in winners:
                key = (month, seat)
                total = checked_add(self.claims.get(key, 0), share)
                if total is None:  # pragma: no cover - bounded by the pool itself
                    raise InvariantError(f"the claim for {key} exceeds u64")
                self.claims[key] = total

        self.payable = remainder
        for key in [k for k in self.figures if k[0] == month]:
            del self.figures[key]

        return Payout(
            month, len(candidates), best, winners, payable_before, share, remainder, paid
        )

    # -- invariants -------------------------------------------------------

    @property
    def assigned(self) -> int:
        return sum(self.claims.values())

    def assert_conserved(self) -> None:
        """Every unit received is undistributed or owed to a named winner."""
        if self.accrued != self.payable + self.assigned:
            raise InvariantError(
                f"accrued {self.accrued} != payable {self.payable} + assigned "
                f"{self.assigned}"
            )

    # -- evidence ---------------------------------------------------------

    def canonical_state(self) -> dict[str, object]:
        return {
            "schema": c.STATE_SCHEMA,
            "accrued": str(self.accrued),
            "payable": str(self.payable),
            "assigned": str(self.assigned),
            "claims": [
                {"month": month, "seat_id": seat, "amount": str(self.claims[(month, seat)])}
                for month, seat in sorted(self.claims)
            ],
            "open_figures": [
                {"month": month, "seat_id": seat, "seconds": str(self.figures[(month, seat)])}
                for month, seat in sorted(self.figures)
            ],
        }

    def state_digest(self) -> str:
        return digest(c.STATE_LABEL, self.canonical_state())
