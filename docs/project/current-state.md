# Current state

Last updated: 2026-07-26

## Phase

M1 — Sovereign Devnet Alpha. The deterministic in-memory ledger kernel is
merged and verified. The owning storage adapter can now durably create and
validate a height-zero ledger, atomically persist a complete block, and reopen
the identical head through full genesis replay. Deterministic multi-block
restart, snapshot recovery, portable export, new-database archive import, and
fail-closed ambiguous-commit reopen are complete; expanded interruption and
long seeded recovery sequences remain the active roadmap slice.

## Verified facts

- Repository: `kaikisegfault/protocol-stack`.
- F0 merged to `main` through PR #3 on 2026-07-23.
- The reproducible build/toolchain slice merged through PR #7 on 2026-07-23;
  all four GitHub compiler/sanitizer jobs passed.
- Ledger-transition v1 merged through PR #9 on 2026-07-23; all four GitHub
  compiler/sanitizer jobs passed.
- The complete issue #8 in-memory kernel merged through PR #10 on 2026-07-23;
  all four GitHub compiler/sanitizer jobs passed.
- Issue #11 defines the next M1 slice for replaceable atomic persistence,
  reopen/replay, snapshots, corruption detection, and crash recovery.
- ADR 0007 selects the official SQLite 3.53.3 autoconf archive at SHA-256
  `c917d7db16648ec95f714974ace5e5dcf46b7dc70e26600a0a102a3141125db0`
  as the replaceable M1 persistence engine. The adapter requires local
  rollback-journal storage, `synchronous=EXTRA`, lifetime exclusive locking,
  full genesis replay, independent snapshot-plus-suffix recovery, and a
  versioned engine-independent export path.
- On 2026-07-23 the owner granted standing authority for autonomous project
  decisions and repository operations. A `proceed` instruction requires no
  follow-up approval.
- `.codex/config.toml` selects `gpt-5.6-sol` with extra-high (`xhigh`)
  reasoning.
- ADR 0004 accepts PureEdDSA Ed25519, SHA-256 with explicit domain separation,
  fixed-width big-endian PSCE, 32-byte account IDs with Bech32m text addresses,
  and RFC 9162-style ordered Merkle trees for M1.
- ADR 0005 pins CMake 4.4.0, Ninja 1.13.0, and libsodium 1.0.22 with exact
  SHA-256 integrity checks. The supported bootstrap is Linux x86_64.
- Strict signature acceptance requires libsodium-compatible canonical and
  small-order rejection. OpenSSL 3.0.20 alone accepted the adversarial
  identity-key vector and is not a valid consensus verifier.
- `tools/verify.sh` is the clean-clone entry point. It isolates build tools in
  an ignored virtual environment, builds the pinned libsodium and SQLite
  sources, and runs C++ and standard-library-only Python checks through CTest.
- ADR 0006 and `ledger-transition-v1.md` define canonical genesis, a
  single-native-asset transfer, fixed fee-pool routing, exact nonce/expiry and
  failure rules, receipts, and ordered atomic block execution.
- The 1,048,576-byte canonical-object limit bounds version-one genesis to
  21,844 accounts. Transaction shape errors are malformed, while all strict
  Ed25519 canonicality, small-order, and equation failures are invalid
  signatures after the chain check.
- The M1 devnet uses nine atomic decimal places, a `10^18` atomic supply limit,
  a default `10^17` atomic four-account genesis, a 1,000-atomic fixed fee, and
  no post-genesis issuance.
- The in-memory kernel implements strict transaction admission, checked
  transfer execution, bounded canonical genesis loading, state and transaction
  commitments, receipts, and atomic ordered block commit behind an owning
  public `Ledger`.
- Account IDs, chain IDs, transaction IDs, state roots, transaction roots, and
  block IDs are distinct tagged C++ types with unchanged canonical 32-byte
  representations. Persistence, networking, RPC, consensus integration, and
  deployment remain outside the kernel.

## Verification evidence

- The fixed primitive vector suite passes through `tools/verify.sh` with GCC
  12.2.0, Clang 14.0.6, and `-Wall -Wextra -Wpedantic -Werror`.
- Both GCC and Clang AddressSanitizer plus UndefinedBehaviorSanitizer presets
  pass.
- Vectors cover RFC 8032 interoperability, domain separation, transaction
  bytes and identifiers, Bech32m, state and transaction roots, mutation,
  malformed length, checksum, non-canonical scalar, small-order, supply-bound,
  conservation, and ordering rejection.
