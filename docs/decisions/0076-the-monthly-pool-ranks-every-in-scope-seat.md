# ADR 0076: The monthly pool ranks every in-scope seat, with no duty gate and no accumulation cap

- Status: Accepted
- Date: 2026-09-14
- Bounds: [ADR 0035](0035-founder-answers-on-payout-the-cap-and-hub-recovery.md),
  [ADR 0049](0049-the-recovery-pool-and-permanent-best-performer-ranking.md),
  [ADR 0075](0075-founder-answers-on-the-monthly-pool-candidate-set-and-carry.md)
- Relates to: `docs/specifications/economy-transition-v7.md`, the unreferred
  pool's payout slice

## Context

[ADR 0075](0075-founder-answers-on-the-monthly-pool-candidate-set-and-carry.md)
settled two of the payout's founder-reserved decisions on 2026-09-14: the
monthly candidate set is every seat **in scope at any point in the month**,
ranked on the uptime it accumulated during that month, and an accrual with no
candidate carries to the earliest subsequent month that has one.

**Starting the payout slice immediately afterwards found accepted text that says
something else**, and it had not been surfaced when those two were asked.
`economy-transition-v7` defines the per-cycle eligible set and then points it at
the monthly pool:

> The eligible set is **every** in-scope seat that met the cycle's duty threshold
> and is under the accumulation cap, in span or not. It is the candidate set for
> the winner derivation, so it is what competes for the daily reallocation, for
> the recovery pool, **and for the monthly unreferred pool**.

That sentence is a **pointer rather than a complete rule** — it is defined per
cycle and says nothing about how thirty cycle-sets combine into a month, which
is exactly the gap ADR 0075 filled. But it carries two filters ADR 0075's answer
does not.

**The duty filter was already resolved.** It was put to the owner as an option
and declined, so ADR 0075 supersedes version seven's sentence on it. The
practical effect is small: a seat that met no cycle has a monthly figure of zero
and can win only in a month where every candidate is at zero, which the
constitution's "whatever that figure is" contemplates outright.

**The accumulation cap was not resolved**, because it was never surfaced. Under
version seven's sentence a seat at the thirty-window cap is out of the candidate
set even holding the month's top uptime; under ADR 0075's answer as written it
competes and wins. That is a material difference in an ordinary month.

It was genuinely open rather than merely unstated.
[ADR 0035](0035-founder-answers-on-payout-the-cap-and-hub-recovery.md) decided
that a cycle a seat cannot collect because it is at the accumulation limit "is
treated exactly as a cycle it failed, so the day's generation goes to the best
performers and the capped seat is not one of them" — a rule about the **daily
generation** and about mint permissions. Whether it also governs a **monthly
pool payout** is not decided by it, and reading it either way chooses a
beneficiary rather than deducing one. So it was asked.

## Decision

**The monthly unreferred pool's candidate set is every seat in scope at any point
in the month. There is no duty gate and no accumulation-cap filter.** A seat at
the cap competes and can win.

The owner's reasoning, and the reason this is not in tension with ADR 0035: **the
cap exists to stop unminted permissions piling up, and a monthly pool payout is a
new claim the seat has never been offered** rather than one it declined to
collect. ADR 0035's rule is about generation a seat could have taken and did not;
it does not reach value the seat performed for and has not yet been offered. The
reason the daily rule gives therefore does not carry to the monthly one.

**Rejected: keeping the cap filter as version seven states it.** It would keep
one eligible-set rule across the daily reallocation, the recovery pool and the
monthly pool, so nothing would need correcting and no implementation would carry
two candidate rules. It was rejected because it lets the best-performing machine
of a month be paid nothing for it purely for not having minted, which inverts
what the pool is for.

**Rejected: the cap filter with a carry when it empties the candidate set.** It
would keep version seven intact and never strand value, and it carries the same
fairness objection while firing the carry in ordinary months rather than only at
the end of the distribution, where ADR 0075 intended it.

## Consequences

**The monthly candidate set is now complete and the payout slice is unblocked.**
It is: every seat whose 731-cycle span overlapped the month, ranked on the uptime
it accumulated during that month, ties sharing equally, no minimum, no duty gate,
no cap. Its remaining decisions are specification work the constitution names
outright.

**Nothing executable changes.** Both affected sentences are forward references to
a payout neither document implements. No transition, state entry, encoding,
result code, vector, digest, root, or kernel behaviour is touched, and no
accepted vector file can depend on a monthly payout that does not exist.

**Version seven's daily rules are unchanged and remain correct**, including the
accumulation cap in the per-cycle eligible set, which is ADR 0035's and is
untouched here. The correction is only to the clause that points that set at the
monthly pool. It is recorded as a note on the accepted document rather than as a
rewrite, because the rule the document states and implements did not change.

**ADR 0049 carries the same forward reference** — "these *compete* for the daily
reallocation, the recovery pool, and the monthly unreferred pool" — with the duty
filter and, notably, **without** the cap. So ADR 0049 was already consistent with
this decision on the cap and is superseded only on the duty gate. The cap entered
the monthly clause in version seven's restatement rather than in the decision
version seven implements, which is worth recording: **a restatement acquired a
filter the decision it restated did not have**, and it went unnoticed for two
weeks because nothing executes the clause.

**The lesson generalises and is the reason this ADR exists rather than a quiet
edit.** A forward reference in an accepted document is not checked by any test,
because there is nothing to test until the thing it refers to is built. When the
slice that builds it finally starts, the reference is the first thing it reads
and the last thing anyone verified. Reading the accepted contracts *before*
asking the founder-decision questions, rather than after, would have put all
three questions in one batch instead of two.
