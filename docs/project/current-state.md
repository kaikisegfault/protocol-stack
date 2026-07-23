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

F0 is complete on `chore/initial-general`; PR #3 is clean and mergeable.

On 2026-07-23 the owner granted standing authority for autonomous project
decisions and repository operations. A `proceed` instruction requires no
follow-up approval.

Verified foundation evidence:

- all three repository skills pass the official skill validator;
- `.codex/config.toml` parses and selects `gpt-5.6-sol` with high reasoning;
- GitHub issue-form YAML parses;
- all internal Markdown links resolve;
- `git diff --check` passes;
- Git author and committer match the repository owner identity;
- project, architecture, agent, and GitHub-governance chunks were committed and
  pushed separately;
- GitHub issue #1 tracks F0 and issue #2 tracks the first M1 decision package;
- F0 and M1 GitHub milestones and the referenced labels exist.

## Exact next action

Merge PR #3 under the standing delegation, then begin GitHub issue #2:

> Draft the protocol-primitives specification and a decision package comparing
> candidate signature, hashing, address, and canonical encoding suites. Record
> and accept the selected suite in an ADR before consensus-critical
> implementation.

## Open autonomous decisions

- Signature and key scheme.
- Hash function and state-tree construction.
- Address format and canonical binary encoding.
- Native unit name, precision, maximum supply, genesis allocation, and issuance
  schedule.
- Final acceptance of CometBFT as the replaceable M1 consensus/P2P adapter.

## Blockers

None. Protocol-primitives selection remains a mandatory research, ADR, and
verification gate before consensus-critical M1 implementation.
