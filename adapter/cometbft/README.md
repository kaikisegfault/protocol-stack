# CometBFT ABCI++ bridge

This Go module is the replaceable, stateless adapter between CometBFT
`v0.39.3` and the headless C++ application. It implements the accepted
version-one contract in
[`consensus-application-v1.md`](../../docs/specifications/consensus-application-v1.md).

The bridge:

- serves the official CometBFT ABCI `2.0.0` socket interface;
- serializes all supported calls onto one persistent local Unix connection;
- translates only the seven version-one application methods and their exact
  result fields;
- fails unsupported application-mempool and state-sync operations closed;
- holds no canonical ledger state and makes no admission or execution
  decision;
- uses no cgo or Cosmos SDK.

The repository verifier bootstraps the integrity-pinned Go 1.25.10 Linux
x86-64 toolchain, verifies `go.sum`, and runs all bridge packages with cgo
disabled:

```sh
tools/verify.sh
```

For a focused bridge check after bootstrapping the toolchain:

```sh
cd adapter/cometbft
GOTOOLCHAIN=local CGO_ENABLED=0 \
  ../../.cache/go1.25.10/bin/go test ./...
```

The command process requires the C++ application to be listening first:

```sh
protocol-cometbft-bridge \
  -application-socket /absolute/path/application.sock \
  -abci-listen tcp://127.0.0.1:26658
```

Single-node CometBFT configuration, lifecycle orchestration, and restart
integration are the next issue #22 slice; this module deliberately does not
own those operational concerns.
