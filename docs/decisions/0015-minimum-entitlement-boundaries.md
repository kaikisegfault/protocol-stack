# ADR 0015: Minimum-entitlement and hidden-principal split boundaries

- Status: Accepted for M2 research
- Date: 2026-08-02

## Context

ADR 0014 found eighty survivor-family, role, and selected-weight coordinates
where the unchanged proportional entitlement of a one-unit honest participant
is zero. It also found that the accepted capped mechanisms remain profitable
to split when one hidden principal can register distinct participant, owner,
and payout labels. A minimum entitlement could make the smallest accepted
contribution live, but a reserve attached to each registered participant could
also pay the same hidden principal once per label.

M2 therefore needs a bounded comparison before selecting any production floor
or reward rate. The comparison must keep useful work and the accepted reward
mechanisms fixed, separate a participant-labelled reserve from a reserve
proportional to accepted raw work, and expose the exact point at which each
family ceases to be fully funded.

Primary-source review informed the decision:

- Yokoo, Sakurai, and Matsubara show that one actor's use of multiple fictitious
  names can change mechanism outcomes and that resistance can trade off against
  other desirable mechanism properties. The study therefore evaluates a
  hidden principal across distinct registered labels instead of assuming those
  labels are independent actors. Source: [Robust Combinatorial Auction Protocol
  against False-name Bids][yokoo].
- Douceur shows that distinct remote identifiers are not general evidence of
  distinct entities without trusted certification or strong resource
  assumptions. No uniqueness claim is attached to a participant, owner, or
  payout label. Source: [The Sybil Attack][sybil].
- Shreedhar and Varghese allocate fair-queueing service by flow and explicit
  quanta. Their work is comparative evidence that the unit to which a reserve
  is attached is part of the fairness contract. This study compares a reserve
  per label with one per accepted raw-work unit; it does not adopt a packet
  scheduler or network-service guarantee. Source: [Efficient Fair Queuing Using
  Deficit Round-Robin][drr].

These sources do not determine a protocol reward. The study is original,
standard-library-only Python research tooling.

## Classification

This is an economics and mechanism-design research change. It changes no
consensus transition, canonical encoding, cryptography, compatibility surface,
accepted simulator result, production identity policy, actor, floor, rate,
budget, fee, claim, transaction, or C++ code.

## Decision

### Retain only the observed zero-entitlement coordinates

Rebuild the ADR 0014 unsplit support with sixteen dominant raw units, one
honest raw unit, selected weight `1..16`, the six ADR 0012 survivor families,
and both roles. Retain a coordinate exactly when the unchanged proportional
credit construction gives the honest participant zero credit. The reviewed
support must contain eighty coordinates. A count or ordering mismatch is a
study failure.

For dominant identity count `k = 1..16`, partition its sixteen raw units by
the unchanged quotient-and-remainder rule. Every dominant identity and the
honest participant have distinct participant, owner, and payout labels. The
study alone aggregates dominant payouts to one synthetic hidden principal.

### Compare three reserve families

For nonnegative integer floor `m`, positive participant raw work `u_i`,
weighted score `s_i`, role budget `B`, and positive participant count `N`,
compare:

```text
zero:               reserve_i = 0
per_participant:    reserve_i = m
work_proportional:  reserve_i = m * u_i
```

Zero raw work receives no reserve and contributes no score. Sum every reserve
with checked integer arithmetic before allocating anything. A form is feasible
only when total reserve is at most `B`. Infeasible forms have no credit or
payout projection; the study never clips, prorates, borrows, or creates a
claim. Allocate the remaining budget by the unchanged weighted proportional
floor formula, add each participant's reserve, then apply the unchanged
proportional or capped payout projection.

At `m = 0`, every payout map and observable must equal reward-distribution v1.
Because every registered principal is distinct, participant-cap and
principal-cap outputs must remain byte-identical.

### Derive exact funding boundaries

The fixed support has one honest raw unit and sixteen dominant raw units. For
`m > 0`, the exact feasibility boundaries are:

