# Economy scenario suite v1

Status: Accepted M2 evidence contract; not a consensus transition and not a
new model

> **Superseded on 2026-08-07 by
> [ADR 0023](../decisions/0023-founder-decisions-activity-referrals-and-supply.md).**
> The scenario parameters that stood in for unresolved founder decisions are
> now decided, so a version two suite derives them instead of supplying them.
> This document is not edited: it states the contract that the accepted M2
> models implement and that the M2 evidence proves.

This document fixes the deterministic multi-year and adversarial scenarios that
the four accepted M2 models must survive, as required by requirement 13 of
[`m2-founder-economy-proof.md`](../project/goals/m2-founder-economy-proof.md).

The change is classified as evidence, not economics. ADR 0022 records the
alternatives and decision. It changes no M1 bytes, C++ state, configured devnet
supply, and no accepted schema, vector, or digest of
`founder-economy-manifest-v1`, `founder-economy-simulator-v1`,
`founder-seat-schedule-v1`, `revenue-routing-v1`, or `escrow-payout-v1`.

## Scope

Version one defines four named scenarios, the restart-equivalence method, and
the seeded property tests that assert each model's conservation equations.

It adds no model, no transition, no event kind, and no canonical value. Every
event generated here parses under an event schema an accepted model already
defines. A scenario that cannot be expressed under an accepted schema is
evidence about that schema and is recorded as an open gap; it is never met by
widening one.

It does not establish that the modelled economics are sound. A long run that
conserves value is evidence about arithmetic and state transitions, not about
whether the activity metric is fair, whether a snapshot reflects a real machine,
whether a recipient is legitimate, or whether an approval threshold is safe.

### Why the four unresolved founder decisions still do not appear

The activity result, the inactive-cycle performance allocation, the
inactive-cycle referral decision, the direct-channel eligibility result, the
active-seat snapshot, the seat payment settlement, and the AI payout approval
remain supplied research inputs bound to the exact action they authorize. A
multi-year scenario needs thousands of them, which is precisely the pressure
under which a fixture becomes policy by habit. Each generator therefore supplies
them from a stated, deterministic rule that is recorded here as a scenario
parameter, and no generator derives one.

## Determinism rules

- Every generator is a pure function of its fixed parameters or of an explicit
  integer seed.
- No wall clock, environment variable, filesystem order, hash-ordered
  iteration, or unseeded random source reaches an event.
- Seeded sequences use `random.Random(seed)` from the standard library, so a
  failing property names a reproducible input.
- Amounts are native atomic units under the denomination accepted in
  `founder-economy-manifest-v1`, except in the seat sale, which is denominated
  in USD cents as `founder-seat-schedule-v1` fixes.

## Scenario 1: `economy_population`

A complete 731-cycle run over a staggered three-seat population against
`founder-economy-simulator-v1`.

### Parameters

| Parameter | Value |
| --- | ---: |
| Seats | 3 |
| Referrers | seat 1 and seat 2 both refer to seat 0 |
| Activation stagger, in ticks | 61 |
| Inactive period | 73 |
| Inactive phase per seat | 7 |
| Cycles per seat | 731 |

The Founder Constitution gives each seat 731 eligible cycles beginning at that
seat's own first activation, so seats activated on different dates hold
different windows. The simulator has no global clock, so the stagger is
expressed as event order: at tick `t`, the seat activated at tick `k * 61`
evaluates its own cycle `t - k * 61`. Every seat completes exactly 731 cycles
and all three windows overlap in different phases for most of the run.

Seat `k` is inactive in cycle `c` when `(c + 7k) mod 73 == 0`. The phase shift
keeps the three seats' inactive cycles disjoint, so the seat that receives a
reallocated Founder leg is itself active in that cycle. An inactive cycle
supplies a performance allocation crediting the whole 342-unit leg to seat
`(k + 1) mod 3`, and supplies an inactive-cycle referral decision that creates
the referral permission when the cycle index is even and withholds it when odd,
so both branches of that unresolved founder choice are exercised across the
window.

Both seat 1 and seat 2 refer to seat 0, so one referrer accumulates the referral
benefit of two seats for the entire multi-year window. That is the
concentration case for referral value.

### Required derivations

Each of these is computable in closed form from the Founder Constitution and
must equal the value the run produces:

| Quantity | Closed form |
| --- | --- |
| Venture escrow issued | `3 × 731 × 17_100_000_000` |
| Community-grants escrow issued | `3 × 731 × 3_420_000_000` |
| Developer-incentives escrow issued | `3 × 731 × 1_710_000_000` |
| System Creator royalty issued | `3 × 731 × 1_000_000_000` |
| Founder operator channel issued | `3 × 731 × 34_200_000_000` |
| Referral channel issued | `1_452 × 1_710_000_000` |
| Evaluated permission keys | `3 × 731 + 2 × 731` |

The Founder operator total is independent of inactivity: a reallocation changes
the beneficiary of the 342-unit leg, never its amount. The referral count is
`2 × 731` less the ten inactive referral cycles whose supplied decision withheld
creation.

