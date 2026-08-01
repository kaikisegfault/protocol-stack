# Reward distribution study report v1

Date: 2026-08-01

Status: M2 research evidence; no production mechanism or parameter selected

## Question

Can a bounded multi-epoch payout cap eliminate the complete-support
three-quarter concentration failure found by ADR 0012 without creating a
profitable identity split, losing useful-work-derived reward credit, or
emitting an unfunded native claim?

## Method

The standard-library Python study implements the predeclared
`reward-distribution-study-v1` contract. It compares:

- the unchanged proportional floor entitlement;
- a four-opportunity accumulator capped by participant identifier; and
- the same accumulator capped by registered owner principal.

The exact support command was part of:

```sh
python3 simulation/reward_distribution/study.py
```

For every ADR 0012 survivor family and both roles, the study enumerated weights
`1..16` and every ordered contribution pair in `1..20`. Each mechanism saw
76,800 unsplit points and the corresponding 76,800 points where the selected
principal's work was divided deterministically between two participant IDs.

Five fixed eight-epoch trajectories exercised honest variance, intermittent
availability, population change, persistent dominance, and the same dominant
work split across identities. Four no-input allocation epochs then drained or
expired remaining credit. All calculated payouts were replayed against an
independently pre-funded native-economy manifest. Three representative
proportional points were separately reproduced through participation v1 and
its accepted claim-funding adapter.

The study used no floating point, wall clock, network input, package randomness,
model inference, raw telemetry, or external verifier.

## Reproducible identity

- Design digest:
  `9d9157802b488f4e5029859aba8354570b1b725d8ccc00bd19704652e7856eb2`.
- Study digest:
  `3cf94c8c5befbc7dffb185de05496738989d2e3fa50e8cb211cfcc6948594cb4`.
- Exact role points per mechanism and identity form: 76,800.
- Trajectory-mechanism runs: 15.
- Participation/adapter/native-economy cross-checks: 3.

## Exact support result

### Unsplit work

| Mechanism | Nonzero points passing principal alarm | Zero payout | Paid / created credit |
| --- | ---: | ---: | ---: |
| Proportional | 19,020 / 76,800 | 0 | 17,850,052 / 17,850,052 |
| Participant cap | 75,584 / 76,800 | 1,216 | 9,541,176 / 17,850,052 |
| Principal cap | 75,584 / 76,800 | 1,216 | 9,541,176 / 17,850,052 |

For each capped mechanism, every nonzero unsplit payout passed both the
participant and principal three-quarter alarm. The remaining 1,216 points did
not pass by suppressing concentration: they paid zero because one scope had no
positive floor candidate to support a bounded payout. The cap therefore turns
some concentration failures into liveness failures.

### Split work

| Mechanism | Identity-alarm passes | Principal-alarm passes | Zero payout | Paid credit |
| --- | ---: | ---: | ---: | ---: |
| Proportional | 74,988 | 18,936 | 0 | 17,818,172 |
| Participant cap | 76,800 | 20,748 | 0 | 17,674,824 |
| Principal cap | 75,584 | 75,584 | 1,216 | 9,532,968 |

The participant cap makes every split point look bounded by identity, while
only 20,748 pass after the two selected identities are recombined by owner.
It therefore improves the identity metric without controlling the principal.
The principal cap makes every nonzero split point pass both views, with the
same 1,216 zero-payout cases as the unsplit form.

### Same-principal split advantage

| Mechanism | Positive | Zero | Negative | Maximum positive advantage |
| --- | ---: | ---: | ---: | ---: |
| Proportional | 0 | 44,920 | 31,880 | 0 |
| Participant cap | 56,052 | 13,668 | 7,080 | 495 |
| Principal cap | 0 | 69,720 | 7,080 | 0 |

Per-participant floor rounding can make a split disadvantageous, which explains
the negative counts. It never makes the proportional or principal-scoped form
profitable in this complete support. Participant scoping creates a positive
advantage in 73% of points and can release 495 more atoms from a 500-atom
budget when the unsplit dominant scope cannot release value.

This is resistance only to identifiers already bound to the same owner label.
An operator able to register unrelated owner labels remains outside the model.

## Multi-epoch trajectory result

Totals across five trajectories were:

| Mechanism | Created credit | Paid | Expired | Retained budget | Zero-payout epochs |
| --- | ---: | ---: | ---: | ---: | ---: |
| Proportional | 3,992 | 3,992 | 0 | 2,008 | 20 |
| Participant cap | 3,992 | 3,401 | 591 | 2,599 | 15 |
| Principal cap | 3,992 | 2,921 | 1,071 | 3,079 | 12 |

The proportional baseline retained every nonzero credit but passed principal
concentration in none of the five complete trajectories. Participant capping
passed identity concentration in all five and principal concentration in four,
but failed the split trajectory. Principal capping passed both concentration
views in all five, while complete credit retention and bounded liveness passed
in only two.

In the paired persistent-dominance trajectories:

| Mechanism | Unsplit alpha payout | Split alpha payout | Advantage |
| --- | ---: | ---: | ---: |
| Proportional | 720 | 720 | 0 |
| Participant cap | 240 | 720 | 480 |
| Principal cap | 240 | 240 | 0 |

Both capped mechanisms paid 320 of 800 credits and expired 480 when dominance
remained under one participant. Splitting let the participant cap pay all 800
credits, while owner grouping retained the same bounded result as the unsplit
case. The population-change trajectory expired another 111 credits under both
capped scopes after the remaining population became too concentrated.

The cap is therefore not a free concentration improvement. Principal scoping
removes the measured profitable split but sacrifices more payout liveness and
credit retention than participant scoping.

## Funding and compatibility evidence

Every nonzero payout in all 15 trajectories was accepted by native economy v1.
Final reward pool plus node claims exactly equaled each independently pre-funded
pool, and claims exactly equaled calculated paid credit. Pending and expired
study credit never became a native claim.

Balanced, dominant, and same-owner split proportional points produced exact
participation-v1 entitlements, exact `build_funding_events` outputs, and fully
accepted native-economy allocations. Their participation trace digests were:

- balanced:
  `e73101b3d6ea18ce203b205deb59d1745b27416c210596648392c4a79971f3de`;
- dominant:
  `d2bfbea35193fce2504385b69703025e5a9c8d4ef32a82b3b877acb2fa1ac2b0`;
- same-owner split:
  `2863b8f0594d107a099535420fc4119c35d528e14f69ab5f3a7cc424aeecbce2`.

No accepted simulator schema, digest, transition, event, or adapter changed.

## Interpretation

The study rejects a participant-scoped cap as a sufficient concentration
control: it is profitable to split a principal's fixed work across participant
identities in most exact-support points. Grouping by registered owner removes
that measured advantage and bounds every nonzero payout, but it cannot ensure
payout liveness or full useful-credit retention when contribution itself is
more concentrated than the alarm permits.

No compared mechanism simultaneously achieves complete support concentration,
strictly positive payout, complete credit retention, and same-principal split
resistance. M2 therefore has evidence for a real safety/liveness/identity
tradeoff, not a production reward rule.

Before any C++ transition, later work must define admission and principal
binding, analyze splits across apparently unrelated principals, use empirical
work and cost distributions, model strategic behavior and operator exit, and
obtain independent economic and security review. The three-quarter ratio,
four-epoch history, budgets, weights, identities, and funding pools remain
synthetic research coordinates.
