# Native-economy simulation v1

Status: Accepted M2 research contract; not a consensus transition

This document is normative for the version-one independent economic simulator.
It fixes input validation, accounting, event behavior, trace construction, and
metrics so research runs are reproducible. It does not change M1 transaction
bytes, state, fees, roots, persistence, ABCI behavior, or supply.

## Scope and numeric domain

The simulator models exactly one native asset. Every monetary amount, height,
epoch, share, counter, and stored total is a JSON integer in the inclusive
range `0..18,446,744,073,709,551,615` (`u64`). JSON booleans are not integers.
Floating-point and decimal values are invalid anywhere in an input document.

All additions, subtractions, multiplications, and derived release epochs must
be checked against `u64`. The fee split described below uses quotient and
remainder decomposition so its mathematical product need not exceed `u64`.

Identifiers are lowercase ASCII strings matching:

```text
[a-z][a-z0-9_-]{0,63}
```

All input objects reject duplicate JSON keys. Each schema object and event
rejects unknown or missing fields. Input arrays retain their given order.
Maps and sets are serialized in ascending identifier order.

## Manifest

The manifest has exactly these fields:

```json
{
  "schema": "protocol-stack/native-economy-simulation-manifest/v1",
  "research_only": true,
  "parameters": {
    "supply_limit": 1000000,
    "epoch_length": 10,
    "unbonding_epochs": 2,
    "fee_split_denominator": 10,
    "fee_reward_parts": 3
  },
  "authorities": {
    "clock": "clock",
    "issuance": "issuer",
    "fee_allocation": "fee_allocator",
    "treasury": "treasury",
    "escrow": "escrow",
    "reward": "reward",
    "penalty": "penalty"
  },
  "participants": {
    "validators": {
      "validator_a": "alice"
    },
    "nodes": {
      "node_a": "bob"
    }
  },
  "genesis": {
    "height": 0,
    "issued_supply": 100000,
    "accounts": {
      "alice": 40000,
      "bob": 30000
    },
    "fee_pool": 0,
    "treasury": 30000,
    "reward_pool": 0,
    "penalty_pool": 0
  }
}
```

`research_only` must be the JSON boolean `true`. `supply_limit`,
`epoch_length`, `unbonding_epochs`, and `fee_split_denominator` must be
nonzero. `fee_reward_parts` must not exceed `fee_split_denominator`.

Every authority principal and participant identifier must be valid.
Participant payout accounts must be valid account identifiers; they need not
have a nonzero genesis balance. A participant identifier cannot occur in both
the validator and node maps. Genesis balances may be zero. Genesis has no
escrow, bond, unbonding, or claim.

The manifest is valid only when checked addition establishes:

```text
issued_supply =
  sum(accounts)
  + fee_pool
  + treasury
  + reward_pool
  + penalty_pool

0 < issued_supply <= supply_limit
```

The manifest fixes research input, not production policy. In particular, its
share, epoch, balance, and authority values are not protocol defaults.

## State and invariants

State contains the immutable manifest, current height, issued supply, account
map, scalar protocol pools, escrow map, bond map, unbonding map, validator
claim map, node claim map, and accepted event-identifier set.

An escrow record contains its kind (`general` or `venture`), beneficiary
account, amount, and unlock epoch. A bond contains its owner account,
validator identifier, and amount. An unbonding contains the same ownership
fields, an amount, and a release epoch. Claim maps associate a registered
participant identifier with an amount.

Zero-balance accounts persist. Zero-valued escrows, positions, unbondings, and
claims do not exist. The current epoch is always:

```text
epoch = height // epoch_length
```

After genesis and every accepted event, checked addition must establish:

```text
custodied =
  sum(accounts)
  + fee_pool
  + treasury
  + sum(escrows)
  + sum(bonds)
  + sum(unbondings)
  + reward_pool
  + sum(validator_claims)
  + sum(node_claims)
  + penalty_pool

custodied = issued_supply
issued_supply <= supply_limit
issuance_capacity = supply_limit - issued_supply
```

Violation is an internal simulator error, never an ordinary event result.

## Event envelope and common validation

Every event contains `id`, `height`, `kind`, and `actor` plus exactly the
kind-specific fields below. `id` and `actor` are identifiers. `height` is
`u64`. An amount is a `u64`; a zero amount returns `ZERO_AMOUNT`.

The decoder checks exact fields, types, identifier syntax, enum values, and
numeric bounds before execution. A decoder error aborts the simulation without
a trace record. A decoded event is evaluated in this order:

1. return `WRONG_HEIGHT` unless event height equals current height;
2. return `REPLAY` if its identifier is already accepted;
3. evaluate the kind's authority rule and return `UNAUTHORIZED` on failure;
4. evaluate the kind-specific preconditions in their documented order;
5. apply all debits and credits to a copy, verify invariants, record the event
   identifier, and atomically publish the copy.

An ordinary failure emits an empty journal, leaves the complete economic state
and state digest unchanged, and does not consume the identifier. Results are:

