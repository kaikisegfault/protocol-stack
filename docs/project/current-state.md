# Current state

Last updated: 2026-08-07

## Phase

M2 — Founder Economy specification and proof: **complete**. All sixteen
`first-goal.md` requirements pass.

M3 — Founder Economy devnet: **active**. Its first slice is delivered. Issue #94
and PR #95 merged at `d6ad528`, adding `founder-economy-consensus-v1` and
ADR 0023: the height-derived issuance cycle, the version-two genesis and chain
parameters, the canonical economy state and its commitment, five transaction
encodings, and the numeric receipt codes. It is a specification. No C++, Python,
vector, or digest changed, and nothing in the repository executes those bytes.

Issue #71
and PR #72 adopted the first exact contract at merged commit `14486cb`: an
eight-decimal `u64` denomination, all ten fixed issuance-channel caps, the
731-cycle supply derivation, permission liabilities, research-only eligibility
placeholders, ADR 0017, and normative vectors.

Issue #77 then made that contract executable and is merged at `9aeac23`. It
added `founder-economy-simulator-v1`, ADR 0018, the independent
`simulation/founder_economy/` model, a second normative vector file, and a
verifier that derives every recorded value from the loaded manifest and live
runs.

Issue #79 delivered the Founder Seat sale model satisfying `first-goal.md`
requirement 8 and is merged at `c03262f`.

Issue #82 delivered commercial revenue and transaction-fee routing satisfying
`first-goal.md` requirements 9 and 10 and is merged at `5029c00`. It added
`revenue-routing-v1`, ADR 0020, the independent `simulation/revenue_routing/`
model, a third normative vector file, and a verifier whose `walk.py` is a
second implementation the recorded file and the model must both agree with.

Issue #85 delivered escrow payout capabilities satisfying `first-goal.md`
requirement 11. It added `escrow-payout-v1`, ADR 0021, the independent
`simulation/escrow_payout/` model, a fourth normative vector file, and a
verifier that both replays the scenario against an independent walk and proves
the fixture's opening custody is bound to a live `founder-economy-simulator-v1`
run.

Issue #88 delivered the multi-year and adversarial scenario suite satisfying
`first-goal.md` requirement 13. It added `economy-scenario-suite-v1`, ADR 0022,
the deterministic generators in `simulation/scenarios/`, a fifth normative
vector file, and a verifier whose independence is closed-form derivation from
Founder Constitution literals rather than a fifth walk. It added no model,
transition, event kind, or canonical label.

Issue #91 delivered `founder-economy-report-v1.md`, satisfying `first-goal.md`
requirement 14, and this handoff satisfies requirement 16. No C++, consensus,
devnet, or previously accepted simulator behavior changed in any of these
slices.

## What works now

- The completed M1 C++20 ledger processes canonical signed native transfers,
  exact nonces, and fixed fees while rejecting malformed, replayed,
  unauthorized, overflowing, and insufficient-balance transactions.
- SQLite persistence, atomic commit, restart, deterministic state roots, a
  stateless Go ABCI adapter, and pinned CometBFT operate as a reproducible
  four-validator local devnet.
- Independent Python differential testing covers at least 10,000 seeded
  sequences; GCC, Clang, sanitizer, bounded fuzz, single-node, and
  four-validator hosted verification passed on the last merged executable
  state.
- Accepted M2 research models cover native custody, escrow, claims,
  participation, bounded authority, economic stress, concentration,
  identity-split incentives, and minimum entitlements. Their schemas and
  results remain research evidence, not production Founder economics.
- The accepted Founder Economy manifest exactly represents the
  55,743,940,100-unit maximum as 5,574,394,010,000,000,000 eight-decimal atomic
  units, fixes a canonical ten-channel manifest and digest, and proves every
  per-cycle, per-seat, and complete-population supply product without
  activating it.
- The independent Founder Economy simulator executes that contract. It loads
  the manifest under the ordered failure codes, tracks per-channel issued and
  outstanding amounts with checked `u64` arithmetic, and runs seat activation,
  base and referral permission evaluation, atomic exercise, and capped
  direct-channel issuance with deterministic trace, state, and result digests.
  It is research software and activates nothing.
- The Founder Seat sale model derives the complete constitutional price
  schedule and runs the full 100,000-seat sale end to end to exactly USD
  4,231,855,000, enforcing the 100,000-seat capacity and the 1,000-seat
  per-principal bound at their boundaries. It models the sale only; a purchased
  seat is not yet an activated seat.
