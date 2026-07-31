# Authority simulation v1

Status: Accepted M2 research contract; not a consensus transition

This document is normative for the version-one threshold-authority simulator
and its adapters into native-economy simulation v1 and participation
simulation v1. It fixes research input validation, capability and set
versioning, distinct-member threshold results, replay protection, scheduled
rotation, containment, revocation, recovery, trace construction, and exact
target-event binding. It does not change M1 bytes, state, roots, persistence,
ABCI behavior, supply, the CometBFT validator set, or either accepted
simulator-v1 compatibility boundary.

## Scope and numeric domain

The simulator owns no native value, account, participant lifecycle, private
key, public key, signature, raw evidence, model output, or external verifier.
It consumes opaque member-verification results and determines whether they
meet one deterministic research policy.

Every height, epoch, version, threshold, count, delay, and stored total is a
JSON integer in the inclusive range
`0..18,446,744,073,709,551,615` (`u64`). JSON booleans are not integers.
Floating-point and decimal values are invalid anywhere in an input document.
All additions and derived epochs or versions use checked `u64` arithmetic.

Identifiers are lowercase ASCII strings matching:

```text
[a-z][a-z0-9_-]{0,63}
```

A capability is one to three such identifiers separated by `/`. A digest is
exactly 64 lowercase hexadecimal characters representing 32 opaque bytes.
Every object and event rejects unknown or missing fields. Input JSON rejects
duplicate keys. Maps serialize in ascending key order. Sets serialize as
ascending arrays. Input event and approval arrays retain their given order
unless a canonical state record explicitly sorts them.

## Manifest

The manifest has exactly:

```json
{
  "schema": "protocol-stack/authority-simulation-manifest/v1",
  "research_only": true,
  "chain_id": "research_chain",
  "parameters": {
    "epoch_length": 10,
    "min_rotation_delay_epochs": 1,
    "max_rotation_delay_epochs": 4,
    "recovery_delay_epochs": 2,
    "max_action_lifetime_epochs": 2,
    "max_capabilities": 32,
    "max_members_per_set": 8,
    "max_approvals_per_result": 16,
    "max_versions_per_capability": 8
  },
  "clock": "clock",
  "control_sets": {
    "containment": {
      "set_id": "containment_set",
      "version": 1,
      "members": ["contain_a", "contain_b", "contain_c"],
      "threshold": 2
    },
    "recovery": {
      "set_id": "recovery_set",
      "version": 1,
      "members": ["recover_a", "recover_b", "recover_c"],
      "threshold": 2
    }
  },
  "capabilities": {
    "native_economy": {
      "issuance": {
        "set_id": "issuance_set",
        "version": 1,
        "members": ["issuer_a", "issuer_b", "issuer_c"],
        "threshold": 2
      }
    },
    "participation": {
      "registration": {
        "set_id": "registration_set",
        "version": 1,
        "members": ["registrar_a", "registrar_b", "registrar_c"],
        "threshold": 2
      },
      "contribution/validator/vote": {
        "set_id": "vote_set",
        "version": 1,
        "members": ["vote_a", "vote_b", "vote_c"],
        "threshold": 2
      }
    }
  },
  "genesis": {
    "height": 0
  }
}
```

`research_only` must be the JSON boolean `true`. `chain_id`, `clock`,
every module, capability segment, set, and member must be a valid identifier.

All numeric parameters are nonzero. The minimum rotation delay cannot exceed
the maximum. `max_members_per_set` cannot exceed
`max_approvals_per_result`. The manifest contains between one and
`max_capabilities` capability bindings.

Every set has version exactly one at genesis. Its members array is nonempty,
strictly ascending, contains no duplicate, and has at most
`max_members_per_set` entries. Its threshold is in
`1..len(members)`. Set identifiers are globally unique across capability and
control sets. A member may intentionally occur in more than one set; this does
not merge their capability scopes.

The two control sets are immutable in version one. The normal capability map
cannot contain module `authority`. The manifest values are research fixtures,
not production principals, thresholds, delays, or control roots.

## State

State contains current height, one record per capability binding, accepted
event, result, action, and proof identifier sets, and accepted operational
authorization results.

Current epoch is:

```text
current_epoch = height // epoch_length
```

A capability record contains:

```text
module
capability
set_id
active_version
paused
paused_epoch = u64 | null
pause_reason_digest = digest | null
versions
pending_rotation = record | null
```

