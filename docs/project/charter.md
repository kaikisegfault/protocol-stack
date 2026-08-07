# Project charter

## Mission

Build an original, deterministic protocol stack and the staged ecosystem
defined by the [Founder Constitution](founder-constitution.md).

## Current phase

The Sovereign Devnet Alpha is runnable. The project is now entering the
Founder Economy specification and proof milestone. Nothing here is ready for
production funds, biometric reliance, external custody, or security claims.

## Governing document hierarchy

- `founder-constitution.md` fixes founder intent and owner-reserved choices.
- `first-goal.md` defines the nearest measurable operational outcome.
- `roadmap.md` orders the complete dependency ladder.
- accepted specifications and ADRs define implemented technical meaning.
- `current-state.md`, Git, and verification evidence define what works now.

Chat history, deleted drafts, marketing expectations, and research fixture
values are not project state.

## Current architectural defaults

- Original C++20 deterministic account-based ledger kernel.
- Exactly one protocol-native asset and no public asset-creation operation.
- Native protocol modules for supply, fees, Founder economics, treasury,
  escrow, authority, and bridge-facing constraints.
- Controlled application execution only after a separate specification and
  ADR; no public EVM or arbitrary contract deployment.
- Pinned CometBFT `v0.39.4` as the replaceable first consensus/P2P adapter.
- SQLite as the replaceable first owning store.
- Python independent models for economic proof and C++ differential testing.
- Go only for replaceable non-critical infrastructure and adapters.
- Company-hosted AI outside consensus and outside Founder Nodes.
- A deterministic resource meter and fee path even when an application later
  sponsors a user's fee.

## Constitutional invariants

The intended production protocol must enforce:

1. The ledger recognizes exactly one native asset.
2. Issued supply never exceeds 56,993,950,100 display units expressed in the
   accepted atomic denomination. The figure is fixed at genesis; its revision
   on 2026-08-07, before any issuance, is recorded in ADR 0023.
3. No public operation creates another asset, burns native supply, or exceeds
   a founder-directed issuance-channel cap.
4. Operational failure may remove a future benefit but does not slash,
   confiscate, or burn already owned native units.
5. Monetary arithmetic is checked integer arithmetic.
6. Identical ordered inputs produce identical results and state roots.
7. Failed transitions are atomic and replay cannot duplicate value or
   authority.
8. Founder Seat history, accepted ledger history, and accepted application
   version history cannot be silently erased.
9. Wallet signatures alone cannot perform sensitive Founder identity actions;
   accepted biometric authorization is separately bound to the exact action.
10. AI inference, external prices, biometrics, telemetry, and wall clocks are
   not direct consensus computations.
11. AI actions enter through signed, replay-safe, capability-scoped envelopes
    bounded by exact escrow, amount, policy, and expiry rules.
12. One logical AI authority never receives an unconstrained mint, treasury,
    bridge, content, and upgrade key.
13. BTC, ETH, and stablecoins remain external bridge assets and never become
    general-purpose internal balances.

## Native module direction

The complete root module set includes:

- accounts, native transfers, nonces, and fees;
- constitutional supply and the fixed issuance-channel manifest;
- Founder Seat capacity, price, enrollment, identity, managers, activity,
  issuance, revenue, fee, and legacy rules;
- venture, community-grant, developer, and policy-mediated escrows;
- bounded AI decision capabilities and audit receipts;
- approved project, milestone, tranche, product, and commercial-routing rules;
- validator active-set and Founder Node lifecycle;
- controlled application-runtime capabilities and version commitments;
- resource proof, placement, service, and reward interfaces;
- upgrade, timelock, recovery, and emergency containment; and
- bridge-facing purchase, liquidity, swap, withdrawal, and recovery
  capabilities.

Each consensus-visible module requires a canonical specification, invariants,
failure behavior, independent model, adversarial tests, and accepted ADR before
production implementation.

## Authority boundaries

Founder-directed value and authority rules cannot be changed by autonomous
engineering. Missing direct-mint benefits, economic recipients, content
policy, AI delegation, bridge-asset governance, or legacy ownership behavior
must be referred to the owner when they become an implementation dependency.

Within those rules, Claude has standing authority to research, choose, document,
implement, test, publish, and integrate technical mechanisms without approval
pauses. Security evidence may reject an unsafe mechanism without changing the
founder objective; another mechanism must then be selected.

The System Creator Company initially manages releases, node requirements, and
AI models and policies. The Ecosystem AI is the only case-specific decision
source for authority scopes delegated to it. Neither role may rewrite history
or bypass deterministic protocol limits.

## Current milestone boundaries

The current Founder Economy proof milestone includes the exact economic
manifest, deterministic schedules, accounting transitions, independent
simulation, and adversarial evidence.

It does not yet implement production C++ economics, a biometric verifier,
Founder Node packaging, controlled applications, resource hosting, AI serving,
real bridge custody, liquidity, wallet, public testnet, NodeOS, or hardware.
Their constitutional interfaces are preserved now and realized in roadmap
order.

## Safety position

Autonomous development can produce specifications, research software, local
devnets, testnets, and release candidates. Public production readiness requires
independent protocol, cryptographic, economic, biometric, bridge, AI,
reproducible-build, recovery, and operational review. Passing automated tests
is necessary evidence, never a bug-free or safe-custody guarantee.
