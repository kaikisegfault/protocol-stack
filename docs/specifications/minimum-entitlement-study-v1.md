# Minimum-entitlement study v1

## Scope and arithmetic

This specification defines a deterministic research comparison of minimum
entitlement families over the exact one-unit zero-credit support found by ADR
0014. It defines no protocol state, native value, identity credential,
production claim, actor, floor, reward rate, or consensus behavior.

Every budget, floor, count, raw unit, weight, score, reserve, credit, payout,
and digest input is an integer. Unsigned components are in `0..2^64-1`; JSON
booleans are not integers. Products and sums are checked before use. Signed
differences are formed only from checked unsigned components and remain in
`-2^64+1..2^64-1`. Floating point is forbidden.

Canonical JSON and SHA-256 domain separation use the accepted participation v1
construction. The study defines no transaction bytes, signature message,
state root, consensus error, or verifier.

Version one is named:

```text
MINIMUM-ENTITLEMENT(80x16x3x3;m0..5)-v1
```

## Retained zero-credit support

Read the six survivor configurations in the ADR 0012 fixture order. For each
configuration and `validator` then `node`, retain its reviewed role budget. For
selected weight `w = 1..16`, construct the unsplit scores:

```text
dominant raw units = 16
dominant score = 16 * w
honest raw units = 1
honest score = 1
```

Apply reward-distribution v1 proportional credit construction. Retain the
coordinate exactly when honest credit is zero. The retained coordinates are
ordered by survivor fixture, role, then weight and must number exactly eighty.
Their identifiers are `(case_id, role, selected_weight)`.

For dominant identity count `k = 1..16`, calculate:

```text
q, r = divmod(16, k)
units_i = q + 1  for i < r
          q      otherwise
score_i = units_i * w
```

Use ascending participants `dominant_00` through `dominant_15`, each with a
distinct owner and payout account. The honest participant also has distinct
labels. Every included participant has positive raw units and score. Total
dominant raw units and weighted score must be invariant for every `k`.

## Floor families and feasibility

Floor family order is `zero`, `per_participant`, `work_proportional`. Mechanism
order is `proportional`, `participant_cap`, `principal_cap`. Common comparison
floors are the integers `0..5` in ascending order.

For budget `B`, floor `m`, positive raw units `u_i`, and positive weighted
score `s_i`, define reserves:

```text
zero:               R_i = 0
per_participant:    R_i = m
work_proportional:  R_i = m * u_i
R = sum(R_i)
```

The `zero` family is evaluated only at `m = 0`; nonzero floor inputs to that
family are invalid. The two positive-floor families include `m = 0` as an
exact baseline cross-check.

The form is feasible exactly when `R <= B`. If it is infeasible, record the
funding boundary but create no credits, payouts, utility comparisons, or native
events. Do not clip, pro-rate, redistribute, borrow, mint, or carry a deficit.

For a feasible form, set `A = B - R`, `S = sum(s_i)`, and use the unchanged
checked floor-share formula:

```text
q, r = divmod(A, S)
extra_i = q * s_i + floor(r * s_i / S)
credit_i = R_i + extra_i
```

Zero raw work and zero score are absent and receive no reserve. A mismatch
between raw-work and score keys is invalid. Synthetic zero-work probes must
show that adding a zero-valued identifier changes no credit or payout map.

Credit remainder is `B - sum(credit_i)` and stays in the research reward pool.
For the proportional mechanism, each nonzero credit is the payout. For capped
mechanisms, create one source-epoch-zero bucket per nonzero credit and apply
the unchanged reward-distribution v1 candidate, largest-scope cap, consumption,
and pruning rules. No history or drain epoch is added to this single-epoch
comparison.

At floor zero, all result fields shared with reward-distribution v1 must match
its public projection. With distinct registered owner labels,
`participant_cap` and `principal_cap` credit and payout maps must be identical.

## Exact funding and identity boundaries

The positive participant count is `k + 1`; total accepted raw units are always
seventeen. For `m > 0`, derive:

```text
per-participant reserve total = m * (k + 1)
per-participant maximum floor = floor(B / (k + 1))
per-participant maximum identities = min(16, floor(B / m) - 1)

work-proportional reserve total = 17 * m
work-proportional maximum floor = floor(B / 17)
work-proportional maximum identities = 16 when 17 * m <= B
```

If `floor(B / m) - 1` is below one, the per-participant family admits no design
form at that floor. These formulas are calculated for every retained budget,
all `k = 1..16`, and the positive common floors. Equality is feasible and is
recorded as reserve exhaustion. The common support ceiling is independently
recomputed as the minimum maximum floor across every family and design form;
it must equal five.

## Observables

For every feasible form record family, floor, mechanism, coordinate, identity
count, raw and weighted invariants, reserve total, residual allocation budget,
created credit, paid credit, retained budget, honest payout, dominant payout,
zero payout, and registered and hidden-principal concentration.

