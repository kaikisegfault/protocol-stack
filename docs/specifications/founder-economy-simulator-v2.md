# Founder Economy simulator v2

Status: Accepted M3 research model contract; not a consensus transition

This document defines the deterministic input, transition, failure, and digest
contract for the independent standard-library Python Founder Economy simulator
under the direction the Founder Constitution adopted on 2026-08-07. It realizes
the abstract accounting state and transitions specified in
[`founder-economy-manifest-v2.md`](founder-economy-manifest-v2.md) as an
executable model.

The change is classified as economics, input encoding, and state-transition
shape. [ADR 0025](../decisions/0025-founder-economy-simulator-v2-transitions.md)
records the alternatives and decision, and
[ADR 0023](../decisions/0023-founder-decisions-activity-referrals-and-supply.md)
records the founder direction it implements. It changes no M1 bytes, C++ state,
configured devnet supply, previously accepted simulator schema, or state root.

## Relationship to version one

[`founder-economy-simulator-v1.md`](founder-economy-simulator-v1.md) is not
edited, retracted, or reinterpreted. It states the contract the accepted M2
models implement and the M2 evidence proves, and
`simulation/founder_economy/` continues to implement it unchanged.

Version two is a separate accepted contract with its own schema string, domain
labels, event kinds, state shape, failure codes, and digests. The two models
coexist; neither reads the other's manifest, events, or digests.

The transition set changes, not only its parameters:

| | v1 | v2 |
| --- | --- | --- |
| Referral | `evaluate_referral_permission`, conditional | `accrue_referral`, unconditional direct mint |
| Referral of an unreferred seat | `SEAT_NOT_REFERRED` | credited to the unreferred performance pool |
| Permission key | `(seat_id, cycle_index, kind)` | `(seat_id, cycle_index)` |
| Failed-cycle Founder leg | supplied allocation list | derived same-window winner set |
| Cycle activity | supplied `activity_result` | derived from the cycle uptime record |
| Research placeholders | four | one |

## Scope

Version two defines:

- the canonical simulator event array and its five event kinds;
- the cycle uptime record, and the activity predicate and winner set derived
  from it;
- five state transitions and their exact reads, writes, and journals;
- the performance carry and its conservation identity;
- the deterministic state, trace, events, and result digests; and
- the normative vector obligations.

