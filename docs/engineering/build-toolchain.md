# Build and test toolchain

## Supported bootstrap

The M1 reproducible bootstrap currently supports Linux x86_64. A clean machine
needs:

- Python 3.11 or newer with the standard `venv` module;
- GNU Make;
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

CI runs all four presets.

## What the command does

The script checks the supported platform and host prerequisites, creates
`.cache/toolchain-linux-x86_64`, and uses hash-checked requirements to install
the exact CMake and Ninja wheels. CMake then downloads the official libsodium
1.0.22 archive, verifies its committed SHA-256 digest, builds it within the
selected preset, builds the C++20 verification targets, and runs the C++ and
Python suite through CTest.

The Python tests use only the standard library and the exact libsodium shared
library produced by that build. They do not inspect or modify the user's
Python environment.

The `clang-sanitizers` preset additionally builds a separate copy of the
protocol kernel with libFuzzer coverage instrumentation. CTest runs bounded
512-input smoke sessions for transaction admission, text-address decoding,
and canonical genesis loading under AddressSanitizer and
UndefinedBehaviorSanitizer. The other three presets do not build fuzz targets.

## Cache and cleanup

Tool wheels and the isolated virtual environment live under `.cache/`. Each
preset's configuration, downloaded dependency source, compiled dependency,
and test artifacts live under `out/build/<preset>/`. Both roots are ignored by
Git and may be deleted safely; the next verification run reconstructs them
from committed versions and hashes.

The bootstrap deliberately does not share a compiled libsodium tree between
presets because compiler selections and project instrumentation configurations
differ. CMake and Ninja wheel downloads may be served from pip's normal user
download cache, but their contents are still checked against the committed
hashes.

## Dependency inventory

ADR 0005 records versions, archive hashes, licenses, alternatives, update
policy, and removal paths. No Node.js tooling or package manager is involved.
