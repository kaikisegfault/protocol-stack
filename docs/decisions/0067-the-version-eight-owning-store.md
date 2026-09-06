# ADR 0067: The version-eight owning store, and the two column widths that move with a version

- Status: Accepted
- Date: 2026-09-06
- Follows: [ADR 0057](0057-the-version-seven-owning-store.md)

## Context

[ADR 0066](0066-the-version-eight-state-snapshot.md) made a version-eight state
expressible as canonical bytes. It did not make one durable, so
[ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md)'s
fourth step remained: **a version-eight chain could be executed and written down
and could not be stopped and resumed**, which is the first half of requirement 13
of [`first-goal.md`](../project/first-goal.md) — "adversarial four-node economic
scenarios **through restart and recovery**".

[ADR 0057](0057-the-version-seven-owning-store.md) already decided what an owning
store *is* — the connection contract reused from version one, the head stored as
one snapshot payload rather than decomposed into rows, four reopen validations in
a load-bearing order, a candidate copy committed atomically, a verifier supplied
at construction, and the write-path fault and recovery contract its 2026-09-01
update settled. **All of it carries over unchanged**, and this ADR records only
what version eight makes different. Where the two disagree about version eight,
this one governs.

## Decision

### Four figures move with the version, and the DDL is compared verbatim

The stored DDL is compared character for character on every open, so a literal in
it is not a comment about a width — it is the width, and a stale one is a store
that will not reopen or a refusal that fires in the wrong place.

- **`canonical_genesis` is 142 octets**, which is `v8::kGenesisPrefixBytes`:
  version seven's 110 plus `dispute_authority_key`. A stale value here fails the
  very first insert, so it cannot reach a file.
- **`head_snapshot` is at least 222 octets**, which is `snapshot_v8`'s own
  `kFixedSize` — the 158-octet prefix, a root, and a digest. The shortest blob the
  column admits is therefore the shortest one the decoder could parse.
- **`application_id` is `0x50534c38` and `user_version` is 8.** A version-seven
  file presented to this adapter fails on the first pragma, before its table
  names or its 110-octet genesis are ever read.
- **The tables are `ledger_meta_v8` and `blocks_v8`.** The block header column
  stays 146 octets: version eight inherits version one's header unchanged.

**The two width literals fail differently and that asymmetry is the reason the
evidence below exists.** A stale genesis width is caught by the first insert. A
stale `head_snapshot` minimum is not caught by anything — a short blob would
simply reach `decode_snapshot_v8` and come back `invalid_snapshot` instead of
never being stored. That is a weaker refusal rather than a wrong one, which is
exactly the kind of defect a test suite silently accepts.

### `apply_block` takes no uptime schedule and offers no `BlockOrder`

Version seven's store passed an optional `UptimeSchedule` through to
`execute_block`. Version eight's prologue derives the schedule from the seat
table and the window records, so there is nothing to pass: the store loses a
parameter rather than passing a null one, and **a node cannot be handed a
different answer than its peers computed**.

The three `BlockOrder` flags are not exposed either. `ledger.hpp` states that
none of them is a configuration option a chain has — each exists so a trace can
run a rejected reading against the accepted one — so a store that surfaced them
would be offering an operator a way to leave consensus.

### The head rewrite's one available optimisation is now closed

ADR 0057 accepted an `O(state)` head rewrite per commit as node-local operational
cost. Under version seven a transaction-free block at an ordinary height left the
root exactly as it found it, so a store could in principle have skipped the
write. **Under version eight it cannot**: the issue step audits every in-scope
seat at every height and the expiry step resolves those audits
`kResponseDeadlineBlocks` later, so the state differs at every height a seat is
in scope.

This changes no accepted state and ADR 0007 reserves exactly this freedom for
operational data, so the layout is kept and the figure is recorded rather than
acted on. It joins the two costs ADR 0056 and ADR 0064 already record as unpaid
because no fixture yet runs at capacity.

### A store still cannot jump to a height, and the reason hardened

ADR 0057 refused a "jump to height" operation because it would be test-only
machinery in production code answering to no chain rule. That was a design
objection. **Under version eight the operation answers to a chain rule and
contradicts it**: a skipped height is an audit that was owed and never performed.
The `carried` scenario remains the only recorded one with a contiguous run, and
it is replayable only because it activates no seat — which the evidence now
requires rather than assumes.

## Evidence

`version-eight-owning-store` replays the `carried` scenario's four contiguous
blocks — heights 1 through 4 — through a database **closed and reopened between
each pair**, and every block must reproduce its recorded `block_id`,
`resulting_state_root`, and `transaction_root` from
`test-vectors/economy-transition-v8-execution.txt`. Those figures come from a
model that knows nothing about SQLite, so a store that persisted a subtly
different state fails here rather than agreeing with itself. The block rows are
read back with a bare connection and compared against the same vectors, so the
history the store wrote is observed rather than assumed.

