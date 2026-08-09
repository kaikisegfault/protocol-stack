# ADR 0027: The Founder Economy cycle boundary in chain heights

- Status: Accepted
- Date: 2026-08-09

## Context

The Founder Constitution grants each Founder Seat 731 eligible 24-hour-target
cycles beginning at that seat's first activation, and defers the mechanism: "a
chain-defined height or epoch rule must later represent the cycle
deterministically; local wall clocks cannot decide consensus." ADR 0023 repeated
the cycle boundary among the items M3 must specify separately.

Two accepted models have been built against that gap rather than around it.
`founder-economy-simulator-v2` made a `cycle_window` a separate field from a
seat's own `cycle_index` and recorded that it cannot check whether a supplied
window is the correct one for a seat's cycle. `economy-scenario-suite-v2` then
supplied the generator's tick as the window, which is a convention that happens
to be consistent rather than a rule anything enforces.

This ADR closes that gap. It is requirement 4 of `first-goal.md`.

## Decision

### A cycle is a fixed span of block heights on one global grid

```text
CYCLE_BLOCKS          = 28,800
window_of_height(h)   = h / CYCLE_BLOCKS
```

Window `w` is the inclusive height span `[w * 28,800, w * 28,800 + 28,799]`, and
window 0 begins at genesis height zero. Every seat is measured against the same
grid.

Three alternatives were considered.

**Wall-clock day boundaries taken from block timestamps** were rejected outright.
Requirement 4 forbids a wall clock reachable from a transition, and
`consensus-application-v1` already states that timing is not an application
response or canonical ledger state. Reading a proposer's timestamp would import
a value a proposer chooses into an issuance rule worth 574.3 units per cycle.

**Per-seat windows anchored at each seat's activation height** were rejected
because they delete a founder-directed rule. Performance reallocation sends a
failed cycle's 342-unit portion to the highest uptime "in that same cycle", so
the cycle has to name a period several seats can be compared over. If each
seat's windows start at its own activation, two seats share a window only when
their activation heights are congruent modulo 28,800, so essentially every
reallocation would compare a population of one — the failed seat, which cannot
win — the winner set would be empty, and the whole portion would carry forward
indefinitely. That is not a conservative reading of the rule; it is the rule not
running.

**Epochs signalled by validator-set changes**, in the style of chains that cut
epochs at membership transitions, were rejected because they make the length of
a Founder's issuance cycle depend on validator churn. A seat's 731 cycles would
take an unpredictable number of blocks, and an adversary able to influence
set changes would gain influence over issuance timing. Uniform length is worth
more here than alignment with the validator schedule.

The shared grid keeps both of the constitution's statements true. Seats
activated on different dates still have different issuance windows, because the
731-window *span* differs per seat; what does not differ is the grid the spans
are cut from.

### 28,800 blocks, because the founder thresholds divide it exactly

The count is derived from the 24-hour target and the pinned M1
`timeout_commit = "3s"`: 86,400 / 3 = 28,800.

The decisive property is that the same divisor is exact for all three
founder-directed figures:

```text
24 hours = 86,400 s -> 28,800 blocks
18 hours = 64,800 s -> 21,600 blocks
 6 hours = 21,600 s ->  7,200 blocks
```

so the 18-hour activity threshold is exactly 21,600 blocks and the fragmentable
6-hour allowance is exactly 7,200, with nothing rounded. A grid cut at an
interval that did not divide 86,400 would leave the threshold between two
blocks, and the rule would then have to be rounded toward the operator or
against them. Rounding a founder-directed threshold is a change to a
founder-directed value, which the standing delegation does not authorize, so
exactness was treated as a requirement rather than a convenience. The model
computes each quotient and requires a zero remainder rather than trusting the
arithmetic to have worked out.

The commit interval is an input to this derivation and never to a transition.
`CYCLE_BLOCKS` is the normative quantity: retargeting the commit interval later
changes how long a window takes in the world, not which window a height belongs
to or how many blocks it holds.

### A seat's cycles begin at the next full window

```text
first_cycle_window(a) = window_of_height(a) + 1
```

The alternative was to count the window the activation landed in as cycle 0. It
was rejected because activation lands at an arbitrary point inside a window. A
seat activated one block before a boundary would get a first cycle one block
long, could not reach the 18-hour threshold in it, would fail a cycle it was
never able to meet, and would have that cycle's 342-unit Founder portion
reallocated to other seats — a monetary penalty decided by where in a window a
transaction happened to be included. No founder direction authorizes that.

Beginning at the next full window gives every seat 731 complete windows on an
identical schedule, at a cost of at most one window of delay before issuance
opens. The constitution fixes how many cycles a seat receives and not the height
at which the first opens, so this is a choice inside the constitution rather
than a revision of it.

