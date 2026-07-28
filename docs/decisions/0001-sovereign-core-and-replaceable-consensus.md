# ADR 0001: Sovereign C++ core with replaceable consensus

- Status: Accepted
- Date: 2026-07-27
- Last amended: 2026-07-28

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

Security maintenance may raise a transitive module above the version selected
by CometBFT without changing the CometBFT pin. Such an override must select at
least the first patched version from the applicable published advisory, remain
compatible with the pinned Go toolchain, preserve the ABCI surface, record the
resolved graph in `go.mod` and `go.sum`, and pass the focused bridge suite plus
the complete hosted compiler and sanitizer matrix.

The initial bridge graph applies that rule to modules reached through the
official CometBFT packages:

- `golang.org/x/crypto v0.52.0`, reached through CometBFT cryptography;
- `golang.org/x/net v0.55.0`, reached through the gRPC package compiled by the
  official ABCI server package;
- `google.golang.org/grpc v1.82.1`, compiled by that ABCI server package.

These are dependency security floors, not new application capabilities. The
bridge still selects the socket server at runtime, exposes no gRPC listener,
and keeps CometBFT `v0.39.3` and ABCI `2.0.0` unchanged. Go's minimum-version
selection also raises the supporting `x/sys`, `x/text`, Google RPC, and
OpenTelemetry modules recorded in the checked-in module graph. Every selected
module declares compatibility with Go 1.25.

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

On 2026-07-28, repository dependency alerts identified patched floors of
`v0.52.0` for `x/crypto`, `v0.55.0` for `x/net`, and `v1.82.1` for gRPC. Module
path analysis confirmed that all three enter the bridge graph through the
official CometBFT packages described above. Applying the fixed floors with the
pinned Go resolver retained CometBFT `v0.39.3`, ABCI `2.0.0`, and the socket
runtime while producing the committed checksums in `go.sum`. The `x/crypto`
alert set was GHSA-9m57-25v3-79x9, GHSA-f5wc-c3c7-36mc,
GHSA-jppx-rxg9-jmrx, GHSA-x527-x647-q7gg, GHSA-5cgq-3rg8-m6cv,
GHSA-rm3j-f69w-wqmq, GHSA-89gr-r52h-f8rx, GHSA-w879-237q-wc7r,
GHSA-vgwf-h737-ff37, GHSA-qpw4-5x99-6vjp, GHSA-78mq-xcr3-xm33,
GHSA-45gg-vh54-h5m9, and GHSA-q4h4-gmj2-qvw2.

## Research references

- [CometBFT v0.39.3 release](https://github.com/cometbft/cometbft/releases/tag/v0.39.3)
- [CometBFT release policy](https://github.com/cometbft/cometbft/blob/v0.39.3/RELEASES.md)
- [CometBFT v0.39.3 changelog](https://github.com/cometbft/cometbft/blob/v0.39.3/CHANGELOG.md)
- [ABCI++ application requirements](https://github.com/cometbft/cometbft/blob/v0.39.3/spec/abci/abci%2B%2B_app_requirements.md)
- [ABCI++ expected behavior](https://github.com/cometbft/cometbft/blob/v0.39.3/spec/abci/abci%2B%2B_comet_expected_behavior.md)
- [Official Go downloads](https://go.dev/dl/)
- [Go module version selection](https://go.dev/ref/mod#minimal-version-selection)
- [x/crypto advisory GHSA-f5wc-c3c7-36mc](https://github.com/advisories/GHSA-f5wc-c3c7-36mc)
- [gRPC advisory GHSA-p77j-4mvh-x3m3](https://github.com/advisories/GHSA-p77j-4mvh-x3m3)
- [gRPC advisory GHSA-hrxh-6v49-42gf](https://github.com/advisories/GHSA-hrxh-6v49-42gf)
- [x/net advisory GHSA-5cv4-jp36-h3mw](https://github.com/advisories/GHSA-5cv4-jp36-h3mw)
- [Malachite project status](https://github.com/circlefin/malachite)
