# ADR 0001: Sovereign C++ core with replaceable consensus

- Status: Accepted
- Date: 2026-07-27
- Last amended: 2026-07-29

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

Use CometBFT `v0.39.4` as the initial M1 ordering and networking adapter:

- tag and source commit:
  `f96ff7cc244bfa97f399527d917f22ad81414d25`;
- Go module:
  `github.com/cometbft/cometbft v0.39.4`;
- module checksum:
  `h1:Bm7xbN18VfNueEd7cZumACbvVE+Lf9N58sz3oBOVPbw=`;
- module-file checksum:
  `h1:KcZvZTqdLgOisktAoWwwcS2fgO4E110r44KxEGyq8SI=`;
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

The repository builds a narrow node wrapper around CometBFT's official
`DefaultNewNode` start path. Its version command reports the accepted module
pin, and the built binary's Go metadata remains authoritative for dependency
identity and must contain `github.com/cometbft/cometbft v0.39.4`.

The M1 operational network contains exactly four validator replicas. Each
replica owns a distinct CometBFT node key, private-validator key and signing
state, stateless ABCI bridge, C++ application process, and SQLite database.
All four share one byte-identical CometBFT genesis containing the validators in
node-index order with equal voting power `10`. No replica shares application
state or private key material with another.

The local topology is a complete static loopback mesh. Every node lists the
other three node IDs as persistent peers in node-index order, PEX remains
disabled, duplicate loopback IPs are explicitly allowed, and the experimental
libp2p transport remains disabled. The default node-indexed ports are:

| Node | P2P | RPC | ABCI |
| ---: | ---: | ---: | ---: |
| `0` | `27656` | `27657` | `27658` |
| `1` | `27666` | `27667` | `27668` |
| `2` | `27676` | `27677` | `27678` |
| `3` | `27686` | `27687` | `27688` |

An alternate base P2P port may move the whole test topology without changing
its relative layout. Ports, peers, validator keys, process timing, and
CometBFT metadata remain adapter-only deployment data and never enter
canonical application state.

One foreground supervisor initializes or exact-validates all four homes before
starting any long-running child. It starts all applications, then all bridges,
then all CometBFT nodes, waits for each phase to become ready, and terminates
the complete network if any child exits unexpectedly. SIGINT or SIGTERM stops
nodes, bridges, and applications in reverse phase order. Restart reuses the
same four homes and databases and reconciles every replica through ABCI Info.

## Compatibility and updates

The CometBFT project treats minor `0.x` releases as potentially breaking and
patch releases as its compatibility line. The node therefore accepts only
ABCI `2.0.0` and the pinned `v0.39.4` dependency.

A later `v0.39.z` patch may replace this pin only after its source identity,
module checksums, license, changelog, Go requirement, focused bridge tests, and
single-node restart integration pass. Any CometBFT minor release, ABCI version
change, P2P/block protocol change, result-field semantic change, or enabled
experimental subsystem requires an ADR amendment and a coordinated
compatibility plan. No dependency update may silently alter canonical
application results.

Building the official full-node path compiles its dependency closure,
including alternate database and disabled experimental transport
implementations. Their presence in the module graph does not enable those
features: the accepted initializer requires the flood mempool and writes
`p2p.libp2p.enabled = false`. Security alerts nevertheless apply to every
compiled dependency and must be zero before the node candidate merges.

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
and keeps ABCI `2.0.0` unchanged. Go's minimum-version
selection also raises the supporting `x/sys`, `x/text`, Google RPC, and
OpenTelemetry modules recorded in the checked-in module graph. Every selected
module declares compatibility with Go 1.25.

The full-node graph selects `go-libp2p v0.49.0`, Pion DTLS `v3.1.2`,
`quic-go v0.60.0`, and `webtransport-go v0.11.1`. The last two are at or above
the first patched versions for GHSA-vvgj-x9jq-8cj9 and
GHSA-g35j-m5xg-vh3q.
CometBFT `v0.39.4` retains an unused manifest edge to unpatched
`github.com/pion/dtls/v2 v2.2.12`. The root module replaces that path with an
intentionally empty local module. Hosted resolution requires that exact
replacement and proves the node package closure imports no DTLS v2 package;
any future import fails compilation because the replacement contains no code.
The experimental libp2p runtime remains disabled.

Removing CometBFT requires a replacement engine to reproduce the same
application lifecycle, ordered raw transaction input, committed height,
application hash, result mapping, and crash-recovery contract. Canonical
genesis, transaction, receipt, state, snapshot, and archive bytes do not
change merely because the adapter changes.

CometBFT block header `H` contains the application hash produced after height
`H - 1`; consequently `/status` reports that historical header value. ABCI
Info, exposed through `/abci_info`, reports the current durable C++ height and
root. This one-height presentation difference is verified by integration and
does not alter either application hash.

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

### Upstream generic testnet generator

CometBFT's `testnet` command can generate validator homes and persistent-peer
configuration. It is deliberately generic, however, and does not derive the
protocol chain ID and height-zero application root from the C++ canonical
genesis, enforce this repository's disabled-feature profile, or provision one
independent C++ application and bridge per validator. A narrow initializer
using the same accepted CometBFT key and genesis types preserves those checks
without adding another configuration authority.

### Seed discovery or PEX

