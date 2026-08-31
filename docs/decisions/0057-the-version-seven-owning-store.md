# ADR 0057: The version-seven owning store, and why the head is a snapshot

- Status: Accepted
- Date: 2026-08-30

## Context

[ADR 0056](0056-the-version-seven-state-snapshot.md) made a version-seven state
expressible as canonical bytes. It did not make one durable: nothing wrote a
payload to a file, reopened it after a process ended, and continued from it, so
"no state survives a restart" remained true of the repository and requirement 13
of [`first-goal.md`](../project/first-goal.md) — "adversarial four-node economic
scenarios **through restart and recovery**" — still could not begin.

[ADR 0007](0007-sqlite-ledger-persistence.md) already fixes the persistence
boundary: SQLite behind an owning C++20 adapter, one local writer, explicit
durability, process locking, corruption checks, fault-injection seams, and an
engine-independent removal path. It also fixes how a storage artifact is
classified: "Storage rows, files, schemas, and snapshot formats are operational
compatibility data. They never define transaction, receipt, state-root, or block
meaning."

This ADR records the version-seven store built on that boundary.

## Decision

### The connection contract is version one's, reused unchanged

`src/storage/sqlite_connection.cpp` supplies path reservation and normalisation,
the exclusive-create primitive, the lifetime lock, journal-mode handling, path
stability verification, the exclusive-transaction helpers, and the
fault-injection seams. **None of it is version-specific.** ADR 0007 settles all
of it against the filesystem and SQLite rather than against a ledger, so a second
copy would be a second place for a locking or durability rule to be wrong.

Version seven throws its own `FailureV7`, and the version-one codes it can
receive from that shared layer are translated by an explicit mapping rather than
a cast. The two enumerations agree on every number they share; a blind cast would
turn the one code they do not share — `invalid_archive`, which only the archive
import raises — into a value outside the version-seven enumeration.

### The head is one snapshot payload, not a row per entry

Version one decomposes its state into an `accounts` table. Version seven stores
the head as the exact bytes `encode_snapshot_v7` produces.

**The argument is the snapshot's own.** It is already the canonical projection of
everything a state root commits to, already checked against recorded roots,
three gates, and a fuzz target. A second, row-shaped projection of the same state
would be a second opinion about what a state *is* — the mistake ADR 0056 exists
to avoid — and every future entry kind would have to be added on both sides, with
nothing but discipline keeping them in step.

What the schema keeps in its own columns is only what a reopen must agree on
*before* it trusts the payload: the canonical genesis, the chain identity, the
height, and the root.

**The cost is real and is accepted deliberately.** A commit rewrites the whole
head, which is `O(state)` per block; at the 100,000-seat capacity the cycle
assignment records dominate and that is a large write. It is node-local, changes
no accepted state, and is replaceable the day a fixture needs it to be — which is
exactly the freedom ADR 0007 reserves for operational data. A row-level store is
the alternative and it is deferred until something measures the need.

### Reopening validates in four steps, and the snapshot does most of it

1. `PRAGMA integrity_check` and `foreign_key_check`;
2. the pinned `application_id` and `user_version`, then the stored DDL compared
   verbatim, so a table altered underneath the process is refused rather than
   read;
3. the stored canonical genesis compared against the one the caller presents;
4. `decode_snapshot_v7`, whose three gates and conservation invariants establish
   that the payload is a state some sequence of blocks could have produced.

The height and root columns are then required to agree with what the payload
restored to. That is a different claim from the snapshot's own gates: it catches
a row edited without the payload, where the gates alone would happily restore a
consistent state the file does not claim to hold.

An open either hands back a state some sequence of blocks could have produced, or
it hands back an error.

### A block is executed against a candidate and committed atomically

`apply_block` copies the head, runs `execute_block` against the copy, and writes
the new head and the block row inside one exclusive transaction. A block the
kernel rejects is `BlockRejectedV7` rather than a storage error: no write was
attempted and both the durable and live heads are untouched.

