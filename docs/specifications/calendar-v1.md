# Calendar v1

[ADR 0050](../decisions/0050-the-block-timestamp-is-the-ecosystem-clock.md)
decided that the ecosystem's clock is a timestamp the proposing machine stamps
into the block header, that other machines accept it only if it is monotonic and
within tolerance, that execution reads the agreed field and never a clock, and
that a month is a real calendar month beginning on the 1st. It deliberately
fixed only the decision and named four things a `calendar-v1` specification
would have to fix: the mapping, the boundary rule, the acceptance tolerance, and
the derivation from the header field.

This specification is those four things.
[ADR 0074](../decisions/0074-the-consensus-timestamp-and-the-calendar-month.md)
records the choices it makes and the alternatives rejected.

It defines the canonical unit and range of the consensus timestamp, the
monotonicity rule every machine re-checks, the acceptance tolerance stated so
that any consensus adapter can satisfy it, the integer derivation from a
timestamp to a calendar month, the predicate that decides which block opens a
month and therefore which block closes the previous one, and the exact bound on
how far a dishonest proposer can move a month boundary.

It exists because the Founder Constitution pays the unreferred performance pool
to the best-performing Founder Machines of a **month**, and no accepted artifact
yet says what a month is in a form two machines can agree on.

## Scope

This specification defines a field, five rules about it, and an integer
derivation. It measures nothing, ranks nothing, and pays nothing.

In scope:

- the canonical unit, epoch, and accepted range of the consensus timestamp;
- the monotonicity rule, and its genesis case;
- the acceptance tolerance, its two sides, and the form in which an adapter
  satisfies it;
- the separation between the rules a replaying machine re-checks and the one it
  must not;
- the proleptic Gregorian derivation from a timestamp to a year, a month, and a
  monotone month index;
- the inverse derivation from a month index to its first and last millisecond;
- the month-opening predicate over a chain of heights, the month-closing rule it
  implies, empty months, and the chain's partial first month;
- the exact bound on a proposer-induced boundary shift, and the argument that it
  does not accumulate; and
- the resource cost, which is eight octets of header and no state at all.

Explicitly not in scope:

- **the unreferred pool's payout.** The candidate set, the ranking snapshot, the
  height at which the payout executes, and the treatment of an accrual with no
  candidate are the successor slice's, and they carry founder-reserved questions
  this specification does not. What this specification owes that slice is the
  month, and the month is what it delivers.
- **the uptime the ranking would read.** That is
  [`uptime-measurement-v1`](uptime-measurement-v1.md) and
  [`economy-transition-v8`](economy-transition-v8.md). Nothing here observes a
  machine.
- **the ledger version that binds this contract.** Adding a header field and a
  genesis field changes a transition, which under the rule ADR 0024 and ADR 0026
  established requires a new economy contract version rather than an edit. This
  specification defines what that version will apply. It is the same posture
  [`cycle-boundary-v1`](cycle-boundary-v1.md) took, and the same gap: the rule
  moves from undefined to unenforced. **That version is
  [`economy-transition-v9`](economy-transition-v9.md)**, accepted 2026-09-15,
  which closes the gap.
- **the adapter's production algorithm.** How a proposer chooses a value — a
  local reading, CometBFT's weighted median of the previous height's precommits,
  or anything else — is an adapter matter. This specification constrains the
  accepted value, not the way it was reached.

No accepted artifact, vector, digest, C++ source, genesis file, or devnet
behaviour is changed by this specification. Versions one through eight carry no
timestamp and are unaffected.

## Determinism rules

Every quantity here is an integer and every operation is integer addition,
subtraction, multiplication, comparison, or truncating division. There is no
floating point and no locale.

There is exactly one reading of a clock in this specification, and it is not in
a derivation. It is the observing machine's own clock in rule **C5**, which is a
consensus admission check performed once, before a block is committed. Every
other rule — the range, the monotonicity, and the whole calendar derivation —
reads the agreed header field and nothing else.

That separation is the substance of ADR 0050's first decision and it is stated
here as a rule rather than as a description, because getting it wrong is silent:
a machine that re-applied C5 while replaying history would reject the chain's
own past, since the clock it reads on replay is not the clock that agreed the
block.

## Constants

