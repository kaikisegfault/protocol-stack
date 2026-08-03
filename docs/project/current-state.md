# Current state

Last updated: 2026-08-03

## Phase

M2 — Founder Economy specification and proof. Issue #68 is realigning the
repository around the owner-confirmed Founder Constitution before further
economic implementation. The active branch is
`docs/68-founder-constitution`; hosted publication and verification are
pending.

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

## Direction being adopted in issue #68

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
- Base before issue #68: `main` and `origin/main` at `5e107fc`.
- Active issue: #68.
- Active branch: `docs/68-founder-constitution`, not yet published.
- Open PRs: none at branch creation.
- Focused local checks pass `git diff --check`, repository metadata and link
  validation, exact economic arithmetic assertions, and lightweight-scope
  classification.
- Latest base `main` verification: Actions run 30756658019 passed the focused
  metadata path for commit `5e107fc`.
- No repository build, test, server, monitor, or helper process was running at
  branch creation. No generated build directory was present.

## Remaining gap

No Founder Seat, founder-directed supply schedule, revenue distribution,
production escrow, biometric verifier, packaged Founder Node, AI service,
controlled application runtime, resource cloud, bridge, liquidity system,
wallet, public testnet, or mainnet is implemented.

The nearest product result is not one of those services yet. It is a complete,
integer-only Founder Economy specification and simulator that proves the fixed
maximum and every economic route before C++ behavior changes.

## Exact next action

Finish issue #68: inspect the complete direction-alignment diff, run focused
metadata verification, publish the candidate, require terminal GitHub checks,
merge it, verify the exact post-merge commit, and leave a clean handoff. Do not
begin the M2 economic manifest or simulator within the issue #68 documentation
slice.

After issue #68 is completely merged and reconciled, create one bounded M2
issue for the canonical Founder Economy manifest and exact supply derivation.
Specify the atomic denomination, all ten channel caps, their exact sum,
per-seat 731-cycle arithmetic, and research-only placeholders for the still
unresolved activity and direct-channel eligibility rules before implementing
the independent simulator.

## Blockers

None for issue #68.
