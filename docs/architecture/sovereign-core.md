# Sovereign core architecture

## Design rule

Own consensus-critical meaning; isolate replaceable mechanisms.

The protocol kernel defines which ordered inputs are valid and what exact state
results. Consensus, storage, networking, model serving, and operating systems
may change without changing that meaning.

## Layers

### Protocol specification

Canonical definitions for types, encoding, hashing, state transition,
economics, authority, compatibility, and failure behavior.

Specifications precede consensus-critical implementation.

### Deterministic C++ kernel

The kernel owns:

- canonical decoding and validation;
- accounts, balances, nonces, and supply;
- transaction and block execution;
- native economic modules;
- capability and authority checks;
- state roots and deterministic receipts.

It accepts ordered inputs and produces deterministic outputs. It does not own
peer discovery, block agreement, model inference, wall-clock policy, or
hardware management.

### Replaceable adapters

Adapters connect the kernel to:

- cryptographic providers;
- persistent stores;
- consensus and P2P engines;
- RPC and administrative processes;
- future application runtimes;
- AI decision and compute networks.

Adapter-specific data cannot silently enter canonical state. Consensus-visible
behavior requires a specification.

### Reference node

The reference node composes the kernel and adapters into a headless process,
adds lifecycle and observability, and exposes narrowly scoped interfaces.

### Independent reference model

Python independently implements the state-transition specification for
differential and economic testing. It must not call the C++ implementation for
the behavior it is intended to verify.

## Initial consensus boundary

CometBFT is proposed for the first devnet because it can order transactions and
replicate an external application without owning that application's state
transition. The C++ kernel remains the authoritative application.

The adapter must not leak CometBFT-specific types into kernel modules. A future
consensus engine should be replaceable without migrating account or economic
state merely because transport changed.

## Determinism boundary

Consensus state must not depend on:

- floating-point arithmetic;
- locale, wall-clock time, filesystem ordering, or thread scheduling;
- database iteration unless order is explicitly canonicalized;
- undefined or implementation-defined C++ behavior;
- external APIs, DNS, model inference, or mutable remote data;
- platform-native serialization or unversioned schemas.

## Scale boundary

The validator set is distinct from the broader resource-node population.
Validator consensus remains bounded. Storage, inference, training, gateways,
and other workloads scale through separate protocols and do not participate in
every block vote.
