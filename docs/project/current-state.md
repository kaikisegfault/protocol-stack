# Current state

Last updated: 2026-08-03

## Phase

M2 — Founder Economy specification and proof, milestone slice M2.3. Issue #71
and PR #72 adopted the first exact contract at merged commit `14486cb`: an
eight-decimal `u64` denomination, all ten fixed issuance-channel caps, the
731-cycle supply derivation, permission liabilities, research-only eligibility
placeholders, ADR 0017, and normative vectors.

Issue #77 then made that contract executable. It adds
`founder-economy-simulator-v1`, ADR 0018, the independent
`simulation/founder_economy/` model, a second normative vector file, and a
verifier that derives every recorded value from the loaded manifest and live
runs. No C++, consensus, devnet, or previously accepted simulator behavior
changed.

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
- The one-word `proceed`, `conclude`, and `status` workflows reconstruct,
  deliver, and report repository state.

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
specification, JSON manifest, and fixed vectors; issue #77 added a
specification, ADR, Python model, vectors, and verifier for them. Neither
changed current transaction bytes, C++ state, devnet supply, existing simulator
schemas, bridge, wallet, AI, biometric, or resource behavior.

## Repository state

- Repository: `kaikisegfault/protocol-stack`.
- Issues #71 and #77 are the M2 deliveries; PR #72 is merged.
- After PR #72, commits `de9903e` and `4947c46` replaced the Codex agent layout
  with Claude Code and simplified the authorship rules. Both passed hosted
  verification; `4947c46` is the base of the current delivery branch.
- Issue #77 is delivered on branch `feat/77-founder-economy-simulator`.
- Local evidence on the candidate commit: 61 focused simulator tests pass
  across the manifest, model, error, and scenario suites; the vector verifier
  derives and matches 139 manifest and 65 simulator values; repository metadata
  and link validation, `git diff --check`, and the focused verifier unit tests
  pass.
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
  worktree is part of the issue #77 result.

## Remaining gap

No executable Founder Seat, revenue distribution, production escrow, biometric
verifier, packaged Founder Node, AI service, controlled application runtime,
resource cloud, bridge, liquidity system, wallet, public testnet, or mainnet is
implemented. The Founder issuance schedule and permission transitions now exist
only as an independent Python model, not as C++ consensus behavior.

Within `first-goal.md`, the simulator satisfies requirements 1 through 3, 4, 5,
6, 7, and 12 in model form and contributes to 13 and 14. These remain open:

- requirement 8: seat capacity, the 1,000-seats-per-person bound, and the
  USD price-schedule vectors including the USD 4,231,855,000 full-sale total;
- requirement 9: commercial 45/45/10 routing with the 22.5/22.5 case and
  explicit integer remainder behavior;
- requirement 10: separate 100% transaction-fee routing to eligible Founders;
- requirement 11: venture, community-grant, and developer escrow payout
  capabilities that cannot spend through the issuance capability; and
- requirements 13 through 15: the remaining adversarial and multi-year
  scenarios and the accepted report distinguishing proved accounting from
  unresolved policy.

The simulator also models the seat graph only. Enrollment, identity, managers,
and same-cycle liveness proof for a performance recipient are not modelled, and
the last of those cannot be without the unresolved performance policy.

## Exact next action

Create one bounded M2 issue for Founder Seat capacity and pricing on top of
`founder-economy-simulator-v1`. Add the exact 100,000-seat capacity, the
1,000-seats-per-person bound, and the integer USD price schedule with fixed
vectors for the USD 100 first block, the USD 1,000 tier boundary, the USD
91,900 final block, and the USD 4,231,855,000 derived full-sale proceeds.
Keep the external payment proof a bound research placeholder and do not change
C++ consensus in that slice.

## Blockers

None for the next action.

Two founder-reserved decisions are recorded but not yet blocking: whether an
inactive referred cycle creates the referral permission, and direct-channel
eligibility policy. Both are supplied per action as explicit research inputs
and recorded in the trace, so the model reports them rather than inventing one.
They become blocking at the M3 consensus transition, not in the next slice.
