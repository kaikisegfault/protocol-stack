# ADR 0074: The consensus timestamp is a u64 of milliseconds and the month is derived from it

- Status: Accepted
- Date: 2026-09-14
- Bounds: [ADR 0050](0050-the-block-timestamp-is-the-ecosystem-clock.md)
- Relates to: `docs/specifications/calendar-v1.md`,
  `docs/project/founder-constitution.md` (the unreferred performance pool)

## Context

[ADR 0050](0050-the-block-timestamp-is-the-ecosystem-clock.md) decided that the
ecosystem's clock is a timestamp the proposing machine stamps into the block
header, that other machines accept it only if it is monotonic and within
tolerance, that execution reads the agreed field and never a clock, and that a
month is a real calendar month beginning on the 1st. It fixed the decision and
deliberately left four things to a later specification: **the mapping, the
boundary rule, the acceptance tolerance, and the derivation from the header
field**. It also stated the constraint on the last of those — the tolerance is
consensus-visible, because a proposer can move a month boundary within it, so it
must be a stated consensus parameter rather than an adapter default, and the
rule must be statable in a form any adapter can satisfy, since CometBFT's own
time is a median of validator clocks rather than one machine's reading.

Nothing has fixed them in the four weeks since.
`economy-transition-v8` scopes them out by name. The Founder Constitution pays
the unreferred performance pool to the best-performing Founder Machines of a
**month**, and until now no accepted artifact said what a month is in a form two
machines could agree on.

This ADR records the choices `calendar-v1` makes and the alternatives rejected.
The specification carries the rules; this record carries why they are these
rules.

## Decision

### 1. The canonical unit is a `u64` of milliseconds since the Unix epoch

Under the POSIX convention that every day is exactly 86,400,000 milliseconds, so
no leap second is representable.

**Rejected: seconds.** Every founder-directed duration is stated in seconds and
`cycle-boundary-v1` is denominated in seconds throughout, so seconds were the
obvious choice and the one this slice reached for first. They are too coarse at
the edge that matters: a chain catching up after a halt produces blocks faster
than one a second, so a seconds field could satisfy a non-decreasing rule and
could never satisfy a strict one. **The unit is permanent and the monotonicity
rule may not be**, so the unit should be the finer of the two.

**Rejected: nanoseconds.** They would need no conversion from CometBFT at all. A
`u64` of nanoseconds ends in the year 2262, which is not a horizon to write into
a consensus field, and CometBFT transports its time as a protobuf `Timestamp` of
separate seconds and nanoseconds anyway, so an adapter recombines it either way.
Milliseconds reach the year 584,542,046.

**Rejected: an epoch anchored at genesis.** It would make the calendar
derivation depend on a per-deployment constant, so two chains could not be
compared and a genesis mistake would shift every month boundary for the life of
the chain.

### 2. Monotonicity is non-decreasing, not strictly increasing

`t(h) >= t(h - 1)`, and `t(first) >= genesis_timestamp`.

A strict rule is a liveness hazard precisely when a network is already in
trouble: it would make the engine's own catch-up invalid. Nothing needs a strict
rule — a **height** identifies a block, and the calendar derivation is monotone
in `t` under either. The unit leaves a strict rule available to a later version;
this one does not take it.

### 3. The acceptance tolerance is 60 seconds, two-sided

A correct machine accepts height `h` only if, when it first validates that
height, `|t(h) - own_clock| <= 60,000` milliseconds.

**Two-sided, because a one-sided rule is unsound.** Bounding only how far ahead
a stamp may run is the tempting simplification: a colluding proposer set that
stamped far *behind* would hold the chain's clock back indefinitely, never
crossing a month boundary, and would pay nobody while satisfying every other
rule. Both sides are rules and each has its own result code.

**60 seconds, because the floor is about 38 and the ceiling is about 2.4
million.** The floor is what a correct machine can be off by without being at
fault: twice a generous 10-second consumer clock skew, plus BFT time's
one-commit-interval lag of 3 seconds, plus a propagation and validation budget
of 15 seconds — CometBFT's own default `MessageDelay`. The ceiling is the
consequence ADR 0050 names: the tolerance is exactly how far a dishonest
proposer can move a month boundary, and the shortest month is 2,419,200 seconds.
At 60 the value clears the floor by more than half again and sits at 24 parts
per million of the ceiling — at most 20 blocks of the 806,400 in a 28-day month.

**Rejected: CometBFT's PBTS defaults of a 505-millisecond precision with a
15-second message delay.** Well chosen for a datacentre validator set and wrong
for this one. A Founder Machine is a consumer machine in a home. The cost of a
too-tight bound is excluding honest machines from a network whose whole purpose
is that ordinary people run it; the cost of a too-loose bound is 20 blocks of
month boundary. The asymmetry is decisive. 60 seconds is also a figure an
operator can act on: "your clock is more than a minute wrong" is a diagnosable
instruction in a way that "more than 505 milliseconds" is not.

