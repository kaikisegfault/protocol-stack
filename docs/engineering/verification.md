# Verification

## Foundation checks

Before completing F0:

- validate each repository skill with the official skill validator;
- ensure no skill contains template TODO markers;
- inspect all Markdown links and referenced paths;
- parse `.codex/config.toml`;
- verify Git author and committer identity;
- inspect the complete staged diff and confirm no secrets or unrelated changes;
- confirm a clean status after commit and push.

## Reproducible entry point

On supported Linux x86_64 hosts, run:

```sh
tools/verify.sh
```

The command installs hash-pinned CMake, Ninja, and Go tools in the ignored
local cache, verifies the pinned Go module graph, tests and vets the CometBFT
adapter, and builds its bridge, initializer, and node commands with cgo
disabled. It then integrity-checks and builds the pinned libsodium and SQLite
sources, configures the selected CMake preset, runs all registered C++ and
Python tests through CTest, and runs a real single-node CometBFT
transfer/restart/continued-height integration. See `build-toolchain.md` for
host prerequisites, other presets, cache behavior, and cleanup.

CI runs GCC and Clang debug builds plus AddressSanitizer and
UndefinedBehaviorSanitizer builds. The current suite includes unit and boundary
tests, deterministic properties, 10,000 seeded differential sequences, and
bounded libFuzzer smoke under the Clang sanitizer preset.

## Execution policy

GitHub-hosted Actions on the exact pushed commit are the default completion
site for full builds, compiler and sanitizer matrices, fuzzing, simulations,
packaging, and other resource-heavy gates. Locally, run only the lightweight
or focused checks needed for prompt feedback. Do not duplicate a green remote
matrix locally unless the workflow is unavailable or under change, or a remote
failure must be reproduced; document that exception.

Do not detach local repository commands or leave persistent check watchers,
servers, or helpers. Use bounded GitHub status queries. At every completed
phase, confirm the exact remote jobs are terminal, cancel obsolete runs, audit
local processes, preserve evidence, and run `tools/clean-local.sh`. Inspect
unexplained processes or files individually rather than deleting them.

The entry point already includes Go static analysis and single-node process,
transfer, deterministic replay, and restart integration. It will expand with
the four-validator operational devnet and further production surfaces.

Long-running fuzzing, economic simulations, and multi-platform reproducibility
checks may run separately, but their commands and latest evidence must be
documented.

## Evidence rule

Do not claim a check passed without exact local output or a terminal GitHub
check on the current commit. Record the exact command or check and concise
result in the relevant PR or `current-state.md`. If a required check cannot
run, describe why and do not silently downgrade the definition of done.
