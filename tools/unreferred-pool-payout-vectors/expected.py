"""Independent derivation of the unreferred pool's payout.

This module imports nothing from `simulation/`. It restates the rules the
accepted documents state, in the words those documents use, and reaches every
recorded value by a different construction from the model's.

**The constructions differ on purpose.** The model is a machine: it consumes
windows one at a time, carries a balance, and settles a month when a later
month's window arrives. This module is a **closed form**: given the whole
sequence it groups windows by month, sums each seat's figure directly, and
folds the balance forward month by month. Neither is derived from the other, so
a value they agree on has been reached twice rather than stated twice.

Sources restated here, and nowhere derived from the model:

- "The pool is paid to the **single best-performing** Founder Seat of the
  month. Where several seats stand at exactly the same top figure — whatever
  that figure is — they share it equally." - `founder-constitution.md`.
- The candidate set is every seat in scope at any point in the month, with no
  duty gate and no accumulation-cap filter - ADR 0075 and ADR 0076.
- A month with no candidate carries its accrual to the earliest subsequent
  month that has one - ADR 0075.
- `first_cycle_window(a) = window_of_height(a) + 1` and a window of 28,800
  heights - `cycle-boundary-v1`.
- `uptime_seconds = credited_slots * SLOT_SECONDS`, 24 slots of 3,600 seconds -
  `uptime-measurement-v1` as `economy-transition-v8` applies it.
"""

from __future__ import annotations

CYCLE_BLOCKS = 28_800
SLOT_SECONDS = 3_600
SLOTS_PER_WINDOW = 24
WINDOW_UPTIME_SECONDS_MAX = SLOTS_PER_WINDOW * SLOT_SECONDS
ASSIGNMENT_LAG_WINDOWS = 2


def first_cycle_window(activation_height: int) -> int:
    return activation_height // CYCLE_BLOCKS + 1


def in_scope(activation_height: int, window: int) -> bool:
    return first_cycle_window(activation_height) <= window


def group_by_month(sequence, month_of) -> dict[int, list]:
    """Every window of the sequence, grouped by the month it is attributed to."""
    grouped: dict[int, list] = {}
    for index, uptime, accrual in sequence:
        grouped.setdefault(month_of(index), []).append((index, uptime, accrual))
    return grouped


def month_order(sequence, month_of) -> list[int]:
    """Every month index from the first assigned to the last, gaps included.

    The gaps are the months a halt left with no window at all, and they are in
    the list because the payout runs once per closed index rather than once per
    month that happens to hold a window.
    """
    months = [month_of(index) for index, _u, _a in sequence]
    return list(range(min(months), max(months) + 1))


def figures(windows, activations) -> dict[int, int]:
    """Each seat's summed uptime over a month's windows."""
    totals: dict[int, int] = {}
    for index, uptime, _accrual in windows:
        for seat, seconds in uptime.items():
            if seconds:
                totals[seat] = totals.get(seat, 0) + seconds
    return totals


def candidates(windows, activations) -> tuple[int, ...]:
    """Every seat in scope at the month's last window, in ascending order."""
    if not windows:
        return ()
    last = max(index for index, _u, _a in windows)
    return tuple(
        seat for seat in sorted(activations) if in_scope(activations[seat], last)
    )


def settle(sequence, activations, month_of) -> tuple[list[dict], dict, int, int]:
    """Fold the whole sequence and return each month's settlement.

    Returns the per-month records, the claims, the final payable, and the total
    accrued. The closed form: every month from the first to the last is settled
    in ascending order, taking the balance as it stands, and the **last** month
    of the sequence is not settled because no later window has arrived to close
    it.
    """
    grouped = group_by_month(sequence, month_of)
    order = month_order(sequence, month_of)
    last_month = order[-1]

    payable = 0
    accrued = 0
    claims: dict[tuple[int, int], int] = {}
    records: list[dict] = []

    for month in order:
        windows = grouped.get(month, [])
        if month == last_month:
            # Its own accrual still lands; nothing closes it.
            for _index, _uptime, accrual in windows:
                payable += accrual
                accrued += accrual
            break

        # The payout runs before this month's successor accrues, so a month is
        # settled on the balance standing after its own windows and before the
        # next month's first one.
        for _index, _uptime, accrual in windows:
            payable += accrual
            accrued += accrual

        month_candidates = candidates(windows, activations)
        month_figures = figures(windows, activations)
        payable_before = payable

        if not month_candidates:
            records.append(
                {
                    "month": month,
                    "candidate_count": 0,
                    "best_figure": 0,
                    "winners": (),
                    "payable_before": payable_before,
                    "share": 0,
                    "remainder": 0,
                    "paid": 0,
                }
            )
            continue

        best = max(month_figures.get(seat, 0) for seat in month_candidates)
        winners = tuple(
            seat for seat in month_candidates if month_figures.get(seat, 0) == best
        )
        share = payable_before // len(winners)
        paid = share * len(winners)
        remainder = payable_before - paid
        if share:
            for seat in winners:
                claims[(month, seat)] = claims.get((month, seat), 0) + share
        payable = remainder

        records.append(
            {
                "month": month,
                "candidate_count": len(month_candidates),
                "best_figure": best,
                "winners": winners,
                "payable_before": payable_before,
                "share": share,
                "remainder": remainder,
                "paid": paid,
            }
        )

    return records, claims, payable, accrued