Per-seat custody must equal `active_cycles × 34_200_000_000` plus each
reallocation received plus, for seat 0, the whole referral channel.

### Required rejections

The run ends with five adversarial probes, each of which must be rejected
without changing state:

| Probe | Result |
| --- | --- |
| Evaluate cycle 731 | `CYCLE_RANGE` |
| Re-evaluate cycle 730 | `REPLAY` |
| Re-exercise cycle 730 | `PERMISSION_NOT_FOUND` |
| Re-activate seat 0 | `REPLAY` |
| Referral permission for the unreferred seat 0 | `SEAT_NOT_REFERRED` |

The first is the exhaustion boundary: the issuance period ends exactly at the
731st cycle, and no later cycle exists to evaluate.

## Scenario 2: `seat_concentration`

The maximally concentrated complete sale against `founder-seat-schedule-v1`.

Exactly 100,000 seats may be sold and one human may control at most 1,000, so
the smallest population that can absorb the entire capacity is exactly 100
principals. This scenario runs that sale end to end. Each time a principal
reaches its bound, one further purchase by that principal is attempted, so a
saturated principal is proved not to consume a seat across the whole sale rather
than only in a short fixture.

### Required derivations

| Quantity | Value |
| --- | ---: |
| Seats sold | 100,000 |
| Distinct principals | 100 |
| Largest principal holding | 1,000 |
| Proceeds, USD cents | 423,185,500,000 |
| Over-limit attempts | 99 |

The proceeds must equal the sum of the constitutional block schedule, derived
independently of the model, and equal the `founder-seat-schedule-v1` full-sale
constant.

### Required rejections

| Probe | Result |
| --- | --- |
| A saturated principal's next purchase | `PRINCIPAL_SEAT_LIMIT` |
| A fresh principal after capacity is gone | `CAPACITY_EXHAUSTED` |
| A replayed purchase identifier after capacity is gone | `REPLAY` |

Replay is checked ahead of capacity, so an exhausted sale is still not a place
where replay stops mattering.

### Recorded limitation

The per-principal bound is not a per-human bound. Nothing in this scenario shows
that two principal identifiers are two people. That gap belongs to the biometric
enrollment milestone.

## Scenario 3: `routing_population`

A 122-cycle run against `revenue-routing-v1` whose active Founder population
changes every cycle.

The active population size for cycle `c` is `(7c) mod 5`, and the seats are
`(13c + i) mod 97` for `i` below that size, deduplicated and strictly ascending.
The size therefore walks every residue, so the run contains empty, singleton,
and multi-seat cycles in a fixed order, and 25 of the 122 cycles are empty.

One commercial payment and one transaction fee are routed in every cycle. The
payment amount is `1_000_000_007 + 999_983c` and the fee is `500_003 + 97c`;
both steps are coprime to the 200-residue routing period, so successive payments
walk the remainder classes instead of repeating one. Every third cycle carries a
product creator, so both the 45 and the 22.5/22.5 creator cases recur.

### Required properties

- Commercial conservation: the System Creator balance, all creator balances, all
  seat commercial balances, the commercial pool, and the commercial carry sum
  exactly to the commercial routed total.
- Fee conservation: all seat fee balances, the fee pool, and the fee carry sum
  exactly to the fee routed total.
- The routed totals equal the independently summed payment and fee amounts.
- An empty cycle distributes nothing and carries its whole pool forward. Nothing
  is burned by an absent population.
- The pool an empty cycle carries is distributed by the next cycle with an
  active population, so the carry is a delay and not a loss.
- After any cycle with an active population, the carry is strictly below the
  active seat count.

The empty-cycle count is recorded three times over: from the generator's
population rule, from the verifier's independent restatement of that rule, and
from the trace, as the number of accepted closes that credited no seat. The
third agrees with the other two only because every pool in this scenario exceeds
its active seat count, so a per-seat share is never zero. That condition is
stated rather than assumed, because a scenario with smaller payments would break
the agreement without breaking the model.

The run ends one cycle after an empty cycle so the recorded final state contains
value that an empty cycle carried and a later cycle distributed.

### Required rejections

| Probe | Result |
| --- | --- |
| A replayed payment identifier | `REPLAY` |
| Closing a cycle that is not the current one | `CYCLE_MISMATCH` |
| Closing with a snapshot describing another cycle | `INVALID_RESEARCH_INPUT` |

## Scenario 4: `escrow_drain`

A run against `escrow-payout-v1` that exhausts every envelope and drains every
escrow, bound to scenario 1's final state.

`bind_opening_custody` consumes the canonical `founder-economy-simulator-v1`
state value produced by the `economy_population` run. This is the join between
the two models: the escrows are drained of exactly what three seats issued into
them across their complete 731-cycle windows. The bound digest recorded for this
scenario must equal the state digest recorded for scenario 1.

Each escrow's custody is divided into seven payouts. Seven divides none of the
three opening amounts, so each escrow's final payout is a remainder rather than
another full per-payout maximum, and the seven together drain the escrow
exactly. The draining capability's envelope equals that escrow's opening
custody.

### Required properties

