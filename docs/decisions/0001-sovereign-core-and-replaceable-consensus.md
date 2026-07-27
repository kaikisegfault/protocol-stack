# ADR 0001: Sovereign C++ core with replaceable consensus

- Status: Accepted
- Date: 2026-07-27

## Context

The project requires original control of ledger state, economics, and future
authority rules. Implementing deterministic state, Byzantine consensus, P2P,
sync, storage, and cryptography simultaneously would make early failures hard
to isolate and delay a functional devnet.

M1 needs a maintained Byzantine-fault-tolerant ordering and networking engine
without adopting another ecosystem's application framework or state model.
The integration must preserve the option to replace that engine without
migrating canonical account or economic state.

## Decision

Implement the canonical state-transition kernel and the owning persistent
application in C++20. Place consensus and P2P behind the versioned application
contract in `consensus-application-v1.md`.

Use CometBFT `v0.39.3` as the initial M1 ordering and networking adapter:

- tag and source commit:
  `49b82838fcca442b2445f76605c101609ed04130`;
- Go module:
  `github.com/cometbft/cometbft v0.39.3`;
- module checksum:
  `h1:UegHXskZNomsijmm29nL5NkeXtnzkme6fg+q1hPQnEI=`;
- module-file checksum:
  `h1:PmNfvtw256BC41ad0FABts236CSZnvZ0kjPOciBwTdM=`;
- ABCI protocol version: `2.0.0`;
- license: Apache-2.0; the inspected source license has SHA-256
  `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`.

Build the bridge with the official Linux x86-64 Go `1.25.10` archive,
`go1.25.10.linux-amd64.tar.gz`, pinned at SHA-256
`42d4f7a32316aa66591eca7e89867256057a4264451aca10570a715b3637ba70`.
Go modules and `go.sum` pin the complete transitive dependency graph. The
repository does not use Cosmos SDK.

The initial node consists of separate processes:

1. a headless C++ application owns `SQLiteLedger`, canonical admission,
   ordered execution, receipts, state roots, preview state, and durable commit;
2. a thin Go bridge implements the official CometBFT ABCI++ interface and
   translates it to the adapter-neutral local application protocol;
3. CometBFT owns block agreement, validator networking, its own block store,
   and its public transaction-broadcast and health RPCs.

The bridge uses no cgo, holds no canonical application state, and makes no
ledger decision. CometBFT, protobuf, Go, proposer, timestamp, validator, RPC,
and transport types remain outside the C++ kernel and storage APIs.

Use CometBFT's default mature P2P transport and ordinary queue mempool. Disable
the experimental libp2p transport, application mempool, vote extensions, state
sync, validator updates, consensus-parameter updates, and application
snapshots for M1.

## Compatibility and updates

The CometBFT project treats minor `0.x` releases as potentially breaking and
patch releases as its compatibility line. The node therefore accepts only
ABCI `2.0.0` and the pinned `v0.39.3` dependency.

A later `v0.39.z` patch may replace this pin only after its source identity,
module checksums, license, changelog, Go requirement, focused bridge tests, and
single-node restart integration pass. Any CometBFT minor release, ABCI version
change, P2P/block protocol change, result-field semantic change, or enabled
experimental subsystem requires an ADR amendment and a coordinated
compatibility plan. No dependency update may silently alter canonical
application results.

Removing CometBFT requires a replacement engine to reproduce the same
application lifecycle, ordered raw transaction input, committed height,
application hash, result mapping, and crash-recovery contract. Canonical
genesis, transaction, receipt, state, snapshot, and archive bytes do not
change merely because the adapter changes.

## Alternatives considered

### Malachite

Malachite provides a modular Rust BFT framework, but its public project
describes itself as alpha, under heavy development, and not externally
audited. Selecting it would add a second systems-language toolchain while
offering less operational maturity for the immediate M1 devnet.

### Original C++ consensus and P2P

An original engine maximizes infrastructure sovereignty, but building and
hardening consensus, peer networking, block sync, evidence handling, and
operations now would delay the nearest runnable vertical. It remains the M6
evaluation path after application semantics and network operations are proven.

### Direct C++ ABCI socket implementation

Implementing CometBFT protobuf and socket details directly in C++ would spread
adapter types and a large generated-code dependency surface into the reference
node. A narrow out-of-process bridge is smaller, easier to replace, and keeps
the C++ application protocol independent from ABCI.

### In-process Go application or cgo wrapper

Making Go own application state, or calling the C++ kernel through cgo, would
couple lifecycle and failure containment to the adapter. A separate C++ owner
preserves exclusive SQLite ownership and permits each process boundary to be
tested and replaced independently.

## Consequences

- The ecosystem owns monetary, execution, receipt, persistence, and
  application-hash semantics immediately.
- A functional BFT devnet is reachable before an original consensus engine.
- The first node includes a pinned Go infrastructure dependency and a local
  process protocol.
- Finalize and Commit must be split into deterministic non-durable preview and
  exact durable publication.
- Cross-process framing, disconnect, duplicate, replay, and restart behavior
  require dedicated negative and fuzz coverage.
- State sync and validator-set changes are deliberately unavailable in the M1
  application boundary.

## Evidence for acceptance

The selection was checked against the official CometBFT `v0.39.3` source,
release process, changelog, ABCI++ specification, application interface,
socket-server serialization, module manifest, and license. The selected patch
includes the prior `v0.39.2` ABCI socket panic-recovery fix and height
validation. The official Go download manifest provides the pinned toolchain
digest, and the public Go checksum database provides both module checksums.

The adapter-neutral lifecycle, exact result mapping, resource bounds,
durability boundary, replay rules, unsupported features, and required
verification are normative in `consensus-application-v1.md`. This evidence
satisfies the original acceptance condition; implementation remains subject to
the tests and hosted gates defined there.

## Research references

- [CometBFT v0.39.3 release](https://github.com/cometbft/cometbft/releases/tag/v0.39.3)
- [CometBFT release policy](https://github.com/cometbft/cometbft/blob/v0.39.3/RELEASES.md)
- [CometBFT v0.39.3 changelog](https://github.com/cometbft/cometbft/blob/v0.39.3/CHANGELOG.md)
- [ABCI++ application requirements](https://github.com/cometbft/cometbft/blob/v0.39.3/spec/abci/abci%2B%2B_app_requirements.md)
- [ABCI++ expected behavior](https://github.com/cometbft/cometbft/blob/v0.39.3/spec/abci/abci%2B%2B_comet_expected_behavior.md)
- [Official Go downloads](https://go.dev/dl/)
- [Malachite project status](https://github.com/circlefin/malachite)
