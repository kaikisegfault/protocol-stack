# ADR 0001: Sovereign C++ core with replaceable consensus

- Status: Proposed
- Date: 2026-07-23

## Context

The project requires original control of ledger state, economics, and future
authority rules. Implementing deterministic state, Byzantine consensus, P2P,
sync, storage, and cryptography simultaneously would make early failures hard
to isolate and delay a functional devnet.

## Decision

Implement the canonical state-transition kernel in C++20. Keep consensus and
P2P behind an adapter. Use an external CometBFT process as the proposed initial
M1 adapter without using Cosmos SDK.

The kernel owns no CometBFT types or semantics beyond a narrow versioned
boundary. Replacing the adapter must not require changing canonical ledger
state.

## Consequences

- The ecosystem owns its monetary and execution semantics immediately.
- A functional BFT devnet is reachable before an original consensus engine.
- The first node includes a replaceable Go infrastructure dependency.
- Adapter correctness and cross-process handling require dedicated tests.
- Independent C++ consensus remains a later strategic milestone.

## Acceptance

The owner must explicitly accept this record before the M1 consensus adapter is
implemented.
