# ADR 0091: The skewed replica's clock is moved below the process

- Status: Accepted
- Date: 2026-09-24
- Bounds: [ADR 0079](0079-the-version-nine-application-contract.md),
  [ADR 0085](0085-the-version-nine-node-process-binds-the-platform-clock.md)
- Follows: [ADR 0090](0090-the-version-nine-devnet.md)
- Settles: ADR 0085's owed choice of how the devnet skews one clock, which
  ADR 0090 §6 left to this slice
- Relates to: `tests/application/clock_offset_shim.cpp`,
  `tests/application/clock_offset.py`,
  `tests/application/headless_process_v9_test.py`,
  `tests/integration/cometbft_skewed_replica_v9_test.py`,
  `adapter/cometbft/internal/devnet/environment.go`, `tools/verify.sh`

## Context

[`consensus-application-v2`](../specifications/consensus-application-v2.md)
still owed one item of devnet evidence: *a devnet test moves one replica's clock
beyond the tolerance and proves the remaining three continue while the skewed
replica votes against proposals the others accept.*

`protocol-application-v9` reads `CLOCK_REALTIME` once per `ProcessProposal` and
has no way to be told otherwise. The contract says that in a deployment the clock
source *is* the platform real-time clock, and ADR 0085 §5 says the process takes
no flag that offsets or replaces it. ADR 0085 named two candidates and left the
choice to the first slice that needed one:

- an operator option that offsets the reading; or
- an `LD_PRELOAD` time shim.

The engine is statically linked Go, so nothing preloaded reaches it. That does
not matter here, because C5 reads the application's clock.

## Decision

### 1. The clock is moved by a shim built in this repository, not by an option on the process

`libprotocol-clock-offset.so` defines one function, `clock_gettime`. It adds a
signed number of milliseconds to `CLOCK_REALTIME` and passes every other clock
through, so poll and socket timeouts keep real time. It is some eighty lines of
C++ in a test-only CMake `MODULE`, and nothing links it.

**This keeps two accepted statements literally true.** The deployment's clock is
still the platform real-time clock with no option to move it, and the binary the
devnet skews is the binary that ships. The skew is applied where a real machine's
clock goes wrong, which is below the process.

**Rejected: an operator option on `protocol-application-v9`.** It would add no
power an operator lacks, since they own the machine's clock. But it contradicts
the contract's sentence and ADR 0085 §5 as they stand, so both would need
amending for a flag whose only user is a test. It also puts the skew arithmetic
in the shipped binary, so the devnet would test a code path production never
takes.

**Rejected: `libfaketime`.** It is an external dependency. It would have to be
installed on every hosted runner and is not pinned. It also intercepts a dozen
time functions under a configuration language of its own, where this needs one
function and one number.

**Rejected: a test-only build of the application with another clock source.**
The evidence would be about that build. That is ADR 0071's and ADR 0090's reason
for refusing a devnet-only configuration, applied to a binary.

**Rejected: a Linux time namespace.** A time namespace offsets
`CLOCK_MONOTONIC` and `CLOCK_BOOTTIME` only. `CLOCK_REALTIME` cannot be moved
that way.

### 2. The offset is read from a file on every call, and an unreadable one is an unreadable clock

The file named by `PROTOCOL_STACK_CLOCK_OFFSET_FILE` holds an optional sign, one
to twelve digits, and an optional newline. It is read on every call, so a run can
move the clock of a process that is already running. The application reads once
per proposal, so the cost is a few system calls per vote. The harness replaces
the file with `os.replace`, so no read ever sees half of one figure.

**A missing variable, file, or figure fails the call with `EINVAL`.** It does not
fall back to real time, because a shim that fell back would let a misconfigured
run pass as a skewed one. The same property reaches the two paths ADR 0085 could
not test (§6).

### 3. The shim makes raw system calls and takes the project's flags

It reaches the real clock, the file, and the descriptor through `syscall(2)` and
allocates nothing. It sits in `PROTOCOL_STACK_TARGETS` like every other target,
so a sanitizer preset instruments it, which gives its parser UBSan coverage. It
is loaded into an application instrumented the same way.

**GCC's dynamic ASan runtime refuses to start behind any preloaded library.** The
harness therefore adds `verify_asan_link_order=0` to `ASAN_OPTIONS`. That check
protects the load order of interceptors such as `malloc`. The shim defines none
of them, so there is nothing for the order to get wrong. Clang's static runtime
intercepts `clock_gettime` itself, and its interceptor resolves to the shim as
the next definition. Both shapes were run before the first push.

### 4. The supervisor gives one replica's application an environment the others lack

