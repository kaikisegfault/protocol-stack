# Reward distribution study v1

Status: Accepted M2 research contract; not a consensus transition, identity
policy, or economic parameter recommendation

This document is normative for the version-one reward-distribution mechanism
study. It fixes the compared mechanisms, checked arithmetic, scope grouping,
cap, ordering, remainder, credit history, pruning, exact support, trajectories,
objectives, funding checks, report shape, and digest. It does not change any
accepted simulator-v1 contract.

## Scope and numeric domain

The study owns no protocol state or native value. Every epoch, unit, weight,
score, budget, credit, payout, count, product, ratio component, and digest input
is an integer in `0..2^64-1`. JSON booleans are not integers. Every addition
and multiplication is checked before use. Floating point is forbidden.

Canonical JSON and SHA-256 domain separation are the accepted participation
v1 constructions. The study defines no transaction bytes, signature message,
state root, consensus error, principal-verification rule, or production actor.

Version one is named:

```text
REWARD-CAP(6x2x16x20^2;5x8+4)-v1
```

## Identities and scopes

Each study participant has `participant`, `principal`, and `payout_account`
identifiers. A participant maps to one principal for the complete run.
Multiple participants may map to the same principal and payout account,
matching the accepted registration contract. `principal` is a synthetic
grouping label, not proof of personhood, ownership, device identity, or Sybil
resistance.

Mechanisms are evaluated in this order:

```text
proportional
participant_cap
principal_cap
```

`proportional` and `participant_cap` scope by participant. `principal_cap`
groups all participant credits naming the same principal.

## Proportional credit construction

For positive role budget `B`, positive participant weighted score `s_i`, and
their checked positive sum `S`, calculate:

```text
q, r = divmod(B, S)
credit_i = q * s_i + floor(r * s_i / S)
```

Products and sums are checked. An absent or zero score creates no credit; a
zero floor credit creates no bucket. The entitlement remainder is
`B - sum(credit_i)` and stays in the reward pool.

For `proportional`, every nonzero credit is the same epoch's payout. For a
capped mechanism it creates a bucket:

```text
(source_epoch, participant, principal, amount)
```

A bucket is priority state only. It is not an account balance, native claim,
debt, escrow, bond, or guaranteed future payout.

## Capped allocation

At contribution or drain epoch `E`, execute in order:

1. expire buckets where `source_epoch + 4 <= E`;
2. add current nonzero proportional credits;
3. group pending credit by mechanism scope;
4. calculate a floor candidate vector;
5. cap the largest candidate;
6. consume payouts from buckets; and
7. prune empty buckets.

For scope credit `C_j`, checked positive total `C`, and allocation capacity:

```text
A = min(B, C)
q, r = divmod(A, C)
candidate_j = q * C_j + floor(r * C_j / C)
```

Candidate rounding remainder stays unspent. Let `T` be the candidate sum. If
`T = 0`, every payout is zero. Otherwise select largest candidate `L`, breaking
a tie by ascending scope identifier, and let `O = T - L`:

```text
payout_largest = L       if L <= 3 * O
                 3 * O   otherwise
payout_other = candidate_other
```

The multiplication is checked. The resulting nonzero vector satisfies
`4 * maximum_payout <= 3 * total_payout`. If one scope has a candidate,
`O = 0` and all payout is withheld.

`participant_cap` consumes participant buckets in ascending source epoch.
`principal_cap` consumes a principal allowance in ascending
`(source_epoch, participant)` order. Maps serialize by ascending identifier.
There is no largest-remainder redistribution, implicit transfer, negative
credit, or automatic claim. Retained budget is `B - total_payout`.

## History and pruning

A bucket is eligible in its source epoch and the next three allocation epochs.
It expires before allocation in `source_epoch + 4`, which must be representable.
Delete a bucket immediately when fully consumed or expired; never retain zero.
At most four buckets per contributing participant are live after allocation.

Each trajectory has eight contribution epochs and four drain epochs. A drain
uses the same pre-funded capacity and adds no score. After final drain expiry,
no bucket may remain.

## Exact complete-support study

Use the six survivor configurations in the ADR 0012 fixture order. For each
family and `validator` then `node`, retain its reviewed role budget and sweep
selected weight `w = 1..16`. For ordered `a, b = 1..20`:

```text
selected_score = a * w
baseline_score = b
```

