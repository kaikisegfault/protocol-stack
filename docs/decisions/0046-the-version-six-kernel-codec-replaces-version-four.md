# ADR 0046: The version-six kernel codec replaces version four's

- Status: Accepted
- Date: 2026-08-17

## Context

[`economy-transition-v6`](../specifications/economy-transition-v6.md) is
requirement 10's target. It has a specification, an ADR, a sibling model, 462
encoding vectors, an execution model, 512 execution vectors, and two verifiers.
It had no C++ at all.

What the kernel did hold was `src/v4/`, a codec for
[`economy-transition-v4`](../specifications/economy-transition-v4.md) delivered
by M3.9a on 2026-08-15 — **a contract that the very next slice proved has no
conforming implementation**, because version four's kind 11 opens its rejection
conditions with "an unregistered `hub_identity_hash` is `NOT_HUB_VERIFIED`" over
an identity the transaction never carries. Versions five and six both exist
because of that defect.

So the repository compiled exactly one economy contract, and it was the one
contract known to be unimplementable.

## Decision

### Replace `src/v4/` rather than adding `src/v6/` beside it

`include/protocol/v4/economy.hpp`, the six sources under `src/v4/`, and
`tests/kernel/economy_v4_test.cpp` are removed. `include/protocol/v6/economy.hpp`,
nine sources under `src/v6/`, and five test translation units take their place,
and the CTest entry `economy-transition-v4-cpp` becomes
`economy-transition-v6-cpp`.

**The checks are split by subject the way the Python verifier for the same file
is** — `economy_v6_encoding_test.cpp`, `_identity_test.cpp`, `_state_test.cpp`,
and `_settlement_test.cpp` over a shared `economy_v6_fixture.hpp`, mirroring
`encoding_checks.py`, `registry_checks.py`, and `state_checks.py`. Written as
one file it reached 1,430 lines, more than twice the largest test in the
repository; splitting a sequence of independent verification functions by
subject is cohesion rather than the fragmentation the engineering rules warn
against.

**The Python side keeps every version and the C++ side keeps one, and the
asymmetry is not an inconsistency.** A Python model plus its vector file is *the
record of what the hosted matrix verified* on a particular day — the artifact
ADR 0029 and ADR 0038 exist to preserve, and `economy-transition-v4.txt`'s 441
vectors still verify at their recorded count under
`tools/economy-transition-v4-vectors/`. The C++ codec is not a record of
anything; it is one implementation of the byte surface a running chain will use.
Keeping two would double the build, double the sanitizer matrix's work, and
place nothing between them but a version label.

**Rejected: keep both.** It preserves a second implementation of a superseded
contract at a real cost in build time, and it leaves the repository's only
compiled economy contract list containing one entry that cannot be implemented
and one that can. If version four's C++ is ever wanted again it is one `git
show` away, which is what version control is for.

**Rejected: keep version four and add version six, retiring version four
later.** "Later" is the failure mode this ADR exists to end. Version four's codec
was already superseded on the day it merged.

### The signer derivation is the version-one kernel's, not a copy of it

`signer_id` is `H(D("protocol-stack:v1:account") || 0x01 || pk)` — the accepted
version-one account derivation with its subject narrowed from an account to a
signer, which is what a public-key hash is. `src/v1/admission.cpp` already held
it in a file-private helper.

It is now declared in `src/v1/account.hpp` and defined once, and both the
version-one admission path and the version-six codec call it. **A second
implementation of one derivation is a second place for it to drift, and the
drift would be silent, because both copies would agree with themselves.** The
test checks the shared implementation against
`test-vectors/protocol-primitives-v1.txt`'s recorded `account_id`, which is a
third source rather than a second restatement.

### What the codec deliberately does not do

**It is a codec plus the pure derivations, and it performs no state
transition.** Every entry point is a function of its arguments. It holds the
envelope and the fourteen bodies, the six HUB messages, the escrow and signer
derivations, the posture predicates, the state key space and every value
encoding, the economy tree, the version-six state root, genesis, chain identity,
the receipt, the bounded mint walk, and the verified-user arithmetic.

**Of ADR 0045's four derived rules it can reach exactly one, and it reaches it.**
`NOTHING_TO_MINT` as the empty walk range is `walk_range`, a pure function of a
mark and the last assigned window, and the test pins all three of its cases
including the one the literal reading gets wrong: a mark *above* the last
assigned window walks nothing rather than walking backwards.

The other three need a ledger this does not have and are the next slice:
`DEBIT_OVERFLOW`'s position inside the shared envelope order, the unrequested
confirmation field refused at execution with `UNAUTHORIZED`, and the cycle
assignment written as a block's prologue.

**One of the three is pinned from the admitting side even so, and finding that
it was not is the reason this paragraph exists.** A mutation probe that made the
codec refuse a mint carrying a nonzero confirmation field — the rule version
six's text literally states, at admission, under a code the result space does not
contain — **passed**. Nothing in the test or in either accepted vector file
noticed an implementation stricter than the contract can be. The test now
requires such a mint to be *admitted*, so ADR 0045's second rule is fixed from
the only side a codec can fix it from.

## Consequences

**Requirement 11 now covers a contract nothing supersedes.** The C++ and the
independent Python model reproduce one fixed file,
`test-vectors/economy-transition-v6.txt`, and the test derives no second set of
expected values. Two checks reach outside it, and both reach a *third* source
rather than a second opinion of the same file: the kind-1 identity and the signer
derivation against `test-vectors/protocol-primitives-v1.txt`, and the two
cycle-assignment records against `test-vectors/economy-transition-v3.txt`,
because version six's settlement is version three's imported rather than
reimplemented.

**The populated economy root is what makes this more than a width check.** The
44-entry fixture covers every one of the fourteen assigned entry kinds, so one
recorded root constrains every value encoding at once. Two probes that swapped
adjacent same-width fields — `signer_count` with `exempt_slot_mask` in the escrow
record, and `next_escrow_index` with `escrow_count` in the identity record —
both failed there and nowhere else. A table of widths would have accepted both.

**Requirement 10 is partly satisfied and the remainder is named.** The byte and
derivation surface executes; the transitions do not. No chain can run on this.

**Nineteen mutation probes establish that the checks fail closed**, and one of
them found the gap recorded above rather than confirming a check. Among the
others: a changed escrow label, the version-one account octet changed in the one
place it now lives, the state-root schema version — a *number*, which the M3.10b
handoff warned would not appear in a search for `v4` — the RFC 9162 split
replaced by a halving, the bitmap packed least-significant-bit first, a retired
kind given a width, and genesis admitting an account.

**The local harness of M3.9a was reused and its one limit is now known.** A
scratch `sodium.h` backed by the system OpenSSL supplies the two entry points
the kernel uses, so the whole codec compiles and runs in about a second instead
of a ten-minute hosted iteration. It is not committed and is not part of the
build. **It does not reproduce libsodium's rejection of small-order public
keys**, so `tests/kernel/primitives_test.cpp` fails under it at exactly that
assertion and passes under the hosted matrix. That is a property of the harness
and not of the kernel: `src/v1/crypto.cpp` is byte-identical to `origin/main`.

**Nothing accepted was edited.** `economy-transition-v6`'s specification gains a
status line and an evidence pointer and no rule; `economy-transition-v5`'s gains
a corrected sentence about where the kernel's codec now lives, which was a status
statement rather than a rule. Every predecessor vector file verifies at its
recorded count.