**The entry point now states what makes that run replayable.** No block in it
opens an assignment window, audits a seat, or expires a challenge, and the chain
writes no uptime state at all. A later scenario that activated a seat inside
heights 1 through 4 fails there with its reason named rather than at a root
comparison twenty lines later.

**`check_column_bounds` is the case version seven's suite had no reason to
write.** Its column widths were the only ones the family had ever had, so nothing
could be stale. The tamper case that writes a non-snapshot payload proves only
that *some* blob the column admits is refused by the decoder — it would still
pass if the column had kept 190. What pins the figure is the boundary itself:
**221 octets is refused by SQLite's own CHECK and 222 is not**, and a genesis at
version seven's 110 octets is refused where 142 is admitted. The two admitted
writes then leave a file the store must still refuse — `genesis_mismatch`, from
the third validation step — which keeps the case a statement about the column
rather than a way in.

Seven tamper cases edit the database behind the store's back, each a single
statement so its failure has one cause. Two moved with the version and one is
new. The head payload that is not a snapshot is **240 octets rather than 200**,
because a 200-octet blob no longer reaches the decoder at all. The rewritten
schema version is **7 rather than 6**, which is the confusion the pragma exists
to refuse. And a rewritten `application_id` of `0x50534c37` is added beside it,
because the schema comparison checks that identifier *before* it reads a single
table name and nothing previously exercised that branch.

`version-eight-store-recovery` re-establishes ADR 0057's write-path contract
against a version-eight chain rather than restating it: the four rolled-back
faults each cleared and the block re-applied to its recorded root, a commit
failed through the fault VFS's journal sync recovering to height zero and staying
conserved, a commit whose recovery is *also* denied refusing every later call,
and the process **killed** at `after_commit_before_publication` and at
`after_publication` by a re-executed child, with the parent finding the committed
block durable at its recorded root and the chain continuing to the next.

**The normalising diff is the rest of the review.** Rendering both versions with
`sed 's/v7/vX/g;s/V7/VX/g'` and `sed 's/v8/vX/g;s/V8/VX/g'` and diffing them
shows exactly the intended deltas and nothing else. For the schema header, the
internal header, and the open translation unit that diff is **empty**, which is
the strongest available statement that nothing in them was changed by accident.

**No new fuzz target, for ADR 0057's reason.** The untrusted-byte surface is the
snapshot payload and `tests/fuzz/snapshot_v8_fuzz.cpp` already drives it.
Everything this store decodes on its own is two fixed-width column reads and
verbatim text comparisons, reached only after the integrity check and the schema
comparison have accepted the file.

**One stale comment was found in version seven's header and deliberately not
fixed.** It says the genesis is taken as a struct "because version seven
publishes `encode_genesis` and no inverse"; version seven has published
`decode_genesis` since the node process needed it. Version eight's header states
the actual reason — a caller commits to a genesis the kernel accepts before a
file exists, which keeps `invalid_genesis` at creation time rather than at first
use — and version seven's text is left alone because ADR 0065's step 7 deletes
the file.

## Consequences

- Requirement 13's first two bricks are laid for version eight. A version-eight
  state can be written down and a version-eight chain can be stopped and resumed
  without changing where it is going.
- `protocol_storage` compiles two owning stores until ADR 0065's step 7 deletes
  version seven's, which is the cost that ADR already states. It gains three
  translation units and no new dependency.
- **M3.13r has a durable version-eight head to serve from.** `ApplicationV8` and
  the version-eight transport responses are next, and then the ABCI adapter's
  version-eight client — after which step 7 deletes version seven's whole stack
  and the repository compiles one economy contract again.
- The archive, the block-history replay, and concurrent readers remain owed
  exactly as ADR 0057 records them. Nothing here narrows any of the three.

## Alternatives considered

**Interpolate the two width literals into the DDL from `kGenesisPrefixBytes` and
`kFixedSize` so they cannot drift.** Rejected: the DDL is compared verbatim, and
a constructed string makes "stored and compared verbatim" stop being obvious at
the point a reader needs it to be. A `static_assert` against a separate constant
would not help either — it proves the constant, not the string. The boundary test
above proves the string.

**Give the store a "jump to height" operation so the other recorded scenarios
could be replayed.** Rejected twice over: ADR 0057's objection stands, and under
version eight the operation would skip audits the chain owed.

**Reuse `SQLiteLedgerV7` with a version parameter.** Rejected for ADR 0057's
reason, which the migration sharpens: the two differ in what a state *is*, and
one of them is deleted three slices from now.