A height that is not `current + 1` is rejected the same way. The kernel advances a
ledger from `h` to `h + 1` and takes no target height, so any other height names a
block this chain cannot be at; refusing it in the store keeps the contract
explicit rather than making a caller infer the next height.

The payload is encoded before the write path is entered, so a state that cannot
be encoded is a refusal that leaves both heads where they were rather than a
poisoning: nothing was attempted, and the distinction is what keeps the poisoned
state meaning "the durable head is unknown" rather than "something went wrong".

If the write itself fails the store is **poisoned**: the durable head is whatever
the transaction left and this process no longer knows which, so every later call
returns `storage_failure`. **Recovery was owed at first publication and is
recorded below as delivered on 2026-09-01.**

### The verifier is supplied at construction

The kernel takes a `SignatureVerifier` so that "the transition layer never
chooses a verification rule" ([ADR 0045](0045-the-version-six-execution-model-and-three-derived-rules.md)).
The store follows it for the same reason, defaulting to `ed25519_verifier()`.
Without it the recorded scenarios — whose signatures are a stand-in table, not
Ed25519 — could not be replayed through a store at all, and the store's evidence
would have to be a fixture of its own invention.

## Evidence

**The `carried` scenario's four contiguous blocks are replayed through a database
that is closed and reopened between each pair**, and every block must reproduce
its **recorded** `block_id` and `resulting_state_root` from
`test-vectors/economy-transition-v7-execution.txt`.

That is the question ADR 0056's tests could not ask. They restore a *final*
ledger and execute one further block; they establish nothing about a chain
interrupted in the middle of its history. Here no block after the first is
executed against a head that stayed in memory.

**Only one recorded scenario could be used, and the reason is worth recording.**
`carried` is the only one with a contiguous run: the other four skip millions of
heights between segments, because the trace's `advance_to` sets the height rather
than executing the gap. A store that executes every height cannot replay a
scenario that skips 5,846,395 of them, and giving the store a "jump to height"
operation to make it possible would be test-only machinery in production code
answering to no chain rule.

The block rows are read back with a bare SQLite connection and compared against
the same vectors, so the history the store writes is observed rather than assumed
— without it a commit that wrote only the head would pass every other check. The
transaction root is compared there and in the commit the store returns: a probe
that stored the block identifier in that column is refused by the row
comparison, and a probe that zeroed the committed value is refused by the commit
comparison.

**Writing that pair of checks is what found the store's one duplicated
derivation.** The transaction root is the tree over the admitted identifiers, and
the block header already commits to it, but `BlockOutcome` did not carry it — so
the store rebuilt the identifier list from `executed` and ran the tree again.
That is a second opinion about the block it is recording, guaranteed to agree
only because the kernel happens to push `executed` and its identifier list in
lockstep. `execute_block` now carries the root it computed out of the block and
the store records that. It changes no encoding, no state, and no accepted vector:
the header committed to this exact value before and after, which is why every
recorded `block_id` still matches.

**Two of the ten mutation probes found tests that did not exist rather than tests
that were wrong.** Nothing exercised a block the *kernel* rejects whole — every
other refusal returns before `execute_block` is reached — so a store that
committed a rejected block passed the whole suite; offering more raw inputs than
`kMaxRawInputs` is the cheapest such block and closes it. And nothing corrupted
the file in a way `PRAGMA integrity_check` could catch, because every tamper case
above leaves a database SQLite considers valid; overwriting a b-tree page header
does.

**That second gap produced the more useful finding.** With the integrity check
removed, a database whose pages were overwritten reports `genesis_mismatch` —
which tells an operator they opened the wrong chain when in fact their disk is
failing. The check does not merely add a refusal; it is what keeps every later
comparison from lying about why it failed. That is why it runs first.

Six tamper cases edit the database behind the store's back, each a single
statement so its failure has one cause: a renamed table, an added column, and a
rewritten schema version reach the schema comparison; a rewritten root and a
rewritten height reach the columns-agree check; and a head payload that is not a
snapshot reaches the decoder.

