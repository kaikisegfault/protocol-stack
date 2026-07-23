# Vision

## North star

Create a sovereign digital ecosystem whose economic and technical foundation
is owned end to end:

- one blockchain-native economic unit;
- deterministic, auditable protocol rules;
- native staking, escrow, treasury, fee, validator, and node-distribution
  mechanisms;
- an independent node and resource network;
- a self-hosted AI authority operating within protocol-enforced limits;
- dedicated node software and, later, an immutable node operating system;
- long-term paths toward dedicated devices, open hardware, and independent
  connectivity.

This is a direction, not a claim that every layer belongs in the first
implementation or this repository.

## Meaning of sovereignty

Sovereignty means owning:

- the canonical protocol specification and state-transition function;
- monetary and authority invariants;
- upgrade, recovery, and compatibility rules;
- reproducible builds and release policy;
- interfaces to consensus, storage, networking, AI, and hardware;
- the ability to replace infrastructure without rewriting economic state.

It does not require inventing cryptography, databases, compilers, operating
system kernels, or consensus algorithms before the protocol kernel is proven.

## Economic direction

The chain recognizes exactly one protocol-native asset. It provides no public
asset-issuance operation. Core economics are implemented as native protocol
modules rather than publicly deployed contracts.

The immutable layer should contain constitutional invariants such as
single-asset status, supply bounds, authorization limits, and deterministic
accounting. Exact allocations, emissions, reward curves, and penalty values
must be simulated and tested before they are frozen.

## AI direction

The target is a locally hosted, ecosystem-specific AI authority rather than a
permanent dependency on an enterprise model API.

The AI control plane may eventually review submitted ventures, accept or reject
them, allocate bounded treasury budgets, create venture escrows, review
delivery milestones, release funding tranches, pause or terminate funding, and
coordinate resources. Community members and node operators do not vote on
these venture decisions.

AI never becomes part of the consensus computation. Deterministic protocol
rules validate every signed AI decision and prevent actions outside its
capabilities, budgets, escrow balance, policy version, and time window.

The logical authority may be singular while its implementation is a threshold
of independently operated models and keys.

## Scale direction

A future network may contain 100,000 or more participating machines, but they
will not all vote on each block. Roles will include validators, full nodes,
light clients, storage providers, AI compute providers, gateways, and other
resource nodes.

Large-model inference will run on high-bandwidth compute clusters. Ordinary
nodes may host smaller specialized models, policy verifiers, replicated model
artifacts, or independent decision auditors.

## Program boundaries

`protocol-stack` owns protocol specifications, the ledger kernel, reference
node, adapters, protocol tests, and operational tooling.

Future node OS, hardware, chip, satellite, and manufacturing programs should
be separate projects with versioned interfaces to this protocol. They should
not turn this monorepo into an unbounded collection of unrelated systems.