- Every escrow ends with zero available custody.
- For each escrow, `opening == available + paid_out`, `paid_out` equals the sum
  of that escrow's recipient balances, and `paid_out` equals the sum of `spent`
  across the capabilities bound to it. The three equations share no term.
- No payout touches two escrows, and custody never rises after the bind.

### Required rejections

Exhausting delegated authority and exhausting the escrow are different
operational events, so each escrow proves both separately:

| Probe | Result |
| --- | --- |
| A further payout on the drained capability | `ENVELOPE_EXCEEDED` |
| A payout on a freshly granted capability with authority to spare | `INSUFFICIENT_CUSTODY` |

The second is a statement about the escrow rather than about the delegation, and
it is reachable only because the first probe's envelope check precedes the
custody check.

## Restart equivalence

A node that stops after `k` events and resumes from persisted state must reach
the state a single uninterrupted run reaches. Two checks establish that for
these scenarios.

**Prefix replay.** For a prefix length `k`, running the first `k` events from
the initial state must produce the state digest that the complete run reached
after its `k`-th event. For `founder-economy-simulator-v1` the complete run
already records `state_digest_after` on every trace record, so the comparison
needs no additional machinery. For the other three models the complete run's
digest at `k` is obtained by applying the same events through the model's own
`apply_event` and taking its exported `state_digest`.

**Split resume.** Applying events `0..k` and then events `k..n` to the same
state object must produce the digest that one call over all `n` events produces.

Both checks use only functions the accepted models already export. Neither adds
a resume transition, a snapshot format, or a persisted state encoding; those are
M3 obligations.

## Seeded property tests

For each model, seeded random event sequences are generated and the model's
conservation equations are asserted against the recorded final state and
metrics, not against any recorded total.

The generators deliberately emit replays, unbound research fixtures, withheld
approvals, over-limit amounts, and out-of-order cycles alongside legal traffic.
A generator tracks just enough state to keep a useful share of its events
acceptable; that prediction affects only which cases are reached and is never
asserted.

The asserted properties are:

| Model | Property |
| --- | --- |
| `founder-economy-simulator-v1` | `issued + outstanding + remaining == 5_574_394_010_000_000_000`; typed custody sums to issued supply; every channel's `issued + outstanding` is at or below its cap |
| `founder-seat-schedule-v1` | seat prices sum to proceeds; principal counts sum to seats sold; no principal exceeds 1,000; seats sold is at or below 100,000 |
| `revenue-routing-v1` | commercial and fee conservation as in scenario 3; no balance is zero |
| `escrow-payout-v1` | per-escrow `opening == available + paid_out`; recipient balances and charged envelopes each equal `paid_out`; custody never rises after the bind |

Every rejected event in every sequence must carry an empty journal, and for
`founder-economy-simulator-v1`, whose trace records digests on both sides of
each event, a rejected event's state digest must be unchanged.

The assertions are written against the models' published result values and share
no code with the models' own invariant checks, so a defect in an invariant does
not silently satisfy the property.

## Required vectors and evidence

`test-vectors/economy-scenario-suite-v1.txt` records, for each of the four
scenarios, the event, accepted, and rejected counts, the four digests, the
derived totals named above, and each named boundary probe's rejection code.

It does not record an ordered trace. `escrow-payout-v1` records one because its
scenario is 39 events; a 100,101-event scenario cannot be reviewed that way, and
a file nobody reads is not evidence. The trace digest pins the order instead.

The verifier in `tools/scenario-suite-vectors/` must:

1. run all four scenarios and derive every recorded value from the live runs;
2. re-derive the expected totals in closed form from Founder Constitution
   literals it carries itself, importing nothing from `simulation/`, and require
   the live runs to agree with them;
3. require the escrow scenario's bound digest to equal the economy scenario's
   state digest; and
4. fail closed when a recorded key is never derived.

The closed-form derivation is what makes this independent. A second walk of four
models would re-implement thousands of transitions to learn totals that
multiplication already fixes; the arithmetic the constitution states directly is
both cheaper and a stronger check.

## Versioning and compatibility

This suite is additive evidence over five accepted contracts. Changing a
scenario parameter changes its recorded digests and requires a new suite version;
it does not affect any model's schema or vectors.

If a future change to an accepted model's canonical state shape alters a digest
recorded here, this suite must fail rather than adapt. That is the intended
coupling: the scenarios exist to notice such a change.

## Open gaps this suite does not close

- The seat sale, the economy simulator, and the routing model remain unjoined. A
  seat purchased in scenario 2 is not an activated seat in scenario 1, and a
  seat identifier in a routing snapshot is proved to be neither, because the
  activation-height rule and the purchase-to-activation transition are unsettled.
- The per-seat balance carry in `revenue-routing-v1` and the recipient balances
  in `escrow-payout-v1` still have no storage bound at 100,000 seats, and no
  claim or push mechanism moves a credited balance into a spendable account.
- Restart equivalence here is state equivalence under replay. It is not
  persistence, crash-consistency, or a snapshot format.
- A long run that conserves value proves accounting. It proves nothing about
  activity fairness, snapshot honesty, creator legitimacy, approval quality, or
  the safety of any threshold.