- The revenue routing model splits a native commercial payment 45/45/10, halves
  the creator share for the 22.5/22.5 product-creator case, routes the floored
  shares' remainder to the Founder pool under a bound proved by exhaustive scan
  of all 200 residues, routes 100% of a transaction fee to a separate Founder
  fee pool, and distributes both pools per accounting cycle over a bound
  active-seat snapshot while carrying each residue forward. It creates no
  native units and routes value a constitutional channel already issued.
- The escrow payout model holds the three founder-directed escrows separately,
  takes opening custody from a recorded `founder-economy-simulator-v1` state by
  recomputing that model's digest, and releases value only through a capability
  bound to exactly one escrow and bounded by a per-payout maximum, a cumulative
  envelope, an expiry, and revocation. Each escrow conserves independently, and
  a second capability-side account of the same value must agree. It creates no
  native units: custody is fixed at the bind and non-increasing afterwards.
- The scenario suite runs those four models at multi-year scale. Three seats
  staggered 61 ticks apart each complete all 731 cycles with disjoint inactive
  cycles and performance reallocation; exactly 100 principals at the 1,000-seat
  bound absorb the whole 100,000-seat capacity; 122 routing cycles change their
  active population every cycle, 25 of them empty; and every escrow is drained
  and every envelope exhausted against custody the population run itself issued.
  Restart equivalence holds under prefix replay and split resume, and seeded
  property tests assert each model's conservation equations against its
  published results rather than its recorded totals.
- The one-word `proceed`, `conclude`, and `status` workflows reconstruct,
  deliver, and report repository state.

## Accepted M3 consensus contract

`founder-economy-consensus-v1` and ADR 0023 are accepted and unimplemented.
Nothing below is runnable; it is the contract the implementation must satisfy.

- The eligible cycle is a global epoch grid with a per-seat offset.
  `epoch_index(h) = h / epoch_blocks`, a seat activated in epoch `a` holds
  epochs `a + 1` through `a + 731`, and a cycle is evaluable only once
  `epoch_index(h)` has passed it. Cycle zero starts at the next boundary so all
  731 cycles are exactly `epoch_blocks` blocks for every seat. The 24-hour
  figure is a target realized by configuration, not a guarantee: the protocol
  counts blocks, and a halt changes a cycle's wall-clock duration with no rule
  detecting it.
- Schema version 2 defines a new chain, not a migration. Its 157-octet genesis
  fixes total supply, the initial fee pool, and the account count at exactly
  zero, making the constitution's no-genesis-allocation rule a decoder check.
  The unchanged chain-ID derivation over different genesis bytes separates it
  from any version-one chain.
- Five transaction kinds carry seat activation, base and referral permission
  evaluation, permission exercise, and capped direct issuance, each with
  canonical bytes, a normative check order, a replay key, and a resource bound.
  Result codes 16 through 36 sit above the unchanged version-one codes 0
  through 8, and a 49-octet version-two receipt carries the transaction kind so
  a code is read against the kind that produced it.
- Economy state is six record types under a domain-separated RFC 9162 tree,
  committed beside the unchanged accounts tree in a version-two state root.
  Pending permissions are four `u16` watermarks per seat rather than records,
  so a seat's whole accumulation history costs 8 octets on the active path.
  Unconditional economy state at full seat capacity is 200,018 records and
  6,800,388 octets.
- Total supply now changes, replacing a version-one invariant. It rises only
  through exercise and direct issuance, bounded by channel caps whose checked
  sum is exactly the supply limit. There is still no burn, confiscation, or
  public asset-creation operation.
- Three deferred founder decisions travel as signed, payload-bound, expiring
  attestations from three genesis-configured keys. The specification states in
  those words that they are devnet stand-ins with total control over the
  outcomes those policies would decide, that no production network may
  configure them, and what consensus still contains regardless of the attester:
  no attestation can change a leg amount, the 57,430,000,000-atomic base total,
  a channel cap, or the supply limit.
- Version-one transfer bytes, genesis, accounts tree, state root, and receipt
  are unchanged, and the version-one transfer remains valid on a version-two
  chain with its own labels and codes. Six narrowings against the frozen M2
  models are recorded in the specification rather than by editing an accepted
  contract.

## Adopted founder direction

- One native asset with an intended fixed maximum of 55,743,940,100 display
  units and no burn, secondary internal currency, or public asset creation.
