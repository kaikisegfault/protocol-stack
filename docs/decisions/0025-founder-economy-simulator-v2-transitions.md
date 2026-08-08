# ADR 0025: Founder Economy simulator v2 transitions

- Status: Accepted
- Date: 2026-08-08

## Context

[ADR 0023](0023-founder-decisions-activity-referrals-and-supply.md) recorded the
owner's 2026-08-07 decisions, and
[`founder-economy-manifest-v2.md`](../specifications/founder-economy-manifest-v2.md)
restated the economic contract they direct. That slice delivered a
specification, a manifest, a digest, vectors, and a strict loader. It executes
no transition.

The accepted M2 model in `simulation/founder_economy/` implements version one.
Its transition set is now wrong in shape, not only in parameters: the referral
is no longer a permission, the permission `kind` discriminator has one remaining
value, and two of its four research placeholders were replaced by rules the
Founder Constitution now states.

This ADR records the decisions taken to make version two executable. Under the
standing delegation these are engineering choices; none of them selects a
founder-reserved value. Where the Founder Constitution already decides
something, it is implemented as stated rather than re-litigated.

## Decision

### The uptime record is a measurement, and the model derives the verdict

`evaluate_base_permission` takes a `cycle_uptime_record` carrying
`{cycle_window, entries:[{seat_id, uptime_seconds}]}`. The model derives the
activity predicate and the winner set from it.

The alternatives considered were:

1. **Keep a supplied verdict under a new name** — replace `activity_result`
   with, say, `cycle_eligibility`, still carrying a boolean.
2. **Supply the winner list** — keep v1's allocation list and rename it.
3. **Supply measurements and derive everything** — the selected option.
4. **Defer the transition** — leave `evaluate_base_permission` unimplemented
   until the measurement pipeline exists.

Options 1 and 2 were rejected because the handoff and the Founder Constitution
both now fix the rule. The threshold, the fragmentable allowance, the boundary
resolution, the ranking, the tie rule, the winner restriction, and the remainder
rule are all decided; a fixture supplying the answer would discard decided
policy and would let the next slice mistake a fixture for a solved problem.
Option 4 was rejected because the rule being decided is exactly what makes the
transition implementable now, and deferring it would leave M3 with no executable
v2 model at all.

The distinction the selected option preserves is stated in the specification and
is enforced by the schema rather than by convention: a research placeholder
stands in for an undecided founder policy, and the uptime record stands in for a
decided rule whose measurement pipeline is unbuilt. The record therefore cannot
express a verdict, an eligibility flag, a winner, a ranking, or an amount. What
the record does not establish — that a measurement reflects a real machine —
is recorded as an open gap rather than implied to be solved.

### Uptime is counted in whole seconds against a fixed cycle target

`CYCLE_TARGET_SECONDS` is 86,400, `ACTIVITY_THRESHOLD_SECONDS` is 64,800, and
`GRACE_ALLOWANCE_SECONDS` is 21,600. Seconds are the unit because all three
figures are exact integers in it; no stated rule needs a finer unit, and no
coarser unit represents an 18-hour threshold against a fragmentable allowance
exactly.

The Founder Constitution states the rule twice, as a floor on uptime and as a
ceiling on downtime, and derives neither from the other. The model computes both
forms and requires them to agree. That is a cheap check on a document-level
consistency claim, and it is the same technique the manifest verifier uses
against the constitution's two allocation tables.

The boundary is resolved in the operator's favour, as ADR 0023 directs: exactly
64,800 seconds of uptime, equivalently exactly 21,600 seconds of downtime, meets
the cycle.

### A cycle window is separate from a seat's cycle index

The record is keyed by a `cycle_window` that is deliberately not the evaluated
seat's `cycle_index`.

A seat's 731 cycles begin at that seat's own first activation, so two seats'
cycle 7 are different time windows. Reallocation to "the highest uptime in that
same cycle" is only meaningful against a shared window. Reusing `cycle_index` as
the window would have been simpler and would have silently asserted that every
seat's cycles coincide, which is false under the constitution's own activation
rule.

The consequence is honest rather than comfortable: the model cannot verify that
a supplied `cycle_window` is the correct window for a seat's cycle index,
because the mapping is the deferred cycle-boundary rule. Making the window an
explicit separate field puts that gap in every event rather than hiding it in a
coincidence of names.

### A window's record is bound by digest on first reference

The first accepted evaluation referencing a `cycle_window` stores its record's
digest. A later evaluation presenting a different record for the same window is
rejected with `INCONSISTENT_UPTIME_RECORD`.

The alternatives were to store nothing, leaving each event free to present its
own version of a window's uptime; to store the full record, making the window's
measurements inspectable in state; or to store the digest.

Storing nothing was rejected because it would let one run reallocate two failed
cycles in the same window against contradictory winner sets, which no consensus
rule could accept. Storing full records was rejected on size: up to 100,000
measurements per window would dominate the state value and its digest for no
additional guarantee. The digest costs one 32-byte value per referenced window
and gives the same consistency property.

This does not bound production storage. Window digests accumulate for the length
of a run because pruning needs the settlement and finality rules M3.4 defines,
and the specification records that the storage bound remains open.

### The remainder and the empty winner set carry forward

The reallocated pot is the 34,200,000,000-atomic Founder portion plus the
outstanding carry. It is split equally among the winners, and the integer
remainder becomes the new carry. When no seat in the record met the cycle,
nothing is reallocated and the whole pot carries forward.

