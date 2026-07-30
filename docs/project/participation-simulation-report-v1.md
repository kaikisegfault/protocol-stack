# Participation simulation report v1

Date: 2026-07-30

Status: M2 research evidence; not a production parameter recommendation

## Question

Can a separate validator and resource-node participation contract exercise
registration, delayed activation, recoverable jail, permanent removal, exit,
unbond readiness, bounded verifier results, contribution-weighted
entitlements, and native-economy claim funding while remaining deterministic,
failure atomic, and explicit about every authority and remainder?

## Method

The standard-library Python simulator implements
`participation-simulation-v1.md` independently of the C++ ledger. The study
command was:

```sh
python3 simulation/participation/study.py \
  --seed-start 0 --seed-count 24 --rounds 4
```

Each run used the specified `SplitMix64-v1` stream only to create a fixed
manifest and ordered event array. Replay used no Python randomness, wall
clock, network data, node, C++, model inference, raw telemetry, or external
verifier.

Each run registered two validators and two resource nodes. Validators received
abstract stake-verifier results, all participants crossed a delayed activation
boundary, and four contribution/reward rounds used independently scoped
consensus, storage, and compute verifier principals. Each round temporarily
jailed and explicitly recovered one participant. The final lifecycle then
exited one validator, removed one node, and retained both identities.

After each contribution epoch, a fixed research budget was settled
participant-by-participant and finalized. The study converted every nonzero
entitlement into an ordinary native-economy v1 `allocate_reward` event and
required that independent model to fund the matching typed claim from a
pre-funded reward pool. Budget and policy values were generated test inputs.

## Reproducible result

- Study digest:
  `a76ab6f63132d99ae80809aa1d8f9e8d61763218a7414e8d8efd5e3000a68a57`.
- All 2,184 participation events were accepted across 24 runs.
- All 648 authority proof identifiers were unique and accepted.
- All emitted native-economy claim-funding events were accepted.
- Repeating generation, participation replay, entitlement conversion,
  native-economy funding, and report construction was byte-identical.
- Seed-zero trace digest:
  `f84fc1c718022ecceb63ccf50da6d9a186e2bd29d83de8727da112688686a115`.
- Seed-23 trace digest:
  `429d1b07dda498c5700571b25911ad0a457dca64b9969b89898f6b147a821e30`.

The 192 role-epoch budgets contained 11,900 research units:

| Role | Budgets | Budget amount | Funded entitlements | Retained remainder |
| --- | ---: | ---: | ---: | ---: |
| Validator | 96 | 6,089 | 6,000 | 89 |
| Node | 96 | 5,811 | 5,727 | 84 |
| Total | 192 | 11,900 | 11,727 | 173 |

Twenty-three runs emitted 16 nonzero funding events. One run emitted 15
because integer floor allocation produced one zero validator entitlement.
Zero was retained in the finalized budget remainder and emitted no invalid
zero-amount native-economy event. Per-run funded claims ranged from 376 to 645
units; retained reward-pool remainder ranged from 5 to 8 units.

Accepted contribution inputs were:

| Role and kind | Raw units | Research-weighted units |
| --- | ---: | ---: |
| Validator proposal | 1,048 | 7,336 |
| Validator vote | 1,013 | 3,039 |
| Node compute | 919 | 4,595 |
| Node storage | 1,175 | 2,350 |

These weighted units reflect fixture weights only. They are evidence that the
integer settlement path handles different contribution kinds, not evidence
that one kind deserves a particular production multiplier.

## Adversarial and boundary evidence

The reviewed 34-event fixture reaches active, jailed, recovered, exited, and
removed lifecycle states; settles validator entitlements of 7 and 2 from a
10-unit budget; settles node entitlements of 3 and 1 from a 5-unit budget; and
retains one unit of remainder in each role. Its trace digest is
`22c2b495457a13d7a83837ceeb98893b6df148b9ab99761763744dcbbb07b7e3`.

Focused tests independently establish:

- height-before-replay precedence and reuse of failed event and proof
  identifiers;
- delayed activation and mandatory validator stake confirmation;
- role, owner, and capability separation;
- jail deadlines, two-step recovery, and no eligibility while jailed;
- permanent tombstones and delayed validator unbond readiness after removal;
- exit-epoch eligibility cutoff before a late completion event;
- per-proof and per-participant unit caps plus checked weight overflow;
- proof replay refusal and failure atomicity;
- closed-epoch budgets, participant-scoped settlement, order-independent final
  state, zero entitlements, and exact remainder;
- adapter refusal of payout-account or authority mismatch;
- independent native-economy refusal when the reward pool is underfunded;
- exact successful claim funding and pull payout for both roles; and
- strict JSON fields, duplicate-key refusal, integer-only output, CLI replay,
  and a standard-library/local-model import audit.

## Interpretation

The result supports the structural contract. Stable identity tombstones,
height-derived lifecycle delays, recoverable jail, terminal removal,
capability-scoped verifier results, and participant-scoped settlement can be
replayed deterministically without moving value. The explicit adapter can
then fund only nonzero finalized entitlements through ADR 0008's existing
typed pull-claim buckets, while insufficient funding remains an ordinary
native-economy failure.

The study does not establish production stake thresholds, delays, jail or
removal periods, proof authorities, contribution kinds, weights, budgets,
reward rates, penalty sizes, validator-set policy, or node workload
measurement. Before a C++ transition, later M2 work must compare parameter
families under churn, verifier compromise, collusion, concentration, low
revenue, and prolonged inactivity; specify signed threshold envelopes and
rotation/recovery; define state bounds and migration; and obtain independent
economic and security review.
