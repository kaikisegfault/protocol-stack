# Documentation index

## Project

- `project/founder-constitution.md`: authoritative founder intent, fixed
  end-state requirements, decision ownership, and unresolved founder gates.
- `project/vision.md`: long-term direction and boundaries.
- `project/charter.md`: current architecture and governing principles.
- `project/first-goal.md`: current operational outcome and acceptance evidence.
- `project/goals/m1-sovereign-devnet-alpha.md`: retained acceptance contract
  for the completed first runnable devnet milestone.
- `project/goals/m2-founder-economy-proof.md`: retained acceptance contract for
  the completed Founder Economy proof milestone, whose figures predate the
  2026-08-07 direction revision.
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
- `project/founder-economy-report-v1.md`: the accepted M2 milestone report,
  separating what the six Founder Economy contracts and their verifiers prove
  about deterministic accounting from the policy, provenance, identity,
  storage, and production-safety claims none of them establishes.

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

ADR 0022 selects closed-form derivation over a second model walk as the
independence argument for the multi-year scenario suite, defines restart
equivalence as state equivalence under replay, and requires seeded property
tests to assert published values rather than a model's own invariants. It
accepts an evidence contract, not a consensus transition.

ADR 0023 records the founder decisions of 2026-08-07: the maximum supply
revised to 56,993,950,100 before any issuance, the doubled unconditional
referral benefit relocated to the direct-mint channels, the unreferred
performance pool that keeps that channel exactly consumed, the 18-hour activity
threshold with its 6-hour fragmentable grace allowance, highest-uptime
performance reallocation with equal splitting among ties, and an uptime path
that derives validator duties on-chain, proves resource provision by
challenge-response, and gives the Ecosystem AI a dispute window rather than a
signature that could freeze payment. It supersedes the economic figures in ADR
0017 and the unresolved markers in ADRs 0018 and 0022, and activates nothing.

ADR 0024 accepts a second Founder Economy manifest rather than editing the
first, because the M2 evidence is evidence about a specific contract and the two
differ in shape rather than only in parameters. It separates the versions at the
digest domain label, orders the channels as the Founder Constitution's two
allocation tables read, describes the referral by its two destinations so the
exact-consumption claim is machine-checkable, keeps the 18-hour activity
threshold out of the canonical bytes until the cycle boundary is defined, and
makes the verifier's independence a hand-restated constitution rather than a
second model. It accepts an economic contract, not a consensus transition.

ADR 0025 makes that contract executable. It supplies the cycle uptime record as
measurements only, so the activity verdict and the winner set are derived rather
than supplied; separates a shared `cycle_window` from a seat's own
`cycle_index`; binds a window's record by digest on first reference; carries the
integer remainder and the whole pot of an empty winner set forward; replaces the
conditional referral permission with an unconditional direct-mint accrual with
two destinations; and keeps `founder_referral` out of `direct_issue` so a
supplied eligibility fixture cannot mint referral units. It accepts a research
model contract, not a consensus transition.

ADR 0026 rebinds the dependent models to version two. It records that rebinding
is a new version rather than an edit, because `escrow-payout-v1` fixes its
research-input shapes as immutable; that one implementation selected by a
`Binding` is preferred to a duplicate package, because the two versions'
transitions are identical and duplication has no mechanism to notice drift; that
the research scenario is held fixed so a rebinding defect is distinguishable
from an intended scenario difference; and that a cross-version state reuses
`INVALID_RESEARCH_INPUT` rather than gaining a code of its own. It accepts a
compatibility boundary, not a consensus transition.

ADR 0027 defines the cycle boundary in chain heights. It records that a cycle is
28,800 blocks on one global grid rather than a per-seat grid, because
reallocation to the highest uptime "in that same cycle" needs a window several
seats share; that 28,800 is chosen because the pinned 3-second commit interval
divides all three founder-directed durations exactly, so no threshold is
rounded; that a seat's cycles begin at the next full window, because counting the
activating window would fail a seat for where in a window its activation landed;
that activation heights may not decrease; and that a window's nominal duration is
86,400 seconds, so a measurement is denominated against the window rather than a
clock. It defines a schedule and a check, not a consensus transition.

ADR 0028 defines the uptime measurement pipeline. It records that credit is per
one-hour slot, because all three founder-directed figures are whole slots and
partial credit would interpolate between probes; that a seat is credited for the
duties it was assigned rather than for signing, because the constitution bounds
the live signing set; that challenges are selected from the previous height's
state root, so a seat cannot schedule uptime around its own audit; that the
Ecosystem AI's dispute may only subtract and only up to the grace allowance, so
a captured key cannot fail a fully operational node; that silence finalises a
window after one further window; and that a record's seat set is derived from
the bound activation schedule, so an omission is unrepresentable. It measures
and settles no value.

ADR 0029 enforces the cycle boundary and record completeness in the economy
model. It records that one economy version carries both, because the record's
denomination is stable; that the manifest is not re-versioned, because no
founder-directed figure moves; that a sibling package is preferred to a
`Binding` here, on the condition ADR 0026 itself named for when that choice
inverts; that the manifest layer and the window grid are bound rather than
copied; that monotonicity moves to the writer of activation heights; that the
in-scope seat set has no upper bound, because a seat past its issuance span
still runs a node and may still win a reallocation; that an omitted and an
added seat are two codes because they have opposite economic effects; and that
the intrinsic record checks precede the run-history binding check so a code
means one thing. It accepts a research model contract, not a consensus
transition.

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
- `specifications/founder-economy-manifest-v2.md`: the same denomination under
  the 2026-08-07 founder direction — the 56,993,950,100 maximum, the referral
  channel doubled and moved to direct-mint, both referral destinations, one
  remaining research placeholder, and a fixed M3 manifest digest; it supersedes
  version one as direction, retains it as evidence, and is not a consensus
  transition.
