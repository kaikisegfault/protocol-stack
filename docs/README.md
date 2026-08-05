# Documentation index

## Project

- `project/founder-constitution.md`: authoritative founder intent, fixed
  end-state requirements, decision ownership, and unresolved founder gates.
- `project/vision.md`: long-term direction and boundaries.
- `project/charter.md`: current architecture and governing principles.
- `project/first-goal.md`: current operational outcome and acceptance evidence.
- `project/goals/m1-sovereign-devnet-alpha.md`: retained acceptance contract
  for the completed first runnable devnet milestone.
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
- `project/reward-distribution-report-v1.md`: exact M2 payout-cap,
  credit-liveness, and same-principal identity-split evidence.
- `project/admission-cost-report-v1.md`: exact M2 cross-principal split,
  operating-cost, refundable-bond, lock, churn, and honest-entry boundaries.
- `project/minimum-entitlement-report-v1.md`: exact M2 strictly funded floor,
  smallest-honest-entry, and hidden-principal split boundaries.

## Architecture

- `architecture/sovereign-core.md`: system layers and replaceable boundaries.
- `architecture/ledger-kernel.md`: ledger ownership, atomic block application,
  canonical outputs, and failure boundaries.
- `architecture/sqlite-ledger.md`: owning persistence boundary, durable
  height-zero creation, and validated reopen behavior.
- `architecture/local-ai-authority.md`: future company-hosted logical AI
  authority, capability containment, and delegation stages.

## Decisions

Architecture decision records live in `decisions/`. Proposed records are not
irreversible commitments. Accepted records govern implementation until
superseded.

ADR 0016 adopts the Founder Constitution and staged realization order. It
changes project direction but does not activate production economics or alter
current consensus behavior.

ADR 0017 selects the eight-decimal `u64` Founder Economy denomination, fixed
manifest encoding, and outstanding-permission liability shape for M2. It does
not activate those values in the M1 devnet.

ADR 0018 selects the Founder Economy simulator's transition set, bound
research-input encoding, creation-time beneficiary resolution, journal
conservation rules, and digest labels. It accepts a research model contract,
not a consensus transition.

ADR 0019 selects the Founder Seat sale denomination, the exact tier boundary of
the constitutional price schedule, pure-handler failure atomicity, and the
separation of the seat sale model from the economy simulator. It accepts a
research model contract, not a consensus transition.

ADR 0020 selects the integer remainder rule for the commercial split, the
creator sub-split shape, overflow-free share arithmetic, per-cycle Founder
distribution with a carry, and separate fee accounting. It accepts a research
model contract, not a consensus transition.

ADR 0021 selects the separation of escrow payouts from the economy simulator,
the digest-bound opening custody, the two-bound revocable spending capability,
authority-before-funds rejection ordering, and the reconciliation of custody
against capability accounting. It accepts a research model contract, not a
consensus transition.

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
- `specifications/founder-economy-manifest-v1.md`: exact eight-decimal
  denomination, ten issuance-channel caps, 731-cycle derivation,
  permission-liability semantics, unresolved-policy placeholders, and fixed
  M2 manifest digest; it is not a consensus transition.
- `specifications/founder-economy-simulator-v1.md`: strict manifest loading,
  the five Founder Economy transitions, bound research inputs, journal
  conservation, digest labels, and vector obligations for the independent
  Python model; it is not a consensus transition.
- `specifications/founder-seat-schedule-v1.md`: integer USD denomination, the
  100,000-seat capacity, the block price schedule, the per-principal ownership
  bound, and the seat purchase transition; it is not a consensus transition.
- `specifications/revenue-routing-v1.md`: the 45/45/10 commercial split, the
  22.5/22.5 creator case, the proved integer remainder rule, separate 100%
  transaction-fee routing, and per-cycle Founder distribution with a carry; it
  is not a consensus transition.
- `specifications/escrow-payout-v1.md`: the three founder-directed escrows,
  bounded escrow-scoped spending capabilities, custody conservation, and the
  ordered payout rejection conditions; it is not a consensus transition.
- `specifications/economy-scenario-suite-v1.md`: the multi-year and adversarial
  scenarios the four accepted M2 models must survive, their restart-equivalence
  method, and the seeded property tests; it defines no model or transition.
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
- `specifications/reward-distribution-study-v1.md`: deterministic proportional,
  participant-cap, and principal-cap mechanism comparison contract.
- `specifications/admission-cost-study-v1.md`: deterministic hidden-principal
  work split, integer utility, operating-cost, refundable-bond capital-time,
  and churn study contract.
- `specifications/minimum-entitlement-study-v1.md`: deterministic zero-floor,
  per-participant, and work-proportional reserve comparison contract.

The corresponding executable research tools and reviewed fixtures live in
`../simulation/native_economy/`, `../simulation/participation/`,
`../simulation/authority/`, `../simulation/economic_stress/`, and
`../simulation/reward_distribution/`, `../simulation/admission_cost/`, and
`../simulation/minimum_entitlement/`.

The fixed Founder Economy manifest and derivation vectors live in
`../test-vectors/founder-economy-manifest-v1.json`,
`../test-vectors/founder-economy-manifest-v1.txt`, and
`../test-vectors/founder-economy-simulator-v1.txt`. The independent simulator
that consumes them is `../simulation/founder_economy/`, and
`../tools/founder-economy-vectors/verify.py` derives every recorded value from
the loaded manifest and a live run.

The Founder Seat sale model is `../simulation/founder_seats/` with vectors in
`../test-vectors/founder-seat-schedule-v1.txt`.
`../tools/founder-seat-vectors/verify.py` rederives the whole schedule by
walking the constitutional rule and requires the walk, the model, and the
recorded file to agree.

The revenue and transaction-fee routing model is
`../simulation/revenue_routing/` with vectors in
`../test-vectors/revenue-routing-v1.txt`.
`../tools/revenue-routing-vectors/verify.py` replays the whole scenario against
an independent implementation in `walk.py` that uses the naive share form, and
requires that replay, the model, and the recorded file to agree.

The escrow payout model is `../simulation/escrow_payout/` with vectors in
`../test-vectors/escrow-payout-v1.txt`.
`../tools/escrow-payout-vectors/verify.py` replays the whole scenario against an
independent implementation in `walk.py` that carries the escrow caps as
constitutional literals and recomputes the founder-economy state digest with its
own helper. It additionally runs `founder-economy-simulator-v1` on that model's
accepted fixture and requires the escrow fixture's opening custody to be bound to
that run, which is provenance the model itself cannot check.

The multi-year and adversarial scenarios over all four models are
`../simulation/scenarios/` with vectors in
`../test-vectors/economy-scenario-suite-v1.txt`. They add no model, transition,
or canonical label; every event parses under an accepted model's schema.
`../tools/scenario-suite-vectors/verify.py` runs all four scenarios and requires
each recorded total to match both the live run and a closed-form derivation from
Founder Constitution literals that imports nothing from `../simulation/`.

Shared deterministic primitives used by these models live in
`../simulation/common/`.
