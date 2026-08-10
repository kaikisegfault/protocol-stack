# Founder Economy simulator v3

Status: Accepted M3 research model contract; not a consensus transition

This document defines the deterministic input, transition, failure, and digest
contract for the independent standard-library Python Founder Economy simulator
that **enforces** the cycle boundary and record completeness, rather than
recording them as gaps.

It realizes the same accounting contract as version two —
[`founder-economy-manifest-v2.md`](founder-economy-manifest-v2.md) is unchanged
and is not re-versioned — and adds the two checks that
[`cycle-boundary-v1.md`](cycle-boundary-v1.md) and
[`uptime-measurement-v1.md`](uptime-measurement-v1.md) each define and neither
applies.

It satisfies requirements 8 and 9 of
[`first-goal.md`](../project/first-goal.md) in enforced rather than specified
form. The change is classified as state-transition shape and input encoding.
[ADR 0029](../decisions/0029-founder-economy-simulator-v3-enforced-boundary.md)
records the alternatives and the decision. It changes no M1 bytes, C++ state,
configured devnet supply, or previously accepted schema, vector, or digest.

## Relationship to version two

[`founder-economy-simulator-v2.md`](founder-economy-simulator-v2.md) is not
edited, retracted, or reinterpreted. It states the contract the accepted M3.2
and M3.3 evidence proves, and `simulation/founder_economy_v2/` continues to
implement it unchanged.

Version two's versioning section fixes its event kinds, field sets, state shape,
custody-key format, journal buckets, digest labels, and error codes as immutable
for that version, and requires a new simulator schema and ADR for a changed
transition, field, or semantic rule. This version changes a transition's inputs,
the state shape, and the rejection set, so it is a new contract rather than an
edit — the rule ADR 0024 and ADR 0026 already established.

**Three things change. Nothing else does.**

| | v2 | v3 |
| --- | --- | --- |
| Seat record | `{ referrer_seat_id }` | `{ referrer_seat_id, activation_height }` |
| `activate_seat` | `seat_id`, `referrer_seat_id` | plus `activation_height` |
| Cycle window | supplied, unchecked | checked against the seat's schedule |
| Record seat set | any subset of activated seats | exactly the window's in-scope set |
| New failure codes | — | seven, listed below |

The referral, the exercise, the direct-issuance transition, the carry and its
conservation identity, the journal buckets, the channel table, the custody-key
format, the base legs, the activity threshold, the winner rule, the tie rule,
and the remainder rule are **identical** and are incorporated by reference
rather than restated. A reader who needs those rules reads version two.

### What is deliberately not re-versioned

`founder-economy-manifest-v2` is unchanged. No channel, cap, leg, denomination,
subtotal, beneficiary kind, seat capacity, per-person bound, or issuance-cycle
count moves, so the accepted manifest, its 2,267 canonical bytes, and its digest
`84cca09865b6c62bf09d3f6bc3821a2527c7a4835652cffdc0ebefa34b314ce5` are the same
artifact this version loads. A third loader for a byte-identical manifest would
be a third implementation of one accepted contract with nothing keeping the
three equal, so this version binds the accepted v2 manifest layer rather than
copying it.

`uptime-measurement-v1` is unchanged, and no version of it is required. The
`cycle_uptime_record` **shape** is identical: `cycle_window` remains a count and
`uptime_seconds` remains whole seconds bounded by `CYCLE_TARGET_SECONDS`. That
was the finding that fixed the slice order — a pipeline emitting whole hours is
a strict subset of the range version two already validates — and it holds here.
A record `uptime-measurement-v1` emits is accepted by this version unchanged.

`cycle-boundary-v1` is unchanged and is bound, not restated. This model holds no
second copy of the grid.

## Scope

Version three defines:

- the seat record's `activation_height` and the transition that records it;
- the cycle boundary check applied inside `evaluate_base_permission`;
- the in-scope seat set of a window and the completeness check derived from it;
- the resulting rejection set and its exact order; and
- the canonical state value and digests that follow from the changed state.

