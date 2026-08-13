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

Exit: every requirement in
[`goals/m2-founder-economy-proof.md`](goals/m2-founder-economy-proof.md)
passes. No numerical rule becomes a production C++ transition solely because it
appears in the constitution.

All sixteen requirements passed across six accepted contracts, ADRs 0017
through 0022, five verifiers, and the multi-year scenario suite. The accepted
account of what that does and does not establish is
[`founder-economy-report-v1.md`](founder-economy-report-v1.md). No numerical
rule became a C++ transition in this milestone.

The founder direction those contracts encode was revised on 2026-08-07 by ADR
0023. The M2 evidence stands as proof about `founder-economy-manifest-v1`; the
revised contract is M3 work.

## M3 — Founder Economy devnet — active

Restate the economy contract under the revised direction, specify canonical
transactions and state, implement it in C++, extend the independent Python
model and fixed cross-language vectors, and operate adversarial four-node
economic scenarios through restart and recovery.

### M3.1 Revised economic contract — accepted

Accept `founder-economy-manifest-v2`: the 56,993,950,100 maximum, the referral
channel doubled and relocated to direct-mint, and the unreferred performance
pool. Delivered by ADR 0024 with a specification, manifest, digest, 154
vectors, a strict loader, and a verifier whose independence is a hand-restated
Founder Constitution. Version one is retained unedited as the M2 evidence.

### M3.2 Revised simulator — delivered

Revise the independent Python model so the referral is an unconditional
direct-mint accrual and so activity and performance reallocation are derived
rules rather than supplied research inputs. `evaluate_referral_permission`, its
`inactive_referral_result` input, and the permission `kind` discriminator
disappear; the unreferred performance pool becomes a beneficiary. Regenerate
every dependent model, vector, and digest.

### M3.3 Consensus encoding and cycle boundary — delivered

Define the eligible cycle in chain heights or epochs, the canonical state keys,
the transaction encodings, the numeric receipt codes, and the compatibility
boundary against accepted M1 bytes.

`cycle-boundary-v1` delivers the first half and `founder-economy-simulator-v3`
enforces it. `economy-transition-v2` delivers the second: a shared transaction
envelope whose kind-1 instance reproduces the accepted M1 transfer
byte-for-byte, five new kinds, the economy state key space, version-two genesis
and chain identity, the state-root extension, a 56-byte receipt, and a flat
result-code space whose first nine are version one's frozen meanings.

It is a contract, not an implementation. The two authorization predicates it
first left undefined were settled by the founder on 2026-08-13 and are encoded:
a seat is purchased and activated under an off-chain biometric verifier
signature, the chain assigns mint permissions daily by itself, and a mint takes
everything. Only direct-channel eligibility remains reserved, and it refuses one
transaction kind rather than blocking the milestone.

### M3.4 Uptime derivation — delivered

Derive validator duties from on-chain participation, prove resource provision
by challenge-response, and bound the AI dispute window so its expiry finalises
a cycle without a signature.

### M3.5 C++ implementation and devnet

Implement the accepted contract in the deterministic ledger kernel with
cross-language vectors, then operate adversarial four-node scenarios through
restart and recovery.

Take it in two pieces. The pure codec — the envelope and its six bodies, the
receipt, the state keys, the trees, the roots, and genesis — is deterministic
byte work against `test-vectors/economy-transition-v2.txt`. The transitions
follow: purchase, activation, the block-boundary cycle assignment, and the two
mints.

Exit: every requirement in [`first-goal.md`](first-goal.md) passes and the
devnet enforces the fixed cap and accepted Founder, referral, commercial, fee,
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
