# Project charter

## Purpose

Develop an original, deterministic blockchain application and reference node
for a sovereign single-native-asset ecosystem.

## Current phase

The repository is establishing its specifications, engineering controls, and
first operational devnet. Nothing here is ready for production funds or
security claims.

## Current architectural defaults

- C++20 deterministic account-based ledger kernel.
- Native protocol modules for all root economics.
- Replaceable adapters for consensus, peer networking, storage, cryptography,
  and future execution environments.
- CometBFT is the proposed initial consensus and P2P adapter for the first
  devnet; it is not part of the sovereign state-transition rules.
- No Cosmos SDK dependency.
- No public contract deployment or EVM in the first milestone.
- A deterministic resource meter and fee path exist even when applications
  later sponsor user fees.
- Fees route to a native protocol fee pool rather than being implicitly burned.

## Constitutional invariants

These are intended to become protocol-level guarantees:

1. Exactly one protocol-native asset is recognized by the ledger.
2. Supply never exceeds the constitutional maximum.
3. Mint, treasury, escrow, staking, validator, and node-reward actions require
   explicit native capabilities.
4. Monetary arithmetic is integer-only and checked.
5. Identical ordered inputs produce identical state and state roots.
6. AI output is never consensus input unless converted into a signed,
   deterministic decision envelope accepted by native rules.
7. No single model process receives an unconstrained treasury, mint, upgrade,
   or bridge key.

Numerical supply, allocation, emission, reward, penalty, fee-split, and escrow
parameters are deliberately unresolved until specified, simulated, and
accepted.

## Native economic modules

The intended root module set includes:

- accounts and native transfers;
- supply and authorized issuance schedule;
- fee metering and fee-pool routing;
- treasury vaults, budgets, and disbursement constraints;
- immutable and policy-mediated escrows;
- validator registration, bonding, unbonding, rewards, and penalties;
- node-role registration and resource-distribution rewards;
- authority capabilities and signed decision envelopes;
- venture submissions, AI review decisions, milestone plans, evidence roots,
  and tranche-controlled venture escrows;
- protocol upgrades, timelocks, and emergency containment;
- bridge-facing lock/release capabilities if a bridge is later accepted.

Each module requires a specification, invariants, failure behavior, an
independent test model, and an accepted ADR before production implementation.

Venture acceptance, milestone approval, and funding are assigned to the future
AI authority rather than community or node-operator voting. Validators order
and verify accepted transactions; they do not substitute their judgment for a
valid AI venture decision.

## Non-goals for the first milestone

- Mainnet, public fundraising, or custody of real value.
- Complete tokenomics or final economic parameter selection.
- Public smart contracts, Solidity, EVM, or secondary assets.
- Staking-based validator admission.
- A production bridge, wallet, frontend, AI model, node OS, or hardware.
- A novel consensus algorithm.

## Safety position

Autonomous development can produce research software and a local devnet.
Mainnet readiness will require independent protocol, cryptographic, economic,
and implementation review. Passing automated tests is necessary but not
sufficient evidence for irreversible deployment.