### Activation heights must not decrease

Recording an activation at a height below the most recently recorded activation
is rejected as `HEIGHT_NOT_MONOTONIC`. A real activation executes inside the
block that includes it, so the sequence of recorded activation heights on a
chain is non-decreasing by construction. Enforcing it means a replayed,
reordered, or fabricated activation cannot install a schedule in the past and
claim windows the seat did not hold. Equal heights are accepted, because one
block may activate several seats.

### Three rejection codes for a wrong window, not one

`WINDOW_BEFORE_ISSUANCE`, `WINDOW_AFTER_ISSUANCE`, and `WINDOW_NOT_FOR_CYCLE`
are distinct. A window before a seat's span is a claim on issuance that had not
begun, a window after it is a claim on issuance that has ended, and a window
inside the span attached to the wrong cycle index is an accounting error in a
live schedule. Only the third indicates a defect in the caller rather than an
out-of-bounds request, and collapsing them would put an expired seat and a
misfiled cycle in the same trace entry.

### The drift between a window and a day is stated, not hidden

28,800 blocks is 24 hours only when blocks commit at exactly 3 seconds. When
production runs slow a window spans more than 86,400 real seconds, and a node up
throughout it would have accumulated more wall-clock uptime than
`founder-economy-simulator-v2` accepts in a record, whose validity condition 5
caps `uptime_seconds` at `CYCLE_TARGET_SECONDS`.

The resolution is that a window's **nominal** duration is 86,400 seconds and a
measurement is a statement about a window rather than about a clock. Because the
divisions above are exact, an uptime denominated in the window's own blocks is
bounded by construction and converts to the constitution's seconds by
multiplication alone:

```text
uptime_seconds = uptime_blocks * 3,   0 <= uptime_blocks <= 28,800
```

This ADR defines that conversion and its bound. It does not define how a node
earns a block toward `uptime_blocks`, which is requirement 7 and M3.5. The
alternative — widening the economy model's containment bound to admit
wall-clock seconds — was rejected because it would make a record's validity
depend on how fast the chain happened to run, and would let a slow chain inflate
every node's measured uptime against a fixed threshold.

### The boundary is specified now and bound to the economy model later

Applying the check inside `evaluate_base_permission` adds a rejection condition,
requires the seat record to carry `activation_height`, and requires
`activate_seat` to accept a height. Under the rule ADR 0024 and ADR 0026
established — a changed transition is a new contract version, not an edit —
that is a new economy version and a separate slice. This slice defines the
predicate and its model; it modifies no accepted artifact.

## Consequences

- Requirement 4 of `first-goal.md` is satisfied. A cycle is a chain-defined
  quantity computable by any node from height alone, and no transition reaches a
  wall clock.
- `founder-economy-simulator-v2`'s recorded gap has a defined answer. The next
  economy version can reject a `cycle_window` that is not the window for a
  supplied `cycle_index`, and until it does, the gap remains recorded rather
  than closed.
- `economy-scenario-suite-v2`'s tick convention is now checkable against a rule
  instead of being self-consistent. It is not yet checked, because the suite
  binds the economy model rather than this one.
- The founder-directed activity threshold and grace allowance have exact block
  equivalents, 21,600 and 7,200, so M3.5 can define a measurement in blocks
  without renegotiating a constitutional figure.
- The purchase-to-activation gap is narrowed rather than closed. What a seat's
  schedule is, given an activation height, is now defined; what causes an
  activation height to be recorded remains M4.
- Requirement 12 is partly answered for the schedule alone: 800,000 bytes at
  full seat capacity, with no per-cycle row, because every window identifier is
  derived on demand.
- Nothing runnable changes. No C++, consensus, devnet, manifest, economy, seat,
  routing, escrow, or scenario artifact, vector, or digest is modified.

## Compatibility and independent review

This is version one and supersedes no prior rule. `CYCLE_BLOCKS` is the
normative constant; changing it would renumber every window and reassign every
seat's span, so it is a new version and a migration rather than a parameter
change.

The model is research software and activates nothing. Its result codes are model
codes; the numeric consensus receipts for a C++ transition are requirement 5 and
are not defined here.

Two claims in this ADR are design intent rather than proof and need independent
review before the boundary carries value. The first is that the grid is safe
against an adversary who can influence block production rate, since a chain
running slow stretches every window in real time while leaving the nominal
accounting fixed. The second is the interaction between this schedule and the
unbuilt measurement pipeline: the block-denominated conversion is exact, but
nothing yet proves that a block credited to a node reflects a real machine, and
ADR 0023 already records that an uptime scheme surviving adversarial founders
with physical machine access has not been reviewed.