```text
per_participant:   m * (k + 1) <= B
                   maximum feasible k = min(16, floor(B / m) - 1)
                   maximum feasible m = floor(B / (k + 1))

work_proportional: m * 17 <= B
                   maximum feasible m = floor(B / 17), independent of k
```

Boundary calculations are primary outputs, not production recommendations.
Enumerate `m = 0..5` as the complete common comparison support because the
smallest retained budget is `100`, the largest positive participant count is
seventeen, and `floor(100 / 17) = 5`. Any larger global floor is infeasible for
at least one retained form. Per-coordinate formulas preserve larger local
boundaries without selecting or enumerating them.

### Expose both split comparisons

For floor family `f`, feasible floor `m`, and dominant identity count `k`, let
`G(f,m,k)` be total payout to the hidden dominant principal. Record:

```text
same_floor_split_gain = G(f,m,k) - G(f,m,1)
baseline_amplification = G(f,m,k) - G(zero,0,1)
```

The first isolates the benefit of extra labels under the same floor. The
second asks whether introducing the floor and allowing a split increases the
hidden principal's payout over the accepted unsplit baseline. Negative signed
results are retained.

For each family, mechanism, and coordinate, record the smallest common-support
floor that makes the honest payout positive and every same-floor split gain
nonpositive. Separately record the smallest floor satisfying honest entry with
no positive baseline amplification. A missing floor is `null`, not a pass.

### Preserve accepted work and native funding boundaries

Independently cross-check every zero-floor form against reward-distribution v1.
For reviewed boundary samples, reproduce accepted raw units and weighted
scores through participation v1, apply only the study-owned reserve projection,
and emit every nonzero payout through an independently pre-funded
native-economy v1 reward pool. Claims must equal calculated payouts and the
pool plus claims must equal initial funding.

The reserve is analytical allocation credit only. It is not an account balance,
debt, guaranteed claim, issuance event, escrow, fee, or transfer. The normative
contract is `../specifications/minimum-entitlement-study-v1.md`.

## Alternatives not selected

- **Give every registered participant an unconditional native payment:** this
  would turn an unverified label into a claim and makes split amplification the
  mechanism rather than an observable.
- **Pro-rate an infeasible reserve:** pro-rating defines another allocation
  family and can hide the exact budget-exhaustion boundary.
- **Reserve per weighted score:** the remaining-budget allocation already uses
  accepted weights. Repeating the weight in the reserve would not isolate
  whether the reserve unit is a registered label or raw accepted work.
- **Reserve per hidden principal:** that scope is unavailable to the accepted
  protocol and exists only as an analysis label.
- **Choose a floor from the experiment:** synthetic support can reject a family
  or locate boundaries, but it cannot establish empirical work value, demand,
  operator cost, identity uniqueness, or a sustainable issuance schedule.
- **Change the cap or credit-history contract:** keeping accepted behavior fixed
  makes any interaction with the reserve independently reproducible.

## Consequences

- M2 gains exact funding and identity-count boundaries for two materially
  different minimum-entitlement units.
- The report can distinguish honest liveness from hidden-principal payout
  amplification instead of treating a positive smallest payout as sufficient.
- A work-proportional reserve is arithmetically invariant to splitting fixed raw
  work before remainder allocation; that fact does not guarantee cap-level
  split resistance.
- A successful bounded coordinate would remain research evidence only. A
  failure rejects that family over the declared support but does not prove all
  possible reward mechanisms impossible.
- Any production floor still requires empirical economics, independent
  security and fairness review, and a separate consensus ADR, specification,
  activation, and migration contract.

[yokoo]: https://cdn.aaai.org/AAAI/2000/AAAI00-017.pdf
[sybil]: https://www.microsoft.com/en-us/research/wp-content/uploads/2002/01/IPTPS2002.pdf
[drr]: https://iqua.ece.toronto.edu/baochun/ece1771f/papers/deficitrr.pdf
