# Unreferred pool payout v1

The Founder Constitution routes an unreferred seat's referral allocation — 34.2
units for each of its 731 cycles — to the **unreferred performance pool**, and
pays that pool to the best-performing Founder Seat of the month.

**The accrual half has worked since `economy-transition-v3`.** Step 8 of block
execution credits the referral leg to the seat's recorded referrer when it has
one and to the pool otherwise, version six gave the pool a state entry, and
version seven's genesis writes it. **Nothing has ever taken value out of it.**

This specification is the payout: who competes, on what figure, what each winner
receives, what happens to the part that does not divide, and at which height it
all executes.

It is the second half of what
[`calendar-v1`](calendar-v1.md) was written for. It consumes that
specification's month and its central argument — that a period is final only at
the first recognisable point after it, because its last member cannot be
recognised while it is happening — and applies that argument to the sequence in
which this rule's inputs actually arrive, which is **not** the sequence of
heights. Why it is not, and what it costs to get that wrong, is under
"When the payout executes".

## Scope

This specification defines a ranking and an arithmetic over quantities a ledger
holds. It measures nothing, encodes nothing, and moves no octets.

In scope:

- the monthly candidate set, stated once rather than reassembled from three
  decision records;
- the ranking figure, and **which month a cycle's uptime counts toward**;
- the ranking, the exact-tie split, each winner's share, and the remainder;
- the carry when a month has no candidate, and the proof that the case is
  unreachable while any seat is activated;
- the point the payout executes at, why it is not the month's opening block,
  and its order against the accrual step;
- the named quantities a binding ledger version must carry;
- the resource bounds the rule imposes at full seat capacity; and
- when a referral benefit begins for a seat that is purchased and never
  activated, which the Founder Constitution names as specification work.

Explicitly not in scope:

- **entry kinds, keys, octet layouts, transaction kinds, result codes, and block
  execution.** Those belong to the ledger version that binds this specification,
  which is the posture [`cycle-boundary-v1`](cycle-boundary-v1.md),
  [`uptime-measurement-v1`](uptime-measurement-v1.md) and
  [`calendar-v1`](calendar-v1.md) all took. This document names the quantities
  that version must carry and leaves their representation to it.
- **the month.** That is `calendar-v1`: the consensus timestamp, its
  monotonicity rule and tolerance, the derivation to a calendar month, and the
  month-opening predicate. Nothing here re-derives a date.
- **the measurement.** That is `uptime-measurement-v1` and
  `economy-transition-v8`: the slot grid, the challenge, the dispute window, and
  the credit rule. This document reads `uptime_seconds` and issues no challenge.
- **the daily reallocation and the recovery pool.** Those are
  `economy-transition-v7`'s and are untouched, including the accumulation cap in
  its per-cycle eligible set, which is
  [ADR 0035](../decisions/0035-founder-answers-on-payout-the-cap-and-hub-recovery.md)'s.
- **how a winner spends what it is owed.** The claim this rule creates is minted
  by the same machinery the referral balance uses, which the binding version
  supplies.

No accepted artifact, vector, digest, C++ source, genesis file, or devnet
behaviour is changed by this specification.

## Determinism rules

Every quantity is a non-negative integer and every operation is integer
addition, subtraction, multiplication, comparison, or truncating division. There
is no floating point and no wall clock: the month arrives as `calendar-v1`'s
derivation from an agreed header field, and the uptime arrives as
`economy-transition-v8`'s derivation from agreed state.

Ties are resolved by **equality of the figure**, never by seat order, arrival
order, or any other tiebreak. A tie is a shared win and not a contest to settle.

## Bindings

This specification holds no second copy of any founder-directed value.

**The month, its height span, and the height at which it becomes final** are
[`calendar-v1`](calendar-v1.md)'s.

**`uptime_seconds(seat, window)`, `in_scope`, `in_span`, and
`first_cycle_window`** are `economy-transition-v8`'s and
[`cycle-boundary-v1`](cycle-boundary-v1.md)'s, read rather than restated.

**The referral benefit of 34.2 units per cycle, the channel it belongs to, and
its cap** are [`founder-economy-manifest-v3`](founder-economy-manifest-v3.md)'s.

## Constants

