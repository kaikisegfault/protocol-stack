# Roadmap

Milestones follow dependency order. The complete public ecosystem is the north
star; each intermediate exit must still produce honest, runnable evidence.
Dates are omitted until measured delivery velocity and external review
availability exist.

## F0 — Agent and project foundation — complete

Establish repository instructions, durable continuation, architecture
boundaries, ADRs, engineering standards, verification, GitHub publication, and
the `proceed`, `conclude`, and `status` workflows.

Exit: a clean session reconstructs verified state and performs the exact next
bounded action.

## M1 — Sovereign Devnet Alpha — complete

Specify protocol primitives; implement the deterministic C++ ledger,
persistence, replay, and independent Python model; integrate replaceable
CometBFT consensus; and operate a reproducible four-validator local network.

Exit: the retained
[`Sovereign Devnet Alpha`](goals/m1-sovereign-devnet-alpha.md) requirements
pass across GCC, Clang, sanitizers, differential sequences, restart, and
four-replica audits.

## M2 — Founder Economy specification and proof — complete

### M2.1 Direction adoption

Adopt the Founder Constitution, reconcile conflicting project assumptions,
define decision ownership, and redirect autonomous work toward the actual
economic model.

### M2.2 Canonical economic manifest

Specify the atomic denomination and exact maximum supply; Founder and direct-
mint channel caps; 731-cycle issuance; inactive-beneficiary routing; referral
limits; seat pricing; commercial 45/45/10 routing; transaction-fee routing;
escrow custody; claims; rounding; replay; and failure behavior.

Use deterministic stand-ins for external payment, biometric, activity, and
performance evidence. Do not accept mutable external data as consensus input.

### M2.3 Independent simulation and stress evidence

Build or extend independent integer-only models that exactly reconstruct the
maximum supply and every derived schedule. Exercise activation timing,
population changes, inactivity, accumulated permissions, cap exhaustion,
rounding, concentration, direct-channel abuse boundaries, insufficient
escrows, replay, overflow, and multi-year issuance.

Exit: every requirement in `first-goal.md` passes. No numerical rule becomes a
production C++ transition solely because it appears in the constitution.

All sixteen requirements now pass across six accepted contracts, ADRs 0017
through 0022, five verifiers, and the multi-year scenario suite. The accepted
account of what that does and does not establish is
[`founder-economy-report-v1.md`](founder-economy-report-v1.md). No numerical
rule became a C++ transition in this milestone.

## M3 — Founder Economy devnet — active

Specify canonical transactions and state, implement the accepted M2 economy in
C++, extend the independent Python model and fixed cross-language vectors, and
operate adversarial four-node economic scenarios through restart and recovery.

Exit: the devnet enforces the fixed cap and accepted Founder, commercial, fee,
and escrow accounting with deterministic replica agreement.

## M4 — Founder identity, seats, and authority

Specify permanent seat records, the 100,000-seat capacity, per-human limit,
manager history, external-payment proof interface, biometric decision
envelopes, sensitive-action authorization, inactivity, recovery, and legacy
succession.

Use a deterministic test verifier before production biometrics. Build the
camera verifier, evidence service, encrypted storage boundary, and threat model
as separate replaceable components.

Exit: a test Founder can enroll, activate a node, add a manager, exercise
eligible economic rights, recover an address, and complete tested legacy flows
without a wallet key alone rewriting identity.

## M5 — All-in-one Founder Node

Combine the full node, validator capability, resource agent, lifecycle,
updates, health, recovery, and migration into one supported Linux installation
and one operator-facing run experience. Define deterministic active-signer
selection and increasing minimum-requirement policy.

Exit: a clean supported Linux machine can install, enroll, start, stop,
restart, update, and recover one complete Founder service with documented
resource and network behavior.

## M6 — Ecosystem AI and native program control plane

Implement the company-hosted logical AI authority, policy and model manifests,
signed bounded decisions, biometric and moderation workflows, venture review,
milestones, tranche releases, community grants, developer incentives, audit
evidence, outage behavior, and staged delegation.

Exit: AI-managed workflows can operate against funded devnet escrows while
deterministic rules reject excess, stale, replayed, cross-capability, or
unfunded decisions. No Founder or community vote substitutes for AI judgment.

## M7 — Controlled application ecosystem

Specify and implement the approved application runtime, project and product
identity, one product-creator layer, spendable-element registration,
commercial routing, versioned updates, immutable history, capability limits,
and user-facing application discovery.

Exit: a creator can submit a project, receive a bounded milestone plan, deploy
an accepted full-stack test application, publish an approved update, sell a
native-asset item, and reproduce the constitutional revenue split.

## M8 — Founder resource network

Implement capability discovery, geographic placement, multi-node workload
composition, content addressing, storage replication, caching, load balancing,
cold backup, recovery, service evidence, and resource protections. Resources
serve approved ecosystem applications only.

Exit: approved applications remain available through node loss and regional
placement changes without every node storing or executing everything.

## M9 — Controlled bridge and liquidity

Specify and implement the BTC, ETH, and approved-stablecoin custody boundary;
Founder Seat purchase; native swaps; liquidity provision; withdrawals;
pricing; proofs; finality; expiry; refunds; insolvency handling; key recovery;
monitoring; and emergency containment.

Exit: independently audited testnet workflows complete or recover as one
user-level operation, while no foreign asset becomes a transferable internal
balance.

## M10 — Wallet and integrated public testnet

Deliver simple user, Founder, creator, developer, and company interfaces over
the complete testnet. Include wallet recovery, biometric Founder actions,
project and product flows, escrow visibility, AI decisions, node operations,
swaps, liquidity, and withdrawals without requiring blockchain terminology.

Exit: representative end-to-end journeys pass across supported environments,
the economic and authority models match the protocol, and every simulated or
centralized dependency is visibly identified.

## M11 — Production readiness and public launch

Complete independent security, cryptography, economic, biometric, consensus,
AI-control, bridge, reproducible-build, recovery, privacy, and operational
reviews. Run staged networks, incident exercises, upgrade rehearsals, load and
failure tests, and release reproducibility checks.

Exit: the integrated public-launch foundation in the Founder Constitution is
usable together, every mandatory review has a terminal result, all critical
findings are resolved, and no document describes a research stand-in as
production protection.

## M12 — Independent NodeOS and physical infrastructure

Build an immutable Linux-based NodeOS as a versioned program, then evaluate
and produce dedicated Founder machines. Pursue custom hardware and independent
connectivity only when measured requirements justify them.

Exit: Founder hardware is plug-and-run, reproducibly provisioned, remotely
observable without surrendering node custody, and compatible with the
protocol's versioned node interface.
