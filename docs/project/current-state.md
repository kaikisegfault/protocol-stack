# Current state

Last updated: 2026-08-08

## Phase

M3 — Founder Economy devnet, in progress. Slice M3.1 delivered the revised
economic contract, M3.2 made it executable, and M3.3 rebound every dependent
model to it, all on 2026-08-08. Requirement 3 of `first-goal.md` is satisfied.
M2 completed on 2026-08-05 with all sixteen requirements of
`goals/m2-founder-economy-proof.md` passing.

On 2026-08-07 the owner supplied the four outstanding founder decisions and
revised the economy. ADR 0023 records them: the maximum supply is now
56,993,950,100 display units, the Founder referral doubled to 34.2 units per
cycle and moved to the direct-mint channels as an unconditional benefit,
unreferred seats fund a monthly performance pool, a cycle is met at 18 hours of
fully operational uptime with a 6-hour fragmentable grace allowance, and a
failed cycle's 342 units go to the highest uptime that cycle.

**The accepted M2 models are therefore superseded as founder direction.** They
implement `founder-economy-manifest-v1` and remain exactly as verified; the
constitution now specifies a v2 that only the new economy model implements. The
seat, routing, escrow, and scenario-suite models still bind v1. Nothing about
what runs today changed, because none of it activates anything.

### How M3.3 was delivered

Issue #108 and PR #109 delivered `escrow-payout-v2` at merged commit `a8ea180`,
and issue #110 and PR #111 delivered `economy-scenario-suite-v2` at merged commit
`04cdd23`. Together they satisfy requirement 3 of `first-goal.md`: all four
dependent models are re-verified against version two, every recorded digest is
regenerated, and both verifiers still fail closed in both directions.

The slice was split because the suite binds the escrow model, so rebinding the
suite depends on the escrow model already having a v2 binding.

**Rebinding is a new version, not an edit, and the repository decided that rather
than the session.** `escrow-payout-v1.md` fixes its research-input shapes and
digest labels as immutable and requires a new schema and ADR to change them, and
`economy-scenario-suite-v1.md` already recorded that its scenario parameters were
superseded and that a version two suite would derive them. ADR 0026 records both
halves.

Escrow payout differs in exactly six strings: the five domain labels it writes
and the one founder-economy state label it reads. Every transition, rejection
condition, rejection order, journal bucket, and invariant is identical, so the
two versions share one implementation selected by a `Binding` record. A duplicate
package was rejected — `founder_economy_v2` earned one because its transition set
changed shape, while two copies of a thousand lines of identical payout logic
would have nothing to notice drift.

The escrow v2 fixture is the v1 scenario with only its four embedded economy
states rebound. Holding the scenario fixed is what makes the rebinding auditable:
the two runs produce identical result codes for all 39 events in identical order,
and their final states differ in exactly one member, `bound_state_digest`. That
equivalence is asserted, because a rebinding defect that altered a payout rule
would still produce a self-consistent vector file.

The opening custody is unchanged at 34,200,000,000 / 6,840,000,000 /
3,420,000,000 atomic units. The escrow legs are unrevised and both fixtures accept
two base permissions, so the amounts coincide while the state they come from does
not. Both facts are recorded rather than one being assumed.

**The suite's scenario 1 changed shape.** Version one supplied the activity
verdict and the performance recipient because the constitution had not decided
them; both are now decided, so the generator supplies measurements and the model
derives the answers. The tick is the shared `cycle_window`: three seats staggered
61 ticks apart hold different cycle indices at the same tick, and reallocation to
"the highest uptime in that same cycle" is only meaningful against a shared
window. Reusing `cycle_index` would have put exactly one seat in every window, so
no reallocation would ever have had a candidate.

The intended winner is given the only maximal uptime and the model derives the
winner set. Every other seat sits exactly on the 64,800-second threshold, so the
founder-directed boundary is exercised in every reallocating window rather than
only in a unit test. At most one seat may fail per window, which the generator
asserts rather than assumes: two would make the winner set depend on evaluation
order. A fourth seat is activated and never evaluates, because all three
population seats consume their whole 731-cycle windows and the three uptime
probes need an unevaluated key to reach `MISSING_UPTIME_RECORD`,
`INVALID_UPTIME_RECORD`, and `INCONSISTENT_UPTIME_RECORD` in order.

Scenarios 2 and 3 are proved version-independent rather than asserted to be: the
19 seat and 26 routing vectors are byte-identical in both vector files.

