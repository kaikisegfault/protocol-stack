# ADR 0007: SQLite-backed M1 ledger persistence

- Status: Accepted
- Date: 2026-07-23

## Context

M1 needs local ledger state to survive clean shutdown, process interruption,
I/O failure, and recoverable power loss without changing the deterministic
kernel. The persistence boundary must atomically retain the materialized state,
canonical block outputs, and admitted transaction journal; reconstruct a
validated `Ledger`; support portable snapshots; and remain replaceable.

The node is a single local writer. It does not need a client/server database,
high write concurrency, distributed storage, or a consensus-visible storage
layout. It does need a mature atomic-commit implementation, explicit durability
settings, process locking, corruption checks, fault-injection seams, a small
dependency surface, and an engine-independent removal path.

SQLite, LMDB, RocksDB, and a custom journal were evaluated from their current
upstream documentation and releases. Storage rows, files, schemas, and snapshot
formats are operational compatibility data. They never define transaction,
receipt, state-root, or block meaning.

## Decision

### Dependency and build

Use SQLite 3.53.3 through its official autoconf amalgamation:

- archive:
  `https://sqlite.org/2026/sqlite-autoconf-3530300.tar.gz`;
- archive size: 3,282,443 bytes;
- SHA-256:
  `c917d7db16648ec95f714974ace5e5dcf46b7dc70e26600a0a102a3141125db0`;
- upstream SHA3-256:
  `98f2b3f3c11be6a03ea32346937b032c2472ebbd7a716bed36ca2f5693e7ce8b`;
- SQLite source ID:
  `2026-06-26 20:14:12 d4c0e51e4aeb96955b99185ab9cde75c339e2c29c3f3f12428d364a10d782c62`;
- upstream SHA3-256 for the extracted `sqlite3.c`:
  `28e484abdaa43630e34040ef6ed92be973a1ad54107803d8af5145b889c23ed7`.

The deliverable SQLite library and documentation are public domain. Build-only
files in the autoconf archive retain their own permissive notices, which must
remain in the extracted dependency and dependency inventory.

Build a static library with the default serialized
`SQLITE_THREADSAFE=1` mode. The pinned configuration is:

```text
--disable-shared
--enable-static
--disable-load-extension
--disable-math
--disable-json
--disable-carray
--disable-readline
```

Compile the library with `SQLITE_DQS=0`, `SQLITE_TRUSTED_SCHEMA=0`, and
`SQLITE_ENABLE_API_ARMOR`. API armor is a secondary application-bug diagnostic,
not a safety guarantee. The exact non-default configuration must be built and
tested in every supported compiler preset. Do not enable options that omit
locking, synchronization, integrity checking, or SQLite's testable behavior.

SQLite remains behind an owning C++20 adapter. Kernel code does not include
SQLite headers, issue SQL, or depend on storage result codes.

### Filesystem and connection contract

Support one ordinary local-filesystem database reached through one stable
pathname. Network filesystems, no-lock VFS modes, URI filenames, unmanaged
hard-link aliases, and moving, renaming, copying, or unlinking the database or
its journal while open are unsupported. A raw SQLite file is not a portable
snapshot.

Creation and opening are separate operations. Creation first reserves the
pathname with the platform's exclusive-create primitive and fails if its target
already exists; SQLite's `SQLITE_OPEN_EXCLUSIVE` flag does not supply this
guarantee. A crash after reservation but before schema commit leaves an empty
file that ordinary opening rejects. Opening fails if its target is missing,
empty, not the expected application, or not the expected chain. Tests may use
temporary local files; production does not use `:memory:`.

Open with a private cache, extended result codes, and no-follow behavior where
the platform supports it. Do not enable URI interpretation. On every
connection, read back every setting, and reject any mismatch:

1. enable defensive mode and disable trusted schema, triggers, and views;
2. set and read back `foreign_keys=ON`, `cell_size_check=ON`, and
   `mmap_size=0`;
