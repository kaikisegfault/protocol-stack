# ADR 0018: Founder Economy simulator transition and encoding shape

- Status: Accepted for M2 simulation; not a consensus activation
- Date: 2026-08-03

## Context

ADR 0017 accepted the eight-decimal denomination, the ten fixed issuance
channels, and the permission-liability model, and
`founder-economy-manifest-v1.md` fixed the manifest bytes and abstract
accounting state. Both deliberately stopped before defining an executable
transition set.

`first-goal.md` requires an independent standard-library Python implementation
with frozen fixtures and digests that proves the maximum supply and every
economic route before C++ behavior changes. Three concrete gaps blocked that:

1. `founder-economy-manifest-v1.txt` is normative but no test executes it, so
   its values are reviewed rather than reproduced.
2. The manifest specification names abstract state and failure codes but no
   canonical event encoding, journal shape, or digest set, so two independent
   implementations could disagree while both claiming conformance.
3. The four research placeholders have no bound representation, so a
   simulator could accept an unbound fixture and silently invent policy.

The repository already contains five accepted research simulators. Their
schemas model generic staking, penalty, and treasury shapes that the Founder
Constitution does not adopt, so extending one would import rejected mechanisms
into founder-directed accounting.

## Decision

### A separate simulator package

Implement `simulation/founder_economy/` as a new package rather than extending
`simulation/native_economy/` or `simulation/participation/`. The existing
packages keep their accepted schemas and results unchanged. The new package
consumes the fixed manifest directly and models only constitutional
mechanisms.

### Manifest as a fixed contract, not a template

The loader compares every identifier, order, kind, amount, beneficiary kind,
and placeholder against the accepted contract, then independently rederives
every product and subtotal from the leg amounts, the 100,000-seat capacity, and
the 731-cycle schedule. A manifest that parses but derives a different total is
rejected as `SUPPLY_MISMATCH` rather than being simulated.

`RANGE` is ordered before `MANIFEST_MISMATCH` so an unrepresentable value is
reported as a range failure rather than as a content difference.

### Explicit null research inputs

Every transition that consumes a research placeholder carries that field
always, with the JSON value `null` modelling absence. Absence produces
`MISSING_RESEARCH_INPUT` and a present result whose binding fields differ from
the attempted action produces `INVALID_RESEARCH_INPUT`.

Binding is total: the activity and referral results bind seat and cycle, the
performance allocation binds the inactive source seat and cycle, and the direct
eligibility result binds channel, decision identifier, beneficiary, and amount.
An unbound or partially bound fixture cannot authorize a different action.

### Beneficiary resolution at creation

The `founder_operator` and `founder_referral` beneficiaries resolve to concrete
custody keys when the permission is created, not when it is exercised. This is
what makes an inactive cycle's reallocation permanent, as the constitution
requires: the original seat cannot recover the 342-unit benefit by exercising
later.

### A four-bucket journal with two balance rules

Journals use `capacity:`, `outstanding:`, `issued:`, and `custody:` buckets and
must satisfy both:

```text
sum(capacity) + sum(outstanding) + sum(issued) = 0
sum(custody) = sum(issued)
```

Creation moves value from capacity to outstanding, exercise moves it from
outstanding to issued and mirrors it into custody, and direct issuance moves it
from capacity to issued and mirrors it into custody. Every accepted transition
is machine-checked against both rules and against the full state invariants.

### Digest set

Manifest, events, state, trace, and result digests all use RFC 8785 canonical
bytes under the accepted `D(label)` domain separation. Every monetary value in
a digest preimage is a canonical decimal string; only small exact counts appear
as JSON numbers.

Because counts remain JSON numbers, seat identifiers and cycle indexes are
bounded at parse time by 9,007,199,254,740,991 rather than by `u64`. A larger
count could not be canonicalized, so it is refused as an input-shape error
before it can reach a digest preimage; semantic bounds inside that range remain
ordinary modelled rejections. The canonical state value that the state digest
covers is specified exactly, so an independent implementation can reproduce the
digest from the document rather than from this code.