A version record contains:

```text
version
members
threshold
activated_epoch
retired_epoch = u64 | null
source = genesis | rotation | recovery
revoked_members
```

Versions are consecutive from one, strictly ordered, and never deleted. Exactly
one final version is active and has a null retirement epoch. It equals
`active_version`. Every earlier version has a retirement epoch no earlier
than its activation. A revoked member belongs to that version and occurs once.

When `paused` is false, both pause fields are null. When true, both are
non-null. A pause does not alter the active version.

A pending rotation contains the next consecutive version, strictly ascending
members, threshold, scheduled activation epoch, and the accepted schedule
result, action, and digest identifiers. It is absent while a capability is
paused.

An accepted operational authorization result contains exactly:

```json
{
  "schema": "protocol-stack/authority-result/v1",
  "result_id": "result_1",
  "action_id": "action_1",
  "chain_id": "research_chain",
  "module": "native_economy",
  "capability": "issuance",
  "set_id": "issuance_set",
  "set_version": 1,
  "valid_from_epoch": 0,
  "deadline_epoch": 1,
  "action_digest": "0000000000000000000000000000000000000000000000000000000000000000",
  "authorized_height": 0,
  "authorized_epoch": 0,
  "approvals": [
    {
      "member": "issuer_a",
      "proof_id": "proof_1",
      "evidence_digest": "1111111111111111111111111111111111111111111111111111111111111111"
    }
  ]
}
```

Its approval records sort by member, then proof identifier. Accepted results
sort by result identifier in canonical state.

After genesis and every accepted event, the simulator verifies all record
shapes and cross-references, every numeric bound, strict version continuity,
active and pending relations, pause relations, accepted-result domains, and
that every retained accepted-result identifier occurs in the accepted result
set. An invariant violation is an internal simulator error, never an ordinary
event result.

## Approval results

An approval has exactly `member`, `proof_id`, and `evidence_digest`.
It represents an externally authenticated affirmative member result over the
event's declared action digest. The simulator never dereferences the digest or
verifies a signature.

For one threshold operation, approval evaluation is:

1. return `LIMIT` if the list is empty or exceeds
   `max_approvals_per_result`;
2. in input order, return `PROOF_REPLAY` if a proof identifier was accepted
   previously or occurs earlier in the same event;
3. return `DUPLICATE_MEMBER` if a member occurs earlier in the list;
4. return `UNAUTHORIZED_MEMBER` if the member belongs to none of the sets
   whose threshold must approve this operation; and
5. after the list, return `THRESHOLD` unless each required set contains at
   least its threshold number of the distinct approving members.

One member that belongs to two required sets may count once toward each, as one
verified result over the same digest. Proof identifiers are globally unique
across every accepted threshold operation. Approvals are consumed only when
the complete event succeeds.

## Event envelope and common execution

Every event contains `id`, `height`, and `kind` plus exactly the
kind-specific fields. The decoder validates exact fields, types, identifier
and digest syntax, member-array ordering, enum values, and numeric bounds
before execution. A decoder error aborts replay without a trace record.

Every decoded event begins:

1. return `WRONG_HEIGHT` unless its height equals current height;
2. return `REPLAY` if its event identifier was accepted; and
3. evaluate the documented event conditions against a complete state copy.

A threshold event additionally tests, in order:

1. `RESULT_REPLAY` for an accepted result identifier;
2. `ACTION_REPLAY` for an accepted action identifier;
3. `DOMAIN_MISMATCH` unless its chain equals the manifest chain;
4. the documented capability, set, version, and status conditions;
5. `INVALID_TARGET` if `valid_from_epoch > deadline_epoch` or their
   difference exceeds `max_action_lifetime_epochs`;
6. `TOO_EARLY` if current epoch is before `valid_from_epoch`;
7. `EXPIRED` if current epoch is after `deadline_epoch`;
8. a control-action digest comparison where applicable; and
9. approval evaluation.

The common threshold fields are `chain_id`, `set_id`, `set_version`,
`result_id`, `action_id`, `valid_from_epoch`, `deadline_epoch`,
`action_digest`, and `approvals`. Operational authorization additionally
names its target `module` and `capability`; control events name their
target separately while the digest uses module `authority`.

On success, invariant checking completes before the event, result, action, and
proof identifiers are atomically recorded. An ordinary failure changes no
state and consumes no identifier.