No v1 artifact, C++, consensus, or devnet behavior changed.
`simulation/founder_economy/` is untouched, and `escrow-payout-v1.txt`, its
fixture, and `economy-scenario-suite-v1.txt` are byte-for-byte unchanged and
still pass.

### How M3.2 was delivered

Issue #103 and PR #104 delivered `founder-economy-simulator-v2` at merged commit
`a0521d0`. It added the specification, ADR 0025, the executable model in
`simulation/founder_economy_v2/`, a research scenario fixture, 189 normative
vectors, and a second verifier entry point in `tools/founder-economy-v2-vectors/`.

The transition set changed shape, not only parameters. The referral left the
permission system entirely: `accrue_referral` is unconditional, direct-mint, and
keyed by `(referred_seat_id, cycle_index)`, with no activity and no eligibility
input. An unreferred seat credits `unreferred_performance_pool:global` rather
than being rejected, which is what consumes the channel exactly at capacity, so
`SEAT_NOT_REFERRED` is gone. The permission `kind` discriminator went with the
referral, and `INVALID_PERFORMANCE_ALLOCATION` went with the supplied allocation
list it validated.

`evaluate_base_permission` now derives the activity verdict and the winner set
from a cycle uptime record instead of reading two supplied fixtures.

**The record carries measurements only.** It cannot express a verdict, an
eligibility flag, a winner, a ranking, or an amount, and tests assert that a
record carrying an `active` flag or a `winners` list fails to parse. This is the
distinction the slice existed to preserve: a research placeholder stands in for
an undecided founder policy, while the record stands in for a rule ADR 0023 and
the Founder Constitution already decide but whose measurement pipeline is
unbuilt. `MISSING_UPTIME_RECORD`, `INVALID_UPTIME_RECORD`, and
`INCONSISTENT_UPTIME_RECORD` are deliberately distinct from the research codes so
a trace can tell a missing measurement from a missing founder decision.

A `cycle_window` is separate from a seat's `cycle_index`. A seat's 731 cycles
begin at its own first activation, so two seats' cycle 7 are different windows
and reallocation to "the highest uptime in that same cycle" is only meaningful
against a shared one. The model cannot verify that a supplied window is the
correct window for a seat's cycle — that is the deferred cycle-boundary rule — so
the separate field keeps the gap visible in every event rather than hiding it in
a coincidence of names.

The carry needed care. Carried value is unreserved channel capacity, not a fourth
ledger dimension, so folding it into the journal's channel balance would
double-count it and no accepted journal would balance. It is pinned by its own
identity instead, per event in the engine and cumulatively in the state
invariants:

```text
issued(founder_operator) + outstanding(founder_operator) + performance_carry
  = count(evaluated_permission_keys) * 34,200,000,000
 <= cap(founder_operator)
```

asserted as an equality rather than a bound, because a bound would admit a defect
that lost carried value.

`founder_referral` is rejected by `direct_issue`. That is containment rather than
tidiness: admitting it would let a supplied eligibility fixture mint referral
units outside the per-seat-cycle accounting and place a founder-decided channel
under an undecided placeholder.

No v1 artifact, C++, consensus, or devnet behavior changed.

### How M3.1 was delivered

Issue #99 and PR #100 accepted `founder-economy-manifest-v2` at merged commit
`0c05b52`. It added the specification, ADR 0024, the manifest JSON and its
digest, 154 normative vectors, a strict loader in `simulation/founder_economy_v2/`,
and a verifier in `tools/founder-economy-v2-vectors/`.

The contract fixes the 56,993,950,100 display maximum as
5,699,395,010,000,000,000 atomic under the unchanged eight-decimal
denomination, and the referral at 34,200,000,000 atomic per cycle as an
unconditional direct-mint channel capped at 250,002,000,000,000,000. The other
nine channel caps, the seat capacity, the per-person bound, the 731-cycle
schedule, and every base-permission leg are unchanged.

Version one was not edited. Its digest names the exact byte string the M2
evidence was verified against, and the two contracts differ in shape rather
than only in parameters: v2 has no `referral_permission` issuance kind, no
`referral_permission` object, and no permission `kind` discriminator. Each
loader rejects the other's manifest, the domain labels differ, and tests assert
both directions. ADR 0024 records that reasoning and four other structural
decisions.

