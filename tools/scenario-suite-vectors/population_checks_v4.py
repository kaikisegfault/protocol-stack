"""Suite version four: the live population run against its closed form.

Every monetary value and every count is `agree`d, so it must match
`expected_v4.py`'s walk before it is compared with the recorded file. The only
values the file pins from the live run alone are the state roots, which are
digests of an encoding the closed form does not restate. Those are what fail
if the contract's state shape changes under the run.
"""

from __future__ import annotations

from types import ModuleType

from checker import Checker

from simulation.economy_transition_v9 import contract as c
from simulation.scenarios import economy_population_v4 as population


def _winners(values: tuple[int, ...]) -> str:
    return ",".join(str(seat) for seat in values) or "none"


def check_fixture(check: Checker, x: ModuleType, run, p) -> None:
    fixture = run.fixture
    check.agree("fixture.people", fixture.people, p.people)
    check.agree("fixture.seats", len(fixture.seats), len(p.seats))
    check.agree(
        "fixture.referred_seats",
        sum(1 for _o, r in fixture.seats.values() if r is not None),
        sum(1 for _o, r in p.seats.values() if r is not None),
    )
    check.agree("fixture.stagger", fixture.stagger, p.stagger)
    check.agree("fixture.millis_per_block", fixture.millis_per_block, p.millis_per_block)
    check.agree("fixture.genesis_millis", fixture.genesis_millis, p.genesis_millis)
    check.agree("fixture.last_span_window", fixture.last_span_window, p.last_span_window)
    check.agree("fixture.drain_window", fixture.drain_window, p.drain_window)
    check.agree("fixture.end_window", fixture.end_window, p.end_window)
    check.agree(
        "fixture.windows_checked", run.observed.windows_checked, p.end_window + 1
    )
    check.agree("contract.cycles_per_seat", c.ISSUANCE_CYCLES_PER_SEAT,
                x.ISSUANCE_CYCLES_PER_SEAT)
    check.agree("contract.referral_leg", c.REFERRAL_LEG_ATOMIC, x.REFERRAL_LEG)
    check.agree("contract.mint_accumulation_cap", c.MINT_ACCUMULATION_CAP,
                x.MINT_ACCUMULATION_CAP)
    for channel, leg in c.BASE_PERMISSION_LEGS:
        check.agree(f"contract.leg.{channel}", leg, x.LEGS[channel])


def check_promise(check: Checker, x: ModuleType, run, p) -> None:
    """Claim one: every channel delivers what the manifest promised for the
    cycles that ran, with nothing left outstanding and nothing left pooled.

    Only a run that reaches every seat's last cycle and the drain can make this
    claim, so a property run stopped at a horizon skips it.
    """
    ledger, totals = run.ledger, x.channel_totals(p)
    for channel in sorted(totals):
        check.agree(f"channel.{channel}.promised", ledger.channel_issued[channel],
                    totals[channel])
    check.agree("channel.outstanding_total", sum(ledger.channel_outstanding.values()), 0)


def check_channels(check: Checker, x: ModuleType, run, p) -> None:
    """What each channel issued, and every window-level count, against the walk."""
    ledger, walk = run.ledger, x.derive(p)
    for channel in sorted(x.channel_totals(p)):
        check.agree(f"channel.{channel}.issued", ledger.channel_issued[channel],
                    walk.issued.get(channel, 0))
    check.agree("assigned_permissions", ledger.assigned_permissions, walk.assigned)
    check.agree("recovery_pool.final", sum(ledger.pool.values()), sum(walk.pool))
    check.agree("recovery_pool.peak", run.observed.peak_recovery_pool, walk.peak_pool)

    records = population.assignments(ledger)
    live = {
        "empty_winner_windows": sum(
            1 for r in records.values() if r["in_scope_count"] and not r["winner_count"]
        ),
        "multi_winner_windows": sum(1 for r in records.values() if r["winner_count"] > 1),
        "reallocated_permissions": sum(r["reallocated_count"] for r in records.values()),
        "over_cap_seat_windows": _over_cap(run.fixture, records),
    }
    for name, value in live.items():
        check.agree(f"windows.{name}", value, walk.counts.get(name, 0))


def _over_cap(fixture, records: dict[int, dict]) -> int:
    """In-span seats that met the cycle and still accrued nothing: the cap."""
    from simulation.economy_transition_v3.contract import ACTIVITY_THRESHOLD_SECONDS
    from simulation.economy_transition_v3.state import bit_is_set

    count = 0
    for window, record in records.items():
        for seat in fixture.seats:
            if not fixture.first_cycle_window(seat) <= window <= (
                fixture.last_cycle_window(seat)
            ):
                continue
            credited, disputed = fixture.slots(seat, window)
            met = (credited - disputed) * c.SLOT_SECONDS >= ACTIVITY_THRESHOLD_SECONDS
            if met and not bit_is_set(record["accrued_bitmap"], seat):
                count += 1
    return count