Results are:

| Name | Meaning |
| --- | --- |
| `OK` | Event accepted |
| `WRONG_HEIGHT` | Event height is not current height |
| `REPLAY` | Event identifier was already accepted |
| `RESULT_REPLAY` | Result identifier was already accepted |
| `ACTION_REPLAY` | Action identifier was already accepted |
| `PROOF_REPLAY` | A member proof identifier was already accepted or duplicated |
| `DOMAIN_MISMATCH` | Chain, module, capability, or set family is not the named domain |
| `NOT_FOUND` | Target capability or pending rotation is absent |
| `PAUSED` | Target capability is contained |
| `ALREADY_EXISTS` | A pending rotation or pause already exists |
| `WRONG_SET` | Set identifier or version is not currently eligible |
| `UNAUTHORIZED` | Clock actor lacks its capability |
| `UNAUTHORIZED_MEMBER` | An approval member is outside every required set |
| `DUPLICATE_MEMBER` | One member appears twice in the approval list |
| `THRESHOLD` | One or more required sets lack enough distinct approvals |
| `INVALID_STATUS` | Rotation, pause, revocation, or recovery state forbids the event |
| `INVALID_TARGET` | Version, threshold, member, delay, or validity relation is invalid |
| `TOO_EARLY` | Validity, activation, or recovery epoch has not arrived |
| `EXPIRED` | The authority-result deadline has passed |
| `DIGEST_MISMATCH` | A control digest is not the exact canonical digest |
| `LIMIT` | A manifest execution bound would be exceeded |
| `OVERFLOW` | Checked height, epoch, version, or counter arithmetic exceeds `u64` |

## Action digests

Canonical JSON is UTF-8 output equivalent to:

```python
json.dumps(
    value,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=True,
    allow_nan=False,
)
```

with no trailing newline.

An operational target event is bound by:

```text
SHA-256(
  "protocol-stack:authority:action-v1\0"
  || canonical({
       "schema": "protocol-stack/authority-action/v1",
       "chain_id": chain_id,
       "module": module,
       "capability": capability,
       "set_id": set_id,
       "set_version": set_version,
       "result_id": result_id,
       "action_id": action_id,
       "valid_from_epoch": valid_from_epoch,
       "deadline_epoch": deadline_epoch,
       "action": exact_target_event
     })
)
```

A control action uses the same construction with module `authority`,
capability `rotation`, `containment`, or `recovery`, its authorizing
control or active set identifier and version, and an exact action object
defined below. The action object excludes event `id`, `height`,
`chain_id`, result/action/window fields, digest, and approvals because those
already occur in the outer digest context.

## Events

### `advance_height`

Fields: `actor`, `to_height`.

Actor must equal `clock`. At maximum height return `OVERFLOW`.
`to_height` must equal current height plus one or return
`INVALID_TARGET`. No rotation, pause, expiry, or recovery happens
automatically at a height or epoch boundary.

### `authorize_action`

Fields: `chain_id`, `module`, `capability`, `set_id`,
`set_version`, `result_id`, `action_id`, `valid_from_epoch`,
`deadline_epoch`, `action_digest`, `approvals`.

The module and capability binding must exist. The capability must not be
paused. Set identifier and version must equal its active version. Apply the
common threshold window and approval rules against that active set.

Success records one canonical operational authorization result. It does not
execute or contain the target event.

### `schedule_rotation`

Fields: the common threshold fields plus `target_module`,
`target_capability`, `next_version`, `next_members`,
`next_threshold`, and `activation_epoch`.

The authorizing set fields must equal the target capability's active set. The
target must not be paused or already have a pending rotation. Retained
versions must be below `max_versions_per_capability`.

`next_version` must equal active version plus one. The proposed member array
must satisfy the manifest set rules, and its threshold must be valid. Compute:

```text
minimum = current_epoch + min_rotation_delay_epochs
maximum = current_epoch + max_rotation_delay_epochs
```

Overflow returns `OVERFLOW`. Activation outside the inclusive range returns
`INVALID_TARGET`.

The exact control action is:

```json
{
  "kind": "schedule_rotation",
  "target_module": "native_economy",
  "target_capability": "issuance",
  "set_id": "issuance_set",
  "next_version": 2,
  "next_members": ["issuer_d", "issuer_e", "issuer_f"],
  "next_threshold": 2,
  "activation_epoch": 2
}
```

