# ADR 0006: M1 devnet ledger and monetary parameters

- Status: Accepted
- Date: 2026-07-23

## Context

The in-memory M1 kernel needs exact values and failure behavior before
implementation. These choices must fit `u64`, preserve a single native asset,
make fees and replay handling auditable, and avoid pretending that early
devnet constants are production tokenomics.

## Decision

Adopt the state transition and constants in
[`ledger-transition-v1.md`](../specifications/ledger-transition-v1.md).

Use `PSU` as non-consensus display shorthand, nine decimal places, a
1,000,000,000-display-unit constitutional cap, and a default 100,000,000-unit
M1 genesis split equally across four deployment-provided bootstrap accounts.
There is no post-genesis issuance in M1.

Use a fixed fee of 1,000 atomic units for every successful transfer. Route the
fee in full to the native fee pool. Failed transfers make no writes and pay no
fee. The fee limit remains signed so a later transition version can introduce
a bounded fee schedule without changing the version-one transaction bytes.

Admit only canonical, correct-chain, strictly signed transactions. Commit all
admitted transaction IDs, including stateful failures, and produce their
deterministic execution receipts in input order. Malformed, wrong-chain, and
invalid-signature bytes remain outside application receipts and commitments as
required by ADR 0004.

## Rationale and alternatives

Nine decimal places provide sub-unit granularity while allowing one billion
display units to fit comfortably in `u64` (`10^18` atomic units). Six decimals
would also fit and be simpler to display, while eighteen decimals would make
even modest display-unit caps exceed `u64`; neither offers an M1 protocol
advantage.

A fixed fee makes conservation and differential testing explicit. Dynamic
base fees, byte metering, congestion auctions, validator rewards, and fee
burning require economic simulation and are deferred. Zero fees would avoid
early pricing but would fail to exercise the native fee-pool path required by
the first operational goal.

Charging stateful failures can discourage abuse but adds balance-dependent
failure paths and makes retry behavior harder to audit. M1 charges only
successful transfers. A later metered transition can change this with a new
version.

Pruning zero-balance accounts would reduce state size but would need a separate
nonce tombstone or replay window. Retaining accounts preserves monotonic replay
protection with the smallest state machine.

Committing admitted failures makes proposer inputs and deterministic results
observable at the application boundary. Committing malformed or
invalid-signature bytes would conflict with the primitive specification and
unnecessarily give meaningless bytes application identity.

## Security, economic, and compatibility effects

- No public operation can mint, burn, issue another asset, or change the
  configured supply.
- Checked arithmetic and full-transition atomicity protect conservation.
- Chain ID, strict signatures, exact next nonces, and expiry heights bound
  replay.
- A successful self-transfer charges the same fixed fee and advances replay
  state without changing ownership.
- The unused difference between genesis supply and the supply limit is not
  circulating and has no issuance path in M1.
- These values govern an M1 devnet genesis only. Production parameters require
  M2 simulation and a new accepted genesis/transition decision; changing a
  live chain's constants is not backward compatible.

## Evidence

Acceptance requires the normative ledger-transition vectors and passing
independent C++20 and Python harnesses under all compiler and sanitizer
presets. The first production kernel change must use these vectors unchanged
and add property and randomized differential sequences rather than replacing
the decision harness.
