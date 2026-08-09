# ADR 0028: The uptime measurement pipeline

- Status: Accepted
- Date: 2026-08-09

## Context

The Founder Constitution decides what uptime *is worth* — a cycle is met at 18
hours of cumulative fully operational uptime with a fragmentable 6-hour
allowance, and a failed cycle's 342-unit Founder portion goes to the highest
uptime in the same cycle — and defers how uptime is *established*, naming three
layers and stating that "the exact challenge construction, sampling rate,
dispute window length, dispute resolution, and settlement bounds require a
specification and independent review."

`founder-economy-simulator-v2` derives the activity verdict and the winner set
from a cycle uptime record, and records that the record is an abstract input:
nothing proves an `uptime_seconds` value reflects a real machine, and a record
omitting seats yields a winner set over the seats it does list without that
being detected. ADR 0027 fixed the window the measurement is taken over and the
exact conversion `uptime_seconds = uptime_blocks * 3`, and explicitly deferred
how a node earns a block.

This ADR decides that. It is requirement 7 of `first-goal.md` and the per-cycle
uptime-record part of requirement 12.

## Decision

### Credit is per slot, and a slot is one hour

A window is subdivided into 24 slots of 1,200 blocks. A slot is credited whole
or not at all.

```text
SLOT_BLOCKS              = 28,800 / 24 = 1,200
ACTIVITY_THRESHOLD_SLOTS = 21,600 / 1,200 = 18
GRACE_ALLOWANCE_SLOTS    =  7,200 / 1,200 =  6
uptime_seconds           = credited_slots * 3,600
```

24 slots is the granularity at which the constitution's own figures — 24 hours,
18 hours, 6 hours — are whole slots. The rule is then applied in the units it
was written in rather than re-derived into a finer denomination the founder
never chose.

The conversion lands exactly on the units `founder-economy-simulator-v2` already
validates. This is why M3.5 precedes M3.6: had the economy model been rebound to
the cycle boundary first, and the measurement then denominated in blocks, the
record's shape would have changed twice and two economy contract versions would
have been spent where one does. The record's shape is now confirmed stable, so
M3.6 carries the boundary check and the activation height in one version.

**Rejected: crediting partial slots.** It requires evidence at a granularity the
chain cannot supply for a node holding no validator duty in the period, so it
would interpolate between two probes and credit blocks no evidence covers. The
coarseness is paid for by the founder-directed allowance, which is six whole
slots: an operator may lose six outright and still meet the cycle. The
constitution states there is "no partial-credit mode" for a node's health, so
crediting a fraction of a slot would also contradict it directly.

### A seat is credited for the duties it was assigned, not for signing

Validator participation and transaction servicing are derived from on-chain
records, and a report is only ever produced for a duty the seat was assigned. An
empty assignment is satisfied vacuously.

This follows from a decided rule rather than being a lenience. The constitution
requires validator capability of every eligible Founder Node while stating that
this "does not require all 100,000 machines to vote on every block," and that
the protocol "must select and rotate a bounded live signing set." A node outside
the live set produces no validator evidence at all.

**Rejected: crediting only seats that signed.** It fails every unselected seat
in every slot, so essentially the whole population fails every cycle and the
whole population's Founder portion is reallocated to the small selected set.
That is not a strict reading of the constitution; it is a contradiction of the
sentence that bounds the signing set, and it would silently convert a
distribution rule into a concentration rule.

### Challenges are selected per height from a beacon nobody can predict

```text
selected(seat, height) =
    digest_int( label, { beacon(height), seat } ) mod 1,200 == 0
```

`beacon(height)` is the canonical state root at `height - 1`. A seat learns of
its challenge at most one block — three seconds — before it must answer, so it
cannot schedule uptime around its own audit. No cryptographic primitive is
introduced: this is the labelled digest construction the accepted models already
use over canonical bytes.

**The sampling rate is one probe per credited unit.** `CHALLENGE_PERIOD_BLOCKS`
equals `SLOT_BLOCKS`, so a seat expects exactly one challenge per slot. That is
the coarsest rate supplying evidence for every slot it credits, and it fixes the
population load at about 83 responses per block at full capacity — carried by
the seats being audited, not by every transaction, which is the bound the
constitution places on this choice.

**Rejected: a fixed per-seat probe schedule.** Deriving each seat's probe heights
once per window or once per slot makes them known in advance, and a node that
knows its audit times can be operational only at them.

**Rejected: proving every block.** Per-block proof for 100,000 seats is 28,800
times the traffic and is the population-wide hidden work the constitution
forbids.

Selection excludes the final 20 heights of a slot, so a challenge and its
60-second deadline always lie inside one slot. That is what makes the per-slot
state disposable at the slot boundary and the storage bound hold.

### The dispute may only subtract, and only up to the grace allowance

The Ecosystem AI may void a slot in a closed window. There is no transition by
which a dispute adds credit, so a captured key can reduce a result and never
manufacture one: it cannot mint, cannot direct value to a chosen recipient, and
cannot make a failed node appear to have met a cycle.

