# Participation simulation v1

Status: Accepted M2 research contract; not a consensus transition

This document is normative for the version-one validator and resource-node
participation simulator. It fixes research input validation, lifecycle,
authority-result handling, contribution accounting, entitlement settlement,
trace construction, and the adapter into native-economy simulation v1. It does
not change M1 bytes, state, persistence, ABCI behavior, the CometBFT validator
set, or any production economic parameter.

## Scope and numeric domain

The simulator models two disjoint roles: `validator` and `node`. It owns no
asset, balance, bond, unbonding liability, reward pool, or claim.

Every height, epoch, amount, unit, weight, count, and stored total is a JSON
integer in `0..18,446,744,073,709,551,615` (`u64`). JSON booleans are not
integers. Floating-point and decimal values are invalid anywhere in an input
document. All additions, multiplications, derived epochs, weighted units, and
entitlements use checked `u64` arithmetic.

Identifiers are lowercase ASCII strings matching:

```text
[a-z][a-z0-9_-]{0,63}
```

An evidence digest is exactly 64 lowercase hexadecimal characters and
represents 32 opaque bytes. The simulator never dereferences it. Each object
and event rejects unknown or missing fields. Input arrays retain order. Input
JSON rejects duplicate keys. Maps and sets serialize in ascending identifier
order; record arrays use the explicit tuple order stated below.

## Manifest

The manifest has exactly:

```json
{
  "schema": "protocol-stack/participation-simulation-manifest/v1",
  "research_only": true,
  "parameters": {
    "epoch_length": 10,
    "activation_delay_epochs": 1,
    "exit_delay_epochs": 1,
    "removal_hold_epochs": 2,
    "max_jail_epochs": 4,
    "max_participants": 32,
    "validator_minimum_bond": 1000,
    "max_units_per_proof": 100,
    "max_units_per_participant_epoch": 400
  },
  "authorities": {
    "clock": "clock",
    "registration": "registrar",
    "stake": "stake_verifier",
    "lifecycle": "lifecycle",
    "enforcement": "enforcement",
    "reward": "reward"
  },
  "contributions": {
    "validators": {
      "vote": {
        "verifier": "consensus_verifier",
        "weight": 3
      }
    },
    "nodes": {
      "storage": {
        "verifier": "storage_verifier",
        "weight": 2
      }
    }
  },
  "genesis": {
    "height": 0
  }
}
```

`research_only` is the JSON boolean `true`. `epoch_length`,
`activation_delay_epochs`, `exit_delay_epochs`, `removal_hold_epochs`,
`max_jail_epochs`, `max_participants`, `validator_minimum_bond`,
`max_units_per_proof`, and `max_units_per_participant_epoch` are nonzero.
`max_units_per_proof` cannot exceed
`max_units_per_participant_epoch`.

Every authority, contribution kind, and verifier is a valid identifier.
`validators` and `nodes` each contain at least one contribution kind, and each
kind is scoped by its enclosing role. A weight is nonzero `u64`.

All values are research fixtures. In particular, none is a production stake
threshold, duration, cap, contribution weight, authority, or reward rule.

## State and derived values

State contains:

- immutable manifest parameters and authority bindings;
- current height;
- participant records;
- accepted event and proof identifier sets;
- contribution records and aggregate counters;
- role-epoch budget records; and
- participant entitlements.

Current epoch is:

```text
current_epoch = height // epoch_length
```

A participant record contains:

```text
participant
role = validator | node
owner
payout_account
phase = pending | active | exit_pending | exited | removed
registered_epoch
activation_epoch
activated_epoch = u64 | null
exit_epoch = u64 | null
unbond_ready_epoch = u64 | null
jailed_until_epoch = u64 | null
recovery_requested = boolean
bond_id = identifier | null
confirmed_bond = u64 | null
terminal_reason = identifier | null
removed_epoch = u64 | null
```

