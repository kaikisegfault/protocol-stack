# ADR 0010: Capability-scoped threshold authority results

- Status: Accepted for M2 research
- Date: 2026-07-31

## Context

ADRs 0008 and 0009 expose every privileged native-economy and participation
operation through an explicit capability, but their research manifests assign
each capability to one principal. That makes accounting and lifecycle trust
visible without yet answering how multiple independent authorities approve one
exact action, how authority sets rotate, or how compromised and unavailable
members are contained.

M2 needs an independently executable authorization boundary before economic
parameter sweeps or C++ transitions can treat a verifier result as permission.
The boundary must distinguish external evidence and signature verification
from deterministic authorization, bind an approval to one exact domain and
action, count distinct members, prevent result and action replay, and model
rotation, revocation, recovery, and emergency pause without selecting a
production signature scheme, principal, or quorum.

Primary-source review informed the decision:

- The Update Framework assigns different roles to different key sets, counts
  each key only once toward a threshold, versions trust roots consecutively,
  and requires a replacement root to satisfy both the previous and new
  thresholds. Its update and wall-clock expiry machinery is not adopted, but
  distinct-member counting and dual-threshold trust continuity are useful.
  Source: [TUF specification][tuf].
- EIP-712 separates otherwise identical structured messages by application,
  version, chain, and verifier domain, while explicitly leaving replay
  protection to the application. The project does not adopt its Ethereum ABI,
  Keccak hash, contract address, or signing RPC, but it adopts the principle
  that semantic context belongs inside the signed digest.
  Source: [EIP-712][eip-712].
- RFC 9591 specifies FROST as a threshold signature whose participant
  identifiers are distinct and whose participant selection and key
  distribution are external to the signing protocol. FROST is a credible
  future implementation option, but adopting its group, distributed key
  generation, nonce lifecycle, or aggregate signature now would prematurely
  make a cryptographic decision.
  Source: [RFC 9591][frost].
- RFC 9334 separates evidence appraisal by a Verifier from application
  authorization by a Relying Party. The selected research model consumes
  opaque, externally verified member results and then applies its own
  capability, threshold, epoch, replay, and containment policy.
  Source: [RFC 9334][rats].
- Cosmos SDK ADR 030 scopes grants to individual message methods and permits
  bounded authorization implementations rather than granting one implicit
  omnibus privilege. The project adopts capability scoping, not the SDK
  account, protobuf, or routing model.
  Source: [Cosmos SDK ADR 030][cosmos-authz].
- NIST SP 800-57 treats cryptoperiods, compromise, revocation, replacement,
  split knowledge, trust anchors, and recovery as explicit key-management
  concerns. This supports modeling lifecycle separately from an operational
  approval result rather than treating a key identifier as permanent.
  Source: [NIST SP 800-57 Part 1 Rev. 5][nist-800-57].

These sources are comparative evidence, not protocol dependencies. The model
and implementation are original standard-library-only Python research tools.

## Decision

### Separate research model

Add an authority simulation v1 contract instead of modifying either accepted
simulator v1. It owns no native value, participant lifecycle, raw evidence,
private key, public key, signature, or model output. It records versioned
capability bindings, externally verified member results, authorization
results, scheduled rotations, pauses, revocations, recoveries, and replay
identities.

Native-economy and participation remain the only models that execute their
respective state changes. A deterministic adapter releases an already accepted
authority result only when it binds the exact target event and the target
manifest independently agrees with its module, capability, and actor.

### Distinct externally verified member results

Version one counts one approval per distinct member identifier in the active
authority set. Each approval carries a globally unique proof identifier and an
opaque 32-byte evidence digest. Replay never parses a signature, certificate,
attestation format, raw evidence, or model output.

An approval means that an external verifier already authenticated that member
and its affirmative result over the declared action digest. The simulator then
checks membership, uniqueness, threshold, capability, set version, validity
window, and replay state. Fewer than threshold compromised or colluding
members cannot authorize an action in the model. A threshold of compromised or
colluding members can; the simulator makes that trust limit explicit rather
than claiming Byzantine safety beyond the configured threshold.

No production member count, threshold, identity, key type, signature format,
aggregation scheme, verifier, or diversity rule is selected.

### Exact action domain and replay identities

Every operational result binds:

- the authority-result schema version;
- chain identifier;
- target module and capability;
- authority-set identifier and consecutive version;
- independent result and action identifiers;
- valid-from and deadline epochs; and
- the exact target simulator event.

The adapter computes a domain-separated SHA-256 action digest over canonical
JSON for this research contract and requires exact equality with the accepted
result. Event, result, action, and member-proof identifiers have separate
global replay sets and are consumed only on success.

This research digest is not a production signature encoding or protocol
commitment. A later consensus design must select canonical binary bytes and a
reviewed cryptographic verifier independently.

### Capability containment

Authority sets are bound to one module and capability. An approval for one
chain, module, capability, set identifier, set version, epoch window, action,
or action identity cannot authorize another.

The shared adapters cover only the already privileged event classes in the
native-economy and participation v1 contracts. Account-owner and
participant-owner events continue to use their existing ownership rules and
cannot be elevated through an authority result.

### Rotation

An ordinary rotation creates exactly the next version for one capability. It
must:

- be authorized by the threshold of the currently active set;
- be affirmed by the threshold of the proposed next set over the same exact
  rotation digest;