The reach is capped at 6 slots per seat per window, which is the founder-directed
grace allowance, and the cap is therefore derived rather than picked:

```text
24 - 6 = 18 = ACTIVITY_THRESHOLD_SLOTS
```

**A seat credited for every slot still meets its cycle after a maximal dispute.**
The AI can consume an operator's whole allowance and cannot by itself fail a
fully operational node.

This is the constitution's own containment argument applied in the second
direction. It requires that the AI's signature not be a precondition for
payment, because otherwise "an AI outage or a company decision would freeze every
Founder's income, which would make the company the effective owner of the reward
path." An unbounded void power restores exactly that ownership through a
different door — a company able to zero any node's cycle at will owns the reward
path whether or not its signature is required. One number the constitution
already fixed closes both doors.

**Rejected: an uncapped dispute.** It reintroduces company ownership of the
reward path.

**Rejected: a dispute that must be adjudicated before a result stands.** It
makes payment depend on AI liveness, which the constitution refuses.

### Silence finalises after one window

A window's dispute period is the whole of the following window; at the start of
the window after that, the result is final regardless of AI availability. Reusing
the existing grid makes finalisation a window comparison rather than a second
period with its own boundary conditions, and delays a seat's exercise of a cycle
by at most two windows.

### Completeness is derived, not validated

A record's seat set is the in-scope set derived from the bound activation
schedule — every seat activated strictly before the window's first height. An
omission is unrepresentable rather than detected, because the set is derived
rather than supplied.

This closes the gap `founder-economy-simulator-v2` and ADR 0027 both record. That
model validates that every listed seat is activated, which cannot tell it which
seats are missing, so a record listing three of a hundred seats produces a
winner set over those three.

The model binds `cycle-boundary-v1`'s state by recomputing its digest, the
one-way read ADR 0021 established for escrow. As there, recomputing a digest
proves consistency and not provenance, and the verifier closes that gap by
running the cycle-boundary model on its own fixture and requiring this model's
fixture to bind that exact run.

### Storage is bounded at 800,000 bytes

```text
100,000 seats * ( 2 counter bytes + 2 retained windows * 3 bitmap bytes )
```

Three properties make the bound hold rather than merely be computed: selection
is derived on demand so no issued challenge is stored, a challenge and its
deadline lie inside one slot so the counters are discarded at slot close, and a
dispute clears a bit in a bitmap that already exists rather than adding a row.

## Consequences

- Requirement 7 of `first-goal.md` is satisfied as a specification and a model.
  The three layers the constitution names are defined, and the AI cannot freeze
  or seize the reward path in either direction.
- The per-cycle uptime-record part of requirement 12 is answered at 800,000
  bytes. Per-seat balances and escrow recipient balances remain open.
- `founder-economy-simulator-v2`'s record shape is confirmed stable, so M3.6 is
  one economy version carrying the cycle-boundary check and the activation
  height rather than two.
- The record's completeness gap is closed at the producing end. The economy
  model still cannot detect an omission in a record it is handed; it will no
  longer be handed one, and M3.6 is where the two ends meet.
- A new founder-reserved item is recorded rather than invented: the concrete
  resource commitment a Founder Node must prove it holds. It sets what an
  operator must own in order to be paid and belongs to the Founder Node and
  resource-network milestone.
- Nothing runnable changes. No C++, consensus, devnet, manifest, economy, seat,
  routing, escrow, scenario, or cycle-boundary artifact, vector, or digest is
  modified.

## Compatibility and independent review

This is version one and supersedes no prior rule. `SLOTS_PER_WINDOW`,
`CHALLENGE_PERIOD_BLOCKS`, `RESPONSE_DEADLINE_BLOCKS`, `DISPUTE_WINDOW_WINDOWS`,
and `DISPUTE_CAP_SLOTS_PER_SEAT` are normative; changing the first
re-denominates every credit and is a migration rather than a parameter change.

The model is research software and activates nothing. Its result codes are model
codes; the numeric consensus receipts for a C++ transition are requirement 5.

Three claims are design intent rather than proof and need the independent review
of `first-goal.md` requirement 15 before the pipeline carries value.

The first is the anti-gaming claim, and it is bounded by an undecided value. The
challenge protocol is specified and the challenge *content* is not, so until the
resource commitment is decided, an answered challenge proves that something able
to produce it was reachable within sixty seconds. That is liveness of a
responder rather than possession of a resource, and every anti-gaming property
claimed here inherits that limit.

The second is the sampling margin. A seat down for `D` challengeable heights
escapes with probability `(1 - 1/1200)^D`, so a lost slot is caught about 63% of
the time and a lost window with probability above 0.999999. Whether that margin
is adequate against a founder with physical access to the machine is the
question ADR 0023 already records as unreviewed.

The third is beacon bias. A proposer with influence over the state root at
`h - 1` has some influence over who is challenged at `h`. This is the same
adversary ADR 0027 refers to review for the block production rate, and the two
should be reviewed together.