3. set and read back `synchronous=EXTRA`, whose numeric value is `3`;
4. set and read back `locking_mode=EXCLUSIVE`;
5. set and read back `journal_size_limit=0` and a zero busy timeout;
6. execute `BEGIN EXCLUSIVE; COMMIT` successfully before publishing the
   adapter, then retain that connection for the adapter lifetime.

Setting exclusive locking mode does not itself acquire an exclusive lock. The
explicit transaction makes a second process fail fast and causes the owning
connection to retain its lock until close.

Creation sets and reads back `journal_mode=DELETE` after reserving the new
path. Opening an existing database acquires exclusive ownership first, then
queries and requires `journal_mode=DELETE`; it never silently transitions an
unexpected WAL or other journal mode. This prevents a mode-changing PRAGMA
from checkpointing or modifying an unvalidated database before ownership.

With exclusive locking, SQLite normally retains the rollback-journal file and
commits by invalidating its header even though `journal_mode` reports `DELETE`.
`synchronous=EXTRA` therefore behaves like `FULL` on ordinary lifetime commits;
its additional directory synchronization applies when a DELETE-mode journal is
actually unlinked, normally during final lock-exit cleanup. The adapter must not
assume or test for one internal journal implementation. The durability contract
is SQLite's documented rollback-journal behavior on a truthful local filesystem
whose locking, write, synchronization, and storage-cache operations work as
reported. It is not an unconditional guarantee against dishonest hardware,
filesystem damage, or arbitrary external writes.

### Ownership and atomic publication

The adapter owns the live ledger as `std::unique_ptr<Ledger>`. For an expected
next height it:

1. copy-constructs an independent candidate ledger;
2. applies the ordered raw block to that candidate;
3. derives the admitted raw transactions by walking the kernel's raw-aligned
   admission results;
4. starts one SQLite write transaction;
5. writes the materialized state delta, block row, admitted journal rows,
   exact kernel outputs, and new head metadata;
6. commits durably;
7. publishes with `live.swap(candidate)`.

The pointer swap is non-throwing. No allocation, logging, callback, or other
fallible action is allowed between a successful database commit and the swap.
The adapter returns success only after both have completed.

The adapter serializes reads, block application, snapshot creation, export, and
recovery. It never exposes a borrowed `Ledger`, `State`, account reference, or
SQLite handle outside that ownership guard. Public reads return owned values or
run a caller-supplied read operation entirely while the guard is held, so
publication cannot leave a dangling view.

Kernel block rejection occurs before persistence and leaves both states
unchanged. Admission failures are never journaled. Empty and entirely
unadmitted blocks still advance height and create a block row with the empty
transaction root. A local kernel exception is an operational failure: the
adapter leaves both states unchanged and fails closed rather than translating
it into a protocol result.

The kernel provides a narrow operational restoration factory that validates an
owned `State` before constructing a `Ledger`. It first checks the state's
intrinsic invariants, then compares every immutable parameter with a trusted
`Parameters` value derived by loading canonical genesis, and finally compares
the expected state root. The adapter passes that trusted genesis value into the
factory. On open, the expected canonical genesis comes from caller
configuration trusted independently of the database and must exactly match the
persisted copy; snapshot bytes, the persisted copy alone, and database metadata
are never the parameter authority. A state root alone is insufficient because
the version-one state-root preimage does not contain `fixed_fee`.

### Storage schema version one

Set SQLite `application_id` to `0x50534c44` (ASCII `PSLD`) and `user_version`
to `1`. Version one has these logical tables:

| Table | Required contents and key |
| --- | --- |
| `ledger_meta` | one row containing canonical genesis, chain ID, supply limit, total supply, fixed fee, current height, fee pool, and current state root |
| `accounts` | account ID primary key, balance, and nonce |
| `blocks` | height primary key, previous state root, transaction root, resulting state root, admitted count, exact 146-byte header, and block ID |
| `admitted_transactions` | height and admitted ordinal primary key, exact 200-byte transaction, transaction ID, and exact 47-byte receipt |
| `snapshots` | height primary key, versioned snapshot payload, expected state root, and payload digest |

