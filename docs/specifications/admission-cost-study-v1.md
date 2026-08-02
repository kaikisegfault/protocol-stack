# Admission cost study v1

Status: Accepted M2 research contract; not a consensus transition, identity
policy, admission parameter, or economic recommendation

This document is normative for the version-one cross-principal admission-cost
study. It fixes exact support, hidden-principal identities, work partitioning,
utility, operating and capital-time costs, persistent and churn strategies,
lock checks, objectives, funding checks, report shape, and compatibility. It
changes no accepted simulator-v1 contract.

## Scope and numeric domain

The study owns no protocol state, native value, identity credential, or claim.
Every amount, epoch, unit, weight, score, count, payout, cost, bond, duration,
exposure, ratio component, and digest input is an integer. Monetary and count
components are in `0..2^64-1`; JSON booleans are not integers. Products and
sums are checked before use. Signed utility differences are calculated only
from checked unsigned components and must remain in `-2^64+1..2^64-1`.
Floating point is forbidden.

Canonical JSON and SHA-256 domain separation are the accepted participation
v1 constructions. The study defines no transaction bytes, signature message,
state root, consensus error, production principal, or verifier.

Version one is named:

```text
ADMISSION-COST(6x2x16x20x16;8+4;L1..16)-v1
```

## Design coordinates

Use the six survivor configurations in the ADR 0012 fixture order and
`validator` then `node`. Retain each configuration's reviewed per-role budget.
For every selected weight `w = 1..16` and honest raw units `h = 1..20`, set:

```text
dominant_total_units = 16
dominant_total_score = 16 * w
honest_score = h
```

For dominant identity count `k = 1..16`, calculate:

```text
q, r = divmod(16, k)
units_i = q + 1  for i < r
          q      otherwise
score_i = units_i * w
```

Identifiers are ascending `dominant_00` through `dominant_15`. Every included
identity has positive units and distinct values for participant, registered
principal, and payout account. The honest participant also has distinct
labels. The study separately maps every dominant identity to the synthetic
`hidden_dominant` principal. That label is never passed to participation v1 or
reward-distribution v1.

Total dominant units and score must equal their unsplit values for every form.
The complete support contains:

```text
base coordinates = 6 * 2 * 16 * 20 = 3,840
identity forms per mechanism = 3,840 * 16 = 61,440
```

Mechanism order is `proportional`, `participant_cap`, `principal_cap`. Apply
the unchanged reward-distribution v1 single-epoch projection. With distinct
registered scopes, participant-cap and principal-cap payout maps must be
identical at every point.

## Payout and concentration observables

For each form record created credit, paid credit, zero payout, dominant payout,
honest payout, registered identity and principal concentration, and hidden-
principal concentration. Hidden aggregation combines every dominant payout
under one scope and leaves the honest payout separate. A nonzero hidden payout
passes the unchanged alarm exactly when:

```text
4 * maximum_hidden_scope_payout <= 3 * total_payout
```

A zero payout is `null`, not a concentration pass. Admission cost changes
utility but never rewrites a payout or makes a failing distribution pass.

## Integer operating-cost boundary

An operating cost is a nonnegative integer utility charge paid once per
distinct admitted identity in the evaluated strategy. It is not a native
transfer, fee, burn, tax, or claim.

For one exact-support coordinate and mechanism, let `G_k` be the dominant
payout with `k` identities and `G_1` the unsplit payout:

```text
zero_cost_gain_k = G_k - G_1
net_utility_k(c) = G_k - k * c
net_split_advantage_k(c) = zero_cost_gain_k - (k - 1) * c
```

For `k > 1`, the minimum nonnegative integer cost deterring that form is:

```text
break_even_k = 0                                  if zero_cost_gain_k <= 0
               ceil(zero_cost_gain_k / (k - 1))  otherwise
```

Ceiling division is `quotient + (remainder != 0)` after checked inputs. The
coordinate deterrence floor is the maximum over `k = 2..16`; the global floor
is the maximum across complete support.

The smallest-honest-entry ceiling is the minimum `G_h` paid to the one-unit
honest participant at unsplit coordinates. The inclusive operating-cost
interval is:

```text
global_deterrence_floor <= c <= smallest_honest_entry_ceiling
```

It is feasible only when the lower bound does not exceed the upper bound.
`c = 0` is the predeclared zero-cost baseline.

## Refundable native-bond capital time

The research bond is an account-funded native-economy v1 `general` escrow with
the owner as beneficiary. Its principal is part of issued supply throughout
the lock and is completely returned. It is never included in gross or net
utility.

For positive bond amount `b`, active duration `a`, positive post-exit lock
`l`, and nonnegative rational rate `n/d` with `d > 0`, first sum exact
identity exposures for each strategy:

```text
identity_exposure_i = b * (a_i + l)
strategy_exposure = sum(identity_exposure_i)
incremental_exposure = strategy_exposure - baseline_exposure
incremental_capital_time_cost = ceil(incremental_exposure * n / d)
net_split_advantage = zero_cost_gain - incremental_capital_time_cost
```

All components are checked `u64`; subtraction requires the strategy exposure
to be at least the baseline exposure. The ceiling is applied once after exact
exposures are summed, not independently per identity. For positive zero-cost
gain `G`, the exact deterring rate boundary is open below and unbounded above:

