# CometBFT node adapter

This Go module contains the replaceable adapter between CometBFT `v0.39.4`
and the headless C++ application. It implements the accepted version-one
contract in
[`consensus-application-v1.md`](../../docs/specifications/consensus-application-v1.md).

The module provides three cgo-free commands:

- `protocol-cometbft-bridge`, the stateless ABCI++ socket bridge;
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
three commands with cgo disabled, and runs the real single-node restart
integration:

```sh
tools/verify.sh
```

For a focused bridge check after bootstrapping the toolchain:

```sh
cd adapter/cometbft
GOTOOLCHAIN=local CGO_ENABLED=0 \
  ../../.cache/go1.25.10/bin/go test ./...
```

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
