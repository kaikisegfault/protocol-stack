# protocol-stack

`protocol-stack` is the open-source research and implementation monorepo for a
sovereign, single-native-asset blockchain stack.

The project is in its foundation phase. Its first operational milestone is a
reproducible four-validator local devnet backed by an original deterministic
C++20 ledger kernel. It is not production-ready.

## Start here

- [Vision](docs/project/vision.md)
- [Project charter](docs/project/charter.md)
- [First operational goal](docs/project/first-goal.md)
- [Roadmap](docs/project/roadmap.md)
- [Current state and next action](docs/project/current-state.md)
- [Documentation index](docs/README.md)

Codex sessions opened at the repository root automatically receive the
instructions in [AGENTS.md](AGENTS.md). A clean session can continue the next
verified unit of work with:

```text
proceed
```

On a supported Linux x86_64 development host, configure, build, and test the
current implementation with:

```sh
tools/verify.sh
```

See the [build and test toolchain](docs/engineering/build-toolchain.md) for
host prerequisites and compiler/sanitizer presets.

## License

Apache License 2.0. See [LICENSE](LICENSE).
