# Uptime measurement v1

The Founder Constitution requires that "uptime must reach consensus without
trusting a founder's own machine," and names three layers: validator
participation and transaction servicing derived from on-chain records, resource
provision proved by challenge-response, and a bounded Ecosystem AI dispute
window whose expiry finalises a result without a signature.

This specification is that pipeline. It defines what a seat earns credit for,
how a challenge is selected and answered, what a dispute may assert and how far
it may reach, when a window's result becomes final, and the exact
`cycle_uptime_record` the pipeline produces.

It satisfies requirement 7 of `docs/project/first-goal.md` and the per-cycle
uptime-record part of requirement 12. The decisions and the alternatives
rejected are recorded in
[ADR 0028](../decisions/0028-uptime-measurement-pipeline.md).

## Scope

This specification measures. It settles no economic value.

In scope:

- the slot grid a window is subdivided into, and its exact correspondence to the
  founder-directed 24-hour, 18-hour, and 6-hour figures;
- the two evidence sources, and the mapping from the constitution's five
  components of "fully operational" onto them;
- challenge selection, its unpredictability, its timing, and the response
  deadline;
- the slot credit rule and its conjunctive, no-partial-credit form;
- the dispute window, what a dispute may assert, the bound on its reach, and
  finalisation by expiry;
- record completeness, which closes the gap
  [`founder-economy-simulator-v2`](founder-economy-simulator-v2.md) records that
  a record omitting seats ranks the seats it does list without that being
  detected; and
- the storage bound on per-cycle uptime records at 100,000 seats.

Explicitly not in scope:

