# Current state

Last updated: 2026-08-07

## Phase

M3 — Founder Economy devnet, not yet started. M2 completed on 2026-08-05 with
all sixteen requirements of
`goals/m2-founder-economy-proof.md` passing.

On 2026-08-07 the owner supplied the four outstanding founder decisions and
revised the economy. ADR 0023 records them: the maximum supply is now
56,993,950,100 display units, the Founder referral doubled to 34.2 units per
cycle and moved to the direct-mint channels as an unconditional benefit,
unreferred seats fund a monthly performance pool, a cycle is met at 18 hours of
fully operational uptime with a 6-hour fragmentable grace allowance, and a
failed cycle's 342 units go to the highest uptime that cycle.

**The accepted models are therefore superseded as founder direction.** They
implement `founder-economy-manifest-v1` and remain exactly as verified; the
constitution now specifies a v2 they do not implement. Nothing about what runs
today changed, because none of it activates anything.

### How M2 was delivered

Issue #71 and PR #72 adopted the first exact contract at merged commit
`14486cb`: an eight-decimal `u64` denomination, all ten fixed issuance-channel caps, the
731-cycle supply derivation, permission liabilities, research-only eligibility
placeholders, ADR 0017, and normative vectors.

Issue #77 then made that contract executable and is merged at `9aeac23`. It
added `founder-economy-simulator-v1`, ADR 0018, the independent
`simulation/founder_economy/` model, a second normative vector file, and a
verifier that derives every recorded value from the loaded manifest and live
runs.

Issue #79 delivered the Founder Seat sale model satisfying `goals/m2-founder-economy-proof.md`
requirement 8 and is merged at `c03262f`.

Issue #82 delivered commercial revenue and transaction-fee routing satisfying
`goals/m2-founder-economy-proof.md` requirements 9 and 10 and is merged at `5029c00`. It added
`revenue-routing-v1`, ADR 0020, the independent `simulation/revenue_routing/`
model, a third normative vector file, and a verifier whose `walk.py` is a
second implementation the recorded file and the model must both agree with.

Issue #85 delivered escrow payout capabilities satisfying `goals/m2-founder-economy-proof.md`
requirement 11. It added `escrow-payout-v1`, ADR 0021, the independent
`simulation/escrow_payout/` model, a fourth normative vector file, and a
verifier that both replays the scenario against an independent walk and proves
the fixture's opening custody is bound to a live `founder-economy-simulator-v1`
run.

Issue #88 delivered the multi-year and adversarial scenario suite satisfying
`goals/m2-founder-economy-proof.md` requirement 13. It added `economy-scenario-suite-v1`, ADR 0022,
the deterministic generators in `simulation/scenarios/`, a fifth normative
vector file, and a verifier whose independence is closed-form derivation from
Founder Constitution literals rather than a fifth walk. It added no model,
transition, event kind, or canonical label.

Issue #91 delivered `founder-economy-report-v1.md`, satisfying `goals/m2-founder-economy-proof.md`
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
  activating it. That maximum is the superseded v1 figure; the constitution now
  directs 56,993,950,100.
- The independent Founder Economy simulator executes that contract. It loads
  the manifest under the ordered failure codes, tracks per-channel issued and
  outstanding amounts with checked `u64` arithmetic, and runs seat activation,
  base and referral permission evaluation, atomic exercise, and capped
  direct-channel issuance with deterministic trace, state, and result digests.
  It is research software and activates nothing. Its referral transition is
  superseded: a referral is now unconditional and direct-mint.
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

## Adopted founder direction

- One native asset with an intended fixed maximum of 56,993,950,100 display
  units and no burn, secondary internal currency, or public asset creation. The
  maximum was raised from 55,743,940,100 on 2026-08-07, before any issuance, to
  fund the doubled referral channel; it becomes immutable at genesis.
- Exactly 100,000 permanent biometric Founder Seats, all-in-one Founder Nodes,
  731-cycle issuance, fixed allocation channels, 45/45/10 commercial routing,
  and 100% Founder transaction-fee routing.