Require exact control digest equality, then count approvals against both the
current version and the proposed set. Success stores one pending rotation.

### `activate_rotation`

Fields: `actor`, `target_module`, `target_capability`.

Actor must equal `clock`. The capability and pending rotation must exist,
and the capability must not be paused. Current epoch must be at least the
scheduled activation epoch. Success retires the active version at current
epoch, appends and activates the pending version with source `rotation`, and
clears the pending record.

### `pause_capability`

Fields: the common threshold fields plus `target_module`,
`target_capability`, and `reason_digest`.

The authorizing set must equal the immutable containment set. The target must
exist and not already be paused. The exact control action is:

```json
{
  "kind": "pause_capability",
  "target_module": "native_economy",
  "target_capability": "issuance",
  "reason_digest": "0000000000000000000000000000000000000000000000000000000000000000"
}
```

Require the exact containment digest and threshold. Success sets the pause
epoch and reason and clears any pending rotation.

### `revoke_member`

Fields match `pause_capability` plus `member`.

The target must exist and not already be paused. The member must belong to the
active version and must not already be revoked. The exact control action names
kind, target module, target capability, member, and reason digest.

Require the containment digest and threshold. Success appends the member to
the active version's sorted revoked-member set, pauses the capability, and
clears any pending rotation. The active threshold is never silently reduced.

### `recover_capability`

Fields: the common threshold fields plus `target_module`,
`target_capability`, `next_version`, `next_members`, and
`next_threshold`.

The authorizing set must equal the immutable recovery set. The target must be
paused, retained versions must be below their limit, and proposed set fields
must be valid. `next_version` must equal active version plus one.

Compute `paused_epoch + recovery_delay_epochs`; overflow returns
`OVERFLOW`, and an earlier current epoch returns `TOO_EARLY`.

The exact control action is:

```json
{
  "kind": "recover_capability",
  "target_module": "native_economy",
  "target_capability": "issuance",
  "set_id": "issuance_set",
  "next_version": 2,
  "next_members": ["issuer_d", "issuer_e", "issuer_f"],
  "next_threshold": 2
}
```

Require exact recovery digest equality, then count approvals against both the
recovery control set and proposed replacement set. Success retires the active
version at current epoch, appends and activates the replacement with source
`recovery`, clears pause state and any pending rotation, and preserves prior
versions and revocations.

## Shared target-event adapter

The adapter consumes:

- one complete authority simulation result and its parsed manifest;
- one parsed native-economy v1 or participation v1 manifest; and
- an ordered list of `(result_id, exact_target_event)` pairs.

It first validates the complete batch into a temporary list. Any error aborts
with no partial output. Each result identifier must exist exactly once in the
authority final state. The result chain must equal the authority manifest
chain. The result module must equal the target simulator.

The adapter derives the exact capability and expected actor from the target
manifest:

| Module | Event kinds | Capability |
| --- | --- | --- |
| `native_economy` | `advance_height` | `clock` |
| `native_economy` | `issue` | `issuance` |
| `native_economy` | `allocate_fees` | `fee_allocation` |
| `native_economy` | `treasury_grant`, `fund_rewards`, treasury-source `open_escrow` | `treasury` |
| `native_economy` | `release_escrow` | `escrow` |
| `native_economy` | `allocate_reward` | `reward` |
| `native_economy` | `penalize`, `route_penalty` | `penalty` |
| `participation` | `advance_height` | `clock` |
| `participation` | `register_validator`, `register_node` | `registration` |
| `participation` | `confirm_bond` | `stake` |
| `participation` | `activate`, `recover` | `lifecycle` |
| `participation` | `jail`, `remove` | `enforcement` |
| `participation` | `set_reward_budget`, `settle_entitlement`, `finalize_budget` | `reward` |
| `participation` | `attest_contribution` | `contribution/<role>/<contribution_kind>` |

For a clock event, expected actor is the target manifest clock authority.
Every other listed capability uses the corresponding target authority or
contribution verifier. Account-source `open_escrow` and every unlisted
owner-authorized event are invalid adapter targets.

For each pair, the adapter requires:

1. exact target-event schema validity under the target v1 decoder;
2. result module and derived capability equality;
3. target actor equality with the target manifest principal;
4. one matching capability binding in the authority manifest;
5. result set identifier and version matching a retained authority result;
6. exact recomputation of the operational action digest; and
7. no repeated result or target event identifier within the batch.

