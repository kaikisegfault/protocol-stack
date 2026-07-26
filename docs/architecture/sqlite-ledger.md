# SQLite ledger boundary

Status: M1 implementation architecture

ADR 0007 selects SQLite as a replaceable operational persistence engine. This
document describes the implemented owning C++ boundary. Storage rows and files
do not define protocol meaning; the ledger kernel and its canonical bytes
remain authoritative.

## Implemented outcome

`create_sqlite_ledger` creates a brand-new database at height zero and commits
the caller-configured canonical genesis state. `SQLiteLedger::apply_block`
copy-constructs an independent kernel candidate, applies the complete ordered
raw-input block, persists the resulting materialized state and canonical
history in one transaction, commits, and publishes the candidate through a
non-throwing pointer swap. A kernel block rejection never starts a storage
transaction.

`open_sqlite_ledger` performs full genesis replay of every retained block
before publishing a live ledger. It admits only the stored 200-byte journal
rows, in explicit height and ordinal order, and compares every replayed
transaction ID, receipt, root, application header, and block ID with the
stored canonical output. The replay head must then exactly equal metadata,
materialized accounts, the fee pool, and the public ledger root.

The public engine-independent snapshot codec implements ADR 0007's exact
`PSSN` version-one bytes. Decoding verifies framing and the exact total length
before account allocation, checks the SHA-256 domain-separated digest, requires
strict account ordering, validates caller-trusted immutable parameters, and
restores through the kernel's state-invariant and root checks.

The public engine-independent archive codec implements ADR 0007's exact
`PSAR` version-one bytes. The encoder accepts canonical genesis, contiguous
canonical block outputs and admitted transaction records, plus a head
snapshot. It independently loads genesis, replays every admitted block through
the kernel, exact-compares transaction IDs, receipts, headers and block IDs,
and requires the decoded snapshot to equal the replayed head before emitting
bytes. The decoder bounds all attacker-controlled lengths and counts before
allocation or advancement, never reserves from the declared block count,
rejects non-exact framing, verifies the archive digest, and performs the same
complete semantic replay.

`SQLiteLedger::create_snapshot` serializes with reads and block application,
verifies that the durable metadata head equals the owned ledger, independently
decodes the candidate bytes, and atomically replaces the one retained snapshot.
It returns the exact durably stored payload. Opening independently decodes that
snapshot and compares its complete state and root at the same height reached by
authoritative full-genesis replay. It then starts a second ledger from that
independently restored snapshot, re-queries and replays only later block and
journal rows, compares every suffix transaction ID, receipt, root, header, and
block ID, and requires the recovered state and root to equal authoritative full
replay. A snapshot at the current head exercises the same path with an empty
suffix.

`SQLiteLedger::export_archive` holds the adapter guard and one SQLite read
transaction while it fully validates the durable ledger against
caller-trusted genesis and the owned head. It creates a fresh snapshot of that
verified head, then reads every block and admitted transaction in explicit
height and ordinal order with exact width, count, and contiguity checks. The
public codec replays that independently projected archive before export
returns. Export does not change the retained database snapshot.

`import_sqlite_archive` accepts an untrusted `PSAR` version-one payload and a
new target pathname. It decodes, digest-checks, and semantically replays the
complete archive before normalizing or reserving the target. Any archive
framing, genesis, history, projection, snapshot, or digest failure returns
`SQLiteLedgerError::invalid_archive` and creates no target artifact.

After validation, import exclusively reserves the target and installs the
schema, exact admitted history, materialized head, metadata, and exact archive
snapshot in one SQLite transaction. It closes that creation connection,
reopens through the ordinary full-genesis replay and snapshot-plus-suffix
validation path using the archive's canonical genesis, and requires a fresh
export to be byte-identical to the input before returning the live ledger.
Import never overwrites an existing path, performs no in-place migration, and
leaves a reserved artifact for diagnosis if an operational failure occurs
after reservation.

The public header exposes no SQLite handle or SQL type. `SQLiteLedger` is
move-constructible but not copyable or assignable. It owns the live
`protocol::v1::Ledger`, serialized connection, normalized path, exact canonical
genesis bytes, and cached state root. `read_head` returns either owned state
and root values or a typed storage error while holding the adapter mutex;
callers receive no borrowed view, and a poisoned instance never exposes its
possibly stale pre-commit cache.
`apply_block` returns one of the exact kernel `BlockCommit`, the deterministic
kernel `BlockError`, or an operational `SQLiteLedgerError`.

## Trusted creation input

The caller supplies canonical genesis bytes whose identity is trusted outside
the database. The adapter fully loads and copies those bytes before touching
the target path. Invalid genesis therefore creates no artifact.