| Name | Value | Source |
| --- | ---: | --- |
| `MILLIS_PER_SECOND` | 1,000 | this specification |
| `MILLIS_PER_DAY` | 86,400,000 | derived |
| `TIMESTAMP_EPOCH` | 1970-01-01T00:00:00.000Z | this specification |
| `MIN_TIMESTAMP_MILLIS` | 0 | the epoch |
| `MAX_TIMESTAMP_MILLIS` | 253,402,300,799,999 | 9999-12-31T23:59:59.999Z |
| `MIN_CALENDAR_YEAR` | 1970 | the epoch |
| `MAX_CALENDAR_YEAR` | 9999 | this specification |
| `MONTHS_PER_YEAR` | 12 | the Gregorian calendar |
| `MAX_MONTH_INDEX` | 96,359 | derived |
| `TIMESTAMP_TOLERANCE_SECONDS` | 60 | this specification |
| `TIMESTAMP_TOLERANCE_MILLIS` | 60,000 | derived |
| `TARGET_COMMIT_SECONDS` | 3 | `consensus-application-v1` |
| `MAX_BOUNDARY_SHIFT_BLOCKS` | 20 | derived |
| `SECONDS_PER_MONTH_MINIMUM` | 2,419,200 | derived, a 28-day month |
| `CALENDAR_STATE_BYTES` | 0 | derived |

`MAX_MONTH_INDEX` is `(9999 - 1970) * 12 + 11`. `MAX_BOUNDARY_SHIFT_BLOCKS` is
`TIMESTAMP_TOLERANCE_SECONDS / TARGET_COMMIT_SECONDS`, and that division is
exact; the model requires a zero remainder rather than reporting a rounded
figure.

### The unit is the millisecond

The canonical timestamp is a `u64` count of milliseconds since
`TIMESTAMP_EPOCH`, under the POSIX convention that every day is exactly
`MILLIS_PER_DAY` milliseconds. Leap seconds are not represented; a leap second
is absorbed by the second that carries it, which is what every civil timekeeping
service already delivers to a machine.

**Rejected: seconds.** Every founder-directed duration is stated in seconds and
`cycle-boundary-v1` is denominated in seconds throughout, so seconds were the
obvious unit and they are the one this specification reached for first. They are
too coarse for the rule to survive its own edge: a chain that produces two
blocks inside one second — which is ordinary when a halted network catches up —
could satisfy a non-decreasing rule but could never satisfy a strict one, so
choosing seconds would foreclose a stricter monotonicity rule for every later
version. The unit is a permanent decision and the rule may not be; the unit
should therefore be the finer of the two.

**Rejected: nanoseconds.** CometBFT's own time is nanosecond-precision, so
nanoseconds would need no conversion at all. A `u64` of nanoseconds since the
epoch ends in the year 2262, which is a horizon this project should not write
into a consensus field, and CometBFT transports the value as a protobuf
`Timestamp` of separate seconds and nanoseconds anyway, so an adapter recombines
it in either case. A `u64` of milliseconds reaches the year 584,542,046.

**Rejected: a chain-local epoch anchored at genesis.** It would make every
timestamp smaller and would make the calendar derivation depend on a
per-deployment constant, so two chains could not be compared and a genesis
mistake would silently shift every month boundary for the life of the chain. The
Unix epoch is the value every machine already has.

### The accepted range

A timestamp outside `[MIN_TIMESTAMP_MILLIS, MAX_TIMESTAMP_MILLIS]` is invalid.
The upper bound is the last millisecond of the year 9999, which is where this
specification stops defining the calendar; a `u64` reaches far beyond it, and the
bound exists so that every derivation below is **total** — every accepted
timestamp has a year, a month, and a month index, and no derivation has an
undefined case to guess at.

## The five rules on the field

Let `t(h)` be the timestamp of the block at height `h`, and let `g` be the
genesis timestamp, which a conforming ledger version binds in its genesis file
exactly as it binds the chain identity.

### C1 — Range

`MIN_TIMESTAMP_MILLIS <= t(h) <= MAX_TIMESTAMP_MILLIS` for every height, and
`MIN_TIMESTAMP_MILLIS <= g <= MAX_TIMESTAMP_MILLIS` for genesis.

### C2 — Monotonicity

For the chain's first block, `t(h) >= g`. For every later height,
`t(h) >= t(h - 1)`.

**Non-decreasing, not strictly increasing.** Two consecutive blocks may carry
the same millisecond. The rule has to be satisfiable by *any* adapter at *any*
block rate, and a strict rule is a liveness hazard precisely when a network is
already in trouble: a chain catching up after a halt produces blocks as fast as
it can, and a strict rule would make the engine's own recovery invalid. Nothing
in this specification needs a strict rule — a height, not a timestamp, is what
identifies a block, and the calendar derivation is monotone in `t` under either
rule.