`protocol-cometbft-devnet start` gains a repeatable
`-application-env index:NAME=VALUE`. The environment reaches that replica's
application and nothing else, because the bridge and the node read no variable
a test would set. It survives `stop-replica` and `start-replica`, because a
machine keeps its clock across a restart. A name repeated for one replica is
refused rather than resolved, because `exec` would silently keep the last one.

### 5. One network passes through three clocks, and the replica itself says which heights each governed

Replica 3's clock starts 120 seconds ahead, then moves to 120 seconds behind,
and is then corrected. That is twice the tolerance each way, so stamps that trail
real time by a commit timeout are far outside it.

- **Ahead**, every vote must name decision `5`, `TIMESTAMP_BEHIND_TOLERANCE`.
- **Behind**, every vote must name decision `4`, `TIMESTAMP_AHEAD_OF_TOLERANCE`.
- **Corrected**, it must name nothing.

The replica's `ProcessProposal` for height `h` runs while its committed height is
`h - 1`. So every vote at or below the height it reports just before a rewrite
was cast on the old clock. Every vote two or more past the height it reports just
afterwards was cast on the new one. The height or two in between are not
asserted.

Each clock must govern at least four heights, which is one full proposer
rotation. Each skewed clock must reject at least two of them, including one a
peer proposed. Across the two, a block the skewed replica proposed must be
committed. None of the three correct replicas may reject anything, at any
height. Each phase ends with all four agreeing with the model's root at a common
height, and the stop is followed by the durable audit of height, stamp, and root.
Transactions enter through the skewed replica as well as through its peers,
because `CheckTx` reads no clock.

**Rejected: requiring a rejection at every height.** A replica whose propose step
times out before the proposal arrives votes nil without asking the application,
so "every height" would be a claim about scheduling on a loaded runner.

### 6. The headless process test reaches ADR 0085's two unreached paths

Through the shim, the binary is started with no offset file. It must exit before
it creates its database or its socket, and say its clock cannot be read. It is
then started with its clock moved onto the recorded January stamp, which it must
now **accept**. That proves the shim reaches the process, because the real clock
refuses the same stamp earlier in the same test. Then the file is made
unreadable. The next proposal must stop the process nonzero, say it is stopping
rather than voting on an assumed value, and leave no socket. A fresh process on
the real clock must find the store at genesis.

## Findings

**The pinned engine asks a proposer to process its own proposal.** Replica 3
rejected its own blocks at heights 1, 5, and 9 of the first local run, and each
was committed by the other three. So a skewed replica votes against its own
proposals too. They still commit, because a block's stamp is the engine's median
of vote times and not the proposer's clock.

**Correction needs nothing.** The first height the corrected clock governed was
accepted, with no restart and no repair, because the replica never stopped
agreeing on state. That is what `consensus-application-v2` means by a liveness
condition rather than a safety one, seen end to end.

**The skewed replica is invisible to every value the health check compares.** It
held the model's root at every observation. Its only trace is the bridge's
`rejected proposal` line, which is exactly what the contract's third topology
delta predicted.

## Evidence

This container cannot reach the pinned libsodium and SQLite hosts. So before the
first push the two targets were built in a scratch copy against the system
libsodium 1.0.18 and SQLite, with the libsodium version check relaxed in that
copy only. The Go binaries were built with the pinned toolchain through the
module proxy. That was the only way to run a timing-sensitive four-node test
before spending a fifteen-minute hosted cycle on it. The scratch copy is not
evidence the repository relies on; the hosted matrix is.

- **The shim** against probes built plain, with GCC ASan and UBSan, and with
  Clang ASan and UBSan. It applied offsets both ways, borrowed across a second
  boundary, and left `CLOCK_MONOTONIC` alone. Malformed and overlong figures, a
  missing file, and a missing variable each failed with `EINVAL`.
- **The headless test**, under a debug build and a GCC sanitizer build. Two
  mutants of the shim were each caught: one that falls back to real time, and
  one that ignores the offset.
- **The skewed-replica run**, under both builds, in 46 seconds each.
- **The existing four-validator run**, as a regression check on the harness
  change.
- **The new Go tests**: `-application-env` parsing, its refusals, and a child
  seeing an inherited, an added, and an overridden variable.

## Consequences

- **`consensus-application-v2`'s devnet evidence is met.** The kind-22 mint is
  the one exception, and its evidence stays below the engine (ADR 0090 §5).
- **The next slice is deleting `src/v8/`**, under ADR 0065's staged
  replacement, as version seven's was.
- **No accepted vector file, specification rule, manifest, encoding, kernel
  source, or production process changes.** `protocol-application-v9` is
  untouched. The Go supervisor gains a flag whose default changes nothing.