Validators have a non-null `bond_id`; nodes have `null`. A confirmed bond is
never zero and exists only for a validator. `activation_epoch` is
`registered_epoch + activation_delay_epochs`. `activated_epoch` records the
explicit successful activation or is null. `exit_epoch` exists exactly for
`exit_pending`, `exited`, or a removed participant that had requested exit.
An exited participant's `unbond_ready_epoch` equals its exit epoch.
`removed_epoch` exists exactly for `removed`. A removed validator has an
unbond-ready epoch no earlier than `removed_epoch + removal_hold_epochs`. Node
records never have an unbond-ready epoch.

A participant is reward eligible for epoch `E` exactly when, at contribution
acceptance:

```text
phase is active or exit_pending
and jailed_until_epoch is null
and (phase is active or E < exit_epoch)
```

A passed jail deadline does not clear jail. Exit eligibility ends at
`exit_epoch` even if `complete_exit` has not executed.

A contribution record is keyed by `(epoch, role, participant, kind)` and
stores raw units and checked weighted units. Aggregate state stores, for each
`(epoch, role, participant)`, its weighted units and, for each
`(epoch, role)`, total weighted units plus the number of participants with a
nonzero total. A participant contributes to that count only on its first
accepted proof for the role and epoch.

A role-epoch budget contains:

```text
epoch
role
amount
total_weight
participant_count
settled_count
allocated
finalized
remainder = u64 | null
```

Its `total_weight` and `participant_count` are immutable snapshots of the
closed contribution epoch. An entitlement keyed by
`(epoch, role, participant)` contains the participant weight and amount,
including a possible zero amount.

After every accepted event, the simulator verifies all record shapes,
cross-references, `u64` values, aggregate sums, phase relations, counter
relations, and:

```text
budget.allocated =
  sum(entitlement.amount for that epoch and role)

budget.settled_count =
  count(entitlements for that epoch and role)

budget.allocated <= budget.amount

if budget.finalized:
  budget.settled_count = budget.participant_count
  budget.remainder = budget.amount - budget.allocated
else:
  budget.remainder is null
```

An invariant violation is an internal simulator error, never an ordinary
event result.

## Event envelope and execution

Every event contains `id`, `height`, `kind`, and `actor` plus exactly the
kind-specific fields below. `height` is `u64`. Identifiers and digests use the
formats above. Proof-bearing events have a `proof_id` distinct from the event
identifier and an `evidence_digest`.

The decoder validates exact fields, types, enums, and numeric bounds before
execution. A decoder error aborts the simulation without a trace record. A
decoded event is evaluated:

1. return `WRONG_HEIGHT` unless its height equals current height;
2. return `REPLAY` if its event identifier was accepted;
3. apply the event's documented authorization and preconditions in order to a
   complete state copy;
4. verify invariants, record the event identifier, and atomically publish the
   copy on success.

For a proof-bearing event, `PROOF_REPLAY` is tested immediately after event
authorization and before event-specific target conditions. A proof identifier
is recorded only on success.

An ordinary failure changes no state and consumes no event or proof identifier.
Result names are:

| Name | Meaning |
| --- | --- |
| `OK` | Event accepted |
| `WRONG_HEIGHT` | Event height is not current height |
| `REPLAY` | Event identifier was already accepted |
| `UNAUTHORIZED` | Actor lacks the required capability or ownership |
| `PROOF_REPLAY` | Proof identifier was already accepted |
| `NOT_FOUND` | Participant, contribution aggregate, or budget is absent |
| `ALREADY_EXISTS` | Participant, bond confirmation, budget, or entitlement exists |
| `INVALID_ROLE` | Supplied role conflicts with the participant or manifest |
| `INVALID_STATUS` | Participant phase or jail/recovery state forbids the event |
| `INVALID_TARGET` | Height, epoch, bond, timing, or evidence relation is invalid |
| `TOO_EARLY` | A scheduled lifecycle or closed-epoch condition has not arrived |
| `LIMIT` | A manifest count or unit cap would be exceeded |
| `ZERO_AMOUNT` | Bond, contribution units, or role budget is zero |
| `BOND_REQUIRED` | Validator activation lacks the required confirmed bond |
| `NOT_ELIGIBLE` | Participant cannot contribute or settle for the target epoch |
| `OVERFLOW` | Checked arithmetic exceeds `u64` |
| `BUDGET_NOT_FINAL` | Claim funding was requested from an unfinalized budget |
| `MANIFEST_MISMATCH` | Claim funding participants, payout accounts, or authority differ |

