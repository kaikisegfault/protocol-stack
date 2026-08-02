# Minimum-entitlement study report v1

Date: 2026-08-02

Status: M2 research evidence; no production floor or reward rate selected

## Question

Can a deterministic, strictly funded minimum entitlement give every smallest
accepted honest contributor a positive payout across the eighty zero-credit
coordinates from ADR 0014 without increasing a hidden principal's payout when
fixed useful work is split across registered labels?

## Method

The standard-library Python study implements the predeclared
`minimum-entitlement-study-v1` contract. It rebuilt the six ADR 0012 survivor
families, both roles, selected weights `1..16`, sixteen dominant raw units, and
one honest raw unit. It retained exactly the eighty unsplit coordinates where
the unchanged proportional formula paid the honest participant zero. They are
the `case_00`, `case_01`, `case_15`, and `case_21` 100-atom configurations,
both roles, at selected weights `7..16`.

For hidden-principal identity count `k = 1..16`, dominant raw work was
partitioned losslessly by quotient and remainder. Every identity used a
distinct participant, owner, and payout label. The study compared:

```text
zero floor:          reserve_i = 0
per participant:     reserve_i = m
work proportional:   reserve_i = m * raw_units_i
```

It summed reserves first, rejected any reserve above the fixed role budget,
allocated the remaining budget by the unchanged weighted proportional floor
formula, and then applied each accepted reward mechanism. The zero family used
only `m = 0`; the two reserve families used every common floor `m = 0..5`.
This produced 3,840 zero-family forms and 23,040 forms for each reserve family,
or 49,920 evaluated forms in total.

The report distinguishes same-floor split gain from amplification relative to
the unchanged zero-floor unsplit payout. It also derives the exact maximum
floor and identity-count formula at every boundary. No clipped or prorated
reserve, floating point, randomness, network input, wall clock, model
inference, or external verifier is used.

## Reproducible identity

- Design digest:
  `b4063b2ec8b6035a1f9b76008100c3d6dbf63cfbb8f52a989f8e1d9f2daef03f`.
- Study digest:
  `e07a9d6f9e0b691a772b7195440d1c9d010dd0fd17f934c92b36dc98e2cec67b`.
- Retained coordinates: 80.
- Evaluated forms: 49,920.
- Accepted zero-floor cross-checks: 3,840.
- Participation weighted-work replays: 6.
- Native funding replays: 126.

## Common-support result

Each reserve-family and mechanism row contains 6,400 positive-floor forms and
7,200 split comparisons across all six common floors, including floor zero.

| Floor family | Mechanism | Positive honest payouts | Profitable same-floor splits | Positive baseline amplification | Joint break-even |
| --- | --- | ---: | ---: | ---: | ---: |
| Per participant | Proportional | 6,400 / 6,400 | 0 / 7,200 | 0 / 7,680 | 1 |
| Per participant | Participant cap | 6,400 / 6,400 | 7,200 / 7,200 | 7,600 / 7,680 | none |
| Per participant | Principal cap | 6,400 / 6,400 | 7,200 / 7,200 | 7,600 / 7,680 | none |
| Work proportional | Proportional | 6,400 / 6,400 | 0 / 7,200 | 0 / 7,680 | 1 |
| Work proportional | Participant cap | 6,400 / 6,400 | 7,200 / 7,200 | 7,600 / 7,680 | none |
| Work proportional | Principal cap | 6,400 / 6,400 | 7,200 / 7,200 | 7,600 / 7,680 | none |

Under proportional allocation, floor one is a complete-support joint boundary
for both reserve families. Every one-unit honest contributor receives one
atom. No split increases the hidden principal's payout relative to either the
same-floor unsplit form or the unchanged zero-floor unsplit baseline. Integer
flooring of the remaining proportional budget sometimes lowers the aggregate
dominant payout as labels split: there were 6,408 negative per-participant
same-floor differences and 5,768 negative work-proportional differences. A
negative rounding difference is retained as evidence; it is not redistributed.

This result does not make per-participant and per-work reserve semantics
equivalent. The per-participant reserve total changes with `k`; the work reserve
total remains `17 * m`. They happen to share the proportional pass over the
complete common support because neither creates positive hidden-principal
payout amplification there.

Neither reserve family repairs either accepted cap. Every capped split form is
profitable at every tested floor. Both capped mechanisms are byte-identical
because all registered principals are distinct. Their maximum same-floor gain
is 99 atoms, first witnessed by `case_00`, validator role, weight eight, floor
zero, and a three-way dominant split. Positive floors also turn honest credit
into cap room: relative to the zero-floor unsplit baseline, 7,600 of 7,680
capped forms increase hidden-principal payout.

## Exact funding boundaries

All retained coordinates have budget `B = 100`. For positive floor `m`:

```text
per-participant maximum floor = floor(100 / (k + 1))
per-participant maximum k = min(16, floor(100 / m) - 1)
work-proportional maximum floor = floor(100 / 17) = 5
```

The per-participant maximum falls from 50 at `k = 1` to 5 at `k = 16`.
It exactly exhausts the budget at `(k, m)` values `(1, 50)`, `(3, 25)`,
`(4, 20)`, and `(9, 10)`. All four equality projections are feasible. For
every family and `k`, the next integer floor is rejected before credit or
payout creation. The work-proportional maximum is five for every identity
count, reserves 85 atoms, and leaves fifteen for weighted allocation.

The common ceiling is therefore five. Larger per-participant floors are local
boundaries only: they cannot be one globally funded floor across all sixteen
identity counts. These formulas locate funding limits but do not recommend a
budget, floor, rate, or reserve recipient.

## Concentration, liveness, and compatibility

Both positive-floor families paid every smallest honest form and every form
remained live. That does not make the resulting payout balanced after hidden
aggregation. No proportional form passed the unchanged 75-percent
concentration alarm because the fixed design deliberately compares one honest
unit with sixteen heavily weighted dominant units. Only 400 of 7,680 forms per
capped reserve-family row passed after hidden aggregation; another eighty
zero-floor unsplit forms paid nobody and are `null`, not passes.

Synthetic zero-work labels changed none of the nine family/mechanism probes and
received no reserve. All 3,840 zero-family forms exactly matched the public
reward-distribution v1 projection. Six boundary work forms reproduced their
raw units and selected weights through participation v1; its unchanged adapter
matched the zero-family proportional payout. All 126 selected floor and cap
payout maps were accepted by fresh, pre-funded native-economy reward pools.
Typed claims equaled calculated payouts, and reward pool plus claims equaled
the 100-atom initial funding.

No accepted simulator schema, digest, transition, event, adapter, M1 byte or
root, persistence behavior, ABCI behavior, supply rule, C++ transition, or
validator set changed.

## Interpretation

The bounded result retains proportional allocation with a floor of one as a
research hypothesis: it fixes zero payout over this support without increasing
hidden-principal payout or creating an unfunded claim. It simultaneously
rejects both minimum-entitlement families as repairs for the accepted caps.
The capped failure is structural at the registered-scope boundary, not a lack
of honest minimum credit.

The proportional pass is not a production recommendation. The support fixes
one honest unit, sixteen dominant units, synthetic weights, a 100-atom budget,
and reviewed survivor families; it does not establish empirical work quality,
participant costs, demand, identity uniqueness, strategic equilibrium,
issuance sustainability, or a fair concentration target. Selecting any floor
requires broader work and participant distributions, multi-epoch credit and
entry analysis, empirical economics, and independent fairness and security
review. No identity provider, registrar, uniqueness proof, floor, reward rate,
budget, actor, claim, transaction, or consensus transition is accepted.
