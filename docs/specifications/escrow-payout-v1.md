# Escrow payout v1

Status: Accepted M2 research model contract; not a consensus transition

This document fixes the deterministic integer behavior of the three
founder-directed escrows when value leaves them, as required by requirement 11
of [`m2-founder-economy-proof.md`](../project/goals/m2-founder-economy-proof.md).

The change is classified as economics, authority, and state-transition shape.
ADR 0021 records the alternatives and decision. It changes no M1 bytes, C++
state, configured devnet supply, or accepted simulator schema, and it modifies
neither `founder-economy-simulator-v1`, `founder-seat-schedule-v1`, nor
`revenue-routing-v1`.

## Scope

Version one defines what happens to native value a constitutional issuance
channel has already placed in an escrow: how a bounded spending capability is
delegated, how one payout is authorized and bounded, and how the escrow's
custody is conserved.

It creates no native units. No issuance channel, no channel cap, and no part of
the 55,743,940,100-unit maximum is consumed, because a payout moves value the
`base_permission` channels already issued.

It does not define the AI evaluation that approves a proposal, the milestone or
tranche plan, the approval threshold, the recipient's later use of the funds,
the cycle length in heights, or the signature and envelope encoding that would
carry a capability on a real chain. Those are consensus, AI-framework, and
founder-reserved work.

### Relationship to the other accepted models

This is a separate model with its own schema, state, and digests.
`founder-economy-manifest-v1`, `founder-economy-simulator-v1`,
`founder-seat-schedule-v1`, and `revenue-routing-v1` remain byte-for-byte
unchanged, including their event kinds, vectors, and digests.

`founder-economy-simulator-v1` credits escrow custody through `credit_custody`
and has no spend transition. Its invariant is `typed custody == issued supply`,
so custody there can only grow. A payout would break both that invariant and
the schema ADR 0018 froze, so this model takes escrow custody as an opening
input instead of extending it.

The opening input is not a free parameter. It carries a complete
`founder-economy-simulator-v1` state value together with the digest that value
claims, and this model recomputes that model's `state-v1` digest over the value
before reading a single amount, so the opening custody is exactly what the
claimed digest commits to.

The model cannot by itself tell whether that digest is a genuine accepted
economy result: a self-consistent invented state would also pass. That link is
established one level up, where the normative vectors record the digest and the
verifier derives it from an actual economy run on the accepted economy fixture.
The model's own defence against an invented state is the manifest cap: an
opening amount above the escrow's constitutional bound is rejected regardless of
how consistent the supplied state is.

## Determinism rules

The model is a pure function of its event input. It must not read a wall clock,
environment variable, locale, random source, network, or any mutable external
value, and must not use floating-point arithmetic anywhere.

All monetary arithmetic is unsigned `u64` with checked addition, subtraction,
and multiplication. Any checked operation that would leave the range fails; it
never wraps or saturates.

## Denomination

Payouts move the native asset, so they use the denomination already accepted in
`founder-economy-manifest-v1`.

| Property | Exact value |
| --- | ---: |
| Storage type | `u64` |
| Decimal places | 8 |
| Atomic units per display unit | 100,000,000 |
| Maximum supply in atomic units | 5,574,394,010,000,000,000 |

## The three escrows

The escrow set is fixed and closed. Each identifier is exactly the channel
identifier the accepted manifest already uses, and each cap is that channel's
manifest cap.

| Escrow | Manifest cap in atomic units |
| --- | ---: |
| `venture_escrow` | 1,250,010,000,000,000,000 |
| `community_grants_escrow` | 250,002,000,000,000,000 |
| `developer_incentives_escrow` | 125,001,000,000,000,000 |

No transition adds an escrow, renames one, or merges two. A fourth treasury
category would require an explicit founder decision and a new manifest channel,
which this model deliberately cannot express.

The corresponding custody key in a recorded economy state is
`{escrow_id}:global`, matching that model's singleton custody keys.

## Capability containment

A payout is authorized by a capability, never by an account or a key held
directly by the AI. A capability is bound to exactly one escrow and carries two
independent bounds plus an expiry.

```text
capability = {
  escrow_id            one of the three fixed escrows
  per_payout_maximum   u64, greater than zero
  envelope_total       u64, at least per_payout_maximum
  spent                u64, never above envelope_total
  expiry_cycle         u64, usable while current_cycle <= expiry_cycle
  revoked              bool
}
```

