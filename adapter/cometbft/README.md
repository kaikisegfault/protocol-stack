# CometBFT node adapter

This Go module contains the replaceable adapter between CometBFT `v0.39.4`
and the headless C++ application. It implements the accepted version-one
contract in
[`consensus-application-v1.md`](../../docs/specifications/consensus-application-v1.md),
and, under `-protocol-version 8`, the version-eight responses recorded in
[ADR 0068](../../docs/decisions/0068-the-version-eight-application-layer.md) and
[ADR 0069](../../docs/decisions/0069-the-version-eight-node-process-and-adapter.md).

Under `-protocol-version 9` it implements
[`consensus-application-v2.md`](../../docs/specifications/consensus-application-v2.md):
local frame version 2, a timestamp on `ProcessProposal`, `FinalizeBlock`, and
`InitChain`, the protobuf-to-millisecond conversion, the eight-value proposal
decision, and the fifth derived genesis value, as
[ADR 0086](../../docs/decisions/0086-the-go-local-client-speaks-the-version-two-frame.md),
[ADR 0087](../../docs/decisions/0087-the-bridge-carries-the-engines-time.md), and
[ADR 0088](../../docs/decisions/0088-the-launcher-derives-the-genesis-time-and-the-first-block-carries-it.md)
record. **Version nine has not yet run on a network**; the devnet evidence the
contract lists is still owed. Versions one and eight both use frame version 1,
although version eight's finalized-block payload differs from version one's, so
a mismatched pair between them is refused at the result count rather than at the
frame header. That is a drift
[ADR 0079](../../docs/decisions/0079-the-version-nine-application-contract.md)
records and version two closes by moving the version field.

The module provides four cgo-free commands:

- `protocol-cometbft-bridge`, the stateless ABCI++ socket bridge;
- `protocol-cometbft-devnet`, the strict four-replica initializer, foreground
  supervisor, health checker, transaction submitter, and single-replica stop
  and start control;
- `protocol-cometbft-init`, the strict single-node home initializer;
- `protocol-cometbft-node`, the pinned CometBFT node process.

The adapter:

- serves the official CometBFT ABCI `2.0.0` socket interface;
- serializes all supported calls onto one persistent local Unix connection;
- translates only the seven application methods and their exact result fields;
- reads a version-seven finalized block with the same frames and one different
  decoder, and refuses each version's finalized block under the other, so a
  client started at the wrong version fails closed rather than misreading a
  block;
- refuses to forward a `FinalizeBlock` at a height the application has already
  committed, using a height taken only from the application's own answers;
- fails unsupported application-mempool and state-sync operations closed;
- holds no canonical ledger state and makes no admission or execution
  decision;
- uses no cgo or Cosmos SDK;
- fixes the CometBFT genesis time, initial height, application identity,
  validator, and supported M1 configuration, with the genesis application state
  naming the ledger version so that a mismatched pair is refused at `InitChain`
  rather than at the first block;
- refuses to overwrite an existing genesis with different semantics.

The repository verifier bootstraps the integrity-pinned Go 1.25.10 Linux
x86-64 toolchain, verifies `go.sum`, tests and vets all packages, builds all
four commands with cgo disabled, and runs the real single-node compatibility
and four-validator restart integrations:

```sh
tools/verify.sh
```

For a focused bridge check after bootstrapping the toolchain:

```sh
cd adapter/cometbft
GOTOOLCHAIN=local CGO_ENABLED=0 \
  ../../.cache/go1.25.10/bin/go test ./...
```

## Four-validator lifecycle

From a clean clone on supported Linux x86-64, the repository wrapper builds
only the missing pinned runtime binaries, decodes the public synthetic genesis,
strictly initializes four independent homes, and remains in the foreground
while supervising all twelve children:

```sh
tools/devnet.sh start
```

The first build downloads the pinned CMake, Ninja, Go, libsodium, SQLite, and
Go-module inputs into ignored local caches. The persistent default network is
under `.local/devnet`; its generated unencrypted validator keys are for local
development only. Application sockets use a deterministic short owner-only
directory below the platform temporary directory and are removed after orderly
shutdown.

In another terminal, require four healthy RPCs, a complete three-peer view at
every validator, no catching-up replica, one equal-power validator set, and
identical CometBFT, ABCI, and application heads:

```sh
tools/devnet.sh health
```

