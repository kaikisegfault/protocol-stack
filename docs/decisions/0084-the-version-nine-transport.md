# ADR 0084: The version-nine transport writes statuses 7 and 8 through a signature

- Status: Accepted
- Date: 2026-09-21
- Bounds: [ADR 0079](0079-the-version-nine-application-contract.md),
  [ADR 0082](0082-the-version-two-application-frame.md)
- Follows: [ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md),
  [ADR 0068](0068-the-version-eight-application-layer.md),
  [ADR 0083](0083-the-version-nine-application-reads-one-clock.md)
- Relates to: `include/protocol/application/response_v9.hpp`,
  `include/protocol/application/dispatcher_v9.hpp`,
  `src/application/response_v9.cpp`, `src/application/dispatcher_v9.cpp`,
  `include/protocol/application/unix_server_v1.hpp`,
  `src/application/unix_connection_v1.cpp`

## Context

[ADR 0083](0083-the-version-nine-application-reads-one-clock.md) delivered
`ApplicationV9`, which answers in `ApplicationInfoV9`, `FinalizedBlockV9`,
`CommittedHeadV9`, and a `ProposalDecision`.
[ADR 0082](0082-the-version-two-application-frame.md) delivered the version-two
frame's request half. Nothing turned the application's answers into version-two
frames, and no socket served one, so a node process had nothing to call.

Version eight delivered the equivalent pieces as one slice in M3.13r, and this
one follows its shape: a response encoder, a dispatcher, and a
`serve_connection` overload. What differs is version nine's four changed
responses, its eight-value decision, its two new statuses, and the fact that
its socket must read a **different frame version** from the two before it.

## Decision

### 1. Statuses `7` and `8` are written by a function that takes no kind

[`consensus-application-v2`](../specifications/consensus-application-v2.md) says
statuses `7` and `8` are reachable **only** from kind 6. Kind 5 reports the same
two conditions as decisions `2` and `3` under status zero, because there the
correct answer is a vote and here it is a halt.

`encode_timestamp_failure_v9(request_id, failure)` takes no `MessageKind`. It
writes a finalize response or nothing, so no caller can write status `7` on a
proposal and no maintainer can add a branch that does without changing a
signature. It is the same move ADR 0083 made for the clock: the rule is a
function's shape rather than a check a caller has to remember.

**Rejected: one error encoder over a widened status type.** A single
`encode_error_response_v9(kind, request_id, status)` over the union of both
spaces would need a runtime check that `status >= 7` implies
`kind == finalize_block`. That check would be correct today, and nothing would
stop the next caller from bypassing it by writing its own encoder call.

### 2. The version-one path refuses a timestamp status smuggled into it

`encode_error_response_v9` accepts version one's six statuses and **refuses
`7` and `8` cast into an `ApplicationError`**, as `invalid_payload`. Without
that refusal the kind-free function above would be a convention, because the
other path could still write the same octets under any kind.
`encode_timestamp_failure_v9` refuses anything but its two values for the same
reason.

### 3. A decision outside the eight is refused rather than written

The enum cannot hold a ninth value unless something cast it there. **A stray
value would still vote the right way**, because the adapter votes REJECT on
every nonzero byte, and it would report an outcome the contract does not name.
That is the silent kind of wrong, so the encoder catches it rather than leaving
it to the vote.

### 4. A receipt is version nine's only if its version octets say `9`

The finalize response's per-transaction receipts are checked against a prefix
derived from `v9::kReceiptVersion`, as version eight's are against its own. So a
version-eight receipt framed as a version-nine answer is refused. The layout is
version eight's with the version field at `9`, so the result byte stays at
offset 39.

### 5. The socket loop is one function over a wire, and each overload names its wire

`serve_with` was one function over a dispatcher and hard-coded version one's
decoders. It now takes a wire policy as well — a header decoder, a request
decoder, and the request type the second produces — and the three overloads
name theirs: `WireV1` for versions one and eight, `WireV2` for version nine.

**The header of `unix_server_v1.hpp` said the opposite until now**: that the `V1`
was the frame format's version and that "a new ledger version adds an overload
here and not a wire". That held through version eight and is false of version
nine, whose blocks carry a timestamp. The header now says the `V1` is the
socket's version — the path rules, the bind, the ownership check, and the loop —
and that the wire an overload reads is part of its signature.

**Rejected: a server that accepts either frame version.** Choosing the decoder
from each frame's version octet would let a version-one bridge talk to a
version-nine application, and the frame version exists to stop exactly that
pairing. Each overload reads one version and refuses the other at the header.

**Rejected: a `UnixSocketServerV2` class.** It would copy the listener's path,
bind, and ownership code, all of which is identical, to change two decoder calls.

### 6. Diagnostics stay empty