- satisfy configured minimum and maximum height-derived activation delays;
- fit the configured member and retained-version bounds; and
- activate through an explicit clock event at or after its scheduled epoch.

Only one rotation may be pending for a capability. Until explicit activation,
the old set remains active. Activation retires the old version, activates the
new version, and retains both for audit. A pause or revocation clears any
pending rotation so a pre-containment schedule cannot activate later.

The dual threshold follows TUF trust continuity and also tests whether the
proposed members are available. It does not prove that either set is
uncompromised.

### Revocation, containment, and recovery

Version one has two immutable, research-manifest control sets:

- containment may pause a target capability or revoke one active member; and
- recovery may replace a paused capability after a height-derived delay.

Containment and recovery actions are themselves distinct-member threshold
actions with exact digests and replay identities. Revoking an active member
immediately pauses the entire target capability instead of silently lowering
its threshold. Paused capabilities fail closed for operational results and
ordinary rotation. Recovery requires both its control-set threshold and the
proposed replacement-set threshold, installs exactly the next version, clears
the pending rotation, and unpauses the capability.

Control sets cannot target or rotate themselves in simulator v1. Production
root-of-trust replacement, catastrophic compromise recovery, and
constitutional emergency authority require a later threat model and
independent review. This research boundary deliberately exposes that remaining
root instead of pretending to solve it recursively.

### Deterministic and bounded execution

The simulator uses checked unsigned 64-bit heights, epochs, versions, counters,
and limits. Epoch is derived only from height. Events execute in input order
against a complete copy. Shape-invalid input aborts replay; an ordinary failure
changes no state and consumes no identifier.

Manifest limits bound capabilities, members per set, approvals per threshold
operation, retained versions per capability, rotation delay, recovery delay,
and action lifetime. Event-list length remains caller-bounded. Replay invokes
no C++, node, network service, filesystem ordering, wall clock, Python
randomness, external verifier, or inference process.

The normative contract is
`../specifications/authority-simulation-v1.md`. It changes no consensus
behavior.

## Threat assumptions and limits

- A collector, coordinator, or event submitter is untrusted; it cannot make
  duplicate or unauthorized members count.
- Opaque verifier results are assumed authentic. Forged verifier results are
  outside the simulator and must be prevented by a future cryptographic
  implementation.
- Fewer than threshold compromised members cause denial attempts or partial
  approvals, not authorization.
- Threshold collusion authorizes the bounded capability. Containment reduces
  exposure only while its independent threshold remains available and honest.
- Offline members can block ordinary action, rotation, or recovery. The model
  records this availability cost and does not weaken a threshold.
- A compromised containment or recovery threshold can pause or replace the
  capabilities in its scope. Production separation, delays, budgets, and
  independent root recovery remain unresolved.
- Height-derived deadlines prevent stale use during replay but do not provide
  wall-clock freshness.

## Alternatives not selected

- **One multisignature principal per capability:** this hides which member and
  set version contributed, makes rotation and offline behavior opaque, and
  promotes a cryptographic container before the authorization contract is
  stable.
- **FROST aggregate signatures now:** FROST can reduce on-chain signature size,
  but key generation, participant coordination, nonce safety, ciphersuite, and
  recovery are consequential cryptographic decisions. The selected result
  model can later be backed by FROST or independent signatures.
- **Weighted thresholds:** unequal member power adds policy and arithmetic
  choices without evidence that they improve the first authority boundary.
  Version one counts distinct members equally.
- **Current-set-only rotation:** a current threshold could install an
  unavailable next set without evidence that the replacement can affirm the
  transition. Dual approval makes that failure visible before activation.
- **Automatic rotation at an epoch boundary:** hidden state changes complicate
  replay and recovery. Explicit activation keeps work bounded and auditable.
- **Continue after one member is revoked:** dynamically reducing the member
  set or threshold risks authorizing with a policy no result actually named.
  Fail-closed pause followed by versioned recovery is explicit.
- **Automatic unpause after a deadline:** passage of height does not prove that
  compromise has been remediated.
- **One global authority set:** compromise would cross module and capability
  boundaries. Explicit bindings contain ordinary authority.

## Consequences

- Both accepted research simulators can share one exact threshold-result
  boundary without changing their v1 schemas or digests.
- Distinct member, replay, domain, rotation, pause, and recovery behavior is
  independently testable before cryptographic implementation.
- Dual-set rotation and replacement increase availability requirements.
- Retained identifiers, results, and set versions grow with replay; a future
  consensus design needs exact history pruning and state-size rules.
- Immutable research control sets leave catastrophic control-root recovery
  unresolved by design.
- A future C++ implementation still requires a consensus specification,
  canonical binary encoding, reviewed signature scheme and library, state-root
  integration, transaction and block limits, activation and migration,
  adversarial security review, and production authority policy.

[tuf]: https://theupdateframework.github.io/specification/latest/
[eip-712]: https://eips.ethereum.org/EIPS/eip-712
[frost]: https://www.rfc-editor.org/rfc/rfc9591.html
[rats]: https://www.rfc-editor.org/rfc/rfc9334.html
[cosmos-authz]: https://docs.cosmos.network/sdk/latest/reference/architecture/adr-030-authz-module
[nist-800-57]: https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final