Two bounds exist because they answer different questions. `per_payout_maximum`
bounds a single mistaken or malicious release. `envelope_total` bounds the
cumulative authority delegated, so a capability that is used repeatedly still
stops at a stated total. A capability whose per-payout bound exceeded its
envelope would make the first bound unreachable, so that shape is rejected.

**The envelope bounds authority; custody bounds value.** Both must hold at
payout time. An envelope larger than the escrow's current custody is a valid
grant: the constitution requires the AI to reduce, counteroffer, queue, or
reject a request it cannot fund, so an under-funded delegation must be
expressible and must fail at the moment of spending rather than at the moment
of delegation.

### What containment means here

Three properties are structural rather than asserted:

1. **No issuance capability exists in this model.** There is no transition that
   creates native units, consumes a channel cap, or increases custody after
   binding. `bind_opening_custody` is the only writer of an opening or
   available custody amount, and it rejects once bound, so total custody is
   fixed at bind and non-increasing forever after.
2. **A capability reaches exactly one escrow.** A payout naming an escrow other
   than the capability's is `ESCROW_MISMATCH`. Each escrow keeps its own
   custody, its own paid-out total, and its own recipient balance map, so no
   expression in the model reads two escrows' custody together.
3. **A capability cannot exceed the value present.** A payout above the
   escrow's available custody is `INSUFFICIENT_CUSTODY`, checked independently
   of the envelope, so exhausting authority and exhausting funds are distinct
   observable failures.

Revocation and expiry provide containment in time. A compromised or superseded
capability is stopped without touching custody, which is what makes a failure
in one delegated workflow unable to drain an escrow.

### What custody is never subject to

Escrow custody is never burned, expired, swept, or redirected. A capability
expires; the value it could have released stays in the escrow and remains
available to a later capability indefinitely. This is the constitutional rule
that unused escrow value is not lost merely because no suitable use was found
during an accounting period, and it is why expiry is a property of the
capability record and never of a custody amount.

## Research inputs

Two inputs are supplied rather than derived, and both are recorded in the trace
so a reader can see exactly what the model was told.

```text
economy_state_result = { state_digest, state_value }
approval_result      = { payout_id, decision, evaluation_reference }
```

`economy_state_result` binds opening custody to a recorded economy run.
`state_value` is a complete `founder-economy-simulator-v1` canonical state
value and `state_digest` is the digest it claims; the model recomputes the
digest over the supplied value under that model's `state-v1` label and rejects
any disagreement. Proving that the claimed digest is a genuine accepted economy
result is the verifier's obligation, not the model's; the model additionally
refuses any opening amount above the escrow's manifest cap, so an invented state
still cannot open an escrow beyond its constitutional bound.

`approval_result` stands in for the unresolved AI evaluation. `decision` is
exactly `approved` or `rejected`, and `payout_id` must equal the payout it
authorizes so an approval cannot be replayed onto a different release.
`evaluation_reference` is an opaque identifier carried into the trace.

The AI evaluation criteria, milestone and tranche policy, approval thresholds,
proposal negotiation, and termination rules are deliberately not invented here.
A supplied `approved` decision is a deterministic fixture, not evidence that any
proposal was sound, and it cannot become a production consensus input by
renaming. The approval decides only *whether* a release proceeds. It never
decides an amount, a bound, or which escrow is charged.

## State

```text
bound_state_digest                     = string | null
current_cycle                          = u64
opening_custody[escrow_id]             = u64
available_custody[escrow_id]           = u64
paid_out_total[escrow_id]              = u64
capabilities[capability_id]            = capability
recipient_balances[escrow_id][recipient_id] = u64
accepted_payout_ids                    = set<payout identifier>
```

The three escrow-keyed maps always contain exactly the three fixed escrow
identifiers. Every amount begins at zero, no capability exists, and
`bound_state_digest` is `null`. A recipient balance map never stores a zero
entry, so the canonical state has one representation per logical state.

### Invariants

At every accepted state, for each of the three escrows independently:

```text
opening_custody   = available_custody + paid_out_total
paid_out_total    = checked_sum(recipient_balances[escrow].values())
paid_out_total    = checked_sum(spent of every capability bound to escrow)
opening_custody  <= the escrow's manifest cap
```

and globally:

```text
every capability satisfies 0 < per_payout_maximum <= envelope_total
every capability satisfies spent <= envelope_total
every stored recipient balance is in 1 .. u64_max
every scalar is in 0 .. u64_max
when bound_state_digest is null, every custody amount is zero, no capability
  exists, and no payout has been accepted
```