Use `STRICT` and `WITHOUT ROWID` tables where applicable, foreign keys from
journal rows to blocks, and exact type-and-length checks for every fixed field.
The only SQLite integers are bounded operational fields such as the singleton
metadata key and SQLite's schema identifiers.

Every protocol `u64` is an exact eight-byte big-endian BLOB. SQLite INTEGER is
signed and cannot represent the protocol's full unsigned range. Heights and
balances are BLOB8; admitted counts and ordinals are BLOB4; identifiers and
roots are BLOB32. Duplicate admitted transaction IDs are valid, so only
`(height, ordinal)` is unique.

All reconstruction queries contain an explicit `ORDER BY`. Fixed-width
big-endian keys make byte order agree with unsigned numeric order, but every
decoded height and ordinal is still checked for exact contiguity. Rowid,
planner order, filesystem order, and unspecified iteration order never enter
kernel input.

The canonical genesis, admitted transaction, receipt, header, and identifier
bytes are stored directly. Typed database columns are checked projections; if
a projection disagrees with the canonical bytes or kernel output, opening
fails.

### Snapshot and portable export contract

An internal version-one snapshot is an engine-independent byte sequence:

```text
"PSSN" ||
u16(1) ||
chain_id[32] ||
height:u64 ||
supply_limit:u64 ||
total_supply:u64 ||
fixed_fee:u64 ||
fee_pool:u64 ||
account_count:u64 ||
sorted account_count * (account_id[32] || balance:u64 || nonce:u64) ||
state_root[32] ||
snapshot_digest[32]
```

All integers use big-endian encoding. The digest is:

```text
SHA-256(
  D("protocol-stack:storage:snapshot-v1") ||
  every preceding snapshot byte
)
```

Accounts are strictly increasing by unsigned account ID. The decoder checks
the count and exact total length with overflow-safe arithmetic before
allocation, rejects trailing bytes, validates supply conservation and immutable
parameters, recomputes the state root, and checks the digest. `account_count`
must fit `size_t` and the remaining input must contain exactly
`account_count * 48 + 64` bytes. This operational format is not a consensus
PSCE object and does not inherit the one-megabyte canonical-object limit.

A portable version-one archive has this exact framing:

```text
"PSAR" ||
u16(1) ||
genesis_length:u32 ||
canonical_genesis[genesis_length] ||
block_count:u64 ||
block_count * (
  header[146] ||
  block_id[32] ||
  admitted_count:u32 ||
  admitted_count * (
    transaction[200] ||
    transaction_id[32] ||
    receipt[47]
  )
) ||
snapshot_length:u64 ||
head_snapshot[snapshot_length] ||
archive_digest[32]
```

The block count equals the head snapshot height. Headers encode contiguous
heights beginning at one, and admitted counts equal their header counts. The
final digest is SHA-256 over
`D("protocol-stack:storage:archive-v1")` followed by every preceding archive
byte.

Archive import is streaming. It requires `genesis_length` to fit the accepted
canonical-genesis bound, each admitted count to be at most 65,535, each `u64`
length or count to fit the host `size_t` before conversion, and every
multiplication and addition to fit both `size_t` and the remaining input before
allocation or advancement. It never reserves memory directly from
`block_count`; even a zero-admission block must have its complete fixed record
available before the loop advances. Deployments may impose a documented
operational archive-size limit, but no storage limit changes consensus
acceptance.

Import is allowed only into a new empty database. It validates framing and
digests, loads genesis through the kernel, replays every admitted transaction
block, compares every transaction ID, receipt, root, header, and block ID,
compares the head snapshot, and only then creates the database. This archive,
not SQLite page bytes or its online-backup API, is the migration and removal
contract. A raw consistent backup may be offered separately for same-engine
operational recovery.

Snapshot creation and export are serialized with block application. They begin
one SQLite read transaction at a verified committed head, confirm that database
metadata and the owned ledger agree, and capture genesis, history, materialized
state, and head without releasing the adapter guard. A capture cannot combine
rows or state from different heights.