- Exactly 100,000 permanent biometric Founder Seats, all-in-one Founder Nodes,
  731-cycle issuance, fixed allocation channels, 45/45/10 commercial routing,
  and 100% Founder transaction-fee routing.
- One company-hosted logical Ecosystem AI outside consensus and outside
  Founder Nodes, with separately bounded biometric, moderation, project,
  treasury, and developer-program capabilities.
- AI-approved controlled full-stack applications, one project creator plus at
  most one product creator, immutable accepted history, and Founder-only
  resource infrastructure.
- BTC, ETH, and approved stablecoins restricted to Founder Seat purchase,
  liquidity, native swaps, and withdrawal; they never become general internal
  balances.

These are target requirements, not runnable Founder behavior. Issue #71 added a
specification, JSON manifest, and fixed vectors; issues #77, #79, #82, and #85
each added a specification, ADR, Python model, vectors, and verifier for part of
them; issue #88 added a specification, ADR, deterministic generators, vectors,
and verifier that exercise all four at multi-year scale; and issue #94 added the
specification and ADR that fix how the accepted economy would be encoded in
consensus. None changed current transaction bytes, C++ state, devnet supply,
existing simulator schemas, bridge, wallet, AI, biometric, or resource behavior.

## Repository state

- Repository: `kaikisegfault/protocol-stack`.
- Issues #71, #77, #79, #82, #85, #88, and #91 are the M2 deliveries; PRs #72,
  #78, #80, #83, #86, #89, and #92 are merged.
- Issue #94 and PR #95 are the first M3 delivery, merged by rebase at `d6ad528`.
  PR final-head Actions run 31191322748 and post-merge run 31191385407 both
  passed the focused metadata path; the hosted matrix was correctly skipped for
  a documentation-only change.
- After PR #72, commits `de9903e` and `4947c46` replaced the Codex agent layout
  with Claude Code and simplified the authorship rules.
- Issue #77 and PR #78 merged at `9aeac23`. PR final-head Actions run
  30849218092 and post-merge run 30850030514 both passed the complete hosted
  matrix — scope classification, GCC and Clang debug, both sanitizers, and the
  aggregate required check.
- Issue #79 and PR #80 merged at `c03262f`. PR final-head Actions run
  30852439693 and post-merge run 30853305170 both passed the complete hosted
  matrix — scope classification, GCC and Clang debug, both sanitizers, and the
  aggregate required check.
- Issue #82 and PR #83 merged by rebase at `5029c00`. PR final-head Actions run
  30896652965 and post-merge run 30897473243 both passed the complete hosted
  matrix. Squash merge is disabled on this repository; use `--rebase`.
- Issue #85 and PR #86 merged by rebase at `512dc0c`. PR final-head Actions run
  30900989541 and post-merge run 30901790621 both passed the complete hosted
  matrix — scope classification, GCC and Clang debug, both sanitizers, and the
  aggregate required check.
- Issue #88 and PR #89 merged by rebase at `20f7fcf`. PR final-head Actions run
  31012045337 and post-merge run 31013129150 both passed the complete hosted
  matrix — scope classification, GCC and Clang debug, both sanitizers, and the
  aggregate required check. Runs 31011546356 and 31011900980 were superseded by
  later pushes to the same branch and were cancelled.
- Issue #91 and PR #92 merged by rebase at `7b4cd6a`, with post-merge run
  31015245429 passing the focused metadata path; the hosted matrix was correctly
  skipped for a documentation-only change. The preceding handoff merged at
  `bc4272a` with post-merge run 31014389973.
- No delivery branch, open PR, additional worktree, or generated build
  directory remains from any delivery.
- Local evidence: 67 Founder Economy tests, 49 Founder Seat tests, 57 revenue
  routing tests, and 57 escrow payout tests pass; the economy verifier derives
  139 manifest and 65 simulator values, the seat verifier derives 96 values
  while confirming an independent walk of the constitutional rule agrees with
  the model on all 1,000 blocks, the routing verifier derives 200 values while
  confirming an independent replay agrees with the model and with 2,400
  contract share computations, and the escrow verifier derives 169 values while
  confirming an independent walk agrees with the model on all 39 events and
  that three caps match the Founder Constitution; repository metadata and link
  validation, `git diff --check`, and the focused verifier unit tests pass.
- The scenario suite adds 48 tests — 14 multi-year, 15 market, 19 property — and
  133 vectors derived across 107,812 events in four scenarios. Every monetary
  total agrees with a closed-form derivation in
  `tools/scenario-suite-vectors/expected.py`, which imports nothing from
  `simulation/`; changing one constitutional literal there was confirmed to fail
  five vectors, including the maximum-supply accounting.
