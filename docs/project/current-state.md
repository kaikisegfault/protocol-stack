# Current state

Last updated: 2026-07-23

## Phase

M1 — Sovereign Devnet Alpha. The deterministic in-memory ledger kernel is
merged and verified. Atomic persistence, replay, snapshots, and recovery are
the active roadmap slice.

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
- Restore tests prove genesis and nonzero-height reconstruction, ordinary and
  restored block-output equivalence, next-block continuation, copy/move
  ownership, live zero-balance accounts with nonzero nonce, intrinsic invariant
  rejection, every parameter mismatch, stale roots, and error precedence.
  GCC debug, GCC ASan+UBSan, and Clang debug pass 14/14 CTest tests; Clang
  ASan+UBSan passes 17/17 including all three fuzz targets.

## Exact next action

Continue issue #11:

> Implement the owning SQLite adapter's database-creation and height-zero reopen
> boundary: accept caller-trusted canonical genesis, create a new path
> exclusively, install the exact version-one schema and durability settings,
> commit genesis state, and reject an existing database unless integrity,
> schema, genesis, materialized state, and root validation all agree.

## Open autonomous decisions

- Final acceptance of CometBFT as the replaceable M1 consensus/P2P adapter.

## Blockers

None.

The remote `protocol/6-ledger-transition-spec` branch is not a project blocker,
but it contains the unique pre-existing `protocol-stack.code-workspace` commit
and must not be deleted until that file is deliberately retained or discarded.
