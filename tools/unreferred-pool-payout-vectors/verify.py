#!/usr/bin/env python3
"""Independently derive and check the unreferred-pool-payout-v1 vectors.

Every recorded value is rederived twice: once from the accepted documents in
`expected.py`, which imports nothing from `simulation/` and settles the whole
sequence in closed form, and once from a live run of the model, which is a
machine consuming one window at a time and carrying a balance. A value both
reach has been derived by two constructions; a value only the model reproduces
would be a restatement of the model rather than evidence about it.

`--emit` rewrites the vector file from the same derivations through the same
agreement gate, so a recorded value is never transcribed by hand.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import expected as e
from checker import Checker, read_vectors

from simulation.calendar import months as calendar_months
from simulation.unreferred_pool import contract as c
from simulation.unreferred_pool import scenario
from simulation.unreferred_pool.ledger import UnreferredPool, Window


def month_of(index: int) -> int:
    return calendar_months.month_index(scenario.timestamp_of_height(index * 28_800))


def closed_form():
    return e.settle(scenario.SEQUENCE, scenario.ACTIVATIONS, month_of)


def check_constants(check: Checker) -> None:
    check.section("The window arithmetic, imported rather than restated.")
    check.agree("constants.slot_seconds", e.SLOT_SECONDS, c.SLOT_SECONDS)
    check.agree("constants.slots_per_window", e.SLOTS_PER_WINDOW, c.SLOTS_PER_WINDOW)
    check.agree(
        "constants.window_uptime_seconds_max",
        e.WINDOW_UPTIME_SECONDS_MAX,
        c.WINDOW_UPTIME_SECONDS_MAX,
    )
    check.agree(
        "constants.assignment_lag_windows",
        e.ASSIGNMENT_LAG_WINDOWS,
        c.ASSIGNMENT_LAG_WINDOWS,
    )
    check.equal("constants.referral_atomic_per_cycle", scenario.REFERRAL_ATOMIC_PER_CYCLE)


def check_attribution(check: Checker, pool: UnreferredPool) -> None:
    check.section(
        "A window is attributed to the month containing its first height. The "
        "fixture's genesis sits off a day boundary so one window straddles a "
        "month boundary, and the figures the rejected last-height rule would "
        "have produced are recorded beside the real ones."
    )
    for window in scenario.windows():
        check.agree(
            f"attribution.window_{window.index}.month", month_of(window.index), window.month
        )
    check.equal(
        "attribution.straddling_windows",
        ",".join(str(index) for index in scenario.straddling_windows()),
    )
    check.equal("attribution.months_touched", ",".join(str(m) for m in scenario.months_touched()))

    # The straddling window is February's under the accepted rule. Under the
    # rejected one February would hold no uptime at all, which is what makes the
    # two rules distinguishable rather than merely described.
    first_month = scenario.months_touched()[0]
    accepted = {}
    for index, uptime, _accrual in scenario.SEQUENCE:
        if month_of(index) != first_month:
            continue
        for seat, seconds in uptime.items():
            if seconds:
                accepted[seat] = accepted.get(seat, 0) + seconds
    rejected = scenario.figures_under_last_height_attribution(first_month)
    check.equal(
        "attribution.first_month_figures",
        ";".join(f"{seat}={accepted[seat]}" for seat in sorted(accepted)) or "none",
    )
    check.equal(
        "attribution.first_month_figures_under_last_height_rule",
        ";".join(f"{seat}={rejected[seat]}" for seat in sorted(rejected)) or "none",
    )
    check.equal(
        "attribution.the_two_rules_differ_on_this_fixture", accepted != rejected
    )


def check_payouts(check: Checker, pool: UnreferredPool) -> None:
    check.section(
        "Every month the fixture closes, settled by the machine and by the "
        "closed form. The last month is not closed, because no later window "
        "has arrived to close it."
    )
    records, _claims, _payable, _accrued = closed_form()
    live = {payout.month: payout for payout in pool.payouts}

    check.equal("payout.months_settled", len(records))
    if len(records) != len(live):
        check.failures.append(
            f"payout: the closed form settled {len(records)} months and the "
            f"model settled {len(live)}"
        )
        return

    for record in records:
        month = record["month"]
        payout = live[month]
        for field in ("candidate_count", "best_figure", "payable_before", "share", "remainder", "paid"):
            check.agree(f"payout.month_{month}.{field}", record[field], getattr(payout, field))
        check.agree(
            f"payout.month_{month}.winners",
            ",".join(str(seat) for seat in record["winners"]) or "none",
            ",".join(str(seat) for seat in payout.winners) or "none",
        )
        check.equal(f"payout.month_{month}.winner_count", len(payout.winners))
        # A share that does not divide leaves a remainder strictly below the
        # winner count, which is what makes it a remainder rather than a share.
        if payout.winners:
            check.equal(
                f"payout.month_{month}.remainder_is_below_the_winner_count",
                payout.remainder < len(payout.winners),
            )
            check.equal(
                f"payout.month_{month}.share_times_winners_plus_remainder",
                payout.share * len(payout.winners) + payout.remainder,
            )


def check_carry(check: Checker, pool: UnreferredPool) -> None:
    check.section(
        "A month with no candidate carries, and the theorem that says the case "
        "cannot arise once a seat is activated: in-span is a subset of "
        "in-scope, so a month that accrued has someone to pay."
    )
    carried = [payout.month for payout in pool.payouts if payout.carried]
    check.equal("carry.months_carried", ",".join(str(m) for m in carried) or "none")
    check.equal("carry.months_carried_count", len(carried))

    # Every carried month accrued nothing. This is the theorem measured rather
    # than asserted: a carried month that had accrued would mean the rule can
    # strand value, which is the failure the carry exists to prevent and the
    # one it would then be causing.
    records, _claims, _payable, _accrued = closed_form()
    grouped = e.group_by_month(scenario.SEQUENCE, month_of)
    accrual_in_carried = sum(
        accrual
        for month in carried
        for _index, _uptime, accrual in grouped.get(month, [])
    )
    check.equal("carry.accrual_inside_carried_months", accrual_in_carried)
    check.equal(
        "carry.a_carried_month_never_held_accrual", accrual_in_carried == 0
    )

    # And the carry reaches: the balance a carried month left is still payable.
    check.equal("carry.payable_after_the_run", pool.payable)


def check_conservation(check: Checker, pool: UnreferredPool) -> None:
    check.section(
        "Every unit the pool received is undistributed or owed to a named "
        "winner, checked after every assignment rather than at the end."
    )
    records, claims, payable, accrued = closed_form()
    check.agree("conservation.accrued", accrued, pool.accrued)
    check.agree("conservation.payable", payable, pool.payable)
    check.agree("conservation.assigned", sum(claims.values()), pool.assigned)
    check.equal(
        "conservation.accrued_equals_payable_plus_assigned",
        pool.accrued == pool.payable + pool.assigned,
    )
    check.equal("conservation.claim_count", len(pool.claims))
    for month, seat in sorted(pool.claims):
        check.agree(
            f"claim.month_{month}.seat_{seat}",
            claims[(month, seat)],
            pool.claims[(month, seat)],
        )
    # A zero share writes no claim, so no recorded claim is zero.
    check.equal(
        "conservation.no_recorded_claim_is_zero",
        all(amount > 0 for amount in pool.claims.values()),
    )


def check_candidates(check: Checker, pool: UnreferredPool) -> None:
    check.section(
        "The candidate set: in scope at any point in the month, no duty gate, "
        "no accumulation-cap filter, derived from the seat table rather than "
        "from what anyone happened to accumulate."
    )
    grouped = e.group_by_month(scenario.SEQUENCE, month_of)
    for month in scenario.months_touched():
        closed = e.candidates(grouped.get(month, []), scenario.ACTIVATIONS)
        check.agree(
            f"candidates.month_{month}",
            ",".join(str(seat) for seat in closed) or "none",
            ",".join(str(seat) for seat in pool.candidates(month)) or "none",
        )
    for seat, height in sorted(scenario.ACTIVATIONS.items()):
        check.agree(
            f"candidates.seat_{seat}.first_cycle_window",
            e.first_cycle_window(height),
            pool.first_window(seat),
        )
    # A seat that ran zero seconds all month is still a candidate, which is what
    # "no duty gate" means and what a figures-derived candidate set would lose.
    zero_month = 676
    ran = {seat for (month, seat) in pool.claims if month == zero_month}
    check.equal(
        "candidates.a_month_of_zeroes_still_has_every_candidate",
        len(pool.candidates(zero_month)) == len(scenario.ACTIVATIONS),
    )
    check.equal("candidates.month_of_zeroes_winner_count", len(ran))


def check_ordering(check: Checker) -> None:
    check.section(
        "Two orderings the rule states and that are invisible without a test: "
        "several months closed by one assignment settle in ascending order, and "
        "the payout precedes the closing assignment's own accrual."
    )
    # Ascending order: the run that closes three months at once must pay the
    # earliest first, or a carry cannot reach a later month.
    pool = scenario.build()
    batch = [p.month for p in pool.payouts]
    check.equal("ordering.settled_months", ",".join(str(m) for m in batch))
    check.equal("ordering.settled_months_ascend", batch == sorted(batch))

    # Payout before accrual: run the final window's accrual first and the
    # closing month is paid a window of its successor's accrual. The figure the
    # wrong order produces is recorded, so the rule is normative rather than
    # described.
    correct = scenario.build()
    wrong = UnreferredPool(scenario.ACTIVATIONS)
    for window in scenario.windows():
        if window.month > (wrong.last_assigned_month or window.month):
            # accrue first, then let `assign` settle on the inflated balance
            inflated = Window(window.index, window.month, dict(window.uptime), 0)
            wrong.payable += window.accrual
            wrong.accrued += window.accrual
            wrong.assign(inflated)
        else:
            wrong.assign(window)
    check.equal(
        "ordering.the_wrong_order_pays_a_different_amount",
        wrong.assigned != correct.assigned,
    )
    check.equal("ordering.assigned_in_the_stated_order", correct.assigned)
    check.equal("ordering.assigned_if_accrual_ran_first", wrong.assigned)


def check_bounds(check: Checker, pool: UnreferredPool) -> None:
    check.section("The bounds the rule imposes, and the guard behind the figure.")

    # Measured rather than asserted: replay the run and record the most months
    # that ever hold an open figure at once. The claim is that assignment lag
    # never leaves a third month accumulating, because the payout fires as soon
    # as a window of a later month arrives.
    replay = UnreferredPool(scenario.ACTIVATIONS)
    most = 0
    for window in scenario.windows():
        replay.assign(window)
        most = max(most, len({month for month, _seat in replay.figures}))
    check.equal("bounds.most_months_accumulating_at_once", most)

    check.equal("bounds.open_figures_after_the_run", len(pool.figures))
    check.equal(
        "bounds.nominal_month_figure_seconds_max", 31 * c.WINDOW_UPTIME_SECONDS_MAX
    )
    # The figure accumulates with a checked addition rather than an
    # assumed-safe one, because how many windows fall in a month depends on the
    # block rate and no consensus rule bounds that from above.
    check.equal("bounds.max_figure_seconds", c.MAX_FIGURE_SECONDS)


def check_state(check: Checker, pool: UnreferredPool) -> None:
    check.section("The model's own state label, schema, and digest.")
    check.equal("state.schema", c.STATE_SCHEMA)
    check.equal("state.label", c.STATE_LABEL)
    check.equal("state.digest", pool.state_digest())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vectors",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "test-vectors"
        / "unreferred-pool-payout-v1.txt",
    )
    parser.add_argument(
        "--emit",
        action="store_true",
        help="rewrite the vector file from the derivations instead of checking it",
    )
    arguments = parser.parse_args()

    c.assert_exact_derivation()
    c.assert_agrees_with_cycle_boundary()
    c.assert_agrees_with_uptime_measurement()

    pool = scenario.build()
    if scenario.build().state_digest() != pool.state_digest():
        sys.stderr.write("the model is not deterministic across repeated runs\n")
        return 1

    check = Checker(read_vectors(arguments.vectors), emit=arguments.emit)
    check_constants(check)
    check_attribution(check, pool)
    check_candidates(check, pool)
    check_payouts(check, pool)
    check_carry(check, pool)
    check_conservation(check, pool)
    check_ordering(check)
    check_bounds(check, pool)
    check_state(check, pool)
    check.require_full_coverage()

    for failure in check.failures:
        sys.stderr.write(f"vector mismatch: {failure}\n")
    if check.failures:
        return 1

    if arguments.emit:
        written = check.write(arguments.vectors)
        sys.stdout.write(f"emitted {written} unreferred-pool-payout-v1 vectors\n")
        return 0

    sys.stdout.write(
        f"derived and matched {check.checked} unreferred-pool-payout-v1 vectors\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