A seed node with PEX would reduce the explicit peer list, but would re-enable a
subsystem intentionally disabled for M1 and make readiness depend on discovery
convergence. The four-node test network is small enough that explicit
persistent peers are simpler to inspect and reproduce.

### Ring or partial static topology

A ring uses fewer connections and can still connect all validators, but a
single missing edge can partition or delay the smallest BFT network. Six
undirected loopback connections are negligible, and the full mesh makes the
health requirement exact: every validator directly observes the other three.

### Shared application process

Four consensus processes could share one application and database, but that
would not prove deterministic replicated execution or independent recovery.
Separate application owners are required so equal roots are evidence rather
than a consequence of shared memory or storage.

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
- A local four-validator run owns twelve long-running child processes and four
  independent durable ledgers; foreground supervision and bounded teardown are
  part of the tested operational contract.
- Complete-mesh loopback topology is an M1 operational default, not a
  production network architecture or validator-admission policy.

## Evidence for acceptance

The initial selection was checked against the official CometBFT `v0.39.3`
source, release process, changelog, ABCI++ specification, application
interface, socket-server serialization, module manifest, and license. The
official Go download manifest provides the pinned toolchain digest, and the
public Go checksum database provides module checksums.

On 2026-07-28, `v0.39.4` replaced the initial patch after inspection of its
signed tag, exact source commit, release notes, changelog delta, module
manifest, Go `1.25.0` requirement, and unchanged license digest. The patch
retains ABCI `2.0.0`, P2P protocol `8`, and block protocol `11`, and includes
ABCI deadlock, blocksync validation, mempool amplification/race, consensus
locking/double-sign, node cleanup, and quic advisory fixes. Its module and
module-file checksums are committed above.

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

The single-node implementation derives protocol chain and height-zero root
identities through the C++ kernel, initializes an exact fixed-time CometBFT
genesis, starts the official node path, commits a signed transfer, stops all
three processes, repeats strict initialization, reconciles through Info, and
commits the next height. The integration independently compares ABCI results,
the current `/abci_info` root, the one-height-lagged `/status` header hash, and
the durable C++ root.

For the four-validator amendment, the accepted `v0.39.4` configuration source
was inspected for persistent-peer, duplicate-IP, PEX, and libp2p behavior; the
accepted genesis and upstream testnet-generator sources were inspected for
validator-set validation, key generation, common-genesis construction, and
peer population. CometBFT's operator documentation confirms that four
validators are the minimum set that can tolerate one validator failure and
documents the `nodeID@host:port` persistent-peer form. Static full mesh was
selected over the alternatives above because it retains the existing
fail-closed feature profile and gives the smallest local network an exact,
directly observable readiness condition.

The hosted resolver run 30385565279 used the public checksum database, removed
the DTLS v2 code path, verified the empty replacement, proved the node package
closure contains no DTLS v2 package, and passed all Go tests, vet, and the
cgo-free node build. GitHub's branch dependency comparison then reported zero
vulnerabilities across the resolved `go.mod` delta.

## Research references

- [CometBFT v0.39.4 release](https://github.com/cometbft/cometbft/releases/tag/v0.39.4)
- [CometBFT release policy](https://github.com/cometbft/cometbft/blob/v0.39.4/RELEASES.md)
- [CometBFT v0.39.4 changelog](https://github.com/cometbft/cometbft/blob/v0.39.4/CHANGELOG.md)
- [ABCI++ application requirements](https://github.com/cometbft/cometbft/blob/v0.39.4/spec/abci/abci%2B%2B_app_requirements.md)
- [ABCI++ expected behavior](https://github.com/cometbft/cometbft/blob/v0.39.4/spec/abci/abci%2B%2B_comet_expected_behavior.md)
- [CometBFT v0.39.4 configuration source](https://github.com/cometbft/cometbft/blob/v0.39.4/config/config.go)
- [CometBFT v0.39.4 genesis validation](https://github.com/cometbft/cometbft/blob/v0.39.4/types/genesis.go)
- [CometBFT v0.39.4 testnet generator](https://github.com/cometbft/cometbft/blob/v0.39.4/cmd/cometbft/commands/testnet.go)
- [CometBFT validator-network operator guidance](https://docs.cometbft.com/v0.38/core/using-cometbft)
- [Official Go downloads](https://go.dev/dl/)
- [Go module version selection](https://go.dev/ref/mod#minimal-version-selection)
- [Pion DTLS advisory GHSA-9f3f-wv7r-qc8r](https://github.com/advisories/GHSA-9f3f-wv7r-qc8r)
- [quic-go advisory GHSA-vvgj-x9jq-8cj9](https://github.com/advisories/GHSA-vvgj-x9jq-8cj9)
- [webtransport-go advisory GHSA-g35j-m5xg-vh3q](https://github.com/advisories/GHSA-g35j-m5xg-vh3q)
- [x/crypto advisory GHSA-f5wc-c3c7-36mc](https://github.com/advisories/GHSA-f5wc-c3c7-36mc)
- [gRPC advisory GHSA-p77j-4mvh-x3m3](https://github.com/advisories/GHSA-p77j-4mvh-x3m3)
- [gRPC advisory GHSA-hrxh-6v49-42gf](https://github.com/advisories/GHSA-hrxh-6v49-42gf)
- [x/net advisory GHSA-5cv4-jp36-h3mw](https://github.com/advisories/GHSA-5cv4-jp36-h3mw)
- [Malachite project status](https://github.com/circlefin/malachite)