For ownership rules that depend on a referenced escrow, bond, unbonding, or
participant, existence is necessarily checked before ownership. Those event
sections state that precedence explicitly.

| Name | Meaning |
| --- | --- |
| `OK` | Event accepted |
| `WRONG_HEIGHT` | Event height is not current height |
| `REPLAY` | Event identifier was already accepted |
| `UNAUTHORIZED` | Actor lacks the required capability or ownership |
| `ZERO_AMOUNT` | Monetary amount is zero |
| `NOT_FOUND` | Required account, position, participant, or record is absent |
| `ALREADY_EXISTS` | A new escrow, bond, or unbonding identifier exists |
| `INVALID_TARGET` | Source, destination, role, or timing relation is invalid |
| `TOO_EARLY` | A time-locked release epoch has not arrived |
| `INSUFFICIENT_FUNDS` | The selected source bucket is below the amount |
| `SUPPLY_LIMIT` | Issuance exceeds remaining capacity |
| `OVERFLOW` | A checked destination or derived value exceeds `u64` |

## Events

### `advance_height`

Fields: `to_height`.

The actor must equal the `clock` authority. `to_height` must equal current
height plus one. Height maximum returns `OVERFLOW`; any other target returns
`INVALID_TARGET`. The event changes height but moves no value, so its journal
is empty.

No automatic transfer or iteration occurs at an epoch boundary.

### `issue`

Fields: `amount`.

The actor must equal the `issuance` authority. Zero amount, insufficient
issuance capacity, and checked treasury addition are tested in that order.
Success increases issued supply and treasury by amount.

The balanced journal debits `issuance_capacity` and credits `treasury`.

### `transfer`

Fields: `source`, `destination`, `amount`.

The actor must equal `source`. Source and destination must differ. The source
account must exist and cover amount; destination addition must not overflow.
Success debits the source account and credits the destination, creating a
zero-sequence research account if absent. The simulator models value flow, not
M1 signatures or nonces.

### `charge_fee`

Fields: `account`, `amount`.

The actor must equal `account`. The account must exist and cover amount; fee
pool addition must not overflow. Success debits the account and credits fee
pool. This event represents an already-authorized charge and does not replace
M1 transaction execution.

### `allocate_fees`

Fields: `amount`.

The actor must equal the `fee_allocation` authority. Fee pool must cover
amount. Compute reward credit without overflowing an intermediate:

```text
quotient, remainder = divmod(amount, fee_split_denominator)
reward =
  quotient * fee_reward_parts
  + (remainder * fee_reward_parts) // fee_split_denominator
treasury_credit = amount - reward
```

The two bounded products and the reward addition are checked. Success debits
fee pool, credits reward pool by `reward`, and credits treasury with the exact
remainder. Zero journal entries are omitted.

### `treasury_grant`

Fields: `recipient`, `amount`.

The actor must equal the `treasury` authority. Treasury must cover amount and
the recipient account addition must not overflow. Success transfers treasury
value to the recipient account, creating it if absent.

### `fund_rewards`

Fields: `amount`.

The actor must equal the `treasury` authority. Treasury must cover amount and
reward-pool addition must not overflow. Success transfers the amount from
treasury to reward pool.

### `open_escrow`

Fields: `escrow_id`, `escrow_kind`, `source_kind`, `source`,
`beneficiary`, `unlock_epoch`, `amount`.

`escrow_kind` is `general` or `venture`. `source_kind` is `account` or
`treasury`. For an account source, actor and source must match. For treasury,
actor must equal the treasury authority and source must be the literal
`treasury`. Beneficiary is an account identifier.

The escrow identifier must be unused. Unlock epoch must be strictly greater
than current epoch. The selected source must exist and cover amount. Success
debits the source and creates the escrow.

### `release_escrow`

Fields: `escrow_id`.

The actor must equal the `escrow` authority. The escrow must exist and current
epoch must be at least unlock epoch. Beneficiary addition must not overflow.
Success removes the escrow and credits its complete amount to the beneficiary
account, creating it if absent.

### `bond`

Fields: `bond_id`, `owner`, `validator`, `amount`.

The actor must equal `owner`. The validator must be registered, the bond
identifier unused, and the owner account present with sufficient funds.
Success debits the account and creates the bond.

### `begin_unbond`

Fields: `bond_id`, `unbonding_id`, `amount`.

The bond must exist and actor must equal its owner. The unbonding identifier
must be unused and the bond must cover amount. The release epoch is current
epoch plus `unbonding_epochs`; overflow returns `OVERFLOW`. Success reduces or
removes the bond and creates the unbonding liability.

### `complete_unbond`

Fields: `unbonding_id`.

The unbonding must exist and actor must equal its owner. Current epoch must be
at least its release epoch, and owner-account addition must not overflow.
Success removes the unbonding and credits its complete amount to the owner.

### `allocate_reward`

Fields: `role`, `participant`, `amount`.

`role` is `validator` or `node`. The actor must equal the `reward` authority.
The participant must exist in the corresponding manifest map. Reward pool must
cover amount and the participant's claim addition must not overflow. Success
moves amount from reward pool to the typed claim map.