Submit caller-supplied exact transaction bytes by naming a hexadecimal file.
The command does not sign or rewrite them. The bundled first transaction uses
nonce `1` against the bundled genesis:

```sh
tools/devnet.sh transaction examples/devnet/transaction-1.hex
```

Press Ctrl-C in the start terminal. The supervisor stops all CometBFT nodes,
then bridges, then applications, and preserves every home and database. Start
again with the same command in that foreground terminal. In another terminal,
confirm health at the retained height and root, then submit the nonce-`2`
fixture through validator `1`:

```sh
tools/devnet.sh health
tools/devnet.sh transaction examples/devnet/transaction-2.hex 1
```

### Taking one replica down while the others keep committing

The supervisor listens on a control socket in the socket root, so one replica
can leave a running network and come back to it. Both commands answer as soon
as the supervisor has done the work; neither waits for the network to agree
again.

```sh
tools/devnet.sh stop-replica 3
tools/devnet.sh start-replica 3
```

**A replica is its three processes**, so a stop takes the CometBFT node, the
bridge, and the application, in that order, and a start brings them back in the
reverse one. Three of four validators still hold more than two thirds of the
voting power, so the network keeps committing; taking two down halts it.

While a replica is down, `health` and `transaction` must be told which replicas
are expected to be running, because both otherwise require all four to have
converged:

```sh
tools/devnet.sh health 0,1,2
tools/devnet.sh transaction examples/devnet/transaction-2.hex 1 0,1,2
```

**`-nodes` names the replicas expected to run, not the ones to look at.** Every
replica named must be up and converged, and every replica *not* named must be
absent from the others' peer sets — so a replica that was supposed to be
stopped and is still gossiping fails the observation. What does not narrow is
the validator set: it comes from a genesis file four homes share, and stopping
a process does not retire its validator, so all four are still required.

Bringing the replica back and then asking for whole-network health is what
requires it to catch up, which is where it executes the blocks it never voted
on:

```sh
tools/devnet.sh start-replica 3
tools/devnet.sh health
```

The underlying command takes the same three subcommands directly, which is
what a version-eight network uses:

```sh
protocol-cometbft-devnet stop-replica -root /absolute/path -index 3
protocol-cometbft-devnet health -root /absolute/path -nodes 0,1,2
protocol-cometbft-devnet start-replica -root /absolute/path -index 3
```

**This is a stopped replica, not a network partition.** Blocking a peer's P2P
port needs privileges the harness does not have, and a two-two split would
commit nothing on either side.

### One replica whose machine differs from its peers

`start` takes a repeatable `-application-env index:NAME=VALUE`. It adds a
variable to that replica's application process and to nothing else, and it
survives `stop-replica` and `start-replica`. The devnet uses it to run one
version-nine replica on a wrong clock, by preloading the test-only
`libprotocol-clock-offset.so` into that application
([ADR 0091](../../docs/decisions/0091-the-skewed-replica-is-skewed-below-the-process.md)):

```sh
protocol-cometbft-devnet start -root /absolute/path ... -protocol-version 9 \
  -application-env 3:LD_PRELOAD=/absolute/path/libprotocol-clock-offset.so \
  -application-env 3:PROTOCOL_STACK_CLOCK_OFFSET_FILE=/absolute/path/skew
```

The file holds a signed count of milliseconds, such as `+120000`, and is read
on every clock read, so rewriting it moves that replica's clock while it runs.
The replica keeps agreeing on every root. Its bridge logs `rejected proposal`
with decision `TIMESTAMP_BEHIND_TOLERANCE` or `TIMESTAMP_AHEAD_OF_TOLERANCE`
for each proposal it votes against.

Use a different absolute `PROTOCOL_STACK_DEVNET_ROOT` to initialize a new
network without deleting retained evidence. Set
`PROTOCOL_STACK_DEVNET_SOCKET_ROOT` to the same absolute short-lived directory
in every terminal when overriding the deterministic platform-temporary
default. Set
`PROTOCOL_STACK_DEVNET_BASE_P2P_PORT` when the default `27656..27688` loopback
block is occupied. Every repeated start refuses partial homes, changed keys,
changed genesis, or changed configuration.

## Version eight

A version-eight node is the same three processes with the version-eight
application binary and `-protocol-version 8` on both the initializer and the
bridge. The two must agree: the genesis application state the initializer
writes is what `ApplicationV8` requires at `InitChain`.

