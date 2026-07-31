# ADR 0011: Orthogonal cross-simulator economic stress study

- Status: Accepted for M2 research
- Date: 2026-07-31

## Context

ADRs 0008, 0009, and 0010 define three independent research boundaries for
native-asset accounting, validator and resource-node participation, and
capability-scoped threshold authority. Their fixed studies establish local
invariants, but they do not expose interactions among issuance, fee routing,
reward obligations, stake and lifecycle delays, contribution weights,
penalties, authority availability, authority capture, and recovery latency.

M2 needs a reproducible screening study before any numerical economic value is
proposed for production. A full three-level Cartesian study across thirteen
factors would require 1,594,323 configurations before seed replication. An
unstructured random search would be smaller but would not prove balanced level
or pair coverage. The selected design must remain cheap enough for every
hosted verification preset while being explicit about the interactions it
cannot identify.

Primary-source review informed the decision:

- NIST describes three-level fractional factorial and orthogonal-array designs
  as economical screening designs that balance factor levels in relatively few
  runs and can expose curvature, while warning that they provide limited
  information about interactions. This supports an orthogonal first screen,
  not a claim that 27 cases establish an economic optimum.
  Source: [NIST three-level and fractional factorial designs][nist-oa].
- NIST defines orthogonal-array strength by full factorial coverage in every
  selected subset of that many factors. The study therefore proves strength
  two directly: every factor pair covers all nine ordered level pairs exactly
  three times.
  Source: [NIST DOE glossary][nist-glossary].
- The Basel Committee's stress-testing principles call for objectives,
  coverage, granularity, internally consistent scenarios, sufficiently severe
  and varied stresses, documented exclusions, sensitivity analysis, and
  reverse stress that starts from an adverse outcome. These are useful design
  disciplines even though this protocol is not a bank and no regulatory ratio
  is adopted.
  Source: [BCBS stress-testing principles][bcbs].
- EIP-1559 separates fee paths and documents that fee routing affects both
  validator incentives and issuance pressure. This project does not adopt its
  auction, dynamic base fee, burn, gas accounting, or Ethereum execution
  model; the source supports treating fee volume and fee destination as
  independent experimental factors.
  Source: [EIP-1559][eip-1559].
- Ethereum's proof-of-stake specification makes validator eligibility,
  activation, rewards, inactivity penalties, slashing, and exit timing
  separate bounded mechanisms. The project adopts none of its balances,
  formulas, constants, or validator-set transition, but the separation
  supports testing stake, delay, reward, and penalty families independently.
  Source: [Ethereum consensus specification][ethereum-consensus].

These sources guide experimental structure only. The model and implementation
are original, standard-library-only research tooling and have no external
runtime dependency.

## Decision

### Add a composition study, not simulator v2 behavior

Add `economic-stress-study-v1` as a deterministic orchestration layer over the
unchanged native-economy v1, participation v1, and authority v1 engines and
adapters. It introduces no new economic transition, authority rule, state
root, transaction, or simulator-v1 compatibility surface.

The study builds complete research manifests and ordinary events, asks the
accepted engines to validate and execute them, and summarizes exact outputs.
An accepted threshold result must release the exact privileged target event
before that target is presented to its simulator. Owner-authorized events stay
outside the authority adapter.

### Use a reviewed strength-two OA(27,13,3,2)

Use thirteen three-level factors and 27 configurations. Construct the array
over `GF(3)` from every row vector `(x, y, z)` and the thirteen normalized
nonzero projective directions in three dimensions. A cell is the direction's
dot product with the row modulo three.

The construction is versioned and tested rather than imported from a
statistics package. Every factor has each level nine times. Every pair of
factors has all nine ordered level combinations exactly three times. The
design is a screening design: main effects are balanced, but interactions may
be aliased and no regression estimate or statistical significance is claimed.

The factors are:

1. issuance amount;
2. fee volume;
3. fee share routed to rewards;
4. reward budget per role;
5. validator contribution weight;
6. resource-node contribution weight;
7. validator minimum bond;
8. penalty severity;
9. activation delay;
10. exit and unbond delay;
11. authority threshold;
12. authority rotation and recovery delay; and
13. a correlated honest-availability and compromise shock.

All three levels are small synthetic integers fixed by the normative study
contract. They are coordinate labels for screening, not candidate production
defaults or confidence intervals.

### Replicate deterministic actor variation

