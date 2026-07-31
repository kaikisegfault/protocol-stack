# Authority simulation report v1

Status: reproducible M2 research evidence; not production authority policy

## Question

Can one deterministic, capability-scoped result boundary reject incomplete,
duplicated, stale, cross-domain, and contained approvals while supporting
auditable authority-set rotation and recovery for both accepted M2 simulators?

This study tests the mechanics selected by ADR 0010. It does not estimate
real-world member independence, verifier correctness, key-compromise
probability, operational latency, or a safe production quorum.

## Method

The standard-library-only `simulation/authority` package generated and
replayed 24 `SplitMix64-v1` scenarios with seeds `0..23`. Each seed fixes
one 69-event input containing:

- one-member and exact-threshold operational results;
- duplicated and unauthorized members;
- event, result, action, and proof replay attempts;
- wrong-chain and wrong-set domains;
- future and expired epoch windows;
- an old-set-only rotation attempt representing offline proposed members;
- successful old-and-new-set rotation approval and explicit activation;
- a pending rotation canceled by emergency containment;
- fail-closed authorization while paused;
- one active-member revocation without threshold reduction;
- too-early and successful recovery requiring both recovery and replacement
  thresholds; and
- exact native-economy issuance and participation registration target events.

The generator varies the issued research amount and all opaque scenario
evidence digests from the explicit seed. Replay itself reads no random source,
clock, network, node, C++, signature verifier, raw evidence, or model output.

The reviewed seed-zero fixture is:

- `simulation/authority/fixtures/research-manifest-v1.json`;
- `simulation/authority/fixtures/research-events-v1.json`; and
- trace digest
  `26f96d2fccdcb7b9acdcad0b83f81a564aa99196eb4042285ddcf38dba6588a1`.

Run the full study with:

```sh
python3 simulation/authority/study.py --seed-start 0 --seed-count 24
```

## Reproduced results

Across 24 seeds:

- 1,656 events replayed;
- 1,200 events accepted and 456 adversarial events rejected;
- 624 unique member-proof identifiers accepted;
- 72 operational authority results retained;
- all 24 traces were distinct and deterministic;
- every run explicitly activated one dual-threshold ordinary rotation;
- every run completed two delayed dual-threshold recoveries;
- every final state retained seven consecutive authority-set versions across
  four capability bindings and ended with no paused capability; and
- all 48 adapted downstream events were accepted by their independent target
  simulator: one native-economy issuance and one participation registration
  per seed.

Every run observed the same result family:

```text
ACTION_REPLAY
DIGEST_MISMATCH
DOMAIN_MISMATCH
DUPLICATE_MEMBER
EXPIRED
NOT_FOUND
OK
PAUSED
PROOF_REPLAY
REPLAY
RESULT_REPLAY
THRESHOLD
TOO_EARLY
UNAUTHORIZED_MEMBER
WRONG_SET
```

The canonical study digest is:

```text
74e0913b379151a3fd72529837b0dcb31002dbe33251ad5e3ae4bb2fc1739ea4
```

Tests additionally mutate strict manifest and event schemas, numeric types,
member ordering, action bytes, actor bindings, complete result traces, set
families, capability scopes, member and retained-version limits, `u64`
height, and downstream owner-authorized events. Every ordinary failure retains
an identical complete state digest and consumes no replay identifier.

## Interpretation

The study supports these structural conclusions:

- distinct members and independent replay identities are sufficient for a
  deterministic simulator to expose threshold assumptions without choosing a
  signature aggregation scheme;
- binding chain, module, capability, set family, version, epoch window, result
  identity, action identity, and exact target event prevents the tested
  cross-domain substitutions;
- dual old/new approval detects an unavailable replacement before activation;
- revocation is safer to model as fail-closed containment than as an implicit
  threshold reduction; and
- recovery can remain auditable by replacing one consecutive version only
  after a delay and two explicit thresholds.

The study also makes the trust limit visible: an exact configured threshold of
colluding or compromised members authorizes the capability. A collector cannot
make a duplicated member count twice, but the simulator cannot determine
whether externally verified principals are genuinely independent.

## Non-production boundary

No fixture principal, threshold, delay, capability assignment, digest,
evidence result, actor, or research amount is a production recommendation.
The model verifies no signature and contains immutable research control roots.

Before any C++ authority transition, the project still requires canonical
binary encoding, a reviewed cryptographic and key-management scheme,
production principal and quorum evidence, verifier authentication, root
recovery, state-size and pruning rules, state-root integration, activation and
migration, decoder fuzzing, and independent security and cryptographic review.
