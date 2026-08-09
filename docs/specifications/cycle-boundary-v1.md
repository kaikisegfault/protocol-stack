# Cycle boundary v1

The Founder Constitution grants each Founder Seat 731 eligible 24-hour-target
cycles beginning with that seat's first activation, and states that "a
chain-defined height or epoch rule must later represent the cycle
deterministically; local wall clocks cannot decide consensus."

This specification is that rule. It defines the quantity a cycle is measured
in, the identifier two independent nodes compute for a cycle from chain height
alone, when a seat's issuance window opens, and the exact predicate that decides
whether a supplied window is the window for a supplied cycle index.

It satisfies requirement 4 of `docs/project/first-goal.md`. The decisions and
the alternatives rejected are recorded in
[ADR 0027](../decisions/0027-founder-cycle-boundary.md).

## Scope

This specification defines a schedule and a check. It does not measure
anything.

In scope:

- the block-height grid a cycle window is cut from;
- the window identifier and its inclusive height span;
- the mapping from a seat's activation height to its 731-window issuance span;
- the inverse mapping and the rejection conditions of the check
  `founder-economy-simulator-v2` records that it cannot make;
- the exact block-denominated equivalents of the founder-directed activity
  threshold and grace allowance; and
- the storage bound the schedule imposes at full seat capacity.

Explicitly not in scope:

- the uptime measurement itself. Nothing here observes a node, issues a
  challenge, records a response, or establishes that any seat was operational
  for any block. That is the pipeline named in requirement 7 and deferred to
  M3.5.
- the transition that authorizes an activation. This specification takes an
  activation height as given and defines what follows from it. Enrollment,
  payment proof, biometric identity, and the per-person bound remain M4.
- rebinding `founder-economy-simulator-v2`. Adding a rejection condition to
  `evaluate_base_permission` changes a transition, which under the rule ADR 0024
  and ADR 0026 established requires a new economy contract version rather than
  an edit. This specification defines the predicate that version will apply.

No accepted v1 or v2 artifact, vector, digest, C++ source, or devnet behavior is
changed by this specification.

## Determinism rules

Every quantity here is a non-negative integer and every operation is integer
addition, subtraction, multiplication, comparison, or truncating division. There
is no floating point, no wall clock, no timestamp, no locale, and no external
input.

A block height is the M1 ledger height defined in
[`ledger-transition-v1`](ledger-transition-v1.md): the initial state has height
zero, the only valid next height is `h + 1`, and height never decreases. A
height is a `u64`, so every derived quantity is checked against the `u64` bound
rather than assumed to fit.

The pinned M1 CometBFT configuration sets `timeout_commit = "3s"`, and
[`consensus-application-v1`](consensus-application-v1.md) states that timing is
not an application response or canonical ledger state. That commit interval is
therefore an input to the *derivation* of the constants below and never an input
to a transition. Nothing in this specification reads a clock.

## Constants

| Name | Value | Source |
| --- | ---: | --- |
| `GENESIS_HEIGHT` | 0 | `ledger-transition-v1` initial state |
| `TARGET_COMMIT_SECONDS` | 3 | pinned M1 `timeout_commit` |
| `CYCLE_TARGET_SECONDS` | 86,400 | Founder Constitution 24-hour target |
| `ACTIVITY_THRESHOLD_SECONDS` | 64,800 | Founder Constitution 18 hours |
| `GRACE_ALLOWANCE_SECONDS` | 21,600 | Founder Constitution 6 hours |
| `CYCLE_BLOCKS` | 28,800 | derived |
| `ACTIVITY_THRESHOLD_BLOCKS` | 21,600 | derived |
| `GRACE_ALLOWANCE_BLOCKS` | 7,200 | derived |
| `ISSUANCE_CYCLES_PER_SEAT` | 731 | Founder Constitution |
| `FOUNDER_SEAT_CAPACITY` | 100,000 | Founder Constitution |
| `MAX_HEIGHT` | 18,446,744,073,709,551,615 | `u64` bound |