Each orthogonal configuration runs across an explicit bounded range of
`SplitMix64-v1` seeds. The seed changes contribution units and opaque evidence
digests only. It does not change the factor matrix, read a random device, or
introduce wall-clock or network state.

Version one defaults to eight seeds and permits one through sixteen. The
default report therefore contains 216 runs. The seed range is part of the
report identity and digest.

### Compose exact authorization and economic obligations

Each run builds:

- a participation lifecycle with two validators and two resource nodes,
  bounded contribution results, two finalized role budgets, entitlements, and
  one validator exit;
- a native-economy flow with capped issuance, fees, fee allocation, treasury
  reward funding, participant bonds, one bounded penalty, entitlement funding,
  reward claims, and unbond completion; and
- authority results for every privileged target in those flows, one captured
  issuance attempt, one dual-threshold rotation, containment, and delayed
  recovery.

The correlated shock has three named levels. As severity rises, honest
available members fall from three to one while compromised available members
rise from zero to two. Legitimate actions use only the honest subset; the
captured issuance attempt uses only the compromised subset. The configured
threshold therefore exposes both availability loss and the exact point at
which collusion can authorize a bounded capability.

The study does not claim that members are statistically independent, that an
opaque approval is authentic, or that the synthetic correlation describes a
real deployment.

### Define objectives before observing results

Every run reports exact Boolean objectives for:

- native supply conservation and cap adherence;
- legitimate authority availability;
- successful rotation and delayed recovery;
- complete participation execution;
- complete entitlement funding;
- complete native-economy execution;
- absence of configured-threshold capture; and
- an explicit research concentration bound.

Reverse-stress codes identify the objective failures that produced a run's
classification. A run is `infeasible` when configured-threshold capture,
supply failure, or a fully created obligation cannot be funded. It is
`fragile` when those conditions are absent but availability, lifecycle,
control recovery, complete execution, or concentration objectives fail. It is
`robust` only when every objective passes.

These names compare synthetic configurations under this study. They are not a
mainnet readiness assessment and cannot establish an economically optimal or
safe production range.

### Preserve integer and compatibility boundaries

All configuration values, events, state, metrics, counts, ratios, and digests
are integer-only. Ratios are reduced numerator/denominator objects. Replay
uses no floating point, wall clock, network input, model inference, signature
verification, package dependency, or mutable external dataset.

The normative contract is
`../specifications/economic-stress-study-v1.md`. A later production parameter
proposal requires focused high-resolution experiments around any surviving
family, independent economic and security review, and a separate
consensus-visible ADR and specification.

## Alternatives not selected

- **Full `3^13` factorial:** it provides complete interaction coverage but is
  needlessly expensive for an initial screen and would make every hosted
  verification run execute more than 1.5 million configurations per seed.
- **One factor at a time:** it is easy to interpret but cannot expose paired
  fee, funding, weight, delay, and authority interactions.
- **Unstructured seeded Monte Carlo:** fixed seeds can reproduce it, but a
  small sample does not prove balance or pair coverage and makes omissions
  harder to audit.
- **Box-Behnken or response-surface fitting:** these designs are appropriate
  for local quadratic approximation after a plausible region and response
  model exist. M2 first needs a discrete feasibility screen and categorical
  authority shock.
- **Agent-based market behavior now:** demand curves, price response, operator
  costs, market entry, and strategic behavior lack accepted data and would add
  assumptions that dominate the existing deterministic protocol mechanics.
- **Select production values from existing fixtures:** the fixtures were
  deliberately created for coverage, not calibration, and carry no empirical
  or governance mandate.

## Consequences

- M2 gains one compact, reproducible view across all three accepted research
  boundaries without changing their contracts.
- Pairwise balance and reverse-stress classifications are mechanically
  testable and reviewable.
- The study exposes authority availability/capture and economic funding
  shortfalls instead of silently weakening thresholds or obligations.
- Three-level fractional screening cannot resolve all higher-order
  interactions, market dynamics, operator costs, or real-world correlations.
- Any family that appears robust remains a hypothesis requiring narrower
  simulation, empirical inputs, independent review, and a later protocol
  decision.

[nist-oa]: https://www.itl.nist.gov/div898/handbook/pri/section3/pri33a.htm
[nist-glossary]: https://www.itl.nist.gov/div898/handbook/glossary.htm
[bcbs]: https://www.bis.org/bcbs/publ/d450.htm
[eip-1559]: https://eips.ethereum.org/EIPS/eip-1559
[ethereum-consensus]: https://github.com/ethereum/consensus-specs