It does not define serialized consensus transaction bytes, receipt bytes, a
state-root schema, a block result, the transition that **authorizes** an
activation, the challenge construction that produces a measurement, the AI
dispute window, the definition of a month for the unreferred pool, the
distribution of that pool, or production direct-channel eligibility. Those
remain M3 and M4 work and are named in
[What this model does not establish](#what-this-model-does-not-establish).

## Bindings

This model binds two accepted artifacts and holds no second copy of either.

**The manifest layer.** The channel table, caps, base legs, denomination,
seat capacity, issuance-cycle count, referral amount, and cycle time constants
are read from the accepted `founder-economy-manifest-v2` contract. One
founder-directed value has one home.

**The window grid.** `window_of_height`, `first_cycle_window`,
`last_cycle_window`, `window_for_cycle`, `cycle_for_window`, and
`span_is_representable` are read from the accepted `cycle-boundary-v1` model.
The model asserts that its own view of `CYCLE_BLOCKS`, the activity threshold,
and the grace allowance equals that contract's, and that the contract's exact
derivation from the founder-directed seconds still holds, rather than holding a
second opinion about any of them.

There is no digest bind of a recorded cycle-boundary **state**, and that is
deliberate. `cycle-boundary-v1` takes an activation height as given and says so;
this model is the one that records it. Binding a foreign schedule would create a
second activation table that could disagree with the seat table this model
already holds, and the disagreement would be unrepresentable in a consensus
implementation where both are one chain state. The two are instead required to
agree by construction, and the verifier proves it by running the cycle-boundary
model over the same activation heights and requiring identical answers for every
checked window.

## Canonical bytes and digests

The construction is unchanged from version two:

```text
digest(label, value) = SHA-256( D(label) || jcs_bytes(value) )
```

The following labels are fixed for version three:

| Label | Preimage |
| --- | --- |
| `protocol-stack:founder-economy:manifest-v2` | the accepted manifest object |
| `protocol-stack:founder-economy:events-v3` | the parsed event array |
| `protocol-stack:founder-economy:state-v3` | the canonical state value |
| `protocol-stack:founder-economy:trace-v3` | the ordered trace records |
| `protocol-stack:founder-economy:result-v3` | the complete result object |
| `protocol-stack:founder-economy:uptime-record-v3` | one canonical uptime record |

The manifest label is inherited unchanged, because the manifest is the same
accepted artifact. Every other label ends in `-v3`, so no digest computed under
version one or two can be replayed as version three even where the preimage
shape coincides. The record label is versioned even though the record's shape is
not: the label versions the digest domain, not the schema, and the value a
version-two run bound must not satisfy a version-three binding.

### Heights are strings and windows are numbers

A block height is a `u64` and can exceed `MAX_JSON_INTEGER`, the largest integer
a conforming JSON stack represents exactly, so an `activation_height` is a
canonical unsigned decimal string matching `0` or `[1-9][0-9]*` wherever it
appears — in an event, in the state, and in a digest preimage. This is the rule
`cycle-boundary-v1` states and the same rule version two applies to monetary
values.

A cycle window is not, and the difference is derived rather than assumed:

```text
MAX_WINDOW = MAX_HEIGHT / CYCLE_BLOCKS = 640,511,947,003,803
           < MAX_JSON_INTEGER          = 9,007,199,254,740,991
```

Every window reachable from a representable height is therefore an exact JSON
number, with more than a factor of fourteen to spare. Windows stay JSON numbers
in the record, in a pending permission, and in the state, which keeps the
`cycle_uptime_record` shape byte-identical to the one `uptime-measurement-v1`
emits. The model records that inequality as a derived value rather than
asserting the rendering is safe.

This differs from `cycle-boundary-v1`, which renders windows as strings for
uniformity with heights. Neither rendering is wrong; this one is chosen because
holding the record shape fixed is worth more here than matching a neighbouring
model's state layout, and the bound above is what makes it safe.

## The seat record and activation

```text
seats[seat_id] = { referrer_seat_id: seat_id | none, activation_height: u64 }
last_activation_height = u64 | none
```

`activate_seat` gains one field, `activation_height`, and the state gains one
scalar. Activation still issues nothing, reserves nothing, credits nothing, and
emits an empty journal.

Rejection conditions, in this order:

1. `seat_id` outside `0..99,999` is `CYCLE_RANGE`.
2. An `activation_height` above `MAX_HEIGHT`, or whose complete 731-window span
   is not representable, is `HEIGHT_RANGE`.
3. A `referrer_seat_id` outside the bounds, or equal to `seat_id`, is
   `INVALID_REFERRER`.
4. An already-activated `seat_id` is `REPLAY`.
5. A `referrer_seat_id` that is not itself activated is `SEAT_NOT_ACTIVATED`.
6. An `activation_height` below `last_activation_height` is
   `HEIGHT_NOT_MONOTONIC`.

Conditions 1, 3, 4, and 5 keep version two's relative order exactly. Conditions
2 and 6 keep `cycle-boundary-v1`'s relative order exactly — a range failure
before a replay, and a replay before a monotonicity failure — so the two models
agree on which of two simultaneous defects is reported first. The vectors record
pairs carrying two defects at once to prove it.

### Why monotonicity is enforced here

`cycle-boundary-v1` states the reason and cannot enforce it, because it is not
the writer: a real activation executes inside the block that includes it, so an
activation height cannot decrease across the sequence a chain records. This model
is the writer, so a replayed, reordered, or fabricated activation must be unable
to install a schedule in the past and collect windows the seat did not hold.
Dropping the condition at the writing end would leave the containment stated in
one accepted artifact and applied in none.

Equal heights are accepted, because one block may activate several seats.

### What an activation height is not

It is a recorded input. Nothing here proves that a seat paid for a position,
enrolled, passed biometric verification, or is a distinct human, and nothing
here decides which transition supplies the height. The purchase-to-activation
gap is unchanged and remains M4.

## The cycle boundary check

`evaluate_base_permission` rejects a record whose `cycle_window` is not the
window for the supplied `cycle_index`:

```text
window_for_cycle(activation_height, cycle_index)
  = window_of_height(activation_height) + 1 + cycle_index
```

Rejection conditions, in `cycle-boundary-v1`'s order and with its codes:

1. A `cycle_window` below `first_cycle_window` is `WINDOW_BEFORE_ISSUANCE`.
2. A `cycle_window` above `last_cycle_window` is `WINDOW_AFTER_ISSUANCE`.
3. A `cycle_window` inside the span but not equal to `window_for_cycle` is
   `WINDOW_NOT_FOR_CYCLE`.

The three codes are not collapsed into one, for the reason `cycle-boundary-v1`
gives: a window before the span is a claim on issuance the seat had not begun, a
window after it is a claim on issuance that has ended, and a window inside the
span attached to the wrong cycle is an accounting error inside a live schedule.
Only the third indicates a defect in the caller rather than an out-of-bounds
request.

`cycle-boundary-v1`'s `SEAT_RANGE`, `CYCLE_RANGE`, and `SEAT_NOT_ACTIVATED`
conditions are not repeated: this transition already rejects all three earlier,
under version two's existing codes and order.

Once the check accepts, the evaluated seat is necessarily in scope for the
record's window, because `window_for_cycle(a, n) >= first_cycle_window(a)` for
every `n`. The model asserts that consequence rather than re-testing it.

## Record completeness

A record's seat set must be **exactly** the in-scope set of its window.

```text
in_scope(w) = { seat : first_cycle_window(seat.activation_height) <= w }
```

This is `uptime-measurement-v1`'s definition, unchanged: a seat is in scope for
window `w` when it was activated strictly before that window's first height. A
seat activated inside a window cannot have evidence for the whole window, which
is the same reason `cycle-boundary-v1` opens a seat's first cycle at the next
full window.

There is deliberately **no upper bound**. A seat whose own 731 windows have
ended is still in scope, still measured, and may still be a reallocation winner.
The Founder Constitution ends a seat's issuance period and keeps the seat
permanent and its node running, and the winner rule asks for the highest uptime
in the window rather than the highest uptime among seats still issuing. Bounding
the set at `last_cycle_window` would quietly narrow a founder-directed
population.

Rejection conditions, in this order:

1. A listed seat whose `first_cycle_window` is above the record's `cycle_window`
   is `SEAT_NOT_IN_SCOPE`.
2. An in-scope seat absent from the record is `INCOMPLETE_UPTIME_RECORD`.

They are two codes because they are two defects in opposite directions. An
omission shrinks the population a reallocation ranks over and can hand a failed
cycle's Founder portion to a seat that was not the best; an addition admits a
seat that has no evidence for the window and could make it the winner. A single
code would report both as the same event.

Condition 1 is stated per listed seat and is checked before condition 2, so a
record that both adds and omits a seat has one defined result. The vectors record
that pair.

### What this closes

`founder-economy-simulator-v2` records that "the winner set is computed over the
record supplied, and a record that omits seats is not detected", and
`uptime-measurement-v1` closes it only at the producing end, where an omission is
unrepresentable because the seat set is derived. Both directions are now closed:
the pipeline cannot emit an incomplete record, and this model cannot accept one.

The two ends derive the in-scope set from the same rule over the same activation
heights, which is what makes them agree. The verifier proves that agreement by
deriving one model's in-scope set and requiring the other to produce it, rather
than by both reading one implementation.

### What completeness is measured against

The in-scope set is derived from the seat table **as it stands when the
evaluation runs**. Membership itself is a function of the seat's activation
height and the window alone, so it does not drift; what the model cannot know is
whether a seat that will be in scope has not yet activated.

A chain closes that by ordering: a record is emitted only after its window is
final, which is at least two windows after every in-scope seat's activation
height has passed, so every such seat is already recorded. This model has no
current height for an evaluation and cannot require it.

`HEIGHT_NOT_MONOTONIC` narrows the gap rather than leaving it open. Once any
activation has been recorded at or above a window's first height, no later
activation can be in scope for that window, because a lower height is refused.
The residue is an event array that evaluates a window while every activation so
far still lies inside it — an ordering a chain does not produce and this model
does not reject. It is stated here rather than asserted away, and the vectors
record the narrowing as a derived property.

## Base permission evaluation

The complete ordered rejection set, with version two's conditions unchanged and
the new ones interleaved:

1. `seat_id` or `cycle_index` outside `0..99,999` and `0..730` is `CYCLE_RANGE`.
2. An unactivated seat is `SEAT_NOT_ACTIVATED`.
3. An already-evaluated key is `REPLAY`.
4. A `null` `cycle_uptime_record` is `MISSING_UPTIME_RECORD`.
5. A record failing any version-two validity condition is
   `INVALID_UPTIME_RECORD`.
6. A window outside or misfiled against the seat's schedule is
   `WINDOW_BEFORE_ISSUANCE`, `WINDOW_AFTER_ISSUANCE`, or `WINDOW_NOT_FOR_CYCLE`.
7. A listed seat not in scope for the window is `SEAT_NOT_IN_SCOPE`.
8. An in-scope seat absent from the record is `INCOMPLETE_UPTIME_RECORD`.
9. A record whose digest differs from the digest already bound to its
   `cycle_window` is `INCONSISTENT_UPTIME_RECORD`.
10. A leg that does not fit its channel is `CHANNEL_CAP`, and a checked
    intermediate outside `u64` is `ARITHMETIC_OVERFLOW`.

Everything after that is unchanged: the activity verdict, the winner set, the
carry, the legs, the journal, and the writes.

### Why the boundary and completeness checks precede the binding check

Conditions 6, 7, and 8 are properties of the record, the seat, and the schedule
alone. Condition 9 is a property of the run's history — whether some earlier
event already bound a different record to this window.

Ordering the intrinsic checks first means a record that is wrong on its own terms
is reported as wrong on its own terms, rather than as disagreeing with a correct
one. The alternative order would report a misfiled window as
`INCONSISTENT_UPTIME_RECORD` whenever the window happened to have been bound
already and as `WINDOW_NOT_FOR_CYCLE` otherwise, so the same defect would produce
two different codes depending on unrelated history. Both orders are
deterministic; only this one makes a code mean one thing.

A rejected event still binds nothing, so a defective record cannot occupy a
window and make a later correct record inconsistent with it.

## Simulator state

```text
seats[seat_id] = { referrer_seat_id: seat_id | none, activation_height: u64 }
last_activation_height       = u64 | none

channels[channel_id] = { issued_atomic:u64, outstanding_atomic:u64 }
pending_permissions[(seat_id, cycle_index)] = ordered legs
evaluated_permission_keys    = set<(seat_id, cycle_index)>
referral_accrual_keys        = set<(referred_seat_id, cycle_index)>
accepted_direct_decision_ids = set<decision identifier>
bound_uptime_records[cycle_window] = digest
typed_custody[custody_key]   = u64
performance_carry_atomic     = u64
```

Everything below the seat table is version two's state, unchanged.

### Canonical state value

```text
{
  "seats": {
    "{seat:05d}": {
      "referrer_seat_id": "{referrer:05d}" | null,
      "activation_height": s,
      "first_cycle_window": n,
      "last_cycle_window": n
    }
  },
  "last_activation_height": s | null,
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
boolean, and `t` a string.

A seat's span endpoints are derived from its activation height and are recorded
in the state anyway. That is not redundancy for its own sake: it puts the grid
inside the state digest, so a change to `CYCLE_BLOCKS` changes every state digest
rather than silently renumbering windows behind an unchanged one, and it lets a
reader check a pending permission's `cycle_window` against the seat's span
without replaying the run. Both endpoints are within `MAX_WINDOW` by the
`HEIGHT_RANGE` condition, so both are exact JSON numbers.

### Invariants

Version two's invariants hold unchanged. Three are added:

```text
every seat's activation_height is a u64 with a representable 731-window span
last_activation_height is present exactly when a seat is activated, and is
  the maximum recorded activation height
every pending permission's cycle_window equals
  window_for_cycle(seats[seat_id].activation_height, cycle_index)
```

The third is the enforced form of the gap version two records. It is asserted
over the whole pending set at every accepted state, not only at the event that
created the permission, so a defect that wrote a permission under one schedule
and then altered the schedule would fail rather than be reported.

## Canonical event input

Unchanged from version two except for one field:

| Kind | Additional fields |
| --- | --- |
| `activate_seat` | `seat_id`, `referrer_seat_id`, `activation_height` |
| `evaluate_base_permission` | `seat_id`, `cycle_index`, `cycle_uptime_record` |
| `accrue_referral` | `seat_id`, `cycle_index` |
| `exercise_permission` | `seat_id`, `cycle_index` |
| `direct_issue` | `channel`, `decision_id`, `beneficiary_id`, `amount_atomic`, `eligibility_result` |

`activation_height` is a canonical unsigned decimal string. A value that is not
one, including a JSON number, is an input-shape error that aborts the run rather
than a modelled rejection, in the same way version two treats a malformed
`amount_atomic`. A canonical string above `u64` is likewise an input-shape error;
`HEIGHT_RANGE` is reserved for a representable height whose span is not.

The single research placeholder is unchanged:
`direct_channel_eligibility_result`, bound to the exact action it authorizes.

## Result codes

Version two's codes, unchanged, plus seven:

```text
HEIGHT_RANGE              HEIGHT_NOT_MONOTONIC     WINDOW_BEFORE_ISSUANCE
WINDOW_AFTER_ISSUANCE     WINDOW_NOT_FOR_CYCLE     SEAT_NOT_IN_SCOPE
INCOMPLETE_UPTIME_RECORD
```

No code is removed.

Coverage is recorded as a derived claim rather than asserted, so a later change
cannot quietly lose a code or declare one no path reaches. The obligation was
added to `uptime-measurement-v1` after a declared-but-unreachable code was found
by self-review, and it applies here with one distinction that model did not need.

The declared set is partitioned. Every code except two must be produced by
executing an event array, and the vectors record the declared count, the
event-reachable count, the count actually produced, and their equality.
`ARITHMETIC_OVERFLOW` and `INVARIANT` are **guards**: every accumulated quantity
is bounded far below `u64` by a channel cap, so an overflow inside a transition
means the arithmetic is wrong rather than that the input was, and an invariant
failure means a transition wrote a state its own rules forbid. Neither is
reachable from an event array at any representable scale.

`uptime-measurement-v1` deleted its unreachable code because no path produced it
at all. These two are different: paths do produce them, and the vectors prove it
by exercising those paths directly rather than through a scenario. Deleting them
would remove a real check; declaring them reachable would claim coverage the
vectors could not show. The partition is what makes both statements true at once.

These are model result codes. The numeric consensus receipts for a C++ transition
are requirement 5 and are not defined here.

## Resource limits

The abstract ceiling is unchanged: 73,100,000 base evaluation keys and at most
73,100,000 referral accrual keys.

A base evaluation now performs **two** population-scale reads rather than one. It
iterates over its own record's entries, as version two does, and it derives the
window's in-scope set from the seat table. Both are bounded by the 100,000-seat
capacity rather than by the seat-cycle population, and both are reads. No
transition iterates over all cycles.

The seat table grows by one `u64` per seat, which is the 800,000-byte schedule
bound `cycle-boundary-v1` already records at full capacity. Bound window digests
still accumulate for the length of a run at one 32-byte value per distinct
referenced window, and this model still does not prune them, because pruning
needs the settlement and finality rules a consensus implementation will define.

## Versioning and compatibility

The schema strings, event kinds, field sets, research-input shape, uptime-record
shape, custody-key format, journal buckets, digest labels, error codes, and
rejection order are immutable for version three. A changed transition, field, or
semantic rule requires a new simulator schema and ADR.

Versions one, two, and three coexist. The v1 and v2 artifacts are the accepted
M2, M3.2, and M3.3 evidence and remain in place, passing, and unedited. Every
domain label differs, so no digest computed under one version can be replayed as
another.

`escrow-payout-v2` and `economy-scenario-suite-v2` still bind version two.
Rebinding them is the next milestone slice; until then, their recorded digests
remain evidence about the v2 contract and this document makes no claim about
them.

`uptime-measurement-v1` names the record shape it emits with the schema string
`protocol-stack/founder-economy-uptime-record/v2`. That string is unused by any
digest and still names the shape correctly, because this version does not change
it. It is not edited, so no accepted artifact of that specification moves.

Loading or running this model has no effect on an M1 account, fee pool, height,
transaction root, receipt, state root, SQLite database, ABCI response, or
CometBFT validator.

## What this model does not establish

Version two's limits hold except where explicitly closed above. Two of its seven
open items are now closed and the rest are unchanged:

- **The cycle boundary** — closed. The mapping from a seat's `cycle_index` to a
  `cycle_window` is defined by `cycle-boundary-v1` and applied here.
- **Record completeness** — closed at both ends.
- **The measurement itself** — open, and unchanged. Nothing here proves an
  `uptime_seconds` value reflects a real machine. `uptime-measurement-v1`
  specifies the challenge protocol and not the challenge content, so an answered
  challenge proves liveness of a responder rather than possession of a resource.
  The concrete resource commitment is founder-reserved.
- **What causes an activation** — open. A height is recorded, not earned.
- **The unreferred pool's distribution** — open. Accrual is modelled; the month
  definition and the payout are not.
- **Referral start conditions** — open. This model still requires activation.
- **Direct-channel eligibility and the AI funding framework** — open, and
  supplied as the single bound research placeholder.
- **Seat provenance** — open. A seat purchased in the Founder Seat sale model is
  still not proved to be an activated seat here, and the per-principal bound is
  still not a per-human bound.
- **Evaluation ordering** — open, and new. Completeness is measured against the
  seat table as it stands, and this model has no current height for an
  evaluation, so it cannot require that every in-scope seat has already
  activated. Monotonicity bounds the residue to an ordering a chain does not
  produce, as [What completeness is measured against](#what-completeness-is-measured-against)
  states.

Enforcing a schedule is not the same as proving one is right. This version proves
that a supplied window is the window the accepted grid assigns and that a record
covers the population the accepted schedule says was running. It proves nothing
about whether that population was operational, whether the duty reports behind a
measurement are complete, or whether the beacon that selected a challenge was
unbiasable. Those are the independent review requirements ADR 0027 and ADR 0028
record.

## Required vectors and evidence

`test-vectors/founder-economy-simulator-v3.txt`
is normative. It fixes this version's result schema and digest labels, the
inherited manifest digest, the height and window rendering bound, the seat
record and its derived span, every new rejection condition and its order, the
in-scope derivation, the complete trace, totals, custody, and digests of the
checked-in research scenario, and the agreement between this model and
`cycle-boundary-v1` over the same activation heights.

It must be reproduced by an executed verifier rather than by review alone. The
verifier independently derives, rather than restates, every recorded value. Its
independence is a `tools/founder-economy-v3-vectors/expected.py` that imports
nothing from `simulation/` and restates the Founder Constitution's tables and
thresholds and the pinned M1 commit interval by hand, so a value both sources
agree on has been reached from the founder documents and from the model
independently.

The verifier must also fail when a recorded key is never derived, when a derived
key is absent from the file, and when any recorded value is tampered with. A
vector that no derivation reaches is unverified, so partial coverage must not
report success.

Test coverage must include positive, negative, boundary, replay, overflow,
atomicity, ordering, cap-exhaustion, uptime-boundary, tie, carry,
empty-winner-set, record-binding, schedule-boundary, completeness, and complete
731-cycle scenarios, plus byte-identical digests across repeated runs. The
boundary cases that matter are a seat activated at exactly a window's first
height and at its last, the two windows immediately outside a seat's span, the
window one cycle away from the correct one, a record missing exactly one in-scope
seat, and a record carrying exactly one out-of-scope seat.

Acceptance requires full GitHub-hosted verification on the exact commit. Passing
these checks establishes exact accounting under an enforced schedule and a
complete record, not economic safety, measurement integrity, or production
readiness.
