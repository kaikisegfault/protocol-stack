# Consensus application contract v2

Status: Accepted for M3 version nine

This document is normative for the version-nine boundary between an ordering
engine and the persistent protocol application. It does not change the canonical
genesis, transaction, execution, receipt, block, or state-root rules in
[`economy-transition-v9`](economy-transition-v9.md), and it does not restate
[`calendar-v1`](calendar-v1.md)'s rules — it decides **where each one runs**.

This remains an adapter-only compatibility contract. The ordering adapter
supplies a height, a timestamp, and ordered raw transaction bytes. The C++
application remains the only authority for admission, execution, receipts,
application hashes, and durable state.

## Relationship to version one

[`consensus-application-v1`](consensus-application-v1.md) is version one's
contract and remains accepted, unedited, and the record for the M1 network. Two
of its sentences are false of version nine, and closing them is why this document
exists:

- it lists timestamps among the values that are **"not application transition
  inputs"**, and version nine's header carries one that execution reads; and
- it freezes the **local frame version at `1`**, and three request payloads and
  three response payloads change shape.

**Everything version one fixes that version nine does not touch is inherited by
reference and the list is closed.** The inherited set is: the ten boundary
invariants, the deployment identity's SQLite, genesis-file, and socket rules, the
four-validator topology and its port derivation, the supervisor's phase order and
bounds, the CheckTx admission rules and byte limit, PrepareProposal's selection
rules, the staging and Commit atomicity rules, the crash-and-replay table, the
primitive encoding, the unsupported-ABCI-feature list, and the operational
meaning of every diagnostic. Where a section below is silent, version one governs.