The three seconds figures are the same founder-directed values
`founder-economy-simulator-v2` already fixes. This specification restates them
only to derive their block equivalents, and the model asserts that its own
copies equal the economy contract's rather than holding a second opinion.

### The derivation and its exactness

```text
CYCLE_BLOCKS             = CYCLE_TARGET_SECONDS        / TARGET_COMMIT_SECONDS
                         = 86,400 / 3 = 28,800
ACTIVITY_THRESHOLD_BLOCKS = ACTIVITY_THRESHOLD_SECONDS / TARGET_COMMIT_SECONDS
                         = 64,800 / 3 = 21,600
GRACE_ALLOWANCE_BLOCKS   = GRACE_ALLOWANCE_SECONDS     / TARGET_COMMIT_SECONDS
                         = 21,600 / 3 =  7,200
```

All three divisions are exact. That is a property of the chosen grid, not a
coincidence to rely on silently, so the model computes each quotient and
requires a zero remainder, raising `INVARIANT` otherwise. The two identities the
economy contract already states are preserved in blocks:

```text
ACTIVITY_THRESHOLD_BLOCKS + GRACE_ALLOWANCE_BLOCKS = CYCLE_BLOCKS
ACTIVITY_THRESHOLD_BLOCKS * TARGET_COMMIT_SECONDS  = ACTIVITY_THRESHOLD_SECONDS
```

Exactness is what makes the grid usable. A block count converts to the
constitution's seconds by multiplication alone, so the founder-directed 18-hour
threshold is exactly 21,600 blocks with nothing rounded in either direction.
Had the grid been cut at a commit interval that did not divide 86,400, the
threshold would have landed between two blocks and the rule would have had to be
rounded — toward the operator or against them — which is a change to a
founder-directed value and is not available to this specification.

**This is a denomination identity, not a measurement.** It states what a block
count means in the constitution's units. It does not state that any seat was
operational for any block, and nothing here can.

## The window grid

Cycle windows are cut from a single global grid of fixed-length height spans
shared by every seat:

```text
window_of_height(h)   = h / CYCLE_BLOCKS          (truncating division)
window_first_height(w) = w * CYCLE_BLOCKS
window_last_height(w)  = w * CYCLE_BLOCKS + CYCLE_BLOCKS - 1
```

Window `w` is the inclusive height span
`[window_first_height(w), window_last_height(w)]`, which contains exactly
`CYCLE_BLOCKS` heights. Window 0 begins at `GENESIS_HEIGHT`. Every height
belongs to exactly one window, and `window_of_height(window_first_height(w))`
is `w` for every representable `w`, both of which the vectors record.

### Why one shared grid

Reallocation is the constraint. The Founder Constitution sends a failed cycle's
342-unit Founder portion to the node with "the highest cumulative fully
operational uptime **in that same cycle**", so "that same cycle" must name a
period several seats can be compared over.

A per-seat grid anchored at each seat's own activation would make almost no two
seats share a window. Every reallocation would then be a comparison over a
population of one — the failed seat itself, which by construction cannot win —
so the winner set would be empty for essentially every failure and the whole
342-unit portion would carry forward forever. That is not a smaller version of
the founder-directed rule; it silently deletes it.

A shared grid also keeps the constitution's other statement true. "Seats
activated on different dates therefore have different issuance windows" is
satisfied by the *span* differing per seat, not by the grid differing: two seats
activated a month apart have different first and last cycle windows while still
being comparable in every window they overlap in.

### What a window's duration is and is not

A window is exactly `CYCLE_BLOCKS` heights. Its duration in real time is
`CYCLE_BLOCKS` multiplied by the mean commit interval actually achieved, which
is 24 hours only when that mean is exactly `TARGET_COMMIT_SECONDS`. This is why
the Founder Constitution says 24-hour-**target** cycle rather than 24-hour
cycle, and the target is the part this specification implements.

The consequence is real and is stated rather than smoothed over: when block
production runs slow, a window spans more than 86,400 real seconds. A
measurement expressed in raw wall-clock seconds could then exceed
`CYCLE_TARGET_SECONDS` for a node that was up throughout, which
`founder-economy-simulator-v2` rejects as a malformed record under its validity
condition 5.

