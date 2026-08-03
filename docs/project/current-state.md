# Current state

Last updated: 2026-08-03

## Phase

M2 — Founder Economy specification and proof. Issue #71 and PR #72 adopted the
first exact contract: an eight-decimal `u64` denomination, all ten fixed
issuance-channel caps, the 731-cycle supply derivation, permission liabilities,
research-only eligibility placeholders, ADR 0017, and normative vectors at
merged commit `14486cb`. Final-head Actions run 30775698847 and post-merge run
30776173468 passed the full hosted matrix. No C++ or existing simulator
behavior changed.

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

These are target requirements, not runnable Founder behavior. Issue #71 added
a specification, JSON manifest, and fixed vectors. It did not change current
transaction bytes, C++ state, devnet supply, existing simulator schemas,
bridge, wallet, AI, biometric, or resource behavior.

## Repository state

- Repository: `kaikisegfault/protocol-stack`.
- Issue #71 is closed and PR #72 is merged.
- Before this handoff-only update, `main` and `origin/main` equal `14486cb`.
- No delivery branch, open PR, additional worktree, or generated build
  directory remains from the issue #71 delivery.
- Strict local JSON and exact-integer cross-checks reproduce ten channels, the
  5,574,394,010,000,000,000-atomic maximum, per-seat and full schedule
  products, 2,297 canonical JCS bytes, and manifest digest
  `2a8923d40615589cc9c9ef90598c0cec56b72a7efa103cf8c05aceb5b54dc698`.
- Local `git diff --check`, repository metadata and link validation, and
  focused verifier unit tests pass. Scope classification correctly selects
  `full` because JSON and protocol vector paths are not lightweight metadata.
- PR #72 final-head Actions run 30775698847 passed scope classification, GCC
  and Clang debug builds, both sanitizer builds, bounded fuzzing, all Python
  simulations, single-node compatibility, four-validator restart/integration,
  and the aggregate required check on exact commit `463dd3d`.
- Post-merge Actions run 30776173468 passed the same complete matrix and
  aggregate gate on exact `main` commit `14486cb`.
- No dependency, workflow, executable source, generated build directory, or
  additional worktree is part of the issue #71 result.

## Remaining gap

No executable Founder Seat, founder-directed supply schedule, permission
transition, revenue distribution, production escrow, biometric verifier,
packaged Founder Node, AI service, controlled application runtime, resource
cloud, bridge, liquidity system, wallet, public testnet, or mainnet is
implemented.

The nearest product result is not one of those services yet. It is a complete,
integer-only Founder Economy specification and simulator that proves the fixed
maximum and every economic route before C++ behavior changes.

## Exact next action

Create one bounded M2 issue for the standard-library Python Founder Economy
simulator foundation.
Strictly load the accepted manifest, reproduce its vectors, and implement
channel issued/outstanding accounting plus base, referral, inactive-allocation,
permission-exercise, and direct-placeholder transitions with deterministic
trace/state digests and negative, replay, cap, overflow, and atomicity tests.
Do not change C++ consensus in that next slice.

## Blockers

None for the next action.