**Version eight has no contract document of its own**, and that is a gap this
document closes rather than inherits; see
[The drift version one's table already carries](#the-drift-version-ones-table-already-carries).

## What version two changes

1. The clock becomes reachable, from exactly one operation, and never crosses the
   local boundary.
2. `ProcessProposal`, `FinalizeBlock`, and `InitChain` carry a timestamp.
3. `calendar-v1`'s five ordered conditions are placed: all five in
   `ProcessProposal`, the first three in `FinalizeBlock`, and the two that are C5
   nowhere else, structurally rather than by convention.
4. A timestamp failure becomes a block-level outcome with its own observable
   value, in two spaces that differ because the two paths have opposite correct
   responses.
5. The local frame version becomes `2`, and the message table records the real
   payload shapes, including the two version seven and eight already changed.
6. `Info` and `Commit` expose the durable timestamp beside the durable height.
7. The CometBFT genesis gains a fifth derived, enforced value.

## Invariants

Version one's ten boundary invariants hold unchanged. Its eleventh sentence is
replaced:

> Proposer identity, block hash, vote data, timestamps, wall-clock values,
> validator metadata, RPC metadata, connection order, and thread scheduling are
> not application transition inputs.

becomes, for version nine:

**The agreed block timestamp is a transition input and is the only one added.**
Proposer identity, block hash, vote data, validator metadata, RPC metadata,
connection order, and thread scheduling remain outside the transition. A
machine's own clock reading is **not** a transition input, is never committed,
never serialized, and never crosses the local boundary; it decides one vote and
is then discarded.

Three further invariants are added:

11. every value the local protocol carries is a value the network has agreed on
    or is being asked to agree on;
12. no operation other than `ProcessProposal` reads a clock, and no operation
    reachable on a replay, restore, or reconstruction path can reach one;
13. the millisecond a replica derives from the engine's timestamp is a total,
    deterministic function of the agreed value, so every correct replica derives
    the same one.

## The clock, and the one value that never crosses the boundary

C5 is the only rule in `calendar-v1` whose input is not in the block. Something
must read a clock, exactly once, and this contract decides what.

**The C++ application reads its own clock. The local protocol does not carry a
clock reading and the Go bridge never supplies one.**

The clock source is a callable returning milliseconds since
`calendar-v1`'s `TIMESTAMP_EPOCH`, bound when the application is constructed. In
a deployment it is the platform real-time clock; in a test it is a supplied
value. It is not configuration that reaches canonical state, it is not
serialized, and it is not reported by any response.

The reading is taken **once per `ProcessProposal` request, before any condition
is evaluated**, so that the five ordered conditions see one value. A
re-read between conditions 4 and 5 could satisfy neither or both, and the
resulting vote would depend on how long the evaluation took.

**Why the application and not the bridge.** Three reasons, in the order they
matter:

- Version one's third invariant says the adapter cannot create a block result.
  A clock reading decides a vote. A bridge that supplied it could make this
  machine accept a height its own rules refuse, and **nothing downstream would
  ever notice**, because C5 is never re-checked on any later path.
- It is what makes invariant 11 true. The clock is the one value in the system
  that is neither agreed nor proposed for agreement, and keeping it off the wire
  is the difference between that being a rule and being a coincidence.
- The application already owns the durable head, so it already holds the
  predecessor timestamp that C2 compares against. Splitting `calendar-v1`'s five
  ordered conditions across two processes would put the first three in C++ and
  the last two in Go, and **the order is normative** — a split implementation
  could not report the first condition that fired without a round trip.

**Rejected: the bridge reads the clock and passes it in the frame.** It is the
smaller change and it is the one this slice reached for first. It fails the first
reason above outright, and it has a second cost: the frame would then carry a
field that must not be committed, beside six that must be, and every later reader
of the wire would have to know which is which.

**Rejected: the kernel reads the clock.** It is not available. `accept_timestamp`
takes the reading as a parameter precisely so that the kernel owns no clock, and
`economy-transition-v9` makes that a rule rather than an accident.

### What `calendar-v1` requires of a binding version, and where each is met

`calendar-v1` names three obligations for the version that binds it. They are
recorded here against their answers, because a reader comparing the two documents
would otherwise have to reconstruct the mapping.

| Obligation | Where it is met |
| --- | --- |
| apply C1 and C2 in execution | `FinalizeBlock`, through the kernel's block transition, on every path including replay |
| expose the C5 check to its consensus adapter separately from execution | `ProcessProposal`, which is the operation the adapter drives on the admission path and the only one that reads a clock; execution has no access to it |
| carry `TIMESTAMP_TOLERANCE_MILLIS` as a consensus parameter | a fixed protocol constant of the ledger version, at 60,000 ms |

**The third is worth stating precisely, because the phrase can be misread.**
`TIMESTAMP_TOLERANCE_MILLIS` is a constant of the protocol, not a CometBFT
`ConsensusParams` entry and not adapter configuration. It is fixed at 60,000 ms
by `calendar-v1` and lives in the kernel. A settable tolerance would contradict
this contract's own rule that consensus-parameter updates are always empty, and
would let two replicas of one chain disagree about which proposals to accept
while agreeing on every committed value — the failure this whole separation
exists to prevent.

## Deployment identity

Version one's configuration is unchanged: an absolute SQLite path, the exact
canonical genesis byte file, and an absolute local Unix-socket path. Two things
are added.

**The application binds a clock source**, as above. A deployment that cannot
read a clock cannot vote on a proposal and must fail to start rather than vote
on an assumed value.

**Canonical genesis validation applies C1 and reads no clock.** A version-nine
genesis file whose `genesis_timestamp` is outside
`[MIN_TIMESTAMP_MILLIS, MAX_TIMESTAMP_MILLIS]` is malformed and the application
refuses to start. One inside the range is well-formed regardless of what any
machine's clock says. This is forced and not a preference: the chain identity is
`H(label || genesis bytes)`, so a validity rule that read a clock would make two
machines disagree about a chain's own identifier.
`economy-transition-v9`'s
[A genesis timestamp far from civil time](economy-transition-v9.md#a-genesis-timestamp-far-from-civil-time)
states the consequence, and it is a liveness one: a genesis in the future halts
the chain at its first block until civil time reaches it, refused as
`TIMESTAMP_NOT_MONOTONIC` rather than as a tolerance failure.
**Correction of 2026-09-22:** under CometBFT `v0.39.4` the first block's stamp
*is* the genesis time, so a future genesis only delays the start, and a genesis
more than `TIMESTAMP_TOLERANCE_MILLIS` in the past halts the chain at height one
for good;
[ADR 0088](../decisions/0088-the-launcher-derives-the-genesis-time-and-the-first-block-carries-it.md)
records it.

The CometBFT genesis values become **five**:

- `chain_id`: ASCII `ps-` followed by the RFC 4648 URL-safe base64 encoding of
  the derived 32-byte protocol chain ID, with no padding — version one's rule,
  over version nine's chain ID;
- `initial_height`: decimal `1`;
- `app_hash`: the 64 uppercase hexadecimal characters of the version-nine
  height-zero state root;
- `app_state`: the exact UTF-8 JSON string bytes `"protocol-stack-v9"`,
  including the two quote bytes;
- `genesis_time`: the canonical `genesis_timestamp`, rendered with **exactly
  millisecond precision** and a zero nanosecond remainder.

The node launcher derives all five from the same validated canonical genesis and
refuses an existing CometBFT genesis file that differs in any of them.

**`genesis_time` is enforced, not decorative.** C2's first-block rule is
`t(1) >= g`. If the engine and the application disagree about `g`, they disagree
about which first blocks are valid, and the disagreement is silent until the
chain will not start. Enforcing equality at initialization converts that into a
refusal at the one moment an operator is looking.

## The timestamp conversion, and what the bridge may refuse

CometBFT transports a time as a protobuf `Timestamp` of separate `seconds:i64`
and `nanos:i32`. The ledger's unit is the millisecond. The conversion is
normative because the result enters the state root, so every replica must derive
the same one from the same agreed value.

```text
millis = seconds * 1000 + nanos / 1000000
```

with integer division truncating toward zero, evaluated as a checked
multiplication.

**The bridge refuses only what it cannot represent**, and refuses it as an
invalid request:

- `seconds < 0`, which no `u64` millisecond count represents;
- `nanos` outside `[0, 999999999]`, which is not a well-formed `Timestamp`;
- a `seconds * 1000` that overflows, which is a value no clock produced.

**Everything representable is passed through.** A timestamp above
`MAX_TIMESTAMP_MILLIS` is representable and is **not** refused by the bridge; it
is passed to the application and refused there as `TIMESTAMP_RANGE`. This is the
rule that keeps `calendar-v1`'s ordered conditions reachable: a bridge that
pre-filtered the range would make C1 untestable end to end, and the first
condition would exist only in a unit test.

**Truncation, not rounding, and the two cases differ.**

- A **block** timestamp truncates. CometBFT's BFT time has nanosecond precision
  and is not a whole number of milliseconds, so requiring an exact remainder
  would reject essentially every real block. Truncation is safe for both rules
  it feeds: a non-decreasing nanosecond sequence stays non-decreasing under a
  monotone map, and the at-most-0.999 ms downward shift is four orders of
  magnitude inside a 60,000 ms tolerance.
- A **genesis** timestamp must have a zero nanosecond remainder, and a nonzero
  one is a refused genesis. The launcher writes this file, so it controls the
  value, and requiring exactness makes the comparison against the canonical
  genesis field injective. A truncating genesis conversion would accept two
  distinct CometBFT genesis files for one canonical chain.

## Application lifecycle

Version one's ownership, staging, and serialization rules hold unchanged: one
live store, at most one staged block, all application operations serialized, and
read-only admission serialized with Finalize and Commit.

The durable head is now **two scalars and a root** — a height, a timestamp, and a
32-byte state root — because `economy-transition-v9`'s state commits to both
scalars.

### Info

Info returns:

- application data: ASCII `protocol-stack`;
- application version: ASCII `9.0.0`;
- application protocol version: unsigned integer `9`;
- the last durable block height;
- **the last durable block timestamp**;
- the exact 32-byte durable state root as the last application hash.

Everything else is version one's: the ABCI version is required to be exactly
`2.0.0`, a staged candidate is never exposed, a restart opens and validates
SQLite before returning the old or new durable head, and the bridge fails closed
above signed 64-bit maximum height.

**The timestamp is redundant against the root and is reported anyway**, which is
deliberate. The root commits to it, so two agreeing roots already imply agreeing
timestamps — but a root is a hash, and it proves agreement without showing the
value. Reporting the field is what makes a divergence **diagnosable** rather than
merely detectable, and Info is version one's "authoritative recovery handshake":
a handshake that omitted half the head would be one.

### Init chain

InitChain gains the genesis timestamp. The application compares **four** values
against its own validated canonical genesis — the 32-byte chain ID, the initial
height, the exact application-state bytes, and the genesis timestamp — and
returns its independently computed height-zero root.

A mismatch in any of the four is an invalid request, exactly as version one
treats the first three. Initialization before the first committed block remains
idempotent and performs no state write; initialization after a nonzero durable
height remains a sequence failure.

**InitChain applies C1 and never C5.** The genesis timestamp is compared, not
validated against a clock. Canonical genesis loading already applied C1 before
the application began listening, and applying a tolerance here would make a chain
un-initializable one tolerance-width after its genesis was written — which is to
say, would make every chain un-restartable.

### Check transaction

Unchanged. Admission has no timestamp input: it is exact decoding, chain
comparison, sender derivation, and strict signature verification, none of which
reads a height, a state, or a clock. The 1,048,576-byte request limit and the
four-code response mapping are version one's.

**A kind-22 transaction is admitted here like any other.** Whether a monthly pool
mint succeeds depends on the state it meets, which is `FinalizeBlock`'s question.

### Prepare proposal

**Unchanged, and the fact that it is unchanged is a rule rather than an
omission.** Selection is the longest exact prefix satisfying version one's count,
per-input, and total-length bounds, with bytes neither decoded nor reordered.

PrepareProposal does **not** choose or report a timestamp. Under CometBFT the
block time is the engine's, produced by BFT time from vote timestamps, and
`economy-transition-v9` requires that "the proposer's algorithm for choosing a
value" stay unconstrained beyond the accepted value. A contract that had the
application select the stamp would constrain exactly that, and would foreclose
the deployment in which BFT time supplies it.

### Process proposal

ProcessProposal receives a height, a timestamp, and the ordered raw list. It is
**the only operation that reads a clock**, and it reads one once.

It returns a **decision**, in this evaluation order:

| Decision | Name | Condition |
| ---: | --- | --- |
| `0` | `ACCEPTED` | none of the below |
| `1` | `HEIGHT_NOT_NEXT` | the height is not the durable height plus one, or the next height is not representable |
| `2` | `TIMESTAMP_RANGE` | the timestamp is outside `calendar-v1`'s accepted range |
| `3` | `TIMESTAMP_NOT_MONOTONIC` | the timestamp is below the durable head's, or below genesis at height one |
| `4` | `TIMESTAMP_AHEAD_OF_TOLERANCE` | `t > own_clock + TIMESTAMP_TOLERANCE_MILLIS` |
| `5` | `TIMESTAMP_BEHIND_TOLERANCE` | `t < own_clock - TIMESTAMP_TOLERANCE_MILLIS` |
| `6` | `RESOURCE_BOUND` | the raw count, an input length, or the checked total exceeds its bound |
| `7` | `NOT_EXECUTABLE` | the candidate execution rejected the block whole |

The adapter votes ACCEPT on `0` and REJECT on every other value. **Every decision
is a vote and none is an error**: a peer proposing a bad timestamp is an ordinary
event on a live network, and a contract that made it an application exception
would let one malformed proposal stop a correct machine.

**Decisions `0` through `5` are exactly `calendar-v1`'s ordered conditions**, in
its numbering, and a conforming implementation maps its kernel condition values
onto them without a translation table. `6` and `7` are this contract's own and
are numbered after the last kernel condition. An implementation **must** assert
that the kernel's condition count is 6, so that a later version adding a sixth
condition breaks the build rather than silently aliasing `RESOURCE_BOUND`.

**Why the ordered conditions run before the bounds.** The vote is identical under
either order, so this decides only what is *reported* — and therefore what is
testable. `calendar-v1`'s order is normative and total, and a proposal that fails
both a bound and a timestamp rule should report what `calendar-v1` says fires
first.

A staged block already existing, a terminal application, or an application not
yet initialized is a **sequence failure status** and not a decision, which is
version one's rule unchanged: those describe this machine, not the proposal.

The candidate execution is version eight's: the block runs against a copy of the
durable head, nothing is written, and a block this node cannot execute is voted
against here rather than accepted and made fatal at `FinalizeBlock`. Under
version nine the copy also carries the head's timestamp, so the candidate's C1
and C2 are already satisfied by the time it runs and decision `7` can only mean
an invariant, conservation, or bound failure inside the block.

### Finalize block

FinalizeBlock receives a height, a timestamp, and the ordered raw list, accepts
only the next durable height, constructs an independent in-memory ledger from the
owned durable head, and calls version nine's ordered block transition. It does
not open a SQLite write transaction and does not modify the durable ledger.

**It applies C1 and C2. It does not, and cannot, apply C5.** This is the rule
that is easy to get wrong and silent when it is wrong, so the contract requires
it to be **structural**: the operation has no clock parameter and no access to the
bound clock source, so there is no argument a caller could pass and no branch a
maintainer could add without changing a signature. A machine that re-applied the
tolerance here would reject the chain's own past one tolerance-width after
producing it, and every correct replica would do so at a different moment.

Per-transaction results are version one's scheme over version nine's result
space:

| Kernel outcome | ABCI code | Data |
| --- | ---: | --- |
| admitted and execution success | `0` | exact canonical receipt |
| malformed transaction | `1` | empty |
| wrong chain | `2` | empty |
| invalid signature | `3` | empty |
| admitted, execution result `r` in `1..44` | `256 + r` | exact canonical receipt |

The mapped range is `257` through `300`. **Version nine adds no result code**, so
the range is version eight's, and
[`economy-transition-v9`](economy-transition-v9.md#result-codes) holds the result
table rather than this document. Code zero uses an empty codespace; every nonzero
code uses `protocol-stack-v9`. Log, info, events, gas wanted, and gas used are
empty or zero. An admitted result always carries its exact canonical receipt,
including failures; an admission failure never carries one.

The response application hash is the exact 32-byte resulting state root, and the
response also carries the block identifier — see
[The drift version one's table already carries](#the-drift-version-ones-table-already-carries).
Validator updates, consensus-parameter updates, and events are empty.

**A timestamp failure here is fatal, and the status names which rule failed:**

| Status | Meaning |
| ---: | --- |
| `7` | C1 failed on a decided block |
| `8` | C2 failed on a decided block |

FinalizeBlock is only ever called on a block the network already decided. If C1
or C2 fails, this machine's rules and the network's decision disagree about
history, and a deterministic application that has found such a disagreement
cannot continue and be trusted. It stops rather than guess which was right, which
is version one's existing treatment of an invalid next height and an internal
block failure.

**There is deliberately no status for either C5 condition, and the absence is the
point.** The status space is testable for it: an implementation whose status
space contains a tolerance value has a tolerance reachable on the replay path,
which is the defect this separation exists to prevent. A conforming test asserts
the absence rather than the presence.

Everything else is version one's: after a successful response the exact stage is
retained, a byte-identical repeated request returns the byte-identical staged
response, and any different Finalize or proposal request while a stage exists is a
sequence failure.

### Commit

Commit requires one staged block, applies it through the store with the exact
staged height, timestamp, and raw byte sequence, and requires the resulting
durable head to exactly equal the staged preview before returning success. The
store commits the whole block before the application publishes its new owned
head. The ABCI Commit response carries no application hash in ABCI `2.0.0` and
its retain height is zero.

The local Commit response carries the durable **height, timestamp, and root**,
for the same reason Info does.

A kernel rejection, preview mismatch, storage error, close error, recovery error,
missing stage, or duplicate Commit is fatal, and the application never advances to
another height after a terminal storage failure.

## Crash, disconnect, and replay

Version one's table holds unchanged, with the durable head reading two scalars
instead of one:

| Interruption point | Durable application head after restart |
| --- | --- |
| before or during FinalizeBlock | old head |
| after FinalizeBlock, before Commit | old head |
| before the store's durable commit | old head |
| after the store's durable commit, before response | new head |
| after Commit response | new head |

**One rule is added, and it is the one version nine could get wrong quietly.**
When the durable head is old and the ordering engine replays the same height, the
application must reproduce byte-identical results and application hash — which
now requires replaying the **same timestamp**. A replay that advanced the height
and left the stamp behind, or supplied a fresh one, would commit a root naming a
height the stamp does not belong to, and **every later block would still satisfy
C2** because the stale stamp is smaller. The failure would be a wrong root rather
than a refusal, which is the direction that hides.
`economy-transition-v9` records the same shape of defect against the kernel's own
`advance_to`; this is its boundary form.

The engine persists a decided block, including its timestamp, before calling
FinalizeBlock, so the replayed value is available and is the agreed one. A
divergence between the engine's stored block timestamp and the application's
durable head at an equal height is operator-visible divergence and fails closed,
exactly as a differing chain ID, genesis, or application hash does.

## Local application protocol

The local protocol remains operational framing rather than canonical ledger
encoding. Version one's primitive encoding is unchanged: fixed-width big-endian
integers, `i64` two's complement, `bytes32`, `blob` as `length:u32 || bytes`,
`blob_list` as `count:u32 || blob[count]`, one-byte Booleans accepting only `0`
or `1`, no padding, no trailing bytes, and a 33,554,432-byte maximum outer
payload.

### Frame

```text
magic[4] || protocol_version:u16 || direction:u8 || kind:u8 ||
request_id:u64 || payload_length:u32 || payload[payload_length]
```

The magic stays ASCII `PSAP`. **The protocol version becomes `2`.** Direction,
request-id, and framing rules are version one's.

### Message kinds and payloads

| Kind | Name | Request success fields | Response success fields |
| ---: | --- | --- | --- |
| `1` | Info | empty | `app_version:u64 \|\| height:u64 \|\| timestamp:u64 \|\| root:bytes32` |
| `2` | InitChain | `chain_id:bytes32 \|\| initial_height:u64 \|\| genesis_timestamp:u64 \|\| app_state:blob` | `root:bytes32` |
| `3` | CheckTx | `tx:blob` | `code:u32` |
| `4` | PrepareProposal | `max_tx_bytes:i64 \|\| txs:blob_list` | `txs:blob_list` |
| `5` | ProcessProposal | `height:u64 \|\| timestamp:u64 \|\| txs:blob_list` | `decision:u8` |
| `6` | FinalizeBlock | `height:u64 \|\| timestamp:u64 \|\| txs:blob_list` | `root:bytes32 \|\| block_id:bytes32 \|\| result_count:u32 \|\| result[result_count]` |
| `7` | Commit | empty | `height:u64 \|\| timestamp:u64 \|\| root:bytes32` |

Each FinalizeBlock result is `code:u32 || data:blob`, its count must equal the
request raw count, and code/data combinations must match the result rules above
exactly.

**`genesis_timestamp` precedes `app_state` in kind 2** because every
fixed-width field precedes the one variable-length field, which is version one's
own layout rule and is what lets a decoder bound the frame before allocating.

**Kind 5's response is a `decision:u8` and no longer an `accept:Boolean`.** The
Boolean is recoverable as `decision == 0`, and the byte carries which of eight
outcomes produced the vote. **The extra information is safe because it is not
consensus-visible**: ABCI ProcessProposal transports ACCEPT or REJECT and nothing
else, so the value reaches logs and tests and never reaches a peer.

### Response status space

Version one's six statuses, with two added:

| Status | Meaning |
| ---: | --- |
| `1` | invalid request |
| `2` | unsupported operation or version |
| `3` | application sequence failure |
| `4` | kernel block failure |
| `5` | storage or recovery failure |
| `6` | internal application failure |
| `7` | decided block failed C1 |
| `8` | decided block failed C2 |

Status zero requires an empty message and is followed by the kind-specific
success payload. A nonzero status permits a UTF-8 diagnostic of at most 4,096
bytes and no following bytes. Diagnostics remain operational only; the bridge
converts every nonzero status to an ABCI exception and does not place its text in
a consensus result.

**Statuses `7` and `8` are reachable only from kind 6.** Kind 5 reports the same
two conditions as decisions `2` and `3` under a status of zero, because there the
correct response is a vote and here it is a halt.

### The drift version one's table already carries

Version seven added a block identifier to the finalized-block response, and
version eight kept it, **while the frame version stayed at `1` and no contract
document recorded the change.** Two consequences stood until now:

- `consensus-application-v1`'s message table has been stale since version seven,
  and a reader implementing from it would have written a decoder that stops one
  `bytes32` early on every finalized block; and
- a version-one bridge paired with a version-eight application refuses the
  finalize response **at the result count, as a generic protocol failure, on the
  first block** — rather than at the header, as an unsupported version, on the
  first frame. The refusal is real and the existing decoders are correct about
  it; what is missing is that the one field whose job is to announce a shape
  change did not announce one.

Version two closes both: the table above records the real shape, and moving the
protocol version to `2` moves the refusal to the header, where it names the
actual fault. **This is the reason the field exists**, and version nine is the
first version to use it.

Nothing about version seven's or version eight's recorded behavior, vectors, or
committed roots changes. The drift was in the document, not in the bytes.

## Unsupported ABCI features

Version one's list is unchanged: the application mempool, vote extensions, state
sync, application snapshots, validator changes, and consensus-parameter changes
are disabled; `mempool.type = "flood"` and `p2p.libp2p.enabled = false`; the
bridge fails if CometBFT invokes InsertTx or ReapTxs; Query returns code `1` with
codespace `protocol-stack-v9` and no state data; ExtendVote returns empty bytes
and VerifyVoteExtension accepts only empty bytes; state-sync listing returns no
snapshots and offer, load, or apply requests are rejected.

**CometBFT's own timestamp validation is not relied upon and is not a
substitute.** The engine may apply its own rules to a proposal's time; this
contract's conditions are applied regardless and are the only ones whose outcome
reaches the application's vote.

## The four-validator local topology

Version one's topology governs: independent homes, block stores, node keys,
private-validator state, bridges, application processes, sockets, and databases;
the complete loopback-only persistent-peer mesh; the derived port triple and its
validity rule; the supervisor's phase order, its 20-second endpoint bounds and
90-second convergence bound; and the stop, restart, and retention rules.

Three deltas:

- the byte-identical common genesis now additionally carries the derived
  `genesis_time`, and a differing value is fatal and never repaired in place;
- the network-health observation adds the durable **timestamp** to the set of
  values all nodes must report identically, beside the chain ID, block height,
  block-header application hash, ABCI Info height, and current application root.
  ABCI's Info carries no stamp, so the durable stamp is compared where the
  durable head is read, by the independent audit over version two's Info. The
  live observation compares the root, which commits to the stamp
  ([ADR 0090](../decisions/0090-the-version-nine-devnet.md));
- a replica whose clock is outside `TIMESTAMP_TOLERANCE_MILLIS` of its peers'
  votes against proposals it should accept. **This is a liveness condition, not a
  safety one**, it is invisible to every value the health check compares, and it
  is the first operational failure mode in this project that a correct,
  fully-synchronized, agreeing replica can exhibit. An operator diagnoses it from
  decision `4` or `5` in the application log.

## Versioning and migration

Application protocol version `9`, local frame version `2`, codespace
`protocol-stack-v9`, the decision space, the status space, and every result code
mapping in this document are frozen for the version-nine network.

A replacement bridge may change transport implementation but must reproduce this
lifecycle, this conversion, this decision space, and this result mapping. A
change to ordered input meaning, the timestamp's placement or unit, result codes,
application hashes, commit atomicity, or replay behavior requires a new accepted
application-contract version and coordinated activation. A database or canonical
ledger migration follows the separate storage and transition compatibility rules.

**Versions one and two coexist as documents.** Version one remains accepted and
unedited, and every M1 artifact recorded under it remains in place and passing.

## Compatibility boundary

**Frames.** A version-one frame and a version-two frame differ in the protocol
version field, so neither is accepted by the other's decoder and the refusal is
`unsupported_version` at the header rather than a misparse at the payload.

**Payloads.** Kinds 1, 2, 5, 6, and 7 change shape. Kinds 3 and 4 do not.

**Statuses.** Statuses `7` and `8` are new; `1` through `6` keep their version-one
meanings exactly.

**ABCI.** The ABCI version remains `2.0.0`. Nothing in this document requires a
CometBFT change beyond the genesis `genesis_time` value and the pinned
configuration version one already fixes.

**What is not claimed.** No accepted M1 or version-two through version-eight
vector, digest, receipt, root, or recorded devnet result changes, and none is
recomputed under this contract.

## What this contract does not establish

**It does not make a machine's clock correct.** C5 bounds an accepted stamp
against a correct machine's own reading; nothing here proves a machine's reading
is correct. A network whose machines are uniformly wrong by more than the
tolerance cannot make progress, which is the safe failure.

**It does not specify how a deployment obtains civil time.** NTP configuration,
clock discipline, and drift monitoring are operational concerns outside this
boundary, and a later operations document may constrain them without changing a
rule here.

**It does not implement anything.** The snapshot, the owning store, the
application layer, the transport, the node process, and the ABCI adapter are all
still version eight's. This document is what those ports must satisfy; it is not
the port.

**It does not revisit the grinding surface.** `economy-transition-v9` records
that committing the timestamp to the state root widens a quiet block's beacon
grinding surface by about `2^16.9` values and refers it to the independent review
requirement 15 already owes. Nothing at this boundary changes that figure,
because the boundary neither constructs the beacon nor chooses the stamp.

## The founder-decision gate this document ran

**Eighteen decisions were enumerated before any was judged**, and every one is
delegated.

**Five are already fixed by accepted specifications** and were cited rather than
re-chosen: the unit, the range, the tolerance, the five rules, and their
normative order by [`calendar-v1`](calendar-v1.md); and the placement of C1, C2,
and C5 across the two entry points, the genesis timestamp's C1-only validation,
and the absence of a new result code by
[`economy-transition-v9`](economy-transition-v9.md).

**Thirteen are mechanism, encoding, framing, status-space, packaging, and
naming**, which the founder constitution places outside the reserved set: which
component reads the clock and how it is bound; the timestamp conversion and its
two truncation rules; what the bridge may refuse; the decision space and its
eight values; the two added statuses and the deliberate absence of a third and
fourth; the frame version; the six changed payload shapes; the field order within
kind 2; whether Info and Commit expose the timestamp; whether PrepareProposal
changes; the app-state string; the three topology deltas; and the document,
ADR, issue, branch, and PR shape.

**One was close enough to reserved to be worth naming.** The third topology delta
records that a replica with a skewed clock votes against proposals it should
accept — which is a statement about what a participant must *run* in order to
participate. It is classified **delegated because the requirement is already
accepted**: `calendar-v1`'s C5 is what makes a roughly correct clock a
precondition for voting, and this document places the rule rather than creating
it. Had C5 not already been accepted, choosing to require a clock at all would
have been reserved, and this slice would have stopped and asked.

Nothing in this document sets or changes supply, allocation, beneficiaries,
Founder ownership, creator hierarchy, commercial routing, AI institutional
authority, bridge scope, content permanence, or what an end user must do, own,
run, or receive. **No accepted vector file, specification, manifest, encoding, or
kernel source changes.**

## Required evidence

Before this contract is considered implemented:

- fixed C++ vectors cover every decision value `0` through `7`, each produced on
  its own, and every status `1` through `8`;
- a vector proves `ProcessProposal` reports the **first** condition that fires
  when a proposal violates two of them at once, in `calendar-v1`'s order, for at
  least the height-and-range, range-and-monotonicity, and
  monotonicity-and-tolerance pairs;
- a vector proves both sides of C5 separately, with a supplied clock, and proves
  that a stamp exactly at `own_clock ± TIMESTAMP_TOLERANCE_MILLIS` is accepted
  while one millisecond beyond it is not;
- a test proves `FinalizeBlock` accepts a stamp that `ProcessProposal` would have
  refused for tolerance — the same height, the same bytes, one clock moved — which
  is the single test that distinguishes a conforming implementation from one that
  applies C5 on both paths;
- a test proves the application exposes no path from `FinalizeBlock`, Commit,
  restart, or reconstruction to the bound clock source, and a static assertion
  fixes the kernel's condition count at 6;
- conversion tests cover a negative `seconds`, an out-of-range `nanos`, an
  overflowing `seconds * 1000`, a sub-millisecond block stamp truncating
  downward, a genesis stamp with a nonzero nanosecond remainder, and a stamp
  above `MAX_TIMESTAMP_MILLIS` reaching the application rather than the bridge's
  refusal;
- InitChain tests cover a mismatching genesis timestamp, a mismatching
  `genesis_time` in the CometBFT genesis file, and idempotent re-initialization
  before the first block;
- decoder tests cover truncation at every field of the six changed payloads,
  trailing bytes, a version-one frame presented to a version-two decoder and the
  converse, an out-of-range decision byte, hostile counts and lengths, and
  disconnects;
- a bounded sanitizer-backed fuzzer exercises raw and structured version-two
  frames with valid seeds;
- replay evidence covers a decided height replayed with its **same** timestamp
  reproducing a byte-identical root, and a replay supplied a different timestamp
  refused rather than committed;
- Go tests prove exact ABCI conversion in both directions, unsupported-method
  failure, concurrent connection serialization, and lossless byte transport;
- the four-validator devnet commits a signed transfer and a kind-22 monthly pool
  mint, exposes the same height, timestamp, and root on all four replicas, stops,
  restarts, audits every stopped ledger through an independent C++ process, and
  continues at a later height;
  **Correction of 2026-09-24:** the kind-22 mint's evidence stays below the
  engine, and this list was written without the two walls in front of it. No
  seat on a devnet begun at genesis is in scope before height 28,800, and the
  engine's clock cannot be moved to a month's end.
  `economy-transition-v9-execution-cpp` reproduces all 125 recorded execution
  vectors, the payout and the mint included.
  [ADR 0090](../decisions/0090-the-version-nine-devnet.md) records it. The
  durable timestamp is compared by the independent audit, which reads it over
  Info;
- a devnet test moves one replica's clock beyond the tolerance and proves the
  remaining three continue while the skewed replica votes against proposals the
  others accept;
- existing GCC, Clang, AddressSanitizer, UndefinedBehaviorSanitizer, primitive,
  ledger, differential, persistence, snapshot, archive, recovery, and fuzz gates
  remain green.
