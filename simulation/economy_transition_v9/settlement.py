"""The monthly settlement: which month closes, who competes, and what is paid.

This is `unreferred-pool-payout-v1`'s rule over the quantities version nine
encodes. It **binds** that specification's accepted model rather than restating
its judgement: `assert_agrees_with_unreferred_pool` drives both over the same
inputs and requires the winners, the share, the remainder and the claim totals to
be identical, so a divergence is a test failure rather than a second opinion.

**Exactly one month can close per assignment, and the rule says so.** Window
attribution is non-decreasing and consecutive assigned windows carry the cursor's
month and the new one with nothing between them, so every index strictly between
is an **empty** month: no window is attributed to it, so it has no accrual and no
candidates, and a pass over it leaves the balance exactly as it found it. Version
nine therefore pays the cursor's month and advances, in one pass.

**That is a bound as much as a derivation, which is why it is a rule rather than
an optimisation an implementation might make.** The gap between the two months is
bounded by nothing a chain controls: a network halted for a year resumes with
twelve empty months between, and a genesis timestamp decades in the past would
close hundreds at the first assignment. Iterating them would make one block's
work proportional to how long the network was down — a denial of service
reachable by an outage rather than by an attacker.

**No invariant over a single accepted state separates the single pass from the
loop**, because they agree on every state both produce. What separates them is a
scenario, so `assert_single_pass_equals_loop` settles the same inputs both ways
and requires them equal, and a vector runs it over a multi-month halt.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.common.canonical import InvariantError, checked_add
from simulation.cycle_boundary.grid import first_cycle_window

from . import contract as c

__all__ = [
    "Pool",
    "Settlement",
    "apply_settlement",
    "assert_agrees_with_unreferred_pool",
    "assert_single_pass_equals_loop",
    "candidates",
    "close_month",
    "settle_month",
]


@dataclass
class Pool:
    """The three quantities kind 12 carries, as a value a settlement rewrites."""

    accrued: int = 0
    payable: int = 0
    minted: int = 0

    def assert_conserved(self, claims: dict[int, tuple[int, int]]) -> None:
        """The two identities, stated over the encoded state rather than argued.

        The first is `unreferred-pool-payout-v1`'s: every unit the pool has
        received is either still undistributed or is owed to a named winner, and
        none is anywhere else. The second is the one that specification names for
        completeness and leaves to the version that implements a mint, and
        version nine states it as an **equality** rather than the bound
        `minted <= accrued - payable`, because an equality catches a unit minted
        twice and the bound does not.
        """
        assigned = sum(accrued for accrued, _ in claims.values())
        if self.accrued != self.payable + assigned:
            raise InvariantError(
                f"pool accrued {self.accrued} != payable {self.payable} + assigned "
                f"{assigned}"
            )
        taken = sum(minted for _, minted in claims.values())
        if self.minted != taken:
            raise InvariantError(
                f"pool minted {self.minted} != the claims' minted total {taken}"
            )


@dataclass(frozen=True)
class Settlement:
    """One month's settlement, recorded whether or not it paid."""

    month: int
    candidate_count: int
    best_figure: int
    winners: tuple[int, ...]
    payable_before: int
    share: int
    remainder: int
    assigned: int

    @property
    def carried(self) -> bool:
        """A month that paid nothing, for either of the two reasons.

        No candidate at all — the safety net ADR 0075 decided, unreachable once
        any seat is activated — or a share that rounded to zero.
        """
        return self.assigned == 0


def candidates(activations: dict[int, int], last_window: int) -> tuple[int, ...]:
    """Every seat in scope at any point in the month, in ascending seat order.

    Derived from the seat table rather than from the accumulated figures, because
    `in_scope` is monotone in the window: a seat is a candidate for a month
    exactly when its first cycle window is at or below the last window attributed
    to that month. Reading the set out of the figures instead would silently
    exclude every seat that ran nothing, which is the whole reason zero-figure
    candidates exist.
    """
    return tuple(
        seat
        for seat in sorted(activations)
        if first_cycle_window(activations[seat]) <= last_window
    )


def settle_month(
    month: int,
    month_candidates: tuple[int, ...],
    figures: dict[int, int],
    payable: int,
) -> Settlement:
    """Rank one completed month. Pure: it writes nothing and reads no state.

    `figures` holds only the seats that ran; a candidate that is absent has a
    figure of zero, which is what makes a zero-uptime seat a candidate without
    anything having written a zero for it.
    """
    if not month_candidates:
        # The theorem `unreferred-pool-payout-v1` proves: an accrual in a month
        # implies a seat was in span in a window attributed to it, in-span
        # implies in-scope, and in-scope never expires. A month that accumulated
        # uptime and has nobody to pay means the derivation is broken, not that
        # the carry is doing its job.
        if figures:
            raise InvariantError(
                f"month {month} accumulated uptime and has no candidate"
            )
        return Settlement(month, 0, 0, (), payable, 0, payable, 0)

    best = max(figures.get(seat, 0) for seat in month_candidates)
    winners = tuple(
        seat for seat in month_candidates if figures.get(seat, 0) == best
    )
    share = payable // len(winners)
    assigned = share * len(winners)
    return Settlement(
        month=month,
        candidate_count=len(month_candidates),
        best_figure=best,
        winners=winners,
        payable_before=payable,
        share=share,
        remainder=payable - assigned,
        assigned=assigned,
    )