```sh
protocol-application-v8 --genesis-identity /absolute/path/protocol.genesis

protocol-cometbft-init -protocol-version 8 ...

protocol-cometbft-bridge -protocol-version 8 \
  -application-socket /absolute/path/application.sock \
  -abci-listen tcp://127.0.0.1:26658
```

The four-validator devnet takes the same flag, and it reaches the genesis and
every bridge from that one place, because a home written for one ledger version
and bridges started for the other is refused at `InitChain`:

```sh
protocol-cometbft-devnet start -protocol-version 8 \
  -genesis /absolute/path/protocol.genesis \
  -application /absolute/path/protocol-application-v8 \
  -bridge /absolute/path/protocol-cometbft-bridge \
  -node /absolute/path/protocol-cometbft-node
```

`tools/devnet.sh` remains version one: it decodes a bundled version-one genesis
and selects version one's application binary, and a version-eight wrapper needs
a bundled version-eight genesis of its own.

**Version seven was the third selectable version and is gone.** ADR 0065 staged
version eight across seven slices and its step 7 deleted version seven's kernel,
storage, application, node binary, and client, so `-protocol-version 7` is now
refused where it once initialized a home no binary could serve.

## Version nine

Version nine's canonical genesis carries a timestamp, and its CometBFT genesis
gains a fifth derived value, `genesis_time`. Identity mode prints it as a third
line of decimal milliseconds, and the initializer takes it as
`-genesis-timestamp`:

```sh
protocol-application-v9 --genesis-identity /absolute/path/protocol.genesis
# chain_id=...
# app_hash=...
# genesis_timestamp=1790000000123

protocol-cometbft-init -protocol-version 9 \
  -genesis-timestamp 1790000000123 ...

protocol-cometbft-bridge -protocol-version 9 \
  -application-socket /absolute/path/application.sock \
  -abci-listen tcp://127.0.0.1:26658
```

The initializer writes the stamp at exactly millisecond precision, which is the
only form the bridge accepts at `InitChain`. It refuses a version-nine home
without a stamp, a version-one or version-eight home with one, and an existing
genesis whose `genesis_time` differs. The devnet reads the stamp from the
application itself. It requires exactly the identity lines the version prints,
so a version-eight binary started as version nine is refused before any home is
written, and so is the reverse.

**The first block is stamped with the genesis time, exactly.** CometBFT fixes
it that way and refuses any other value, and version nine's proposal check
requires every stamp to be within 60 seconds of the machine's own clock. So a
version-nine network has to decide its first block within 60 seconds of its
genesis timestamp, or it never will. Set the stamp at, or shortly ahead of, the
moment the validators start. CometBFT sleeps until a future genesis time, and
serves no RPC while it does.
[ADR 0088](../../docs/decisions/0088-the-launcher-derives-the-genesis-time-and-the-first-block-carries-it.md)
records why.

## Single-node lifecycle

First derive the deployment identity from the same canonical genesis that the
application will load:

```sh
protocol-application --genesis-identity /absolute/path/protocol.genesis
```

Pass the reported 64-character `chain_id` and `app_hash` values to the
initializer:

```sh
protocol-cometbft-init \
  -home /absolute/path/cometbft-home \
  -chain-id <chain_id> \
  -app-hash <app_hash> \
  -proxy-app tcp://127.0.0.1:26658 \
  -rpc-listen tcp://127.0.0.1:26657 \
  -p2p-listen tcp://127.0.0.1:26656
```

Repeated initialization is idempotent only when the complete existing genesis
has the same meaning. The command never prints validator private material.

Start the three long-running processes in this order:

```sh
protocol-application \
  /absolute/path/ledger.db \
  /absolute/path/protocol.genesis \
  /absolute/path/application.sock

protocol-cometbft-bridge \
  -application-socket /absolute/path/application.sock \
  -abci-listen tcp://127.0.0.1:26658

protocol-cometbft-node start --home /absolute/path/cometbft-home
```

Stop in reverse order: node, bridge, then application. On restart, start the
same three processes in the original order. CometBFT reconciles its block store
with the application's durable C++ height and root through ABCI Info.

CometBFT's `/status` `latest_app_hash` is the hash embedded in the latest block
header, so at block height `H` it represents application state after
`H - 1`. The current durable C++ height and root are exposed by `/abci_info`
as `last_block_height` and `last_block_app_hash`.
