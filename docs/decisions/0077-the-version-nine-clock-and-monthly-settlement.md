# ADR 0077: Version nine carries the clock in the block header and settles the month in one pass

- Status: Accepted
- Date: 2026-09-15
- Bounds: [ADR 0050](0050-the-block-timestamp-is-the-ecosystem-clock.md),
  [ADR 0074](0074-the-consensus-timestamp-and-the-calendar-month.md),
  [ADR 0075](0075-founder-answers-on-the-monthly-pool-candidate-set-and-carry.md),
  [ADR 0076](0076-the-monthly-pool-ranks-every-in-scope-seat.md)
- Relates to: `docs/specifications/economy-transition-v9.md`,
  `docs/specifications/calendar-v1.md`,
  `docs/specifications/unreferred-pool-payout-v1.md`

## Context

Two accepted specifications describe rules that no chain applies.

[`calendar-v1`](../specifications/calendar-v1.md) fixes the consensus
timestamp's unit, range, monotonicity rule, tolerance, and the derivation from it
to a calendar month. No block header carries the field it is about.

[`unreferred-pool-payout-v1`](../specifications/unreferred-pool-payout-v1.md)
fixes the monthly candidate set, the ranking figure, the attribution rule, the
tie split, the remainder, the carry, and the point in the window-assignment
sequence at which a month is paid. No state holds the figures it ranks and no
block performs the payout.

Both took the posture [`cycle-boundary-v1`](../specifications/cycle-boundary-v1.md)
and [`uptime-measurement-v1`](../specifications/uptime-measurement-v1.md) took
before version eight, and they leave the same gap: the rules moved from undefined
to **unenforced**. The unreferred performance pool has accrued since
`economy-transition-v3` and **nothing has ever taken value out of it**.

Version eight's own versioning section fixes its state key space, result codes,
kind space, and genesis field table as immutable, so this is a new transition
version rather than a repair — the same position version eight was in with
respect to version seven.

This ADR records the choices `economy-transition-v9` makes and the alternatives
rejected. The specification carries the rules; this record carries why they are
these rules.

## Decision

### 1. The timestamp is a block header field, inserted after the height

The header becomes 154 octets with schema version `9`, and `block_id` is
re-versioned to `protocol-stack:v9:block-id`. This is the first header change in
the project's history; every version through eight inherited version one's 146
octets and its schema version of `1`.

**Rejected: appending the field after the transaction count.** It would keep every
existing offset identical, which reads as a benefit and is a hazard: a decoder
that treated the length loosely would parse a version-nine header as a
version-one header with eight trailing octets and agree with itself about every
field it read. Moving the offsets makes a mis-versioned decode fail at the first
comparison. The height and the timestamp are also the two fields that place a
block on the two grids this ecosystem runs on, and they belong together.

**Rejected: leaving the timestamp in consensus-adapter metadata.**
`consensus-application-v1` already commits adapter metadata that never enters
canonical state, and CometBFT's own header carries a time. Reading it there would
make the month depend on which adapter is running, which contradicts ADR 0001's
replaceable-adapter rule and ADR 0050's requirement that execution read an agreed
application field.

**Rejected: a state entry written by a transition.** Nothing could write it: a
transition has no input that is not already in the block, so the value would have
to arrive as a transaction, and a transaction asserting the time is a value one
node supplies and another cannot reproduce — the same defect that stopped version
eight encoding a duty report.

### 2. The state root commits to the timestamp

The version-nine state carries `timestamp` beside `height`, and the state-root
frame gains it.

**This is forced rather than chosen.** C2 compares `t(h)` with `t(h - 1)`. A
machine that restarted, restored from a snapshot, or reconstructed from the
durable head must know its predecessor's timestamp to validate the next block at
all, and a value two machines could hold differently without their roots
differing is a fork no gate catches. It is version one's argument for committing
to `height`, applied to the second field that orders blocks.

**The cost is that the challenge beacon widens**, because version eight's
`beacon(h)` is the state root at `h - 1`. On a quiet height, where version
eight's root was fully determined, a proposer now has about `2^16.9` timestamp
values inside C5 to grind over. The marginal risk is small — a challenge harms
only a seat that cannot answer, and sparing one seat across a slot needs
essentially every proposal — and it is the same beacon bias ADR 0027 already
refers to independent review.

**Rejected: a beacon that excludes the timestamp.** It removes the new freedom and
costs a second root construction on the pipeline's most adversarial path: the
beacon would stop being a value the header already carries. Recorded so a later
version binding a real challenge predicate can revisit the beacon as one decision
rather than two.

