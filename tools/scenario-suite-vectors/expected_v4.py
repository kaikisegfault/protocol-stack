"""Closed-form expectations for suite version four.

This module is the independence in the version-four verifier. **It imports
nothing from `simulation/`.** The economy literals come from `expected_v2.py`,
the window grid from `tools/cycle-boundary-vectors/expected.py`, and the civil
calendar from `tools/calendar-vectors/expected.py`. Each of those converts an
accepted document by hand and reads no model.

What it adds is a walk of the current contract's settlement, written from the
specifications rather than from the code that executes them:

- the winner set, the accrued set, and the recovery pool's absorption and
  residual (`economy-transition-v7`, ADR 0054);
- the accumulation cap on seats and referrers, with a new referral balance
  marked at the window before its first accrual (`economy-transition-v3`,
  ADR 0094);
- the monthly pool: figures by calendar month, candidates by scope, ties
  split, remainders carried (`unreferred-pool-payout-v1`, ADR 0075);
- the mints, which collect what those rules assigned.

The fixture is restated from `economy-scenario-suite-v4.md` rather than
imported from the generator, so a generator that drifted from its own
specification fails here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from expected_v2 import (
    ATOMIC_UNITS_PER_DISPLAY_UNIT,
    COMMUNITY_GRANTS_LEG,
    DEVELOPER_INCENTIVES_LEG,
    FOUNDER_OPERATOR_LEG,
    ISSUANCE_CYCLES_PER_SEAT,
    MAXIMUM_SUPPLY_ATOMIC,
    REFERRAL_LEG,
    SYSTEM_CREATOR_LEG,
    VENTURE_ESCROW_LEG,
)
from expected_v3 import _load, grid

calendar = _load("expected_calendar", "calendar-vectors/expected.py")

VERSION = "v4"

# Channels 0 to 4 are the five Founder Node legs, 7 the referral channel, and 8
# the verified-user channel the entry airdrop draws on.
LEGS = (
    FOUNDER_OPERATOR_LEG,
    VENTURE_ESCROW_LEG,
    COMMUNITY_GRANTS_LEG,
    DEVELOPER_INCENTIVES_LEG,
    SYSTEM_CREATOR_LEG,
)
REFERRAL_CHANNEL = 7
AIRDROP_CHANNEL = 8
# ADR 0042: every registration is credited one day's verified-user rate.
ENTRY_AIRDROP = 171 * ATOMIC_UNITS_PER_DISPLAY_UNIT // 100
# ADR 0034 and `uptime-measurement-v1`.
MINT_ACCUMULATION_CAP = 30
ASSIGNMENT_LAG_WINDOWS = 2
SLOTS_PER_WINDOW = 24
SLOT_SECONDS = grid.SECONDS_PER_HOUR
THRESHOLD_SECONDS = grid.ACTIVITY_THRESHOLD_SECONDS
CYCLE_BLOCKS = grid.CYCLE_BLOCKS

# --- the fixture, restated from the specification ----------------------------

FIXED_FEE = 1_000
PATTERN = ((0, 12, 0), (1, 17, 0), (9, 18, 0), (17, 22, 1), (24, 23, 0),
           (27, 24, 0), (28, 24, 6))


@dataclass(frozen=True)
class Params:
    """`economy-scenario-suite-v4`'s fixture table, one field per row."""

    genesis_millis: int = calendar.days_from_civil(2027, 1, 1) * calendar.MILLIS_PER_DAY
    millis_per_block: int = grid.TARGET_COMMIT_SECONDS * 1_000
    people: int = 6
    seats: dict = field(default_factory=lambda: {
        0: (0, None), 1: (1, 0), 2: (2, 5), 3: (0, None), 4: (3, 5), 5: (4, 1),
    })
    stagger: int = 61
    keeper: int = 0
    tail_hours: int = 20
    pattern: tuple = PATTERN
    window_factor: int = 7
    seat_factor: int = 11
    outage_period: int = 101
    outage_phase: int = 57
    mint_period: int = 20
    node_mint_phase: int = 3
    referral_mint_phase: int = 10
    seat_lapse: tuple = (2, 400, 460)
    referrer_lapse: tuple = (5, 500, 560)
    pool_hoarder: int = 3
    horizon: int | None = None

    @property
    def referrers(self) -> tuple[int, ...]:
        return tuple(sorted({r for _o, r in self.seats.values() if r is not None}))

    def first_window(self, seat: int) -> int:
        return seat * self.stagger + 1

    def last_window(self, seat: int) -> int:
        return self.first_window(seat) + ISSUANCE_CYCLES_PER_SEAT - 1

    @property
    def last_span_window(self) -> int:
        return max(self.last_window(seat) for seat in self.seats)

    @property
    def drain_window(self) -> int:
        return self.last_span_window + 1

    def month(self, window: int) -> int:
        opening = window * CYCLE_BLOCKS * self.millis_per_block
        return calendar.month_index(self.genesis_millis + opening)

    @property
    def end_window(self) -> int:
        if self.horizon is not None:
            return self.horizon
        window = self.drain_window
        while self.month(window) == self.month(self.drain_window):
            window += 1
        return window + ASSIGNMENT_LAG_WINDOWS

    def credited_hours(self, seat: int, window: int) -> int:
        """Credited slots less disputed ones, from the specification's table."""
        if window > self.last_span_window:
            return 24 if seat == self.keeper else self.tail_hours
        if window % self.outage_period == self.outage_phase:
            return 0
        modulus = self.pattern[-1][0] + 1
        residue = (self.window_factor * window + self.seat_factor * seat) % modulus
        return next(k - d for bound, k, d in self.pattern if residue <= bound)

    def node_mints(self, seat: int, window: int) -> bool:
        lapsed, first, last = self.seat_lapse
        offset = window - seat * self.stagger
        if seat == lapsed and first <= window < last:
            return False
        return offset > 0 and offset % self.mint_period == self.node_mint_phase

    def referral_mints(self, person: int, window: int) -> bool:
        lapsed, first, last = self.referrer_lapse
        if person == lapsed and first <= window < last:
            return False
        earliest = min(
            self.first_window(s) for s, (_o, r) in self.seats.items() if r == person
        )
        return window >= earliest + ASSIGNMENT_LAG_WINDOWS and (
            window % self.mint_period == self.referral_mint_phase
        )


