# Native-economy simulation report v1

Date: 2026-07-29

Status: M2 research evidence; not a production parameter recommendation

## Question

Can the proposed typed-bucket accounting contract exercise multi-actor
issuance, fee, reward, escrow, stake, unbonding, and penalty flows while
preserving exact supply conservation, deterministic replay, bounded integer
arithmetic, and visible liabilities?

## Method

The standard-library Python simulator implements
`native-economy-simulation-v1.md` independently of the C++ ledger. The study
command was:

```sh
python3 simulation/native_economy/study.py \
  --seed-start 0 --seed-count 24 --rounds 4
```

Each run used the specified `SplitMix64-v1` stream only to create a fixed
ordered event array. Replay itself used no randomness, time, network, C++, or
external data. Every run began with four 100,000-unit research accounts,
100,000 treasury units, 500,000 issued units under a 1,000,000-unit limit,
two validators, and two nodes. Those values are test fixtures.

The generated corpus contained 2,112 events. It combined account transfers,
explicit issuance, fee collection and integer allocation, treasury reward
funding, validator and node claim allocation and pull claims, escrow locks and
releases, bonding, partial unbonding, penalties against both bond phases,
height/epoch advances, and explicit penalty routing. Separate boundary tests
exercise rejected events and full-capacity arithmetic.

## Reproducible result

- Study digest:
  `13e5f4dab789137b99e87197bb8c735e200ec9892e823e8b26a0bac1827d98f1`.
- All 2,112 generated events were accepted.
- All 24 runs preserved both custody equality and
  `issued_supply + issuance_capacity = supply_limit` after every accepted
  event.
- Repeating generation and replay produced byte-identical canonical JSON,
  state digests, trace digests, metrics, and study digest.
- Seed-zero trace digest:
  `bb526fcd55e843398d228f0aef1b36f96d37569cf1311056a507240fe9d1f6f7`.
- Seed-23 trace digest:
  `33ecc87bfef5a35c9db7ebe0ae54ca97fb26f47240d0b727f8ca62cebe50c197`.

Final inventory ranges across the 24 runs were:

| Metric | Minimum | Maximum |
| --- | ---: | ---: |
| Issued supply | 500,103 | 500,173 |
| Remaining issuance capacity | 499,827 | 499,897 |
| Spendable accounts | 399,508 | 399,750 |
| Treasury | 99,627 | 99,908 |
| Bonded stake | 309 | 419 |
| Reward pool | 297 | 481 |
| Locked value | 309 | 419 |
| Protocol-owned value | 100,038 | 100,284 |

Escrows and unbondings returned to zero at each generated round boundary;
claimable rewards also returned to zero because each allocated validator and
node claim was pulled during the same round. Remaining locked exposure was
therefore the intentionally retained portion of each bond. The exact final
account Gini coefficient ranged from `525/799088` to `4997/1598188`; no
floating-point approximation was used.

Cumulative accepted flows were:

| Flow | Atomic units |
| --- | ---: |
| Issuance | 3,415 |
| Fees charged and allocated | 5,320 |
| Fee share to reward pool | 1,557 |
| Fee remainder to treasury | 3,763 |
| Treasury reward funding | 14,610 |
| Escrow opened and released | 7,215 |
| Stake bonded | 14,999 |
| Unbonding begun | 5,311 |
| Unbonding completed after penalties | 4,705 |
| Validator rewards allocated and claimed | 3,578 |
| Node rewards allocated and claimed | 2,880 |
| Penalties assessed and routed | 1,515 |

## Adversarial evidence

The fixed reviewed fixture exercises every bucket and both escrow source
types. Focused tests independently establish issuance-cap rejection, checked
fee-share and epoch overflow, wrong height, accepted replay, unauthorized
actors, zero amounts, absent and duplicate records, invalid targets, early
release, insufficient funds, malformed and duplicate-key JSON, role
separation, failure atomicity, and reuse of an identifier after a failed
attempt. Every accepted journal sums to zero; every ordinary failure has an
empty journal and identical before/after state digest.

## Interpretation

The result supports the structural model: typed custody plus explicit
liabilities is sufficient to close the accounting equation through the
required native-economy flows, and pull claims avoid mandatory participant-wide
payout iteration. It does not establish that the fixture's issuance amounts,
fee share, epoch length, unbond duration, allocations, staking levels, or
penalty sizes are economically sound.

Before any C++ transition is accepted, later M2 work must compare parameter
families under adverse participation and revenue conditions, define
validator/node eligibility and authority proofs, decide upgrade and migration
semantics, and obtain independent economic and security review.