def check_referral(check: Checker, x: ModuleType, run, p) -> None:
    """Claim two: every referral leg is a referrer's or the unreferred pool's."""
    ledger, walk = run.ledger, x.derive(p)
    for referrer in p.referrers:
        balance = ledger.referral[population.person(referrer)[0]]
        check.agree(f"referral.{referrer}.accrued", balance.accrued_atomic,
                    walk.referral_accrued[referrer])
        check.agree(f"referral.{referrer}.minted", balance.minted_atomic,
                    walk.referral_minted[referrer])
    # The unreferred seats' assigned cycles reach the pool by construction, so
    # whatever else the pool accrued is a referral leg the cap forfeited.
    fixture = run.fixture
    unreferred_cycles = sum(
        1
        for window in population.assignments(ledger)
        for seat, (_owner, referrer) in fixture.seats.items()
        if referrer is None
        and fixture.first_cycle_window(seat) <= window <= fixture.last_cycle_window(seat)
    )
    check.agree(
        "referral.forfeited_legs",
        ledger.pool_accrued // c.REFERRAL_LEG_ATOMIC - unreferred_cycles,
        walk.counts.get("forfeited_referral_legs", 0),
    )
    check.agree("unreferred.accrued", ledger.pool_accrued, walk.unreferred_accrued)
    check.agree("unreferred.minted", ledger.pool_minted,
                sum(claim[1] for claim in walk.claims.values()))
    check.agree("unreferred.payable", ledger.pool_payable, walk.payable)


def check_months(check: Checker, x: ModuleType, run, p) -> None:
    """Claim three: each month's pool reached that month's best performers."""
    live = [settled for _window, settled in run.observed.settlements]
    walk = x.derive(p)
    check.agree("months.settled", len(live), len(walk.months))
    check.agree(
        "months.paid_nothing",
        sum(1 for settled in live if settled.carried),
        sum(1 for month in walk.months if month[3] == 0),
    )
    for settled, (index, winners, before, share, after) in zip(live, walk.months):
        prefix = f"month.{index}"
        check.agree(f"{prefix}.index", settled.month, index)
        check.agree(f"{prefix}.winners", _winners(settled.winners), _winners(winners))
        check.agree(f"{prefix}.payable", settled.payable_before, before)
        check.agree(f"{prefix}.share", settled.share, share)
        check.agree(f"{prefix}.carried", settled.remainder, after)
    for seat in sorted(p.seats):
        accrued, minted = run.ledger.claim(seat)
        expected = walk.claims.get(seat, [0, 0])
        check.agree(f"claim.{seat}.accrued", accrued, expected[0])
        check.agree(f"claim.{seat}.minted", minted, expected[1])


def check_supply(check: Checker, x: ModuleType, run, p) -> None:
    """Claim four: no unit issued twice or lost, down to each escrow."""
    ledger, walk = run.ledger, x.derive(p)
    check.agree("supply.total", ledger.total_supply, sum(walk.issued.values()))
    check.agree("supply.fee_pool", ledger.fee_pool, walk.fees)
    check.agree("supply.within_maximum",
                ledger.total_supply <= ledger.supply_limit, x.within_supply(p))
    for index in range(p.people):
        check.agree(f"balance.{index}", ledger.balance(run.escrow(index)),
                    walk.balances[index])
    outcomes = {f"{label}.{result}" for label, result in run.observed.results}
    derived = {name for name in walk.counts if "." in name}
    check.agree("transactions.outcomes", ",".join(sorted(outcomes)),
                ",".join(sorted(derived)))
    for (label, result), count in sorted(run.observed.results.items()):
        check.agree(f"transactions.{label}.{result}", count,
                    walk.counts.get(f"{label}.{result}", 0))


def check_roots(check: Checker, run) -> None:
    """The one thing pinned from the live run alone: what the state commits to."""
    for window, root in sorted(run.observed.roots.items()):
        check.equal(f"root.{window}", root)


def check_population(check: Checker, x: ModuleType, run, p=None) -> None:
    """Every section, over the recorded fixture unless another is named."""
    p = x.RECORDED if p is None else p
    check_fixture(check, x, run, p)
    check_promise(check, x, run, p)
    check_differential(check, x, run, p)
    check_roots(check, run)


def check_differential(check: Checker, x: ModuleType, run, p) -> None:
    """Every section that compares the contract with the walk and nothing else.

    It holds for any fixture and any horizon, which is what the property tests
    draw.
    """
    check_channels(check, x, run, p)
    check_referral(check, x, run, p)
    check_months(check, x, run, p)
    check_supply(check, x, run, p)