Creation requires an absolute path with an existing local directory. It
reserves the final filename with `O_CREAT|O_EXCL|O_NOFOLLOW`, forces mode
`0600`, synchronizes the empty file and parent directory, and retains that
reservation descriptor for the adapter lifetime. SQLite closes before the
descriptor. If a later creation step fails, the reserved artifact is
deliberately left in place and ordinary opening rejects it; creation never
silently overwrites or retries through an existing path.

Existing opens never create a file. They reject missing, non-regular,
symbolic-link, or multiply linked targets. The adapter requires a stable,
trusted local pathname and checks SQLite's `SQLITE_FCNTL_HAS_MOVED` result
before publication. Moving, replacing, unlinking, or externally editing the
database or journal while open remains unsupported.

## Connection and durability

The connection uses a private cache, full mutexing, extended result codes, and
no-follow behavior without URI interpretation. Before publication it enables
SQLite defensive mode, disables trusted schema, triggers, views, and memory
mapping, and reads back foreign-key, cell-size, synchronization, journal-size,
busy-timeout, and exclusive-locking settings.

Creation acquires lifetime-exclusive ownership and then establishes rollback
`DELETE` journal mode. Existing open acquires ownership before querying and
requiring that mode, so it cannot silently transition an unvalidated WAL
database. `synchronous=EXTRA` and the explicit `BEGIN EXCLUSIVE; COMMIT`
ownership transaction implement ADR 0007's single-writer local-filesystem
contract. Lock contention fails immediately as
`SQLiteLedgerError::lock_unavailable`.

## Schema and validation

Schema version one sets application ID `0x50534c44` and user version `1`. It
installs exactly five `STRICT`, `WITHOUT ROWID` tables:

- `ledger_meta`;
- `accounts`;
- `blocks`;
- `admitted_transactions`;
- `snapshots`.

Protocol unsigned integers use fixed-width big-endian BLOBs, and identifiers
and roots retain their exact protocol widths. Typed immutable-parameter
projections are checked against canonical genesis bytes. Schema validation
checks the exact schema SQL plus table, column, primary-index, strictness,
rowid, and foreign-key metadata; unknown or modified objects are refused.

Opening requires a single successful `integrity_check` result and an empty
`foreign_key_check`. It exact-compares the persisted canonical genesis with
the independently trusted caller value, replays contiguous block and admitted
transaction rows from genesis, bounds materialized account loading by the
verified replay account count, reconstructs an owned state, and calls
`restore_ledger` with caller-derived immutable parameters and the stored root.
The result must exactly equal the independently replayed state and root.

Admission failures are absent from the journal. Empty and entirely unadmitted
blocks still have a block row and advance height. Duplicate admitted
transactions retain separate contiguous ordinals. Database projections never
replace canonical transaction, receipt, header, or identifier bytes as the
replay authority.

## Error and lifetime behavior

Expected operational rejection is returned as a closed
`SQLiteLedgerError`: invalid genesis or path, existing or missing target, lock
contention, configuration mismatch, integrity failure, schema mismatch,
genesis mismatch, materialized-state mismatch, or generic storage failure.
Allocation exceptions remain local C++ operational failures.

Statements, the SQLite connection, and the creation reservation descriptor use
RAII. A destructor-time close failure terminates rather than silently
discarding an uncertain connection; an explicit recovery-time close failure
leaves the instance terminal and still owning that connection. No fallible
allocation occurs after durable creation validation and before the completed
adapter is returned.

Any error once commit processing begins poisons the live instance and withholds
the candidate. The adapter explicitly closes the owning connection, reopens
through the ordinary integrity, schema, genesis, full-history, snapshot-suffix,
and materialized-head checks, then atomically publishes the recovered old or
new durable head. The failed block call remains an operational error so the
caller must read and reconcile the recovered height. If close or reopen fails,
head reads and later block calls return `storage_failure`.

An internal test-only hook observes the transaction-begin, persistence,
pre-commit, post-commit/pre-publication, and publication boundaries. Tests may
use it to make SQLite reject a commit. The post-commit boundary accepts only a
non-returning child-process termination test; normal execution performs no
fallible work there.

A separate test executable registers a wrapper around SQLite's ordinary
default VFS. The wrapper delegates unchanged behavior except for one armed,
one-shot journal operation. It covers a deliberately partial write reported as
`SQLITE_IOERR_WRITE`, `SQLITE_FULL`, ordinary write I/O error, sync error,
truncate error, and delete error. Pre-commit write failures must retain the old
head. Commit and cleanup failures may recover either the old or new durable
head, but the adapter must validate that head before continuing; every case
then closes and reopens through the ordinary validator.

## Remaining issue 11 work

The ordinary durable commit, full-genesis-replay path, canonical snapshot and
archive codecs, atomic latest-snapshot persistence, independent
snapshot-plus-suffix recovery, portable export, and portable import are
implemented. Automatic close/reopen after an ambiguous commit result and the
block-phase and SQLite VFS injection boundaries are also implemented. Expanded
subprocess termination coverage, long seeded restart sequences, and final issue
closure remain.