| Name | Value | Source |
| --- | ---: | --- |
| `CYCLE_BLOCKS` | 28,800 | `cycle-boundary-v1` |
| `SLOT_SECONDS` | 3,600 | `uptime-measurement-v1` |
| `SLOTS_PER_WINDOW` | 24 | `uptime-measurement-v1` |
| `ASSIGNMENT_LAG_WINDOWS` | 2 | `economy-transition-v7` |
| `ISSUANCE_CYCLES_PER_SEAT` | 731 | Founder Constitution |
| `FOUNDER_SEAT_CAPACITY` | 100,000 | Founder Constitution |
| `WINDOW_UPTIME_SECONDS_MAX` | 86,400 | derived |
| `MAX_SEAT_SPAN_MONTHS` | 25 | `calendar-v1` |

`WINDOW_UPTIME_SECONDS_MAX` is `SLOTS_PER_WINDOW * SLOT_SECONDS`, the most one
window can contribute. The model requires it to equal `cycle-boundary-v1`'s
`CYCLE_TARGET_SECONDS` rather than holding a second opinion about how long a day
is.

## The candidate set

**Every seat in scope at any point in the month competes.** There is no minimum
figure, no duty gate, and no accumulation-cap filter.

```text
candidates(m) = { seat : in_scope(seat, w) for some window w attributed to m }
```

Each of the three parts is founder-directed and each is recorded, because this
set was assembled from three decisions and reassembling it from three documents
is how a later reader gets it wrong:

- **in scope at any point in the month**, rather than at the month's end.
  [ADR 0075](../decisions/0075-founder-answers-on-the-monthly-pool-candidate-set-and-carry.md).
  A seat that ran 29 of 30 days and whose 731-cycle span ended on the 30th is
  exactly the machine the pool exists to reward, so membership is a **range
  overlap** rather than a snapshot at either edge.
- **no duty gate.** ADR 0075. A seat that met no cycle has a figure of zero and
  wins only where every candidate is at zero, which the constitution's "whatever
  that figure is" contemplates outright.
- **no accumulation-cap filter.**
  [ADR 0076](../decisions/0076-the-monthly-pool-ranks-every-in-scope-seat.md). A
  seat at the thirty-window cap competes and can win: the cap exists to stop
  unminted permissions piling up, and this payout is a claim the seat has never
  been offered rather than one it declined to collect, so ADR 0035's daily rule
  does not reach it.

**`in_scope` is permanent.** `economy-transition-v8` defines it as
`seat is activated and first_cycle_window(seat) <= w`, with no upper bound, and
ADR 0049's rule 3 is why: the 731 cycles bound the distribution and not the
machine's operating life. A seat therefore joins the candidate set at its first
cycle and never leaves it. That single fact is what makes the carry below
unreachable, and it is proved rather than assumed.

**It also makes the candidate set free to derive, and that is worth stating
because the obvious implementation is much more expensive.** Since `in_scope` is
monotone in the window, a seat is a candidate for month `m` exactly when
`first_cycle_window(seat) <= last window attributed to m`, which the seat table
already answers. **A binding version therefore does not have to write a
zero-valued accumulator for every in-scope seat** in order for a zero-uptime seat
to be a candidate: it accumulates only nonzero figures, and a candidate with no
accumulator has a figure of zero by absence. At capacity that is the difference
between writing 100,000 entries every window and writing only as many as ran.

## The ranking figure

A candidate's figure for a month is the uptime it accumulated in that month:

```text
figure(seat, m) = sum over windows w attributed to m of uptime_seconds(seat, w)
```

`uptime_seconds` is `economy-transition-v8`'s, which is
`credited_slots * SLOT_SECONDS` over the credited slots not voided by a dispute.
Nothing here re-measures it, and a window in which a seat is not in scope
contributes nothing rather than zero — the seat is simply not among that
window's entries.

### Which month a window is attributed to

**A window is attributed to the month containing its first height**, and its
whole uptime goes to that month.

```text
month_of_window(w) = month_of_height(w * CYCLE_BLOCKS)
```

A window is 28,800 heights, about a day at the commit target, so **one window a
month straddles a month boundary** and its uptime counts toward the month it
began in.

**Why the first height rather than the assignment height.** The natural
implementation reads the month from the block doing the work, and the assignment
runs `ASSIGNMENT_LAG_WINDOWS` windows late, so that reading would push about two
days of every month's uptime into the next month — a systematic distortion the
participant would feel every month. The founder answer is "the uptime it
accumulated **during that month**", so attribution follows when the uptime
happened. The cost is that a binding version must record the month a window
opened in, which is one small value per live window and at most three live at
once.