The three conservation equations are the substance of this model. Each says
every atomic unit an escrow opened with is either still available or credited
to a named recipient of that same escrow. They share no term with each other,
which is what makes "a compromised venture workflow cannot reach the developer
escrow" a structural property rather than a promise.

The third equation is a second, independently maintained account of the same
value. Custody accounting and capability accounting are updated separately and
must agree, so a payout that moved value without charging an envelope, or
charged an envelope without moving value, is an invariant failure rather than a
silent divergence.

None of the equations permits creation: no term on any right-hand side can grow
except by the exact amount a left-hand side falls.

## Canonical bytes and digests

Digest preimages use RFC 8785 canonical bytes under the accepted `D(L)` domain
separation from `protocol-primitives-v1.md`, exactly as in
`revenue-routing-v1`. Every monetary value in a preimage is a canonical
unsigned decimal string; only small exact counts appear as JSON numbers,
bounded at parse time by 9,007,199,254,740,991.

| Label | Preimage |
| --- | --- |
| `protocol-stack:escrow-payout:events-v1` | the parsed event array |
| `protocol-stack:escrow-payout:state-v1` | the canonical state value |
| `protocol-stack:escrow-payout:trace-v1` | the ordered trace records |
| `protocol-stack:escrow-payout:result-v1` | the complete result object |

The binding check reuses the accepted
`protocol-stack:founder-economy:state-v1` label. That label is read, never
written: this model produces no economy state and changes no economy digest.

### Canonical state value

```text
{
  "bound_state_digest": s | null,
  "current_cycle": n,
  "opening_custody":   { "{escrow_id}": s },
  "available_custody": { "{escrow_id}": s },
  "paid_out_total":    { "{escrow_id}": s },
  "capabilities": {
    "{capability_id}": {
      "escrow_id": t,
      "per_payout_maximum": s,
      "envelope_total": s,
      "spent": s,
      "expiry_cycle": n,
      "revoked": b
    }
  },
  "recipient_balances": { "{escrow_id}": { "{recipient_id}": s } },
  "accepted_payout_ids": [ t ]
}
```

`s` is a canonical unsigned decimal string, `n` a JSON integer, `t` a string,
and `b` a JSON boolean. Escrow, capability, and recipient keys are sorted
ascending, as is the payout identifier list.

## Canonical event input

The events input is a JSON array. Each element is an object with exactly `id`,
`kind`, and the fields required by its kind. `id` matches
`^[a-z0-9][a-z0-9_-]{0,63}$` and must be unique across the array; a duplicate
`id` is an input-shape error that aborts the run.

| Kind | Additional fields |
| --- | --- |
| `bind_opening_custody` | `economy_state_result` |
| `grant_capability` | `capability_id`, `escrow_id`, `per_payout_maximum`, `envelope_total`, `expiry_cycle` |
| `execute_payout` | `payout_id`, `capability_id`, `escrow_id`, `recipient_id`, `amount_atomic`, `approval_result` |
| `revoke_capability` | `capability_id` |
| `advance_cycle` | `cycle_index` |

`capability_id`, `payout_id`, `recipient_id`, `escrow_id`, and the research
inputs' identifier fields match the identifier pattern.
`per_payout_maximum`, `envelope_total`, and `amount_atomic` are canonical
unsigned decimal strings within `u64`. `expiry_cycle` and `cycle_index` are
exact unsigned JSON integers. `economy_state_result` and `approval_result` are
always present; `null` models an absent research input.

An `escrow_id` outside the fixed set parses successfully and is rejected by the
transition, so the trace records the attempt rather than aborting the run.

## Transitions

### `bind_opening_custody`

1. A second bind is `ALREADY_BOUND`.
2. A `null` `economy_state_result` is `MISSING_RESEARCH_INPUT`.
3. A `state_value` whose recomputed economy state digest differs from the
   supplied `state_digest` is `INVALID_RESEARCH_INPUT`.
4. A `state_value` that is not a canonical economy state value, or whose
   `typed_custody` amounts are not canonical decimal strings within `u64`, is
   `INVALID_RESEARCH_INPUT`.
5. An escrow custody amount above that escrow's manifest cap is
   `CUSTODY_ABOVE_CAP`.

On success, in one atomic write: each escrow's opening and available custody
are set to the amount its `{escrow_id}:global` custody key holds in the
supplied state, a missing key meaning zero, and `bound_state_digest` records
the verified digest.