- CMake preset JSON, TOML, GitHub workflow and issue-form YAML, Python bytecode
  compilation, shell syntax, internal Markdown links, and `git diff --check`
  pass.
- The independent C++20 and Python ledger decision harnesses reproduce a
  canonical genesis, chain ID, 11 admitted transaction results, three
  admission error classes plus unknown-kind rejection, ordered receipts,
  recipient creation, fee routing, final accounts, transaction/state roots,
  application header, and block ID.
- Ledger vectors cover success, replay, self-transfer, zero amount, low fee
  limit, expiry, absent sender, nonce mismatch and exhaustion, debit overflow,
  insufficient balance, malformed bytes, wrong chain, invalid signature, and
  unauthorized transaction kind.
- All four local presets pass 4/4 CTest tests: GCC, GCC ASan+UBSan, Clang, and
  Clang ASan+UBSan.
- The initial production kernel slice uses owned value types, exact canonical
  shape and chain checks, domain-separated account/transaction IDs, and the
  pinned strict libsodium adapter. Its frozen admission vectors pass 5/5 CTest
  tests under all four local presets.
- The unchanged primitive vector now runs directly through production hashing,
  strict Ed25519 verification and admission, canonical Bech32m address
  encoding/decoding, populated and empty state commitments, and ordered
  transaction commitments. Focused cases cover non-canonical `S`, small-order
  public keys and `R`, malformed lengths, bad checksums and padding, wrong
  chains and HRPs, and admission-precedence overlaps.
- Checked production transfer execution reproduces all nine result codes and
  the 11 admitted frozen-vector receipts. Tests establish fee routing,
  conservation after every accepted transition, self-transfer, recipient
  creation, nonce exhaustion, and byte-equivalent state atomicity for ordinary
  failures and checked recipient/fee-pool invariant failures.
- All four local presets pass 6/6 CTest tests with the transfer execution
  slice: GCC, GCC ASan+UBSan, Clang, and Clang ASan+UBSan.
- The production genesis decoder accepts the full 21,844-account boundary,
  rejects an oversized declared count before allocation, and covers malformed
  framing, parameter, account-order, checked-supply, exact-`u64`, and trailing
  byte failures.
- Commitment tests reproduce the frozen previous/resulting state roots,
  ordered transaction root, canonical receipt bytes, block header, and block
  ID, and independently cover RFC 9162 tree shapes through 65,535 leaves.
- The public ledger tests run the unchanged frozen vectors through production
  genesis load and atomic block commit. They cover all five genesis error
  classes, raw/admitted output alignment, exact receipt bytes, height and
  65,535-input boundaries, empty and unadmitted blocks, duplicates, ordering,
  determinism, tentative-copy isolation, and internal execution atomicity.
- All four local presets pass 9/9 CTest tests with the public block slice: GCC,
  GCC ASan+UBSan, Clang, and Clang ASan+UBSan.
- Deterministic property tests run 9,000 generated states and transfers, cover
  all nine execution results with deliberately overlapping invalid conditions,
  compare every successful post-state exactly, and assert determinism,
  failure atomicity, receipt validity, commitment validity, and supply
  conservation.
- A standard-library-only Python reference model differentially checks 10,000
  nonempty SplitMix64-v1-seeded transaction sequences plus 11 directed
  sequences against the public C++ ledger. Across 19,972 successful blocks and
  60,432 raw inputs, it compares raw-aligned admission results, 48,471 admitted
  transaction IDs, typed and encoded receipts, all roots, headers, block IDs,
  immutable parameters, height, fee pool, and every account after each block.
- The randomized corpus independently covers all three admission errors, every
  execution result reachable from valid genesis, replay, reversed order,
  self-transfer, recipient creation, empty blocks, and all-unadmitted blocks.
  Nonce exhaustion and rejected genesis/block containers remain covered by
  focused boundary tests because nonce exhaustion is not reachable from valid
  genesis within a bounded sequence.
- All four local presets pass 11/11 CTest tests with property and differential
  coverage: GCC, GCC ASan+UBSan, Clang, and Clang ASan+UBSan.
- The Clang sanitizer preset builds a separate copy of every kernel source with
  libFuzzer coverage instrumentation. Fixed-seed 512-input smoke sessions
  exercise raw and structured transaction admission up to 256 bytes, raw and
  structured address decoding up to 256 bytes, and raw and structured genesis
  loading up to 4,096 bytes. Every callback includes a valid signed
  transaction, canonical address round trip, or successful minimal genesis,
  respectively.