**Why the whole window rather than a per-slot split.** Splitting a straddling
window at the month's first height would cut the attribution error from about a
day to about an hour, at the cost of a materially more complex rule: the split
point is a timestamp boundary and slots are height ranges, so the rule would
have to carry the opening block's height and divide each seat's credited bitmap
against it. It was rejected because **the straddle is common to every
candidate** — every seat sees the same window boundary — so it shifts each
candidate by its own uptime in one shared window rather than favouring anyone
systematically, and a month holds about thirty windows.

**Rejected: attributing by the window's last height.** Symmetric with the first
and no better, and it puts a window that begins on the 1st into the previous
month, which reads worse to a participant than the converse.

## The winners and the share

```text
best(m)        = max over candidates(m) of figure(seat, m)
winners(m)     = { seat in candidates(m) : figure(seat, m) == best(m) }
payable(m)     = the pool's undistributed balance when month m closes
share(m)       = payable(m) / |winners(m)|            (truncating)
remainder(m)   = payable(m) - |winners(m)| * share(m)
```

**One winner unless there is an exact tie for first**, which the constitution
states and which is the same shape as the daily failed-cycle reallocation.
Equality is over the integer figure, so a tie is exact or it is not a tie.

**`payable(m)` is the pool's undistributed balance and not "the accrual of month
m".** In an ordinary month the two are the same. They differ in exactly two
cases, and both are already decided: a month that did not pay leaves its accrual
in the balance, and a month whose share did not divide leaves a remainder in it.
Carrying the balance rather than a per-month accrual figure is what makes "only
one month's accrual is distributed per month" true without the pool having to
remember a figure per month.

### The remainder

**The remainder stays in the pool** and is distributed with the next month that
pays.

The Founder Constitution names the pool's remainder rule as specification work
rather than a founder decision, and this is the rule that needs no second
mechanism: the pool already carries an undistributed balance for the
zero-candidate case, so a remainder is the same quantity arriving for a
different reason. **A remainder is at most `|winners(m)| - 1` atomic units**, and
in the overwhelmingly common single-winner month it is exactly zero, because
`payable / 1` divides.

**Rejected: routing the remainder to the recovery pool**, which is what
`economy-transition-v7` does with the *daily* reallocation's remainder. It would
move a monthly accrual into a daily mechanism, so a day's best performer would
collect value a month's ranking was meant to award.

**Rejected: awarding the remainder to the lowest seat identifier among the
winners.** It divides exactly and it breaks a tie the constitution says is not to
be broken, by a quantity that has nothing to do with performance.

## When a month has no candidate

**A month with no candidate does not pay.** `payable` is untouched and the
earliest subsequent month that has a candidate takes it entirely.
[ADR 0075](../decisions/0075-founder-answers-on-the-monthly-pool-candidate-set-and-carry.md)
decided it, and it is ADR 0049's recovery-pool shape applied to the monthly pool
rather than a second mechanism invented for it.

### The case is unreachable while any seat is activated, and that is a theorem

```text
accrual in month m > 0
  => some seat was in span in some window attributed to m
  => that seat was in scope in that window        (in_span implies in_scope)
  => candidates(m) is non-empty
```

The middle step is `economy-transition-v8`'s definition — `in_span(seat, w)` is
`in_scope(seat, w) and w - first_cycle_window(seat) < 731` — so in-span is a
subset of in-scope by construction rather than by coincidence.

**Therefore a month with accrual always has a candidate.** The zero-candidate
case is reachable only before the first activation, when the pool is empty, so
the carry never fires on a chain that has sold and activated one seat. It is a
safety net rather than an operational path.

**The theorem is stated because the alternative is worse than useless.** If a
later change made in-scope expire — a retirement rule, a per-seat sunset — the
carry would become live and a month's accrual could sit undistributed
indefinitely. The model checks the implication over every recorded scenario
rather than asserting it, so such a change fails a vector instead of quietly
turning a safety net into a policy.

**The one case ADR 0075 left open is therefore not reachable either.** It asked
what becomes of a final accrual at the very end of the distribution with no
later month that has a candidate. Since a candidate exists in every month after
the first activation, the payout for the last month with accrual happens in the
month after it, like any other. **It is recorded as closed by derivation rather
than left open**, and the derivation is the same theorem.

## When the payout executes

**A month is paid in the block that assigns the first window of a later month.**

```text
pay when   month_of_window(due) > month_of_window(previous assigned window)
closing    every month index in [month_of_window(previous), month_of_window(due))
```

