# ADR 0061: The version-seven ABCI adapter, and why replay needs a guard

- Status: Accepted
- Date: 2026-09-01

## Context

[ADR 0060](0060-the-version-seven-node-process.md) made a version-seven
application a **process**: a store, an application, and a private Unix socket
that starts, serves, and shuts down. Nothing on the other end of that socket
spoke version seven. `adapter/cometbft` — the frame client, the ABCI
application over it, and the four binaries — was written for version one, so no
consensus engine could drive a version-seven node and requirement 13 of
[`first-goal.md`](../project/first-goal.md), the adversarial four-node economic
scenarios, still had nothing to run.

[ADR 0059](0059-the-version-seven-transport.md) settled what differs on the
wire. This ADR records the adapter that reads it, and the one question the
adapter had to answer that is not encoding: **the replay handshake ADR 0058
recorded as owed to this slice.**

## Decision

### The Go client is version one's client and one different answer

`ClientV7` embeds `Client` and declares `FinalizeBlock`. Nothing else.

The connection, the request-identifier discipline, the terminal latch, the
twenty-octet frame header, the seven kinds, and all five request encoders carry
no ledger-version meaning — a height, a transaction list, a byte budget, an app
state, a raw transaction. A second copy of them would be a second place for a
framing rule to be wrong, and the two would have to be kept in step by
discipline alone. It is the same decision ADR 0059 made on the C++ side, in the
same shape, and it is what makes the two sides legible together.

Three fields are genuinely version-specific and all three are in the finalized
block: the **block identifier** after the state root, a receipt of fifty-six
octets under a version field of 7 with its result byte at offset 39, and a
result range of thirty-three rather than eight.

### The decoder validates rather than trusts

A declared code and its receipt's own result byte must be the same fact; an
admission failure must carry no receipt; a receipt must be version seven's
length under version seven's prefix; a result byte at or above the code count
means the two sides disagree about the contract. The C++ encoder already checks
each of these on the way out. Checking them again here is not redundancy: it is
the only place a **corrupted or mismatched peer** on the socket is caught, and
the adapter has no ledger, no kernel, and no vectors with which to catch it any
other way.

**The two shapes fail closed against each other.** Version seven's decoder
refuses version one's finalized block and version one's refuses version
seven's, so a client dialled at the wrong version cannot silently misread a
block — which is what makes `-protocol-version` a safe flag rather than a
trap.

### One `Application`, parameterized, rather than two

Six of the seven ABCI conversions name no ledger version: the signed height
range, the chain-identity decoding, the app-state bound, the proposal prefix,
the block bounds, the committed head. Duplicating them for version seven would
be about a hundred and fifty lines whose only difference is which copy a later
fix reaches.

So `New` and `NewV7` differ by two things: the codespace that names the result
codes an executed transaction can carry, and whether a finalized block arrives
with an identifier. The bridge's own `FinalizedBlock` carries that identifier
as a **pointer**, because absent must be unmistakable — a zero hash would be
indexed as though it named something.

### The block identifier becomes a block event

ABCI has no field for a second block identifier. CometBFT computes its own
block hash over the transactions and the previous application hash; version
seven's identifier commits to the protocol's own header, including the
transaction root and both state roots, which is a different statement about the
same block.

It is emitted as a `protocol_block` event with an indexed `id` attribute. The
alternative was to decode it and discard it, and the argument against that is
not aesthetic: **a value that crosses a process boundary and is then discarded
is a value the next simplification deletes**, and the C++ encoder's own check
would then be the only thing keeping it on the wire.

**It is observable rather than consensus-visible.** A block event is not hashed
into anything CometBFT agrees on; only a transaction result's code and data
reach `LastResultsHash`.

### The replay handshake is a guard, and the engine never trips it

This is the question ADR 0058 left open, and the answer turned out to be a fact
about the pinned engine rather than a design.

`ApplicationV7` refuses, terminally, a `finalize_block` at any height that is
not its current plus one — **including one it has already committed**. The
worry was the crash window between the application's commit and CometBFT saving
its own state, which leaves the application one block ahead of the engine's
state.

CometBFT v0.39.4 handles that window itself. In `consensus/replay.go`, with the
block store one ahead of the state and the application at the block store's
height, it loads its **own saved** `FinalizeBlock` response and replays that
height against a mock application built from it — the source says, in as many
words, that it does not want to call `Commit` twice for the same block on the
real app. Every other branch either replays from `appBlockHeight + 1`, which is
exactly `current + 1` at each step because each replayed block is committed
before the next is sent, or refuses at the handshake without sending a request
at all when the application is ahead of the block store.