### C3 — Height

A chain's heights are `ledger-transition-v1`'s: the only valid next height is
`h + 1`, and height never decreases. C2 is stated against `h - 1` and relies on
it.

### C4 — Execution reads the field

Deterministic execution reads `t(h)` from the agreed header. It never reads a
clock, a service, or any other moving value. Every quantity in "The calendar
derivation" below is a pure function of `t(h)`.

### C5 — The acceptance tolerance

A correct machine accepts a proposed block at height `h` only if, at the moment
it first validates that height,

```text
| t(h) - own_clock_millis | <= TIMESTAMP_TOLERANCE_MILLIS
```

where `own_clock_millis` is that machine's own reading of civil time in the unit
and epoch above.

**It is two-sided on purpose.** A one-sided rule bounding only how far ahead a
stamp may run is the tempting simplification and it is unsound: a colluding
proposer set that stamped far behind would hold the chain's clock back
indefinitely, never crossing a month boundary, and would pay nobody while
satisfying every other rule here. Both sides are therefore rules, and both are
separately named in the result codes so each can be tested on its own.

**It is a statement about the accepted value, not about the algorithm that
produced it.** This is what lets any adapter satisfy it. A machine that reads its
own clock satisfies C5 directly. CometBFT's BFT time satisfies it under the
standard assumption behind the rest of the consensus layer: the committed time
is a weighted median over more than two thirds of voting power, and with less
than one third Byzantine the median lies within the range of the correct
validators' own readings, so if every correct clock is within `d` of civil time
the committed stamp is too, and any correct machine's own reading differs from it
by at most `2d` plus the one commit interval by which BFT time lags. The
tolerance is chosen to cover that; see below.

**C5 is not re-applied on replay, and C1 and C2 are.** C5 is the only rule here
whose input is not in the block. A machine replaying history, restoring from a
snapshot, or reconstructing state must re-check C1 and C2 and must **not**
re-check C5, because the clock it would read is not the clock that agreed the
block. Applying C5 on replay would make a correct chain unverifiable one
tolerance-width after it was produced. A conforming implementation therefore
exposes the two paths separately, and the model below does.

### Why the tolerance is 60 seconds

The tolerance has a floor and a ceiling and the value sits between them with
room on both sides.

**The floor** is what a correct machine can be off by without being at fault.
Three terms contribute, and they add:

```text
2 x clock skew from civil time  <= 2 x 10s = 20s   (a consumer machine
                                                    running default NTP;
                                                    10s is already an
                                                    unmaintained machine)
BFT time's one-block lag         =        3s       (TARGET_COMMIT_SECONDS)
proposal propagation and
  validation before the check    <=       15s      (CometBFT's own default
                                                    MessageDelay synchrony
                                                    parameter)
                                    ----------
                                           38s
```

A tolerance below that rejects honest proposals, which is a liveness failure of
the whole chain rather than a defence against anything.

**The ceiling** is the founder-visible consequence ADR 0050 names: the tolerance
is exactly how far a dishonest proposer can move a month boundary, so it must be
small relative to a month. At 60 seconds it is `60 / 2,419,200` of the shortest
possible month — under 25 parts per million — and at the 3-second commit target
it moves at most `MAX_BOUNDARY_SHIFT_BLOCKS` = 20 blocks of the 806,400 in a
28-day month.

**60 seconds clears the floor by more than half again and sits more than four
orders of magnitude under the ceiling.** It is also a figure an operator can
reason about without arithmetic: a Founder Machine whose clock is more than a
minute wrong will be told so, and telling an operator "your clock is more than
a minute out" is a diagnosable instruction in a way that "your clock is more
than 505 milliseconds out" is not.

**Rejected: CometBFT's PBTS defaults, a 505-millisecond precision with a
15-second message delay.** They are well chosen for the problem they solve —
keeping block time close to real time on a datacentre validator set — and they
are wrong for this one. A Founder Machine is a consumer machine in a home, and
the cost of a too-tight bound here is that honest machines are excluded from a
network whose entire purpose is that ordinary people run it. The cost of a
too-loose bound is 20 blocks of month boundary. The asymmetry is decisive.

**Rejected: a tolerance derived from the month length, such as one part in a
million.** It sounds principled and it is circular: the quantity that should
determine the tolerance is how wrong a correct machine's clock can be, which has
nothing to do with how long a month is. The month length belongs in the ceiling
check, which is where it is used.

