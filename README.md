# protocol-stack

`protocol-stack` is the open-source research and implementation monorepo for a
sovereign, single-native-asset ecosystem: deterministic blockchain rules,
permanent Founder infrastructure, controlled applications, bounded self-hosted
AI authority, and a restricted external-value boundary.

The project is research software. Its Sovereign Devnet Alpha is runnable; the
active milestone is an exact Founder Economy specification and independent
proof before those economic rules enter C++ consensus. It is not
production-ready.

## Start here

- [Founder Constitution](docs/project/founder-constitution.md)
- [Vision](docs/project/vision.md)
- [Project charter](docs/project/charter.md)
- [First operational goal](docs/project/first-goal.md)
- [Roadmap](docs/project/roadmap.md)
- [Current state and next action](docs/project/current-state.md)
- [Documentation index](docs/README.md)

Codex sessions opened at the repository root automatically receive the
instructions in [AGENTS.md](AGENTS.md), including the boundary between
founder-reserved direction and autonomous engineering. A clean session can
continue the next verified unit of work with:

```text
proceed
```

For a concise, plain-language reality check covering what works, milestone
progress, value, quality, maintainability, and what remains, use:

```text
status
```

On a supported Linux x86_64 development host, one foreground command builds
the required pinned binaries on first use, initializes four independent local
validators, and starts the M1 devnet:

```sh
tools/devnet.sh start
```

In another terminal, inspect the exact four-replica height and root or submit
the first public synthetic signed transfer:

```sh
tools/devnet.sh health
tools/devnet.sh transaction examples/devnet/transaction-1.hex
```

Press Ctrl-C in the start terminal for an orderly stop. Run the same start
command to restart the retained homes and SQLite ledgers; the second fixture
then continues with nonce `2`:

```sh
tools/devnet.sh transaction examples/devnet/transaction-2.hex 1
```

The fixtures have public development keys and must never hold real value.
`PROTOCOL_STACK_DEVNET_ROOT` selects a different persistent network directory,
`PROTOCOL_STACK_DEVNET_SOCKET_ROOT` selects a shared short-lived socket
directory for all terminals, and `PROTOCOL_STACK_DEVNET_BASE_P2P_PORT` moves
the fixed local port block.

Configure, build, test, and run both the single-node compatibility integration
and the complete four-validator lifecycle with:

```sh
tools/verify.sh
```

See the [build and test toolchain](docs/engineering/build-toolchain.md) for
host prerequisites and compiler/sanitizer presets.

## License

Apache License 2.0. See [LICENSE](LICENSE).