**Not in the block that opens the month.** That was this specification's first
rule and it is wrong, and the reason is worth recording because it is invisible
until the bound is checked. `calendar-v1` establishes that the block opening a
month is the only point at which the *month* is final, and that is true of the
month. It is not true of the month's **figures**: a window is assigned
`ASSIGNMENT_LAG_WINDOWS` windows after it opens, so the last two windows of a
month are still unassigned when the next month begins. Paying at the opening
block would rank every seat on a month with its last two days missing, every
month, silently.

**The window-assignment sequence is the right sequence and it has the same
shape.** `month_of_window(w)` is non-decreasing in `w`, because
`month_of_height` is non-decreasing in height and `w * CYCLE_BLOCKS` increases
with `w`. So the assigned windows' months form a non-decreasing sequence, and
the first assigned window of a later month is exactly the point at which every
earlier month's figures are complete — the same "only recognisable point"
argument `calendar-v1` makes, applied to the sequence in which the figures
actually arrive.

The prologue runs only at window-opening heights, so the payout is evaluated at
most once a window and fires about once a month.

**One assignment may close several months**, for the same reason `calendar-v1`
gives: a chain halted across a boundary leaves months with no windows attributed
to them at all. The payout therefore runs once per closed index **in ascending
order**, and the order is normative — a carry from an earlier month must reach a
later one, and descending order would pay the later month first and strand the
earlier balance for another month.

A month with no windows has no candidates and no accrual, so its pass is a no-op
that leaves `payable` exactly as it found it.

### The payout runs before the assigned window's accrual

In that block, **the payout precedes the referral accrual for the window being
assigned**.

This is forced rather than chosen. The window that triggers the payout belongs
to the **new** month, so its accrual belongs to the new month; letting it land
first would pay a closing month one window of its successor's accrual, and "only
one month's accrual is distributed per month" would be false by a day every
month.

It also makes `payable` exactly right at the moment it is read. Every window
assigned since the previous payout belongs to the closing month, so the balance
standing before this window's accrual is that month's accrual plus whatever
earlier months carried — which is precisely what the closing month is owed.

It is stated for the same reason `economy-transition-v7` states that its step 6
reads the pool before step 7 writes it: **two implementations can each read a
sentence about a pool a different way**, and the ordering is invisible in every
test that does not put an accrual and a payout in the same block.

## What a winner receives

**A claim, not a credit.** Each winner's `share(m)` is recorded as an amount that
winner may mint, in the same shape the referral balance already uses.

This is a deduction rather than a choice.
[ADR 0041](../decisions/0041-the-seat-is-tied-to-the-identity-not-an-address.md)
ties a Founder Seat to the owner's HUB verified data rather than to any address,
so **there is no canonical address a payout could credit**; and
[ADR 0035](../decisions/0035-founder-answers-on-payout-the-cap-and-hub-recovery.md)
decided that minted value lands on the address that signed the mint. A rule that
credited an address would have to invent one, and a rule that credits an identity
is the referral balance's existing shape.

**The pool's `minted` total rises when a winner mints, not when it wins.** The
pool therefore needs three quantities rather than two, named here and encoded by
the binding version:

| Quantity | Meaning |
| --- | --- |
| `accrued` | every unit the pool has ever received from unreferred seats |
| `payable` | the part not yet assigned to any winner |
| `minted` | the part a winner has actually taken |

with the identity, at every height:

```text
accrued = payable + (assigned to winners, whether minted or not)
minted <= accrued - payable
```

**The first identity is this document's and the second is the binding
version's.** The first holds over the rule defined here and the model checks it
after every step: every unit the pool has received is either still undistributed
or is owed to a named winner, and none is anywhere else. The second is a
statement about minting, which is out of scope above, so it is named for
completeness and left to the version that implements a mint.

**The binding version must also carry**, per month that is open or awaiting
payment: each in-scope seat's accumulated `figure`, and the month a live window
opened in. Both are stated as quantities rather than entries, because their
encoding is that version's.

## When a referral benefit begins

The Founder Constitution names this as specification work: *when a referral
benefit begins for a seat that is purchased but never activated, since a seat's
731 cycles start at its first activation and an unactivated seat has no cycles to
count.*

**It begins with the seat's first cycle, and a seat that is never activated never
accrues anything.**

This is a derivation and not a choice. `cycle-boundary-v1` fixes
`first_cycle_window(a) = window_of_height(a) + 1` from the activation height `a`,
and the referral leg accrues **per contributing cycle**. A seat with no
activation height has no first cycle, is in no window's contributing set, and
generates no leg to route — to a referrer or to the pool. The question reads as
though an unactivated seat might accrue to *somewhere*; it accrues nowhere,
because there is nothing to accrue.

