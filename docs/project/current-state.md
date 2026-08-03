# Current state

Last updated: 2026-08-03

## Phase

M2 — Founder Economy specification and proof. Issue #68 and PR #69 adopted the
owner-confirmed Founder Constitution and dependency-ordered complete roadmap
at merged commit `9af994f`. Final-head Actions run 30774247804 and post-merge
run 30774269594 passed the focused metadata path. Issue #68 is closed and no
delivery branch remains. No protocol, executable, test, build, dependency,
configuration, or simulation behavior changed.

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

These are target requirements, not runnable behavior. Issue #68 changes only
Markdown and repository skill instructions. It does not change current
transaction bytes, C++ state, devnet supply, simulator schemas, bridge, wallet,
AI, biometric, or resource behavior.

## Repository state

- Repository: `kaikisegfault/protocol-stack`.
- Issue #68 is closed and PR #69 is merged.
- Before this handoff-only update, `main` and `origin/main` equal `9af994f`.
- No delivery branch, open PR, additional worktree, or generated build
  directory remains from issue #68.
- Focused local checks pass `git diff --check`, repository metadata and link
  validation, exact economic arithmetic assertions, and lightweight-scope
  classification.
- PR #69 final-head Actions run 30774247804 passed scope classification and the
  required focused metadata check on exact commit `3d368c9`.
- Post-merge Actions run 30774269594 passed the same focused path on exact
  `main` commit `9af994f`; the compiler and sanitizer matrix correctly skipped
  for Markdown and skill metadata only.
- No repository build, test, server, monitor, or helper process was running at
  the issue #68 merge boundary.

## Remaining gap

No Founder Seat, founder-directed supply schedule, revenue distribution,
production escrow, biometric verifier, packaged Founder Node, AI service,
controlled application runtime, resource cloud, bridge, liquidity system,
wallet, public testnet, or mainnet is implemented.

The nearest product result is not one of those services yet. It is a complete,
integer-only Founder Economy specification and simulator that proves the fixed
maximum and every economic route before C++ behavior changes.

## Exact next action

Create one bounded M2 issue for the canonical Founder Economy manifest and
exact supply derivation. Specify the atomic denomination, all ten channel caps,
their exact sum, per-seat 731-cycle arithmetic, permission-liability model, and
research-only placeholders for the unresolved activity, best-performer, and
direct-channel eligibility rules. Accept the specification and fixed vectors
before implementing the independent simulator; do not change C++ consensus in
that first slice.

## Blockers

None for issue #68.
