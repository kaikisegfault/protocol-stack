# SQLite ledger boundary

Status: M1 implementation architecture

ADR 0007 selects SQLite as a replaceable operational persistence engine. This
document describes the implemented owning C++ boundary. Storage rows and files
do not define protocol meaning; the ledger kernel and its canonical bytes
remain authoritative.

## Implemented outcome

`create_sqlite_ledger` now creates a brand-new database at height zero and
commits the caller-configured canonical genesis state. `open_sqlite_ledger`
reopens only that closed-world height-zero form. It rejects any database with
block, admitted-transaction, or snapshot rows until replay and recovery are
implemented.

The public header exposes no SQLite handle or SQL type. `SQLiteLedger` is
move-constructible but not copyable or assignable. It owns the live
`protocol::v1::Ledger`, serialized connection, normalized path, exact canonical
genesis bytes, and cached state root. `read_head` returns owned state and root
values while holding the adapter mutex; callers receive no borrowed view.

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
the independently trusted caller value, bounds account loading by the trusted
genesis account count, reconstructs an owned state, and calls
`restore_ledger` with caller-derived immutable parameters and the stored root.
The result must exactly equal the independently loaded genesis state and root.

## Error and lifetime behavior

Expected operational rejection is returned as a closed
`SQLiteLedgerError`: invalid genesis or path, existing or missing target, lock
contention, configuration mismatch, integrity failure, schema mismatch,
genesis mismatch, materialized-state mismatch, or generic storage failure.
Allocation exceptions remain local C++ operational failures.

Statements, the SQLite connection, and the creation reservation descriptor use
RAII. A close failure terminates rather than publishing an uncertain storage
state. No fallible allocation occurs after durable creation validation and
before the completed adapter is returned.

## Remaining issue 11 work

The current boundary deliberately cannot apply or replay a block. The next
vertical result is one atomic durable block commit followed by validated clean
reopen and full genesis replay. Snapshot recovery, portable export/import,
fault injection around commit phases, long restart sequences, and final issue
closure follow that working block path.