RECORDED = Params()


# --- the walk ----------------------------------------------------------------


@dataclass
class Walk:
    """The contract's quantities, advanced one window opening at a time."""

    p: Params = RECORDED
    pool: list[int] = field(default_factory=lambda: [0] * len(LEGS))
    marks: dict[int, int] = field(default_factory=dict)
    owed: dict[int, dict[int, list[int]]] = field(default_factory=dict)
    referral_marks: dict[int, int] = field(default_factory=dict)
    referral_accrued: dict[int, int] = field(default_factory=dict)
    referral_minted: dict[int, int] = field(default_factory=dict)
    unreferred_accrued: int = 0
    payable: int = 0
    cursor: int = 0
    figures: dict[int, int] = field(default_factory=dict)
    claims: dict[int, list[int]] = field(default_factory=dict)
    months: list[tuple[int, tuple[int, ...], int, int, int]] = field(default_factory=list)
    issued: dict[int, int] = field(default_factory=dict)
    balances: dict[int, int] = field(default_factory=dict)
    fees: int = 0
    counts: dict[str, int] = field(default_factory=dict)
    assigned: int = 0
    peak_pool: int = 0

    def count(self, name: str, by: int = 1) -> None:
        self.counts[name] = self.counts.get(name, 0) + by

    def issue(self, channel: int, amount: int) -> None:
        self.issued[channel] = self.issued.get(channel, 0) + amount

    def charge(self, person: int) -> None:
        self.balances[person] -= FIXED_FEE
        self.fees += FIXED_FEE

    # A window's assignment, at the opening of `due + 2`.

    def assign(self, due: int) -> None:
        # The month closes whether or not any seat is in scope yet.
        self._settle_month(due)
        scope = [seat for seat in sorted(self.marks) if self.p.first_window(seat) <= due]
        if not scope:
            return
        span = [seat for seat in scope if due <= self.p.last_window(seat)]
        uptime = {seat: self.p.credited_hours(seat, due) * SLOT_SECONDS for seat in scope}
        eligible = [
            seat for seat in scope
            if uptime[seat] >= THRESHOLD_SECONDS
            and due <= self.marks[seat] + MINT_ACCUMULATION_CAP
        ]
        best = max((uptime[seat] for seat in eligible), default=None)
        winners = [seat for seat in eligible if uptime[seat] == best]
        accrued = [seat for seat in span if seat in eligible]
        reallocated = len(span) - len(accrued)
        self._pay(due, winners, accrued, reallocated)
        self._refer(due, span)
        for seat in scope:
            if uptime[seat]:
                self.figures[seat] = self.figures.get(seat, 0) + uptime[seat]
        self.assigned += len(span)
        self.count("empty_winner_windows", not winners)
        self.count("multi_winner_windows", len(winners) > 1)
        self.count("reallocated_permissions", reallocated)
        # Cycles the cap alone cost: the seat ran, met the cycle, and was over.
        self.count("over_cap_seat_windows", sum(
            1 for seat in span
            if uptime[seat] >= THRESHOLD_SECONDS
            and due > self.marks[seat] + MINT_ACCUMULATION_CAP
        ))
        self.peak_pool = max(self.peak_pool, sum(self.pool))

    def _pay(self, due: int, winners: list[int], accrued: list[int], moved: int) -> None:
        count = len(winners)
        taken = list(self.pool) if count else [0] * len(LEGS)
        for channel, leg in enumerate(LEGS):
            share = leg // count if count else 0
            dust = (leg - share * count) * moved
            pooled = taken[channel] // count if count else 0
            # The pool keeps what dividing it left and gains this window's dust.
            self.pool[channel] += dust - pooled * count
            for seat in accrued:
                self.owed[seat].setdefault(due, [0] * len(LEGS))[channel] += leg
            for seat in winners:
                entry = self.owed[seat].setdefault(due, [0] * len(LEGS))
                entry[channel] += moved * share + pooled

    def _refer(self, due: int, span: list[int]) -> None:
        for seat in span:
            referrer = self.p.seats[seat][1]
            if referrer is None:
                self.unreferred_accrued += REFERRAL_LEG
                self.payable += REFERRAL_LEG
                continue
            mark = self.referral_marks.setdefault(referrer, due - 1)
            if due > mark + MINT_ACCUMULATION_CAP:
                self.unreferred_accrued += REFERRAL_LEG
                self.payable += REFERRAL_LEG
                self.count("forfeited_referral_legs")
                continue
            self.referral_accrued[referrer] = (
                self.referral_accrued.get(referrer, 0) + REFERRAL_LEG
            )

    def _settle_month(self, due: int) -> None:
        """Close the cursor's month when the assigned window is in a later one.

        The payout precedes this window's referral accrual, which belongs to
        the new month.
        """
        if self.p.month(due) == self.cursor:
            return
        candidates = [
            seat for seat in sorted(self.marks) if self.p.first_window(seat) <= due - 1
        ]
        best = max((self.figures.get(seat, 0) for seat in candidates), default=0)
        winners = tuple(
            seat for seat in candidates if self.figures.get(seat, 0) == best
        )
        share = self.payable // len(winners) if winners else 0
        for seat in winners if share else ():
            self.claims.setdefault(seat, [0, 0])[0] += share
        before = self.payable
        self.payable -= share * len(winners)
        self.months.append((self.cursor, winners, before, share, self.payable))
        self.cursor = self.p.month(due)
        self.figures = {}

    # The four transactions a participant sends.

    def activate(self, seat: int, window: int) -> None:
        self.marks[seat] = window
        self.owed[seat] = {}
        self.charge(self.p.seats[seat][0])
        self.count("activate.SUCCESS")

    def mint_node(self, seat: int, window: int) -> None:
        """Kind 4: everything the bounded walk reaches, then the mark moves."""
        last = window - ASSIGNMENT_LAG_WINDOWS
        mark = self.marks[seat]
        if mark >= last:
            self.count("mint_node.NOTHING_TO_MINT")
            return
        owner = self.p.seats[seat][0]
        reach = min(last, mark + MINT_ACCUMULATION_CAP)
        for due in [w for w in sorted(self.owed[seat]) if mark < w <= reach]:
            for channel, amount in enumerate(self.owed[seat].pop(due)):
                self.issue(channel, amount)
                if channel == 0:
                    self.balances[owner] += amount
        if any(w <= last for w in self.owed[seat]):
            raise AssertionError(f"seat {seat} left value behind its mark")
        self.marks[seat] = last
        self.charge(owner)
        self.count("mint_node.SUCCESS")

    def mint_pool(self, seat: int) -> None:
        """Kind 22: the whole unminted claim, or nothing to mint."""
        claim = self.claims.get(seat)
        if claim is None or claim[0] == claim[1]:
            self.count("mint_pool.NOTHING_TO_MINT")
            return
        owner = self.p.seats[seat][0]
        self.balances[owner] += claim[0] - claim[1]
        self.issue(REFERRAL_CHANNEL, claim[0] - claim[1])
        claim[1] = claim[0]
        self.charge(owner)
        self.count("mint_pool.SUCCESS")

    def mint_referral(self, person: int, window: int) -> None:
        """Kind 5: the whole balance, and the mark to the last assigned window."""
        last = window - ASSIGNMENT_LAG_WINDOWS
        accrued = self.referral_accrued.get(person, 0)
        minted = self.referral_minted.get(person, 0)
        mark = self.referral_marks.get(person)
        if mark is None or (accrued == minted and mark >= last):
            self.count("mint_referral.NOTHING_TO_MINT")
            return
        self.balances[person] += accrued - minted
        self.issue(REFERRAL_CHANNEL, accrued - minted)
        self.referral_minted[person] = accrued
        self.referral_marks[person] = last
        self.charge(person)
        self.count("mint_referral.SUCCESS")