**Rejected: storing the timestamp durably without committing to it.** It is the
cheapest possible change and it is the fork described above.

### 3. C1 and C2 execute; C5 is admission-only and is exposed separately

Range and monotonicity are deterministic and are re-applied on every replay; both
are block-level conditions that reject a block and produce no transaction result,
exactly as `ledger-transition-v1`'s height rule does. The tolerance reads a clock,
is applied once when a machine first validates a height, and is **never**
re-applied.

**This is `calendar-v1`'s rule rather than a choice**, and it is recorded here
because getting it wrong is silent: a machine that re-applied C5 on replay would
reject the chain's own past one tolerance-width after it was produced. What
version nine adds is the requirement that a conforming implementation expose the
two paths as separate entry points, so that the replay path cannot reach the
clock by accident.

### 4. A window's month is written at its opening height and read at its assignment

Entry kind 20 holds `month_index` for each window whose opening height has passed
and whose assignment has not — the open window and the two inside the assignment
lag. Genesis writes window 0's, because height 0 does not exist and genesis is
window 0's opening height.

**Rejected: deriving the month from the assigning block.** It is the natural
implementation and it is the systematic distortion
`unreferred-pool-payout-v1` rejects by name: assignment runs two windows late, so
about two days of every month's uptime would land in the next month, every month,
and a participant would feel it. The founder answer is "the uptime it accumulated
**during that month**", so attribution follows when the uptime happened.

**Rejected: retaining past timestamps so the month can be recomputed.** A ring of
57,600 heights of timestamps to re-derive a value already known at the moment it
was cheap, on the pattern version eight refused for the beacon.

### 5. The settlement cursor is its own singleton entry

Entry kind 23 holds `accumulating_month`, initialised at genesis to
`month_index(genesis_timestamp)` and set at each assignment to the assigned
window's month.

**Rejected: a fourth field on the unreferred pool entry.** The cursor describes
where the window grid has reached on the calendar, not what the pool holds, and it
would still be needed on a chain whose pool was permanently empty. Five octets is
the whole cost of keeping two subjects apart.

**Rejected: keeping the previously assigned window's month entry one window
longer**, so the predecessor's month is readable and no cursor is needed. It works
for every assignment but the first, where there is no predecessor window at all,
and a special case that fires exactly once in a chain's life at height 57,600 is
invisible forever after. A cursor written at genesis has no special case.

### 6. Exactly one month closes per assignment, and the rule says so

When the assigned window's month exceeds the cursor, version nine pays the cursor's
month and advances to the new one **in a single pass**, rather than iterating every
index between them.

**It is a derivation.** Window attribution is non-decreasing and consecutive
assigned windows carry the cursor's month and the new one with nothing between, so
every index strictly between them is an **empty** month — no window is attributed
to it, so it has no accrual and no candidates, and
`unreferred-pool-payout-v1`'s pass over it is a no-op that leaves the balance
exactly as it found it.

**It is also a bound, and that is why it is worth stating rather than leaving to
an implementation.** The gap between the two months is bounded by nothing a chain
controls: a network halted for a year resumes with twelve empty months between,
and a genesis timestamp decades in the past would close hundreds at the first
assignment. Iterating them would make one block's work proportional to how long
the network was down, which is a denial of service reachable by an outage rather
than by an attacker.

**The ascending-order rule is preserved and is not decorative.** It exists so a
carry from an earlier month reaches a later one, and under version nine only one
index can carry. The theorem underneath is that an empty month accrues nothing,
which is structural: accrual happens only at an assignment and an assignment
attributes to a month that by definition has a window. A later change that gave a
month an accrual with no window would have to restore the loop.

**The equivalence is evidence rather than an assertion**, and it has to be: no
invariant over a single accepted state separates the two rules, because they agree
on every state they both produce. The specification requires a multi-month halt
settled twice — once by the single pass and once by an explicit per-index loop
over the same scenario — and requires the two to agree state for state.

### 7. A winner's award is a per-seat running balance, minted whole by kind 22

Entry kind 22 is `accrued` and `minted` keyed by the seat — the referral balance's
shape. Transaction kind 22 mints the whole difference to any escrow the seat's
identity owns, on kind 4's body, authority ladder, posture confirmation, and fee.

**Rejected: a per-month-per-seat claim**, which is how this was provisionally
described before the slice ran. It would make collecting `n` months cost `n`
transactions and `n` fees, would require the mint to name a month or walk a range,
and would hold an entry per win forever for a seat that never collects. The
founder-directed rule **"a mint takes everything with no quantity choice"** — the
owner's answer in M3.8a, which kinds 4, 5, and 18 all implement — decides it, and
the reasoning the owner gave then is the same reasoning here: a mint that can take
a chosen amount must record what it took.

