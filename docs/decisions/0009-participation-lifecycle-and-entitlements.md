# ADR 0009: Participation lifecycle and reward entitlements

- Status: Accepted for M2 research
- Date: 2026-07-30

## Context

ADR 0008 closes the native asset's value-flow equation and provides typed
validator and node claim buckets, but its participants are static manifest
entries. M2 still needs a deterministic contract for registration, activation,
exit, jail and recovery, terminal removal, contribution evidence, and reward
eligibility before production thresholds or rates can be evaluated.

This contract must not make mutable telemetry or an external verifier a
consensus oracle. It must distinguish evidence appraisal from deterministic
authorization, cap every accepted contribution, avoid implicit population-wide
work, and expose the exact boundary at which a funded entitlement becomes an
ADR 0008 pull claim.

Primary-source review informed the decision:

- Ethereum's beacon-chain specification represents activity as an
  epoch-bounded interval, delays activation and exit, limits queue churn, and
  keeps a validator slashable through a later withdrawable epoch. These are
  useful lifecycle separations, but its exact queue, stake, reward, and
  slashing parameters are not adopted.
  Sources: [validator predicates and registry][ethereum-registry],
  [exit and withdrawability][ethereum-exit].
- The Cosmos SDK distinguishes unbonded, bonded, and unbonding states, keeps
  unbonding stake slashable for earlier offences, supports recoverable jail,
  and makes tombstoning permanent. The distinction between temporary
  operational failure and terminal safety failure is adopted without its
  wall-clock queues, stake ranking, delegation, or burn policy.
  Sources: [staking lifecycle][cosmos-staking],
  [jail and tombstone behavior][cosmos-slashing].
- Polkadot separates pausing validation from unbonding and uses payable
  activity points rather than raw stake alone to vary validator rewards.
  This supports explicit contribution inputs, but its era, selection,
  commission, and payout rules are not adopted.
  Sources: [validator offboarding][polkadot-offboarding],
  [era points and rewards][polkadot-rewards].
- Filecoin distinguishes provider evidence, ongoing contribution, faults, and
  explicit recovery. Its proof systems demonstrate that role-specific work can
  have independently verified evidence, but no Filecoin proof, quality
  multiplier, collateral threshold, or reward rule is reused.
  Source: [storage mining][filecoin-mining].
- RFC 9334 separates an Attester's Evidence from a Verifier's Attestation
  Result and lets a Relying Party apply its own bounded appraisal policy. This
  is the selected trust shape: the research state machine consumes a
  capability-scoped verifier result, never raw telemetry, and independently
  enforces role, epoch, replay, and unit limits.
  Source: [RATS architecture][rats].

These sources are comparative evidence, not dependencies. The model and
implementation are original, standard-library-only Python research tooling.

## Decision

### Separate participation model

Add a versioned `participation-simulation-v1` research contract instead of
changing native-economy simulation v1. It owns no native value. It records
participant lifecycle, accepted proof identifiers, contribution units,
research reward budgets, and calculated entitlements.

The native-economy simulator remains the only M2 model that moves value. A
participation entitlement becomes funded only when a deterministic adapter
emits an ordinary native-economy `allocate_reward` event and that event is
accepted against the reward pool.

### Stable identity and explicit lifecycle

A registration authority creates one stable validator or node identity bound
to an owner and payout account. Participant identifiers remain as exited or
removed tombstones and cannot be reused in version one.

Registration enters `pending`. Activation is a participant-scoped explicit
event after a height-derived delay. Validators additionally require a
stake-authority result that binds a native-economy bond identifier and amount;
nodes do not implicitly become validators and have no simulated stake
requirement.

An owner may request exit. Eligibility ends at the scheduled exit epoch even
if the explicit completion event is late. Completing exit records the epoch
at which a future native-economy unbond operation may begin. The
native-economy model independently retains the configured unbonding liability
and penalty exposure after that operation.

Temporary jail and permanent removal are distinct. Enforcement may jail an
active or exiting participant until a bounded epoch. Recovery requires both an
owner request after the deadline and a lifecycle-authority event. Removal is
terminal, retains the participant tombstone, and delays unbond readiness by a
research-manifest hold. Neither path silently moves or destroys stake.

### Bounded verifier results

Every registration, stake confirmation, jail, removal, and contribution input
binds a globally unique proof identifier and a 32-byte evidence digest.
Registration, stake, and enforcement principals have distinct capabilities.
Each contribution kind names its own verifier principal and integer research
weight.

Contribution results are accepted only for the current height-derived epoch
while the participant is eligible. Version one caps raw units per proof and
per participant per epoch, checks weighted arithmetic in `u64`, and consumes a
proof identifier only on success. Raw evidence, workload measurement, model
inference, network data, and verifier implementation remain outside replay.