- A cycle is met at 18 hours or more of cumulative fully operational uptime,
  where fully operational means every node component healthy at once. The
  6-hour grace allowance is cumulative and fragmentable.
- A failed cycle's 342-unit Founder portion goes to the highest cumulative
  uptime in that same cycle, shared equally among exact ties, restricted to
  seats that met the cycle, with the integer remainder carried forward. It
  settles when the failed seat next exercises a permission.
- The Founder referral benefit is 34.2 units per cycle, unconditional, and a
  direct-mint channel capped at 2,500,020,000. A seat bought without a recorded
  referrer routes its allocation to a monthly unreferred performance pool, so
  the channel is consumed exactly.
- Uptime reaches consensus without trusting self-reports: validator duties are
  derived on-chain, resource provision is proved by challenge-response, and the
  Ecosystem AI holds a bounded dispute window rather than a signature that
  could freeze payment.
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
and verifier that exercise all four at multi-year scale. None changed current
transaction bytes, C++ state, devnet supply, existing simulator schemas, bridge,
wallet, AI, biometric, or resource behavior.

## Repository state

- Repository: `kaikisegfault/protocol-stack`.
- Issues #71, #77, #79, #82, #85, #88, and #91 are the M2 deliveries; PRs #72,
  #78, #80, #83, #86, #89, and #92 are merged.
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

All sixteen requirements of `goals/m2-founder-economy-proof.md` passed against
`founder-economy-manifest-v1`. What that does and does not establish is stated
in `founder-economy-report-v1.md` rather than summarized here.

Two qualifiers matter for M3. The models represent a cycle as a deterministic
integer index, so no wall clock reaches a transition, but binding that index to
a chain-defined height or epoch is still undone. And the direction those models
implement was superseded on 2026-08-07, so every accepted schema, vector, and
digest is now evidence about a contract the constitution no longer directs.

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

Milestone slice M3.1: restate the economy contract under the revised direction.
This comes before the consensus encoding, because the referral relocation and
the derived activity rule change which transitions exist, not merely their
parameters.

Create one bounded M3 issue for `founder-economy-manifest-v2`, delivering:

1. a specification and ADR fixing the 56,993,950,100 maximum
   (5,699,395,010,000,000,000 atomic under the unchanged eight-decimal
   denomination) and all ten channel caps, with the referral channel at
   2,500,020,000 in the direct-mint group;
2. the manifest JSON, its canonical byte length, and its digest;
3. normative vectors and a verifier that derives every recorded value and fails
   closed, at the standard the five existing verifiers set.

Prove in the vectors that the two subtotals — 41,981,330,000 and
15,012,620,100 — add to the maximum exactly, and that
`100,000 x 731 x 34.2 = 2,500,020,000` consumes the referral channel with no
remainder.

Do not change `simulation/founder_economy/` in that slice. The simulator
revision is the next one, and it is larger: the referral becomes an
unconditional direct-mint transition, `evaluate_referral_permission` and its
`inactive_referral_result` input disappear, `evaluate_base_permission` takes a
derived activity input and a derived winner set, and the unreferred performance
pool is a new beneficiary. Every dependent model, vector, and digest —
seat, routing, escrow, and the scenario suite — regenerates after that.

Keep `founder-economy-manifest-v1` and every v1 model, vector, and digest in
place and passing. They are the retained M2 evidence and are not edited to
match the new direction.

## Blockers

None for the next action.

Two founder-reserved decisions remain open, and neither blocks M3.1 through
M3.3: eligibility and anti-abuse mechanics for the liquidity-mining,
impermanent-loss, HUB-verified-user, and mystery-box direct-mint channels, and
the AI funding framework with its evaluation criteria, milestone and tranche
policy, and approval thresholds. Both are still supplied to the models as bound
research inputs.

The other two closed on 2026-08-07. Activity, grace, performance ranking, tie
handling, inactive-seat referral treatment, and referral-channel eligibility are
now decided in the Founder Constitution and ADR 0023, and must be implemented as
stated rather than re-litigated or re-supplied as fixtures.

Ask the owner at the point where a specific transition would otherwise have to
invent one of the two that remain.
