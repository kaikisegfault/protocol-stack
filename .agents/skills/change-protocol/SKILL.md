---
name: change-protocol
description: Design or implement consensus-visible changes in protocol-stack, including canonical types or encoding, cryptography, state transitions, tokenomics, fees, staking, escrow, treasury, validators, node rewards, AI authority, upgrades, bridges, and compatibility. Use before modifying behavior that independent nodes must reproduce exactly.
---

# Change the protocol

## Establish the contract

1. Read the charter, relevant accepted ADRs, current specification, and current
   state.
2. Classify the change: primitive, encoding, validation, state transition,
   economics, authority, compatibility, or adapter-only.
3. Confirm whether an owner gate in `AGENTS.md` applies. Research and present a
   recommended default before asking.
4. Write or update the canonical specification before implementation.

The specification must define:

- canonical input and byte representation;
- validity, authorization, and rejection conditions;
- numeric ranges and overflow behavior;
- exact state reads and writes;
- atomicity and failure semantics;
- replay behavior and resource limits;
- receipts, errors, and state-root effects;
- versioning, compatibility, and migration;
- positive, negative, boundary, and adversarial vectors.

## Protect invariants

State every affected invariant explicitly. At minimum consider:

- one-native-asset and supply conservation;
- authorization and capability containment;
- nonce and replay safety;
- deterministic ordering and execution;
- failed-transition atomicity;
- treasury, general escrow, and venture escrow conservation;
- milestone and funding-tranche ceilings;
- validator and node-reward accounting;
- AI budget, threshold, timelock, and expiry limits.

Never implement cryptographic primitives. Never use model inference, wall-clock
data, floating point, database-native ordering, or mutable external data in
canonical execution.

## Implement and verify

1. Keep the kernel independent from consensus, database, and transport types.
2. Add or update the independent Python model when behavior is
   consensus-visible.
3. Add fixed cross-language vectors and property tests before relying on
   randomized tests.
4. Add decoder or validator fuzz coverage for new untrusted input.
5. Run `verify-project`, inspect the diff, and confirm documentation matches
   implementation.
6. Commit the independently complete, verified change and record any
   compatibility effect in the current handoff.

Do not label an economic rule immutable until its specification, simulation,
failure modes, and owner acceptance are recorded.