### An executed vector verifier

`tools/founder-economy-vectors/verify.py` derives every value in the normative
vector file from the loaded manifest and the running simulator and compares the
derivation to the recorded value. It is registered as a CTest test so the
vectors fail closed.

## Alternatives not selected

- **Extend an existing research simulator:** would reuse schemas containing
  staking, slashing, and penalty pools that the constitution rejects, and would
  either break their accepted result digests or force founder accounting into
  a shape that does not match the manifest.
- **Omit a separate simulator specification and let the code define behavior:**
  the manifest specification explicitly defers the event, trace, and
  final-state digest contract to this slice. Leaving it implicit would make an
  independent M3 C++ implementation unverifiable against the Python model.
- **Optional research-input fields:** a missing key and a supplied `null` would
  become indistinguishable from a schema error, and a strict loader would have
  to choose between rejecting the run and inventing an absent-input default.
  An always-present nullable field keeps `MISSING_RESEARCH_INPUT` a modelled,
  traceable rejection.
- **Unbound research fixtures:** a bare boolean would let one fixture authorize
  any seat, cycle, channel, or amount. Total binding is what keeps a research
  stand-in from silently becoming policy.
- **Resolve the Founder beneficiary at exercise:** an inactive seat could
  exercise later and reclaim the reallocated 342 units, contradicting the
  constitutional rule that the benefit cannot be recovered.
- **Single-sum journal balance:** one net-zero rule cannot express both the
  capacity-to-issued movement and its custody mirror without double counting.
  Two explicit dimensions make conservation auditable.
- **Monetary values as JSON numbers in digest preimages:** amounts above the
  interoperable exact-integer range could be rounded by a conforming JSON stack
  before hashing, so an independent implementation could compute a different
  digest from semantically identical input.
- **Model seat pricing, enrollment, commercial routing, and fee routing now:**
  each is required by `first-goal.md` but none depends on this slice's
  accounting core, and bundling them would produce one unreviewable change.
  They follow as separate bounded slices against this contract.
- **Verify the vector file by review:** the previous slice did this, which is
  why an unexecuted normative artifact existed. An executed derivation is the
  only evidence that survives a future edit.

## Consequences

- The fixed maximum, every channel cap, every per-cycle leg, every per-seat
  731-cycle product, and every full-schedule product become executed
  derivations rather than reviewed prose.
- Permission liabilities, atomic exercise, replay keys, and cap exhaustion are
  testable, and rejection paths are proved to write no state by digest
  comparison rather than by inspection.
- Two research placeholders that the constitution reserves — inactive referral
  treatment and direct-channel eligibility — remain supplied per action and
  recorded in the trace, so the model reports the owner decision still required
  instead of encoding one.
- The simulator models the seat graph only. Seat pricing, the 1,000-seat
  per-person bound, enrollment, biometric identity, managers, commercial
  routing, fee routing, and escrow payout remain unmodelled and are named
  explicitly as remaining `first-goal.md` requirements.
- Recipient checks for an inactive cycle prove activation, uniqueness, and
  exclusion of the source seat, but cannot prove same-cycle liveness without
  the unresolved performance policy. That gap is recorded rather than filled.
- No M1 account, transaction byte, state root, database, ABCI response,
  validator, or previously accepted simulator schema changes.

## Compatibility and independent review

This ADR accepts a research model contract. It does not activate a consensus
transition, and its error codes are simulator result codes rather than
consensus receipts. M3 must separately define canonical transaction bytes,
receipts, commitments, a bounded settlement mechanism, and cross-language
vectors, and must resolve the activation-or-new-genesis boundary recorded in
ADR 0017 before a C++ transition exists.

Exact accounting is not economic safety. The activity proof, grace allowance,
performance metric, winner count, tie handling, inactive referral treatment,
and direct-channel eligibility remain founder-reserved or unresolved, and
independent economic and protocol review remains required before any
production activation claim.