No simulator, C++, consensus, devnet, or previously accepted v1 artifact
changed. v2 has no executable model and activates nothing.

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
- The accepted `founder-economy-manifest-v2` contract represents the
  56,993,950,100-unit maximum as 5,699,395,010,000,000,000 eight-decimal atomic
  units, fixes a canonical ten-channel manifest at 2,267 JCS bytes with digest
  `84cca09865b6c62bf09d3f6bc3821a2527c7a4835652cffdc0ebefa34b314ce5`, and puts
  the referral in the direct-mint group at 250,002,000,000,000,000 atomic. Its
  strict loader enforces the eight ordered failure codes and rederives every
  product and subtotal.
- The `founder-economy-simulator-v2` model executes that contract. It runs seat
  activation, base permission evaluation, unconditional referral accrual, atomic
  exercise, and capped direct issuance with deterministic trace, state, and
  result digests. A cycle is met at 64,800 seconds of cumulative fully
  operational uptime, checked in both of the constitution's stated forms; the
  failed-cycle winner set is the highest uptime among seats that met the same
  window, split equally with the remainder carried; an empty winner set carries
  the whole portion. A window's record is bound by digest on first reference, so
  the window's uptime is one fact for a run rather than a per-event opinion. It
  is research software and activates nothing.
- A complete 731-cycle single-seat run reproduces the v2 per-seat schedule
  exactly, including 25,000,200,000,000 Founder-operator, 12,500,100,000,000
  venture-escrow, and 2,500,020,000,000 unreferred-pool atomic units.
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
- The escrow payout model implements two accepted contracts. `escrow-payout-v2`
  binds `founder-economy-simulator-v2` and differs from version one in exactly
  six strings; a state recorded under either economy version is rejected by the
  other's bind with `INVALID_RESEARCH_INPUT`, derived in the vectors rather than
  asserted. Both versions' transitions are identical, which the two runs' equal
  trace codes prove.
- The scenario suite runs under either binding. `economy-scenario-suite-v2`
  reruns all four scenarios against the revised economy: a complete 731-cycle
  staggered population run with derived activity and derived performance
  winners, the 100,000-seat concentrated sale, 122 routing cycles, and an escrow
  drain bound to the v2 population run's own state digest. The referral channel
  is consumed exactly by its two destinations — 5,000,040,000,000 atomic units of
  referrer custody plus a 2,500,020,000,000 unreferred pool equal its whole
  issuance — and the performance carry ends at zero.
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
and verifier that exercise all four at multi-year scale. Issue #99 restated the
contract under the revised direction and issue #103 made that restatement
executable. None changed current transaction bytes, C++ state, devnet supply,
previously accepted simulator schemas, bridge, wallet, AI, biometric, or resource
behavior.

## Repository state

- Repository: `kaikisegfault/protocol-stack`.
- Issue #108 and PR #109 are the M3.3a delivery, merged by rebase at `a8ea180`.
  PR final-head Actions run 31268938270 on `0076d4f` and post-merge run
  31269458528 on `a8ea180` both passed the complete hosted matrix — scope
  classification `full`, GCC and Clang debug, both sanitizers, and the aggregate
  required check. Run 31268730543 was superseded by a later push and was
  cancelled.
- Issue #110 and PR #111 are the M3.3b delivery, merged by rebase at `04cdd23`.
  PR final-head Actions run 31270415727 on `5ba7b14` passed the complete hosted
  matrix; no run on that branch was superseded.
- M3.3 local evidence: eight verifiers pass. The suite derives 133 v1 and 138 v2
  vectors; escrow payout derives 169 v1 and 172 v2; the economy derives 139
  manifest and 65 simulator v1 values, 154 manifest v2 and 189 simulator v2; the
  seat verifier derives 96 and the routing verifier 200, both unchanged. 50 new
  tests pass — 19 escrow v2 and 31 scenario v2 — alongside the 57 existing escrow
  and 48 existing scenario tests, all unchanged.
- Both v2 verifiers fail closed four ways, each confirmed by execution at exit 1
  with the unmutated run as a positive control: a tampered recorded value, a
  recorded key no derivation reaches, a derived key the file does not carry, and
  the v2 verifier run against the v1 vector file. The last is the informative
  one for the suite: it fails first on the superseded maximum supply.
- Issue #103 and PR #104 are the M3.2 delivery, merged by rebase at `a0521d0`.
  PR final-head Actions run 31266418185 on `4392d15` and post-merge run
  31266927181 on `a0521d0` both passed the complete hosted matrix — scope
  classification `full`, GCC and Clang debug, both sanitizers, and the aggregate
  required check.
- PR #105 recorded this handoff and merged by rebase at `3d23416`, with
  post-merge run 31267484643 passing the focused metadata path; the hosted matrix
  was correctly skipped for a documentation-only change.