### `claim_reward`

Fields: `role`, `participant`, `amount`.

The participant must exist in the selected role map. The actor must equal its
configured payout account. The claim must exist and cover amount; payout
account addition must not overflow. Success reduces or removes the claim and
credits the payout account.

### `penalize`

Fields: `source_kind`, `position_id`, `amount`.

`source_kind` is `bond` or `unbonding`. The actor must equal the `penalty`
authority. The selected position must exist and cover amount; penalty-pool
addition must not overflow. Success reduces or removes the position and
credits penalty pool. Issued supply does not change.

### `route_penalty`

Fields: `amount`.

The actor must equal the `penalty` authority. Penalty pool must cover amount
and treasury addition must not overflow. Success transfers quarantined value
to treasury. No version-one event burns issued supply or routes a penalty
directly to rewards or an account.

## Balanced journal

Every accepted monetary event emits entries with `bucket` and signed `delta`.
Buckets use these names:

```text
issuance_capacity
account:<account>
fee_pool
treasury
escrow:<escrow_id>
bond:<bond_id>
unbonding:<unbonding_id>
reward_pool
validator_claim:<participant>
node_claim:<participant>
penalty_pool
```

Entries retain transition order, omit zero deltas, and must sum to zero.
Issuance is balanced against `issuance_capacity`; all other entries move
already issued value. A non-monetary height advance and every ordinary failure
have an empty journal.

## Canonical serialization and digests

Canonical JSON is UTF-8 output from the equivalent of:

```python
json.dumps(
    value,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=True,
    allow_nan=False,
)
```

with no trailing newline. Duplicate keys have already been rejected.

Digests are lowercase hexadecimal SHA-256:

```text
manifest_digest =
  SHA-256("protocol-stack:native-economy:manifest-v1\0" || canonical(manifest))

events_digest =
  SHA-256("protocol-stack:native-economy:events-v1\0" || canonical(events))

state_digest =
  SHA-256("protocol-stack:native-economy:state-v1\0" || canonical(state))

trace_digest =
  SHA-256("protocol-stack:native-economy:trace-v1\0" || canonical(records))
```

The canonical state includes accepted event identifiers in sorted order. It
does not serialize cached totals, derived epoch, metrics, or manifest.

Each trace record contains event index, identifier, kind, acceptance boolean,
result name, height and epoch before and after, journal, and resulting state
digest. A failed record therefore has identical before/after height and state
digest.

The result object contains:

```text
schema = "protocol-stack/native-economy-simulation-result/v1"
manifest_digest
events_digest
records
trace_digest
final_state
metrics
```

`final_state` is the exact canonical state used for its digest.

## Metrics

Metrics contain integers and reduced rational objects only. A rational is:

```json
{"numerator": 1, "denominator": 2}
```

Its denominator is positive; zero is encoded as `0/1`.

Inventory metrics report supply limit, issued supply, issuance capacity, every
scalar pool, and aggregate account, escrow, bonded, unbonding, validator-claim,
and node-claim value.

Exposure metrics report:

- `locked_value`: escrow plus bonded plus unbonding;
- `locked_fraction`: locked value over issued supply;
- `claimable_rewards`: both claim maps;
- `protocol_owned`: fee, treasury, reward, and penalty pools.

Account distribution reports count, sum, minimum, maximum, exact mean, and
exact Gini coefficient over all persistent account balances. For sorted
balances `x[1..n]`, Gini is:

```text
sum((2*i - n - 1) * x[i] for i in 1..n) / (n * sum(x))
```

An empty or zero-sum account population reports `0/1`.

Flow metrics are derived solely from accepted journals and report cumulative
issuance, fees charged, fee allocations, treasury grants, reward funding,
escrow opened/released, stake bonded, unbonding begun/completed, validator and
node rewards allocated/claimed, penalties assessed, and penalties routed.
Research tooling must not interpret any metric as a production recommendation.

## Deterministic scenarios

A scenario generator must name its algorithm and seed. Version one uses an
original, fully specified `SplitMix64-v1` integer stream and deterministic
index selection; it does not use Python's `random` module. Its output is a
manifest and ordinary event array which can be stored, reviewed, and replayed
without the generator.

The fixed fixture and seeded tests must cover every bucket, issuance at and
beyond capacity, every authority class, fee remainder, validator and node
claims, escrow lock and release, partial bond/unbond, bonded and unbonding
penalties, insufficient funds, missing records, overflow, accepted replay,
failed-event atomicity, conservation after every acceptance, exact metrics,
and byte-identical repeated results.

## Compatibility

The two input schema strings, event names and fields, validation order, result
names, journal bucket names, state shape, metric shape, canonical JSON, and
digest domains define simulator version one. Incompatible research-tool
changes require version two.

No simulator state or digest is a protocol commitment. A future consensus
implementation must separately specify canonical encodings, state roots,
transactions, authority proofs, activation, migration, and exact numerical
parameters. It must not infer those from a research fixture.