- `specifications/founder-economy-simulator-v1.md`: strict manifest loading,
  the five Founder Economy transitions, bound research inputs, journal
  conservation, digest labels, and vector obligations for the independent
  Python model; it is not a consensus transition.
- `specifications/founder-economy-simulator-v2.md`: the same model under the
  2026-08-07 direction — the cycle uptime record carrying measurements only, the
  derived activity verdict and winner set, the unconditional direct-mint
  referral with its two destinations, and the performance carry with its
  conservation identity; it is not a consensus transition.
- `specifications/founder-economy-simulator-v3.md`: the same accounting with the
  cycle boundary and record completeness enforced — an `activation_height` on
  the seat record, the window check applied inside base permission evaluation,
  and a record required to cover exactly its window's in-scope seat set; it
  binds the accepted v2 manifest and the accepted window grid rather than
  restating either, and is not a consensus transition.
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
- `specifications/escrow-payout-v2.md`: the same transitions binding
  `founder-economy-simulator-v2`, differing in exactly five domain labels and
  the bound economy state label, with the cross-version compatibility boundary
  and the unchanged escrow caps; it is not a consensus transition.
- `specifications/economy-scenario-suite-v1.md`: the multi-year and adversarial
  scenarios the four accepted M2 models must survive, their restart-equivalence
  method, and the seeded property tests; it defines no model or transition.
- `specifications/economy-scenario-suite-v2.md`: the same four scenarios with
  the population run rebound to `founder-economy-simulator-v2` and the escrow
  drain to `escrow-payout-v2`, supplying a cycle uptime record instead of a
  supplied activity verdict and performance recipient; it defines no model or
  transition.
- `specifications/cycle-boundary-v1.md`: the 28,800-block window grid a cycle is
  cut from, the mapping from a seat's activation height to its 731-window
  issuance span, the ordered conditions of the window check, and the exact block
  equivalents of the founder-directed activity threshold and grace allowance; it
  defines a schedule and measures nothing.
- `specifications/uptime-measurement-v1.md`: the 24-slot grid a window is
  subdivided into, the two evidence sources, challenge selection from an
  unpredictable beacon and its response deadline, the conjunctive slot credit
  rule, the bounded Ecosystem AI dispute window that finalises by expiry, and
  record completeness at the producing end; it measures and settles no value.
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

The revised contract is `../test-vectors/founder-economy-manifest-v2.json` with
vectors in `../test-vectors/founder-economy-manifest-v2.txt`. Its strict loader
is `../simulation/founder_economy_v2/`, and
`../tools/founder-economy-v2-vectors/verify.py` derives every recorded value
from the loaded manifest and from `expected.py`, which imports nothing from
`../simulation/` and restates the Founder Constitution's allocation tables by
hand. Every recorded failure code is produced by a live loader run over a
mutated manifest. No revised model exists yet.

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
`../test-vectors/escrow-payout-v1.txt` and `../test-vectors/escrow-payout-v2.txt`.
`../tools/escrow-payout-vectors/verify.py` replays the whole scenario against an
independent implementation in `walk.py` that carries the escrow caps as
constitutional literals and recomputes the founder-economy state digest with its
own helper. It additionally runs the founder-economy simulator of the selected
version on that model's accepted fixture and requires the escrow fixture's
opening custody to be bound to that run, which is provenance the model itself
cannot check. `--version` selects the accepted contract; version one binds
`founder-economy-simulator-v1` and version two binds
`founder-economy-simulator-v2`, and the v2 vectors additionally derive that no
version-one economy state can satisfy a version-two bind.

The multi-year and adversarial scenarios over all four models are
`../simulation/scenarios/` with vectors in
`../test-vectors/economy-scenario-suite-v1.txt` and
`../test-vectors/economy-scenario-suite-v2.txt`. They add no model, transition,
or canonical label; every event parses under an accepted model's schema.
`--version` selects the suite. Version two rebinds the population run to
`founder-economy-simulator-v2` and the escrow drain to `escrow-payout-v2`, and
supplies a cycle uptime record from which the model derives the activity verdict
and the winner set. Scenarios 2 and 3 record identical values under both
versions, because the Founder Seat sale and revenue routing models carry no
supply or channel figure.
`../tools/scenario-suite-vectors/verify.py` runs all four scenarios and requires
each recorded total to match both the live run and a closed-form derivation from
Founder Constitution literals that imports nothing from `../simulation/`.

The cycle boundary model is `../simulation/cycle_boundary/` with vectors in
`../test-vectors/cycle-boundary-v1.txt`.
`../tools/cycle-boundary-vectors/verify.py` derives every recorded value twice,
once from a live model run and once from an `expected.py` that imports nothing
from `../simulation/` and restates the Founder Constitution's 24, 18, and 6
hours and the pinned M1 commit interval by hand. It holds a seat activation
table and answers whether a window is the window for a seat's cycle; it measures
no uptime and is not bound by any economy model yet.

Shared deterministic primitives used by these models live in
`../simulation/common/`.