- The Clang ASan+UBSan preset passes 15/15 CTest tests including all three fuzz
  targets; GCC, GCC ASan+UBSan, and Clang pass 12/12.
- The integrity-pinned SQLite 3.53.3 dependency builds only its static library
  and public headers, with loadable extensions, JSON, math functions, carray,
  and readline disabled. Its dependency test checks the exact header and
  runtime source identities, serialized thread mode, hardening options,
  untrusted-schema default, rollback journaling, `synchronous=EXTRA`, strict
  tables, durable commit-and-reopen, and rollback-and-reopen.
- Clean dependency-slice verification passes 13/13 CTest tests in GCC debug,
  GCC ASan+UBSan, and Clang debug, and 16/16 in Clang ASan+UBSan including all
  three fuzz targets. Both sanitizer presets compile the SQLite amalgamation
  itself with AddressSanitizer and UndefinedBehaviorSanitizer.
- `restore_ledger` is the public operational construction boundary for a live
  materialized state. It accepts state by value, validates intrinsic state
  invariants before caller-trusted canonical-genesis parameters and the
  expected root, and constructs no ledger on any typed failure. The parameter
  anchor closes the version-one state root's intentional omission of
  `fixed_fee` without changing frozen commitment bytes or transitions.
- The public move-only `SQLiteLedger` owns the live kernel ledger, hardened
  SQLite connection, trusted canonical-genesis copy, and cached root behind a
  mutex. It exposes only an owned coherent head and no SQLite handle or
  borrowed state.
- Creation prevalidates genesis before exclusively reserving an absolute local
  path, installs the exact five-table version-one schema, commits genesis
  accounts and metadata, and retains lifetime single-writer ownership.
  Reopening never creates or changes journal mode and publishes no ledger
  unless integrity, foreign keys, exact schema, caller-trusted genesis,
  materialized state, and root all agree.
- `SQLiteLedger::apply_block` applies ordered raw inputs to an independent
  ledger candidate, writes changed and created accounts, exact admitted
  transaction bytes and kernel outputs, the block row, and head metadata in
  one SQLite transaction, durably commits, and publishes through a
  non-throwing owning-pointer swap. Kernel block rejection never opens a
  storage transaction.
- Opening validates caller-trusted genesis before history, then full-replays
  contiguous block and admitted-transaction rows in explicit height and
  ordinal order. Every replayed transaction ID, receipt, root, application
  header, and block ID must equal storage before the replay head is compared
  exactly with materialized state and metadata. Snapshot rows remain refused.
- The owner prefers one active delivery branch, cleanup of obsolete
  branches/worktrees/build trees at phase boundaries, focused checks while
  iterating, GitHub-hosted execution for heavy gates, no detached local work,
  process and remote-run audits, and removal of reproducible local artifacts
  after every completed phase. `AGENTS.md`, the project skills, and the
  engineering guides record that durable workflow.
- GitHub is the strict durable publication boundary: every retained branch must
  be clean and equal to its upstream at handoff; completed PRs must be merged
  and pruned; local `main` must equal `origin/main`; and only `main` plus one
  documented active delivery branch may remain remotely.
- Restore tests prove genesis and nonzero-height reconstruction, ordinary and
  restored block-output equivalence, next-block continuation, copy/move
  ownership, live zero-balance accounts with nonzero nonce, intrinsic invariant
  rejection, every parameter mismatch, stale roots, and error precedence.
  GCC debug, GCC ASan+UBSan, and Clang debug pass 14/14 CTest tests; Clang
  ASan+UBSan passes 17/17 including all three fuzz targets.
- Clean verification of the height-zero storage slice passes 15/15 CTest tests
  with GCC debug and Clang debug. GCC and Clang ASan+UBSan pass 15/15 and
  18/18 respectively with leak detection disabled because the managed
  execution sandbox traces processes and LeakSanitizer refuses to run under
  `ptrace`; Clang includes all three fuzz smoke tests. Before that sandbox
  transition, the exact focused `storage-sqlite-ledger` test also passed the
  unmodified GCC sanitizer preset with LeakSanitizer enabled.
