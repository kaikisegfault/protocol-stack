# ADR 0022: Multi-year and adversarial scenario evidence

- Status: Accepted for M2 evidence; scenario parameters superseded by ADR
  0023; not a consensus activation
- Date: 2026-08-05

> **Superseded in part on 2026-08-07.** The scenario parameters that stood
> in for unresolved founder decisions are answered by
> [ADR 0023](0023-founder-decisions-activity-referrals-and-supply.md), so a
> v2 suite derives them instead of supplying them. The evidence method below
> still holds.

## Context

`first-goal.md` requirement 13 asks for positive, negative, boundary, replay,
overflow, atomicity, population-change, inactivity, concentration, and complete
multi-year scenarios.

Requirements 1 through 12 already hold in model form. Each of
`founder-economy-simulator-v1`, `founder-seat-schedule-v1`,
`revenue-routing-v1`, and `escrow-payout-v1` carries its own fixture, vectors,
and verifier, and each verifier proves that its model reproduces the values
recorded for its own scenario. That is exactly the evidence a fixture can give,
and exactly its limit: a model that is correct on 39 events is not thereby
correct on 7,308, and a model that conserves value for one seat over one cycle
is not thereby conserving it for three seats over 731.

Five questions had to be settled before writing any scenario:

1. whether the suite extends the accepted models or stands beside them;
2. how a scenario's recorded totals can be checked independently, given that a
   second walk of four models is not affordable;
3. how a multi-year run supplies thousands of research inputs without a fixture
   quietly becoming policy;
4. what restart equivalence can mean for models that have no persistence; and
5. what a seeded property test should assert, when the models already assert
   their own invariants internally.

## Decision

### An additive suite, not a fifth model

Implement `simulation/scenarios/` as deterministic generators over the accepted
event schemas. The suite defines no transition, no event kind, no state, and no
canonical value, and it introduces no domain label. Every digest it records is a
digest an accepted model computes under a label that model already owns.

The alternative was a fifth model that composes the other four. That would have
needed its own schema and its own conservation story, and would have made the
long-run evidence depend on new code that has no independent verifier — the
opposite of what a scenario suite is for.

The boundary is stated positively: a scenario that cannot be expressed under an
accepted schema is evidence about that schema, and is recorded as an open gap
rather than met by widening one.

### Independence comes from closed-form derivation, not a second walk

The verifier carries the Founder Constitution's literals itself, imports nothing
from `simulation/`, and re-derives each scenario's expected totals by
arithmetic: three seats over 731 cycles issue `3 × 731 × 17_100_000_000` into
the venture escrow, and the complete concentrated sale yields the block schedule
summed directly.

`escrow-payout-v1` and `revenue-routing-v1` each ship a `walk.py` that
re-implements their transitions and shares no code with the model. Repeating
that pattern here would mean re-implementing four models to learn totals that
multiplication already fixes, and the re-implementation would then need its own
evidence. Closed-form derivation is both cheaper and stronger: it checks the run
against the constitution rather than against a second reading of the same
specification.

Where a total is not closed-form — a digest, or a count that depends on the
supplied research decisions — the verifier derives it from the live run and the
vector file pins it, exactly as the four model verifiers already do.

### Research inputs are supplied from stated rules, recorded as scenario parameters

A multi-year run needs thousands of activity results, performance allocations,
referral decisions, active-seat snapshots, payment settlements, and payout
approvals. That volume is precisely the pressure under which a fixture becomes
policy by habit.

Each generator therefore supplies them from a stated deterministic rule —
`(c + 7k) mod 73 == 0` for inactivity, `(k + 1) mod 3` for the performance
recipient, `(7c) mod 5` for the active population size — and every rule is
recorded as a scenario parameter in the specification. The rules are chosen to
exercise both branches of each unresolved decision, not to model a real
population. None of them is derived by a model, and none of them is a proposal.

The alternative, generating inputs randomly inside the named scenarios, would
have made the recorded digests depend on a seed rather than on a stated rule,
and would have hidden the fact that a founder decision is being stood in for.

### Restart equivalence is state equivalence under replay

The models have no persistence, so restart equivalence is defined as two
checkable statements. Prefix replay: running the first `k` events from the
initial state reaches the digest the complete run recorded after its `k`-th
event. Split resume: applying `0..k` and then `k..n` to one state reaches the
digest a single call over all `n` reaches.

Both use only functions the accepted models already export. Adding a resume
transition, a snapshot format, or a state encoding to make a stronger claim
would have been new consensus-shaped design inside an evidence slice, and those
are M3 obligations.

The claim is stated as narrowly as it holds: this is state equivalence under
replay, not persistence, crash-consistency, or a snapshot format.

