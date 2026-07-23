# Current state

Last updated: 2026-07-23

## Phase

M1 — Sovereign Devnet Alpha. The protocol-primitives decision is complete on
`research/2-protocol-primitives` and awaits its evidence-bearing PR.

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
- Strict signature acceptance requires libsodium-compatible canonical and
  small-order rejection. OpenSSL 3.0.20 alone accepted the adversarial
  identity-key vector and is not a valid consensus verifier.
- The repository still contains no ledger, networking, persistence, or
  production deployment implementation.

## Protocol-primitives evidence

- `tools/protocol-vectors/verify.sh` passes the fixed vector suite in C++20 and
  the independent Python model.
- The C++ harness passes with `-Wall -Wextra -Wpedantic -Werror`.
- The same C++ vectors pass with AddressSanitizer,
  UndefinedBehaviorSanitizer, and `_GLIBCXX_ASSERTIONS`.
- Vectors cover RFC 8032 interoperability, domain separation, transaction
  bytes and identifiers, Bech32m, state and transaction roots, mutation,
  malformed length, checksum, non-canonical scalar, small-order, supply-bound,
  conservation, and ordering rejection.
- Python bytecode compilation, shell syntax, TOML parsing, GitHub issue-form
  YAML parsing, internal Markdown links, and `git diff --check` pass.
- Clang is not installed in the current environment; issue #4 owns the
  reproducible compiler and sanitizer matrix.

## Exact next action

Open and rebase-merge the issue #2 PR, then begin GitHub issue #4:

> Bootstrap the reproducible C++20 and Python build, dependency, test, and CI
> toolchains, pinning the strict libsodium adapter and providing one
> clean-clone verification command.

## Open autonomous decisions

- Native unit name, precision, maximum supply, genesis allocation, and issuance
  schedule.
- Final acceptance of CometBFT as the replaceable M1 consensus/P2P adapter.
- Exact toolchain and production dependency pins under issue #4.

## Blockers

None.