- Storage coverage proves exclusive creation, private permissions, independent
  and repeated reopen, owned reads and moves, cross-process and in-process
  lock exclusion, no-overwrite/no-create failures, symlink and hard-link
  rejection, unexpected-WAL preservation, exact schema and version refusal,
  wrong genesis, materialized-state and root corruption, immutable-fee
  projection corruption, foreign-key damage, truncated files, and refusal of
  unvalidated history.
- The frozen 15-input ledger block now passes through durable storage with the
  exact kernel `BlockCommit`, 11 admitted journal rows, three omitted
  admission failures, unchanged head on a rejected repeated height, clean
  close, full genesis replay, and an identical owned head.
- Replay rejection coverage proves wrong-genesis precedence at nonzero height,
  missing admitted ordinals, altered transaction and block identifiers, and
  materialized state divergence are refused before publication.
- A four-block restart harness covers a mixed 15-input block, an empty block,
  an entirely unadmitted block, and duplicate admitted transactions. It closes
  and fully reopens before every continued commit, compares each durable
  `BlockCommit` and head with an independent in-memory kernel, confirms four
  block rows and 13 admitted rows, and repeats final reopen twice.
- Clean completion verification passes 16/16 CTest tests in GCC debug, GCC
  ASan+UBSan, and Clang debug, and 19/19 in Clang ASan+UBSan including the
  three existing kernel fuzz smoke tests. Leak detection is disabled only for
  sanitizer completion runs because the managed execution sandbox traces
  processes and LeakSanitizer refuses to run under `ptrace`.
- The public engine-independent snapshot codec implements the exact ADR 0007
  `PSSN` version-one bytes, rejects unsupported versions and non-exact lengths
  before allocation, checks host-size arithmetic, verifies the domain-separated
  digest, requires strict account ordering, anchors immutable parameters to the
  caller-trusted genesis, and restores only a state with matching invariants
  and root.
- `SQLiteLedger::create_snapshot` serializes with block application, confirms
  the durable metadata head, independently decodes the candidate, atomically
  retains one latest snapshot, and returns its exact bytes. Full genesis replay
  independently restores and exact-compares a retained snapshot at its recorded
  height, including when later blocks have advanced the durable head.
- Focused GCC debug verification passes the new `storage-snapshot-v1` test plus
  the existing `storage-sqlite-ledger` and `storage-sqlite-history` tests. The
  snapshot suite freezes the genesis digest; covers deterministic round trips,
  truncation, trailing bytes, count overflow, wrong magic/version/digest,
  parameter, ordering, conservation and root failures; replaces a height-zero
  snapshot at height two; reopens across an older snapshot; and rejects corrupt
  row projections or multiple retained snapshots.
- The Clang sanitizer preset includes a fourth bounded libFuzzer smoke target
  for raw and structured snapshot bytes with a valid seed. PR #15 merged the
  snapshot slice as `63ff68f`; exact-candidate Actions run 30163985474 and
  post-merge `main` run 30164137810 both passed GCC and Clang debug plus
  ASan/UBSan. The first three jobs passed 17/17 tests and Clang ASan/UBSan
  passed 21/21 including all four fuzz targets.
- Opening now starts a second recovery ledger from the independently decoded
  latest snapshot, re-queries and replays only its later block and journal
  rows, compares every suffix transaction ID, receipt, root, header, and block
  ID, and requires the recovered state and root to equal authoritative full
  genesis replay. Restart coverage exercises genesis, behind-head, and
  current-head snapshots, including nonempty and empty suffixes. Focused GCC
  debug verification passes this path together with both existing SQLite test
  targets, 3/3.
- PR #16 merged snapshot-plus-suffix recovery as `3102adf`; exact-candidate
  Actions run 30164373238 and post-merge `main` run 30164507913 both passed GCC
  and Clang debug plus ASan/UBSan. The first three jobs passed 17/17 tests and
  Clang ASan/UBSan passed 21/21 including all four fuzz targets.
- The public engine-independent archive codec implements ADR 0007's exact
  `PSAR` version-one framing. It bounds hostile lengths and counts before
  allocation or advancement, verifies the domain-separated digest, loads
  canonical genesis, replays every admitted block, exact-compares transaction
  IDs, receipts, headers and block IDs, and requires the head snapshot to
  equal the replayed state and root.
- `SQLiteLedger::export_archive` serializes with block application and holds
  one read transaction while it fully validates the durable ledger against
  caller-trusted genesis and the owned head, creates a fresh head snapshot,
  reads history in explicit height and ordinal order with exact projection
  checks, and semantically validates the projected archive before returning
  bytes. Export does not alter the retained database snapshot.