Hidden aggregation combines every dominant payout under one synthetic scope
and leaves the honest payout separate. A nonzero payout passes exactly when:

```text
4 * maximum_hidden_scope_payout <= 3 * total_payout
```

A zero payout is `null`, not a concentration pass.

For family `f`, floor `m`, and identity count `k`, define:

```text
G(f,m,k) = dominant payout
same_floor_split_gain = G(f,m,k) - G(f,m,1)
baseline_amplification = G(f,m,k) - G(zero,0,1)
```

Comparisons require all referenced forms to be feasible. Record negative,
zero, and positive counts and maximum positive values. `same_floor_split_gain`
isolates label splitting. `baseline_amplification` includes both the floor and
the split relative to accepted unsplit behavior.

For each coordinate, family, and mechanism, derive two break-even floors over
the complete common support:

- `same_floor_break_even`: the smallest `m` with positive honest payout and
  nonpositive same-floor gain for every `k = 2..16`;
- `baseline_break_even`: the smallest `m` with positive honest payout and
  nonpositive baseline amplification for every `k = 1..16`.

Use `null` when no common floor passes. A floor-zero honest payout is retained
as a failure. Global break-even exists only when one common floor passes every
retained coordinate for that family and mechanism.

## Predeclared objectives

Report these objectives by floor family, mechanism, and globally:

- `work_invariant`: splitting changes no raw units or dominant weighted score;
- `strictly_funded`: reserve and calculated credit never exceed the role
  budget, and every infeasible reserve creates no projection;
- `zero_work_rejected`: a zero-work label receives no reserve and changes no
  result;
- `honest_entry`: every feasible positive-floor form pays the one-unit honest
  participant a positive amount;
- `nonprofitable_same_floor_split`: every `k = 2..16` has nonpositive
  same-floor split gain;
- `no_baseline_amplification`: every `k = 1..16` has nonpositive amplification
  from the zero-floor unsplit baseline;
- `hidden_concentration`: every nonzero payout passes after hidden aggregation;
- `liveness`: every feasible positive-floor form has a nonzero payout and a
  positive honest payout;
- `budget_exhaustion_safe`: equality at the reserve boundary, when present,
  remains funded and deterministic; and
- `native_funding`: every emitted allocation succeeds and conserves native
  value.

An objective quantified over positive floors excludes `m = 0`. The global
joint objective passes only if one family, one accepted mechanism, and one
common positive floor satisfy honest entry, both hidden-payout objectives,
strict funding, zero-work rejection, liveness, and native funding across the
complete retained support. It does not select that floor for production.

## Cross-checks and native replay

Independently call reward-distribution v1 for all
`80 * 16 * 3 = 3,840` zero-floor forms and require shared result equality.
Require the two capped registered-scope projections to match at every feasible
family and floor form.

Choose the first and last retained `node` coordinates in canonical order. For
each selected coordinate, family, mechanism, `k` in `{1, 2, 16}`, and floor in
`{0, 1, 5}` that is valid and feasible:

1. reproduce every positive raw unit and selected weight through participation
   v1 and require the finalized weighted scores to equal the study input;
2. calculate the study-owned reserve projection without modifying the accepted
   participation reward adapter;
3. create a fresh native-economy v1 manifest with a reward pool funded by the
   role budget;
4. emit nonzero payouts as `allocate_reward` events in ascending participant
   order; and
5. require acceptance, exact claims, and `reward_pool + claims = budget`.

The accepted participation adapter's unchanged zero-floor funding events must
also equal the zero-family proportional projection. A floor reserve is never
passed off as accepted participation credit.

## Fixture and report

The design fixture schema is
`protocol-stack/minimum-entitlement-design/v1`. It contains the study name,
ordered mechanisms and floor families, retained coordinates, common floor
range, fixed raw units, identity range, and exact form counts.

The report schema is `protocol-stack/minimum-entitlement-study/v1`. It contains
the design and design digest, exact funding boundaries, complete-support
summaries, break-even results, cross-checks, predeclared objectives, and a study
digest over every preceding field.

Fixture generation, report generation, and repeated runs must be byte-identical
under sorted-key UTF-8 JSON with two-space indentation, no ASCII escaping, no
NaN, and one terminal newline. Domain strings are:

```text
protocol-stack:minimum-entitlement:design-v1
protocol-stack:minimum-entitlement:study-v1
```

## Interpretation boundary

This study measures deterministic arithmetic over synthetic reviewed support.
It does not establish identity uniqueness, work quality, empirical costs,
participant demand, collusion resistance, equilibrium, token price, issuance
sustainability, legal eligibility, or production safety. No result activates a
floor, cap, role, actor, transfer, fee, claim, or state transition.