**The untrusted-byte surface is the snapshot payload, and it already has a fuzz
target.** `tests/fuzz/snapshot_v7_fuzz.cpp` drives `decode_snapshot_v7`, which is
the only place in this path where an attacker-supplied length or index decides
how far a read goes. Everything the store decodes on its own is two fixed-width
column reads — an eight-octet height and a thirty-two-octet root, each length
checked before it is used — and verbatim text comparisons of the stored DDL, all
reached only after `PRAGMA integrity_check` and the schema comparison have
accepted the file. A second fuzz target over those would be exercising
`std::span::size()`, so this ADR records the reason rather than adding one.

## Consequences

- Requirement 13's first two bricks are laid. A version-seven state can be
  written down, and a chain can be stopped and resumed without changing where it
  is going.
- `protocol_storage` gains two translation units and no new dependency.
- The next slices are the application layer and the CometBFT adapter carrying
  version-seven transactions, which is what turns a store into a node.

## Update, 2026-09-01: the write path's faults and its recovery

The first two items of the owed list below are now delivered, and the contract
they settle is narrower than the original text implied.

**Everything before the commit rolls back and is an ordinary refusal.** A fault
at `before_transaction`, `after_transaction_begin`, `after_persistence`, or
`before_commit` abandons the transaction, leaves the durable head the one it
already was, and **leaves the store usable** — the same store accepts the same
block once the fault is gone. The original text poisoned the store on any write
failure, which was safe and wrong: a refusal that wrote nothing is not a reason
to stop answering.

**Only the commit can leave a head this process cannot name**, and there the
store poisons itself and then **reads the file again**. Recovery closes the
connection, reopens it, runs the same four validation steps an ordinary open
runs, and adopts whatever head the file actually holds — which is either the
block's or its predecessor's, because SQLite's transaction is what decides and
nothing between is reachable. On success the poison is cleared and the store
continues.

**Recovery is allowed to fail, and then the store stays poisoned.** It is
`noexcept` and answers `false`; a store that could not read its own file back
refuses to read a head, refuses to hand out a payload, and refuses every later
block. That is a worse state and an honest one.

The evidence is `version-seven-store-recovery`. The four rolled-back faults are
each driven and then cleared, and the block that follows must reproduce its
**recorded** root. A commit made to fail through the fault VFS's journal sync
must recover to height zero, stay conserved, and then execute the same block to
its recorded root. A commit whose recovery is *also* denied must refuse
everything afterwards. And the process is **killed** at
`after_commit_before_publication` and at `after_publication` by a re-executed
child: in both cases the parent must find the committed block durable at its
recorded root, and must be able to continue the chain to the next block's
recorded root.

That last pair is the property requirement 13 names when it says "through
restart **and recovery**": a fault anywhere in the write path leaves the durable
head at the pre-block root or the post-block root, and never at anything between.

## Owed, and recorded rather than implied

- ~~**Fault-injection coverage of the version-seven write path.**~~ Delivered
  2026-09-01; see the update above.
- ~~**Recovery after a poisoned write.**~~ Delivered 2026-09-01, with a narrower
  contract than this section first assumed; see the update above.
- **The archive and block-history replay.** Version one validates its
  materialized head by replaying every block from genesis. Version seven's head
  is validated by the snapshot's gates and the conservation invariants instead,
  which is an independent check of a different kind, and a replay per open is
  `O(history)`. The archive is the artifact that needs full history.
- **Concurrent readers.** One local writer is ADR 0007's contract and this store
  keeps it; nothing here adds a reader path.

## Alternatives considered

**Decompose the state into rows, as version one does.** Rejected above: a second
projection of the same state, with every future entry kind owed to both.

**Store the snapshot as a file beside the database.** Rejected: the head and the
block that produced it must commit or fail together, and two files cannot be
made atomic without reimplementing what SQLite already provides.

**Reuse `SQLiteLedger` with a version parameter.** Rejected: the two differ in
what a state *is*, not in a setting, and a shared class would carry both
schemas, both validation paths, and two ledger types behind one interface.