def derive(p: Params = RECORDED) -> Walk:
    """The whole run, from genesis to the last collection round."""
    if p is RECORDED and _RECORDED_WALK:
        return _RECORDED_WALK[0]
    walk = Walk(p=p, cursor=p.month(0))
    for person in range(p.people):
        walk.balances[person] = ENTRY_AIRDROP
        walk.issue(AIRDROP_CHANNEL, ENTRY_AIRDROP)
        walk.count("register.SUCCESS")
    for seat in sorted(p.seats):
        walk.charge(p.seats[seat][0])
        walk.count("purchase.SUCCESS")
    for window in range(p.end_window + 1):
        if window >= ASSIGNMENT_LAG_WINDOWS:
            walk.assign(window - ASSIGNMENT_LAG_WINDOWS)
        for seat in sorted(p.seats):
            if seat * p.stagger == window:
                walk.activate(seat, window)
        final = window == p.end_window
        for seat in sorted(p.seats):
            if final or p.node_mints(seat, window):
                walk.mint_node(seat, window)
        for seat in sorted(p.seats):
            pool = p.node_mints(seat, window) and seat != p.pool_hoarder
            if final or pool:
                walk.mint_pool(seat)
        for person in p.referrers:
            if final or p.referral_mints(person, window):
                walk.mint_referral(person, window)
    if p is RECORDED:
        _RECORDED_WALK.append(walk)
    return walk


_RECORDED_WALK: list[Walk] = []


def seat_cycles(p: Params = RECORDED) -> int:
    """Every seat's 731 cycles, which is every permission a whole run assigns."""
    return len(p.seats) * ISSUANCE_CYCLES_PER_SEAT


def channel_totals(p: Params = RECORDED) -> dict[int, int]:
    """What the manifest promised for the cycles that ran, channel by channel."""
    totals = {channel: seat_cycles(p) * leg for channel, leg in enumerate(LEGS)}
    totals[REFERRAL_CHANNEL] = seat_cycles(p) * REFERRAL_LEG
    totals[AIRDROP_CHANNEL] = p.people * ENTRY_AIRDROP
    return totals


def within_supply(p: Params = RECORDED) -> bool:
    return sum(channel_totals(p).values()) <= MAXIMUM_SUPPLY_ATOMIC
