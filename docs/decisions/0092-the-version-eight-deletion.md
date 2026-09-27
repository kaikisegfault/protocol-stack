# ADR 0092: The version-eight deletion, and the evidence version nine had borrowed from it

- Status: Accepted
- Date: 2026-09-27
- Completes: the migration [ADR 0080](0080-the-version-nine-snapshot.md) through
  [ADR 0085](0085-the-version-nine-node-process-binds-the-platform-clock.md)
  each name as ending in this deletion
- Follows: [ADR 0070](0070-the-version-seven-deletion.md), whose method it applies
- Corrects: [ADR 0082](0082-the-version-two-application-frame.md)'s "`wire_v1`
  goes when `src/v8/` does"

## Context

Every version-nine layer now runs under a four-validator network
([ADR 0090](0090-the-version-nine-devnet.md)), including one replica on a wrong
clock ([ADR 0091](0091-the-skewed-replica-is-skewed-below-the-process.md)).
Version eight is no longer the executing contract of anything. ADR 0046's rule,
that the repository compiles one economy contract, has been suspended since the
version-nine kernel landed beside it.

ADR 0070 made one point about deletions of this size: **the decision is not
whether to delete, it is what the deletion is not allowed to take with it.**
The handoff that named this slice marked two traps in advance. The first was
`economy_v8_fuzz`, which had no version-nine counterpart. The second was ADR
0082's sentence about `wire_v1`. Checking each item for a counterpart, as that
handoff required, found three more, and two of them were larger than both.

## Decision

Version eight's C++ kernel, owning store, snapshot, application, transport,
and node process are deleted, with their tests, targets, and CTest entries. The
two version-eight integration runs leave `tools/verify.sh`. The Go adapter
loses its version-eight client, decoder, bridge constructor, codespace, protocol
version, and application state, and `-protocol-version 8` moves to the rejected
list beside 7. The repository compiles exactly one economy contract again, and
ADR 0046's rule applies unamended.

**Kept, each for a reason that would have broken something:**

- **The accepted vector files**, `economy-transition-v8.txt` and
  `economy-transition-v8-execution.txt`. Version nine's codec suite is pinned
  against both, and now more than before; see below.
- **`simulation/economy_transition_v8/`, its two verifiers, and its CTest
  entries.** Version nine's Python model imports it throughout, and it is now
  the only implementation of version eight in the repository.
- **`wire_v1`**, because version one still serves it and `wire_v2.hpp` takes its
  shared declarations from it. ADR 0082 carries the correction in place.
- **`tests/application/application_driver.py`**, the version-one frame driver.
  `application_driver_v2.py` is built on it.
- **Version eight's specification and ADRs**, which are history, and whose
  contract version nine's specification incorporates by reference.

## Five things the deletion would have taken, and what each became

**1. The economy-codec fuzz target.** `economy_v9_fuzz` replaces
`economy_v8_fuzz` in the same slice, as `economy_v8_fuzz` replaced version
seven's. Six entry points are version eight's harness rebound. Six are new:
the genesis, the widened pool, and the four settlement values version nine adds.
**The zero rule is the one that most needed it.** A monthly figure or claim of
zero is absence, so a decoder that opened one would give one fact two
encodings, and no encoder can produce that witness.

The same pass found **the omission ADR 0070 recorded, made again.**
`storage-snapshot-v9-fuzz-smoke` was never added to `set_tests_properties`, so
it ran without the 60-second bound and the `fuzz` label every other smoke entry
has. It has both now.

**2. `receiptResultOffset`.** Declared in `wire_v8.go` and used by
`wire_v9.go`, exactly as ADR 0070 found it declared in `wire_v7.go` and used by
`wire_v8.go`. A deletion by filename would have broken the build. It moves into
`wire_v9.go`. `resultCodeV8`, a test helper `wire_v9_test.go` borrowed, becomes
`resultCodeV9`. The literal boundary checks at results 44 and 45 move with it.

**3. The cross-version claims the version-nine codec suite executed against the
live version-eight kernel**, nineteen checks across three files. `economy_v9_kinds_test.cpp`,
`economy_v9_state_test.cpp`, and `economy_v9_version_test.cpp` each included
`protocol/v8/economy.hpp`. That is the pin M3.13n paid for twice and ADR 0070
named: a comparison against a live kernel dies with the kernel. Each claim is
now pinned to an accepted file. `economy_v9_carried.hpp` reconstructs version
eight's surface from four of them:

| Claim | Was checked against | Now checked against |
|---|---|---|
| Kind 22 is new | `v8::is_transaction_kind` | Version six's envelope table plus version eight's two kinds, **and version nine's table must equal that set plus 22 exactly** |
| The four entry kinds are new | `v8::is_entry_kind` | Version seven's entry table plus version eight's two, with the same exact-equality rule |
| Version eight's pool value is 16 octets | `v8::entry_value_bytes` | Version seven's table, under the pool's recorded name |
| Version eight's header is 146 octets | `v8::kBlockHeaderBytes` | Version eight's execution file: the figure, and a recorded header of that length |
| Version eight's genesis prefix is 142 octets | `v8::kGenesisPrefixBytes` | Version eight's recorded genesis, which carries no account, and the execution file's figure |
| The thirteen carried genesis entries are version eight's | Version eight's encoders | Version seven's widths, the empty values a genesis holds, and the recovery pool's recorded key |
| No code added or renamed | `v8::kResultCodeCount`, `v8::result_code_name` | Version six's thirty-three names, version eight's twelve, and version eight's recorded count, required contiguous |
| The mint message is version six's construction | `v8::mint_message` over this suite's fixture | **Version six's recorded message**, rebuilt over the fields that file recorded it on |