```text
n / d > (G - 1) / incremental_exposure
```

For honest payout `H`, the exact entry-preserving boundary is inclusive:

```text
n / d <= H / exposure
```

Store reduced nonnegative rational objects and explicit lower-bound
inclusivity. Report normalized boundaries for unit bond `b = 1` and every
`l = 1..16`; any positive bond amount scales the denominators exactly. The
unit amount is a normalization, not an admission-bond recommendation.

For the exact-support allocation, every identity has active duration one. The
incremental unit-bond exposure of a `k`-way split is:

```text
(k - 1) * (1 + l)
```

Use zero-cost gain and this exposure to derive the maximum normalized lower
rate boundary. Honest exposure is `1 + l`.

## Persistent and churn trajectories

Use budget `100`, dominant total units `16`, selected weight `1`, honest units
`1`, eight contribution epochs, four drain epochs, and every `k = 1..16`.

- `persistent_k` reuses the same `k` dominant identities in all contribution
  epochs. Each dominant identity is active for eight epochs.
- `churn_k` uses `k` fresh dominant identities in each contribution epoch.
  Each dominant identity is active for one epoch. All `8 * k` registered
  scopes are distinct.

The honest identity persists for eight epochs. Run all three unchanged reward
mechanisms. Aggregate dominant and honest work is integer-identical in every
contribution epoch; participant labels differ exactly as declared by the
persistent and churn strategies. Four drain epochs add no contribution.

Relative to `persistent_1`, record gross dominant payout gain, distinct
dominant identities, hidden-principal concentration, and:

```text
incremental_operating_identities = strategy_identities - 1
persistent unit-bond duration = k * (8 + l)
churn unit-bond duration = 8 * k * (1 + l)
baseline unit-bond duration = 8 + l
incremental unit-bond exposure = strategy duration - baseline duration
```

Derive operating and normalized bond-rate break-even with the same exact
ceiling rules. The churn objective passes only when the selected cost boundary
makes every positive-gain persistent and churn strategy nonprofitable. This is
an incentive result under the declared utility model, not prevention of
registration or collusion.

## Native lock replay

For every post-exit lock `l = 1..16`, replay two unit-bond patterns through an
independent native-economy v1 manifest:

- sixteen persistent escrows opened at epoch zero and unlocked at `8 + l`;
- one churn escrow opened in each of sixteen epochs and unlocked at
  `open_epoch + 1 + l`.

Attempt one release immediately before its unlock epoch and require the typed
ordinary failure. Release every escrow at or after unlock. Require exact final
refund, no remaining escrow, unchanged issued supply, and peak locked values
equal to the analytical projection. Event identifiers remain unique and
ordinary failure changes no state.

## Participation, reward, and funding cross-checks

Independently reproduce proportional points for `k = 1`, `2`, and `16` through
participation v1 with distinct owner and payout labels. Finalize the budget,
call unchanged `build_funding_events`, and require exact equality with the
reward-distribution projection. Execute the funding events through native
economy v1 and require acceptance.

For every persistent and churn mechanism trajectory, independently pre-fund a
native-economy reward pool with `budget * 12`. Emit only nonzero calculated
payouts as ordinary `allocate_reward` events in epoch and participant order.
Every event must succeed. Final reward pool plus typed claims must equal
initial funding, and claims must equal paid credit. Study cost, pending credit,
expired credit, and refundable bond principal never become reward claims.

## Objectives and report

The report records these predeclared objectives per mechanism and globally:

- `work_invariant`: every split preserves sixteen units and weighted score;
- `registered_scope_equivalence`: both capped mechanisms match exactly;
- `funded`: every emitted allocation succeeds and conserves native value;
- `lock_enforced`: early release fails and due release refunds exactly;
- `churn_deterred`: every positive-gain persistent and churn form is covered
  by the derived cost boundary;
- `hidden_concentration`: every nonzero payout passes after hidden-principal
  aggregation;
- `nonprofitable_split`: every form has nonpositive net split advantage at the
  deterrence floor;
- `honest_entry`: the smallest honest participant has nonnegative utility at
  that cost; and
- `joint_cost_range`: one cost interval satisfies split, churn, and honest
  entry objectives without an unfunded claim.

The design fixture schema is
`protocol-stack/admission-cost-design/v1`. The report schema is
`protocol-stack/admission-cost-study/v1`. It contains the design digest,
complete-support summaries, lossless operating and bond-rate boundaries,
trajectory summaries, lock replays, adapter cross-checks, objective results,
and a study digest over the preceding object. Arrays retain specified order.

## Compatibility and exclusions

The study imports accepted simulator functions but changes none. It invokes no
wall clock, network input, package randomness, model inference, external
verifier, floating point, signature verification, dependency package, or
mutable dataset.

Outputs cannot select a production registrar, uniqueness proof, identity
provider, admission fee, burn or treasury route, bond amount, lock duration,
capital rate, token price, stake threshold, reward mechanism, budget, weight,
actor, claim right, transition, encoding, migration, or activation. They omit
empirical work quality and costs, market demand, heterogeneous capital access,
delegation, bribery, collusion, identity rental, and strategic equilibrium.
