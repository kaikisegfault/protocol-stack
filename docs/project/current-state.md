# Current state

Last updated: 2026-07-23

## Phase

F0 — Agent and project foundation.

## Verified facts

- Repository: `kaikisegfault/protocol-stack`.
- Working branch: `chore/initial-general`.
- Git author and committer identity is configured as Giorgi Chomakhashvili
  using the GitHub noreply address documented in `AGENTS.md`.
- The repository contains no blockchain implementation.
- The active product milestone is M1 — Sovereign Devnet Alpha.
- Root economics will be native C++ protocol modules.
- Future venture acceptance, milestone review, and escrow funding decisions are
  assigned to bounded AI authority rather than community or node-owner voting.
- JavaScript, TypeScript, Node.js, React, public contracts, and EVM are excluded
  from M1.

## Foundation status

Repository instructions, project documents, architecture records, engineering
standards, and repository skills have been drafted. They must be validated,
committed, and pushed before F0 is complete.

## Exact next action

Validate every repository skill, inspect all foundation files for contradictions
and stale links, verify the Codex project configuration and Git identity, then
commit and push F0 on `chore/initial-general`.

After F0 is committed, the next unblocked M1 slice is:

> Draft the protocol-primitives specification and a decision package comparing
> candidate signature, hashing, address, and canonical encoding suites. Do not
> implement consensus-critical encoding or cryptography until the owner accepts
> that decision.

## Open owner decisions

- Signature and key scheme.
- Hash function and state-tree construction.
- Address format and canonical binary encoding.
- Native unit name, precision, maximum supply, genesis allocation, and issuance
  schedule.
- Final acceptance of CometBFT as the replaceable M1 consensus/P2P adapter.

## Blockers

None for completing F0. The protocol-primitives selection is an owner gate
before consensus-critical M1 implementation.
