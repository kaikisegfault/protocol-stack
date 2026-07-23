# ADR 0005: Reproducible M1 build toolchain

- Status: Accepted
- Date: 2026-07-23

## Context

M1 needs one clean-clone command that builds and tests the original C++20
kernel and its independent Python reference model. Consensus-path dependencies
must be immutable, integrity checked, license compatible, and replaceable.
Compiler diversity and sanitizer builds must be ordinary configurations rather
than undocumented local procedures.

ADR 0004 requires strict Ed25519 acceptance semantics and identified
libsodium's verifier as suitable. The prototype's system-library lookup and
Python `cryptography` dependency were not reproducible enough for production
integration.

## Decision

Use CMake and CTest as the build and test orchestrator, Ninja as the build
executor, and checked-in CMake presets for GCC and Clang:

- `gcc-debug`;
- `gcc-sanitizers`;
- `clang-debug`;
- `clang-sanitizers`.

The sanitizer presets enable AddressSanitizer and UndefinedBehaviorSanitizer
for project code. The reviewed upstream dependency retains its hardening flags
and is exercised through the sanitized adapter calls. All project C++ targets
compile as C++20 with `-Wall -Wextra -Wpedantic -Werror` and standard-library
assertions enabled.

For the supported M1 bootstrap platform, Linux x86_64, `tools/verify.sh`
creates an ignored repository-local Python virtual environment and installs
these exact wheels with pip hash checking:

| Tool | Version | License | Integrity |
| --- | --- | --- | --- |
| CMake | 4.4.0 | BSD-3-Clause | SHA-256 `51bcb2e65c0d5c1af4a749ba40a321b7436420c7359724ab46719004f3cd2149` |
| Ninja | 1.13.0 | Apache-2.0 | SHA-256 `fb46acf6b93b8dd0322adc3a4945452a4e774b75b91293bafcc7b7f8e6517dfa` |

The host supplies Linux x86_64, Python 3.11 or newer with `venv`, GNU Make,
and the compiler named by the preset. These are checked explicitly or by
CMake configuration. CI fixes the operating-system image and exercises all
four presets.

Pin libsodium 1.0.22 from its official release archive:

- archive:
  `https://download.libsodium.org/libsodium/releases/libsodium-1.0.22.tar.gz`;
- SHA-256:
  `adbdd8f16149e81ac6078a03aca6fc03b592b89ef7b5ed83841c086191be3349`;
- license: ISC.

CMake downloads over verified TLS, checks the archive hash before extraction,
and builds both static and shared libraries from source. C++ tests link the
static archive. The Python harness loads the same exact shared build through a
path supplied by CTest and has no third-party Python runtime dependency.
Cryptography remains behind the harness boundary; no primitive is
reimplemented.

The dependency is isolated under each preset's ignored build directory.
Changing any pinned archive, version, hash, cryptographic build option, or
consensus-facing provider requires review of this ADR, the protocol vectors,
and all compiler/sanitizer jobs. Ordinary build output and tool wheels may be
deleted and reconstructed from the committed files.

## Alternatives

### System packages

System CMake, Ninja, and libsodium packages are convenient but vary by
distribution and time. They remain useful for exploratory work but do not
satisfy the clean-clone evidence path.

### Vendoring or a Git submodule

Vendoring would make source availability explicit but substantially enlarge
the repository and make upstream provenance review harder. A submodule adds
stateful clone behavior. The immutable official archive plus hash provides a
smaller, auditable pin. If offline or archival builds become a milestone
requirement, a repository-owned source mirror can be added without changing
the adapter.

### Conan, vcpkg, or another package manager

These can handle larger dependency graphs but add bootstrap code and lockfile
semantics before the project has such a graph. CMake `ExternalProject` is
sufficient for the single audited C library.

### Bazel or Meson

Both can provide strong build discipline. CMake has broader native support in
the expected C++ and IDE ecosystem and lets M1 expose its small dependency
graph directly.

## Consequences

- One command configures, builds, and tests without depending on a user Python
  environment or system libsodium.
- GCC/Clang and sanitizer behavior is represented in source control and CI.
- First-run verification needs network access to PyPI and the official
  libsodium release host. Cached virtual-environment and build outputs make
  later runs incremental.
- The initial bootstrap is Linux x86_64 only. Supporting another platform
  requires an integrity-pinned tool distribution, presets, and CI evidence.
- Rebuilding libsodium per preset costs CI time but keeps compiler selections
  isolated from each project instrumentation configuration.

## Update and removal path

For an update, verify the upstream release and license, replace each version
and hash atomically, regenerate clean build directories, and run all four
presets plus the adversarial protocol vectors. A provider replacement must
retain the narrow signing/verifying boundary and demonstrate identical strict
acceptance behavior before this dependency can be removed.

## Primary references

- [CMake `ExternalProject`](https://cmake.org/cmake/help/latest/module/ExternalProject.html)
- [CMake presets](https://cmake.org/cmake/help/latest/manual/cmake-presets.7.html)
- [CMake license](https://gitlab.kitware.com/cmake/cmake/-/blob/master/Copyright.txt)
- [Ninja releases](https://github.com/ninja-build/ninja/releases)
- [Ninja license](https://github.com/ninja-build/ninja/blob/master/COPYING)
- [pip secure installs](https://pip.pypa.io/en/stable/topics/secure-installs/)
- [libsodium installation documentation](https://doc.libsodium.org/installation)
- [libsodium license](https://github.com/jedisct1/libsodium/blob/master/LICENSE)
- [libsodium public-key signatures](https://doc.libsodium.org/public-key_cryptography/public-key_signatures)
