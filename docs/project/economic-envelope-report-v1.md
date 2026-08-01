# Economic envelope report v1

Status: reproducible M2 high-resolution evidence; not production tokenomics or
a mainnet-readiness assessment

## Question

Around the six parameter families that survived the broad ADR 0011 screen,
where are the exact reward-funding boundaries, and can contribution weights
alone keep both two-participant roles within the accepted three-quarter
maximum-share alarm across the complete contribution-unit support?

The study answers only those two questions. It does not estimate demand,
market value, operator cost, participation, compromise probability, or a safe
production range.

## Method

The standard-library-only `simulation/economic_stress` package retains these
six screened configurations:

```text
case_00 case_01 case_09 case_15 case_21 case_24
```

For each family, the study:

1. represents every integer issuance value in `100..2500` and every integer
   per-role reward budget in `50..1500`;
2. losslessly compresses the monotone issuance axis into one exact threshold
   profile per budget;
3. sweeps every validator and node selected-contribution weight pair in
   `1..16`;
4. exhausts all `20^4 = 160000` ordered contribution-unit combinations rather
   than sampling more seeds; and
5. independently reproduces floor entitlements, fee split, treasury funding,
   reward availability, and the exact rational concentration comparison.

Focused tests compare the projection with the unchanged authority,
participation, and native-economy simulators and their accepted adapters at all
twelve broad-screen robust case/seed anchors, every family at both grid
extremes, and immediately below and at an exact treasury threshold.

Run the study with:

```sh
python3 simulation/economic_stress/envelope_study.py
```

The reviewed design digest is:

```text
d1c62bd5e925dfb2217db18001f1316dd52380d4527e07249c082a5c2874277d
```

## Financial envelope

The grid represents 3,483,851 issuance/budget cells per family and 20,903,106
overall. A cell is `solvent` only when every one of the 160,000 contribution
combinations can fund all created entitlements in the accepted synthetic event
order.

| Classification | Cells |
| --- | ---: |
| `solvent` | 12,535,520 |
| `mixed` | 0 |
| `insolvent` | 8,367,586 |

Per-family results were:

| Family | Solvent | Insolvent |
| --- | ---: | ---: |
| `case_00` | 2,066,561 | 1,417,290 |
| `case_01` | 2,042,651 | 1,441,200 |
| `case_09` | 2,160,201 | 1,323,650 |
| `case_15` | 2,160,201 | 1,323,650 |
| `case_21` | 2,052,953 | 1,430,898 |
| `case_24` | 2,052,953 | 1,430,898 |

The exact maximum all-combination-funded per-role budget at selected issuance
coordinates was:

| Family | Issue 100 | Issue 500 | Issue 1,000 | Issue 2,000 | Issue 2,500 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `case_00` | 310 | 510 | 760 | 1,260 | 1,500 |
| `case_01` | 300 | 500 | 750 | 1,250 | 1,500 |
| `case_09` | 350 | 550 | 800 | 1,300 | 1,500 |
| `case_15` | 350 | 550 | 800 | 1,300 | 1,500 |
| `case_21` | 401 | 500 | 750 | 1,250 | 1,500 |
| `case_24` | 401 | 500 | 750 | 1,250 | 1,500 |

These steps follow directly from the fixed fee path and the all-or-nothing
treasury event. `case_00` routes its 20-unit fee entirely to treasury;
`case_01` routes a 200-unit fee entirely to rewards; `case_09` and `case_15`
split 200 equally; and `case_21` and `case_24` route an 800-unit fee entirely
to rewards. Penalties occur after treasury funding and cannot repair a failed
funding event.

No financial cell was mixed. When treasury funding succeeded, the requested
two-role budget covered every entitlement combination. Below the threshold,
the fixed fee-funded reward pool was either sufficient for every combination
or insufficient for all of them at the represented coordinates. Every
accepted transition remained supply-conserving and capped in the composed
cross-checks.

These boundaries do not show that issuance is desirable. They only state how
much synthetic treasury capacity this fixed flow requires for a synthetic
budget after a fixed fee split.

## Concentration envelope

Each of 1,536 family and validator/node weight cells represents all 160,000
ordered contribution combinations.

| Classification | Cells |
| --- | ---: |
| `within_bound` | 0 |
| `mixed` | 1,536 |
| `concentrated` | 0 |

Every weight pair cleared the alarm for some combinations and failed it for
others. No weight pair in `1..16` held both roles within the three-quarter
maximum-share alarm across the complete `1..20` unit support.

For every family, the least concentrated grid cell was validator weight one
and node weight one. It passed 81,796 of 160,000 combinations, the exact ratio
`20449/40000`. Weight sixteen for both roles passed only 900 combinations, or
`9/1600`.

The original survivor coordinates passed these exact combination counts:

| Family | Validator weight | Node weight | Passing combinations | Ratio |
| --- | ---: | ---: | ---: | ---: |
| `case_00` | 1 | 1 | 81,796 | `20449/40000` |
| `case_01` | 4 | 16 | 4,260 | `213/8000` |
| `case_09` | 4 | 4 | 20,164 | `5041/40000` |
| `case_15` | 1 | 1 | 81,796 | `20449/40000` |
| `case_21` | 1 | 1 | 81,796 | `20449/40000` |
| `case_24` | 4 | 4 | 20,164 | `5041/40000` |

The result rejects a weight-only robustness claim for this fixture. A later
reward design must evaluate mechanisms such as multi-epoch aggregation,
bounded marginal contribution, more participants per role, payout smoothing,
or an explicit distribution rule. None is selected here, and real
contribution measurement and Sybil resistance remain unresolved.

## Interpretation and limits

The evidence supports these bounded conclusions:

- the accepted fee and treasury event order creates a sharp, exactly
  auditable funding frontier;
- retained floor remainder never violates conservation and can affect a
  boundary by atomic units;
- fee routing changes the frontier but does not create a production budget;
- issuance can fund synthetic obligations but is not evidence for inflation;
- selected contribution weights cannot guarantee the existing distribution
  alarm across the complete accepted unit support; and
- the twelve broad-screen robust runs were isolated points, not robust
  production neighborhoods.

The experiment omits transaction demand and pricing, asset value, operator
costs, participant entry and exit incentives, adaptive behavior, delegation,
validator consensus power, empirical contribution distributions, correlated
operators, Sybil resistance, compromise rates, and cryptographic verification.

The canonical study digest is:

```text
3af8b35f0ea7e0b378e1974da307dd9d16ae2475089ff4b53e582e815e48559f
```

No family, boundary, weight, budget, fee route, or issuance amount is a
production recommendation. Any later candidate requires empirical assumptions,
an independently reviewed reward-distribution mechanism, economic and security
review, and a separate consensus specification with activation and migration.
