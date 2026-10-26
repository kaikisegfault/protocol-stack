# ADR 0109: The version-ten owning store moves two widths and two markers, and writes each marker once

- Status: Accepted
- Date: 2026-10-26
- Bounds: [ADR 0081](0081-the-version-nine-owning-store.md),
  [ADR 0067](0067-the-version-eight-owning-store.md),
  [ADR 0057](0057-the-version-seven-owning-store.md),
  [ADR 0007](0007-sqlite-ledger-persistence.md)
- Follows: [ADR 0104](0104-the-version-ten-kernel-is-staged-beside-version-nine.md),
  step 4, and [ADR 0108](0108-the-version-ten-snapshot.md)
- Relates to: `include/protocol/storage/sqlite_ledger_v10.hpp`,
  `src/storage/sqlite_ledger_v10*.cpp`, `src/storage/sqlite_schema_v10.cpp`

## Context

[ADR 0108](0108-the-version-ten-snapshot.md) made a version-ten state
expressible as canonical bytes. ADR 0104 puts the owning store next, because the
application, the transport, and the node all wait on a durable head.

**Almost all of the store needed no decision.** The connection, locking,
journal, and path-stability contract is version one's. The head-as-one-payload
layout, the candidate-copy write path, the poisoning rule, the recovery, the
seed and its inspection, and the storage-code vocabulary are ADR 0057's, ADR
0067's, and ADR 0081's, and none of it is version-specific. The store is version
nine's with the namespace rebound. Normalised against version nine's, the two
store units differ in comments alone, and the schema unit in its widths, its
markers, and the one finding below.

**The store had nothing model-recorded to replay.** Every recorded
version-ten chain jumps to the activation height, and a store commits one height
at a time. M4.3h-1 recorded a five-height `restart.` run contiguous from genesis
first (issue #411). Its fifth block registers both machines through kind 23.

## Decisions

### 1. Two widths move and one does not

The DDL is stored and compared verbatim on every open, and three of its literals
are widths:

- `canonical_genesis` is `v10::kGenesisPrefixBytes`, **182** rather than version
  nine's 150, because the build authority key is a genesis field;
- `head_snapshot` is `snapshot_v10`'s `kFixedSize`, **262** rather than 230: the
  198-octet prefix, a root, and a digest (ADR 0108);
- `header` is `v10::kBlockHeaderBytes`, **still 154**, because version ten keeps
  version nine's header schema and bytes.

Each is checked at its boundary, as ADR 0081 decided. One octet below is refused
by SQLite's own CHECK and exactly the width is admitted. The snapshot boundary
is 261 refused and 262 admitted, which a stale 230 would fail. The genesis
boundary is version nine's 150 refused and 182 admitted.

### 2. The application identifier is `PS10`, and the schema version is 10

Version nine's identifier is `PSL9`, version one's `PSLD` with its version in the
last octet. A two-digit version does not fit there, so version ten's takes the
last two octets: `PS10`, `0x50533130`. The tables are `ledger_meta_v10` and
`blocks_v10`. A version-nine file presented to this store fails on its first
pragma, before its table names or its 150-octet genesis are read. The tamper
cases rewrite each marker to version nine's value and require
`schema_mismatch`.

### 3. The build authority key reaches a restore from the genesis alone

The store derives a restore's six parameters from the genesis its caller
presents. ADR 0108 made the build authority key the sixth, because the ledger
keeps it, kind 23 reads it, and no root commits to it. So it is never read from
the file. A genesis that differs only in that key is refused at open as
`genesis_mismatch`, because it changes the canonical bytes, and refused as a
seed as `invalid_snapshot`, because it changes the chain identity the payload
names.

**The evidence aims at it.** No root commits to the key, so every root
comparison holds for a store that lost it. The restart run's fifth block is
applied by a store reopened just before it, and its two recorded kind-23
successes are what show the key reached the reopened head. Every head check
also compares the key itself. A probe that zeroed the key after the restore was
caught by that comparison at the first reopen.

## The finding

**The first port created files under version nine's markers, then refused to
reopen any of them.**

Version nine's schema states each marker twice. The constants
`kApplicationIdV9` and `kSchemaVersionV9` are what a reopen compares against,
and `install_schema_v9` writes the pragmas as separate literals,
`"PRAGMA main.application_id = 1347636281"` and `"PRAGMA main.user_version = 9"`.
The port changed the constants and kept the literals. The store therefore wrote
`PSL9` and 9, committed the first block, and refused its own file at the first
reopen as `schema_mismatch`. The restart-equivalence case caught it, because it
reopens before the second block.

**Version ten writes both pragmas from the constants**, so each marker is one
fact. Version nine's store is left as it is: it is delivered, it is correct, and
ADR 0104's step 7 deletes it. The defect only appears when a copy changes one of
the two statements.

## Evidence

- `storage_sqlite_ledger_v10_tests`, CTest `version-ten-owning-store`:
  - the restart run applied through a database closed and reopened before every
    block. Every block reproduces its recorded root, block identifier,
    transaction root, admitted count, and stamp. The stored block rows are read
    back with a bare connection;
  - the same five blocks without a restart;
  - version nine's refusals, rebound: a height away from the next, a block the
    kernel rejects, both clock refusals, another genesis, another genesis
    timestamp, another build authority key, and an invalid genesis;
  - tampering with each marker, column, and payload, the three width
    boundaries, and a corrupted page;
  - seeding from a two-block head and executing blocks three to five to the
    recorded roots, with every seed refusal matched by inspection.
- `storage_sqlite_recovery_v10_tests`, CTest `version-ten-store-recovery`:
  version nine's fault matrix against the restart run's first block. Every
  rolled-back fault, a failed commit that recovers, one that cannot recover and
  stays poisoned, and a termination after the commit and after the publication.
- **Local, against a scratch header and the system SQLite 3.40.1 runtime**:
  both suites pass. The repository pins 3.53.3, and the hosted matrix is the
  gate. Three mutation probes each fail the suite: a stale 230 for the
  snapshot width, a stale 150 for the genesis width, and a restore that drops
  the build authority key.

## Alternatives rejected

- **`PSLA` as the identifier**, the tenth value in hexadecimal. It keeps the
  `PSL` prefix, but a reader would take `A` for a letter rather than a version.
- **Fixing version nine's store as well.** It is correct as delivered. Changing
  it would put a commit against a version that is to be deleted, and would not
  move its tests.
- **Keeping a column for the build authority key.** The genesis it is derived
  from is already stored and compared byte for byte on every open. A column
  would be a second copy that could disagree.

## Consequences

**A version-ten chain now survives the process that built it.** The next step
is ADR 0104's step 5: the application, the transport, and an application
contract that names `economy-transition-v10`, maps results 1 through 49, and
reads a 182-octet genesis. `economy-transition-v10` leaves to that slice whether
the contract is a new version or a stated rebinding.

**Both stores are compiled and both suites run** until ADR 0104's step 7, which
is the staged coexistence that record allows.
