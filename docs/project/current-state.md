# Current state

Last updated: 2026-07-23

## Phase

M1 — Sovereign Devnet Alpha. Protocol primitives are accepted and the
reproducible build/toolchain slice is verified.

## Verified facts

- Repository: `kaikisegfault/protocol-stack`.
- F0 merged to `main` through PR #3 on 2026-07-23.
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
  an ignored virtual environment, builds the pinned libsodium source, and runs
  C++ and standard-library-only Python checks through CTest.
- The repository still contains no ledger, networking, persistence, or
  production deployment implementation.

## Protocol-primitives evidence

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

## Exact next action

Land the verified GitHub issue #4 build/toolchain slice, then begin issue #6:

> Specify deterministic M1 ledger state transitions and devnet monetary
> constants, including exact failure atomicity and normative cross-language
> vectors.

## Open autonomous decisions

- Devnet native unit name, precision, supply limit, genesis allocation, and fee
  constants under issue #6.
- Final acceptance of CometBFT as the replaceable M1 consensus/P2P adapter.

## Blockers

None.