### Startup validation and recovery

Before exposing a ledger, opening performs:

1. `PRAGMA integrity_check`, requiring the single result `ok`, followed by an
   empty `foreign_key_check`;
2. exact application ID, user version, schema SQL, table, column, index, and
   constraint checks;
3. canonical genesis loading and comparison of chain ID and immutable
   parameters;
4. structural checks of all fixed widths, block heights, admitted ordinals,
   headers, and snapshot framing;
5. full replay from genesis, comparing each stored transaction ID, receipt,
   previous/transaction/resulting root, header, block ID, and any snapshot at
   the height just reached;
6. independent restoration of the latest retained snapshot and replay of its
   suffix, comparing each result with full replay;
7. exact comparison of the verified replay head with materialized accounts,
   fee pool, height, metadata root, and public ledger root.

For M1, full genesis replay remains the startup and audit authority even when a
snapshot exists. Snapshot-plus-suffix recovery is independently exercised and
must reach the identical head. Pruning history or trusting authenticated prefix
evidence requires a later ADR.

Unknown, older, newer, partially migrated, or semantically inconsistent
schemas are refused. M1 performs no in-place automatic migration and does not
repair or skip corrupt history.

### Failure model

A failure before the write transaction leaves durable and published state
unchanged. A statement failure before `COMMIT` preserves the old durable state
only after rollback succeeds and SQLite confirms that no transaction remains.

Once commit processing begins, any error from commit, rollback,
synchronization, journal cleanup, or adapter code before publication is
potentially ambiguous. The adapter then:

- withholds and discards the candidate;
- marks the instance poisoned;
- accepts no next height;
- finalizes every owned statement, incremental-BLOB handle, and backup handle,
  then requires `sqlite3_close` to return success without claiming a head;
- reopens through the complete recovery path;
- publishes only the recovered durable ledger.

`sqlite3_close_v2` is not used for recovery because it may return success while
leaving a zombie connection. A busy or otherwise unsuccessful close leaves the
instance terminal and still owning its connection; no replacement connection
is opened until cleanup and close are confirmed. Close is not treated as a
complete I/O-error reporting channel. The subsequent exclusive open and full
validation, not an assumed close result, establish the durable head.

The recovered database may be at the old or new height. The caller must
reconcile from the recovered height rather than blindly retrying. Storage
errors are typed operational errors, never protocol receipts or consensus
rejection codes.

## Alternatives

### LMDB 1.0

LMDB has a compact C API, copy-on-write pages, MVCC reads, and one active
writer, so it is the closest fallback. It was not selected because the new
1.0 line changes the established on-disk format, already has follow-up fixes,
requires explicit map sizing and `MAP_FULL` recovery, and provides a less
direct application-level fault-injection path. Selecting it would also require
forbidding `NOSYNC`, `NOMETASYNC`, `WRITEMAP`, `MAPASYNC`, and `NOLOCK`.

### RocksDB 11.1

RocksDB offers atomic write batches, synchronous WAL writes, checksums,
checkpoints, process locking, and extensive fault tools. Its large C++ build,
compression and support dependency graph, background flush and compaction
behavior, option surface, and file-format upgrade burden are disproportionate
for a small single-writer M1 node. Recent recovery and compaction corruption
fixes further increase the version-review obligation.

### Custom append-only journal

A custom journal would minimize third-party code but would make this project
responsible for filesystem locking, checksums, torn writes, sync ordering,
directory durability, crash recovery, compaction, snapshots, and fault
injection. `rename` alone does not make data durable; files and containing
directories require correct synchronization, and behavior still depends on the
filesystem and device. Reimplementing a database is not justified for M1.

## Consequences

- M1 gains one mature local transaction boundary with a small C API and a
  stable single-file database format.
- Every successful block has one durable database commit followed by one
  non-throwing in-memory publication point.