- M3.2 local evidence: the simulator verifier derives 189 vectors and the
  manifest verifier still derives 154; 96 new tests pass — 38 model, 39
  transition-error, and 19 scenario — alongside the 61 existing v2 manifest and
  loader tests. All five retained v1 verifiers pass unchanged, so the M2 evidence
  is intact.
- The simulator verifier fails closed five ways, each confirmed by execution: a
  tampered recorded value, a recorded key no derivation reaches, a derived key
  the file does not carry, a Founder Constitution literal that no longer spans a
  cycle, and a model constant that disagrees with the constitution. The last is
  the informative one: shrinking the model's threshold to 64,500 seconds does not
  merely change a number, it makes the constitution's two stated forms of the
  cycle rule disagree and turns an accepted evaluation into a rejection.
- The research scenario reaches all fourteen modelled result codes, and the
  verifier records that as a derived claim so a later scenario cannot quietly
  lose coverage. Every prefix of a mixed scenario reproduces the state the full
  run held at that point.
- Two guards are unreachable at real scale and are proved present rather than
  reached. A zero equal-split share requires the Founder portion shrunk below the
  winner count, because the smallest possible share at the full 100,000-seat
  capacity is 342,000 atomic units. Arithmetic overflow requires a carry near the
  `u64` maximum, because every channel cap leaves more than double its own size
  in headroom.
- Issue #99 and PR #100 are the M3.1 delivery, merged by rebase at `0c05b52`.
  PR final-head Actions run 31262789135 on `e9de7a7` and post-merge run
  31263319868 both passed the complete hosted matrix — scope classification
  `full`, GCC and Clang debug, both sanitizers, and the aggregate required
  check. Runs 31262577723 and 31262627548 were superseded by later pushes to the
  same branch and were cancelled.
- PR #101 recorded this handoff and merged by rebase at `852e289`, with
  post-merge run 31263846117 passing the focused metadata path; the hosted
  matrix was correctly skipped for a documentation-only change.
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
- M3.1 local evidence: the v2 verifier derives 154 vectors; 23 manifest and 38
  error tests pass; all five v1 verifiers pass unchanged, so the retained M2
  evidence is intact.
- The v2 verifier fails closed five ways, each confirmed: a tampered recorded
  value, a recorded key never derived, a derived key the file does not carry, a
  manifest that disagrees with the Founder Constitution, and an edit to the
  retained v1 contract table down to one atomic unit.
- The fourth of those is the load-bearing one. `expected.py` imports nothing
  from `simulation/` and restates the constitution's two allocation tables by
  hand in tenths of a display unit. The constitution states the economy twice —
  as per-eligible-cycle amounts and as maximum channel totals — and derives
  neither from the other, so requiring them to agree checks the manifest against
  the founder document rather than against a second reading of the
  specification. A forged manifest and contract table raising the referral to
  34.3 units per cycle, propagated consistently through the referral cap, the
  direct-mint subtotal, and the maximum supply, passes every loader stage and is
  still rejected by four `expected.py` comparisons.
- Every recorded v2 rejection is produced by a live loader run over a minimally
  mutated manifest rather than named, and five pairs carrying two defects at
  once prove which stage reports first. A positive control asserts the same
  entry point accepts the unmutated manifest.
- The vectors prove the supply revision is accounted to the referral channel
  alone: the maximum rose by 1,250,010,000 display units, the referral channel
  rose by exactly that, and the summed change across the other nine channels is
  zero. That sum is taken in atomic units against the retained v1 contract
  table, because summing in display units divided a one-atomic-unit divergence
  to zero and hid what the check exists to find.
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
a chain-defined height or epoch is still undone. And the direction the M2 models
implement was superseded on 2026-08-07, so their accepted schemas, vectors, and
digests are evidence about a contract the constitution no longer directs.

M3.1 restated that contract, M3.2 made it executable, and M3.3 rebound every
dependent to it, which closes the second qualifier. `escrow-payout-v2` and
`economy-scenario-suite-v2` bind version two; the seat and revenue-routing models
needed no change, which was re-proved rather than assumed — neither imports either
economy package, and neither carries a supply figure, channel cap, channel
identifier, referral amount, or issuance-cycle count. The retained v1 contracts,
models, vectors, and digests remain in place and passing as the M2 evidence.

