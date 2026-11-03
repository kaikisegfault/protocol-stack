# Local cpp feedback without cmake

The owner's machine has `g++` 12 and `clang++` 14 but no `cmake` or `ninja`.
`tools/verify.sh` would install them into a `.cache` venv, which the owner's
resource rules discourage. On 2026-10-09 (M4.4), a scratch build gave full
local feedback in about two minutes. A member-initialization defect was caught
before any hosted run.

- Compile the kernel sources (`PROTOCOL_STACK_KERNEL_SOURCES` in
  `CMakeLists.txt`) plus the changed files with `g++ -std=c++20 -Wall -Wextra
  -Wpedantic -Werror -D_GLIBCXX_ASSERTIONS -I include -I src -I <shim>`, in
  parallel, into the scratchpad.
- `<shim>/sodium.h` declares only the six symbols in use, and links
  `-l:libsodium.so.23`, the system 1.0.18 runtime. No headers are installed.
- Python checks that use `pinned_sodium` refuse 1.0.18. A scratch runner that
  relaxes only that version-string `require` lets them run locally.
- Nothing scratch is committed. The hosted matrix on the pinned 1.0.22 stays the
  gate. Delete the scratch objects afterwards.
- **Sanitizers and libFuzzer work locally with clang 14** (checked 2026-10-26,
  M4.3g): `-fsanitize=address,undefined[,fuzzer]` links against
  `/usr/lib/llvm-14/lib/clang/14.0.6/lib/linux/libclang_rt.fuzzer-x86_64.a`.
  The 2026-10-22 delivery record said this host had no libFuzzer, which was
  wrong. Use it to time a new fuzz smoke against CTest's 60 s `TIMEOUT`. Hosted
  runners ran the v10 execution target about 1.7x slower than this host under
  parallel CTest.
- **Store code needs SQLite, which has no headers here.** The runtime is the
  system `libsqlite3.so.0` (3.40.1); link it with `-l:libsqlite3.so.0
  -lpthread`. On 2026-10-26 (M4.3h) a copy of SQLite 3.53.0's official
  `sqlite3.h` from `~/.bun/install/cache/better-sqlite3@12.9.0@@@1/deps/sqlite3/`
  served as declarations in the scratch shim. Both v10 store suites ran,
  including the fault VFS. The repository pins 3.53.3, and hosted runs stay
  the gate.
- **Rebuild every unit that includes a changed test-fixture header.** A stale
  object with an old struct layout crashed the suite (2026-10-26) before
  anything was wrong with the code.
- **Blind spot: the hosted GCC is 13+, and local GCC 12 cannot emit
  `-Werror=dangling-reference`.** It failed both GCC presets in M3.18b and
  again in M4.3d (2026-10-18, run 39136276697), both times on
  `const auto& x = f(..., "literal")` where `f` returns a reference and takes
  `const std::string&`. Copy the result (`const std::string x = f(...)`), as
  the v9 tests do, and grep new tests for that shape before pushing.

**Why:** a hosted round trip is 12 to 16 minutes, and a compile error found
there wastes one. This route populates no repository cache.

**How to apply:** use it for C++ slices before pushing. Do not use it for
network runs, which need CometBFT built and stay hosted-only. See
`run-only-necessary-hosted-checks.md`.