**The consequence for the pool is worth stating.** An unreferred seat that is
bought and never switched on contributes **nothing** to the unreferred pool. The
channel's exact consumption — 100,000 seats x 731 cycles x 34.2 — is the
consumption of *activated* seats' cycles, and a chain where seats go unactivated
issues less than the cap rather than issuing it elsewhere. That is the same
property the base permission already has and it is not a leak.

## Resource cost

| Quantity | Bound at capacity | Note |
| --- | ---: | --- |
| Accumulated figures | 100,000 | only for seats that ran |
| Months accumulating at once | 1 | window assignment is ordered |
| Live window months | 3 | the open window and the two in the lag |
| Winner claims per month | 100,000 | only in an exact tie across every seat |
| Seat span in months | 25 | `calendar-v1`, nominal |

**The payout walks every candidate once per month.** At capacity that is one
pass to find the maximum and one to collect the winners, once a month rather
than once a block. It is cheaper by three orders of magnitude than the per-block
costs `economy-transition-v8` already pays, and it is recorded here so a later
session prices it rather than rediscovering it.

**Exactly one month accumulates at a time**, and this document said two until
the model measured it. The reasoning behind the wrong figure was about the
*height* sequence: assignment lags, so a month's last windows are assigned after
the next month has begun on the wall, and it looked as though two months must
therefore be open together.

They are not, because **the payout is driven by the window sequence and
`month_of_window` is monotone in the window index**. Every window of a month is
therefore assigned before any window of the next, so a month's figures are
complete and deleted before its successor accumulates anything. The lag moves
*when* a settlement happens; it does not interleave two months' figures.

The vector records the largest number of months ever holding an open figure
during the recorded run, measured by replaying it, rather than asserting the
bound. That is why the figure is right.

**The accumulated figures are deleted when their month is paid**, which is the
single largest state change this rule makes — up to 100,000 entries in one
block at capacity, though only for seats that actually ran. A binding version
may spread that deletion only if doing so changes no accepted state.

Because only one month accumulates, the peak is one month's figures rather than
two, so the rule's whole standing state is bounded by the seats that ran in the
current month plus the claims not yet minted.

### The figure is bounded in practice and guarded in principle

At the commit target a month holds about thirty-one windows, so a figure is
about 2,678,400 seconds and fits in a `u32` three decimal orders clear.

**That is a nominal bound and not an invariant, and the distinction matters.**
A window is 28,800 *heights* and a month is a span of *timestamps*, so how many
windows fall in a month depends on how fast blocks are produced, which no
consensus rule fixes — `calendar-v1` bounds the timestamp against civil time but
nothing bounds the block rate from above. A chain producing blocks far faster
than the target puts proportionally more windows in a month.

So the figure is a `u64` and its accumulation is a **checked** addition rather
than an assumed-safe one. Overflow would need on the order of `2 x 10^14`
maximal windows in a single month, which is not reachable by any chain that also
satisfies `calendar-v1`'s tolerance, but the guard is present rather than
argued: **a bound that depends on an operational rate is not a bound**, and this
document would rather carry one check than a paragraph explaining why the check
is unnecessary.

## Vectors

`test-vectors/unreferred-pool-payout-v1.txt` records the rule. Every value is
reached twice — once by `tools/unreferred-pool-payout-vectors/expected.py`, which
imports nothing from `simulation/`, and once by a live model run — and the
recorded cases are chosen where an error is visible:

- a single winner, and an exact tie of two and of three, with the share and the
  remainder at each;
- a month whose share does not divide, and the remainder arriving in the next
  month's payout;
- a month with candidates and no accrual, which pays nothing and is not an error;
- a month with no candidates at all, which carries, and the accrual theorem
  proved over every scenario rather than asserted;
- a window that straddles a month boundary, attributed to the month it began in,
  with the figure that a last-height attribution would have produced recorded
  beside it so the two rules are distinguishable;
- a halt that closes three months in one assignment, processed in ascending
  order, with the carry reaching the third;
- a month whose last windows are assigned after the next month has begun, paying
  on the complete figure, with the figure a month-opening-block trigger would
  have ranked on recorded beside it so the two triggers are distinguishable;
- the payout and the accrual in the same block, in both orders, so the stated
  order is normative rather than decorative;
- a seat that joins the candidate set mid-month and one whose span ends
  mid-month, both of which compete;
- a seat at the accumulation cap winning a month; and
- the figure bound at a full month of maximal windows.