So the adapter reconciles nothing, and **inventing a reconciliation would have
been worse than useless**: to answer a repeat honestly it would have to
reproduce the per-transaction receipts of a block whose results the application
no longer holds and the store never recorded, and any answer it synthesised
instead would be exactly the fabricated agreement this layer exists to prevent.

What it does instead is refuse to *forward* such a request. The height comes
from the application's own answers to `Info` and `Commit` and is never counted
here, so it can never exceed the height the application would accept and can
never refuse a legitimate `current + 1`. The cost is one comparison per block.
The benefit is that if any engine ever does ask — a version change, a
misconfiguration, an operator pointing two engines at one node — the failure is
a legible error the engine stops on rather than a node bricked on a
contradiction it did not commit.

### The genesis application state is version-specific

`ApplicationV7` requires `"protocol-stack-v7"` at `init_chain`, and **that is
what stops a node started against a version-one genesis and a version-seven
engine**: it refuses at `init_chain` rather than at the first block.
`protocol-cometbft-init` therefore takes `-protocol-version`, and the parser
compares as the wider type so that 257 is not admitted as version one.

The devnet stays on version one explicitly rather than by omission. A
version-seven local network needs its genesis and the `-protocol-version` its
supervisor passes each bridge to be one choice, and that belongs with the
four-node slice.

## Evidence

**All thirty-six results a version-seven block can report** — three admission
failures and thirty-three execution results — are decoded and each field
checked against the receipt that produced it. Eight refusals are exercised: a
wrong result count, a truncated identifier, trailing octets, a version-one
receipt version under a version-seven code, a result byte at the code count, a
declared code disagreeing with its receipt, a version-one receipt length, and
an admission failure carrying data.

**The version-seven client sends version one's request byte for byte**, read
off a real socket pair and compared against the shared encoder's output, and it
answers `Info` through the embedded client with no second copy of anything. A
protocol failure in its response is terminal for the whole connection.

**The bridge is driven through `Info`, `CheckTx`, `Query`, and a finalized
block carrying all three result shapes.** The identity event's type, key, index
flag, and value are each checked, and version one must emit no event at all.

**The guard is exercised from both sides of a commit.** A height below the one
`Info` reported and the reported height itself are refused *without reaching the
local application*, which the fake asserts by counting its own calls; the next
height succeeds; the same height repeated after its own commit is refused; and
the height after that succeeds. A separate case proves the guard counts nothing
itself: an adapter that never asked `Info` still forwards the first block of a
chain, and height zero — which is not a block height — is refused by the same
comparison.

**A home initialized for version seven carries the version-seven application
state**, and re-initializing that home for version one is refused rather than
adopted, because the initializer exact-validates an existing genesis.

## Owed, and recorded rather than implied

- **The end-to-end run.** Nothing here has spoken to a real CometBFT engine.
  The single-node integration test drives version one; driving version seven
  needs the recorded blocks' **raw inputs**, which no accepted vector file
  carries today — the version-seven vectors record each block's roots,
  identifier, and receipts but not the transactions that produced them. That is
  the next slice, and only four of the five recorded blocks are reachable
  through it: `carried.block4` is at height 1,152,000.
- **The four-node devnet.** Its genesis and its bridges must choose one version
  together, and it stays on version one until they do.
- **The uptime schedule is still `nullptr`.** A chain driven through this
  adapter executes correctly and pays nobody, which ADR 0058 already records.
  Four nodes agreeing on blocks that pay nobody would satisfy the word
  "four-node" and not the word "economic".

## Alternatives considered

**A second frame codec and a second connection for version seven.** Rejected
for the reason ADR 0059 rejects a second wire: the framing rules carry no
ledger-version meaning, so the copies would differ in nothing but their names
while doubling the places one can be wrong.

**Two `Application` types in the bridge.** Rejected: six of seven conversions
are identical, and the copies would drift the first time one was fixed.

**Making the application answer a repeated finalize instead of latching.**
Rejected. The response it would have to reproduce contains per-transaction
receipts that the stage no longer holds after `commit` and that the store never
records, so answering would mean either re-executing a block against a head
that has moved past it — a different question — or synthesising a reply. The
engine does not ask, so nothing is bought for the risk.

**A single `FinalizedBlock` with a zero identifier for version one.** Rejected:
a zero hash is a value, and it would have been emitted, indexed, and eventually
compared.