**Rejected: a tolerance derived from the month length.** One part per million of
a month sounds principled and is circular — how wrong a correct clock can be has
nothing to do with how long a month is. The month length belongs in the ceiling
check, which is where it is used.

**It is a consensus parameter, not an adapter default**, as ADR 0050 requires:
two machines applying different tolerances disagree about which blocks are
acceptable, which is a fork.

**It is stated as a condition on the accepted value rather than as a production
algorithm**, which is what lets any adapter satisfy it. A machine reading its own
clock satisfies it directly. CometBFT's BFT time satisfies it under the
assumption the rest of the consensus layer already makes: the committed time is
a weighted median over more than two thirds of voting power, and with less than
one third Byzantine the median lies within the range of correct validators'
readings.

### 4. C1 and C2 are re-checked on replay; C5 is not

The range and the monotonicity rules are deterministic and every replay,
snapshot restore, and state reconstruction re-applies them. The tolerance is the
only rule whose input is not in the block, and a replaying machine must **not**
re-apply it: the clock it would read is not the clock that agreed the block, so
applying it would make a correct chain unverifiable one tolerance-width after it
was produced.

This is the substance of ADR 0050's first decision and it is recorded as a rule
rather than as a description because getting it wrong is silent. A conforming
implementation exposes the two paths separately. The model does, and the vector
file records one stamp ten days out offered to both — accepted by the replay
path, refused by the admission path — so the separation is falsifiable rather
than asserted.

### 5. The calendar is the proleptic Gregorian calendar in UTC

A consensus timestamp is one global value; there is no participant whose local
zone consensus could read, and a per-participant boundary would mean the same
block closed different months for different people. The participant-visible
consequence is stated in the specification rather than left implicit: the 1st
begins at midnight UTC, so a machine in UTC+13 sees the month roll in the
afternoon of its own 1st.

The month index is `(year - 1970) * 12 + (month - 1)`, which is 0 for the epoch
month and 96,359 for December 9999, where the accepted range ends.

### 6. The block that opens a month is the block that closes the previous one

A month's last height cannot be recognised when it executes, because whether a
later block falls in the same month is not yet known. The opening block is the
only recognisable point, so a transition acting on a completed month — the
unreferred pool's payout is the one this work exists for — executes there.

**A block closes every month index in `[month_of(h - 1), month_of(h))`**, not
only the immediately preceding one. Monotonicity requires only that time not go
backwards, so a chain halted across a month boundary resumes with a jump, and
every index between is an **empty month** holding no heights at all. An
implementation assuming a single predecessor would silently skip a month's
accrual the first time a network was down across a boundary.

### 7. The calendar stores nothing

A height's month is a pure function of a field the header carries once a ledger
version binds this specification. The cost is eight octets per header and one
integer derivation per query.

## Consequences

**No accepted artifact changes.** Versions one through eight carry no timestamp,
and none of their genesis files, headers, state roots, receipts, or vectors is
touched. The version-eight block header stays 146 octets. This is the posture
`cycle-boundary-v1` took, and it carries the same gap: the rule moves from
undefined to **unenforced**, and a later ledger version is what enforces it.

**The ledger version that binds this specification adds two fields**, a header
timestamp and a genesis timestamp, which makes it a new contract version rather
than an edit under the rule ADR 0024 and ADR 0026 established. It must apply C1
and C2 in execution, expose C5 to its consensus adapter separately, and carry
the tolerance as a consensus parameter.

**`consensus-application-v1` lists timestamps among the inputs that are not
application transition inputs.** That stays true of everything it excludes —
proposer identity, vote data, wall-clock readings — and becomes false of the
agreed header field on the version that binds this specification, which is a
difference that version states rather than one this ADR makes retroactively.
**Both are now stated.**
[`economy-transition-v9`](../specifications/economy-transition-v9.md) binds the
fields and [ADR 0079](0079-the-version-nine-application-contract.md) accepts
[`consensus-application-v2`](../specifications/consensus-application-v2.md),
which carries the corrected sentence.

**Cycle windows stay in block heights.** ADR 0050 is explicit that mixing the
two units is the mistake the separation exists to prevent. Nothing here converts
a month to blocks or a cycle to a date; the 20-block figure is a statement about
a tolerance, not a mapping between the grids.

**The unreferred pool's payout is not decided by this ADR and is the immediate
successor.** The candidate set, the ranking snapshot, the treatment of an accrual
with no candidate, and what a partial first month owes are its questions, and
some of them are founder-reserved. What this work owes that slice is the month,
and the month is what it delivers.

**One figure the successor slice will need is recorded rather than left to be
rediscovered.** A seat's 731-cycle span — nominally 731 days at the 3-second
commit target, which is a sizing figure and not a consensus quantity — touches at
most **25** calendar months, derived by walking every start day in a four-century
window rather than by reasoning about month lengths.
