# ADR 0014: Cross-principal admission-cost boundary study

- Status: Accepted for M2 research
- Date: 2026-08-02

## Context

ADR 0013 found that participant-scoped reward capping is profitable to split
when one registered owner controls multiple participant identifiers. Grouping
by the registered owner removed that measured advantage, but the registration
contract does not prove that different owner or payout labels represent
different real principals. A hidden operator can therefore put each identity
in a different registered scope and recover the participant-scoped result.

Before proposing an identity system or admission price, M2 needs to locate the
exact cost at which that strategy stops being profitable and compare it with
the reward available to the smallest accepted honest contributor. It must
distinguish a recurring or identity-specific expense from a refundable native
bond: refunded principal is locked capital, not a consumed fee. It must also
show how identity churn changes the number of admissions and locked-capital
exposure.

Primary-source review informed the decision:

- Douceur shows that distinct remote identities cannot generally be treated as
  distinct entities without a trusted certification authority or strong
  resource assumptions. Different registered labels therefore remain study
  scopes, not unique-principal evidence. Source: [The Sybil Attack][sybil].
- Budish distinguishes recurring flow expenditure from a one-time stock-like
  resource. That distinction supports keeping per-identity operating expense
  separate from refundable locked principal. No proof-of-work rule or attack
  model is adopted. Source: [The Economic Limits of Bitcoin and the
  Blockchain][budish].
- Gans and Gandal extend that comparison to proof of stake and characterize
  its cost as illiquid financial resources. This supports measuring bond
  amount-times-lock exposure and a separate capital-time charge instead of
  subtracting the returned principal from utility. Source: [More (or Less)
  Economic Limits of the Blockchain][gans-gandal].
- Ethereum's consensus specification separates validator deposits, activation,
  exit, and later withdrawal. It is evidence that a deposit can remain
  unavailable across lifecycle intervals; no Ethereum balance, duration,
  slashing, validator, or reward rule is adopted. Source: [Ethereum Phase 0
  validator lifecycle][ethereum-validator].

These sources are comparative evidence only. The study is original,
standard-library-only Python research tooling.

## Classification

This is an economics and mechanism-design research change. It changes no
consensus transition, canonical encoding, cryptography, compatibility surface,
accepted simulator behavior, production identity policy, actor, price, fee,
bond, duration, reward rate, or C++ code.

## Decision

### Hold work fixed across hidden-principal identities

Retain the six ADR 0012 survivor families and both participation roles. At
each exact-support coordinate, hold dominant work at sixteen raw contribution
units, sweep its selected weight through `1..16`, and sweep one honest
participant's raw units through `1..20` at weight one.

For identity count `k = 1..16`, partition the sixteen dominant units by exact
quotient and remainder in ascending participant order. Every identity receives
at least one unit. Give every dominant identity a distinct participant,
registered owner, and payout label, while recording one hidden-principal label
only in the study. Total dominant units and weighted score remain invariant.

Evaluate the unchanged proportional, participant-cap, and principal-cap
mechanisms. Because registered principals are distinct, the two capped
mechanisms must produce identical payouts; a mismatch is a study failure. The
proportional mechanism remains the unchanged control.

### Derive integer operating-cost boundaries

Measure gross utility in the same integer atomic-unit numeraire as calculated
reward payout. This is a comparison unit, not a native claim or token-price
assumption. For a nonnegative integer per-identity operating cost `c`:

```text
net_utility(k, c) = dominant_payout(k) - k * c
split_advantage(k, c) =
  dominant_payout(k) - dominant_payout(1) - (k - 1) * c
```

For each positive zero-cost gain, derive the minimum deterring integer cost by
ceiling division. Take the maximum across identity counts and exact-support
coordinates. Do not enumerate a chosen cost grid.

