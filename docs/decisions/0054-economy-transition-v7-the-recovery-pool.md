# ADR 0054: Version seven encodes the recovery pool

- Status: Accepted
- Date: 2026-08-19

## Context

[ADR 0049](0049-the-recovery-pool-and-permanent-best-performer-ranking.md)
deletes the per-channel carry and replaces it with a recovery pool, so that the
node distribution assigns 100% of its permissions rather than leaking two
silent remainders into a term nothing ever releases.
[`first-goal.md`](../project/first-goal.md) requirement 9 now states the revised
rule and the Founder Constitution carries it.

That decision settles **what the chain must do**. It leaves four things a
contract has to settle before anything can implement it: where the pool lives in
state, how a mint learns what a cycle owed it, which conservation identity
replaces the carry identity, and whether the change is an edit or a version.

The last one is not open. The pool changes the state key space, the cycle
assignment record, and the per-channel identity, and the repository's rule is
that a changed transition is a new version rather than an edit to an accepted
one. So this is `economy-transition-v7`, and
[`economy-transition-v6`](../specifications/economy-transition-v6.md) is
retained unedited as the record of what was verified.

Two premises of ADR 0049 were checked against the code before this contract was
written, and one of them is wrong for the accepted model. That check is recorded
here because acting on the stated premise would have produced a rewrite the
repository did not need.

## Decision

### 1. The pool is one entry carrying five legs, and entry kind 7 is retired

Entry kind 7 held ten `carry` entries, one per channel, of which only the five
Founder Node legs were ever nonzero. Version seven removes it and **retires the
number permanently**, joining 9 and 11. Assigning a new meaning to a number a
reader associates with an accepted contract is the cheapest possible way to
create an auditing mistake, and the rule that produced 9 and 11 applies here
unchanged.

Entry kind 17 is the recovery pool: key `u8(17)`, one octet, value five `u64`
legs in channel order 0 through 4, forty octets.

**Per-channel is derived rather than chosen.** The five legs have five different
beneficiaries — the Founder operator's own escrow and four typed custody kinds —
and each channel carries its own cap and its own conservation identity. A single
scalar could not say which channel a recovered unit belongs to, so it could not
be paid out without inventing a split. The ten entries collapse to one because
one entry can hold five fields; the five fields do not collapse further.

### 2. The cycle assignment record records what that cycle absorbed

A mint walks at most thirty windows and reads one record per window. The pool's
balance at any window is a function of **every** earlier cycle, so a mint that
had to derive it would replay the whole assignment history, which is unbounded
and is exactly the implicit cost the settlement's other counts exist to avoid.

So the record gains five `u64` fields — `pool_absorbed_atomic`, per channel —
placed after `bitmap_bits` and before the two bitmaps, which keeps every
fixed-width field contiguous ahead of the variable-length tail. The record's
fixed part goes from 24 octets to 64.

**The absorbed amount is recorded rather than the per-winner share.** Both make
the mint a bounded read. The absorbed amount additionally makes the pool's own
arithmetic checkable from the record alone: the residual returned to the pool is
`absorbed - winner_count * (absorbed // winner_count)`, which a share alone
cannot express. It is also the same shape as the reallocation, which records
`reallocated_count` and `winner_count` and derives the share, so one reader's
habit covers both.

### 3. The identity loses its third term and gains a second identity

Version six states, per Founder Node channel:

```text
issued(c) + outstanding(c) + carry(c) = assigned_cycle_permissions * leg(c)
```

with the carried remainder moved **out of** `outstanding`. Version seven states:

```text
issued(c) + outstanding(c) = assigned_cycle_permissions * leg(c)
```

with nothing moved out. The pool is a named portion of `outstanding` rather than
a term beside it, which is the same shape the referral channel already uses for
the unreferred pool, and it is what ADR 0049 means by the identity losing its
third term.

That alone would not catch a stranded unit, because `outstanding` is a single
number and a defect that lost a claim would simply leave a larger one. So
version seven adds the identity that names both halves:

```text
outstanding(c) = claimable(c) + recovery_pool(c)
```

where `claimable(c)` is what the recorded assignment records still owe every
seat from its own mark forward. **This is the statement that 100% is assigned**,
and it is an equality rather than a bound, so a defect that created value
without a claimant and a defect that destroyed a claim both fail it.

`claimable` is exact rather than approximate because the accumulation cap is
applied at assignment: a seat over the cap accrues no bit and wins no bit, so no
bit can exist outside the thirty windows a mint reaches, and a mark that
advances past an uncollected bit is unreachable.

### 4. The pool is read before the cycle's own dust is added

A cycle with any winner takes the pool's balance **as it stood before this
cycle's assignment**. Its own reallocation dust, and the residual from dividing
the pool it just took, both land in the pool for the cycle after. That is ADR
0049's "its own dust simply returns to the pool for the cycle after", stated as
an order rather than as a remark, because the alternative reading — absorb after
contributing — changes what a winner receives and would be a silent divergence
between two implementations that both read the ADR.

A cycle with no winner absorbs nothing and leaves the pool untouched.

**Having any winner is the trigger, not having reallocated anything.** A cycle
in which every in-span seat accrued has a winner set and a zero reallocation
count, and it still takes the pool, because the pool is value looking for the
best performer rather than a share of this cycle's reallocation.

### 5. ADR 0049's premise about the winner set is wrong for the accepted model,
and the slice is smaller because of it