- Startup is deliberately expensive because it replays all retained history
  and cross-checks snapshots. Correctness evidence precedes pruning or fast
  startup.
- Exclusive locking prevents casual concurrent inspection. Export and backup
  operations run through the owning adapter.
- `journal_size_limit=0` favors bounded residual disk use over reusing the
  largest retained journal.
- Integrity checking detects structural corruption; semantic replay detects
  well-formed but incorrect ledger data. Neither repairs arbitrary media
  damage.
- The adapter relies on local filesystem and hardware durability contracts and
  must document that operational assumption for deployment.

## Verification gate

Acceptance requires all four compiler/sanitizer presets plus:

- create, close, reopen, empty-block, all-unadmitted-block, execution-failure,
  long seeded sequence, repeated-restart, and full-genesis-replay tests;
- snapshot encode/decode, export/import, snapshot-plus-suffix, and independent
  format fixtures;
- second-writer exclusion and stable-path misuse tests;
- semantic corruption, structural corruption, truncated history, duplicate or
  missing ordinal, unknown schema, wrong genesis, and projection-mismatch
  tests;
- adapter fault points before, during, and after every commit phase, including
  rollback failure; the durable-commit-before-publication interval is tested
  only by a non-returning subprocess kill hook, never by a recoverable callback
  or exception;
- SQLite VFS injection for short writes, disk-full, I/O, sync, truncate, and
  delete failures, plus subprocess termination around commit boundaries;
- Clang sanitizer fuzz targets for snapshot and archive decoding, with
  structured valid seeds and malformed length, count, overflow, truncation, and
  trailing-byte cases;
- unchanged frozen ledger vectors through commit, reopen, snapshot restore,
  and replay.

## Update and removal path

An SQLite update requires a new exact archive pin and integrity review, release
and corruption-fix review, confirmation of every compile option and runtime
setting, clean builds in all presets, and the complete recovery/fault suite.
The storage schema never changes merely because SQLite changes.

A schema change increments the operational format version and is implemented
as export, validate, and import into a new file. In-place guessing or partial
migration is forbidden. Keep the old database recoverably until the new file
has completed full replay and head comparison.

To replace SQLite, export the versioned portable archive through the adapter,
import it into the replacement engine, and replay and compare every canonical
output and final state. Close both adapters, change configuration to the
already verified new pathname, start and validate the replacement, and retain
the old database recoverably until post-switch verification succeeds. This is
an explicit offline cutover; it does not claim a crash-atomic cross-engine
rename.

## Primary references

- [SQLite 3.53.3 release](https://sqlite.org/releaselog/3_53_3.html)
- [SQLite source downloads and hashes](https://sqlite.org/download.html)
- [SQLite copyright](https://sqlite.org/copyright.html)
- [Appropriate uses for SQLite](https://sqlite.org/whentouse.html)
- [Atomic commit in SQLite](https://sqlite.org/atomiccommit.html)
- [SQLite locking](https://sqlite.org/lockingv3.html)
- [SQLite PRAGMA reference](https://sqlite.org/pragma.html)
- [SQLite temporary and journal files](https://sqlite.org/tempfiles.html)
- [SQLite compile-time options](https://sqlite.org/compile.html)
- [SQLite security guidance](https://sqlite.org/security.html)
- [How SQLite is tested](https://sqlite.org/testing.html)
- [How SQLite databases become corrupt](https://sqlite.org/howtocorrupt.html)
- [SQLite online backup API](https://sqlite.org/backup.html)
- [SQLite transaction error behavior](https://sqlite.org/lang_transaction.html)
- [LMDB source and API](https://github.com/LMDB/lmdb)
- [RocksDB basic operations](https://github.com/facebook/rocksdb/wiki/Basic-Operations)
- [RocksDB overview](https://github.com/facebook/rocksdb/wiki/RocksDB-Overview)
- [Linux `fsync(2)`](https://man7.org/linux/man-pages/man2/fsync.2.html)
- [Linux `rename(2)`](https://man7.org/linux/man-pages/man2/rename.2.html)