Adapter errors are `RESULT_NOT_FOUND`, `MODULE_MISMATCH`,
`CAPABILITY_MISMATCH`, `ACTOR_MISMATCH`, `SET_MISMATCH`,
`ACTION_DIGEST_MISMATCH`, `TARGET_INVALID`, and
`MANIFEST_MISMATCH`.

Success returns byte-for-byte equivalent Python data for the ordered target
events. The target simulator independently executes them and may still return
an ordinary economic or participation failure. Authority acceptance never
creates value, contribution, entitlement, or participant state.

## Canonical trace and digests

Digest domains are:

```text
manifest_digest =
  SHA-256("protocol-stack:authority:manifest-v1\0" || canonical(manifest))

events_digest =
  SHA-256("protocol-stack:authority:events-v1\0" || canonical(events))

state_digest =
  SHA-256("protocol-stack:authority:state-v1\0" || canonical(state))

trace_digest =
  SHA-256("protocol-stack:authority:trace-v1\0" || canonical(records))
```

Canonical state sorts capabilities by `(module, capability)`, versions by
version, version member and revoked-member arrays lexically, authorization
results by result identifier, and every accepted identifier set lexically. It
does not serialize the manifest, cached epoch, or metrics.

Each trace record contains event index, event identifier, kind, acceptance,
result name, height and epoch before and after, state digests before and after,
accepted result and action identifiers or null, and accepted proof identifiers
sorted lexically. Failed records have identical before/after height and state
digest and null or empty accepted-identifier fields.

The result object contains:

```text
schema = "protocol-stack/authority-simulation-result/v1"
manifest_digest
events_digest
records
trace_digest
final_state
metrics
```

## Metrics and adversarial studies

Metrics contain integers only and report:

- capability, active-version, paused-capability, retained-version, member, and
  threshold counts;
- accepted and rejected events by kind and result;
- accepted authorization results by module and capability;
- accepted approval and unique member-proof counts;
- scheduled and activated rotations;
- pauses, member revocations, and recoveries; and
- minimum and maximum approval surplus above threshold for accepted
  operational results.

A deterministic scenario generator must name its algorithm and seed. Version
one reuses the exact `SplitMix64-v1` algorithm from native-economy simulation
v1. Randomness creates fixed manifest and event arrays only. Replay invokes no
random, time, network, C++, node, verifier, or external-data API.

The fixed fixture and reproducible seeded study cover:

- both downstream modules and ordinary capability separation;
- exact threshold, sub-threshold compromise, and threshold collusion;
- duplicate members and proof, result, action, and event replay;
- unauthorized and offline members;
- future, current, and expired validity windows;
- wrong chain, module, capability, set identifier, and set version;
- control digest mutation;
- successful dual-threshold scheduled rotation and activation;
- unavailable proposed members preventing rotation;
- pending-rotation cancellation by containment;
- explicit pause and fail-closed operational results;
- member revocation without threshold reduction;
- too-early and successful dual-threshold recovery;
- action-digest mutation and cross-capability adapter rejection;
- exact native-economy issuance and participation registration adapter output;
- owner-authorized target refusal;
- deterministic replay and ordinary-failure atomicity; and
- checked height, epoch, version, member, approval, capability, and retained
  version bounds.

No generated member, threshold, delay, digest, or action is a production
recommendation.

## Resource limits and compatibility

Manifest parameters bound capabilities, members, approvals, versions, action
lifetime, rotation delay, and recovery delay. Event input length, accepted
identifier history, and authorization-result history are caller-bounded for
research. There is no pruning, migration, identifier reuse, delegation,
weighted threshold, or automatic expiry transition in version one.

The manifest and result schema strings; field names; identifier forms; event
names and fields; validation precedence; result and adapter errors; capability
mapping; action and control digest objects; state and metric shapes; canonical
sort orders; and digest domains define simulator version one. An incompatible
research-tool change requires version two.

No authority state, digest, proof, result, threshold, or set version is a
protocol commitment. A future consensus implementation requires canonical
binary encoding, a reviewed signature and key-management scheme, cryptographic
and decoder fuzzing, state-root integration, transaction and block limits,
history pruning, activation, migration, catastrophic root recovery, production
principals and quorums, and independent security and cryptographic review.