**It is a consensus parameter, not an adapter default.** ADR 0050 requires this
and the reason is that two machines applying different tolerances disagree about
which blocks are acceptable, which is a fork. The value is stated here, is
carried by the ledger version that binds this specification, and is not
configurable per deployment.

## The calendar derivation

The calendar is the **proleptic Gregorian calendar in UTC**. Every derivation
below is integer arithmetic on `t` alone.

**Why UTC, stated rather than assumed.** A consensus timestamp is one global
value; there is no participant whose local zone consensus could read, and a
per-participant boundary would mean the same block closed different months for
different people, which is not a calendar but one per zone. The consequence is
worth stating plainly because a participant experiences it: the 1st begins at
midnight UTC, so a machine in UTC+13 sees a month roll at one o'clock in the
afternoon of its own 1st. Every global system makes this trade and the
alternative is incoherent, but the participant-visible fact belongs in the
specification rather than in the arithmetic.

### Days

```text
day_index(t) = t / MILLIS_PER_DAY            (truncating; t >= 0)
```

`day_index` is the count of whole days since 1970-01-01. It is non-decreasing in
`t`, and it is exact because `MILLIS_PER_DAY` is a constant rather than a
measurement: no leap second is represented, so every day is the same length.

### The civil date of a day

`civil_from_days(z)` returns the proleptic Gregorian `(year, month, day)` of day
index `z`, and `days_from_civil(y, m, d)` is its inverse. Both are the standard
closed-form integer algorithms, they use only integer division and
multiplication, and the model requires

```text
days_from_civil(civil_from_days(z)) == z
```

over every day in the accepted range rather than at sampled points, which is
2,932,897 days and runs in seconds.

The Gregorian leap rule is the whole rule and not the common abbreviation of it:
a year is a leap year when it is divisible by 4 **and** not by 100, **or** it is
divisible by 400. The years where the abbreviation and the rule disagree are
recorded as vectors — 2000 is a leap year and 2100 is not — because an
implementation that tested only 2024 would pass.

### The month index

```text
(y, m, d)      = civil_from_days(day_index(t))
month_index(t) = (y - MIN_CALENDAR_YEAR) * MONTHS_PER_YEAR + (m - 1)
```

`month_index` is a non-decreasing function of `t`, is 0 for the epoch month, and
is `MAX_MONTH_INDEX` for December 9999. It therefore fits in a `u32` with four
decimal orders to spare. **The reason for anchoring at 1970 is the zero point
rather than the width** — an index counted from year zero would also fit — and
the zero point matters because it makes the epoch month index 0 instead of an
arbitrary constant that every implementation would have to agree on separately.

### The inverse

```text
year_of(i)          = MIN_CALENDAR_YEAR + i / MONTHS_PER_YEAR
month_of(i)         = i % MONTHS_PER_YEAR + 1
month_start_millis(i) = days_from_civil(year_of(i), month_of(i), 1)
                        * MILLIS_PER_DAY
month_end_millis(i)   = month_start_millis(i + 1) - 1
```

`month_end_millis(MAX_MONTH_INDEX)` is `MAX_TIMESTAMP_MILLIS`, which is why the
year bound and the timestamp bound are one decision rather than two.

Three identities hold for every index in range and the model checks all three
over the whole range rather than at endpoints:

```text
month_index(month_start_millis(i)) == i
month_index(month_end_millis(i))   == i
month_start_millis(i) % MILLIS_PER_DAY == 0
```

## The month over a chain

### Which month a height is in

```text
month_of_height(h) = month_index(t(h))
```

Because `t` is non-decreasing (C2) and `month_index` is non-decreasing in `t`,
the sequence of month indices along a chain is non-decreasing. That is the
property the payout slice rests on and it is a consequence of C2 rather than a
separate rule.

### Which height opens a month

Height `h` **opens** a month when

```text
h is the chain's first height
  or  month_of_height(h) > month_of_height(h - 1)
```

### Which height closes one, which is the rule a transition uses

A month's last height cannot be recognised when it is executed, because whether a
later block falls in the same month is not yet known. The usable rule is
therefore the opening one read backwards:

> **The block that opens a new month is the block at which every earlier month
> becomes final.**

A transition that must act on a completed month — the unreferred pool's payout is
the one this specification exists for — executes in the block that opens the next
month, not in the last block of its own. This is the single most consequential
sentence here for the successor slice, and it is a derivation rather than a
choice: no other height is recognisable.

### Empty months, and a chain that skips several