It does not define serialized consensus transaction bytes, receipt bytes, a
state-root schema, a block result, an activation height, a chain epoch length,
the mapping from a seat's cycle index to a cycle window, the challenge
construction or sampling rate that produces an uptime measurement, the AI
dispute window, the definition of a month for the unreferred pool, the
distribution of that pool, or production direct-channel eligibility. Those
remain M3 and M4 work and are named as gaps in
[What this model does not establish](#what-this-model-does-not-establish).

The model remains one native asset. Every amount is a count of that asset's
atomic unit. A channel, pool, or typed custody bucket is an accounting
partition, not a second asset.

## Determinism rules

The simulator is a pure function of its two JSON inputs. It must not read a
wall clock, environment variable, locale, random source, network, hash seed
that affects output ordering, or any mutable external value. It must not use
floating-point arithmetic anywhere, including for intermediate derivations.

All monetary arithmetic is unsigned `u64` with checked addition, subtraction,
and multiplication as defined in `founder-economy-manifest-v2.md`. Any checked
operation that would leave the range fails; it never wraps, saturates, or
promotes to a wider type in an accepted result.

Every derived set is ordered before it reaches state or a digest. The winner
set is emitted in ascending seat order, so two implementations that compute the
same set produce the same legs, the same journal, and the same digest.

## Canonical bytes and digests

Every digest preimage is produced by parsing duplicate-free I-JSON and
serializing it with the JSON Canonicalization Scheme in RFC 8785. Using `D(L)`
from [`protocol-primitives-v1.md`](protocol-primitives-v1.md):

```text
digest(label, value) = SHA-256( D(label) || jcs_bytes(value) )
```

Every monetary value inside a digest preimage is a canonical unsigned decimal
string matching `0` or `[1-9][0-9]*`. Only small exact counts — seat
identifiers, cycle indexes, cycle windows, uptime seconds, trace indexes,
channel counts, and array lengths — appear as JSON numbers. No monetary value
is ever serialized as a JSON number, so no digest preimage depends on binary64
range.

The following labels are fixed for version two:

| Label | Preimage |
| --- | --- |
| `protocol-stack:founder-economy:manifest-v2` | the accepted manifest object |
| `protocol-stack:founder-economy:events-v2` | the parsed event array |
| `protocol-stack:founder-economy:state-v2` | the canonical state value |
| `protocol-stack:founder-economy:trace-v2` | the ordered trace records |
| `protocol-stack:founder-economy:result-v2` | the complete result object |
| `protocol-stack:founder-economy:uptime-record-v2` | one canonical uptime record |

The manifest label, canonical byte length 2,267, and digest
`84cca09865b6c62bf09d3f6bc3821a2527c7a4835652cffdc0ebefa34b314ce5` are
inherited unchanged from `founder-economy-manifest-v2.md`. The simulator must
reproduce them from the checked-in manifest file rather than restating them.

Every version-two label ends in `-v2`, so no digest computed under version one
can be replayed as version two even where the preimage shape coincides.

## Cycle time constants

A cycle is a 24-hour-target window. Uptime is counted in whole seconds.

| Constant | Value | Source |
| --- | ---: | --- |
| `CYCLE_TARGET_SECONDS` | 86,400 | 24-hour-target cycle |
| `ACTIVITY_THRESHOLD_SECONDS` | 64,800 | 18 hours or more of fully operational uptime |
| `GRACE_ALLOWANCE_SECONDS` | 21,600 | cumulative fragmentable 6-hour allowance |

The Founder Constitution states the rule twice, as a floor on uptime and as a
ceiling on downtime, and derives neither from the other. The two agree exactly
because:

```text
ACTIVITY_THRESHOLD_SECONDS + GRACE_ALLOWANCE_SECONDS = CYCLE_TARGET_SECONDS
```

The model therefore evaluates both forms and requires them to agree, rather
than picking one and asserting the equivalence in a comment. A seat with
exactly 64,800 seconds of uptime, and equivalently exactly 21,600 seconds of
downtime, meets the cycle: ADR 0023 resolves the boundary in the operator's
favour, because an allowance a founder cannot fully use is not the allowance
they were promised.

Seconds are the counting unit because a cycle target of 86,400 seconds and both
thresholds are exact integers in it. No finer unit is required by any stated
rule, and no coarser unit represents the 18-hour threshold exactly against a
fragmentable allowance.

## The cycle uptime record

A cycle uptime record is the model's abstract form of the measurement the
Founder Constitution requires: validator participation and transaction
servicing derived from on-chain records, and resource provision proved by
challenge-response, reviewed under a bounded AI dispute window.

```text
cycle_uptime_record = {
  cycle_window : count,
  entries      : [ { seat_id : count, uptime_seconds : count } ]
}
```

`cycle_window` identifies the shared 24-hour-target window the record measures.
It is deliberately not the evaluated seat's `cycle_index`. A seat's 731 cycles
begin at that seat's own first activation, so two seats' cycle 7 are different
windows, and reallocation to "the highest uptime in that same cycle" is only
meaningful against a shared window. Collapsing the two would silently assert
that every seat's cycles coincide.

### What makes this a derivation and not a fixture

The record carries measurements only. It never carries a verdict, an
eligibility flag, a winner, a ranking, or an amount. The model computes the
activity predicate and the winner set from the measurements under the rules
below, so the answer cannot be supplied.

This is the exact respect in which the record differs from the research
placeholder it replaces. A research placeholder stands in for a founder policy
that has not been decided; supplying `active: true` supplies the policy's
answer. The uptime record stands in for a derivation whose rule *is* decided —
ADR 0023 and the Founder Constitution fix the threshold, the allowance, the
ranking, the tie rule, and the remainder rule — but whose measurement pipeline
is not yet built. Renaming a verdict fixture would defeat this distinction, so
the record's schema makes a verdict inexpressible.

What the record does not establish is stated in
[What this model does not establish](#what-this-model-does-not-establish); in
particular, nothing here proves that a supplied measurement reflects a real
machine.

### Record binding

The first accepted evaluation that references a `cycle_window` binds that
window to its record's digest under the
`protocol-stack:founder-economy:uptime-record-v2` label. Every later evaluation
referencing the same window must present a record with the same digest, or the
event is rejected with `INCONSISTENT_UPTIME_RECORD`.

The digest preimage orders `entries` by ascending seat, so the binding is over a
window's measurements rather than over the order one event happened to present
them in. Duplicate seats are rejected before the digest is taken, so that order
is total.

A window's uptime is therefore one fact for the whole run rather than a
per-event opinion, which is what a consensus rule will require. Only the digest
is retained, so the binding costs one 32-byte value per referenced window
instead of a stored table of up to 100,000 measurements.

### Record validity

Every field of a record is a count, so `cycle_window`, `seat_id`, and
`uptime_seconds` are already bounded by `MAX_JSON_INTEGER` at parse time as
input-shape errors. Beyond that, a record is invalid, giving
`INVALID_UPTIME_RECORD`, when any of the following holds:

1. `entries` is empty.
2. Any `seat_id` is outside `0..99,999`.
3. Any `seat_id` is repeated.
4. Any `seat_id` is not an activated seat.
5. Any `uptime_seconds` exceeds `CYCLE_TARGET_SECONDS`.
6. The evaluated seat does not appear in `entries`.

The seat bound and the activation requirement apply to every listed seat, not
only the evaluated one, because any listed seat may become a reallocation
recipient and must have a custody bucket.

Condition 5 is a containment bound, not a measurement claim: a window cannot
contain more uptime than its own duration, so a record asserting otherwise is
malformed rather than merely surprising. Condition 6 makes the evaluated seat's
own activity derivable; without it the transition would have no measurement to
apply its threshold to.

A record is not required to list every activated seat. The model derives from
the record it is given and does not prove that the record is complete; a record
that omits seats yields a winner set over the seats it does list. Completeness
is a property of the measurement pipeline that M3.4 must establish, and it is
not established here.

### Derived activity

For the evaluated seat's entry:

```text
met_cycle = uptime_seconds >= ACTIVITY_THRESHOLD_SECONDS
          = (CYCLE_TARGET_SECONDS - uptime_seconds) <= GRACE_ALLOWANCE_SECONDS
```

Both forms are computed and required to agree. A disagreement is a model defect
and raises `INVARIANT` rather than producing a result.

### Derived winner set

When the evaluated seat did not meet the cycle:

```text
qualified = { e in entries : e.uptime_seconds >= ACTIVITY_THRESHOLD_SECONDS }
maximum   = max( e.uptime_seconds for e in qualified )
winners   = sorted( e.seat_id for e in qualified if e.uptime_seconds = maximum )
```

The winner is the highest uptime actually achieved in that window, whatever
value that turns out to be, not a fixed perfection bar. Restricting `qualified`
to seats that met the cycle implements the founder-directed rule that a failed
seat never rewards another failed seat, and it excludes the evaluated seat
automatically, because a seat that failed the cycle is not in `qualified`. The
model asserts that exclusion rather than relying on it.

`winners` is empty exactly when no seat in the record met the cycle.

## Performance carry and reallocation

The Founder portion of a failed cycle is 34,200,000,000 atomic units. It is
combined with the outstanding carry, split equally, and the integer remainder
becomes the new carry.

```text
pot       = checked_add( FOUNDER_OPERATOR_LEG, performance_carry_atomic )
share     = pot / count(winners)          integer division
remainder = pot mod count(winners)

legs      = one leg of `share` for each winner, in ascending seat order
carry'    = remainder
```

When `winners` is empty, nothing is reallocated: no Founder leg is created and
the whole pot carries forward.

```text
legs   = ()
carry' = pot
```

Both rules are founder-directed in the Founder Constitution's performance
reallocation section, which states that the remainder of an equal split is
carried forward rather than burned, and that if no node met the cycle at all,
nothing is reallocated and the value is carried forward.

The carry is consumed when the permission is created, not when it is exercised,
because the beneficiary set is resolved at creation. That is the same rule that
makes an inactive cycle's reallocation permanent in version one: a later
exercise cannot restore the original seat, and it cannot re-run the split
against a different winner set.

`share` is never zero. The pot is at least 34,200,000,000 and the winner count
is at most the 100,000-seat capacity, so the smallest possible share is 342,000
atomic units. The model still rejects a zero leg through its state invariants,
so the bound is proved rather than assumed.

### The carry conservation identity

At every accepted state, where `n` is the number of accepted base evaluations —
which is exactly `count(evaluated_permission_keys)`, because version two has no
path that consumes an evaluation key without creating a permission:

```text
issued(founder_operator)
  + outstanding(founder_operator)
  + performance_carry_atomic
  = n * FOUNDER_OPERATOR_LEG
  <= cap(founder_operator)
```

The model asserts the equality, not merely the bound. A bound would admit a
defect that lost carried value; the equality does not.

Each accepted base evaluation adds exactly one Founder leg amount to the sum of
the three terms, whichever path it takes: an active cycle reserves the leg, a
reallocation reserves `pot - remainder` and leaves `remainder` in the carry, and
an empty winner set reserves nothing and leaves the whole pot in the carry.
Exercise moves value from outstanding to issued and does not change the sum.

This identity is the reason the carry cannot inflate supply: carried value is
capacity that has not been reserved, and it is bounded by the same channel cap
as issued and outstanding value. The model asserts it as a state invariant, so a
defect that created value through the carry would fail rather than be reported.

## Simulator state

```text
seats[seat_id] = { referrer_seat_id: seat_id | none }

channels[channel_id] = {
  issued_atomic:u64,
  outstanding_atomic:u64
}

pending_permissions[(seat_id, cycle_index)] = ordered legs
evaluated_permission_keys    = set<(seat_id, cycle_index)>
referral_accrual_keys        = set<(referred_seat_id, cycle_index)>
accepted_direct_decision_ids = set<decision identifier>
bound_uptime_records[cycle_window] = digest
typed_custody[custody_key]   = u64
performance_carry_atomic     = u64
```

There is no permission `kind` discriminator, because the referral is no longer a
permission. Every channel begins at zero issued and zero outstanding, the carry
begins at zero, and there is no genesis allocation.

### Replay and custody keys

A permission replay key is rendered `{seat_id}:{cycle_index}` with the seat
zero-padded to five digits and the cycle to three, so the key set sorts
identically under numeric and lexicographic ordering. `00042:007` is the key for
seat 42, cycle 7. A referral accrual key uses the same rendering over the
referred seat and cycle. The two live in disjoint sets and never collide.

A custody key is `{beneficiary_kind}:{beneficiary_id}` where the beneficiary
kind is resolved at permission creation or at accrual, not at exercise:

| Manifest beneficiary kind | Resolved custody key |
| --- | --- |
| `venture_escrow` | `venture_escrow:global` |
| `community_grants_escrow` | `community_grants_escrow:global` |
| `developer_incentives_escrow` | `developer_incentives_escrow:global` |
| `system_creator_company` | `system_creator_company:global` |
| `cycle_founder_or_performance_winners` | `founder_seat:{seat_id}` |
| `recorded_referrer` | `founder_seat:{referrer_seat_id}` |
| `unreferred_performance_pool` | `unreferred_performance_pool:global` |
| direct-channel beneficiary | `direct_beneficiary:{beneficiary_id}` |

A `founder_seat` identifier is zero-padded to five digits for the same ordering
reason.

### Invariants

At every accepted state:

```text
for each channel:
  issued_atomic + outstanding_atomic <= cap_atomic

issued_supply            = checked_sum(channel.issued_atomic)
outstanding_permissions  = checked_sum(channel.outstanding_atomic)

issued_supply                            <= maximum_supply_atomic
issued_supply + outstanding_permissions  <= maximum_supply_atomic
checked_sum(typed_custody)                = issued_supply

issued(founder_operator) + outstanding(founder_operator)
  + performance_carry_atomic
    = count(evaluated_permission_keys) * FOUNDER_OPERATOR_LEG
   <= cap(founder_operator)

every pending permission's legs sum to its recorded total
every pending permission key is in evaluated_permission_keys
no stored amount is zero
```

Outstanding permission units are liabilities against channel capacity. They are
not issued supply, circulating supply, an account balance, or spendable escrow
custody. The performance carry is neither: it is unreserved channel capacity
that a future reallocation will distribute.

### Canonical state value

The state digest is taken over exactly this value, so an independent
implementation must reproduce this shape to reproduce the digest:

```text
{
  "seats": { "{seat:05d}": "{referrer:05d}" | null },
  "channels": { "{channel_id}": { "issued_atomic": s, "outstanding_atomic": s } },
  "pending_permissions": {
    "{permission key}": {
      "seat_id": n, "cycle_index": n, "cycle_window": n,
      "met_cycle": b,
      "total_atomic": s,
      "legs": [ { "channel": t, "custody_key": t, "amount_atomic": s } ]
    }
  },
  "evaluated_permission_keys": [ t ],
  "referral_accrual_keys": [ t ],
  "accepted_direct_decision_ids": [ t ],
  "bound_uptime_records": { "{cycle_window}": t },
  "typed_custody": { "{custody key}": s },
  "performance_carry_atomic": s
}
```

`s` is a canonical unsigned decimal string, `n` a JSON integer, `b` a JSON
boolean, and `t` a string. `channels` contains all ten manifest channels in
every state, including those still at zero. `legs` preserves creation order; the
three key arrays are sorted ascending. A custody entry is absent rather than
zero. JCS sorts every object key, so the emitted member order is not itself
normative.

A pending permission records the `cycle_window` and `met_cycle` its legs were
derived from, so the trace shows which measurement decided a reallocation and a
reader can check the legs against the record without replaying the run.

## Canonical event input

The events input is a JSON array. Each element is an object with exactly `id`,
`kind`, and the fields required by its kind. `id` matches
`^[a-z0-9][a-z0-9_-]{0,63}$` and must be unique across the array; a duplicate
`id` is an input-shape error that aborts the run rather than a modelled
rejection.

Seat identifiers, cycle indexes, cycle windows, and uptime seconds are JSON
integers bounded by 9,007,199,254,740,991, the largest integer a conforming JSON
stack represents exactly. That bound is a parse-time input-shape error, not a
modelled rejection: a count above it could not be canonicalized, so it must be
refused before it can reach a digest preimage. Semantic bounds inside that range
remain modelled rejections.

Monetary values are canonical unsigned decimal strings. A research-input field
is always present; the JSON value `null` models an absent research input and
produces the modelled `MISSING_RESEARCH_INPUT` rejection. A `null`
`cycle_uptime_record` likewise produces `MISSING_UPTIME_RECORD`.

| Kind | Additional fields |
| --- | --- |
| `activate_seat` | `seat_id`, `referrer_seat_id` |
| `evaluate_base_permission` | `seat_id`, `cycle_index`, `cycle_uptime_record` |
| `accrue_referral` | `seat_id`, `cycle_index` |
| `exercise_permission` | `seat_id`, `cycle_index` |
| `direct_issue` | `channel`, `decision_id`, `beneficiary_id`, `amount_atomic`, `eligibility_result` |

`referrer_seat_id` is `null` for an unreferred seat or a seat identifier that is
not the activating seat. `exercise_permission` carries no `permission_kind`,
because there is only one kind of permission. `channel` must be one of the four
`direct_mint` channel identifiers that carry a research placeholder;
`founder_referral` is not among them. `decision_id` and `beneficiary_id` match
the identifier pattern.

### The remaining research input

```text
eligibility_result = { channel, decision_id, beneficiary_id,
                       amount_atomic, eligible:bool }
```

This is the single research placeholder the manifest names. It is bound to the
exact action it authorizes: a well-formed object whose binding fields differ
from the attempted action produces `INVALID_RESEARCH_INPUT` and is never
silently reinterpreted.

It is a deterministic stand-in. Its authenticity, authorization, resource bound,
and real policy are unresolved and cannot become production consensus inputs by
renaming a fixture.

## Transitions

### Seat activation

Reads the seat bounds and the seat table. Writes one seat record.

1. `seat_id` outside `0..99,999` is `CYCLE_RANGE`.
2. A `referrer_seat_id` outside the bounds, or equal to `seat_id`, is
   `INVALID_REFERRER`.
3. An already-activated `seat_id` is `REPLAY`.
4. A `referrer_seat_id` that is not itself activated is `SEAT_NOT_ACTIVATED`.

Activation issues nothing, reserves nothing, and emits an empty journal. This
version models the seat graph only; enrollment, payment proof, biometric
identity, manager records, and the 1,000-seats-per-person bound belong to M4 and
are explicitly not modelled here.

Requiring the referrer to be an activated seat is a modelling choice, not a
founder decision. The Founder Constitution lists "whether a referrer must itself
hold a Founder Seat" as open specification work. This model requires it because
the referral credits `founder_seat:{referrer_seat_id}` custody and a
non-seat referrer has no such bucket. A decision that admits non-seat referrers
requires a new beneficiary kind and a new contract version.

### Base permission evaluation

Creates one base permission for `(seat_id, cycle_index)`.

1. `seat_id` or `cycle_index` outside `0..99,999` and `0..730` is
   `CYCLE_RANGE`.
2. An unactivated seat is `SEAT_NOT_ACTIVATED`.
3. An already-evaluated key is `REPLAY`.
4. A `null` `cycle_uptime_record` is `MISSING_UPTIME_RECORD`.
5. A record failing any validity condition is `INVALID_UPTIME_RECORD`.
6. A record whose digest differs from the digest already bound to its
   `cycle_window` is `INCONSISTENT_UPTIME_RECORD`.
7. If the evaluated seat met the cycle, the `founder_operator` leg is
   34,200,000,000 atomic units for `founder_seat:{seat_id}`.
8. If it did not, the derived winner set and the carry produce the Founder legs
   as specified in [Performance carry and reallocation](#performance-carry-and-reallocation).
9. Every resulting leg is proved against its channel: a checked
   `issued + outstanding + amount` above `cap_atomic` is `CHANNEL_CAP`, and a
   checked intermediate outside `u64` is `ARITHMETIC_OVERFLOW`.

On success the four fixed legs and the resolved Founder legs are stored as one
ordered pending permission, the key is recorded as evaluated, the window is
bound if it was not already, the carry is updated, and every involved channel's
outstanding amount increases. No beneficiary receives issued custody. Any
failure performs none of these writes, does not consume the key, does not bind
the window, and does not change the carry.

The failed path retains the complete base permission: the four non-Founder legs
keep their fixed beneficiaries and amounts. Only the 34,200,000,000-atomic
Founder portion changes beneficiary, and only that portion interacts with the
carry.

### Referral accrual

Credits one unconditional direct-mint accrual for
`(referred_seat_id, cycle_index)`.

1. Bounds failures are `CYCLE_RANGE`.
2. An unactivated seat is `SEAT_NOT_ACTIVATED`.
3. An already-accrued key is `REPLAY`.
4. The beneficiary is `founder_seat:{referrer_seat_id}` when the seat has a
   recorded referrer, and `unreferred_performance_pool:global` when it does not.
5. A checked `issued + outstanding + 3,420,000,000` above the `founder_referral`
   cap is `CHANNEL_CAP`, and a checked intermediate outside `u64` is
   `ARITHMETIC_OVERFLOW`.

On success the `founder_referral` channel's issued amount and the beneficiary's
typed custody increase by 3,420,000,000 atomic units and the accrual key is
recorded, all atomically. A failure changes no state and does not consume the
key.

The accrual takes no activity input and no eligibility input. It is
unconditional by founder direction: a referrer cannot operate, repair, or
influence someone else's machine, so a benefit that evaporated when that machine
failed would penalise the referrer for an event outside their control. Its
eligibility is the recorded referrer relationship the state already holds.

Because every seat-cycle reaches exactly one of the two destinations, the
channel is consumed exactly at full capacity when every seat completes its
window:

```text
3,420,000,000 * 100,000 * 731 = 250,002,000,000,000,000
```

Referral accrual and base evaluation are independent. Failure or cap exhaustion
in either can never remove, modify, or block the other, and neither consumes the
other's replay key.

### Permission exercise

References one pending permission key.

1. Bounds failures are `CYCLE_RANGE`.
2. No pending permission for the key is `PERMISSION_NOT_FOUND`. A second
   exercise therefore cannot issue value again.
3. A pending permission whose legs do not sum to its recorded total is
   `INVARIANT`. Partial exercise, per-leg exercise, implicit expiry, burn,
   sweep, and beneficiary substitution are not expressible in this schema and
   are invalid.
4. Every outstanding subtraction must be valid, every issued and custody
   addition must fit `u64`, and every channel cap must hold. A violation is
   `ARITHMETIC_OVERFLOW` or `CHANNEL_CAP`.

On success, in one atomic journal: every affected channel's outstanding amount
decreases, its issued amount increases by the same value, every typed
beneficiary is credited, and the pending permission is removed while its
evaluated replay key is retained. A failure changes no state.

Exercise is where a reallocation settles, in the same atomic transition that
credits the escrows and the System Creator. It does not recompute the winner
set, re-read a record, or touch the carry; those were fixed at evaluation.

Authorization is an explicit simulator capability. This document does not accept
it as a production authority.

### Direct-channel issuance

Selects one placeholder `direct_mint` channel, a positive amount, one
beneficiary, and a unique decision identifier.

1. A channel identifier that is unknown, is not `direct_mint`, or is
   `founder_referral` is `INVALID_CHANNEL`.
2. A zero amount is `ZERO_AMOUNT`; an amount above `u64` is a `TYPE` input
   error at parse time.
3. A previously accepted `decision_id` is `REPLAY`.
4. A `null` `eligibility_result` is `MISSING_RESEARCH_INPUT`.
5. A result whose channel, decision identifier, beneficiary, or amount differs
   from the attempted action is `INVALID_RESEARCH_INPUT`.
6. A false `eligible` result is `NOT_ELIGIBLE` and consumes no decision
   identifier.
7. A checked `issued + outstanding + amount` above `cap_atomic` is
   `CHANNEL_CAP`.

On success the channel's issued amount and the beneficiary's typed custody
increase by the same amount and the decision identifier is recorded, all
atomically. Any failure changes no state and does not consume the decision
identifier.

Excluding `founder_referral` from this transition is load-bearing rather than
tidy. The referral channel is consumed exactly by the per-seat-cycle accrual
above, and its eligibility is the recorded referrer relationship rather than an
undecided policy. Admitting it here would let a supplied eligibility fixture
mint referral units outside the per-seat-cycle accounting, which would break the
exact consumption the manifest fixes and would place a founder-decided channel
under an undecided placeholder.

## Journals and atomicity

An accepted transition emits an ordered journal of
`{bucket, direction, amount_atomic}` entries. Buckets are `capacity:{channel}`,
`outstanding:{channel}`, `issued:{channel}`, `custody:{key}`, and
`carry:performance`. `direction` is `increase` or `decrease` and
`amount_atomic` is a positive canonical decimal string, so a journal never
contains a signed or zero amount and never needs a JSON number.

An entry's signed delta is `+amount_atomic` for `increase` and `-amount_atomic`
for `decrease`. `capacity:{channel}` is the derived remaining capacity
`cap - issued - outstanding`. The engine requires all three of the following,
where the channel sum excludes both custody and carry entries:

```text
sum(capacity deltas) + sum(outstanding deltas) + sum(issued deltas) = 0
sum(custody deltas) = sum(issued deltas)

for a base evaluation, and only for a base evaluation:
  sum(outstanding:founder_operator deltas) + sum(carry deltas)
    = FOUNDER_OPERATOR_LEG
```

Permission creation moves value from capacity to outstanding, exercise moves it
from outstanding to issued and mirrors it into custody, and direct issuance and
referral accrual move it from capacity to issued and mirror it into custody.

The carry is deliberately outside the first equation. It is not a fourth ledger
dimension: carried value is remaining channel capacity that a future
reallocation has been promised, and remaining capacity is already one of the
three terms. Adding the carry there would double-count it and no accepted
journal would balance.

The third equation is the per-event form of the carry conservation identity, and
it is what a reallocation must satisfy. An active cycle reserves the whole
Founder portion and moves no carry. A reallocation reserves `pot - remainder`
and moves the carry from `carry_in` to `remainder`, and the two terms sum to the
portion exactly. An empty winner set reserves nothing and carries all of it. No
other event kind may move the carry at all, which the engine also asserts.

A carry entry is emitted only when the carry actually changes, so a journal
never carries a zero entry.

Every transition is applied to a clone of the accepted state. An accepted
outcome is committed only after its journal balances and the full state
invariants hold. A rejected outcome discards the clone, must emit no journal,
and must leave the state digest unchanged; the engine asserts both.

Because rejection is checked by comparing state digests before and after, a
silent partial write is a test failure rather than a documentation claim.

## Result and trace

One run produces:

```text
schema           = protocol-stack/founder-economy-simulation-result/v2
manifest_digest  = the accepted manifest digest
manifest_canonical_length = 2267
events_digest    = digest over the parsed event array
records          = ordered trace records
trace_digest     = digest over records
final_state      = canonical state value
state_digest     = digest over final_state
metrics          = derived totals
result_digest    = digest over the result object without this field
```

Each trace record contains the event index, event identifier, kind, acceptance
flag, result code, the state digest before and after, and the journal. A
rejected record has an empty journal and equal before and after digests.

`metrics` reports the maximum supply, issued supply, outstanding permissions,
remaining capacity, and the performance carry; per channel its cap, issued,
outstanding, and remaining amounts; the activated seat, pending permission,
evaluated key, referral accrual, bound window, and accepted decision counts; and
the `founder_operator` accounted total that the carry conservation identity
fixes. Metrics are derived views; no invariant depends on them, and adding one
is a compatible change that alters the result digest.

## Resource limits

The abstract ceiling is 73,100,000 base evaluation keys and at most 73,100,000
referral accrual keys. A transition reads and writes only the seat, cycle,
channel, permission, custody, window, and carry entries it names; no transition
iterates over all seats or all cycles.

A base evaluation iterates over its own record's entries, which is bounded by
the 100,000-seat capacity. That is the one population-scale read in the model,
and it is bounded by the seat capacity rather than by the seat-cycle population.

Bound window digests accumulate for the length of a run, one 32-byte value per
distinct referenced window. This model does not prune them, because pruning
requires the settlement and finality rules that M3.4 defines. The production
storage bound on per-cycle uptime records is therefore still open, and this
model does not close it.

Simulation scenarios are bounded by their event arrays. A production encoding
and bounded settlement mechanism remain M3 work.

## Versioning and compatibility

The schema strings, event kinds, field sets, research-input shape, uptime-record
shape, custody-key format, journal buckets, digest labels, and error codes are
immutable for version two. A changed transition, field, or semantic rule
requires a new simulator schema and ADR.

Version one and version two coexist. The v1 artifacts are the accepted M2
evidence and remain in place, passing, and unedited. Neither model accepts the
other's manifest, and every domain label differs, so no digest computed under
one version can be replayed as the other.

The accepted M2 seat, revenue-routing, escrow-payout, and scenario-suite models
still bind version one. Regenerating them against version two is the next
milestone slice; until then, their recorded digests remain evidence about the v1
contract and this document makes no claim about them.

Loading or running this model has no effect on an M1 account, fee pool, height,
transaction root, receipt, state root, SQLite database, ABCI response, or
CometBFT validator. The existing M1 nine-decimal supply remains conserved. The
eight-decimal Founder target is not an in-place reinterpretation of M1 balances;
the migration or new-genesis requirement in ADR 0017 is unchanged.

Error codes here are simulator result codes. M3 must separately define consensus
receipts, numeric codes, and commitments before a C++ transition exists.

## What this model does not establish

The derivations above replace two supplied fixtures with computation. They do
not supply the inputs that computation will need in production, and the
following remain open:

- **The measurement itself.** Nothing here proves that an `uptime_seconds`
  value reflects a real machine. The challenge construction, sampling rate, AI
  dispute window length, and dispute resolution are unspecified, and ADR 0023
  records that an uptime scheme surviving adversarial founders with physical
  machine access requires independent security review that has not occurred.
- **Record completeness.** The winner set is computed over the record supplied,
  and a record that omits seats is not detected.
- **The cycle boundary.** The mapping from a seat's `cycle_index` to a
  `cycle_window` is not defined or checked. The model binds a window's record
  once it is referenced, but it cannot tell whether that window is the correct
  one for the seat's cycle. A chain-defined height or epoch rule is required and
  is first-goal evidence requirement 4.
- **The unreferred pool's distribution.** Accrual into
  `unreferred_performance_pool:global` is modelled; paying it out is not. The
  definition of a month in cycles, the pool's tie and remainder rules, and its
  storage bound are named as open work in ADR 0023.
- **Referral start conditions.** When a referral accrual begins for a purchased
  but never activated seat is undecided; this model requires activation.
- **Direct-channel eligibility and the AI funding framework.** Both remain
  founder-reserved and are supplied as the single bound research placeholder.
- **Seat provenance.** A seat purchased in the Founder Seat sale model is still
  not proved to be an activated seat here, and the per-principal bound is not
  yet a per-human bound.

## Required vectors and evidence

[`founder-economy-simulator-v2.txt`](../../test-vectors/founder-economy-simulator-v2.txt)
is normative. It fixes this version's result schema, digest labels, cycle time
constants and their identity, the derived activity boundary, the winner set and
carry arithmetic, the referral accrual destinations and exact channel
consumption, the zero-write atomicity claims, and the complete trace, totals,
custody, and digests of the checked-in research scenario.

It must be reproduced by an executed verifier rather than by review alone. The
verifier independently derives, rather than restates, every recorded value, and
its independence is the same `expected.py` module the manifest verifier uses:
that module imports nothing from `simulation/` and restates the Founder
Constitution's tables and thresholds by hand.

The verifier must also fail when a recorded key is never derived, when a derived
key is absent from the file, and when any recorded value is tampered with. A
vector that no derivation reaches is unverified, so partial coverage must not
report success.

Test coverage must include positive, negative, boundary, replay, overflow,
atomicity, cap-exhaustion, uptime-boundary, tie, carry, empty-winner-set,
record-binding, and complete 731-cycle scenarios, plus byte-identical digests
across repeated runs.

Acceptance requires full GitHub-hosted verification on the exact commit. Passing
these checks establishes exact accounting under a stated measurement, not
economic safety, measurement integrity, or production readiness.
