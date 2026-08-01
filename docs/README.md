# Documentation index

## Project

- `project/vision.md`: long-term direction and boundaries.
- `project/charter.md`: current architecture and governing principles.
- `project/first-goal.md`: first operational outcome and acceptance evidence.
- `project/roadmap.md`: ordered milestones.
- `project/current-state.md`: verified handoff between sessions.
- `project/native-economy-simulation-report-v1.md`: reproducible M2 seeded
  accounting study and its explicitly non-production interpretation.
- `project/participation-simulation-report-v1.md`: reproducible M2 validator
  and node lifecycle, entitlement, and claim-funding study.
- `project/authority-simulation-report-v1.md`: reproducible M2 threshold
  result, rotation, containment, recovery, and shared-adapter study.
- `project/economic-stress-report-v1.md`: reproducible M2 orthogonal
  cross-simulator parameter-family and reverse-stress study.
- `project/economic-envelope-report-v1.md`: exact M2 reward-funding and
  within-role concentration boundaries around the screened survivor families.

## Architecture

- `architecture/sovereign-core.md`: system layers and replaceable boundaries.
- `architecture/ledger-kernel.md`: ledger ownership, atomic block application,
  canonical outputs, and failure boundaries.
- `architecture/sqlite-ledger.md`: owning persistence boundary, durable
  height-zero creation, and validated reopen behavior.
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
- `specifications/consensus-application-v1.md`: adapter-neutral ordering
  lifecycle, application results, durable commit, restart, and local framing.
- `specifications/native-economy-simulation-v1.md`: versioned integer-only
  accounting, authority, event, trace, and metric contract for the independent
  M2 research simulator; it is not a consensus transition.
- `specifications/participation-simulation-v1.md`: validator and resource-node
  lifecycle, bounded verifier-result, entitlement, and native-claim funding
  contract for M2 research.
- `specifications/authority-simulation-v1.md`: capability-scoped
  distinct-member thresholds, action results, rotation, containment, recovery,
  and shared simulator adapters for M2 research.
- `specifications/economic-stress-study-v1.md`: deterministic three-level
  orthogonal parameter screening across the accepted M2 simulators.
- `specifications/economic-envelope-study-v1.md`: exact high-resolution
  reward-funding and within-role concentration boundaries around the screened
  M2 survivor families.

The corresponding executable research tools and reviewed fixtures live in
`../simulation/native_economy/`, `../simulation/participation/`,
`../simulation/authority/`, and `../simulation/economic_stress/`.