Both rules are founder-directed. The Founder Constitution's performance
reallocation section states that the integer remainder of an equal split is
carried forward rather than burned, and that if no node met the cycle at all,
nothing is reallocated and the value is carried forward. They are implemented as
stated.

The carry is consumed when the permission is created rather than when it is
exercised. This follows version one's rule that the beneficiary is resolved at
creation, which is what makes a reallocation permanent: a later exercise cannot
restore the original seat, and it must not be able to re-run the split against a
different winner set.

The resulting conservation identity is asserted as a state invariant:

```text
issued(founder_operator) + outstanding(founder_operator)
  + performance_carry_atomic = n * 34,200,000,000
```

for `n` accepted base evaluations. Every path adds exactly one Founder leg
amount to the three terms, so carried value is unreserved capacity bounded by
the same channel cap as issued and outstanding value. A defect that created
supply through the carry fails an invariant rather than being reported as a
result.

### The referral becomes an unconditional accrual with two destinations

`evaluate_referral_permission` and its `inactive_referral_result` are removed.
`accrue_referral` credits 3,420,000,000 atomic units per referred seat-cycle
directly into custody, keyed by `(referred_seat_id, cycle_index)`.

`SEAT_NOT_REFERRED` disappears. An unreferred seat's accrual is credited to
`unreferred_performance_pool:global` rather than rejected, which is what makes
the channel consume exactly at capacity. Rejecting it would have made the
realised maximum depend on how many buyers happened to arrive through a
referrer.

Accrual into the pool is modelled; paying the pool out is not, because the
definition of a month in cycles and the pool's tie and remainder rules are named
as open work in ADR 0023. The model accumulates a pool balance and stops there
rather than inventing a distribution.

The accrual requires the referred seat to be activated. When a referral begins
for a purchased but never activated seat is explicitly undecided in the Founder
Constitution; requiring activation is the conservative reading, since an
unactivated seat has no cycles to count, and it is recorded as a modelling
choice rather than a settled rule.

### A referrer must itself be an activated seat

Seat activation continues to require the recorded referrer to be an activated
seat. The Founder Constitution lists "whether a referrer must itself hold a
Founder Seat" as open specification work, so this is a modelling choice.

It is required here because the accrual credits `founder_seat:{referrer}`
custody, and a non-seat referrer has no such bucket. Admitting one would need a
new beneficiary kind, so a decision to admit non-seat referrers changes the
contract rather than a parameter, and would require a new version.

### `founder_referral` is not reachable through `direct_issue`

`direct_issue` accepts only the four `direct_mint` channels that carry the
remaining research placeholder. `founder_referral` is a `direct_mint` channel
but is rejected with `INVALID_CHANNEL`.

This is containment, not tidiness. The referral channel is consumed exactly by
the per-seat-cycle accrual, and its eligibility is the recorded referrer
relationship the state already holds. Admitting it to `direct_issue` would let a
supplied eligibility fixture mint referral units outside the per-seat-cycle
accounting, breaking the exact consumption the manifest fixes and placing a
founder-decided channel under an undecided placeholder.

### New and removed failure codes

`MISSING_UPTIME_RECORD`, `INVALID_UPTIME_RECORD`, and
`INCONSISTENT_UPTIME_RECORD` are added.
`INVALID_PERFORMANCE_ALLOCATION` and `SEAT_NOT_REFERRED` are removed.

The uptime failures are deliberately distinct from `MISSING_RESEARCH_INPUT` and
`INVALID_RESEARCH_INPUT`. Reusing the research codes would make a trace unable
to distinguish a missing measurement from a missing founder decision, which is
the one distinction this slice exists to preserve.

`founder-economy-manifest-v2.md` lists the semantic failures the revised
simulator must preserve and records that its numeric codes remain a separate
acceptance step, so adding codes here does not contradict it.

## Consequences

- `simulation/founder_economy_v2/` becomes an executable model rather than a
  loader. `simulation/founder_economy/` is untouched and continues to implement
  and prove version one.
- The accepted M2 seat, revenue-routing, escrow-payout, and scenario-suite
  models still bind version one. Regenerating them against version two is the
  next slice; until then their recorded digests remain evidence about the v1
  contract.
- Two of first-goal requirement 7's three parts remain untouched: uptime is
  represented, but neither the challenge construction nor the dispute window is
  specified. Requirement 8's threshold and allowance are now implemented, and
  requirement 9's reallocation, tie, restriction, and remainder rules are
  implemented.
- Requirement 4, an exact cycle boundary in heights or epochs, is not addressed
  and is made more visible by the separate `cycle_window` field.
- Requirement 12's storage bound on per-cycle uptime records is not closed. The
  digest binding bounds the model's cost per window but does not define pruning.
- No C++, consensus, devnet, bridge, wallet, AI, biometric, or resource behavior
  changes. The model activates nothing and issues no native unit.

## Compatibility and independent review

Version two coexists with version one. Every domain label ends in `-v2`, so no
digest computed under one version can be replayed as the other, and neither
model reads the other's manifest or events.

The vectors and their verifier prove exact accounting under a supplied
measurement. They do not prove measurement integrity, economic safety, or
production readiness. An uptime scheme that survives adversarial founders with
physical machine access requires independent security review, and no such review
has occurred.