Two are stronger than what they replace. The exact-equality rule is new: a kind
either table has and the other lacks now fails by number. And the mint message
was compared with a sibling kernel that was itself a port. It is now compared
with the bytes the accepted file recorded.

The old code comment said version eight's file "does not record the count".
**That was wrong.** `result.code_count=45` is recorded there, and it is now the
pin.

**Six claims are behaviour only an implementation of version eight can show:**
that a version-eight decoder refuses kind 22 and each of the five
version-nine entries. No version-eight C++ is left to ask. The version-eight
Python model is kept, and `tools/economy-transition-v9-vectors/verify.py`
already ran all six against it. The coverage guard names that verifier as
where they are owed, so each `*version_eight_refuses*` vector is still claimed by
something. The direction that matters to a version-nine chain survives in C++:
version nine refuses version eight's pool value by width. The value is written
as a literal of the width version seven's table fixes, with a positive control
at version nine's width. That is ADR 0070's treatment of the version-seven
receipt, applied again, and the Go wire test's version-eight receipt becomes a
literal the same way.

Fifteen mutation probes each corrupted one recorded figure a new pin reads. All
fifteen failed the suite by name.

**4. The inherited snapshot refusals.** `snapshot_v9_entry_refusals.cpp` said
outright that it sampled the inherited value rules because
`storage_snapshot_v8_tests` "holds the full set". Deleting that suite would
have left twenty-three rules over the seat, the channels, the identity, the
escrow, the assignment record, the two uptime kinds, the referral balance, and
the custody entry with **no snapshot-level check at all.** None of them was
version eight's to lose. They are version nine's rules, running in version
nine's decoder.

`snapshot_v9_inherited_refusals.cpp` carries the sweep across, with its
reasoning. Two fixtures reach every inherited kind a version-nine chain writes:
the `settled` chain, and that chain rebuilt to its first audit height. That
height holds an open challenge beside a window record, which is what version
eight's `deadline` scenario was for.

**Two inherited kinds appear in no version-nine chain**, because the trace buys
every seat without a referrer and issues nothing directly: the referral balance
and the typed custody entry. Their cases insert an entry, reseal, and require
the refusal. Each is paired with a control that inserts the same entry with a
lawful value and must fail at gate 3 instead. That control is what makes the
refusal the decoder rule's. Without it, an inserted entry refused for being out
of place would pass a test about its value.

Seven mutants each removed or weakened one decoder rule, and all seven fail the
suite. Six fail it by name. The seventh drops the channel index bound, and the
eleventh channel then trips the standard library's bounds assertion on the
ten-element array that bound guards, which is the defect the bound exists to
prevent.

**5. `wire_v1`**, which ADR 0082 said would go. It stays, as recorded above.

**One item had a counterpart and was not ported.**
`driven_application_v8_test.py` ran a whole-block refusal and seven other
scenarios against a live process. Each has a version-nine counterpart:

- **The four-validator run's driven replica:** a block from the future, a stamp
  running backwards, the terminal latch, and a durable reopen.
- **The headless process test:** a foreign genesis stamp and a staged block.
- **The transport suite over a real socket:** commit before init, a wrong
  height, and frame bounds refused before dispatch.

## A finding the port surfaced, recorded rather than fixed here

The referral control's first draft inserted a **fully minted** balance for a
registered identity that referred no seat, and **the restore accepted it.** Gate
3's contract is that a restore hands back a state some sequence of blocks could
have produced, or nothing. No block writes that entry: a referral balance
comes into existence only when an assignment accrues to a referrer.

It is narrower than it first looks, and it is not new. The referral check in
`conservation_failures` sums what balances *owe*, so an inserted balance
that owes anything is refused. An orphan that owes nothing adds nothing to the
sum, and it passes. **No unit can be minted from it.** A node restored from such
a snapshot holds a root no network produced, and it would disagree with its
peers at the next block. The invariant is version eight's, ported unchanged, so
version eight's restore had the same gap.

Closing it means requiring each referral balance to name an identity some seat
refers to. **The place for that is the snapshot's `complete` step**, which
already refuses an uptime entry naming a seat the chain never sold. That keeps
the rule out of `conservation_failures`, which execution reads too, so no
block's acceptance can move. It is a storage change with its own evidence, and
not something to fold into a deletion. The control here therefore owes ten
units, and its comment points at this record.

## Consequences

**ADR 0065's staging is fully spent**, as ADR 0070 left it. The next kernel
replacement opens the staging question again rather than inheriting an answer.

**The suite loses every version-eight C++ entry and keeps every version-eight
Python one.** CTest counts fall from 178 to 168 under the GCC presets and from
188 to 177 under the Clang sanitizer preset. That is ten entries, plus version
eight's snapshot fuzz smoke, while `economy-transition-v8-fuzz-smoke` becomes
`economy-transition-v9-fuzz-smoke`. The codec entry
`economy-transition-v9-cpp` takes two more accepted files as arguments.

**The review is a grep.** Across live sources and tests, references to deleted
files, targets, namespaces, and Go identifiers return exactly two pointers,
each citing this record: `wire_v9.go` on where `receiptResultOffset` came from,
and the snapshot suite on where its sweep came from. What remains is history
prose, the retained Python model's own names, and claims about version eight's
*recorded* artifacts.

**The build and sanitizer matrix stop carrying two economy kernels.**
