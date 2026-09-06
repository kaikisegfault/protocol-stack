# ADR 0068: The version-eight application layer, and the figure a rebinding cannot get wrong quietly

- Status: Accepted
- Date: 2026-09-06
- Follows: [ADR 0058](0058-the-version-seven-application-layer.md), [ADR 0059](0059-the-version-seven-transport.md)

## Context

[ADR 0067](0067-the-version-eight-owning-store.md) made a version-eight state
durable. It did not make one *reachable*: nothing could answer an `info`, accept
a proposal, finalize a block, or commit one, so
[ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md)'s
fifth step remained before a consensus engine could drive a version-eight chain
at all.

[ADR 0058](0058-the-version-seven-application-layer.md) already decided what this
layer *is* — the seven ABCI operations, `finalize_block` pure and staging what it
produced, `commit` replaying the same block through the store and requiring the
store to reproduce exactly what was staged, the terminal latch after any refusal
once the chain is ready, `process_proposal` executing against a candidate copy so
a block this node cannot execute is voted against rather than fatal later, and
the store taken by value because one local writer is [ADR 0007](0007-sqlite-ledger-persistence.md)'s
contract. [ADR 0059](0059-the-version-seven-transport.md) decided the frame
format and that a ledger version adds a response encoder and a dispatcher rather
than a wire. **All of it carries over unchanged**, and this ADR records only what
version eight makes different.

## Decision

### The owed uptime item is closed rather than satisfied

ADR 0058 recorded, under *Owed*, that `execute_block` takes an uptime schedule
and version seven's application does not supply one — so **"a chain driven
entirely through `ApplicationV7` writes no cycle assignment record and accrues
nothing to any seat"** — and named wiring a measurement to this layer as "the
dependency between here and a chain that pays anyone".

Version eight's prologue derives the schedule from the seat table and the window
records. **There is no parameter to supply.** Both call sites — `process_proposal`
and `finalize_block` — lose an argument rather than pass a null one, and the owed
item disappears instead of being satisfied. That is the step that unblocks
requirement 13's *economic* scenarios, and it is why the adversarial half of that
requirement was ordered after the kernel rather than before it.

**It is not free.** Under version eight a block audits every in-scope seat at
every height, so `process_proposal` evaluates one selection digest per in-scope
seat to decide a vote where at most heights it previously evaluated nothing. ADR
0058 accepted the copy-and-execute cost when it was cheaper; the reason it
accepted it is unchanged, and this ADR records the new figure rather than
revisiting the decision.

### Five figures move, and the fifth is the one worth recording

Four were on the list this slice started from: `kApplicationProtocolVersionV8`
becomes 8, the expected app state becomes `"protocol-stack-v8"`,
`kReceiptVersion` becomes 8 in the encoder's own assertion, and `execute_block`
loses its schedule.

The fifth was not, and it is the interesting one. **The receipt magic prefix
carries the receipt version as its last octet**, and version seven's encoder
writes it out as a literal — `{'P','S','R','C', 0, 7}` — with a
`static_assert(kReceiptVersion == 7)` two lines below it that says nothing about
the array. A rebound version-eight encoder therefore compares version-eight
receipts, whose own bytes carry 8, against a version-seven prefix, and **no
finalized block encodes at all**.

Version eight derives the octets from `v8::kReceiptVersion` instead of restating
them, which is what makes the assertion beside them cover the prefix rather than
stand next to a second copy of the same number.

**That failure mode is the opposite of ADR 0067's and the pair is the lesson.**
The store's `head_snapshot` minimum was a moved figure that, left stale, merely
moved a refusal one layer later — invisible to every test that only asked whether
the refusal happened. The receipt prefix is a moved figure that, left stale,
breaks the first block on the happy path. **A figure that moves with a version is
either checked on the happy path or it needs a boundary case; there is no third
kind**, and knowing which one you have is the question worth asking before the
tests are written rather than after.

### No version-eight wire, and a third overload rather than a second server

`wire_v1` decodes every request for both versions. The 20-octet header, the seven
message kinds, the six wire errors, and the five request payloads carry no
ledger-version meaning, so version eight adds `response_v8.cpp` and
`dispatcher_v8.cpp` and one more `serve_connection` overload on
`UnixSocketServerV1`. **The `V1` in that name is the frame format's version, not
the ledger's**, which is exactly why a new ledger version costs an overload here
and not a socket.

## Evidence

`version-eight-application` drives the `carried` scenario's four contiguous
blocks through all seven operations with the application **rebuilt from the file
between each pair**, and every block must reproduce its recorded
`resulting_state_root` from `test-vectors/economy-transition-v8-execution.txt`.
The refusals are exercised in full: `init_chain` under another chain identity, at
an initial height that is not one, and with a foreign app state; committing with
nothing staged; finalizing a block this chain cannot be at; finalizing a second,
different block at one height; proposing while a block is staged; and the
terminal latch after each.

