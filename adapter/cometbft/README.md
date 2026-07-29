# CometBFT node adapter

This Go module contains the replaceable adapter between CometBFT `v0.39.4`
and the headless C++ application. It implements the accepted version-one
contract in
[`consensus-application-v1.md`](../../docs/specifications/consensus-application-v1.md).

The module provides four cgo-free commands:

- `protocol-cometbft-bridge`, the stateless ABCI++ socket bridge;
- `protocol-cometbft-devnet`, the strict four-replica initializer, foreground
  supervisor, health checker, and transaction submitter;
- `protocol-cometbft-init`, the strict single-node home initializer;
- `protocol-cometbft-node`, the pinned CometBFT node process.

The adapter:

- serves the official CometBFT ABCI `2.0.0` socket interface;
- serializes all supported calls onto one persistent local Unix connection;
- translates only the seven version-one application methods and their exact
  result fields;
- fails unsupported application-mempool and state-sync operations closed;
- holds no canonical ledger state and makes no admission or execution
  decision;
- uses no cgo or Cosmos SDK;
- fixes the CometBFT genesis time, initial height, application identity,
  validator, and supported M1 configuration;
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
development only.

In another terminal, require four healthy RPCs, a complete three-peer view at
every validator, one equal-power validator set, and identical CometBFT, ABCI,
and direct C++ application heads:

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

Use a different absolute `PROTOCOL_STACK_DEVNET_ROOT` to initialize a new
network without deleting retained evidence. Set
`PROTOCOL_STACK_DEVNET_BASE_P2P_PORT` when the default `27656..27688` loopback
block is occupied. Every repeated start refuses partial homes, changed keys,
changed genesis, or changed configuration.

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