The last two are adapter errors and never event trace results.

## Lifecycle events

### `advance_height`

Fields: `to_height`.

Actor must equal `clock`. At maximum height return `OVERFLOW`.
`to_height` must equal current height plus one or return `INVALID_TARGET`.
No lifecycle or entitlement transition occurs automatically at an epoch
boundary.

### `register_validator`

Fields: `participant`, `owner`, `payout_account`, `bond_id`, `proof_id`,
`evidence_digest`.

Actor must equal `registration`. Test proof replay, participant existence, and
the participant limit in that order. Success creates a `pending` validator
with a checked activation epoch and no confirmed bond. Participant, owner,
payout, and bond identifiers must be pairwise well-shaped but may name the
same principal where their roles permit it.

### `register_node`

Fields: `participant`, `owner`, `payout_account`, `proof_id`,
`evidence_digest`.

Authorization and precedence match `register_validator`. Success creates a
`pending` node with a checked activation epoch and no bond fields.

### `confirm_bond`

Fields: `participant`, `bond_id`, `amount`, `proof_id`, `evidence_digest`.

Actor must equal `stake`. Test proof replay, participant existence, validator
role, `pending` phase, absent confirmation, matching bond identifier, zero
amount, and the research minimum in that order. An amount below the minimum
returns `BOND_REQUIRED`. Success records the observed amount but moves no
value. The digest is an opaque reference to independently appraised stake
state.

### `activate`

Fields: `participant`.

Actor must equal `lifecycle`. The participant must exist in `pending` phase
and current epoch must be at least `activation_epoch`. A validator must have a
confirmed bond at or above the research minimum. Success changes phase to
`active` and records `activated_epoch = current_epoch`.

### `request_exit`

Fields: `participant`.

Actor must equal the participant owner. The participant must exist in
`active` phase, whether jailed or not. Success checks and records:

```text
exit_epoch = current_epoch + exit_delay_epochs
phase = exit_pending
```

A validator's future unbond-ready epoch is not published until exit completes.
Requesting exit neither moves stake nor cancels a jail.

### `complete_exit`

Fields: `participant`.

Actor must equal the participant owner. The participant must be
`exit_pending`, and current epoch must be at least `exit_epoch`. Success changes
phase to `exited`, clears jail and recovery fields, and for a validator sets
`unbond_ready_epoch = exit_epoch`. It moves no stake. A future consensus
adapter must authorize native-economy `begin_unbond` only at or after this
epoch; native-economy then enforces its independent release delay.

### `jail`

Fields: `participant`, `until_epoch`, `proof_id`, `evidence_digest`.

Actor must equal `enforcement`. Test proof replay and participant existence.
The participant must be `active` or `exit_pending` and not already jailed.
`until_epoch` must be greater than current epoch and at most
`current_epoch + max_jail_epochs`; arithmetic overflow returns `OVERFLOW` and
an out-of-range target returns `INVALID_TARGET`. Success records the deadline
and clears any recovery request. It does not change an exit epoch or stake.

### `request_recovery`

Fields: `participant`.

Actor must equal the participant owner. The participant must be jailed in
`active` or `exit_pending` phase. Current epoch must be at least
`jailed_until_epoch`. If an exit-pending participant has reached its exit
epoch, return `INVALID_STATUS`; it must complete exit instead. An existing
request returns `ALREADY_EXISTS`. Success sets `recovery_requested`.

### `recover`

Fields: `participant`.

