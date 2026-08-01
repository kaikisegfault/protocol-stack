# Economic envelope study v1

Status: Accepted M2 research contract; not a consensus transition or parameter
recommendation

This document is normative for the version-one high-resolution solvency and
concentration envelope study. It fixes survivor selection, integer grids,
complete contribution support, independent projection arithmetic,
classifications, report shape, cross-checks, and digests. It does not change
the accepted native-economy, participation, authority, or economic-stress v1
contracts.

## Scope and numeric domain

The study owns no protocol state. It projects two exact response surfaces from
accepted research rules, summarizes their complete finite domains, and checks
selected points by composing the three accepted simulators through their exact
adapters.

Every input, family coordinate, amount, unit, weight, entitlement, count,
product, quotient, remainder, ratio component, and digest input is an integer
in `0..2^64-1`. JSON booleans are not integers. Each intermediate addition and
multiplication is checked before use. Floating-point and decimal values are
forbidden.

Canonical JSON and SHA-256 domain separation are exactly the construction in
authority simulation v1. The study defines no protocol bytes, transaction,
signature message, state root, or consensus error.

All families, ranges, classifications, and alarms are synthetic. None is a
production default, safe range, forecast, estimate, confidence interval, or
recommendation.

## Design identity and survivor selection

Version one is named:

```text
EXACT-ENVELOPE(6;2401x1451;16x16;20^4)-v1
```

The survivor families are the ADR 0011 configurations whose frozen default
study contained at least one `robust` run. They occur in this order:

```text
case_00 case_01 case_09 case_15 case_21 case_24
```

The reviewed design fixture stores each complete ADR 0011 configuration,
including its original case index, thirteen levels, values, and derived honest
and compromised member counts. Construction must prove byte equality with
the corresponding configurations from economic stress study v1.

For every survivor family:

- `authority_available`, `rotation_available`, `recovery_available`, and
  `authority_uncaptured` are structurally true under its retained threshold
  and shock;
- activation, exit, unbond, authority delay, fee volume, fee split, bond, and
  penalty values remain fixed;
- the financial grid replaces only issuance and per-role reward budget; and
- the concentration grid replaces only validator and node selected weights.

Selecting a survivor means only that at least one of seeds `0..7` passed all
ADR 0011 objectives. It does not promote the configuration or its robust seed.

## Complete contribution-unit support

The accepted economic-stress participation manifest generates four ordered
units, each in `1..20`, for:

```text
validator_a validator_b node_a node_b
```

Version one evaluates the complete Cartesian support. Each role therefore has
`20 * 20 = 400` ordered unit pairs, and both roles have
`400 * 400 = 160000` ordered combinations.

This enumeration replaces seed sampling for study conclusions. SplitMix64-v1
seeds remain useful only for cross-checking exact composed runs.

The fixture records:

```text
contribution_unit_min = 1
contribution_unit_max = 20
role_combination_count = 400
joint_combination_count = 160000
```

## Independent entitlement projection

For a role budget `B`, selected participant units `a`, baseline participant
units `b`, and selected contribution weight `w`:

```text
selected_score = a * w
baseline_score = b
role_score = selected_score + baseline_score
```

Each score and sum is checked. Both scores are nonzero in version one.

For each participant score `s`, calculate the accepted floor entitlement
without relying on an overflowing mathematical product:

```text
q, r = divmod(B, role_score)
entitlement = q * s + floor(r * s / role_score)
```

Both products and the final sum are checked. The two role entitlements are
independent of settlement order. Their sum is at most `B`; the difference is
the retained role remainder.

The joint entitlement total is the sum of both validator entitlements and
both node entitlements. Construct one count histogram for each role across its
400 ordered pairs, then convolve the two histograms. The resulting counts must
sum to 160,000.

## Financial grid and exact funding profile

The financial axes are every integer in these inclusive ranges:

```text
issuance_amount = 100..2500
reward_budget_per_role = 50..1500
```