### Property tests assert published values, not the models' own invariants

Each seeded sequence is run and the conservation equations are asserted against
the result's `final_state` and `metrics` — the published canonical values — with
arithmetic written in the test.

Calling a model's `assert_invariants` on its own final state would have been
shorter and would have proved nothing: the engine already calls it, so the test
would re-run a check whose failure it was supposed to detect independently. A
defect in an invariant must not be able to satisfy the property that is meant to
catch it.

The generators emit replays, unbound fixtures, withheld approvals, over-limit
amounts, and out-of-order cycles alongside legal traffic, and the properties are
asserted whatever the mix of acceptance turns out to be. A generator's internal
prediction of what will be accepted keeps the traffic interesting; it is never
asserted.

### The escrow scenario binds the economy scenario

`escrow_drain` binds the canonical state of the `economy_population` run rather
than a synthetic opening, and the vectors require its bound digest to equal that
run's state digest.

This is the existing `escrow-payout-v1` binding used at multi-year scale: the
escrows are drained of exactly what three seats issued into them across their
complete windows. It joins the two models over a long run without adding a
transition to either, and it is still the one-way read ADR 0021 accepted.

## Alternatives not selected

- **A fifth composed model:** needs its own schema, conservation story, and
  verifier, and makes long-run evidence depend on unverified new code.
- **Extend each accepted model with long-run scenarios in place:** would put
  scenario parameters inside contracts that ADRs 0018 through 0021 froze, and
  would spread one coherent evidence question across four specifications.
- **A second independent walk of all four models:** re-implements thousands of
  transitions to learn totals that arithmetic fixes, and the walk itself would
  need evidence.
- **Record only digests, with no closed-form totals:** a digest proves
  reproducibility and nothing about correctness; a run could conserve value
  perfectly and still issue the wrong amount.
- **Random inputs inside the named scenarios:** makes recorded digests depend on
  a seed rather than a stated rule and hides where a founder decision is stood
  in for.
- **Derive the activity metric, performance ranking, or approval policy to make
  long runs realistic:** every one of those is an explicitly deferred founder
  decision, and a multi-year run is the worst place to invent one because its
  scale makes the invention look like evidence.
- **Run the complete 100,000-seat population through the economy simulator:**
  the simulator clones state per event, so the run is quadratic in evaluated
  permission keys; 73.1 million cycles is not reachable, and three staggered
  seats over complete windows prove the same per-seat and per-channel arithmetic.
- **Assert invariants by calling each model's `assert_invariants`:** re-runs the
  check the engine already ran, so an invariant defect would satisfy its own
  test.
- **Add a resume or snapshot transition to make restart evidence stronger:** new
  consensus-shaped design inside an evidence slice, and an M3 obligation.
- **Skip the boundary probes because the fixtures already cover the codes:** the
  question at multi-year scale is not whether a code exists but whether it still
  fires after 7,300 accepted events, which is a different claim.

## Consequences

- Requirement 13 becomes executed evidence: a complete 731-cycle staggered
  population run, the maximally concentrated complete sale, a routing run whose
  population changes every cycle including 25 empty ones, and an escrow run that
  drains every escrow and exhausts every envelope.
- The four models are now proved to hold their conservation equations at
  thousands of events, not only at their fixtures, and to still reject boundary,
  replay, and authority violations after long accepted runs.
- The escrow model's binding is exercised at multi-year scale, and the suite
  fails loudly if either model's canonical state shape changes.
- No accepted schema, vector, or digest changes. No native units are created,
  and no C++ consensus, devnet, or bridge behavior is touched.
- The suite adds roughly a minute of hosted verification per matrix job: about
  24 seconds for the vector verifier, 19 for the market scenarios, 15 for the
  multi-year scenarios, and 3 for the properties. The economy population run is
  the dominant cost because the simulator clones state per event; that cost is a
  property of the accepted model and is not worked around here.
- A scenario parameter is now a recorded contract. Changing one changes recorded
  digests and requires a new suite version.
- Long-run conservation is proved. Nothing here shows that the activity metric
  is fair, that a snapshot reflects a real machine, that a creator or recipient
  is legitimate, that an approval threshold is safe, or that any of the four
  unresolved founder decisions has been answered.

## Compatibility and independent review

This ADR accepts an evidence contract. It activates no consensus transition,
creates no native units, and adds no canonical label or digest domain.

M3 must separately define persistence and the crash-consistency claim that
restart equivalence only gestures at here, the storage bounds on per-seat and
per-recipient balances that these long runs make concrete, the join between the
seat sale and seat activation, and the consensus receipts and numeric codes.
Surviving long deterministic runs is not production safety, and independent
protocol, economic, and adversarial review remains required.