C2 requires only that time not go backwards. A chain that halts for six weeks
resumes with a stamp six weeks later, so `month_of_height(h)` may exceed
`month_of_height(h - 1)` by more than one. Every index strictly between them is
an **empty month**: a month with no heights at all.

An opening block therefore closes **every** index in
`[month_of_height(h - 1), month_of_height(h))` — its predecessor's own month and
every empty month after it — not only the immediately preceding one. An
implementation that assumed a single predecessor would silently skip a month's
worth of an accrued pool the first time a network was down across a month
boundary, which is exactly the kind of defect that is invisible until it is
expensive.

An empty month accrues nothing, because every accrual in this ecosystem is
per-cycle and a cycle is a span of heights. What it does and does not owe is the
successor slice's to state; what this specification owes is that empty months
exist and are enumerable.

### The chain's first month is partial

The chain's first block opens a month at whatever point in that month genesis
fell. The first month is therefore a partial month, and the last month of a
chain that stops is partial at the other end. Neither is an error and neither is
distinguishable by the derivation; both are named here so the successor slice
decides about them deliberately.

## The boundary shift, bounded and non-accumulating

**The bound.** A proposer whose block opens a month can stamp it anywhere within
`TIMESTAMP_TOLERANCE_MILLIS` of civil time and have it accepted, so it can move
the boundary by at most `TIMESTAMP_TOLERANCE_SECONDS` in either direction: at
most `MAX_BOUNDARY_SHIFT_BLOCKS` blocks at the commit target. It can move the
boundary *earlier* only by stamping ahead of civil time and *later* only by
stamping behind it, and C5 bounds both.

**It does not accumulate.** This is the property that matters and it is not
obvious. Each block's stamp is bounded against the *current* civil time at every
correct machine, not against the previous block's stamp, so a proposer that
stamps 60 seconds late does not thereby license the next proposer to stamp 120
seconds late — the next block is judged against civil time afresh. The chain's
clock is therefore pinned to within one tolerance of civil time at every height,
and the error at the boundary of month `m + 1` is independent of the error at the
boundary of month `m`. A specification that bounded each stamp only against its
predecessor would permit unbounded drift, which is why C5 is stated against the
observer's clock rather than against `t(h - 1)`.

**What the shift is worth.** Whatever the successor slice attributes to the 20
blocks that can change months, and no more. This specification does not know that
figure and deliberately does not guess at one; it states the bound in blocks so
the payout slice can price it.

## Rejection conditions, in order

A machine evaluating a proposed block's timestamp applies these in order and
reports the first that fires. The order is normative: a timestamp outside the
representable range is refused before any derivation is attempted on it, which is
what keeps every later rule total.

| Order | Code | Condition |
| ---: | --- | --- |
| 1 | `HEIGHT_NOT_NEXT` | the height is not the chain's next height |
| 2 | `TIMESTAMP_RANGE` | `t` is outside the accepted range |
| 3 | `TIMESTAMP_NOT_MONOTONIC` | `t` is below the predecessor's, or below genesis |
| 4 | `TIMESTAMP_AHEAD_OF_TOLERANCE` | `t > own_clock + TIMESTAMP_TOLERANCE_MILLIS` |
| 5 | `TIMESTAMP_BEHIND_TOLERANCE` | `t < own_clock - TIMESTAMP_TOLERANCE_MILLIS` |
| — | `ACCEPTED` | none of the above |

Conditions 1 to 3 are deterministic and are re-applied on every replay.
Conditions 4 and 5 are the two sides of C5 and are applied once, at admission,
and never again.

**Atomicity.** A rejection writes nothing. The rejected height does not become the
chain's head, the predecessor timestamp is unchanged, and a machine that refused
a block is in the state it was in before the block arrived. The model measures
this on one instance across a run of rejections rather than by comparing two
freshly built instances, which would only show that the model is deterministic.

**Replay.** Re-applying an already accepted height fails condition 1, because the
chain's next height has moved past it. There is no separate replay rule and no
separate code.

## Overflow and numeric range

Every value is a non-negative integer bounded by `u64`. The derivations that could
overflow are bounded rather than assumed:

- `month_end_millis(i)` calls `month_start_millis(i + 1)`, so `i` is required to
  be at most `MAX_MONTH_INDEX` and the internal `i + 1` reaches exactly
  `MAX_MONTH_INDEX + 1`, whose start is `MAX_TIMESTAMP_MILLIS + 1`. That is the
  single value the derivation computes outside the accepted range, it is
  representable, and it is the reason the range ends where it does rather than at
  the `u64` bound.