ADR 0049 states that "today `derive_winner_set` considers only seats inside
their own 731 cycles, so a machine past its distribution cannot win anything".
In `simulation/economy_transition_v3/settlement.py` that is not what
`derive_assignment` does: it passes **every** in-scope seat to
`derive_winner_set`, filtered only by met-the-cycle and under-the-cap. `in_span`
appears three times in that module and none of them is the winner set — it gates
`accrued`, `assigned`, and the referral accrual. The same is true of
`founder-economy-simulator-v3`, whose in-scope rule has "deliberately no upper
bound".

So the contributing set and the eligible set are **already two different sets**,
and the eligible one already includes machines past their own distribution.
Version seven therefore **states and guards** rules 2 and 3 rather than
implementing them: the specification names both sets, and a vector fails if an
`in_span` filter is ever added to the winner set. Rewriting a correct derivation
on a stated premise, without first reproducing the defect it describes, is how a
regression enters an accepted contract.

The rest of ADR 0049's premise holds exactly: `split_permission(0)` does put the
entire base permission into the carry, every leg's remainder does accumulate
there, and nothing anywhere releases either.

### 6. The chain identity, root, genesis, and receipt re-version; the derivations
do not

`protocol-stack:v7:chain-id`, `protocol-stack:v7:state-root`, and the three
`protocol-stack:v7:economy-*` tree labels are new, and the genesis schema
version, the state-root schema version, and the receipt version are `7`. So a
version-seven root is never equal to a root of any of the six predecessors, and
the six non-collisions are required separately.

**Every other label is retained at the version that accepted it.** The account
derivation stays `protocol-stack:v1:account`, the escrow derivation stays
`protocol-stack:v6:escrow`, and the six HUB messages keep their version-six
labels, because none of those artifacts changed and a label names the artifact
rather than the contract that reads it. Version six retains version one's
account label for the same reason.

**A version-six signature cannot be replayed onto a version-seven chain
regardless**, because every signed message binds `chain_id` and the chain
identity is derived over the genesis bytes, whose schema version and label both
differ. That is a derived property, and it is recorded as a vector rather than
asserted.

### 7. The contract binds `founder-economy-manifest-v3`

The manifest digest bound into genesis becomes version three's, which
[ADR 0053](0053-founder-economy-manifest-v3-the-channel-rename.md) accepted. The
only difference it carries is channel 9's identifier, so no cap, leg, subtotal,
bound, or total moves; the vectors record the digest change and the unchanged
figures together, so "the binding moved and the economy did not" is checkable
rather than described.

## Alternatives rejected

**Keep the carry and release it at the end of issuance.** ADR 0049 rejected it
on its own ground: there is no clean end once each machine has its own
activation date. It is repeated here only to record that the contract did not
reopen it.

**Ten pool entries, one per channel, mirroring the carry.** It changes nothing
about the arithmetic and keeps a shape whose ten-ness was already
misleading — five of the ten were structurally always zero. One entry with five
named legs says what is true.

**Derive the pool balance at mint time from the assignment history.** Rejected in
decision 2: unbounded work inside a transition, and two implementations would
disagree about where to stop.

**Give the pool its own payout path with its own ranking and tie rules.**
Rejected by ADR 0049 and not reopened. The winner set already splits an exact
tie equally and the pool's own residual returns to it, so a second path would be
a second place for the same rules to drift.

**Edit `economy-transition-v6` in place.** The state key space, the assignment
record, and the conservation identity all move. An accepted contract with
recorded vectors is the record of what was verified; editing it would make that
record false.

## Consequences

**Requirement 12 gains one entry, loses ten, and grows every assignment record.**
Ten `carry` entries at 10 octets each become one 41-octet pool entry, and each
cycle assignment record grows by 40 octets. At the 100,000-seat bound a record
already carries two 12,500-octet bitmaps, so the growth is under two parts in a
thousand of the entry that dominates the bound.

**Genesis writes fourteen entries where version six wrote twenty-three.**

**The C++ kernel is unaffected by this slice and targeted by the next.** The
version-six codec and its ten executing transitions compile a contract this one
supersedes in the settlement only; the four seat transitions the kernel refuses
are exactly the ones whose contract just changed, which is why they were left
refused rather than implemented against version six.

**One property is stated and not reachable.** ADR 0049's pool lifecycle — a pool
that can receive no further inflow is marked consumed and then archived — has no
version-seven encoding, because the recovery pool can receive inflow for as long
as any cycle is assigned and therefore never reaches that state. It is recorded
as a property of later pools rather than given an unreachable state bit.

## Compatibility and independent review

`economy-transition-v6` and every predecessor, their vectors, their verifiers,
and the version-six C++ codec are retained unedited. The version-seven model
imports version six for everything it does not change, so a constant that moved
without a vector reaching it is caught by a package-level carryover check rather
than left to reading.

Two claims need review.

**That `claimable(c)` is exact.** It rests on the argument that no accrued or
winner bit can exist outside the thirty windows a mint reaches, which rests in
turn on the accumulation cap being applied at assignment against the same mark
the walk uses. The argument is stated in the specification and checked by
vectors over a schedule that crosses the cap in both directions; it has not been
checked by an implementation other than this repository's.

**That reading the pool before adding the cycle's own dust is the intended
order.** It is the reading ADR 0049's own sentence gives, and the alternative is
self-consistent. If the owner intended the other order, the difference is one
cycle of latency on dust and is a specification edit rather than a redesign.