The unsplit form maps `selected` and `baseline` to different principals. The
split form uses:

```text
selected_a_units = floor(a / 2)
selected_b_units = a - selected_a_units
```

and multiplies each by `w`. Both selected identities map to
`selected_owner`; a zero half is absent. Total selected score is invariant.

There are `6 * 2 * 16 * 20 * 20 = 76800` role points per mechanism and
identity form. Record credited and paid amounts, zero payout, identity and
principal concentration, and selected-principal payout.

For corresponding forms:

```text
split_advantage = split selected-principal payout
                  - unsplit selected-principal payout
```

Record positive, zero, and negative counts and maximum positive amount. A
mechanism has no profitable same-principal split when every advantage is zero
or negative. It says nothing about identities registered with different
principal labels; negative differences may arise from per-participant floors.

## Trajectory design

All trajectories use budget `100`, history `4`, eight contribution epochs,
and four drain epochs. Scores are weighted research units. The fixture fixes:

- `honest_variance`: two principals range from balanced to `20:1` and reverse;
- `intermittent_availability`: three principals alternate absence, overlap,
  and single-principal epochs;
- `population_change`: a principal joins, another leaves, and the final input
  epoch has one remaining principal;
- `dominant_unsplit`: `alpha` contributes 18 through one participant while
  `beta` contributes 2; and
- `dominant_split`: the same `alpha` contributes 9 and 9 through two
  participants while `beta` contributes 2.

The last pair has identical per-principal work in every input epoch. Their
selected-principal total payout difference is trajectory split advantage.

## Objectives and metrics

Each mechanism and trajectory records checked totals for weighted score,
created, paid, and expired credit, retained budget, maximum pending credit,
zero-payout and payout epochs, identity and principal concentration passes,
native funding events, and native funding failures.

Ratios are reduced nonnegative numerator/positive denominator objects.
`useful_credit_retention` is `paid_credit / created_credit` after drains. It
measures retention of reward credit derived from weighted work, not work
quality or raw-unit coverage. Zero-credit floor inputs remain visible in the
weighted score.

Objectives are:

- `funded`: every emitted native allocation is accepted;
- `bounded_history`: no bucket remains after final drain expiry;
- `bounded_liveness`: expired credit is zero;
- identity/principal concentration: every nonzero payout epoch passes in that
  scope;
- `complete_retention`: paid credit equals created credit; and
- `nonprofitable_split`: no paired selected-principal split advantage is
  positive.

A zero-payout epoch is not a concentration pass and remains a liveness result.

## Native funding and adapter cross-checks

For every trajectory-mechanism result, build an independent native-economy v1
manifest with scenario participants and payout accounts, and:

```text
initial_reward_pool = budget * 12
issued_supply = initial_reward_pool
supply_limit = initial_reward_pool
```

Other buckets and accounts start at zero. Emit one ordinary nonzero
`allocate_reward` per participant payout in epoch and participant order. Every
event must succeed. Final reward pool plus validator and node claims must equal
initial funding, and claims must equal paid credit. Pending or expired study
credit is never included in the manifest.

Independently construct representative node-role participation-v1 flows for
balanced, dominant, and same-owner split points. Finalize their budgets, call
unchanged `build_funding_events`, and require exact equality with proportional
payouts. Execute those events through native economy and require acceptance.
Any mismatch aborts. Capped outputs are never called participation-v1
entitlements.

## Design fixture and report

The design fixture schema is
`protocol-stack/reward-distribution-design/v1`. It contains exactly the study
name, mechanisms, cap ratio, history and drain lengths, exact-support ranges
and counts, survivor identifiers, and five complete trajectories.

The report schema is `protocol-stack/reward-distribution-study/v1`. It contains
the design digest, exact-support summaries, trajectory summaries, paired split
comparisons, adapter cross-check count, global objective counts, and a study
digest over the preceding object. Arrays retain specified order.

## Compatibility and exclusions

The study imports accepted simulator functions but changes none. It uses no
wall clock, network input, package randomness, model inference, external
verifier, decimal arithmetic, or mutable dataset.

Outputs cannot select a production owner definition, registrar, admission
rule, identity proof, cap ratio, history, expiry, reward source, budget, weight,
rate, authority, claim right, transition, encoding, migration, or activation.
They omit operator costs, market demand, collusion, principal concealment,
delegation, stake power, and strategic equilibrium.
