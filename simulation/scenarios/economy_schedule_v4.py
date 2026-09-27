"""The fourth suite's fixture: who buys, who refers, how machines run, who collects.

**Every figure here is research, not a founder value.** The population, the
stagger, the uptime pattern, and the collection schedule are chosen to reach
the paths the current contract has. Each choice is a field of `Fixture`, so
`tools/scenario-suite-vectors/expected_v4.py` can restate it independently, and
so the property tests can draw other populations from the same shape. The
founder-directed figures, such as the legs, the threshold, the cap, and the
731 cycles, are read from the contract and never from here.

**The recorded fixture runs at the commit target: three seconds a block, so a
window is exactly one day.** Genesis is midnight on 2027-01-01, so window `w`
opens at the start of day `w`, and a calendar month holds 28 to 31 windows. The
run crosses February 2028, so the leap day is on the path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property

from simulation.calendar.civil import days_from_civil
from simulation.economy_transition_v9 import contract as c
from simulation.economy_transition_v9.timeline import month_of

CYCLE_BLOCKS = c.CYCLE_BLOCKS

# Credited and disputed slots by residue: each row covers residues up to its
# bound. A third of windows sit exactly on the eighteen-hour threshold, one in
# 29 is an hour below it, and one is a perfect record under a maximal dispute.
PATTERN = (
    (0, 12, 0),
    (1, 17, 0),
    (9, 18, 0),
    (17, 22, 1),
    (24, 23, 0),
    (27, 24, 0),
    (28, 24, 6),
)


@dataclass(frozen=True)
class Fixture:
    """One research population and everything it does, as data."""

    genesis_millis: int = days_from_civil(2027, 1, 1) * 86_400_000
    millis_per_block: int = 3_000
    people: int = 6
    # seat -> (owner, referrer or None). Person 0 owns two seats and refers a
    # third; person 1 is referred and refers onward; person 5 only refers.
    seats: dict[int, tuple[int, int | None]] = field(default_factory=lambda: {
        0: (0, None), 1: (1, 0), 2: (2, 5), 3: (0, None), 4: (3, 5), 5: (4, 1),
    })
    # Seat k activates in window k * stagger, so the lives overlap in phases and
    # every referrer's first accrual lands after window 30 (ADR 0094).
    stagger: int = 61
    activation_offset: int = 100
    # The one machine at full uptime once every seat's issuance has ended, so the
    # first window after the last cycle has one winner and the recovery pool
    # drains to zero rather than to a residual.
    keeper: int = 0
    tail_hours: int = 20
    pattern: tuple[tuple[int, int, int], ...] = PATTERN
    window_factor: int = 7
    seat_factor: int = 11
    # A network-wide outage: nobody is credited, nobody meets the cycle, and the
    # whole contribution enters the recovery pool.
    outage_period: int = 101
    outage_phase: int = 57
    # Collection every twenty windows keeps everyone under the thirty-window cap
    # except inside the two lapses, which exceed it on purpose. The hoarder
    # never collects its monthly pool claims until the last round.
    mint_period: int = 20
    node_mint_phase: int = 3
    referral_mint_phase: int = 10
    seat_lapse: tuple[int, int, int] = (2, 400, 460)
    referrer_lapse: tuple[int, int, int] = (5, 500, 560)
    pool_hoarder: int = 3
    # A run that stops early, for the property tests. `None` runs until the
    # drain window's month has settled.
    horizon: int | None = None

    # --- the calendar ------------------------------------------------------

    def stamp(self, height: int) -> int:
        return self.genesis_millis + height * self.millis_per_block

    def window_month(self, window: int) -> int:
        """`calendar-v1`'s month of a window's opening height."""
        return month_of(self.stamp(window * CYCLE_BLOCKS))

    # --- the seats ---------------------------------------------------------

    @cached_property
    def referrers(self) -> tuple[int, ...]:
        return tuple(sorted({r for _o, r in self.seats.values() if r is not None}))

    def activation_window(self, seat_id: int) -> int:
        return seat_id * self.stagger

    def activation_height(self, seat_id: int) -> int:
        start = self.activation_window(seat_id) * CYCLE_BLOCKS
        return start + self.activation_offset + seat_id

    def first_cycle_window(self, seat_id: int) -> int:
        return self.activation_window(seat_id) + 1

    def last_cycle_window(self, seat_id: int) -> int:
        return self.first_cycle_window(seat_id) + c.ISSUANCE_CYCLES_PER_SEAT - 1

    @cached_property
    def last_span_window(self) -> int:
        return max(self.last_cycle_window(seat) for seat in self.seats)

    @cached_property
    def drain_window(self) -> int:
        return self.last_span_window + 1

    @cached_property
    def end_window(self) -> int:
        """The first window whose opening settles the drain window's month."""
        if self.horizon is not None:
            return self.horizon
        window = self.drain_window
        while self.window_month(window) == self.window_month(self.drain_window):
            window += 1
        return window + c.ASSIGNMENT_LAG_WINDOWS

    # --- the machines ------------------------------------------------------

    def slots(self, seat_id: int, window: int) -> tuple[int, int]:
        """`(credited, disputed)` slot counts for one seat in one window."""
        if window > self.last_span_window:
            return (24, 0) if seat_id == self.keeper else (self.tail_hours, 0)
        if window % self.outage_period == self.outage_phase:
            return (0, 0)
        residue = (self.window_factor * window + self.seat_factor * seat_id) % (
            self.pattern[-1][0] + 1
        )
        return next((k, d) for bound, k, d in self.pattern if residue <= bound)

    @staticmethod
    def bitmaps(credited: int, disputed: int) -> tuple[int, int]:
        """Credited slots are the low bits, and disputed ones the lowest of those."""
        return (1 << credited) - 1, (1 << disputed) - 1

    # --- the collections ---------------------------------------------------

    def node_mints(self, seat_id: int, window: int) -> bool:
        """Whether a seat's owner collects kind 4 in a window before the last."""
        lapsed, first, last = self.seat_lapse
        offset = window - self.activation_window(seat_id)
        if seat_id == lapsed and first <= window < last:
            return False
        return offset > 0 and offset % self.mint_period == self.node_mint_phase

    def referral_mints(self, person: int, window: int) -> bool:
        """Whether a referrer collects kind 5, once a balance can exist."""
        lapsed, first, last = self.referrer_lapse
        if person == lapsed and first <= window < last:
            return False
        earliest = min(
            self.first_cycle_window(seat)
            for seat, (_owner, referrer) in self.seats.items()
            if referrer == person
        )
        return window >= earliest + c.ASSIGNMENT_LAG_WINDOWS and (
            window % self.mint_period == self.referral_mint_phase
        )

    def pool_mints(self, seat_id: int, window: int) -> bool:
        """Every seat but the hoarder asks for its pool claim when it collects."""
        return seat_id != self.pool_hoarder and self.node_mints(seat_id, window)


RECORDED = Fixture()
