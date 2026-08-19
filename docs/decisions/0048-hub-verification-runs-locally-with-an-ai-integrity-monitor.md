# ADR 0048: HUB verification runs locally, with the AI as its integrity monitor

- Status: Accepted
- Date: 2026-08-19

## Context

[ADR 0039](0039-hub-verification-is-mandatory-for-everyone.md) made HUB
verification mandatory for everyone. What it did not settle is **who performs
it**. Until now the constitution answered "an ecosystem-owned camera-verification
system and the company-hosted Ecosystem AI", and version six's genesis carries a
single `verifier_key`: one key, held by the company, whose signature is required
on **every registration in the ecosystem**.

That is the single most centralized point in the whole design, and it is larger
than the AI question [ADR 0047](0047-the-founder-machine-runs-the-ecosystem-ai.md)
answers. Mandatory verification plus one signing key is a global admission
chokepoint and a switch that can stop anyone from ever joining.

Two further facts constrain any replacement:

- **The chain has never checked uniqueness.** `economy-transition-v6` states
  plainly that it does not check that a HUB uniqueness hash reaches at most one
  account, so verification is exactly as strong as whatever performs it. The
  32-byte commitment the chain stores catches no duplicate, because two captures
  of one face never produce the same bytes and so never produce the same hash.
- **Raw biometric data must not spread.** The constitution already forbids raw
  images, video, and linkage data from becoming ordinary blockchain data, and
  already records that saying so does not establish that face verification is
  secure.

## Decision

### 1. Verification is a local, offline, sandboxed process on the founder's own machine

The whole process runs **between the Founder Machine and the founder**, in a
fully sandboxed offline environment, on the founder's **own** machine. No remote
verifier, no company service, and no network participant is in the loop.

The verdict itself is **deterministic software**. Sensitive material stays in the
machine's multisignature vaults and never leaves the sandbox.

**Rejected: verification on a machine other than the subject's own**, assigned by
the same beacon that assigns AI judgment. It was proposed here because a founder
verifying themselves on their own machine holds every input to their own
verification — the worst threat model available. The owner rejected it: the
enclosed local process is the architecture, and its integrity is secured by the
monitor below and by machine attestation rather than by moving the work to a
stranger's hardware. Recorded because the residual risk it addresses is real and
named under Consequences.

### 2. The AI is the integrity monitor, not the verifier

The local model **never decides whether a person is who they claim to be.** That
is the deterministic verifier's verdict.

What the model does is **watch the process**: whether verification was initiated
fairly, whether the inputs supplied to it were genuine and unmanipulated, and
whether anything about the run looks interfered with. It holds encrypted tooling
for that evaluation, and it holds **dispute authority** — it can reject a run,
force re-initialization, and require the process to start again with fair inputs.

This is the right division of labour, and it is the general shape worth reusing:
**a deterministic verdict, supervised by a non-deterministic monitor.** "Is this
the enrolled person" is a measurement and belongs to software that gives the same
answer twice. "Did this process run honestly" is a judgment, has no closed form,
and is exactly what a model is good at.

### 3. The single verifier key becomes a registry of per-machine attestation keys

Genesis's one `verifier_key` is replaced by a **registry of attestation keys, one
per Founder Machine**. A registration is valid when it is signed by a machine
that is in the active seat set and running an attested build.

**The chokepoint does not vanish; it moves and multiplies.** Whoever signs the
software build is the root of trust, and during initialization that is the
company. This ADR does not claim otherwise. What it buys is that no single key
can refuse an individual registration, that the trust is in a published build
rather than in an operator's discretion, and that renouncing the build-signing
authority is a single, legible act — which is what
[ADR 0047](0047-the-founder-machine-runs-the-ecosystem-ai.md)'s end of
initialization transfers.

### 4. Uniqueness is a replicated commitment, and its stabilization is an open dependency

Every HUB identity's uniqueness commitment is **replicated to every Founder
Machine**. At a million identities that is about 32 MB; a machine holds the whole
set and compares locally, so uniqueness is checked without any lookup service.

For that comparison to find anything, a capture must produce the **same**
commitment every time. That requires a noisy-to-stable step — a fuzzy extractor
or secure sketch, storing per-identity helper data and deriving one stable key
from any capture of that person. With it, uniqueness is an equality over 32-byte
values, replication is cheap, and no raw template ever leaves the sandbox.

**That scheme is named as an open dependency requiring independent cryptographic
review, and nothing is built on it until that review exists.** The constitution
forbids implementing cryptographic primitives from scratch, and this is the kind
of primitive that fails quietly.

**Rejected: replicate raw biometric templates and match fuzzily.** It is what most
systems do and it would work. It also puts every participant's biometric template
on every Founder Machine — a hundred thousand machines owned by strangers, where
one breach leaks the whole population — and it contradicts the constitution's
existing rule on raw biometric data directly.

## Consequences

**A recorded scaling constraint.** The 99.99% figures the industry reports are
for 1:1 matching — "is this the person who enrolled?" — which is mature. Checking
one capture against a whole population is the same technique applied N times, so
false accepts accumulate with N. At the ecosystem's realistic near-term scale of
100,000 to 1,000,000 identities this is manageable; it is recorded because it
worsens with growth rather than improving, and the parameters must be chosen
against a target population rather than against a demo.

**The residual risk of self-verification is stated, not solved.** Both the
deterministic verifier and its monitor run on the founder's own machine, so a
founder who defeats the machine's attestation defeats both. The monitor raises
the cost from trivial to requiring a compromised attested build. **This is the
strongest argument for the physical machine phase**: attestation on hardware the
ecosystem produces is materially harder to defeat than attestation on software a
founder installed, and the software-only phase is the weaker of the two.

**Genesis changes shape and version six does not carry it.** Replacing a single
`verifier_key` field with a registry is a genesis and state-layout change, so it
belongs to a later contract version. `economy-transition-v6` keeps its single
key, and the kernel that implements it is unaffected by this ADR.

**The constitution's biometric paragraph is edited, not weakened.** Its
requirement for a separate threat model, independent review, unlinkability,
retention, coercion limits, and false-acceptance targets stands. Only the actor
changes: the company-hosted Ecosystem AI becomes the local model on the founder's
own machine.