`version-eight-transport` sends the same blocks as request frames over a real
Unix socket and reads the response frames back, so the encoder, the dispatcher,
and the third `serve_connection` overload are checked against bytes rather than
against return values.

**Two boundary checks are new and both apply ADR 0067's rule.** The protocol
version is pinned to its literal with a `static_assert` in both suites: comparing
`info().application_version` against `kApplicationProtocolVersionV8` — which the
inherited checks do — is a claim that the value reaches the caller and no claim
about *which* value it is, and it passes unchanged with version seven's 7 still in
place. And `init_chain` is refused with **version seven's** app state beside
version one's: version one's is the case version seven's own suite already had,
and version seven's is the string a stale deployment would actually still be
sending — the only thing distinguishing a moved app-state constant from an
unmoved one.

**The receipt prefix needed no new test**, and that is the finding rather than an
omission. The inherited transport suite failed on the first finalized block with
*"the response did not encode"* the moment the rebinding was compiled, which is
what a figure checked on the happy path does.

**The normalising diff is the rest of the review.** Rendering both versions with
`sed 's/v7/vX/g;s/V7/VX/g'` and `sed 's/v8/vX/g;s/V8/VX/g'` and diffing them
shows exactly the intended deltas and nothing else. It is **empty** for the
dispatcher header, the response header, the internal header, and the dispatcher
translation unit.

**Version seven's transport suite was rebuilt and re-run** after the shared
`serve_connection` overload was added, because that file is not version-eight's
and an added overload is the kind of change that can move overload resolution
somewhere else. It passes unchanged.

**Seven mutation probes, each checked to have changed the code the test runs.**
Six are caught and each names its own subject: the protocol version left at 7
fails the `static_assert`; the app state left at version seven's on **both**
sides — the realistic blanket-rebinding error, where the happy path still agrees
with itself — is caught *only* by the new version-seven refusal case; the app
state left at version seven's on the implementation side alone is caught by the
happy path; the receipt prefix restated as a literal 7 fails the first finalized
block; a refusal that does not latch is caught by "init_chain after a refusal";
and a repeated finalize that returns the stage whatever was asked is caught by
"finalizing a second, different block at one height".

**The seventh passed uncaught, and it is worth stating plainly rather than
burying.** Removing `commit`'s requirement that the store's commit record equal
the staged one changes nothing any test observes — **the equality ADR 0058 calls
"the whole safety argument" has no test that can fail it.** That is inherited
from version seven rather than introduced here, and it is a guard with no
constructible violating input rather than a defect: making the store disagree
with the kernel about a block both just accepted, on the same head, would take a
fault-injection seam that returns a corrupted commit record, and adding one would
be test-only machinery in production code — the thing ADR 0057 and ADR 0067 each
rejected. It is recorded here so a later session finds it written down instead of
rediscovering it, and so that a reader of ADR 0058 knows the argument rests on
inspection rather than on a failing test. **Do not delete the guard**: M3.13p's
prefix-width assertion was the same shape, and the lesson there was that a guard
with no violating input is not a defect.

## Consequences

- **A version-eight chain can be driven by a consensus engine.** What remains
  before one runs is ADR 0065's step 6 — `protocol-application-v8` and the Go
  adapter's version-eight client — and then step 7's deletion.
- `protocol_application` compiles two application layers and two response
  encoders until step 7, which is the cost ADR 0065 already states. It gains four
  translation units and no new dependency.
- **`main_v7.cpp` bounds its genesis read at 110 octets and a version-eight
  genesis file is 142.** That is step 6's figure, recorded here because this is
  the slice that made the layer beneath it version eight.
- ADR 0058's other owed items are untouched: the replay handshake, and the fact
  that nothing here speaks to CometBFT until the adapter does.

## Alternatives considered

**Give the store or the application a way to supply an uptime schedule anyway,
for symmetry with version seven.** Rejected: the schedule is derived from state
every node has, and an interface that could supply a different one is an
interface that could take a node out of consensus.

**Keep the receipt prefix as a literal and add a test that pins it.** Rejected:
the prefix is already checked on every finalized block, so the test exists — what
was missing was the derivation. A literal plus a test that pins the literal is
two copies of a number and a check that they agree.

**A version-eight wire and a `UnixSocketServerV8`.** Rejected for ADR 0059's
reason, which has not weakened: nothing in the frame format carries ledger
meaning, and a second copy would be a second place for a framing rule to be
wrong.