Actor must equal `lifecycle`. The participant must be jailed, have requested
recovery, remain in `active` or pre-exit `exit_pending` phase, and have reached
the jail deadline. Success clears jail and the request. A removed participant
can never reach this transition.

### `remove`

Fields: `participant`, `reason`, `proof_id`, `evidence_digest`.

Actor must equal `enforcement`. Test proof replay and participant existence.
An `exited` or `removed` participant returns `INVALID_STATUS`. Success changes
phase to `removed`, stores the reason and `removed_epoch = current_epoch`, and
clears jail and recovery state. For a validator it sets:

```text
unbond_ready_epoch =
  current_epoch + removal_hold_epochs
```

If a later existing exit epoch is greater, that greater epoch is retained.
Nodes retain no unbond-ready epoch. Removal moves and penalizes no value.

## Contribution and entitlement events

### `attest_contribution`

Fields: `participant`, `role`, `contribution_kind`, `epoch`, `units`,
`proof_id`, `evidence_digest`.

The role and contribution kind select one exact verifier from the manifest;
actor must equal it. Test proof replay, participant existence, participant
role, current epoch equality, eligibility, zero units, per-proof cap,
participant-epoch raw-unit cap, checked weight multiplication, checked
participant weighted total, and checked role total in that order.

Success increments the kind record, participant aggregate, and role aggregate.
It records the proof identifier. Multiple accepted proofs may contribute to
one kind record, but each proof remains globally unique.

### `set_reward_budget`

Fields: `epoch`, `role`, `amount`.

Actor must equal `reward`. Role must be valid. `epoch` must be strictly less
than current epoch, ensuring its contribution totals are closed. The
role-epoch aggregate must exist and be nonzero. An existing budget returns
`ALREADY_EXISTS`; zero amount returns `ZERO_AMOUNT`. Success snapshots the
total weight and participant count. It does not reserve or move native value.

### `settle_entitlement`

Fields: `epoch`, `role`, `participant`.

Actor must equal `reward`. The budget and participant contribution aggregate
must exist; role must match. An existing entitlement returns
`ALREADY_EXISTS`. Compute without an unbounded intermediate:

```text
quotient, remainder = divmod(budget.amount, budget.total_weight)
entitlement =
  quotient * participant_weight
  + (remainder * participant_weight) // budget.total_weight
```

Both products, the addition, budget allocated addition, and settled counter
are checked. Success records the entitlement even when zero and updates the
budget counters. Participant lifecycle changes after contribution acceptance
do not retroactively erase an earned entitlement.

### `finalize_budget`

Fields: `epoch`, `role`.

Actor must equal `reward`. The budget must exist and not be finalized.
`settled_count` must equal `participant_count` or return `TOO_EARLY`. Success
sets:

```text
finalized = true
remainder = amount - allocated
```

No amount moves. Finalization is constant-time with respect to participant
count.

## Claim-funding adapter

The adapter consumes:

- one complete participation result and its parsed manifest;
- one native-economy v1 manifest;
- one finalized epoch and role; and
- one native-economy event height.

It checks:

1. the role budget exists and is finalized;
2. every nonzero entitlement participant occurs in the matching
   native-economy manifest role;
3. the native-economy payout account equals the participation registration's
   payout account; and
4. a single principal is both the participation reward authority and the
   native-economy reward authority.

Any mismatch aborts with `MANIFEST_MISMATCH` and emits no partial list.
Otherwise, entitlements are ordered by participant identifier. Each nonzero
entitlement becomes:

```json
{
  "id": "fund_<32 lowercase hex characters>",
  "height": 20,
  "kind": "allocate_reward",
  "actor": "reward",
  "role": "validator",
  "participant": "validator_a",
  "amount": 7
}
```

The suffix is the first 32 hex characters of:

```text
SHA-256(
  "protocol-stack:participation:funding-event-v1\0"
  || canonical({
       "trace_digest": participation trace digest,
       "epoch": epoch,
       "role": role,
       "participant": participant,
       "amount": amount,
       "height": height
     })
)
```

