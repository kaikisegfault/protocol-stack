# ADR 0085: The version-nine node process binds the platform clock

- Status: Accepted
- Date: 2026-09-21
- Bounds: [ADR 0079](0079-the-version-nine-application-contract.md),
  [ADR 0083](0083-the-version-nine-application-reads-one-clock.md)
- Follows: [ADR 0084](0084-the-version-nine-transport.md)
- Relates to: `src/application/main_v9.cpp`,
  `tests/application/application_driver_v2.py`,
  `tests/application/headless_process_v9_test.py`

## Context

`ApplicationV9` takes a clock source at construction and reads it once per
`ProcessProposal`. [ADR 0083](0083-the-version-nine-application-reads-one-clock.md)
made that the only read, and every test so far has supplied the clock. This
slice is the first place a real one is bound, and so the first place three
questions have to be answered: which clock, what happens when there is none at
startup, and what happens when one stops being readable later.

`consensus-application-v2` answers the second outright: a deployment that cannot
read a clock cannot vote on a proposal and must **fail to start** rather than
vote on an assumed value. The other two are this ADR's.

## Decision

### 1. The clock is `CLOCK_REALTIME`, in milliseconds, truncated toward zero

`calendar-v1` counts milliseconds since `TIMESTAMP_EPOCH`, which is the Unix
epoch, under the POSIX convention that every day is exactly 86,400,000
milliseconds and a leap second is absorbed by the second that carries it. That
is what `CLOCK_REALTIME` delivers. The conversion truncates the nanoseconds,
exactly as the contract converts a block stamp, so this machine's reading and
the stamps it compares against are in the same unit by the same rule.

A reading before the epoch is not a reading, because no `u64` millisecond count
represents it. A reading whose millisecond count would overflow a `u64` is not
one either.

**Rejected: `CLOCK_MONOTONIC`.** It is not civil time, and C5 compares against
civil time.

**Rejected: `CLOCK_TAI`.** It runs 37 seconds ahead of POSIX time today. That is
inside the 60,000 ms tolerance, but it is a systematic offset against every peer
reading `CLOCK_REALTIME`, and `calendar-v1` names the POSIX convention.

### 2. The clock is read once before anything is opened

A machine that cannot read a clock must not come up far enough to be asked for a
vote. So the process reads the clock before it opens the store, the application,
or the socket, and exits nonzero if the read fails. The contract's rule is thus
enforced before the socket exists, as well as by `make_application_v9` refusing
an empty source.

### 3. A clock that stops being readable stops the process

`ClockSourceV9` returns a `u64` and has no error channel. The bound source
throws when a read fails, the exception unwinds out of `ProcessProposal` and the
serve loop, and `main` reports it and exits nonzero. The socket and the store
close on the way.

Nothing needs undoing. `ProcessProposal` reads the clock after it has read the
head and before it evaluates any condition, and it writes nothing and stages
nothing.

**Rejected: return `0`.** Every real stamp would be ahead of the tolerance, so
the machine would vote against everything forever and log a reason that is
false: `TIMESTAMP_AHEAD_OF_TOLERANCE` would describe a clock fault as a peer's
fault.

**Rejected: return the maximum.** The same, with `BEHIND` in place of `AHEAD`.

**Rejected: return the last good reading.** It is the assumed value the contract
forbids. A clock frozen at its last reading makes C5 pass on proposals it would
refuse, silently, for as long as the stamps stay near the frozen value.

**Rejected: `std::abort`.** It stops the process equally well, but it leaves
the socket file behind and reports nothing.

### 4. Identity mode prints the genesis stamp, in decimal milliseconds

CometBFT's genesis gains a fifth derived value, `genesis_time`, and the contract
requires the launcher to derive all five from the same validated canonical
genesis. `--genesis-identity` therefore prints `genesis_timestamp=` beside
`chain_id=` and `app_hash=`.

It prints the value the chain commits to, not a civil time. Rendering it as
RFC 3339 with exactly millisecond precision is the launcher's job. A second time
formatter in C++ would be a second place for that rendering to be wrong, and it
would have nothing to compare against.

### 5. There is no clock-injection option

The process takes no flag that offsets or replaces its clock. The headless test
does not need one, because of the finding below. The devnet test that
`consensus-application-v2` asks for — one replica's clock beyond the tolerance —
will need some way to skew one process. That is recorded under "Owed" as the
devnet slice's decision, not settled here.

## The finding

### The recorded chain places a real clock without faking one

The recorded version-nine chain's stamps are January 2026. Against any real clock
since then, a proposal carrying the recorded first-block stamp is **behind** the
tolerance, and a proposal carrying a stamp in 2100 is **ahead** of it. Together
the two decisions place the process's clock strictly between them, which a
stubbed, zero, frozen-at-epoch, or missing clock cannot do. `FinalizeBlock` then
accepts the January stamp anyway, which is the process-level form of ADR 0083's
central test.

The same fact limits what the process test can replay. The recorded run is
signed under a stand-in verifier table, and this binary verifies with Ed25519,
so the recorded transactions would be refused as results. The block the test
finalizes is therefore empty. The checks on it are the ones that need no
recorded root:

- two processes over the same genesis agree on it;
- one millisecond of stamp changes its root, which is the stamp entering the
  state root, observed from outside the process; and
- the stamp survives a restart.

## Evidence

`version-nine-headless-process` starts the binary six times:

1. **Identity mode** prints the recorded chain identity, the height-zero root read
   from the recorded first header, and the recorded genesis stamp. A genesis
   stamped at `MAX_TIMESTAMP_MILLIS` is accepted, with a different chain
   identity. One stamped a millisecond past it is refused, as are a short, an
   empty, a version-eight-schema, and a version-eight-width genesis.
2. **A fresh process** reports version 9, height zero, the genesis stamp, and the
   genesis root. A premature commit is a status.
3. **InitChain at a foreign genesis stamp** is an invalid request.
4. **The real clock**: January is `TIMESTAMP_BEHIND_TOLERANCE` and 2100 is
   `TIMESTAMP_AHEAD_OF_TOLERANCE`. The empty January block finalizes, and
   Commit reports height 1, the January stamp, and the finalized root.
5. **A restart** reports that head, stamp included. A decided block one
   millisecond below it answers status `8`.
6. **A second database** finalizes the same block to the same octets and refuses
   a fresh stamp at the staged height. **A third**, given that fresh stamp,
   reaches a different root.

**What is not tested at the process level.** The startup refusal of an
unreadable clock, and the runtime stop, cannot be reached without faking the
platform clock. The application-level refusal of an empty clock source is
tested in `version-nine-application`. The two process paths are small enough to
read in full, and they are stated in this ADR so a reviewer can check them
against it.

## Consequences

**Every C++ piece of version nine's node now exists.** What is left of the stack
is the Go side: the adapter's version-two client and its ABCI conversion, the
launcher's `genesis_time`, and the devnet. Then `src/v8/` can be deleted.

**The shared Python driver gained a wire version rather than a copy.**
`application_driver.Connection` names its frame version in one class attribute,
and `application_driver_v2.Connection` overrides that attribute and the five
operations whose payloads changed. Version eight's tests read the same octets
they always did.

## Owed

**The devnet's skewed replica needs a way to skew one clock.** The two candidates
are an operator option that offsets the reading, which adds no power an operator
lacks since they own the machine's clock, and an `LD_PRELOAD` time shim, which
adds a dependency and touches no source. The choice belongs to the devnet slice,
which is the first to need it.