This is a bounded authorization model, not a claim that one production
verifier key is sufficient. Exact signed envelopes, threshold policies,
cryptographic proof systems, key rotation, and verifier recovery remain future
protocol decisions.

### Participant-scoped entitlement settlement

After an epoch ends, the reward authority may set one explicit research budget
for each role with accepted weighted contribution. A participant-scoped
settlement computes:

```text
entitlement =
  floor(role_budget * participant_weight / role_weight)
```

The implementation uses quotient and remainder decomposition so no
intermediate mathematical product need exceed `u64`. Settlement order does not
affect an entitlement. A role budget finalizes only after the recorded number
of contributing participants has settled. Integer remainder stays unallocated
and therefore remains in the native-economy reward pool; it is neither lost
nor routed implicitly.

The claim adapter is deterministic and emits one nonzero `allocate_reward`
event per finalized entitlement. It verifies that the participation role,
participant, payout account, and reward authority agree with the supplied
native-economy manifest. A rejected native-economy event creates no claim and
does not alter the participation result.

No production reward source, role budget, contribution weight, reward rate,
stake threshold, delay, jail duration, removal hold, verifier, or actor is
selected by this ADR. All manifest values are research fixtures.

### Bounded execution

Every state-changing event addresses one participant, proof, role budget, or
height. No height or epoch boundary performs a hidden participant scan or
value transfer. Manifest limits bound registered participants and accepted
contribution units. Budget finalization compares counters rather than scanning
the participant set.

Events execute in input order on a copy. Shape-invalid input aborts replay. An
ordinary failure changes no state and consumes neither event nor proof
identifier. Accepted event identifiers cannot be replayed.

The normative contract is
`../specifications/participation-simulation-v1.md`. It changes no consensus
behavior.

## Alternatives not selected

- **Extend native-economy v1 in place:** its schema and digests are already an
  accepted compatibility boundary. A separate model preserves existing
  fixtures and makes the funding boundary auditable.
- **Self-reported contribution:** an operator could manufacture reward units.
  Capability-scoped verifier results make trust explicit and bounded.
- **Put raw telemetry or general attestation parsers in consensus:** mutable
  measurements and complex vendor formats would expand determinism and parser
  risk. The model consumes only a small, versioned appraisal result.
- **Stake-only rewards:** stake provides security exposure but does not prove
  useful validator or resource-node work. Stake remains an activation input;
  accepted contribution units drive this research entitlement.
- **Equal reward for every registered participant:** inactive identities would
  dilute rewards and there would be no contribution signal.
- **Direct automatic payout:** population-wide epoch payout couples work to
  participant count and bypasses the existing typed claim liability.
- **Largest-remainder redistribution:** it exhausts the research budget but
  introduces rank and tie-break behavior. Independent floor shares plus an
  explicit retained remainder are simpler and order-independent.
- **Automatic recovery after a jail deadline:** a deadline alone does not show
  that an owner remediated the fault or that the lifecycle authority accepted
  recovery.
- **Delete identities on exit or removal:** deletion permits ambiguous reuse
  and loses lifecycle evidence. Stable tombstones preserve replay safety.
- **One failure state:** recoverable downtime and terminal safety faults have
  materially different authority and risk consequences.

## Consequences

- Validator and node identities have one deterministic research lifecycle.
- Contribution trust and caps are visible instead of hidden behind reward
  allocation.
- Reward weighting can be varied without changing the accounting model.
- Settlement and claim funding are independently observable and failure
  atomic.
- Retained integer remainder keeps the reward pool fully accounted.
- Stable tombstones and global proof identifiers increase retained research
  state; a future consensus design needs explicit pruning or bounded-history
  rules.
- Production cryptographic envelopes, verifier diversity, delegation,
  validator-set updates, parameter selection, C++ transitions, encoding,
  migration, and independent economic/security review remain required.

[ethereum-registry]: https://ethereum.github.io/consensus-specs/specs/phase0/beacon-chain/#registry-updates
[ethereum-exit]: https://ethereum.github.io/consensus-specs/specs/phase0/beacon-chain/#initiate-validator-exit
[cosmos-staking]: https://docs.cosmos.network/sdk/v0.50/build/modules/staking/README
[cosmos-slashing]: https://docs.cosmos.network/sdk/v0.50/build/modules/slashing/README
[polkadot-offboarding]: https://docs.polkadot.com/node-infrastructure/run-a-validator/onboarding-and-offboarding/stop-validating/
[polkadot-rewards]: https://docs.polkadot.com/node-infrastructure/run-a-validator/staking-mechanics/rewards/
[filecoin-mining]: https://spec.filecoin.io/systems/filecoin_mining/storage_mining/
[rats]: https://www.rfc-editor.org/rfc/rfc9334.html