There are 2,401 issuance values and 1,451 budget values, or 3,483,851 cells
per family and 20,903,106 across six families.

All issuance values are positive, within the accepted study's initial 4,500
unit capacity, and produce issued supply no greater than 11,000 against the
unchanged 13,000 limit. This range proves no production issuance safety.

For a survivor's fixed fee volume `F` and fee reward parts `P` with denominator
ten:

```text
fee_reward = floor(F * P / 10)
fee_treasury = F - fee_reward
treasury_before_funding = 500 + issuance_amount + fee_treasury
requested_reward_funding = 2 * reward_budget_per_role
```

Use quotient-and-remainder decomposition for the fee calculation and checked
arithmetic for every term.

The accepted `fund_rewards` event is all-or-nothing:

```text
treasury_funding_accepted =
  treasury_before_funding >= requested_reward_funding

available_reward = fee_reward +
  (requested_reward_funding if treasury_funding_accepted else 0)
```

Penalty routing occurs later in the accepted flow and cannot fund this event.
Bonding and claims move already issued units and do not change available
reward at the allocation boundary.

A contribution combination is funded exactly when:

```text
joint_entitlement_total <= available_reward
```

Sequential allocations are all accepted in that case. Otherwise later
allocations may fail atomically, and the combination is not completely funded.

### Lossless issuance compression

For each family and budget, define the saturated treasury threshold:

```text
base_treasury = 500 + fee_treasury
required = 0 if requested_reward_funding <= base_treasury
           else requested_reward_funding - base_treasury
```

If `required <= 100`, every issuance cell accepts treasury funding. If
`required > 2500`, no issuance cell accepts it. Otherwise `required` is the
minimum issuance cell that accepts it.

Below that threshold, `available_reward` is exactly `fee_reward`, independent
of issuance. At or above it, `available_reward` includes the complete requested
funding and every entitlement combination is funded because each role's
entitlements sum to at most its budget.

One budget profile therefore losslessly represents all 2,401 issuance cells.
It records:

- family identifier and budget;
- minimum and maximum joint entitlement totals;
- fee reward and treasury amounts;
- the in-range minimum issuance for treasury funding or `null`;
- exact fallback funded combination count out of 160,000; and
- exact `solvent`, `mixed`, and `insolvent` issuance-cell counts.

The three cell classes are:

```text
solvent    funded combinations = 160000
mixed      funded combinations in 1..159999
insolvent  funded combinations = 0
```

Classification counts across a profile must sum to 2,401 and across the
report must sum to 20,903,106. `solvent` is scoped only to complete reward
funding in this synthetic flow.

## Concentration grid

For each survivor family, retain its original per-role budget and sweep:

```text
validator_weight = 1..16
node_weight = 1..16
```

There are 256 weight cells per family and 1,536 overall. Each cell represents
all 160,000 ordered contribution combinations.

For each role's two entitlements, the unchanged ADR 0011 alarm passes exactly
when the role total is nonzero and:

```text
4 * maximum_role_entitlement <= 3 * role_entitlement_total
```

The cell passes for a joint combination only when both role alarms pass. The
validator result depends only on the validator unit pair and weight; the node
result depends only on the node pair and weight. Count each role's passing
pairs independently and multiply the two exact counts.

Each concentration cell records:

- family identifier and the two weights;
- validator and node passing pair counts out of 400;
- joint passing combination count out of 160,000;
- the joint passing ratio as a reduced numerator/denominator object; and
- the cell classification.

The three classes are:

```text
within_bound  passing combinations = 160000
mixed         passing combinations in 1..159999
concentrated  passing combinations = 0
```

Classification counts must sum to 1,536. These names apply only to the fixed
two-participant alarm and complete synthetic unit support.

## Full-composition cross-checks

The projection must expose a point evaluator that accepts one survivor-derived
configuration and four explicit contribution units. Tests independently map
SplitMix64-v1 seeds to those units and compare projected results with
`run_configuration` from economic stress study v1.

