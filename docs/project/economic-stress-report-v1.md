# Economic stress report v1

Status: reproducible M2 screening evidence; not production tokenomics or a
mainnet-readiness assessment

## Question

When the accepted native-economy, participation, and threshold-authority
models are composed, which synthetic parameter families preserve accounting,
authorization, lifecycle, obligation funding, recovery, and concentration
objectives under one balanced set of adverse conditions?

This study screens mechanics and failure boundaries. It does not estimate
demand, asset price, operator cost, member independence, compromise
probability, or a safe production parameter.

## Method

The standard-library-only `simulation/economic_stress` package executes a
reviewed `OA(27,13,3,2)-GF3-v1` design. Its thirteen three-level factors cover:

- issuance and fee volume;
- fee routing and reward budgets;
- validator and resource-node contribution weights;
- validator minimum bond and penalty severity;
- activation, exit, and unbond delay;
- authority threshold and rotation/recovery delay; and
- one correlated honest-availability and compromise shock.

The 27 configurations replace a full 1,594,323-case Cartesian screen. The
array is strength two: every factor level occurs nine times, and every factor
pair covers all nine ordered level pairs exactly three times. Eight explicit
`SplitMix64-v1` seeds replicate contribution-unit and opaque-evidence
variation, producing 216 runs.

Each run:

1. obtains exact threshold results for privileged participation targets;
2. executes registration, activation, contributions, two role budgets,
   entitlements, and one validator exit;
3. derives exact native-economy allocation targets from finalized
   entitlements;
4. replays the complete authority list and releases only exact retained
   results;
5. executes capped issuance, fees, fee routing, treasury reward funding,
   bonds, penalties, allocations, claims, and unbonding; and
6. attempts dual-threshold authority rotation, containment, and delayed
   recovery.

The correlated shock supplies `(honest, compromised)` member counts of
`(3,0)`, `(2,1)`, and `(1,2)`. Legitimate results use only the honest subset;
one captured issuance attempt uses only the compromised subset. This exposes
the configured trust boundary without treating the synthetic shock as a
deployment forecast.

Run the reviewed study with:

```sh
python3 simulation/economic_stress/study.py --seed-start 0 --seed-count 8
```

The reviewed design digest is:

```text
b59793533b8c963c47ca0d3d182eb320c144b8e4d3929b41b75e777c7dc83647
```

## Results

The 216 runs produced this classification:

| Classification | Runs |
| --- | ---: |
| `robust` | 12 |
| `fragile` | 92 |
| `infeasible` | 112 |

`robust` means every predeclared objective passed. `fragile` means supply and
capture safety held, but at least one availability, lifecycle, recovery,
execution, funding, or concentration objective failed. `infeasible` means a
configured threshold was captured, supply failed, or a completely created
obligation could not be fully funded.

Objective pass counts were:

| Objective | Passed |
| --- | ---: |
| supply conserved and capped | 216 |
| legitimate authority available | 144 |
| rotation available | 144 |
| recovery available | 144 |
| participation complete | 144 |
| entitlement funding complete | 96 |
| native-economy flow complete | 96 |
| authority uncaptured | 144 |
| within-role concentration alarm clear | 17 |

Every accepted economic transition conserved the single native asset and no
run exceeded the supply cap. Of 144 runs that completely created
participation obligations, 96 funded them completely and 48 exposed an
ordinary reward-pool shortfall. Every one of the 72 exact-threshold captured
issuance results was released and accepted by the capped economy model; the
cap still conserved supply, but authorization policy was classified
infeasible.

Reverse-stress counts were:

| Code | Runs |
| --- | ---: |
| `AUTHORITY_CAPTURE` | 72 |
| `AUTHORITY_UNAVAILABLE` | 72 |
| `ECONOMY_INCOMPLETE` | 120 |
| `FUNDING_SHORTFALL` | 120 |
| `PARTICIPATION_INCOMPLETE` | 72 |
| `RECOVERY_UNAVAILABLE` | 72 |
| `REWARD_CONCENTRATION` | 199 |
| `ROTATION_UNAVAILABLE` | 72 |

`FUNDING_SHORTFALL` is also reported when participation never completed; only
48 of its 120 occurrences were completely created but underfunded obligations.
Those 48, rather than all 120, trigger the funding part of the infeasible
classification.

## Authority boundary

Every threshold/shock pair occurs in 24 runs. Its structural outcomes were:

| Threshold | Shock | Legitimate live | Uncaptured |
| ---: | --- | ---: | ---: |
| 1 | nominal `(3,0)` | 24 | 24 |
| 1 | degraded `(2,1)` | 24 | 0 |
| 1 | severe `(1,2)` | 24 | 0 |
| 2 | nominal `(3,0)` | 24 | 24 |
| 2 | degraded `(2,1)` | 24 | 24 |
| 2 | severe `(1,2)` | 0 | 0 |
| 3 | nominal `(3,0)` | 24 | 24 |
| 3 | degraded `(2,1)` | 0 | 24 |
| 3 | severe `(1,2)` | 0 | 24 |

This reproduces the intended threshold tradeoff exactly. A count below
threshold cannot authorize or rotate; compromised members at threshold can
authorize the bounded capability. The simulator does not infer whether real
principals are independent or authentic.

## Economic and concentration boundary

The screen separates obligation creation from funding. Treasury funding can
fail even though authority, participation, and conservation all succeed;
fee-to-reward routing may fund some allocations after that failure, and later
allocations fail atomically when the pool is exhausted. No deficit or negative
balance is created.

Only 17 runs cleared the deliberately coarse within-role three-quarter share
alarm. High selected-versus-baseline contribution weights and uneven seeded
units frequently concentrated a two-participant role budget. This demonstrates
that conservation and full funding are not distribution objectives: a run can
pay every unit owed and still be classified fragile for concentration.

The factor array produced 173 distinct authority traces and 153 distinct
participation and native-economy traces. Repetition is expected when different
factor coordinates do not affect an unavailable flow or when integer
allocation maps several inputs to the same outcome.

The canonical default study digest is:

```text
d697f437a5e94d3cbba02cb131609b0591a59930968dc2c5880b49c9590f40de
```

## Interpretation and limits

The evidence supports these bounded conclusions:

- supply conservation remains independent of funding, liveness, distribution,
  and authority-policy success in the tested models;
- authority availability and capture are different objectives and neither may
  be optimized away by silently reducing threshold;
- creating an entitlement does not prove the reward pool can fund it;
- fee destination, treasury capacity, issuance, and reward obligations need a
  joint solvency envelope;
- stake and contribution weights need distribution objectives in addition to
  conservation; and
- rotation and recovery inherit the same correlated availability pressure as
  ordinary authority unless production control roots are independently
  diversified.

The orthogonal design balances every pair but aliases higher-order
interactions. Its results cannot identify causal main effects, fit an optimum,
or extrapolate outside the synthetic levels. The study omits transaction
demand and pricing, market value, operator costs, adaptive behavior, validator
set power, correlated infrastructure failure, empirical compromise rates,
cryptographic verification, history pruning, and governance response.

No factor level, three-quarter alarm, classification, or surviving family is a
production recommendation. Any later candidate requires a narrower
high-resolution experiment, empirical assumptions, independent economic and
security review, and a separate consensus specification with activation and
migration.
