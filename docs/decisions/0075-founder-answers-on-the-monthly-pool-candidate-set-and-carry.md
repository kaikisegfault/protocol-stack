# ADR 0075: Founder answers on the monthly pool's candidate set and an unpayable accrual

- Status: Accepted
- Date: 2026-09-14
- Bounds: [ADR 0049](0049-the-recovery-pool-and-permanent-best-performer-ranking.md),
  [ADR 0050](0050-the-block-timestamp-is-the-ecosystem-clock.md),
  [ADR 0074](0074-the-consensus-timestamp-and-the-calendar-month.md)
- Relates to: `docs/project/founder-constitution.md` (the unreferred performance
  pool), the unreferred pool's payout slice

## Context

The Founder Constitution routes an unreferred seat's 34.2 units per cycle to the
**unreferred performance pool**, and pays that pool to the **single
best-performing** Founder Seat of the month, ranked by cumulative fully
operational uptime, with exact ties sharing equally — "whatever that figure is",
which decides that there is **no minimum**.

[`calendar-v1`](../specifications/calendar-v1.md) and
[ADR 0074](0074-the-consensus-timestamp-and-the-calendar-month.md) delivered the
month on 2026-09-14 and deliberately stopped there. Running the founder-decision
gate over the payout that follows surfaced two decisions the accepted documents
do **not** distinguish between, and both change who receives value, which is the
test that makes a decision founder-reserved rather than mechanism:

1. **Whose figure is compared.** "Single best-performing Founder Seat of the
   month" fixes the rule and not the candidate set. A seat in scope at the
   month's end, a seat in scope at any point during it, and a seat that met at
   least one cycle in it are three different sets that pay three different people
   in an ordinary month.
2. **Where a month's accrual goes when the candidate set is empty.** The daily
   failed-cycle reallocation has the recovery pool, which ADR 0049 created so
   that 100% of the node distribution is assigned. The monthly pool has no
   stated analogue, and an empty candidate set is reachable: unreferred seats
   accrue through a month whose last in-scope span ends inside it.

They were recorded as not-yet-blocking during M3.15a's gate and raised at its
close, once `calendar-v1` was accepted and they became the nearest dependency.

## Decision

### 1. The candidate set is every seat in scope at any point in the month

Any seat whose 731-cycle span overlapped the month competes, ranked on the uptime
it accumulated **during that month**. Membership is not decided by a snapshot at
either edge.

The owner's reason is the fairness case the alternative fails: **a seat that ran
29 of 30 days and whose span ended on the 30th is exactly the machine the pool
exists to reward**, and a month's-end snapshot would exclude it and pay a worse
performer instead.

**Rejected: in scope at the month's end.** It is the simplest to implement — one
snapshot and no per-month membership — and it forfeits a month a seat mostly
earned. It also degrades at the end of the distribution, where the candidate set
would shrink toward empty as spans expire while the pool still holds accrual.

**Rejected: a floor of at least one met cycle.** It would keep a permanently dead
machine from winning a month in which nobody ran, and it is a **minimum**, which
the constitution's "whatever that figure is" reads as having already decided
against.

### 2. An unpayable accrual carries to the earliest subsequent month with a candidate

A month with accrual and no candidate does not pay. Its accrual stays in the
pool, and the earliest subsequent month that has a candidate takes it entirely.

This is [ADR 0049](0049-the-recovery-pool-and-permanent-best-performer-ranking.md)'s
recovery-pool shape applied to the monthly pool rather than a second mechanism
invented for it, which is why it was the recommendation: the rule, its carry, and
its "earliest subsequent winner takes it entirely" are already accepted, already
modelled, and already understood.

**Rejected: routing into the ADR 0049 recovery pool itself.** One pool instead of
two is tidier and it mixes a monthly accrual into a daily mechanism, so a *day's*
best performer would collect value a *month's* ranking was meant to award.

**Rejected: paying the treasury.** It guarantees the channel is assigned with no
carry state at all, and it moves value out of Founder Machines and into the
company, which the node distribution otherwise never does.

**Rejected: asserting the case cannot happen.** If it is in fact reachable — and
the end of the distribution is where it would be — the chain would halt rather
than pay anyone.

## Consequences

**The unreferred pool's payout slice is unblocked.** Its remaining decisions are
specification work the constitution names outright: the pool's remainder rule,
the storage bound on accrued referral balances at 100,000 seats, and when a
referral benefit begins for a seat purchased but never activated.

**Membership is a range overlap rather than a snapshot**, so the payout
transition reads each seat's activation height and 731-window span against the
month's height span rather than against a single height. `calendar-v1` supplies
the month's span, and `cycle-boundary-v1` supplies the seat's, so neither is new
machinery.

**The payout executes in the block that opens the next month.** That is ADR
0074's derivation rather than a choice here: a month's last height is not
recognisable when it executes, so the opening block is the only point at which a
completed month is final. The same block closes every month index in
`[month_of(h - 1), month_of(h))`, so a carry that spans a halt is settled in one
step rather than in one step per skipped month.

**One case is deliberately left open.** A final accrual at the very end of the
distribution may have no later month with a candidate at all. The carry rule does
not say where that goes; the question put it as the option's cost and the owner
accepted it. **It is the payout slice's to raise again** if its own model shows
the case is reachable rather than theoretical, and it must be raised rather than
answered autonomously, because it would decide a beneficiary.