Cross-checks must cover:

- all twelve robust case/seed pairs in the frozen ADR 0011 report;
- every survivor family;
- financial values immediately below and at an in-range treasury threshold;
- the minimum and maximum financial grid values;
- weight one and weight sixteen for each role;
- exact floor remainder and zero-remainder cases;
- completely funded and funding-shortfall outcomes; and
- concentration pass and failure outcomes.

For every composed point, the unchanged simulators must conserve and cap
supply, preserve authority availability and non-capture for the survivor
family, and match projected entitlement amounts, retained remainder, complete
funding, and concentration. Any mismatch aborts verification.

The projection is not permitted to emit, authorize, or mutate a simulator
event and cannot replace any accepted simulator result.

## Design fixture and report

The design fixture has schema:

```text
protocol-stack/economic-envelope-design/v1
```

It contains exactly:

```text
schema
design
survivor_case_ids
survivor_configurations
issuance_range {minimum, maximum, step}
budget_range {minimum, maximum, step}
weight_range {minimum, maximum, step}
contribution_unit_range {minimum, maximum, step}
role_combination_count
joint_combination_count
financial_cell_count
concentration_cell_count
```

All steps are one.

The report has exactly:

```text
schema = protocol-stack/economic-envelope-study/v1
design = EXACT-ENVELOPE(6;2401x1451;16x16;20^4)-v1
design_digest
family_count = 6
financial_cell_count = 20903106
concentration_cell_count = 1536
joint_combination_count = 160000
financial_classification_counts
concentration_classification_counts
family_summaries
financial_profiles
concentration_cells
study_digest
```

Families, profiles, and cells retain design order. Profiles sort by budget.
Concentration cells sort by validator weight and then node weight. All map keys
use lexical order under canonical encoding.

Family summaries contain exact financial and concentration classification
counts and the original survivor configuration. They do not collapse or rank
families into a production recommendation.

Digest domains are:

```text
design_digest =
  SHA-256("protocol-stack:economic-envelope:design-v1\0" || canonical(design))

study_digest =
  SHA-256("protocol-stack:economic-envelope:study-v1\0" || canonical(report
  without study_digest))
```

The design and default report digests are frozen after independent replay and
review.

## Command line and resource limits

The command is:

```sh
python3 simulation/economic_stress/envelope_study.py
```

`--output` writes canonical pretty JSON with one trailing newline. Without it,
the same bytes are written to standard output.

Version one accepts no manifest, event, family, range, or seed file. Its
finite grids are compile-time research constants. Histogram and profile sizes
are asserted before report construction. It exposes no new untrusted protocol
byte decoder.

## Evidence and compatibility

Tests cover:

- reviewed survivor fixture equality and frozen design digest;
- exact range endpoints, steps, shapes, and total cell counts;
- checked quotient-and-remainder entitlement and fee arithmetic;
- all 160,000 contribution combinations through factored histograms;
- lossless financial threshold compression and classification totals;
- exact concentration factorization and rational ratios;
- positive, negative, floor, zero-remainder, threshold, and range boundaries;
- deterministic repeated construction and report digest;
- full-composition agreement at survivor and adversarial boundary points;
- integer-only report output and command-line identity;
- standard-library and accepted-local-model import boundaries; and
- every existing simulator's focused regression suite.

No new fuzz target applies because the study accepts no untrusted protocol
bytes or external data. Python argument parsing and generated JSON remain
caller-bounded and are covered by ordinary negative and CLI tests.

The study changes no accepted simulator schema, event, error, state, metric,
digest, or adapter behavior. It changes no M1 byte, root, persistence, ABCI,
supply, fee, or CometBFT validator-set behavior.

An incompatible family selection, grid, support, projection, classification,
report shape, or digest requires economic envelope study v2. Any production
proposal still requires empirical assumptions, independent economic and
security review, and a separate consensus specification with activation and
migration.