The contract permits a UTF-8 diagnostic of up to 4,096 bytes on a nonzero
status. This encoder writes none, as version eight's does. Diagnostics are
operational only and the bridge never places one in a consensus result, so
nothing downstream would read them yet.

## The finding

### `RESOURCE_BOUND` cannot arrive over the wire either

ADR 0083 found that decision `7` is not reachable from a proposal's contents.
Building this transport's tests found that **decision `6` is not reachable over
the wire at all**. `wire_v2`'s request decoder enforces the same three bounds as
`within_block_bounds` — the raw count against the kernel's own `kMaxRawInputs`,
each input against 1,048,576 bytes, and the checked total against 16,777,216 —
and a frame that violates any of them is refused as `resource_limit` before it
is dispatched. The socket loop turns that into a protocol failure, and the
application is never asked.

The full stack refuses earlier still. The Go bridge's `validateBlock` votes REJECT
on an oversized proposal before it builds a frame at all, which is version
one's rule and is recorded in
`adapter/cometbft/internal/bridge/application.go`.

So over the wire the application can answer decisions `0` through `5`, and `6`
and `7` are defence in depth: `6` against a caller that bypasses the frame, `7`
against a chain-state failure no peer can induce. The suite records both
absences as measurements. It builds the over-count and over-length frames and
requires the decoder to refuse them without reaching the clock, and it proves
both bytes at the encoder, where every value can be produced.

## Evidence

`version-nine-transport` is one CTest entry over three translation units and a
support header:

- **The pipeline.** The `restart` run's four contiguous blocks are driven as
  version-two frames. Every finalize response reproduces the recorded root and
  block identifier. Every admitted input carries a receipt that decodes as
  version nine's, and whose own result byte produces the code beside it. Commit
  and Info report the recorded height, **timestamp**, and root, and a
  byte-identical repeated finalize answers byte-identical octets.
- **The clock, counted over the wire.** Each decided proposal frame reads it once.
  A proposal while a block is staged answers status `3` without reading it.
  Finalize, its repeat, Commit, Info, CheckTx, PrepareProposal, InitChain, and
  both fatal finalizes read it zero times.
- **Decisions `0` through `5` from the application**, each on its own, each as
  one octet under status zero, including both sides of C5.
- **Statuses from the application**: `1` from a mismatching genesis stamp, `3`
  before initialization and while staged, and `7` and `8` from decided blocks
  failing C1 and C2, after which the application answers `3` to everything.
- **Replay.** A finalize at the staged height with a fresh stamp is refused. After
  a restart the height replays from the file with its own stamp, and the whole
  finalize body is byte-identical to the first.
- **The encoder alone**: all eight decision bytes, `8` and `255` refused;
  statuses `1` through `6` on all seven kinds; `0`, `7`, and `8` refused through
  the `ApplicationError` path; `7` and `8` written on kind 6 through their own;
  Info and Commit octet for octet; and the receipt refusals. Each receipt refusal
  sits beside an accepted control, so a suite that passed against an encoder
  refusing everything is not possible.
- **A real socket.** The version-nine overload serves init, proposal, finalize,
  and commit, and reads the clock once. A version-one frame then offered to it
  ends the connection as a `protocol_failure` **with no response written**.

**The first hosted run found a defect in the suite, not in the transport.** The
suite's response reader held a `std::span` over a returned temporary, so every
case that built one from `require_ok(...).body` read freed memory. Both sanitizer
presets named it as a heap-use-after-free and no other entry failed. The reader
now owns a copy.

**What this slice could not do locally.** The dependencies are built from source
by CMake, and building libsodium, SQLite, and the kernel is what the owner's
resource rules reserve for hosted runners. The new sources and all three test
units were checked with `-fsyntax-only` under both GCC 12 and Clang with the
project's `-Wall -Wextra -Wpedantic -Werror`. Every runtime claim above is the
hosted matrix's. ADR 0083's mutation probes needed a built suite, so none were
run here. The suite's cases are instead written so that each refusal has an
accepted control beside it.

## Consequences

**The next slice is the node process**: `protocol-application-v9`, which binds a
platform real-time clock, opens `SQLiteLedgerV9`, and serves this overload,
with a headless process test. After it comes the Go adapter's version-two client
and its ABCI conversion, then the devnet, then the deletion of `src/v8/`.

**Versions one and eight are untouched in behaviour.** Their overloads now name
`WireV1` explicitly and read the same decoders they always did, and both of
their suites still run.

## Owed

**The response decoder tests the contract lists belong to the adapter.**
Truncation at every field of the changed response payloads, an out-of-range
decision byte, and hostile counts and lengths are properties of the side that
*reads* a response, which is the Go bridge. The C++ side only writes responses,
and a C++ reader over them would be test code testing test code.