Zero entitlements emit no event. The output list is ordinary native-economy v1
input. Funding succeeds only if that independent simulator accepts each event
against its reward pool. Participation settlement never guarantees available
funds and never creates a native claim by itself.

## Canonical serialization and trace

Canonical JSON and digest construction match native-economy simulation v1:
UTF-8 `json.dumps` with sorted keys, compact separators, ASCII escaping,
non-finite values forbidden, and no trailing newline.

Digest domains are:

```text
manifest_digest =
  SHA-256("protocol-stack:participation:manifest-v1\0" || canonical(manifest))

events_digest =
  SHA-256("protocol-stack:participation:events-v1\0" || canonical(events))

state_digest =
  SHA-256("protocol-stack:participation:state-v1\0" || canonical(state))

trace_digest =
  SHA-256("protocol-stack:participation:trace-v1\0" || canonical(records))
```

Canonical state serializes participants by identifier and both accepted sets
as sorted arrays. Contribution records sort by
`(epoch, role, participant, kind)`, participant aggregates and entitlements by
`(epoch, role, participant)`, and role aggregates and budgets by
`(epoch, role)`. It serializes no cached derived epoch or metric.

Each trace record contains event index, event identifier, kind, acceptance,
result, height and epoch before and after, state digests before and after, and
the accepted proof identifier or `null`. Failed records have identical
before/after height and state digest.

The result object contains:

```text
schema = "protocol-stack/participation-simulation-result/v1"
manifest_digest
events_digest
records
trace_digest
final_state
metrics
```

## Metrics and deterministic studies

Metrics use integers and reduced rational objects only. They report:

- participant counts by role and effective phase, including jailed overlays;
- registration, activation, exit, jail, recovery, and removal event counts;
- accepted proof counts by proof-bearing event and contribution kind;
- raw and weighted contribution units by role and kind;
- budgets, allocated entitlements, retained remainder, and zero
  entitlements by role;
- exact activation-wait, exit-wait, and removal-hold epoch totals; and
- claim-funding event counts and amounts when an adapter study is requested.

A deterministic scenario generator must name its algorithm and seed.
Version one reuses the exact `SplitMix64-v1` algorithm specified by
native-economy simulation v1. Randomness creates a fixed manifest and event
array only; replay uses no random, time, network, C++, node, or external-data
API.

The fixed fixture and seeded tests cover both roles, every lifecycle phase,
activation and exit boundaries, validator bond requirements, recoverable jail,
permanent removal, contribution verifier separation, proof replay and caps,
checked weighted overflow, closed-epoch budgets, zero and nonzero
entitlements, retained remainder, settlement order independence, funding
manifest mismatch, reward-pool insufficiency, accepted claim funding,
deterministic replay, and failure atomicity.

## Resource limits and replay

`max_participants` bounds participant records. Event input length is bounded by
the caller; the simulator processes one event at a time. Per-proof and
participant-epoch caps bound accepted raw units but not the number of accepted
proof records; research callers must bound event arrays. A future consensus
specification must add exact transaction, block, proof-history, epoch-history,
and state-size limits before adopting any behavior.

Accepted event and proof identifiers, tombstones, contribution history,
budgets, and entitlements are retained for the complete research replay.
There is no pruning, migration, or identifier reuse in version one.

## Compatibility

The manifest and result schema strings; fields; roles; phases; event names and
fields; validation precedence; result names; state and metric shapes; adapter
event derivation; canonical JSON; sort orders; and digest domains define
simulator version one. An incompatible research-tool change requires version
two.

No participation state, digest, proof, budget, or entitlement is a protocol
commitment. A future C++ transition requires canonical binary encoding,
signature and threshold rules, verifier rotation/recovery, transaction and
block resource limits, state roots, exact production parameters, activation,
migration, CometBFT validator-update behavior, adversarial simulations, and
independent economic and security review.
