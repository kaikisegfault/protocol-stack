# ADR 0012: Exact economic solvency and concentration envelope

- Status: Accepted for M2 research
- Date: 2026-08-01

## Context

ADR 0011 screened thirteen economic, participation, lifecycle, and authority
factors with a strength-two orthogonal array. Six configurations produced at
least one robust run across the reviewed eight-seed study, but only twelve of
216 runs were robust. The dominant remaining failures were reward-funding
shortfall and within-role reward concentration.

The screen was deliberately low resolution. Its three factor levels cannot
locate the exact funding boundary created by integer fee splits, all-or-nothing
treasury funding, and floor entitlements. Eight seeded contribution samples
also cannot establish how the concentration alarm behaves across the complete
accepted `1..20` contribution-unit support. M2 needs one focused experiment
before any production economic range can be proposed.

Primary-source review informed the decision:

- NIST distinguishes economical screening designs from higher-resolution
  designs intended to investigate interactions and response surfaces. The
  completed strength-two array served the screening purpose; the next study
  should focus only on the responses it exposed.
  Source: [NIST use of fractional factorial designs][nist-fractional].
- NIST response-surface guidance describes fitted linear, interaction,
  quadratic, and sometimes cubic models. Those models are inappropriate for
  the discontinuous responses here: integer floors, threshold comparisons,
  and atomic failure produce exact steps rather than a smooth noisy surface.
  Source: [NIST response surface designs][nist-response].
- The Basel Committee's stress-testing principles emphasize predeclared
  objectives, adequate granularity, internally consistent scenarios,
  sensitivity analysis, documented exclusions, and reverse stress. This
  project is not a bank and adopts no regulatory ratio, but those disciplines
  support an exact boundary study and explicit non-production limits.
  Source: [BCBS stress-testing principles][bcbs].

These sources guide experimental structure only. The study remains original,
standard-library-only research tooling with no external runtime dependency.

## Classification

This is an economics research change. It does not change consensus,
compatibility, canonical encoding, cryptography, authority behavior, simulator
v1 behavior, or any state transition.

## Decision

### Retain only screened survivor families

Freeze the six ADR 0011 configurations that produced at least one robust run
in the reviewed seed range:

```text
case_00 case_01 case_09 case_15 case_21 case_24
```

Their issuance, budget, validator weight, and node weight coordinates are
experimental anchors, not accepted values. Authority, availability shock,
lifecycle delay, fee path, bond, and penalty coordinates remain fixed within
each family so the new study isolates the two identified failure surfaces.

### Enumerate exact financial boundaries

For each survivor family, enumerate every integer issuance amount in
`100..2500` and every integer per-role budget in `50..1500`. This represents
3,483,851 financial cells per family and 20,903,106 cells overall.

Do not materialize every cell. Reward funding is monotone in issuance under
the accepted event order, so one exact profile per family and budget can
losslessly describe the complete issuance axis. Each profile records the
minimum issuance at which the all-or-nothing treasury funding event succeeds,
the result below that boundary using fee-funded rewards alone, and exact cell
classification counts.

For every profile, evaluate entitlement totals over the complete ordered
contribution-unit support `1..20` for both participants in both roles. Use
histogram convolution to count all `20^4 = 160,000` combinations without
sampling or iterating an expanded configuration report.

A financial cell is:

- `solvent` when all 160,000 contribution combinations can fund every created
  entitlement;
- `mixed` when some but not all combinations can be funded; or
- `insolvent` when no combination can be funded.

These labels describe only the accepted synthetic flow. They do not measure
market solvency, asset value, operator cost, or production safety.

### Enumerate exact concentration boundaries

For each survivor family, hold its per-role budget and sweep validator and
node selected-contribution weights independently through every integer in
`1..16`. Evaluate the accepted three-quarter maximum-share alarm over all
160,000 ordered contribution combinations.

Factor the exact count into independent 400-pair role counts and multiply the
counts; do not infer independence in a production population. A concentration
cell is `within_bound`, `mixed`, or `concentrated` when respectively all, some,
or none of the complete synthetic support clears both role alarms.

The three-quarter alarm is unchanged from ADR 0011. This study does not adopt
a Gini coefficient, Herfindahl index, stake-power rule, delegation model, or
production reward-distribution objective.

### Use an independent exact projection

Implement a small arithmetic projection from the accepted v1 rules. It must
independently reproduce:

- quotient-and-remainder floor entitlements;
- fee reward share and treasury remainder;
- all-or-nothing treasury reward funding;
- sequential fully funded or failure-atomic claim allocation;
- capped issuance within the selected range; and
- the exact rational concentration comparison.

The projection is not a simulator v2 and owns no state. Cross-check survivor
and boundary points against the unchanged authority, participation, and
native-economy simulators through their accepted adapters. A mismatch is a
study error, not evidence that the projection may replace an accepted engine.

### Preserve deterministic and compatibility boundaries

All values, counts, products, divisions, remainders, ratios, grids, and
digests are checked integers. Replay uses no floating point, regression,
confidence estimate, wall clock, network input, model inference, signature
verification, dependency package, or mutable external dataset.

The normative contract is
`../specifications/economic-envelope-study-v1.md`. The resulting evidence may
reject candidate families or motivate a later experiment. It cannot select a
production issuance schedule, reward budget, contribution weight, threshold,
or C++ transition.

## Alternatives not selected

- **Fit a quadratic response surface:** the objective responses contain hard
  threshold and floor discontinuities. A smooth fit would add approximation
  error where an exact integer grid is inexpensive.
- **Extend the thirteen-factor screen:** another low-resolution fraction would
  broaden coverage without resolving the two observed boundaries.
- **Use more seeded Monte Carlo samples:** additional seeds remain samples of
  a small complete `1..20` support. Exact enumeration is cheaper and stronger.
- **Execute all 20,903,106 cells through all three simulators:** this would
  duplicate invariant transitions even though the accepted event order makes
  the relevant arithmetic losslessly compressible. Focused full-composition
  cross-checks retain independence at much lower hosted cost.
- **Vary authority and lifecycle again:** ADR 0011 already resolves their
  structural threshold outcomes for the selected shocks. They remain fixed so
  this study does not confound availability with funding and distribution.
- **Select the broad-screen robust coordinates as production defaults:** only
  twelve seeded runs passed synthetic objectives, and no empirical cost,
  demand, compromise, or validator-power evidence exists.

## Consequences

- M2 gains atomic-unit funding boundaries and complete contribution-support
  concentration counts around every screened survivor family.
- The compressed financial profiles are lossless under the accepted event
  order and materially smaller than a cell-by-cell report.
- Analytical and full-composition implementations remain independently
  checkable.
- The study still omits market demand and price, operator costs, strategic
  behavior, participant correlation, Sybil resistance, stake-based consensus
  power, empirical compromise rates, and production authority policy.
- Any surviving range remains a research hypothesis requiring empirical
  assumptions, independent economic and security review, and a separate
  consensus ADR, specification, activation, and migration contract.

[nist-fractional]: https://www.itl.nist.gov/div898/handbook/pri/section3/pri3345.htm
[nist-response]: https://www.itl.nist.gov/div898/handbook/pri/section3/pri336.htm
[bcbs]: https://www.bis.org/bcbs/publ/d450.htm
