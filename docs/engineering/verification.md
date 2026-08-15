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

CTest runs the registered entries concurrently, at `nproc` jobs by default.
Every entry is an independent process given its own path under the build
directory, which `tests/tools/test_registration_test.py` checks statically
because a shared path would race intermittently rather than fail outright. Set
`PROTOCOL_STACK_TEST_JOBS=1` to restore serial execution when reproducing an
ordering-sensitive failure. The two CometBFT integrations run after CTest and
remain serial: they bind real ports and supervise process groups.

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
Markdown, static image assets below `docs/`, `SKILL.md`, `LICENSE`, or `NOTICE`
uses the lightweight metadata path: whitespace, required repository paths,
settings JSON parsing, repository skill frontmatter, template-marker absence,
internal Markdown links, and focused verifier unit tests. It does not run
compilers, sanitizers, fuzzers, simulations, or live networks.

Any executable script, source, test, build file, workflow, dependency file,
protocol artifact, configuration file, or unclassified path fails closed to
the full matrix. A change to the classifier, metadata verifier, or workflow
itself therefore receives full verification. Branch protection requires the
aggregate `Verification required` check, which fails unless the selected path
and scope classifier both succeed.

The two paths do not overlap, so a check that must run on every change needs an
entry in both. `tests/tools` modules are executed by `unittest discover` on the
lightweight path and by their registered CTest entries on the full path; a
module registered in neither runs on documentation changes only. The
registration guard was in exactly that state, which meant the check that
catches an unregistered test was skipped by every pull request able to add one.

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

## Vector file conventions

A recorded vector file in `test-vectors/` is normative, and every value in one
must be reproduced by a registered verifier that fails in both directions: a
derived key the file does not carry is a failure, and a recorded key no
derivation reaches is also a failure.

Three rules exist because each was learned from a defect that reached an
accepted file.

**A boolean vector may only be true.** Its name is the claim, so recording
`false` records the negation of what the name says — and nothing catches it,
because a derivation returning `False` is faithfully recorded as `false` and
then faithfully reproduced. M3.8b found
`state.no_entry_is_keyed_by_seat_cycle=false` in an accepted file doing exactly
that. Phrase negative properties positively, and make a derived `False` a
failure in the checker rather than a value.

**A vector's name must assert no more than its value establishes.** A key called
`..._is_unchanged` whose value is a length has not established that anything is
unchanged; record the length under a plain name and the equality as a boolean
beside it.

**A claim must be checked against something other than itself.** A comparison
between a fixture and the same fixture, or a set membership that holds by
construction, records `true` forever and detects nothing. Where a third source
exists — an accepted vector file from an earlier version — compare against it,
so a formula that a model and its independent derivation got wrong the same way
still fails.