- Focused GCC debug verification passes the archive codec/export test together
  with the existing SQLite ledger, history, and snapshot targets, 4/4. The
  archive suite freezes a 3,745-byte one-block fixture and digest; covers
  deterministic zero-block, empty-block, and populated-block round trips,
  truncation, trailing bytes, hostile counts and lengths, wrong
  magic/version/digest, history and snapshot corruption; and proves
  deterministic multi-block export across repeated calls and reopen. The Clang
  sanitizer configuration exposes a fifth bounded libFuzzer target with raw,
  structured, and valid archive seeds.
- `import_sqlite_archive` decodes and semantically replays an untrusted archive
  before path normalization or reservation, maps every archive rejection to
  `invalid_archive`, and never overwrites an existing target. After validation
  it writes the version-one schema, exact admitted history, materialized head,
  metadata, and exact head snapshot in one transaction, closes creation,
  reopens through full genesis and snapshot recovery, and requires a
  byte-identical fresh export before returning the live ledger.
- Import coverage proves deterministic height-zero and three-block round
  trips, including an empty block and duplicate admitted transactions; exact
  head and retained snapshot recovery; malformed and semantic-corruption
  refusal without creating a target; validation-before-path error precedence;
  and preservation of an existing target. The existing bounded archive fuzz
  target covers the only untrusted-byte parser used by import.
- `PROTOCOL_STACK_PRESET=gcc-debug tools/verify.sh` passes 18/18 CTest tests
  after the import implementation. After adding the height-zero import
  boundary, the rebuilt focused `storage-archive-v1` test passes 1/1.
- PR #18 merged portable archive import as `d840902`; exact-candidate Actions
  run 30209529359 and post-merge `main` run 30209691096 both passed GCC and
  Clang debug plus ASan/UBSan. The first three jobs passed 18/18 tests and
  Clang ASan/UBSan passed 23/23 including all five fuzz smoke targets.
- Head reads now return either one owned verified head or a typed storage
  error. Once commit processing reports an error, the adapter withholds the
  candidate, explicitly closes the connection, reopens through integrity,
  schema, full-genesis, snapshot-suffix, and materialized-state validation,
  then non-throwingly publishes only the recovered old or new durable head.
  A close or reopen failure leaves the instance terminal; stale cached state
  is unavailable and later block application fails closed.
- An internal test-only block hook observes transaction begin, persistence,
  pre-commit, post-commit/pre-publication, publication, and recovery-open
  boundaries. Coverage proves ordinary pre-commit rollback, an actual SQLite
  commit-hook rejection followed by old-head automatic recovery and continued
  commit, terminal recovery refusal without stale reads or later heights, and
  external reopen of that old durable database.
- A non-returning subprocess terminates after SQLite reports durable commit
  but before in-memory publication. The parent fully reopens the new durable
  head and successfully commits its next block. No recoverable callback or
  exception simulates the durable-commit/pre-publication interval.
- `PROTOCOL_STACK_PRESET=gcc-debug tools/verify.sh` passes 19/19 CTest tests
  with the focused recovery suite.
- PR #19 merged fail-closed ambiguous-commit recovery as `8787ca4`;
  exact-candidate Actions run 30210623514 passed GCC debug 19/19, GCC
  ASan/UBSan 19/19, Clang debug 19/19, and Clang ASan/UBSan 24/24 including
  all five fuzz smoke targets. Post-merge `main` run 30210783762 passed all
  four jobs on that rebased commit.
- A test-only wrapper around SQLite's registered default VFS delegates
  ordinary behavior and injects one armed journal failure at a block boundary.
  The focused suite reaches and verifies partial write, disk-full, write I/O,
  sync, truncate, and delete failures. Pre-commit failures retain the old head;
  ambiguous commit or cleanup failures expose only a fully validated old or
  new durable head, continue at the corresponding next height, and survive an
  external reopen.
- The dedicated VFS failure test and the existing recovery test pass 2/2 after
  a warning-clean GCC debug rebuild. The complete local suite passes 20/20.

## Exact next action

Continue issue #11:

> Expand subprocess termination across the remaining block-write phases, then
> run long fixed-seed commit/snapshot/restart/recovery sequences and close
> issue #11 when the full hosted matrix remains green.

## Open autonomous decisions

- Final acceptance of CometBFT as the replaceable M1 consensus/P2P adapter.

## Blockers

None.