- `own_clock + TIMESTAMP_TOLERANCE_MILLIS` in condition 4 is evaluated as a
  comparison rather than as a sum where a clock near the `u64` bound would wrap.
  Condition 5's subtraction is guarded the same way.
- `day_index(t)` is at most 2,932,896 and `month_index(t)` at most 96,359, so
  both fit in a `u32`. They are `u64` in the model because every other quantity
  is, and the bound is recorded rather than relied on silently.

## Resource cost

The calendar adds **no state**. A height's month is a pure function of a field the
header already carries once this specification is bound, so nothing is stored,
nothing is indexed, and `CALENDAR_STATE_BYTES` is 0. The cost is eight octets per
block header and one integer derivation per query.

A seat's 731-cycle span touches at most **25** calendar months. That figure is
**nominal**: it converts 731 cycles to 731 days at the 3-second commit target, in
the same direction `cycle-boundary-v1` converts seconds to blocks, and it is a
sizing input rather than a consensus quantity — nothing derives a month from a
cycle. It is recorded because the successor slice needs it to bound a per-seat
monthly record if it decides it needs one. The model derives it by walking every
start day in a four-century window rather than by reasoning about month lengths,
because the reasoning is where the off-by-one lives.

## Compatibility

`calendar-v1` is additive and binds nothing yet.

- **Versions one through eight are unaffected.** None carries a timestamp, none
  reads one, and none of their genesis files, headers, state roots, receipts, or
  vectors changes. The version-eight block header stays 146 octets.
- **The ledger version that binds this specification** adds the header field and
  the genesis field, which makes it a new contract version rather than an edit to
  an accepted one. It must apply C1 and C2 in execution, expose the C5 check to
  its consensus adapter separately from execution, and carry
  `TIMESTAMP_TOLERANCE_MILLIS` as a consensus parameter.
- **`consensus-application-v1` lists timestamps among the inputs that are not
  application transition inputs.** That remains exactly true of the values this
  specification excludes — proposer identity, vote data, wall-clock readings —
  and it becomes false of the agreed header field on the version that binds this
  specification, which is a difference the binding version states rather than one
  this specification makes retroactively.
- **`cycle-boundary-v1` is untouched and stays in heights.** ADR 0050 is explicit
  that cycle windows remain block-denominated and that mixing the two units is
  the mistake the separation exists to prevent. Nothing here converts a month to
  blocks or a cycle to a date; `MAX_BOUNDARY_SHIFT_BLOCKS` is a statement about a
  tolerance, not a mapping between the grids.

## Vectors

`test-vectors/calendar-v1.txt` records the derivation. Every value in it is
reached twice — once by `tools/calendar-vectors/expected.py`, which imports
nothing from `simulation/` and computes the calendar by accumulating month
lengths from 1970 rather than by the closed form the model uses, and once by a
live model run. Two different algorithms agreeing is the evidence; a single
algorithm restating itself would not be.

The recorded cases are chosen where an error is visible rather than where a value
is round:

- the epoch itself, and the last millisecond before the second month;
- the first and last millisecond of a month, on both sides of a boundary;
- February in a common year, a divisible-by-4 leap year, the year 2000, and the
  year 2100, which is the pair the abbreviated leap rule gets wrong;
- the maximum timestamp and the maximum month index;
- a full round trip over every day in the accepted range and every month index in
  it, reported as a mismatch count rather than as a claim;
- equal consecutive timestamps, accepted under C2;
- each rejection condition reached on its own, and the count of modelled codes
  reached, so a later scenario cannot lose coverage while still passing;
- a chain that halts across two whole months, with the set of months its
  resuming block closes; and
- the clockless replay of an accepted chain, agreeing with the live run height
  for height.

## Open items this specification deliberately does not settle

- **The unreferred pool's payout.** Named above, and the successor slice.
- **Whether a later version makes C2 strict.** The unit permits it and nothing
  requires it. Recorded so the choice of unit is legible.
- **The behaviour of a chain whose genesis timestamp is far from civil time.** C5
  governs every block, so such a chain either has an unacceptable first block or
  a monotonicity failure at it; which of the two it should report is the binding
  version's, since only that version has a genesis file to refuse.
  **[`economy-transition-v9`](economy-transition-v9.md) answers it**: genesis
  validation applies C1 and reads no clock, because the chain identity is a hash
  of the genesis bytes, and a chain whose genesis is in the future reports
  `TIMESTAMP_NOT_MONOTONIC` at its first block, which is what the ordered
  conditions above reach first.