- All five verifiers fail closed when a recorded vector key is never derived.
  The economy, routing, and escrow verifiers were each confirmed to fail on a
  tampered recorded value. The suite verifier was confirmed to fail three ways:
  a tampered value, a recorded key never derived, and a derived key the file
  does not carry.
- The escrow drain scenario binds the population run's own state digest, so the
  escrows are proved drained of exactly what three seats issued into them across
  their complete 731-cycle windows. The empty-cycle count is recorded three
  times: from the generator's population rule, from the verifier's independent
  restatement of it, and from the trace as closes that credited no seat. The
  third agrees with the other two only because every pool in that scenario
  exceeds its active seat count, which the specification states rather than
  assumes.
- The routing remainder bound is proved, not asserted: the remainder depends
  only on `amount mod 200`, so scanning all 200 residues in both creator cases
  is complete. It is at most 2 atomic units with one creator and 3 with two.
- Routing share arithmetic uses the amount's quotient and remainder. The direct
  `45 * amount / 100` form leaves `u64` above roughly 7.4% of maximum supply,
  so it would have rejected a representable payment as an overflow.
- Escrow custody is fixed at the bind and never rises afterwards, because
  `bind_opening_custody` is the only writer of a custody amount and rejects once
  bound. The vectors record `containment.custody_increases_after_bind=0` and
  `containment.multi_escrow_payouts=0`, both derived by the independent walk.
- The escrow binding proves consistency, not provenance: the model only
  recomputes the supplied economy state's digest, so a self-consistent invented
  state would also pass it. The verifier closes that gap by running the economy
  simulator on its accepted fixture and requiring the escrow fixture to bind
  that exact run. Inside the model, the manifest cap is the defence, and a
  `CUSTODY_ABOVE_CAP` vector exercises it. The specification and ADR 0021 both
  state this split rather than overclaiming the digest check.
- `ARITHMETIC_OVERFLOW` is unreachable through escrow events because the caps
  are far below `u64`. The checked arithmetic is still exercised directly by
  the tests so the guard is proved present rather than assumed.
- The verifier reproduces 2,297 canonical JCS bytes and manifest digest
  `2a8923d40615589cc9c9ef90598c0cec56b72a7efa103cf8c05aceb5b54dc698` from the
  checked-in manifest, and fails closed when a recorded vector key is never
  derived or when any recorded value is tampered with.
- The 731-cycle single-seat scenario reproduces the recorded per-seat schedule
  exactly, including 25,000,200,000,000 Founder-operator and
  1,250,010,000,000 referral atomic units.
- Scope classification correctly selects `full` because Python source, CMake,
  and vector paths are not lightweight metadata.
- No dependency, workflow, C++ source, generated build directory, or additional
  worktree is part of any M2 result.

## Remaining gap

No executable Founder Seat, revenue distribution, production escrow, biometric
verifier, packaged Founder Node, AI service, controlled application runtime,
resource cloud, bridge, liquidity system, wallet, public testnet, or mainnet is
implemented. The Founder issuance schedule, permission transitions, revenue
routing, and escrow payouts now exist only as independent Python models, not as
C++ consensus behavior.

The accepted consensus contract does not narrow that gap. No version-two byte is
encoded or decoded anywhere, no vector file for it exists, and the C++ kernel is
unchanged. A specification that no implementation has been checked against is
also unproved: the encoding may contain errors that only a harness will find.

All sixteen `first-goal.md` requirements now pass: 1 through 13 in model and
scenario form, 14 as `founder-economy-report-v1.md`, 15 as ADRs 0017 through
0022, and 16 as hosted verification on each accepted commit plus this handoff.
What that does and does not establish is stated in the report rather than
summarized here.

Requirement 3's qualifier is now half closed. The models represent a cycle as a
deterministic integer index, so no wall clock reaches a transition, which is
what that requirement forbids. `founder-economy-consensus-v1` binds that index
to a chain-defined epoch, but only on paper: no code derives a cycle from a
height, and the models still take the index directly.

Restart equivalence is state equivalence under replay. It is not persistence,
crash-consistency, or a snapshot format, and no model has any of those.