def apply_settlement(
    settlement: Settlement,
    pool: Pool,
    claims: dict[int, tuple[int, int]],
    figures: dict[tuple[int, int], int],
) -> None:
    """Write what a settlement decided: the claims, the balance, the deletion.

    **A zero share writes no claim entry**, which is a rule rather than an
    optimisation: a claim is a balance and a balance of zero is absence, the same
    rule the monthly figure follows. In the zero-best month that is the difference
    between writing up to 100,000 entries recording that nobody was paid anything
    and writing none.
    """
    if settlement.share:
        for seat in settlement.winners:
            accrued, minted = claims.get(seat, (0, 0))
            total = checked_add(accrued, settlement.share)
            if total is None:  # pragma: no cover - bounded by the pool itself
                raise InvariantError(f"the claim for seat {seat} exceeds u64")
            claims[seat] = (total, minted)
    pool.payable = settlement.remainder
    for key in [k for k in figures if k[0] == settlement.month]:
        del figures[key]


def close_month(
    cursor: int,
    due_month: int,
    activations: dict[int, int],
    last_window: int,
    pool: Pool,
    claims: dict[int, tuple[int, int]],
    figures: dict[tuple[int, int], int],
) -> tuple[Settlement | None, tuple[int, ...]]:
    """The single pass. Returns what was settled and the empty indices skipped.

    `due_month` is the assigned window's month, read from its kind-20 entry, and
    `last_window` is the last window attributed to the closing month, which is
    the assigned window's predecessor.
    """
    if due_month < cursor:
        raise InvariantError(
            f"the assigned window is in month {due_month}, behind the cursor "
            f"{cursor}"
        )
    if due_month > c.MAX_MONTH_INDEX or cursor > c.MAX_MONTH_INDEX:
        raise InvariantError("a month index is outside calendar-v1's range")
    if due_month == cursor:
        return None, ()

    settlement = settle_month(
        cursor,
        candidates(activations, last_window),
        {seat: seconds for (month, seat), seconds in figures.items() if month == cursor},
        pool.payable,
    )
    apply_settlement(settlement, pool, claims, figures)
    pool.assert_conserved(claims)
    return settlement, tuple(range(cursor + 1, due_month))


def assert_single_pass_equals_loop(
    cursor: int,
    due_month: int,
    activations: dict[int, int],
    last_window: int,
    pool: Pool,
    claims: dict[int, tuple[int, int]],
    figures: dict[tuple[int, int], int],
) -> None:
    """Require the single pass and an explicit per-index loop to agree exactly.

    The loop is `unreferred-pool-payout-v1`'s rule written literally — one pass
    per closed index in ascending order — and it is run here against a copy so
    the comparison costs the caller nothing. The two must reach the same balance,
    the same claims, and the same remaining figures.

    This is the evidence the equivalence needs, because no invariant over a
    single accepted state separates the two: they agree on every state both
    produce, so what distinguishes them is a scenario.
    """
    looped_pool = Pool(pool.accrued, pool.payable, pool.minted)
    looped_claims = dict(claims)
    looped_figures = dict(figures)
    for month in range(cursor, due_month):
        month_figures = {
            seat: seconds
            for (index, seat), seconds in looped_figures.items()
            if index == month
        }
        # An empty month has no window attributed to it, so it has no last
        # window and no candidate set to read against. Its pass is a no-op.
        window = last_window if month == cursor else None
        settlement = settle_month(
            month,
            candidates(activations, window) if window is not None else (),
            month_figures,
            looped_pool.payable,
        )
        apply_settlement(settlement, looped_pool, looped_claims, looped_figures)

    single_pool = Pool(pool.accrued, pool.payable, pool.minted)
    single_claims = dict(claims)
    single_figures = dict(figures)
    close_month(
        cursor, due_month, activations, last_window, single_pool, single_claims,
        single_figures,
    )

    for name, looped, single in (
        ("payable", looped_pool.payable, single_pool.payable),
        ("claims", looped_claims, single_claims),
        ("figures", looped_figures, single_figures),
    ):
        if looped != single:
            raise InvariantError(
                f"closing months {cursor}..{due_month - 1} the two ways disagrees "
                f"on {name}: the loop gives {looped!r} and the single pass gives "
                f"{single!r}"
            )


def assert_agrees_with_unreferred_pool(
    month: int,
    activations: dict[int, int],
    last_window: int,
    figures: dict[int, int],
    payable: int,
) -> None:
    """Require this arithmetic to be `unreferred-pool-payout-v1`'s model's.

    The accepted model is a machine over a window sequence and this is a function
    over one month's inputs, so the comparison is made where the two are the same
    subject: the candidate set, the winners, the share and the remainder for one
    completed month. A restatement that reached a different winner would fail
    here rather than survive as a second opinion about who is paid.
    """
    from simulation.unreferred_pool.ledger import UnreferredPool

    reference = UnreferredPool(activations)
    reference.month_last_window[month] = last_window
    reference.figures = {(month, seat): seconds for seat, seconds in figures.items()}
    reference.payable = payable
    reference.accrued = payable
    theirs = reference._settle(month)

    ours = settle_month(
        month, candidates(activations, last_window), figures, payable
    )
    mismatches = [
        name
        for name, here, there in (
            ("candidate count", ours.candidate_count, theirs.candidate_count),
            ("best figure", ours.best_figure, theirs.best_figure),
            ("winners", ours.winners, theirs.winners),
            ("share", ours.share, theirs.share),
            ("remainder", ours.remainder, theirs.remainder),
            ("assigned", ours.assigned, theirs.paid),
        )
        if here != there
    ]
    if mismatches:
        raise InvariantError(
            f"month {month}: version nine and unreferred-pool-payout-v1 disagree "
            f"on {', '.join(mismatches)}"
        )