**Rejected: folding the award into kind 5 with an identity-keyed balance.** Both
draw on the referral channel, so the accounting would work, and it would add no
transaction kind. It conflates two different earnings under one number — "I
referred people" and "my machine performed best" — loses the per-seat attribution
when two seats of one owner tie, and reinterprets an accepted transaction's
meaning rather than adding one beside it.

**Rejected: crediting an address directly.**
[ADR 0041](0041-the-seat-is-tied-to-the-identity-not-an-address.md) ties a seat to
the owner's verified identity rather than to any address, so there is no canonical
address a payout could credit; a rule that credited one would have to invent it.
`unreferred-pool-payout-v1` already records this as a deduction.

**Keyed by the seat rather than by the identity**, because the winner is a seat and
two seats of one owner can both win in a tie. The mint's authority is still the
seat's identity, which is kind 4's rule unchanged.

### 8. Version nine adds no result code

Kind 22 reuses kind 4's ladder exactly, so every refusal it can produce already
has a number: `CYCLE_RANGE`, `SEAT_NOT_PURCHASED`, `SEAT_NOT_ACTIVATED`,
`UNAUTHORIZED`, `ESCROW_NOT_FOUND`, `ESCROW_NOT_OWNED`, `NOTHING_TO_MINT`,
`BIOMETRIC_REQUIRED`, and `CHANNEL_CAP`. The space stays at 45.

That is a property rather than an accident, and the opposite would be worth
noticing: a new mint needing a new refusal would be a mint whose authority rules
differ from every other mint's. The timestamp conditions `calendar-v1` names are
block-level and belong to the application contract's status space, not to this
document's transaction result space.

### 9. The monthly figure's key carries its month

Entry kind 21 is keyed `(month_index, seat_id)` even though exactly one month ever
accumulates, so the seat alone would have done and would be four octets shorter.

**Rejected: keying by the seat alone.** It is version eight's choice for the seat
window record restated: a stale entry from another month is then visibly wrong
rather than silently counted, and the invariant that catches it can be stated over
the state instead of over the history that produced it. Only nonzero figures are
written, and a decoder refuses a zero, because a zero figure is a second encoding
of absence.

### 10. The application contract needs a version, and this document does not write it

`consensus-application-v1` states that timestamps are not application transition
inputs and freezes its local frame at version 1. Both become false under version
nine: `ProcessProposal` and `FinalizeBlock` must carry the proposed timestamp,
`InitChain` the genesis timestamp, and the two must differ in exactly one respect
— `ProcessProposal` applies C5 and `FinalizeBlock` never does.

`economy-transition-v9` states what that contract must gain and stops there, which
is version eight's layering: the transition defines the contract and the stack
slices carry it. Writing both in one document would put a wire encoding inside a
consensus transition.

## Consequences

**A ninth chain identity, and a stack migration behind it.** A new chain ID, state
root, economy tree, block ID, genesis schema, and receipt version re-version the
snapshot, the owning store, the application layer, the transport, the node
process, and the ABCI adapter, which took ten slices for version seven and seven
for version eight. Version eight cannot be edited — its own versioning section
forbids it — so the alternative was not available rather than rejected.

**The block header changes for the first time**, so every component that parses
one parses a different shape, and the local application protocol gains a frame
version alongside its own contract version. That is the largest single difference
between this migration and version eight's, which touched no header at all.

**The unreferred pool stops accruing without limit.** From version nine the pool
has a `payable` balance that a monthly settlement empties into claims, and the
referral channel's outstanding term splits into a balance and a set of claims
without changing its total. No unit is created or destroyed by anything in this
decision.

**A month's ranking is only as honest as the measurement beneath it.** Version
eight measures liveness of a responder rather than possession of a resource, so
the figure this version ranks on is a count of answered audits. A later version
binding a real challenge predicate tightens what the monthly pool rewards without
changing a rule in this one.

**The founder-decision gate passed with nothing reserved.** Twenty-two decisions
were enumerated before any was judged; three are founder answers this version
implements (ADR 0075 and ADR 0076), six are fixed by `calendar-v1` and
`unreferred-pool-payout-v1`, and thirteen are encoding, storage, ordering,
packaging, and naming. **One was close enough to reserved to be worth naming**:
whether a winner's award is a running balance or a per-month award decides how many
transactions and fees a participant needs in order to collect, which is a question
about what an end user must do to be paid. It is delegated because the owner
already answered it in M3.8a; had no such answer existed, the slice would have
stopped and asked.