The four models are only partly joined. The escrow model is the only one that
binds another: it takes opening custody from a recorded
`founder-economy-simulator-v1` state by digest, a one-way read that changes
nothing in the economy model, and the scenario suite now exercises that binding
against a complete 731-cycle population run rather than a small fixture. The
others remain unjoined. A seat purchased in the sale model is not an activated
seat in the economy model, and a seat identifier in a routing snapshot is not
proved to be either, because the activation height rule and the
purchase-to-activation transition are unsettled. Enrollment, biometric
identity, managers, and same-cycle liveness proof for a performance recipient
are not modelled, and the last of those cannot be without the unresolved
performance policy. The per-principal seat bound is not yet a per-human bound.

Routing and escrow payouts prove accounting, not policy. Nothing shows that the
activity metric is fair, that a snapshot reflects a real machine, that a creator
or product is legitimately approved, that the transaction-fee amount rule is
sound, that any AI evaluation is well made, that an approval threshold is safe,
or that a payout recipient is legitimate. The per-seat balance carry has no
storage bound at 100,000 seats, escrow recipient balances have no storage bound
either, and no claim or push mechanism moves a credited balance into a spendable
account. An escrow capability is modelled as a record; the signed envelope,
replay domain, and encoding that would carry one on a real chain are undefined.

## Exact next action

Make `founder-economy-consensus-v1` executable, starting with the reference
encoder and the normative vectors rather than with C++.

Create one bounded M3 issue for a standard-library Python implementation of the
version-two bytes and the vector file it derives, following the established
`tools/*-vectors/` pattern:

1. encode and decode version-two genesis, the attestation preimage, and all five
   transaction kinds, with the admission checks that are stateless;
2. compute the six economy leaf layouts, the economy tree, and the version-two
   state root, reusing the accepted version-one accounts-tree construction;
3. execute the five transitions against the canonical state with their normative
   check order, result codes, and no-write-on-failure behavior; and
4. emit `test-vectors/founder-economy-consensus-v1.txt` covering the obligations
   the specification lists, with a verifier that derives every recorded value and
   fails closed when a recorded key is never derived or a value is tampered with.

This is the right next slice because a specification no implementation has been
checked against is unproved, and the Python side is the cheaper place to find an
encoding error. It is also where the version-one accounts tree, state-root
construction, and Ed25519 handling get exercised against the new labels before
the C++ kernel commits to them.

The C++20 kernel implementing the same bytes, and the cross-language agreement
that `protocol-primitives-v1` requires, follow in the slice after it. Keep the
accepted M2 schemas, vectors, and digests frozen: the new model implements the
consensus rules, not the M2 model's, and its vectors derive from the
specification rather than from any M2 result digest.

This slice is unblocked. It uses `max_performance_recipients = 64`, the devnet
parameter the specification already fixes, so it does not depend on any of the
four founder-reserved decisions.

## Blockers

None for the next action.

One founder-reserved decision is now close to blocking. The Founder performance
winner count sets `max_performance_recipients`, and through it the reallocation
storage bound: worst case is 1,973,700,000 octets with single-recipient
reallocations and 57,237,300,000 at the 64-recipient ceiling, the second well
beyond a minimum-spec Founder Node. ADR 0023 records that incentive bounds this
in practice — exercise is permissionless and deletes the record while paying its
recipient — but that incentive is not containment, and the consensus bound
cannot be selected without the winner count. Ask the owner when the storage
bound becomes the nearest dependency, which is the slice after the reference
encoder, not this one.

Four founder-reserved decisions are recorded but not yet blocking: whether an
inactive referred cycle creates the referral permission, direct-channel
eligibility policy, the Founder activity metric with its grace allowance,
performance ranking, winner count, and tie rule, and the AI funding framework
with its evaluation criteria, milestone and tranche policy, and approval
thresholds. Each is supplied per action as an explicit research input and
recorded in the trace, so the models report them rather than inventing one. The
scenario suite supplies thousands of them from stated deterministic rules that
`economy-scenario-suite-v1` records as scenario parameters, which is volume, not
resolution.

They become blocking during M3, when a research input must become a consensus
rule. That transition has now started rather than finished. The accepted
encoding does not invent any of the four; it carries three of them as signed
attestations from genesis-configured keys that the specification labels devnet
stand-ins, and it fixes the referral policy result as a per-cycle supplied
value. Each stand-in must be replaced by an accepted policy with its own
specification before any public network, so the encoding defers the decisions
without hiding them.

Ask the owner at the point where a specific transition would otherwise have to
invent one, or where a bound cannot be selected without an answer. The winner
count reaches the second of those first, as recorded above.