The honest-entry ceiling is the minimum payout to the one-unit honest
participant at the corresponding unsplit coordinates. A nonempty inclusive
integer interval between the deterrence floor and honest-entry ceiling is the
predeclared joint objective. Zero payout is retained as evidence; it is not
silently treated as successful entry.

### Treat a refundable bond as capital-time exposure

Represent a research admission bond with an unchanged native-economy general
escrow so it applies uniformly to validator and node study identities without
repurposing validator stake. The account-funded principal must remain in
issued supply, reject release before its unlock epoch, and return completely
to its owner at unlock. No bond is slashed, spent, rewarded, or routed.

For bond amount `b`, active duration `a`, post-exit lock `l`, and nonnegative
rational capital-time rate `n/d`, define checked exposure and integer charge:

```text
exposure = b * (a + l)
capital_time_cost = ceil(exposure * n / d)
```

The report derives exact open/inclusive rational rate boundaries as functions
of `b` for every `l = 1..16`; it does not choose `b`, `n/d`, an asset price, or
an annualized return. Refundable principal is never subtracted from utility.

### Make persistent and churn strategies explicit

Compare eight contribution epochs plus the accepted four drain epochs. A
persistent strategy reuses `k` identities; a churn strategy uses `k` fresh
identities each contribution epoch. Both hold sixteen dominant units and one
honest unit fixed per epoch. Operating cost is paid once for every distinct
admitted identity. Bond exposure counts each identity's active epochs plus its
post-exit lock, so churn cannot reuse a still-locked bond in the projection.

Record distinct admissions, incremental identity and exposure counts, gross
gain, hidden-principal concentration, exact operating break-even, and exact
bond-rate break-even. Separately replay unit native escrows for every lock
length to prove early-release refusal, complete refund, supply conservation,
and deterministic peak churn lock.

### Preserve funding and accepted boundaries

Cross-check representative unsplit, two-way, and sixteen-way proportional
points through participation v1 and its unchanged funding adapter. Fund every
trajectory payout through an independently pre-funded native-economy v1 reward
pool. Pending research credit and utility cost never become native claims.

The normative contract is
`../specifications/admission-cost-study-v1.md`.

## Alternatives not selected

- **Treat different owner labels as different principals:** ADR 0013 and
  Douceur make that assumption unsupported.
- **Choose a registrar or proof-of-personhood provider:** this experiment
  measures the gap that such a system would need to close; it cannot select
  one without security, privacy, governance, and recovery analysis.
- **Charge or burn an irreversible admission fee:** doing so selects a native
  value route and can exclude low-reward entrants. This study derives the
  boundary before choosing any recipient or disposition.
- **Count refundable principal as cost:** the owner receives it back. Only
  checked capital-time exposure and an explicit opportunity-charge rate enter
  utility.
- **Select an interest rate, token price, or production bond grid:** exact
  threshold formulas preserve every integer cost and rational-rate case
  without promoting synthetic coordinates.
- **Change the accepted cap or participation contracts:** retaining them makes
  hidden-principal scope failure independently reproducible.

## Consequences

- M2 gains exact split-deterrence and honest-entry boundaries across every
  hidden-principal identity count in the bounded design.
- Refundability, lock duration, churn, and capital-time charge remain separate
  observables instead of one ambiguous admission price.
- A feasible interval would remain only a research hypothesis; an empty
  interval directly rejects cost-only admission across the tested support.
- The study cannot prove unique identity, empirical operator cost, capital
  scarcity, strategic equilibrium, work quality, demand, or production
  safety.
- Any production admission mechanism still requires empirical inputs,
  independent economic, privacy, and security review, and a separate consensus
  ADR, specification, activation, and migration contract.

[sybil]: https://www.microsoft.com/en-us/research/wp-content/uploads/2002/01/IPTPS2002.pdf
[budish]: https://www.nber.org/papers/w24717
[gans-gandal]: https://www.nber.org/papers/w26534
[ethereum-validator]: https://ethereum.github.io/consensus-specs/phase0/validator/
