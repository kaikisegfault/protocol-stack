# ADR 0079: The version-nine application contract reads a clock in one operation and nowhere else

- Status: Accepted
- Date: 2026-09-17
- Bounds: [ADR 0074](0074-the-consensus-timestamp-and-the-calendar-month.md),
  [ADR 0077](0077-the-version-nine-clock-and-monthly-settlement.md),
  [ADR 0078](0078-the-version-nine-execution-model.md)
- Follows: [ADR 0068](0068-the-version-eight-application-layer.md),
  [ADR 0059](0059-the-version-seven-transport.md),
  [ADR 0001](0001-sovereign-core-and-replaceable-consensus.md)
- Relates to: `docs/specifications/consensus-application-v2.md`,
  `docs/specifications/consensus-application-v1.md`

## Context

[`economy-transition-v9`](../specifications/economy-transition-v9.md) is
specified, modelled, and in the C++20 kernel. Nothing between that kernel and a
devnet can be ported until the boundary contract exists, because two sentences of
[`consensus-application-v1`](../specifications/consensus-application-v1.md) are
false of version nine: it lists timestamps among the values that are "not
application transition inputs", and it freezes the local frame version at `1`.

Version nine's specification deliberately stopped at naming five requirements a
conforming contract must satisfy and declined to settle them, on the grounds that
a boundary contract is a separate accepted artifact. This record covers settling
them, plus one thing the slice found that was not on anyone's list.

**Most of the contract needed no decision.** The ten boundary invariants, the
staging and Commit atomicity rules, the crash-and-replay table, admission,
proposal selection, the topology, the supervisor, and the unsupported-feature
list are version one's and carry over unchanged. What follows is the set this
slice had to settle, and the finding that outranks all of them.

## Decision

### 1. The C++ application reads the clock; the wire never carries one

C5 is the only rule in [`calendar-v1`](../specifications/calendar-v1.md) whose
input is not in the block, so exactly one component must read a clock. It is the
C++ application, through a clock source bound at construction, read **once per
`ProcessProposal` request before any condition is evaluated**.

**Rejected: the Go bridge reads it and passes it in the frame.** This is the
smaller change and it is the one this slice reached for first. It fails version
one's third invariant — *the adapter cannot create a block result* — because a
clock reading decides a vote, so a bridge supplying it could make this machine
accept a height its own rules refuse. The reason that matters more than the
invariant citation is that **nothing downstream would ever notice**: C5 is not
re-checked on any later path, by design, so a wrong clock from the bridge would
produce a machine that silently votes against its own rules for as long as the
bridge is wrong.

It has a second cost. The frame would carry one field that must never be
committed beside six that must be, and every later reader of the wire would have
to know which is which. Keeping the reading out of the frame is what makes
"every value the local protocol carries is a value the network agreed on or is
being asked to agree on" a rule rather than a coincidence, and the contract
states it as invariant 11 so a later change has something to violate.

**Rejected: the kernel reads it.** Not available, and deliberately so.
`accept_timestamp` takes the reading as a parameter precisely so the kernel owns
no clock.

A third argument settled it rather than the two above. The application already
owns the durable head and therefore already holds the predecessor timestamp C2
compares against. A bridge-side clock would put `calendar-v1`'s first three
ordered conditions in C++ and its last two in Go — and **the order is normative**,
so a split implementation could not report the first condition that fired without
a round trip, or would have to duplicate the head across the boundary to avoid
one.

### 2. Two reporting channels, because the two paths have opposite correct responses

`economy-transition-v9` requires a timestamp failure to be "a block-level status
rather than a transaction result, distinguishing at least the four conditions
`calendar-v1` names". One space would have satisfied the letter and been wrong.

**`ProcessProposal` reports a decision under a status of zero.** A peer proposing
a bad timestamp is an ordinary event on a live network. Reporting it as a nonzero
status would convert it to an ABCI exception, because the bridge converts every
nonzero status to one — so **one malformed proposal from one peer would stop a
correct machine**. The decision is a `u8` whose values `0` through `5` are exactly
`calendar-v1`'s ordered conditions in its own numbering, with `6` and `7` for the
resource bound and an unexecutable block.

**`FinalizeBlock` reports a nonzero status and is fatal.** It is only ever called
on a block the network already decided. A C1 or C2 failure there means this
machine's rules and the network's decision disagree about history, and a
deterministic application that has found such a disagreement cannot continue and
be trusted. Statuses `7` and `8` name which rule failed, because the moment a
machine halts is the moment an operator most needs the reason.

**There is deliberately no status for either C5 condition.** That absence is the
contract's structural statement that the tolerance is unreachable on the replay
path, and it is *testable*: an implementation whose status space contains a
tolerance value has a tolerance reachable from `FinalizeBlock`. A conforming test
asserts the absence rather than the presence, which is the rarer and stronger
shape of evidence.

The decision byte is safe to be richer than the vote because **it is not
consensus-visible**: ABCI ProcessProposal transports ACCEPT or REJECT and nothing
else, so the eight values reach logs and tests and never reach a peer.

### 3. The separation of C5 is structural, not conventional

`ProcessProposal` calls `accept_timestamp`, which takes a clock reading.
`FinalizeBlock`'s path is `execute_block`, which has no parameter that could carry
one, and the contract additionally requires that the operation have no access to
the bound clock source. **There is no argument a caller could pass and no branch a
maintainer could add without changing a signature.**

This is the one rule in the slice that is easy to get wrong and silent when it is:
a machine that re-applied the tolerance on the replay path would reject the
chain's own past one tolerance-width after producing it, and every correct replica
would do so at a different moment, so the network would appear to suffer random
uncorrelated corruption. The kernel already made the separation structural; this
contract requires the boundary to keep it that way rather than re-deriving it.