Binding is deliberately the only way value enters. A run whose first accepted
payout precedes a bind is impossible, because no capability can exist.

### `grant_capability`

1. An unbound state is `NOT_BOUND`.
2. A previously used `capability_id` is `REPLAY`.
3. An `escrow_id` outside the fixed set is `UNKNOWN_ESCROW`.
4. A zero `per_payout_maximum` or zero `envelope_total` is `ZERO_AMOUNT`; a
   capability that can release nothing is authority without meaning.
5. A `per_payout_maximum` above `envelope_total` is `INVALID_CAPABILITY`.
6. An `expiry_cycle` below `current_cycle` is `CAPABILITY_EXPIRED`.

On success the capability is recorded with `spent` zero and `revoked` false. No
custody moves, so the journal is empty.

An envelope above the escrow's available custody is **not** an error. The
delegation is bounded authority, not a reservation, and the custody check
belongs to the payout.

### `execute_payout`

Conditions are evaluated in exactly this order, so a payout that violates
several of them has one deterministic result code:

1. A previously accepted `payout_id` is `REPLAY`.
2. An unknown `capability_id` is `UNKNOWN_CAPABILITY`. This also covers every
   payout attempted before a bind, since no capability can exist then.
3. An `escrow_id` differing from the capability's is `ESCROW_MISMATCH`.
4. A revoked capability is `CAPABILITY_REVOKED`.
5. A `current_cycle` above the capability's `expiry_cycle` is
   `CAPABILITY_EXPIRED`.
6. A zero `amount_atomic` is `ZERO_AMOUNT`.
7. A `null` `approval_result` is `MISSING_RESEARCH_INPUT`.
8. An `approval_result` whose `payout_id` differs from this payout is
   `INVALID_RESEARCH_INPUT`.
9. An `approval_result` whose `decision` is `rejected` is `APPROVAL_WITHHELD`.
10. An `amount_atomic` above `per_payout_maximum` is `PAYOUT_LIMIT_EXCEEDED`.
11. An `amount_atomic` that would take `spent` above `envelope_total` is
    `ENVELOPE_EXCEEDED`.
12. An `amount_atomic` above the escrow's `available_custody` is
    `INSUFFICIENT_CUSTODY`.
13. A checked custody, total, balance, or envelope step that leaves `u64` is
    `ARITHMETIC_OVERFLOW`.

Authority is checked before funds on purpose. A request that is both
unauthorized and unfunded reports the authority failure, so a capability bound
cannot be probed for an escrow's balance.

`ARITHMETIC_OVERFLOW` is unreachable through events. An escrow's opening custody
is at or below its manifest cap, a payout is at or below available custody, and
the caps are far below `u64`, so no accumulating total can leave the range. The
checked arithmetic is specified and tested directly anyway: a guard that is
absent because a bound currently makes it unnecessary is a guard that
disappears the moment the bound changes.

On success, in one atomic write: the escrow's `available_custody` falls by the
amount, its `paid_out_total` rises by the amount, the recipient's balance in
that escrow's map rises by the amount, the capability's `spent` rises by the
amount, and the payout identifier is recorded.

### `revoke_capability`

1. An unknown `capability_id` is `UNKNOWN_CAPABILITY`.
2. An already revoked capability is `ALREADY_REVOKED`.

On success the capability is marked revoked. Custody, totals, and balances are
untouched, so the journal is empty. Revocation is permanent; a superseding
delegation is a new capability, which keeps the historical record of what was
delegated intact.

### `advance_cycle`

1. A `cycle_index` that is not the current cycle is `CYCLE_MISMATCH`. This
   covers replaying a passed cycle and skipping ahead.
2. A step that leaves `u64` is `ARITHMETIC_OVERFLOW`.

On success `current_cycle` increases by one. No value moves, so the journal is
empty. The cycle counter exists only to make expiry deterministic; it is not an
accounting period and distributes nothing.

Any failure of any transition performs none of its writes and consumes no
identifier.

## Journals and atomicity

An accepted event emits an ordered journal of
`{bucket, direction, amount_atomic}` entries. A zero-valued entry is never
emitted, so a bucket that receives nothing simply does not appear.

| Transition | Buckets |
| --- | --- |
| `bind_opening_custody` | `economy_custody` out; `custody:{escrow_id}` in |
| `grant_capability` | none |
| `execute_payout` | `custody:{escrow_id}` out; `recipient:{escrow_id}:{recipient_id}` in |
| `revoke_capability` | none |
| `advance_cycle` | none |

