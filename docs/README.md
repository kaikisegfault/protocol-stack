# Documentation index

## Project

- `project/vision.md`: long-term direction and boundaries.
- `project/charter.md`: current architecture and governing principles.
- `project/first-goal.md`: first operational outcome and acceptance evidence.
- `project/roadmap.md`: ordered milestones.
- `project/current-state.md`: verified handoff between sessions.

## Architecture

- `architecture/sovereign-core.md`: system layers and replaceable boundaries.
- `architecture/local-ai-authority.md`: future self-hosted AI control plane.

## Decisions

Architecture decision records live in `decisions/`. Proposed records are not
irreversible commitments. Accepted records govern implementation until
superseded.

## Engineering

- `engineering/continuation.md`: the cross-session `proceed` protocol.
- `engineering/standards.md`: language, modularity, determinism, and dependency
  standards.
- `engineering/build-toolchain.md`: reproducible build, test, dependency, and
  cache commands.
- `engineering/verification.md`: required evidence and quality gates.
- `engineering/git-workflow.md`: issues, branches, atomic commits, PRs, and
  authorship.

## Specifications

Canonical protocol specifications live in `specifications/` and must define
consensus-critical behavior before implementation. An accepted version is
immutable; compatible changes require a new version.

- `specifications/protocol-primitives-v1.md`: canonical version-one encoding,
  cryptography, identifiers, addresses, transactions, and commitments.
- `specifications/ledger-transition-v1.md`: M1 genesis, native transfer, fee,
  receipt, and ordered block semantics.
