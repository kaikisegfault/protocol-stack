# ADR 0003: AI authority outside consensus

- Status: Proposed safety design; product direction fixed by ADR 0016
- Date: 2026-07-23
- Revised: 2026-08-03

## Context

The Founder Constitution assigns biometric verification, project and milestone
review, bounded treasury management, developer programs, and moderation to one
logical company-hosted Ecosystem AI. Model inference is probabilistic,
hardware-dependent, mutable, and too expensive to reproduce inside every
deterministic node transition.

Putting inference in consensus would make model, hardware, timing, and serving
differences capable of splitting the chain. Giving one model process an
unrestricted omnibus key would instead make compromise of any AI workflow a
compromise of all funds and authority.

## Proposed decision

Run all AI inference and training outside consensus and outside Founder Nodes.
The company operates the logical AI authority on self-hosted inference
infrastructure. Redundant replicas or specialized models are implementation
details, not community or Founder voting authorities.

AI workflows submit versioned, signed decision envelopes. Native C++ modules
deterministically enforce capability, source escrow, amount, budget, policy,
model manifest, evidence commitment, expiry, timelock, and replay limits.

Give biometric, moderation, venture, grant, developer, and later roles distinct
capabilities. No ordinary AI capability may mint, change supply, alter Founder
Seat economics, rewrite history, change its own policy, or upgrade the
protocol.

The company controls models and policies initially and delegates authority one
scope at a time. Once a scope is delegated as AI-only, a human or community
vote cannot substitute a case-specific decision. AI unavailability pauses that
scope while deterministic chain operation and custody continue.

## Consequences

- Model technology can change without a consensus migration.
- Founder Node hardware does not need local inference capacity.
- One coherent AI authority can serve the ecosystem without receiving one
  unrestricted key.
- Protocol limits can reject a compromised model's out-of-scope request, but
  cannot guarantee that an in-scope judgment is wise.
- AI downtime pauses managed decisions, making serving redundancy and recovery
  important external systems.
- Company policy control is a material establishment-period trust boundary.

## Acceptance gate

Accept production AI authority only after the canonical decision-envelope
specification, each owner-approved AI role framework, threat models, staged
evaluations, key and model recovery rules, deterministic protocol tests, and
independent reviews are complete. This proposed ADR changes no current
consensus behavior.