M3.2 supplies the activity and reallocation computation that three removed
placeholders used to stand in for, but it does not supply the measurement that
computation reads. The uptime record is an abstract input whose shape, bounds,
and determinism are fixed and whose challenge construction, sampling rate,
dispute window length, and dispute resolution are not. Nothing in the model
proves that an `uptime_seconds` value reflects a real machine, and a record that
omits seats yields a winner set over the seats it does list without that being
detected. The month definition for the unreferred pool, that pool's payout, tie,
and remainder rules, and the cycle boundary in heights or epochs also remain
unspecified. Accrual into the pool is modelled; paying it out is not.

M3.3 exercised that input at multi-year scale without narrowing the gap. The
scenario suite supplies a `cycle_window` by generator convention — the tick — and
supplies every `uptime_seconds` value it then derives verdicts from. A suite that
conserves value under supplied measurements is evidence about the derivation, not
about the measurements. Its winner is also deliberately unique in every window,
so the tie and remainder paths of the reallocation rule are covered by
`founder-economy-simulator-v2`'s own vectors rather than by the suite.

Restart equivalence is state equivalence under replay. It is not persistence,
crash-consistency, or a snapshot format, and no model has any of those.

The four models are only partly joined. The escrow model is the only one that
binds another: it takes opening custody from a recorded founder-economy state by
digest, a one-way read that changes nothing in the economy model, and the
scenario suite exercises that binding against a complete 731-cycle population run
rather than a small fixture. Version two of both preserves exactly this, and no
more. The
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

Milestone slice M3.4: define the cycle boundary in chain heights or epochs,
satisfying requirement 4 of `docs/project/first-goal.md`.

Create one bounded M3 issue. Take the cycle boundary before the rest of the
uptime pipeline, because it is the smaller half and the other half depends on it.
M3.2 and M3.3 left the dependency visible in every event rather than hidden: a
`cycle_window` is a separate field from a seat's `cycle_index`, and no model can
check that a supplied window is the correct one for a seat's cycle, because the
mapping is exactly what this slice defines. The scenario suite currently supplies
the tick as the window, which is a generator convention and not a rule.

The slice should decide and specify:

1. **What a cycle is measured in.** Heights or epochs, and how a seat's cycle
   `n` maps to a window identifier that two independent nodes compute
   identically. No wall clock may be reachable from a transition.
2. **When a seat's issuance window opens.** The Founder Constitution gives each
   seat 731 cycles beginning at its own first activation, so the activation
   height rule is part of this. It is also the unsettled rule behind the
   purchase-to-activation gap, so check whether this slice closes that too or
   only narrows it.
3. **The check the model cannot make today**, so that
   `evaluate_base_permission` can reject a `cycle_window` that is not the window
   for the supplied `cycle_index`.

Requirement 4 says "with no wall clock reachable from a transition", which the
models already satisfy by representing a cycle as a deterministic integer index.
The work is binding that index to a chain-defined quantity, not removing a clock.

M3.5 is then the rest of requirement 7: the challenge construction, sampling
rate, dispute window length, and dispute resolution that produce an
`uptime_seconds` value. M3.2 fixed the shape of that input and M3.3 exercised it
at multi-year scale; neither built the pipeline behind it, and nothing yet proves
a measurement reflects a real machine.

Requirements 5, 6, and 10 — canonical state keys, transaction encodings, numeric
receipt codes, the M1 compatibility boundary, and the C++20 implementation — come
after the boundary is defined, because they serialize what the boundary settles.

Keep `founder-economy-manifest-v1`, `founder-economy-simulator-v1`,
`escrow-payout-v1`, `economy-scenario-suite-v1`, and every v1 model, vector, and
digest in place and passing. They are the retained M2 evidence and are not edited
to match the new direction. `simulation/founder_economy/` stays untouched.

## Blockers

None for the next action.

Two founder-reserved decisions remain open, and neither blocks M3.1 through
M3.4: eligibility and anti-abuse mechanics for the liquidity-mining,
impermanent-loss, HUB-verified-user, and mystery-box direct-mint channels, and
the AI funding framework with its evaluation criteria, milestone and tranche
policy, and approval thresholds. Both are still supplied to the models as bound
research inputs, and `founder-economy-manifest-v2` keeps
`direct_channel_eligibility_result` as its single research placeholder for
exactly that reason.

The other two closed on 2026-08-07. Activity, grace, performance ranking, tie
handling, inactive-seat referral treatment, and referral-channel eligibility are
now decided in the Founder Constitution and ADR 0023, and must be implemented as
stated rather than re-litigated or re-supplied as fixtures.

Ask the owner at the point where a specific transition would otherwise have to
invent one of the two that remain.
