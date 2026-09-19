# ADR 0081: The version-nine owning store keeps the head's second scalar in a column of its own

- Status: Accepted
- Date: 2026-09-19
- Bounds: [ADR 0007](0007-sqlite-ledger-persistence.md),
  [ADR 0057](0057-the-version-seven-owning-store.md),
  [ADR 0067](0067-the-version-eight-owning-store.md)
- Follows: [ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md),
  [ADR 0080](0080-the-version-nine-snapshot.md),
  [ADR 0079](0079-the-version-nine-application-contract.md)
- Relates to: `include/protocol/storage/sqlite_ledger_v9.hpp`,
  `src/storage/sqlite_ledger_v9*.cpp`, `src/storage/sqlite_schema_v9.cpp`

## Context

[ADR 0080](0080-the-version-nine-snapshot.md) made a version-nine state
expressible as canonical bytes and named this as what it owed: nothing yet wrote
one of those payloads to a file.
[ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md)'s
enumeration puts the owning store fourth, directly after the snapshot, and
everything above it — `ApplicationV9`, the transport, the node process, the ABCI
adapter — waits on a durable head.

**Most of the store needed no decision.** The connection, locking, journal, and
path-stability contract is version one's; the head-as-one-payload layout, the
candidate-copy write path, the poisoning rule, and the storage-code vocabulary
are [ADR 0057](0057-the-version-seven-owning-store.md)'s and
[ADR 0067](0067-the-version-eight-owning-store.md)'s, and none of it is
version-specific. `sqlite_ledger_v9_open.cpp` is a **provably empty normalising
diff** against version eight's. What follows is the set this slice had to settle,
and the finding that outranks it.

## Decision

### 1. The durable head keeps a timestamp column, although the payload carries one

[`consensus-application-v2`](../specifications/consensus-application-v2.md)
defines the durable head as **two scalars and a root**. The head snapshot already
carries the stamp and `snapshot_v9` decodes it, so the column is not needed to
*restore* anything — which is exactly why the handoff left the choice to this
slice rather than deciding it in advance.

It is kept, and not for the cheap read. A file whose columns named the height and
the root would be **stating half of a head it holds whole**, and the half it
omitted would be the one version nine added. The column costs eight octets per
head rewrite and one comparison per reopen, and it buys the reopen a third
comparison that the root's does not imply: the root refuses a *payload* whose
stamp was changed alone, and cannot refuse a **column** that disagrees with an
unchanged payload. A column is what a later reader — or a later version of this
store — would be tempted to trust without decoding anything.

**The restore still reads the payload and never the column.** The column is a
claim the file makes about itself, checked against the payload and then
discarded; `state_mismatch` is what a disagreement produces.

### 2. The stamp is written in the same statement as the height

`persist_block_v9` advances `current_height`, `current_timestamp_millis`,
`current_state_root`, and `head_snapshot` in one `UPDATE`. The defect this
version could hide — a head that advanced its height and left its stamp behind —
would need two statements to exist, so it is refused by the shape of the write
rather than by a test that has to think of it.

### 3. `apply_block` takes the agreed timestamp, and C5 is not reachable from it

The store hands the caller's stamp to `execute_block` unchanged, which applies C1
and C2 against the durable head. **It must not apply C5.** A store executes
blocks the network already decided — a commit, a replay, a recovery — and one
that re-applied the proposal tolerance would refuse the chain's own past one
tolerance-width after producing it. ADR 0079 puts the tolerance at
`ProcessProposal` and nowhere else; this signature has no clock to give it, which
is the enforcement rather than the convention.

The same argument refuses an uptime schedule parameter and a `BlockOrder`
parameter. The prologue derives the schedule from the seat table and the window
records, so a node cannot be handed a different answer than its peers computed;
and the `BlockOrder` flags are demonstration flags rather than a configuration a
chain has, so a store that exposed them would be offering an operator a way to
leave consensus.

### 4. Three DDL literals move with the version, and each is pinned at its boundary

`canonical_genesis` is `v9::kGenesisPrefixBytes` — **150**, not version eight's
142, because `genesis_timestamp` is a tenth genesis field. `head_snapshot` is
`snapshot_v9::kFixedSize` — **230**, not 222, because the prefix grew by the
stamp. `header` is `v9::kBlockHeaderBytes` — **154**, not 146, and it is the
first time in nine versions that this one has moved at all.

Each is checked at the octet: one below is refused by SQLite's own CHECK and
exactly the width is admitted. A tamper case proves only that *some* blob the
column admits is refused by the decoder, and would still pass against a stale
literal. **The header literal is the one a copied DDL would silently keep**, and
its failure shape is the worst of the three: a store that creates a genesis and
then refuses every block.

### 5. There is still no operation that skips a height

[ADR 0057](0057-the-version-seven-owning-store.md) refused a "jump to height"
operation as test-only machinery in production code answering to no chain rule.
Under version nine it answers to a chain rule and **contradicts** it: every height
audits every in-scope seat and every height's stamp is a value C2 compared, so a
skipped height is an audit that was owed and never performed and a comparison that
never happened. The objection was a design preference under version seven and is a
correctness argument now.

## The finding

**The column could not be called `current_timestamp`, and the reason is that
SQLite would have read the machine's clock instead.**

`CURRENT_TIMESTAMP` is an SQL keyword. SQLite resolves a bare `current_timestamp`
in an expression to its own wall-clock reading rather than to a column of that
name, so the column's `typeof` CHECK evaluated the keyword — `typeof` returns
`'text'` and `length` returns 19 — and refused **every** insert, on the first
genesis this store ever wrote. A `SELECT current_timestamp` would have returned
the time of day.

The CHECK is what caught it. A schema without one would have stored the column and
read back the clock, in the single component of this repository whose whole job is
to hold the chain's stamp rather than the machine's — and the shadowing is silent
in every direction: the `CREATE TABLE` succeeds, the name is legal, and only an
expression over it misbehaves.

The column is `current_timestamp_millis`, which also states its unit. **The block
row's column is `timestamp` and needs no suffix**, because no keyword shadows it;
renaming both to match would have hidden the reason rather than recorded it.

## Consequences

**A version-nine chain now survives the process that built it, and the next slice
is `ApplicationV9` and the transport responses**, which
[`consensus-application-v2`](../specifications/consensus-application-v2.md)
already specifies and whose required-evidence section is their acceptance
criteria. After them, `protocol-application-v9` and the Go client, and then the
deletion of `src/v8/`.

**Version eight's store is untouched and still green.** Both stores are compiled
and both suites run, which is ADR 0065's staged coexistence and is owed a deletion
at the end of the sequence rather than at its start.

**The suite replays a run recorded for it.** Every other version-nine chain jumps
from height 2 to the activation height with `advance_to`, which no store,
application, or transport can follow — each commits one height at a time. The
contiguous `restart` run was recorded by the Python model and reproduced by the
C++ kernel before anything replayed it, so the figures this store is compared
against come from a model that knows nothing about SQLite.

**The restart evidence aims at the stamp rather than only at the root.** Between
the run's two equal-stamped heights the reopened store is offered height 3 one
millisecond below block 2's stamp, which it must refuse, and then at exactly that
stamp, which it must admit. A store that restored a smaller stamp admits both; one
that restored a larger stamp admits neither. A root comparison alone proves
agreement without ever showing which stamp came back.

## Owed

**Nothing about the head, and one thing about the history.** `blocks_v9` stores a
header per height and nothing reads it back except the tests; the replay path that
would consume it belongs to the node process, not to the store, and version one's
`sqlite_history_replay_v1.cpp` is still the only implementation of that shape.
