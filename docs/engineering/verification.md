# Verification

## Foundation checks

Before completing F0:

- validate each repository skill with the official skill validator;
- ensure no skill contains template TODO markers;
- inspect all Markdown links and referenced paths;
- parse `.claude/settings.json`;
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
adapter, and builds its bridge, devnet supervisor, single-node initializer, and
node commands with cgo disabled. It then integrity-checks and builds the pinned
libsodium and SQLite sources, configures the selected CMake preset, runs all
registered C++ and Python tests through CTest, and runs both the real
single-node CometBFT compatibility integration and the four-validator
transfer/stop/restart/continued-height integration. See `build-toolchain.md`
for host prerequisites, other presets, cache behavior, and cleanup.

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

Verification is risk-proportionate. A changed-path set containing only
Markdown, static image assets below `docs/`, `SKILL.md`, skill
`agents/openai.yaml`, `LICENSE`, or `NOTICE` uses the lightweight metadata
path: whitespace, required repository paths, TOML parsing, repository skill
frontmatter and UI metadata, template-marker absence, internal Markdown links,
and focused verifier unit tests. It does not run compilers, sanitizers, fuzzers,
simulations, or live networks.

Any executable script, source, test, build file, workflow, dependency file,
protocol artifact, configuration file, or unclassified path fails closed to
the full matrix. A change to the classifier, metadata verifier, or workflow
itself therefore receives full verification. Branch protection requires the
aggregate `Verification required` check, which fails unless the selected path
and scope classifier both succeed.

The owner machine is resource-constrained. Dependency graph resolution,
lock-file generation for expanded graphs, full verification, direct VCS module
retrieval, and other operations that populate large reproducible caches belong
on GitHub-hosted runners. Retrieve only the reviewed manifest, patch, or small
artifact needed to continue locally. When a local exception is unavoidable,
announce its expected disk/CPU/memory cost first, bound it, and run
`tools/clean-local.sh` immediately after preserving evidence.

Do not detach local repository commands or leave persistent check watchers,
servers, or helpers. Use bounded GitHub status queries. At every completed
phase, confirm the exact remote jobs are terminal, cancel obsolete runs, audit
local processes, preserve evidence, and run `tools/clean-local.sh`. Inspect
unexplained processes or files individually rather than deleting them.

The entry point includes Go static analysis, the single-node compatibility
path, and a four-validator full-mesh integration. The latter supervises twelve
processes, checks all direct peers and validator sets, commits independently
modelled signed transfers, compares every ABCI head, stops cleanly, audits all
four durable SQLite replicas directly through independent C++ application
processes, restarts the retained network, independently models any intervening
empty blocks, and continues at a later height.

Long-running fuzzing, economic simulations, and multi-platform reproducibility
checks may run separately, but their commands and latest evidence must be
documented.

## Evidence rule

Do not claim a check passed without exact local output or a terminal GitHub
check on the current commit. Record the exact command or check and concise
result in the relevant PR or `current-state.md`. If a required check cannot
run, describe why and do not silently downgrade the definition of done.