That rejection is correct and the grid is not what must change. A window's
**nominal duration** is `CYCLE_TARGET_SECONDS`, and a measurement is a statement
about the window rather than about a wall clock, so the measurement pipeline must
report uptime against the nominal duration. The exact conversion is available
because the divisions above are exact:

```text
uptime_seconds = uptime_blocks * TARGET_COMMIT_SECONDS,  0 <= uptime_blocks <= CYCLE_BLOCKS
```

An uptime denominated in the window's own blocks is bounded by construction, is
derived from records the chain already holds, and converts to the constitution's
seconds without rounding. This specification defines that conversion and its
bound. It does not define how a node earns a block toward `uptime_blocks`, which
is exactly the open work in requirement 7 and is named again under
[What this specification does not establish](#what-this-specification-does-not-establish).

## A seat's issuance span

A seat's schedule is fixed by one recorded quantity, its `activation_height`:

```text
first_cycle_window(a) = window_of_height(a) + 1
window_for_cycle(a, n) = first_cycle_window(a) + n,   0 <= n <= 730
last_cycle_window(a)  = first_cycle_window(a) + ISSUANCE_CYCLES_PER_SEAT - 1
```

A seat's 731 cycles are therefore the 731 consecutive windows beginning with the
first window that starts **after** its activation height.

### Why the next full window rather than the activating one

Activation lands at an arbitrary point inside a window. Counting that partial
remainder as the seat's cycle 0 would give a seat activated one block before a
window boundary a first cycle of one block, in which reaching the 18-hour
threshold is impossible. The seat would fail a cycle it was never able to meet,
and its 342-unit Founder portion would be reallocated to other seats, purely
because of where in a window its activation transaction happened to be included.

That is a monetary penalty imposed by block placement, which no founder
direction authorizes. Beginning at the next full window gives every seat 731
complete windows, so the schedule is identical for every seat regardless of when
it activated and the founder-directed 731 is 731 real opportunities rather than
730 plus a fragment.

The cost is bounded and is at most one window of delay before issuance begins.
The Founder Constitution fixes the number of cycles a seat receives and not the
height at which the first one opens, so this is a specification choice within
the constitution rather than a change to it.

### Range and overflow

`activation_height` is a `u64`. A window identifier must itself be addressable,
meaning its own first and last heights are representable, which bounds windows
by

```text
MAX_WINDOW = MAX_HEIGHT / CYCLE_BLOCKS = 640,511,947,003,803
```

A seat's span is representable only when its whole span stays inside that bound:

```text
last_cycle_window(a) <= MAX_WINDOW
```

An activation height failing this is rejected rather than wrapped, because a
wrapped window would silently alias another seat's schedule. The condition is
unreachable at any plausible height — the grid represents 876,213,333,794
back-to-back 731-window seat spans — so it is a guard proved present rather than
one expected to fire. It is still computed with checked arithmetic and is
exercised directly by tests, in the same way the economy model exercises
`ARITHMETIC_OVERFLOW`.

## Model state

The model holds a seat table and the height of the most recent activation:

```text
activation_heights[seat_id] = height
last_activation_height      = height or absent
```

State is rendered canonically and digested under the label
`protocol-stack:cycle-boundary:state-v1`, with seats ordered by ascending
identifier so the digest is over the recorded schedule rather than the order
activations happened to arrive in.

Heights and window identifiers are canonical unsigned decimal strings rather
than JSON numbers. A `u64` height exceeds 9,007,199,254,740,991, the largest
integer a conforming JSON stack represents exactly, so rendering one as a number
could not be canonicalized safely. This is the same rule
`founder-economy-simulator-v2` applies to monetary values, for the same reason.
Seat identifiers, cycle indices, and block counts stay JSON numbers because each
is bounded well inside that range.

### Storage bound

One `u64` per activated seat:

```text
FOUNDER_SEAT_CAPACITY * 8 bytes = 800,000 bytes
```

The schedule needs nothing else. `first_cycle_window`, `last_cycle_window`, and
every one of a seat's 731 window identifiers are derived from the activation
height on demand, so no per-cycle row is stored and the bound is independent of
how far through its issuance span a seat has progressed. This is a partial
answer to requirement 12, covering the schedule only; per-seat balances,
per-cycle uptime records, and recipient balances are unaffected and remain open.

## Transitions

### Record activation

Records `activation_height` for a seat. Reads the seat table and
`last_activation_height`; writes one entry and updates
`last_activation_height`.

Rejection conditions, in this order:

1. `seat_id` outside `0..99,999` is `SEAT_RANGE`.
2. `height` above `MAX_HEIGHT`, or whose `last_cycle_window(height)` is not
   representable, is `HEIGHT_RANGE`.
3. An already-activated `seat_id` is `REPLAY`.
4. A `height` below `last_activation_height` is `HEIGHT_NOT_MONOTONIC`.

Condition 4 is a consensus property rather than tidiness. A real activation
executes inside the block it is included in, so the activation height is the
executing block's height and cannot decrease across the sequence of activations
a chain records. Enforcing it here means a replayed, reordered, or fabricated
activation cannot quietly install a schedule in the past and collect windows the
seat did not hold. Equal heights are accepted, because a single block may
activate several seats.

Ordering matters and is fixed: an out-of-range seat identifier is reported
before an out-of-range height, and a replayed seat is reported before a
non-monotonic height, so a request carrying two defects has one defined result.
The vectors record pairs carrying two defects at once to prove which condition
reports first.

Recording an activation issues nothing, reserves nothing, and credits nothing.

### Check window

Decides whether `cycle_window` is the window for `(seat_id, cycle_index)`. This
is a pure query: it reads the seat table and writes nothing.

Rejection conditions, in this order:

1. `seat_id` outside `0..99,999` is `SEAT_RANGE`.
2. `cycle_index` outside `0..730` is `CYCLE_RANGE`.
3. A seat with no recorded activation height is `SEAT_NOT_ACTIVATED`.
4. A `cycle_window` below `first_cycle_window` is `WINDOW_BEFORE_ISSUANCE`.
5. A `cycle_window` above `last_cycle_window` is `WINDOW_AFTER_ISSUANCE`.
6. A `cycle_window` inside the span but not equal to `window_for_cycle` is
   `WINDOW_NOT_FOR_CYCLE`.

Otherwise the check accepts.

Conditions 4, 5, and 6 are deliberately three codes rather than one. They are
different failures: a window before the span is a claim on issuance the seat had
not yet begun, a window after it is a claim on issuance that has ended, and a
window inside the span but attached to the wrong cycle index is an accounting
error within a live schedule. A single code would collapse an expired seat and a
misfiled cycle into the same trace entry, and the second is the one that
indicates a defect in a caller rather than an out-of-bounds request.

### The inverse

`cycle_for_window(a, w)` returns `w - first_cycle_window(a)` when that
difference is within `0..730`, and no cycle otherwise. It is a total function on
the accepted domain and is the exact inverse of `window_for_cycle` there, which
the vectors record as a round trip over every one of a seat's 731 cycles rather
than at the endpoints alone.

## What this closes for the economy model

`founder-economy-simulator-v2` records under
[What this model does not establish](founder-economy-simulator-v2.md) that "the
mapping from a seat's `cycle_index` to a `cycle_window` is not defined or
checked". The predicate above is that mapping, and a later economy version
applies it by adding one rejection condition to `evaluate_base_permission`:

```text
cycle_uptime_record.cycle_window != window_for_cycle(activation_height, cycle_index)
```

Two things must change in that version, and naming them here is part of
defining the boundary. The seat record must carry `activation_height`, which it
does not today, and `activate_seat` must accept a height. Both are additions to
a transition's inputs and state, so that version is a new contract rather than an
edit, on exactly the grounds ADR 0024 and ADR 0026 already established.

This specification does not make that change and does not modify
`simulation/founder_economy_v2/`, whose accepted vectors and digests are
unchanged.

## Versioning and compatibility

This is version one of the cycle boundary and supersedes nothing. There is no
prior rule to be compatible with, because the mapping did not exist.

`CYCLE_BLOCKS` is the normative quantity. `TARGET_COMMIT_SECONDS` is how it was
derived and is not itself consensus state, so a later change to the pinned
commit interval changes how long a window takes in the world and does not change
how many blocks it contains or which window a height belongs to. A chain that
retargets its commit interval keeps every window identifier and every seat
schedule it had already computed, and gains a drift between nominal and real
duration that the measurement pipeline must absorb under the nominal-duration
rule above.

Changing `CYCLE_BLOCKS` itself is a different matter: it would renumber every
window and reassign every seat's span, so it is a new version of this
specification and a migration, not a parameter change.

Loading or running this model has no effect on an M1 account, fee pool, height,
transaction root, receipt, state root, SQLite database, ABCI response, or
CometBFT validator, and no effect on any accepted economy, seat, routing,
escrow, or scenario artifact.

Error codes here are model result codes. The numeric consensus receipts for a
C++ transition are requirement 5 and are not defined here.

## What this specification does not establish

- **That any seat was operational for any block.** The grid says how many blocks
  a window contains and what a block count means in the constitution's seconds.
  It observes nothing. The challenge construction, sampling rate, dispute window
  length, and dispute resolution that would produce an `uptime_blocks` value
  remain unspecified and are requirement 7.
- **Record completeness.** Nothing here makes a window's uptime record list
  every seat that held that window, and the economy model's winner set is still
  computed over the record it is given.
- **What causes an activation.** The model takes a height and records it. Which
  transition supplies that height, and under what payment, enrollment, and
  biometric preconditions, is M4. The purchase-to-activation gap is therefore
  narrowed to exactly that question and is not closed: a seat purchased in
  `founder-seat-schedule-v1` is still not proved to be an activated seat here.
- **That the real duration of a window is 24 hours.** It is 24 hours at the
  target commit interval and drifts with actual block production. The nominal
  duration rule above states how a measurement must be denominated so that drift
  cannot corrupt an accounting rule; it does not bound the drift itself.
- **The unreferred pool's month.** ADR 0023 leaves the definition of a month in
  cycles open. A month is presumably a whole number of windows now that a window
  is defined, but which number, and how the 731-cycle span divides into months,
  is a founder-reserved question this specification does not answer.

## Required vectors and evidence

[`cycle-boundary-v1.txt`](../../test-vectors/cycle-boundary-v1.txt) is
normative. It fixes the constants and the exactness of their derivation, the
grid's height spans and its window round trip, the seat schedule for activation
heights at and around window boundaries, the complete 731-window span of a seat
including both endpoints and the round trip across every cycle in it, every
rejection condition and its order, the storage bound, and the state digest of a
recorded scenario.

It must be reproduced by an executed verifier rather than by review alone. The
verifier independently derives, rather than restates, every recorded value. Its
independence is a `tools/cycle-boundary-vectors/expected.py` that imports
nothing from `simulation/` and restates the Founder Constitution's 24, 18, and 6
hours and the pinned M1 commit interval by hand, so a value both sources agree
on has been reached from the founder document and from the model independently.

The verifier must also fail when a recorded key is never derived, when a derived
key is absent from the file, and when any recorded value is tampered with. A
vector that no derivation reaches is unverified, so partial coverage must not
report success.

Test coverage must include positive, negative, boundary, replay, ordering,
overflow, and complete-span scenarios, plus byte-identical digests across
repeated runs. The boundary cases that matter are the last height of a window
and the first height of the next, a seat activated at exactly a window's first
height, and the two windows immediately outside a seat's span.

Acceptance requires full GitHub-hosted verification on the exact commit. Passing
these checks establishes an exact, deterministic, wall-clock-free schedule and
the check that enforces it. It establishes nothing about measurement.