The single test that distinguishes a conforming implementation from one that
applies C5 on both paths is in the required evidence: the same height, the same
bytes, one clock moved, accepted by `FinalizeBlock` and refused by
`ProcessProposal`.

### 4. The conversion truncates for a block and is exact for genesis

CometBFT transports a time as protobuf `seconds:i64` and `nanos:i32`; the ledger's
unit is the millisecond. The conversion is normative because its result enters the
state root.

**A block timestamp truncates.** BFT time has nanosecond precision and is not a
whole number of milliseconds, so requiring an exact remainder would reject
essentially every real block. Truncation is safe for both rules it feeds: a
non-decreasing nanosecond sequence stays non-decreasing under a monotone map, and
the at-most-0.999 ms downward shift is four orders of magnitude inside a 60,000 ms
tolerance.

**A genesis timestamp must have a zero remainder.** The launcher writes that file
and controls the value, and exactness makes the comparison against the canonical
genesis field injective — a truncating genesis conversion would accept two
distinct CometBFT genesis files for one canonical chain.

**The bridge refuses only what it cannot represent**, and a timestamp above
`MAX_TIMESTAMP_MILLIS` is representable. It is passed through and refused by the
application as `TIMESTAMP_RANGE`. A bridge that pre-filtered the range would make
C1 unreachable end to end, and `calendar-v1`'s first timestamp condition would
exist only in a unit test.

### 5. `genesis_time` becomes a fifth derived, enforced CometBFT genesis value

C2's first-block rule is `t(1) >= g`. If the engine and the application disagree
about `g` they disagree about which first blocks are valid, and the disagreement
is silent until the chain will not start. The launcher derives `genesis_time` from
the same validated canonical genesis as the other four values and refuses a
differing existing file, which converts a silent liveness failure into a refusal
at the one moment an operator is looking.

### 6. The frame version becomes 2, and the message table is corrected

Six payload shapes change: Info, InitChain, ProcessProposal, FinalizeBlock, and
Commit. Version one froze the frame at `1` and said that a change to ordered input
meaning, result codes, application hashes, commit atomicity, or replay behavior
requires a new accepted contract version. This is that version, and the field
exists for exactly this.

## The finding that outranks the decisions

**Version seven added a block identifier to the finalized-block response, version
eight kept it, the frame version stayed at `1`, and no contract document ever
recorded it.** The slice found this while reconciling version one's message table
against `response_v8.cpp` rather than against version one's prose.

Two consequences stood until now:

- `consensus-application-v1`'s message table has been **stale since version
  seven**, and a reader implementing a decoder from the accepted document would
  have written one that stops one `bytes32` early on every finalized block; and
- the mismatch between a version-one bridge and a version-eight application is
  caught **in the wrong place**. Both decoders are correct and the C++ and Go
  comments both say so: version one's refuses at the result count, because the
  block identifier displaces every field after the root. But that is a generic
  protocol failure on the first block, where it should have been an unsupported
  version on the first frame.

The second is the one worth the record, and it is narrower than it first looked —
this is **not** a silent misparse, and the slice checked rather than assumed it.
The protocol version field exists to turn a shape mismatch into a refusal that
names the fault, at the header, before a block is ever executed. Leaving it at `1`
across two shape changes meant the repository had that mechanism and was not
using it, so the diagnosis available to an operator was one layer further from
the cause than it needed to be. **Version nine is the first version to use it.**

Nothing about version seven's or version eight's recorded behavior, vectors, or
committed roots changes — the drift was in the document, not in the bytes, and no
artifact is recomputed. But it is the second time in this project that a figure
which looked like framing turned out to move with the version;
[ADR 0068](0068-the-version-eight-application-layer.md) recorded the first, the
receipt magic prefix carrying the receipt version as its last octet. The pattern
is the same and the lesson is the same: **reconcile a contract document against
the code that implements it, not against its own prose.**

## Consequences

**A port now has something to satisfy.** The snapshot, the owning store, the
application layer, the transport, the node process, and the ABCI adapter are each
a separate slice, and each is version eight's shape with this contract's deltas.
The contract states required evidence for all of them rather than leaving each
port to invent its own.

**One new operational failure mode exists and it is a liveness one.** A replica
whose clock is outside the tolerance of its peers votes against proposals it
should accept. It is invisible to every value the network-health check compares —
chain ID, height, roots, peer set, validator set all agree — and it is the first
failure in this project that a correct, fully-synchronized, agreeing replica can
exhibit. The contract adds the durable timestamp to the health comparison and
names decisions `4` and `5` as the diagnosis, and the devnet evidence list
requires a test that produces it deliberately.

**The clock is now a deployment dependency.** An application that cannot read a
clock cannot vote and must fail to start rather than vote on an assumed value.
NTP configuration, clock discipline, and drift monitoring are outside this
boundary and are owed to a later operations document.

**Version one stays accepted and unedited.** It remains the record for the M1
network and every M1 artifact recorded under it remains in place and passing. The
stale table above is corrected in version two rather than by editing an accepted
document.

## Owed

**Independent review of the widened grinding surface.**
`economy-transition-v9` records that committing the timestamp to the state root
gives a proposer about `2^16.9` timestamp values to grind over on a quiet block,
and refers it to the independent review requirement 15 already owes. Nothing at
this boundary changes that figure, because the boundary neither constructs the
beacon nor chooses the stamp. The referral stands.

**Clock-discipline requirements for a Founder Machine.** This contract makes a
roughly correct clock a precondition for voting and does not say how a machine
obtains one. That belongs to an operations document and is not blocking: a devnet
on one host shares a clock.
