# Roadmap

Milestones are ordered by dependency. Dates are intentionally omitted until the
specifications and measured delivery velocity exist.

## F0 — Agent and project foundation

Establish repository instructions, durable continuation state, architecture
boundaries, ADRs, repository skills, engineering standards, and authorship
rules.

Exit: a clean Codex session can read the repository, identify the active goal,
and select the exact next action from `current-state.md`.

## M1 — Sovereign Devnet Alpha

1. Specify protocol primitives and select the cryptographic, hashing, address,
   and canonical encoding suite.
2. Bootstrap reproducible C++20 and Python verification toolchains.
3. Implement and cross-check the deterministic in-memory ledger kernel.
4. Add persistent atomic state, replay, snapshots, and recovery tests.
5. Integrate a replaceable CometBFT ABCI adapter.
6. Operate and harden a four-validator local devnet.

Exit: every requirement in `first-goal.md` passes.

## M2 — Native economy specification and simulator

Specify the complete native module set for supply, allocation, fees, treasury,
escrow, staking, validator lifecycle, node roles, rewards, penalties,
timelocks, upgrades, and emergency containment.

Build an independent economic simulator before freezing numerical parameters.
No production economic parameter becomes immutable solely because it appeared
in an early implementation.

## M3 — Native economy devnet

Implement accepted M2 modules in C++, extend the independent Python model, and
operate adversarial multi-node economic scenarios.

## M4 — AI authority control plane

Implement venture submission review, signed decisions, model and policy
manifests, bounded treasury budgets, native venture escrows, milestone evidence
review, funding tranche release, audit evidence, threshold authorization, and
small-model verifiers. Community members and node operators do not vote on
venture decisions. AI remains outside consensus.

## M5 — Resource and AI compute network

Add node-role registration, capability discovery, workload scheduling,
attestation where justified, rewards, penalties, model distribution, and
high-bandwidth inference-cluster support.

## M6 — Independent node infrastructure

Evaluate and, if strategically justified, replace initial consensus/P2P
infrastructure with an independently implemented C++ engine. Build an
immutable Linux-based NodeOS distribution as a separate project.

## M7 — Controlled external swap bridge

Design a narrowly scoped native-asset swap boundary. Foreign assets do not
become general-purpose wrapped assets inside the protocol. Bridge work requires
its own threat model and independent audits.

## Production gate

No mainnet until independent security, cryptography, economic, consensus,
reproducible-build, recovery, and operational reviews are complete.