The engine requires of every accepted journal:

```text
no entry has amount zero
total decreases equal total increases
no bucket appears twice in the same direction
```

and additionally per transition:

```text
bind_opening_custody: the economy_custody decrease equals the sum of the three
  derived opening amounts, and each custody increase equals that escrow's
  derived opening amount
execute_payout: the custody decrease and the recipient increase both equal
  amount_atomic, and both name the capability's escrow
grant_capability, revoke_capability, advance_cycle: the journal is empty
```

A bind of a state whose three escrows are all empty emits an empty journal.
That is accepted: the state still becomes bound, and the balance rule holds
trivially.

### Failure atomicity by construction

A handler is a pure function of the state and the event. It returns either a
rejection or a complete write set, and never holds a reference it can partially
write. The engine commits a write set only after the journal checks pass.
Atomicity is therefore a property of the transition's shape, not of a
compensating copy that must be remembered to be taken.

This follows `revenue-routing-v1` and `founder-seat-schedule-v1` rather than
`founder-economy-simulator-v1`, whose clone-and-compare approach is quadratic in
the run length. As defence in depth the engine compares a constant-time state
summary around every rejection, and the tests compare full state digests around
rejections on bounded scenarios.

Full state invariants are `O(capabilities + credited recipients)`, so a run
asserts them before the first event, after the last, and on a fixed stride of
accepted events.

## Result and trace

One run produces `schema`, `events_digest`, `records`, `trace_digest`,
`final_state`, `state_digest`, `metrics`, and a `result_digest` over the result
without that field. The schema string is
`protocol-stack/escrow-payout-result/v1`.

Each trace record contains the event index, event identifier, kind, acceptance
flag, result code, and the journal. A rejected record has an empty journal.

`metrics` reports the three escrow identifiers with their caps, opening,
available, and paid-out amounts, the bound state digest, the capability count,
the revoked count, the exhausted-envelope count, the recipient count and
largest recipient balance per escrow, the accepted payout count, and the
current cycle. Metrics are derived views; no invariant depends on them.

## Resource limits

A grant, a revoke, a cycle advance, and a payout read and write only the named
scalar and map entries they touch, so all four are constant time. A bind reads
the supplied economy state once, which is bounded by that model's own state
size. No transition iterates over all payouts, all capabilities, or all
historical cycles.

## Versioning and compatibility

The schema strings, event kinds, field sets, escrow identifier set, escrow
caps, research-input shapes, state shape, capability shape, journal buckets,
digest labels, error codes, and the order in which payout conditions are
evaluated are immutable for version one. A changed bound, a new escrow, or a
changed rejection order requires a new schema and ADR.

Running this model has no effect on an M1 account, height, transaction root,
receipt, state root, SQLite database, ABCI response, CometBFT validator, or on
`founder-economy-manifest-v1`, `founder-economy-simulator-v1`,
`founder-seat-schedule-v1`, or `revenue-routing-v1` state, vectors, or digests.

Error codes here are simulator result codes. M3 must separately define consensus
receipts, numeric codes, and commitments before a C++ transition exists.

## Required vectors and evidence

[`escrow-payout-v1.txt`](../../test-vectors/escrow-payout-v1.txt) is normative.
It fixes the denomination, the three escrow identifiers and caps, the bound
economy state digest and the opening custody it yields, a research scenario
trace and its digests, the per-escrow conservation totals, the containment
counts, and every rejection code.

The executed verifier must independently derive, not restate, every recorded
value, and must fail when a recorded key is never derived.

Test coverage must include a payout at exactly the per-payout bound and one
atomic unit above it, an envelope exhausted exactly and then exceeded, a payout
of exactly the available custody and one atomic unit above it, a capability
used against a foreign escrow, a revoked and an expired capability, a withheld
approval, an approval bound to a different payout, a replayed payout, a
tampered economy state binding, custody above a manifest cap, overflow near
`u64` maximum, conservation after every accepted event, the independence of the
three escrows, the non-increase of available custody across a whole run,
atomicity of every rejection, and byte-identical digests across repeated runs.

Passing these checks establishes exact custody conservation and capability
containment. It does not establish that any AI evaluation is sound, that a
milestone or tranche plan is appropriate, that an approval threshold is safe,
that a recipient is legitimate, or that a real signed envelope would carry a
capability correctly. Those remain founder-reserved decisions and later
milestone work requiring independent review.