- **the content of a challenge.** What a node must hold, compute, or serve to
  answer one is the concrete resource commitment. It sets what an operator must
  own in order to be paid, so it is a founder-reserved value belonging to the
  Founder Node and resource-network milestone. This specification defines the
  challenge *protocol* and treats the answer as an abstract predicate. What that
  costs is stated in
  [What this pipeline does not establish](#what-this-pipeline-does-not-establish).
- the deterministic active-set protocol that assigns validator duties. This
  specification consumes an assignment and never computes one.
- rebinding [`founder-economy-simulator-v2`](founder-economy-simulator-v2.md).
  Applying the check inside `evaluate_base_permission` changes a transition,
  which under the rule ADR 0024 and ADR 0026 established requires a new economy
  contract version rather than an edit. That is M3.6.
- the numeric consensus receipt codes and transaction encodings for a C++
  transition, which are requirement 5.

No accepted v1 or v2 artifact, vector, digest, C++ source, or devnet behavior is
changed by this specification.

## Determinism rules

Every quantity is a non-negative integer and every operation is integer
addition, subtraction, multiplication, comparison, or truncating division. There
is no floating point, no wall clock, no timestamp, no locale, and no mutable
external input.

A block height is the M1 ledger height defined in
[`ledger-transition-v1`](ledger-transition-v1.md). A window is the 28,800-height
span defined in [`cycle-boundary-v1`](cycle-boundary-v1.md). Neither is restated
here: this specification binds the cycle-boundary model rather than holding a
second copy of the grid.

No cryptographic primitive is implemented. Challenge selection uses the same
labelled digest construction the accepted models already use, over canonical
RFC 8785 bytes.

## Constants

| Name | Value | Source |
| --- | ---: | --- |
| `CYCLE_BLOCKS` | 28,800 | `cycle-boundary-v1` |
| `SLOTS_PER_WINDOW` | 24 | derived |
| `SLOT_BLOCKS` | 1,200 | derived |
| `ACTIVITY_THRESHOLD_SLOTS` | 18 | derived |
| `GRACE_ALLOWANCE_SLOTS` | 6 | derived |
| `SLOT_SECONDS` | 3,600 | derived |
| `RESPONSE_DEADLINE_BLOCKS` | 20 | selected |
| `CHALLENGEABLE_HEIGHTS_PER_SLOT` | 1,180 | derived |
| `CHALLENGE_PERIOD_BLOCKS` | 1,200 | selected |
| `DISPUTE_WINDOW_WINDOWS` | 1 | selected |
| `DISPUTE_CAP_SLOTS_PER_SEAT` | 6 | derived |
| `RETAINED_WINDOWS` | 2 | derived |
| `FOUNDER_SEAT_CAPACITY` | 100,000 | Founder Constitution |

### The slot grid is the constitution's own units

A window is subdivided into slots, and a slot is credited or it is not. The
grid is not an arbitrary granularity: at 24 slots a slot is exactly one hour,
and all three founder-directed figures are whole slots.

```text
SLOT_BLOCKS             = CYCLE_BLOCKS / SLOTS_PER_WINDOW     = 1,200
ACTIVITY_THRESHOLD_SLOTS = ACTIVITY_THRESHOLD_BLOCKS / SLOT_BLOCKS = 18
GRACE_ALLOWANCE_SLOTS    = GRACE_ALLOWANCE_BLOCKS / SLOT_BLOCKS    =  6
```

A cycle is met at 18 of 24 slots and fails when more than 6 are lost, which is
the constitution's rule stated in its own numbers rather than a re-derivation of
it. The model computes each quotient and requires a zero remainder rather than
trusting the arithmetic to have worked out, in the same way
`cycle-boundary-v1` does for the block grid.

Uptime converts to the units
[`founder-economy-simulator-v2`](founder-economy-simulator-v2.md) already
accepts, exactly and without changing that model's record shape:

```text
uptime_blocks  = credited_slots * SLOT_BLOCKS
uptime_seconds = uptime_blocks * TARGET_COMMIT_SECONDS
               = credited_slots * SLOT_SECONDS
               = credited_slots * 3,600
```

This is the finding that decided the slice order. `uptime_seconds` remains the
denomination of the record, so M3.6 rebinds the economy model to the cycle
boundary without also renaming a field, and one economy contract version carries
both changes rather than two carrying one each. A pipeline producing whole hours
is a strict subset of the `0..86,400` range that model already validates, so no
accepted validity condition is loosened.

### The 6-hour allowance is preserved, not re-interpreted

Losing a slot costs a whole hour, so an outage of one block and an outage of one
hour cost the same. That is the constitution's own rule rather than a penalty
added here: it states that a node "either runs with every component healthy or
it does not," that there is "no partial-credit mode," and that the allowance
exists so that "ordinary restarts, updates, and brief network faults do not
punish an honest operator." Six whole hours of allowance is what absorbs the
rounding. An operator may lose six slots outright and still meet the cycle.

The alternative — crediting partial slots — was rejected because it requires
evidence at a granularity the chain cannot supply for a node that holds no
validator duty in that period, so it would have to interpolate between two
probes and credit blocks no evidence covers.

## Bindings

This model binds two accepted artifacts and holds no second copy of either.

**The activation schedule.** The set of seats a window's record must cover is
derived from `cycle-boundary-v1`'s activation table. The model takes a recorded
cycle-boundary state, recomputes its
`protocol-stack:cycle-boundary:state-v1` digest, and rejects a state whose digest
does not reproduce with `INVALID_BOUND_SCHEDULE`. This is the one-way read
[`escrow-payout-v1`](escrow-payout-v1.md) established: the schedule is unchanged
by being read.

As that model records, recomputing a digest proves consistency and not
provenance — a self-consistent invented schedule would also bind. The verifier
closes that gap the same way, by running the cycle-boundary model on its own
accepted fixture and requiring this model's fixture to bind that exact run.

**The founder figures.** `CYCLE_BLOCKS`, the threshold, and the allowance are
read from the cycle-boundary contract, which in turn defers to
`founder-economy-manifest-v2`. Three tables holding the same founder-directed
constant can drift, so this one holds none of them independently.

## Evidence

The Founder Constitution enumerates five components that must be healthy at
once. The chain can observe two of them directly and the rest only through a
challenge. The mapping is stated rather than assumed:

| Constitution component | Evidence source |
| --- | --- |
| validator duties under the active-set protocol | on-chain duty report |
| transaction servicing | on-chain duty report |
| the full blockchain node | challenge-response |
| application compute, storage, caching, delivery | challenge-response |
| the workload and health agents | challenge-response |

The last three are not separately attested. A single challenge stands for all of
them, because answering one requires the node to be running, to hold what it
claims, and to serve it. What that does *not* establish is stated in
[What this pipeline does not establish](#what-this-pipeline-does-not-establish).

### On-chain duty evidence

A duty report names a seat, a kind, and whether the duty was performed. Reports
are produced by the chain from records it already keeps — votes, proposals, and
serviced transactions — so a report is an observation rather than a claim, needs
no attestation, and cannot be forged by the seat it concerns.

A report is only ever produced for a duty the seat was *assigned*. This is the
load-bearing consequence of a decided rule and not a convenience. The
constitution requires validator capability of every eligible Founder Node while
explicitly stating that this "does not require all 100,000 machines to vote on
every block," and that the protocol "must select and rotate a bounded live
signing set." A node outside the live signing set therefore produces no
validator evidence at all, through no fault of its own.

Crediting only seats that signed would fail every unselected seat in every slot
and redirect essentially the whole population's 342-unit Founder portion to the
small selected set, which is not a strict reading of the constitution but a
contradiction of it. A seat is therefore credited for the duties it was assigned,
and an empty assignment is satisfied vacuously. Continuous block-granular
evidence is a property a selected seat has and an unselected seat does not; the
challenge layer is what covers the unselected case.

### Challenge selection

At each height, every in-scope seat is independently selected or not by a
predicate over that height's beacon:

```text
selected(seat_id, height) =
    digest_int( CHALLENGE_LABEL, { beacon(height), seat_id } )
        mod CHALLENGE_PERIOD_BLOCKS  ==  0
```

`beacon(height)` is the canonical ledger state root at `height - 1`, which
`ledger-transition-v1` already defines as deterministic and which no participant
can compute before that block commits. A seat therefore learns it has been
challenged at most one block — three seconds — before it must begin answering,
so it cannot schedule uptime around its own audit.

`CHALLENGE_PERIOD_BLOCKS` equals `SLOT_BLOCKS`, so a seat expects exactly one
challenge per slot. That equality is the whole of the sampling-rate decision:
the rate is one probe per credited unit, which is the coarsest rate that
supplies evidence for every slot it credits.

Selection excludes the final `RESPONSE_DEADLINE_BLOCKS` heights of every slot,
leaving `CHALLENGEABLE_HEIGHTS_PER_SLOT = 1,180` challengeable heights. A
challenge and its deadline are therefore always inside one slot, which is what
makes per-slot state bounded and disposable at slot close rather than carried
across a boundary.

Selection is per seat and independent, so the number of seats challenged at a
height is a random variable with expectation
`FOUNDER_SEAT_CAPACITY / CHALLENGE_PERIOD_BLOCKS`, about 83 responses per block
at full capacity. That is a bounded, predictable load carried by the seats being
audited. It is not population-wide hidden work inside every transaction, which
the constitution forbids: an ordinary payment carries none of it. The
interaction between that expected load and block capacity is a resource bound
for the C++ transition slice, not a rule settled here.

### Response

A seat selected at height `h` must have a response recorded at a height in
`(h, h + RESPONSE_DEADLINE_BLOCKS]`. A response is attributed to the slot of its
*challenge* height, never of its inclusion height.

Twenty blocks is sixty seconds. It absorbs propagation and inclusion latency and
the brief faults the grace allowance exists for, while remaining far below a
slot, so a node cannot be absent for a slot and answer for it afterwards.

## Model state

```text
bound_schedule_digest : digest or absent
height                : the last executed height
window_bitmaps[window][seat_id]  : SLOTS_PER_WINDOW bits
slot_issued[seat_id]  : challenges issued to the seat in the open slot
slot_answered[seat_id]: those answered on time and correctly
pending[seat_id]      : challenge heights awaiting a response in the open slot
disputed[window][seat_id] : slots voided by a finalised dispute
finalised[window]     : whether the window's record is final
```

State is rendered canonically and digested under
`protocol-stack:uptime-measurement:state-v1`, with windows, seats, and slots in
ascending order so the digest covers the recorded evidence rather than the order
it arrived in. Heights are canonical decimal strings for the reason
`cycle-boundary-v1` gives: a `u64` height exceeds the largest integer a
conforming JSON stack represents exactly.

### Storage bound

Per seat: two per-slot counters and one bitmap per retained window.

```text
LIVE_SLOT_BYTES_PER_SEAT      = 2
WINDOW_BITMAP_BYTES_PER_SEAT  = SLOTS_PER_WINDOW / 8              = 3
RETAINED_WINDOWS              = 1 + DISPUTE_WINDOW_WINDOWS        = 2

FOUNDER_SEAT_CAPACITY * ( 2 + 2 * 3 ) = 800,000 bytes
```

Three properties make the bound hold rather than merely be computed. Challenge
selection is derived from the beacon on demand, so no issued challenge is
stored. A challenge and its deadline lie inside one slot, so the per-slot
counters are discarded at slot close and never accumulate. And a dispute records
a cleared bit in a bitmap that already exists rather than a new row, so the
dispute layer adds nothing.

The bound is per seat because nothing else scales with the population. A beacon
is the canonical state root of a block, which a node already holds as ledger
state, so recomputing selection from it costs no storage at all; only the open
slot's beacons are ever needed, because a response may not name a challenge from
a closed slot. The model discards them at slot close for the same reason.

This answers the per-cycle uptime-record part of requirement 12. Per-seat
balances and escrow recipient balances are unaffected and remain open.

## Transitions

Every input is a count, a canonical digest string, or a boolean where stated. A
value outside those domains is an input-shape error rather than a modelled
rejection, in the same way `cycle-boundary-v1` and
`founder-economy-simulator-v2` treat one.

### Bind schedule

Binds the activation table this model derives its in-scope seat set from. Reads
a recorded cycle-boundary state; writes `bound_schedule_digest`.

Rejection conditions, in this order:

1. An already-bound model is `REPLAY`.
2. A state whose recomputed `protocol-stack:cycle-boundary:state-v1` digest does
   not equal its recorded digest is `INVALID_BOUND_SCHEDULE`.

A seat is **in scope** for window `w` when its `first_cycle_window` is at most
`w` — equivalently, when it was activated strictly before the window's first
height. A seat activated inside a window cannot have evidence for the whole
window, and `cycle-boundary-v1` already opens a seat's first cycle at the next
full window for the same reason.

### Execute block

Advances the chain by one height, applies that height's duty reports, and closes
a slot or a window when the height reaches one. Reads and writes the live slot
state and the open window's bitmap.

Rejection conditions, in this order:

1. An unbound model is `SCHEDULE_NOT_BOUND`.
2. A `height` above `MAX_HEIGHT` is `HEIGHT_RANGE`.
3. A `height` that is not the successor of the last executed height is
   `HEIGHT_NOT_MONOTONIC`.
4. A duty report naming a seat outside `0..99,999` is `SEAT_RANGE`.
5. A duty report naming a seat not in scope for the open window is
   `SEAT_NOT_IN_SCOPE`.
6. A duty report of an unknown kind is `INVALID_DUTY_KIND`.
7. Two duty reports naming the same seat and kind at one height is
   `DUTY_REPLAY`.

A report with `performed = false` clears the seat's bit for the open slot. A
report with `performed = true` writes nothing, because a slot's bit begins set
and evidence only ever removes credit.

At the last height of a slot, every in-scope seat whose `slot_issued` exceeds
its `slot_answered` has its bit cleared, and both counters reset. At the last
height of a window, the window closes: its bitmap is retained for the dispute
window and a new bitmap opens with every in-scope seat's bits set.

### Submit response

Records a seat's answer to a challenge. Reads the beacon-derived selection;
writes `slot_answered` and `pending`.

Rejection conditions, in this order:

1. An unbound model is `SCHEDULE_NOT_BOUND`.
2. A `seat_id` outside `0..99,999` is `SEAT_RANGE`.
3. A seat not in scope for the open window is `SEAT_NOT_IN_SCOPE`.
4. A `challenge_height` outside the open slot is `CHALLENGE_NOT_OPEN`.
5. A `challenge_height` for which `selected(seat_id, challenge_height)` is false
   is `CHALLENGE_NOT_ISSUED`.
6. A response at a height above `challenge_height + RESPONSE_DEADLINE_BLOCKS`
   is `RESPONSE_TOO_LATE`.
7. A second response to the same challenge is `RESPONSE_REPLAY`.
8. A response whose answer predicate is false is `RESPONSE_INVALID`.

The slot check precedes the selection check because a beacon is discarded at
slot close, so a challenge from an earlier slot is no longer recomputable.
Reporting it as never issued would be false; it was issued and its slot is over.

Conditions 5 and 7 are the containment conditions. A seat cannot manufacture
credit by answering a challenge it was never issued, and cannot cover a missed
challenge by answering an issued one twice.

A response is carried by a block like any transaction, so its inclusion height
is the executed height at the time it is submitted. A slot therefore closes when
the first height of the next slot executes rather than at the end of its own
last height; closing eagerly would discard a response to the slot's last
challenge.

`RESPONSE_INVALID` is a rejection here and a lost slot at slot close, not a
separate penalty. A wrong answer and a missing answer cost the same, because the
credit rule counts answers rather than attempts.

### File dispute

Voids one slot of one seat in a closed, not yet finalised window. Reads the
retained bitmap; writes `disputed`.

Rejection conditions, in this order:

1. A signer other than the recorded Ecosystem AI key is `UNAUTHORIZED_DISPUTE`.
2. A `seat_id` outside `0..99,999` is `SEAT_RANGE`.
3. A `slot_index` outside `0..23` is `SLOT_RANGE`.
4. A window that has not closed is `WINDOW_NOT_CLOSED`.
5. A window already finalised is `DISPUTE_WINDOW_CLOSED`.
6. A seat not in scope for that window is `SEAT_NOT_IN_SCOPE`.
7. A slot already voided for that seat and window is `DISPUTE_REPLAY`.
8. A slot the seat was not credited for is `DISPUTE_SLOT_NOT_CREDITED`.
9. A seat already at `DISPUTE_CAP_SLOTS_PER_SEAT` void slots in that window is
   `DISPUTE_CAP_EXCEEDED`.

### The dispute may only subtract, and only this far

There is no transition by which a dispute adds credit. A compromised or captured
AI key can therefore reduce a result and never manufacture one, so the dispute
layer cannot mint, cannot move value to a chosen recipient, and cannot make a
failed node appear to have met a cycle.

The cap is the founder-directed grace allowance, and that choice is derived
rather than picked:

```text
SLOTS_PER_WINDOW - DISPUTE_CAP_SLOTS_PER_SEAT = 24 - 6 = 18
                                              = ACTIVITY_THRESHOLD_SLOTS
```

**A seat credited for every slot still meets its cycle after a maximal dispute.**
The AI can consume an operator's entire allowance and cannot, by itself, fail a
node that was fully operational. Failing a seat requires that the seat had
already lost at least one slot on its own evidence.

That is the containment the constitution asks for in the direction it asks for
it. It states that the AI's signature is deliberately not a precondition for
payment, because otherwise "an AI outage or a company decision would freeze
every Founder's income, which would make the company the effective owner of the
reward path." An unbounded void power would restore exactly that ownership
through a different door: a company able to zero any node's cycle at will holds
the reward path whether or not its signature is required. Bounding the reach at
the allowance closes both doors with one number the constitution already fixed.

A dispute names a reason code and is recorded. Reason codes are an audit trail
here and carry no protocol effect: every dispute inside the bounds has the same
effect on the result, so a mis-stated reason cannot change what is paid.

### Finalisation by expiry

A window `w` closes at the end of its last height. Its dispute window is the
whole of window `w + 1`. At the first height of window `w + 2` the record is
**final**, whether or not the Ecosystem AI was ever available.

`DISPUTE_WINDOW_WINDOWS = 1` reuses the existing grid instead of introducing a
second period, so finalisation is a window comparison rather than a new
threshold. It gives a reviewer one full day over a completed day, and delays a
seat's exercise of a cycle by at most two windows.

Silence finalises. No signature, liveness, quorum, or acknowledgement from the
AI is required at any point, so an outage of any length delays nothing and
withholds nothing.

### Emit record

Produces the `cycle_uptime_record` for a finalised window in exactly the shape
`founder-economy-simulator-v2` accepts. A pure query: it writes nothing.

Rejection conditions, in this order:

1. A window that is not final is `RECORD_NOT_FINAL`.
2. A window with no in-scope seats is `WINDOW_HAS_NO_SEATS`.

The record carries one entry per in-scope seat, ordered by ascending seat:

```text
uptime_seconds(seat) = ( credited slot bits not voided ) * SLOT_SECONDS
```

### Completeness

The record's seat set is **exactly** the in-scope set derived from the bound
schedule. A seat cannot be omitted, because the set is derived rather than
supplied, and cannot be added, because a seat outside the set has no bitmap.

This closes the gap `founder-economy-simulator-v2` and `cycle-boundary-v1` both
record. That model validates that every listed seat is activated but cannot know
which seats are missing, so a record listing three of a hundred seats yields a
winner set over those three. Here the omission is unrepresentable: the winner
set of a reallocation is taken over every seat the schedule says was running.

The model asserts this as an invariant on every emitted record rather than
trusting the construction, and the vectors derive the emitted seat set from the
schedule independently of the emitting code.

## Invariants

1. `credited_slots` is in `0..24` for every seat and window.
2. `uptime_seconds` is `credited_slots * 3,600` and never exceeds
   `CYCLE_TARGET_SECONDS`, so every emitted record satisfies
   `founder-economy-simulator-v2`'s containment condition by construction.
3. A slot bit is only ever cleared, never set, after a window opens. Evidence
   removes credit and never adds it.
4. Voided slots per seat per window never exceed `DISPUTE_CAP_SLOTS_PER_SEAT`.
5. A seat credited for every slot has `uptime_seconds` at or above
   `ACTIVITY_THRESHOLD_SECONDS` after any admissible set of disputes.
6. An emitted record's seat set equals the in-scope set for that window.
7. `slot_issued` and `slot_answered` are zero at every slot boundary.
8. Every arithmetic result is checked against the `u64` bound; an overflow is
   `ARITHMETIC_OVERFLOW` rather than a wrapped value.

Invariant 5 is the containment theorem stated as a checkable property, and the
model asserts it after every dispute rather than relying on the cap arithmetic
being right.

## Result codes

```text
ACCEPTED                   SEAT_RANGE                 SEAT_NOT_IN_SCOPE
SCHEDULE_NOT_BOUND         INVALID_BOUND_SCHEDULE     REPLAY
HEIGHT_RANGE               HEIGHT_NOT_MONOTONIC       INVALID_DUTY_KIND
DUTY_REPLAY                CHALLENGE_NOT_ISSUED       CHALLENGE_NOT_OPEN
RESPONSE_TOO_LATE          RESPONSE_REPLAY            RESPONSE_INVALID
UNAUTHORIZED_DISPUTE       SLOT_RANGE                 WINDOW_NOT_CLOSED
DISPUTE_WINDOW_CLOSED      DISPUTE_REPLAY             DISPUTE_SLOT_NOT_CREDITED
DISPUTE_CAP_EXCEEDED       RECORD_NOT_FINAL           WINDOW_HAS_NO_SEATS
ARITHMETIC_OVERFLOW
```

These are model codes. The numeric consensus receipts for a C++ transition are
requirement 5 and are not defined here.

## Versioning and compatibility

This is version one and supersedes no prior rule. `SLOTS_PER_WINDOW`,
`CHALLENGE_PERIOD_BLOCKS`, `RESPONSE_DEADLINE_BLOCKS`,
`DISPUTE_WINDOW_WINDOWS`, and `DISPUTE_CAP_SLOTS_PER_SEAT` are normative.

Changing `SLOTS_PER_WINDOW` re-denominates every credit and changes what a lost
slot costs, so it is a new version and a migration rather than a parameter
change. Changing `DISPUTE_CAP_SLOTS_PER_SEAT` above `GRACE_ALLOWANCE_SLOTS`
breaks invariant 5 and is refused by the model rather than accepted as a
configuration.

The schema strings, digest labels, result codes, and record shape are immutable
under this version. A change to any of them requires a new schema and an ADR.

## What this pipeline does not establish

- **That an answered challenge reflects a real machine holding real data.** The
  challenge protocol is defined and the challenge *content* is not. Until the
  resource commitment is decided, an answer proves that something able to
  produce it was reachable within sixty seconds, which is liveness of a
  responder rather than possession of a resource. Every anti-gaming claim in this
  specification is bounded by that. The commitment sets what an operator must
  own in order to be paid and is founder-reserved.
- **That sampling catches a dishonest node.** Selection is unpredictable and
  independent per height, so a seat down for `D` challengeable heights escapes
  with probability `(1 - 1/1200)^D`; a full lost slot is caught with probability
  about 0.63 and a full lost window with probability above 0.999999. Those are
  properties of the sampling rate, not proofs about an adversary, and the
  concrete security margin needs the independent review of requirement 15.
- **That duty reports are complete.** The model consumes reports and does not
  derive them. A chain that fails to report an assigned duty credits a seat that
  did not perform it.
- **That the beacon is unbiasable.** A proposer with influence over the state
  root at `h - 1` has some influence over who is challenged at `h`. The
  interaction between block production and challenge selection is the same
  adversary ADR 0027 already refers to independent review.
- **Anything about value.** No transition here issues, reserves, credits, or
  moves a unit. The pipeline produces a record; what an economy version does
  with one is M3.6.

## Vectors

`test-vectors/uptime-measurement-v1.txt` records derived values under stable
keys. Every recorded rejection is produced by a live model run over a minimally
mutated input rather than named, with a positive control asserting the unmutated
input is accepted. Coverage includes:

- the grid derivation and every zero-remainder requirement;
- the containment theorem at its boundary, including a maximal dispute against a
  perfect seat and the first cap-exceeding dispute;
- selection determinism, its per-slot expectation, and the excluded final
  heights of a slot;
- the deadline boundary at `h + 20` and `h + 21`;
- every result code, each produced by execution;
- record completeness against a schedule with seats in and out of scope; and
- replay, monotonicity, and restart equivalence under prefix replay.
