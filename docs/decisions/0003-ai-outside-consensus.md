# ADR 0003: AI authority outside consensus

- Status: Proposed
- Date: 2026-07-23

## Context

The long-term vision delegates venture review and funding management to local
AI deployed on node-owned infrastructure. Model inference is probabilistic,
hardware dependent, expensive, and unsuitable for deterministic replicated
execution. A single unrestricted model key would also be a catastrophic
authority boundary.

## Decision

Run AI inference and training outside consensus. AI systems submit versioned,
signed decision envelopes. Native C++ modules deterministically enforce
capabilities, budgets, venture escrow conservation, milestone and tranche
limits, thresholds, timelocks, expiry, and replay protection.

Community members and node operators do not vote on venture approval,
milestones, or funding. Large models run on high-bandwidth compute clusters.
General nodes perform loosely coupled storage, batch, evaluation, and
verification work. High-value decisions eventually require threshold
attestations from independent AI authorities.

## Consequences

- Model technology can evolve without changing consensus.
- The protocol can remain operational when AI infrastructure is unavailable.
- AI cannot exceed deterministic economic limits if a model is compromised.
- The resource network and model-governance system become substantial
  independent subsystems.

## Acceptance

Accept the authority, threshold, and recovery model under the standing
delegation only after its specification, threat model, simulations, and
independent review requirements are recorded. Acceptance is required before an
AI authority module is implemented.
