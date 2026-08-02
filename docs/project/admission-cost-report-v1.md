# Admission cost study report v1

Date: 2026-08-02

Status: M2 research evidence; no production identity or admission rule selected

## Question

Can a recurring per-identity operating cost or refundable native-bond
capital-time cost remove every profitable hidden-principal split found under
the ADR 0013 caps without excluding the smallest accepted honest contributor,
creating an unfunded claim, or counting returned principal as a fee?

## Method

The standard-library Python study implements the predeclared
`admission-cost-study-v1` contract. It retained the six ADR 0012 survivor
families, both roles, their reviewed budgets, and all three unchanged ADR 0013
mechanisms.

At each of 3,840 base coordinates, dominant work remained exactly sixteen raw
units while selected weight swept `1..16` and honest work swept `1..20`. The
dominant work was partitioned losslessly across every identity count `1..16`.
Every identity received a distinct participant, owner, and payout label, so
neither accepted cap could group the hidden principal. This produced 61,440
identity forms and 57,600 split comparisons per mechanism.

The study derived the minimum integer operating cost by exact ceiling division
instead of enumerating prices. It separately expressed refundable bond cost as
an open rational capital-time-rate boundary over checked amount-times-lock
exposure for every post-exit lock `1..16`. Returned principal never entered
utility.

Thirty-two persistent and churn trajectories per mechanism then held sixteen
dominant and one honest unit fixed for eight contribution epochs plus four
drain epochs. Native-economy general escrows independently replayed persistent
and churn unit bonds for all sixteen lock lengths. Proportional points with one,
two, and sixteen dominant identities were independently reproduced through
participation v1 and its funding adapter.

The replay used no floating point, wall clock, network input, package
randomness, model inference, mutable dataset, or external verifier.

## Reproducible identity

- Design digest:
  `5af307b2b7dcd4421951db807d37458fddb182e1c151529eb657519ad2244f0b`.
- Study digest:
  `011c4a787a22dc72ef85e30a5b71f9444c0d53b6767674a8c5aa562e550e5da7`.
- Base coordinates: 3,840.
- Identity forms per mechanism: 61,440.
- Persistent and churn trajectories: 96.
- Native lock replays: 32.
- Participation/adapter/native-economy cross-checks: 3.

## Exact-support result

| Mechanism | Profitable split forms | Maximum gain | Deterrence floor | Honest-entry ceiling |
| --- | ---: | ---: | ---: | ---: |
| Proportional | 0 / 57,600 | 0 | 0 | 0 |
| Participant cap | 51,960 / 57,600 | 495 | 495 | 0 |
| Principal cap | 51,960 / 57,600 | 495 | 495 | 0 |

The two capped mechanisms produced byte-identical payout maps at every point.
Once owner and payout labels were distinct, principal capping reduced exactly
to participant capping. The maximum witness used the `case_09` 500-atom budget,
validator role, selected weight sixteen, one honest unit, and a two-way split:
the hidden principal's payout increased from 3 to 498 atoms.

The capped mechanisms paid zero in 112 identity forms. Every other capped form
passed the alarm under its registered labels, but only 9,368 of 61,440 passed
after all dominant identities were recombined under the hidden principal. The
registered metric therefore does not establish principal concentration when
registration labels can be split.

The smallest one-unit honest contributor received zero at 80 of 192 unsplit
family, role, and weight coordinates. The first deterministic witness was the
`case_00` 100-atom budget at selected weight seven. Consequently, no positive
integer per-identity cost can both deter every capped split and preserve every
smallest honest entry: the required inclusive interval is `495 <= c <= 0`.

For unit-bond normalization the one-epoch capital-time conclusion is the same.
At lock one the capped deterrence rate must be strictly greater than `247`,
while the complete-support honest upper bound is zero. At lock sixteen the
lower bound scales to strictly greater than `494/17`, but the honest upper
bound remains zero. No tested lock creates a joint rational-rate interval;
changing bond amount scales both exposure denominators and does not repair the
zero-reward witness.

## Persistent and churn result

| Mechanism | Profitable strategies | Maximum gain | Deterrence floor | Honest horizon payout |
| --- | ---: | ---: | ---: | ---: |
| Proportional | 0 / 32 | 0 | 0 | 40 |
| Participant cap | 31 / 32 | 632 | 632 | 40 |
| Principal cap | 31 / 32 | 632 | 632 | 40 |

Only the unsplit persistent baseline lacked a profitable capped deviation. A
persistent two-way split raised the hidden principal's twelve-epoch payout
from 120 to 752 atoms, so its one additional admission requires an integer
cost of at least 632. Churning two fresh identities per input epoch produced
the same gross payout but spread the gain over fifteen additional admissions,
for a per-admission break-even of 43. A persistent or churned sixteen-way form
paid 640 atoms, a 520-atom gain; their respective per-admission break-evens
were 35 and 5.

The trajectory-wide capped operating interval is `632 <= c <= 40`, also empty.
Every lock `1..16` has an empty capital-time rate interval. Only one of the 32
capped strategies passed hidden-principal concentration across all nonzero
payout epochs.

The cost boundary is an incentive result, not identity prevention. It assumes
the declared utility numeraire and that every distinct admission bears the
cost or lock. It does not prove that a registrar can observe the hidden
principal, prevent rented identities, or enforce an external operating cost.

## Lock, funding, and compatibility evidence

All 32 native lock replays rejected the selected pre-unlock release with
`TOO_EARLY`, left the failed state unchanged, returned all sixteen unit bonds,
ended with no escrow, and conserved issued supply. Persistent peak lock was
sixteen units. Churn peak lock was exactly `min(16, lock + 1)`, exposing how a
longer refund delay increases concurrent capital without treating that capital
as spent.

Every nonzero payout in all 96 trajectories was accepted against an
independently pre-funded native-economy reward pool. Final reward pool plus
typed claims equaled initial funding, and claims equaled paid credit. The
one-, two-, and sixteen-way proportional points exactly matched participation
v1 entitlements, `build_funding_events`, and native-economy allocations.

No accepted simulator schema, digest, transition, event, adapter, M1 byte or
root, persistence behavior, ABCI behavior, supply rule, C++ transition, or
validator set changed.

## Interpretation

The study rejects cost-only admission as a complete answer over the declared
support. Hidden-principal splitting is widely profitable under both capped
forms, while some smallest accepted contributors receive no payout from which
any positive identity cost or capital-time charge could be recovered. A
longer refundable lock raises capital exposure and slows reuse, but it cannot
create a nonempty deterrence-and-entry interval when the honest upper bound is
zero.

This does not select free admission or reject all bonds. It shows that any
production proposal needs more than a synthetic universal per-identity cost:
empirical work and operating-cost distributions, an explicit principal or
resource-binding threat model, treatment of zero-entitlement useful work,
heterogeneous access to capital, strategic entry and exit analysis, and
independent economic, privacy, and security review. No identity provider,
registrar, uniqueness proof, price, bond, duration, reward rate, actor, or
consensus transition is accepted.
