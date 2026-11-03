# Local go feedback offline

The owner's host has no CometBFT in `~/go/pkg/mod` (about 271 MB, mostly the
pinned go1.25.10 toolchain), and the resource rules forbid fetching the
dependency graph locally. Two checks still work, both verified on 2026-10-28
(M4.3k):

- **`internal/localapp` imports only the standard library**, so its suite runs
  offline: `cd adapter/cometbft && GOPROXY=off GOFLAGS=-mod=readonly
  GOCACHE=<scratchpad>/gocache go test ./internal/localapp/`. `GOPROXY=off`
  guarantees no download. The default module cache supplies the toolchain, and a
  separate `GOMODCACHE` breaks that, so keep the default. The build cache was
  63 MB; delete it afterwards.
- **`bridge`, `nodeconfig`, and the `cmd/` packages import CometBFT.** A scratch
  `go/types` program (run with `GO111MODULE=off`) type-checks a package
  directory. It resolves stdlib through `importer.ForCompiler(fset, "source",
  nil)` and parses `internal/localapp` from source. It fakes every other import
  as an empty package, and drops errors that mention the faked packages. It
  caught an unused import and a wrong `localapp` method in probes. It cannot
  check calls into CometBFT itself.

**Why:** the hosted round trip is 12 to 17 minutes, and in M4.3k the hosted run
was the first compile of the bridge changes. It passed, but only these checks
stood between an edit and a wasted run.

**How to apply:** use both before pushing Go changes, then let the hosted matrix
compile and run everything. See `local-cpp-feedback-without-cmake.md` for the
C++ equivalent and `run-only-necessary-hosted-checks.md`.
