# Build and test toolchain

## Supported bootstrap

The M1 reproducible bootstrap currently supports Linux x86_64. A clean machine
needs:

- Python 3.11 or newer with the standard `venv` module;
- GNU Make;
- `tar`;
- GCC for the default preset;
- Clang as well when running the complete compiler matrix;
- outbound HTTPS on the first run.

On Ubuntu 24.04 the host prerequisites are:

```sh
sudo apt-get update
sudo apt-get install --yes build-essential clang make python3 python3-venv
```

From the repository root, the complete default verification command is:

```sh
tools/verify.sh
```

Select another committed configuration with `PROTOCOL_STACK_PRESET`:

```sh
PROTOCOL_STACK_PRESET=gcc-sanitizers tools/verify.sh
PROTOCOL_STACK_PRESET=clang-debug tools/verify.sh
PROTOCOL_STACK_PRESET=clang-sanitizers tools/verify.sh
```

CI runs all four presets. This GitHub-hosted matrix is the normal completion
path. Avoid rebuilding all four presets locally by default; use a focused
local target only when it materially improves iteration, and reserve a local
full matrix for workflow changes, unavailable CI, or failure reproduction.

## What the command does

The script checks the supported platform and host prerequisites, creates
`.cache/toolchain-linux-x86_64`, and uses hash-checked requirements to install
the exact CMake and Ninja wheels. It downloads the official Go 1.25.10 Linux
x86-64 archive, verifies the SHA-256 accepted in ADR 0001, verifies the pinned
Go module graph, runs all CometBFT adapter tests and vet, and builds the bridge,
strict single-node initializer, four-validator supervisor, and pinned node
commands with cgo disabled. CMake then downloads the official libsodium 1.0.22
and SQLite 3.53.3 archives, verifies their committed SHA-256 digests, builds
them within the selected preset, builds the C++20 verification targets, and
runs the C++ and Python suite through CTest. Finally, the process integrations
run both the single-node compatibility path and the twelve-process
four-validator lifecycle. The latter checks exact peers and validator sets,
commits a signed transfer, stops and restarts every replica, commits the next
height, and compares all four durable application roots.

For an operational devnet without running the test suite, this foreground
command builds only missing runtime binaries and then starts the fixed local
topology:

```sh
tools/devnet.sh start
```

Its first run still downloads and integrity-checks the required build,
libsodium, SQLite, Go, and module inputs. This focused path is for operating the
documented network; the complete hosted verification matrix remains the
evidence gate for changes.

The Python tests use only the standard library and the exact libsodium shared
library produced by that build. They do not inspect or modify the user's
Python environment.

The `clang-sanitizers` preset additionally builds a separate copy of the
protocol kernel with libFuzzer coverage instrumentation. CTest runs bounded
512-input smoke sessions for transaction admission, text-address decoding,
and canonical genesis loading under AddressSanitizer and
UndefinedBehaviorSanitizer. The other three presets do not build fuzz targets.
Both sanitizer presets also apply AddressSanitizer and
UndefinedBehaviorSanitizer to the pinned SQLite amalgamation. Libsodium retains
its explicit release build flags and is exercised through the instrumented
protocol-stack test harnesses.

## Cache and cleanup

Tool wheels, the isolated virtual environment, the pinned Go toolchain, Go
module and build caches, and the four Go runtime binaries live under
`.cache/`. Each preset's configuration, downloaded dependency sources,
compiled dependencies, and test artifacts live under `out/build/<preset>/`.
Both roots are ignored by Git and may be deleted safely; the next verification
run reconstructs them from committed versions and hashes.

The ignored `.local/devnet` directory is different: it contains generated
validator keys, CometBFT block stores, and four SQLite ledgers retained across
operator restarts. `tools/clean-local.sh` deliberately does not remove it.

The bootstrap deliberately does not share compiled dependency trees between
presets because compiler selections and project instrumentation configurations
differ. CMake and Ninja wheel downloads may be served from pip's normal user
download cache, but their contents are still checked against the committed
hashes.

After a phase's evidence is recorded and no local verification process is
running, remove the known reproducible repository artifacts:

```sh
tools/clean-local.sh
```

The command deletes only the four committed preset trees, isolated repository
toolchain, Go toolchain/module/build caches and integration binaries, and
Python bytecode caches under `tools/` and `tests/`. It does not kill processes
or delete unexplained files. Audit and resolve those separately.
GitHub-hosted runners are ephemeral; obsolete or superseded runs must still be
cancelled, and workflow concurrency should prevent duplicate runs for the same
branch or pull request.

## Dependency inventory

ADR 0005 records the build-tool and cryptographic dependency inventory. ADR
0007 records SQLite's version, archive hashes, deliverable public-domain
status, retained build-script notices, configuration, update policy, and
removal path. No Node.js tooling or package manager is involved.
