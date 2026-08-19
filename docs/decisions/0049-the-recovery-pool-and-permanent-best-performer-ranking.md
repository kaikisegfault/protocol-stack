# ADR 0049: The recovery pool replaces the carry, and ranking is permanent

- Status: Accepted
- Date: 2026-08-19

## Context

The owner set a requirement on 2026-08-19 that the node distribution had never
been measured against: **the system must assign 100% of its mint permissions.
Nothing may be missed.** Whether a founder then mints is their business — a
permission that is never collected is a choice — but a permission that is never
*created*, or created and then stranded, is a defect.

Measured against that requirement the model leaks in three places, all silently:

1. **Zero-winner cycles.** `split_permission(0)` puts the entire base permission
   into `carry`.
2. **Indivisible remainders.** Any leg that does not divide evenly among the
   winners leaves dust in `carry`.
3. **Unsold seats.** Permissions are created only for seats that are in scope,
   and in scope is derived from an activation height, so a seat never sold
   creates none of its 731 permissions.

And **`carry` is only ever added to.** No transition anywhere releases it. The
first two therefore accumulate permanently: value the manifest promised, that
exists in no channel's issued or outstanding total, and that no participant can
ever reach.

The owner excluded the third from scope — the seats are expected to sell — and
directed a mechanism for the first two.

A second, independent question turned out to be entangled with it. Today
`derive_winner_set` considers only seats **inside their own 731 cycles**, so a
machine past its distribution cannot win anything. That makes the recovery pool
strandable in principle, and it also contradicts what the 731 cycles are for.

## Decision

### 1. `carry` is deleted from state and replaced by a recovery pool

A zero-winner cycle contributes its **whole base permission** to the pool. An
indivisible remainder contributes its **dust**. The pool accumulates across as
many cycles as it needs to.

**The earliest subsequent cycle that has any winner takes 100% of it**, on top of
that cycle's own reallocation, distributed to that cycle's winner set.

This reuses the machinery that already exists rather than adding a second payout
path: the winner set already handles an exact tie by splitting equally, so the
pool needs no tie rule, no ranking rule, and no remainder rule of its own — its
own dust simply returns to the pool for the cycle after.

**Rejected: keep the carry and release it at the end of issuance.** It is a
smaller change and it is wrong in the way that matters. 100% would be true only
at the very end, every intermediate state would sit below the cap, and there is
no clean "end" to release at once each machine has its own activation date.

### 2. The contributing set and the eligible set are different sets

- **Contributing set** — seats inside their own 731 cycles. These *generate* base
  permissions.
- **Eligible set** — every operational seat that met the duty threshold for the
  cycle, in span or not. These *compete* for the daily reallocation, the recovery
  pool, and the monthly unreferred pool.

Today these are one set, and separating them is what makes ranking permanent.

### 3. The 731 cycles bound the native asset distribution and nothing else

A Founder Machine's operating life is not 731 cycles. **731 cycles is the window
of the native asset distribution to escrows, and the founders' initial
incentive — nothing more.** It exists so founders have income during the roughly
two years before the ecosystem generates real revenue; a founder's enduring
incentive is the seat itself, which is a stakeholder's share of the ecosystem.

So a machine whose distribution has finished **keeps operating and keeps
competing**. It appears in the daily and monthly best-performer rankings, and it
can win any pool that still holds value. Since activation dates differ, machines
finish at different times and there is always a population still contributing.

**The best-performer mechanism never deprecates.** It is infrastructure that
later incentive programmes attach to, not an artifact of this distribution.

### 4. Pools have a lifecycle, and value is never deleted

A pool that has been fully consumed and can receive no further inflow is marked
**consumed** and then **archived**. It is not deleted: its history stays
queryable, and future programmes may rank against the same performance data.

## Consequences

**The recovery pool cannot strand.** Because ranking outlives every machine's
distribution window, and machines keep operating after theirs ends, there is
always a subsequent cycle with a winner for as long as anyone is running. An
earlier draft of this decision added a terminal rule that routed leftover value
into the final month's unreferred-pool distribution; the permanence rule makes it
unreachable and it is dropped.

**`carry` leaves the state layout, which is a contract change.** Entry kind 7 and
its ten entries disappear, the per-channel carry identity
`issued + outstanding + carry = assigned x leg` loses its third term, and the
recovery pool needs an entry of its own. That is a new economy contract version
and a new manifest, not an edit to `economy-transition-v6`.

**The settlement slice is rewritten before it is built.** `derive_winner_set`,
`split_permission`, `outstanding_delta`, and the in-scope derivation all change,
and the C++ settlement had not been started — which is why the timing was
fortunate rather than expensive.

**Requirement 12 gains an entry and loses ten.** Ten carry entries at 10 bytes go
away; one recovery pool entry replaces them.

**One thing this does not establish.** Assigning 100% of the permissions is not
the same as issuing 100% of the supply. A permission nobody collects is still
uncollected, and the verified-user channel already satisfies an inequality rather
than an equality for exactly that reason. This ADR closes the gap between what
the manifest promises and what the chain creates; it says nothing about what
participants choose to take.
