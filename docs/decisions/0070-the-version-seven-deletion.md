# ADR 0070: The version-seven deletion, and what a deletion is not allowed to take with it

- Status: Accepted
- Date: 2026-09-09
- Completes: [ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md)
- Restores: [ADR 0046](0046-the-version-six-kernel-codec-replaces-version-four.md)

## Context

[ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md)
permitted two economy contracts to compile at once, and permitted it **only
while a stack migration was in flight and only because the removal was written
down before the first step landed.** Its enumeration ran to seven slices. Six
landed between 2026-09-04 and 2026-09-07 as PRs #247, #250, #253, #256, #259,
and #262. This is the seventh.

Step 7 is the slice that makes the coexistence legitimate retrospectively. ADR
0065 said outright that if the migration were abandoned part-way it would still
run, deleting `src/v8/` instead, "because the outcome this ADR refuses is a
repository that compiles two economy contracts with no decided end."

So the decision this ADR records is not *whether* to delete. That was decided
before version eight had a line of C++. What it records is **what a deletion of
this size is not allowed to take with it**, which turned out to be the whole
difficulty.

## Decision

Version seven's C++ kernel, storage, application, transport, and node process
are deleted, along with their tests, targets, and CTest entries; the Go adapter
loses its version-seven client, codespace, protocol version, and application
state; and `-protocol-version 7` moves from the accepted table to the rejected
list. The repository compiles exactly one economy contract again and ADR 0046's
rule applies unamended.

**Version seven's prose is history and stays.** ADR 0056 through ADR 0062 record
decisions that were correct when they were made, and ADR 0065 is the record of
why two contracts ever coexisted. Nothing in this slice rewrites them to pretend
version seven never existed. What was rewritten is a different category: a
comment in *live* code that pointed at a deleted target — six in `CMakeLists.txt`
that explained a version-eight target "for the reason version seven's does", and
one in `client_v8.go` — because a cross-reference to something that no longer
exists is not a historical record, it is a dangling pointer in prose.

## Four things the deletion kept, and each would have broken something

**1. The accepted version-seven vector files.** `economy-transition-v7.txt` and
`economy-transition-v7-execution.txt` are accepted contracts, and version eight's
predecessor constructions are pinned against the first.
`economy-transition-v8-cpp` still passes that file as an argument. This is the
point M3.13n paid for twice: **an inequality between two digests proves nothing
about either one unless both ends are pinned**, and a pin against the live
version-seven kernel would have died with `src/v7/` at exactly this slice.
`economy_v8_version_test.cpp` says so in a comment written before this slice
existed — "Both survive the deletion of `src/v7/`, which a comparison against the
live version-seven kernel would not" — and it was right.

**2. `simulation/economy_transition_v7/` and its six CTest entries.** Version
eight's Python model *subclasses* it: `ledger.py` overrides four things on
version seven's `Ledger` and `block.py` imports `derive_assignment` from
`economy_transition_v7.settlement`. Only the C++ was deleted.

**3. Version one.** ADR 0065 enumerates version seven's removal and says nothing
about version one's, and `wire_v1` is the frame format both live versions use.

**4. `receiptResultOffset`.** Declared in `wire_v7.go` and used by `wire_v8.go`,
because version eight keeps version seven's receipt layout unchanged. A deletion
that went by filename would have taken it.

## The economy fuzz target, which the enumeration got wrong

ADR 0065's step 7 lists `economy_v7_fuzz` for removal, and the handoff asserted
that every item in the deletion had "a version-eight counterpart already carrying
its evidence." **That was true of every item but this one.** No `economy_v8_fuzz`
was ever added, so deleting version seven's as enumerated would have removed the
repository's only economy-codec fuzz target and left the live contract with none.

That is a coverage drop rather than a migration, and ADR 0065 rules it out in its
own cost section: "Splitting a test target or moving one to a longer-running
preset is available and is preferable to dropping coverage."

`tests/fuzz/economy_v8_fuzz.cpp` therefore replaces it in the same slice. The
four inherited entry points are version seven's harness with the namespace
rebound. Two are new, and **the seat window record is the one that most needed
it**: its pad rule and its subset rule are refusals `seat_window_value` can never
produce a witness for, so arbitrary bytes are the only thing that reaches them.

The same pass found that both snapshot smoke entries had been left out of
`set_tests_properties` when they were added, which cost them the 60-second bound
every other fuzz entry takes. The list now covers every smoke entry.

## What a cross-version refusal test becomes when one version is gone

`TestVersionsSevenAndEightRefuseEachOther` checked both directions through the
two live decoders. Versions seven and eight share a finalized-block shape, so
the receipt's version octet is the only thing separating them on a well-formed
block, and each decoder was required to refuse the other's payload rather than
merely accept its own.

One direction no longer has an implementation and went with it. **The other is
the direction that matters**, because a bridge pointed at a stale version-seven
node must fail closed on the first block rather than on some later result code,
and it survives as `TestVersionEightRefusesAVersionSevenBlock`.

Its version-seven receipt is now a **literal** — `PSRC` with a version octet of
7, at the width version eight kept — rather than a call into a sibling decoder,
for the same reason the kernel's predecessor pins are recorded files. It carries
a positive control, so the refusal is about the version octet rather than about
the frame; a probe that weakens version eight's prefix check to ignore that octet
fails it by name.

## Consequences

**ADR 0065 expires.** Its final sentence made this slice its own expiry
condition, and the next kernel replacement re-opens the staging question rather
than inheriting an answer.

**The suite loses every version-seven C++ entry and keeps every version-eight
one.** The review is a grep: `v7`, `V7`, and `version seven` across `src/`,
`include/`, `tests/` outside `tests/simulation/`, and `adapter/` return only
history prose and pinned claims about version seven's *recorded* artifacts —
the app state string `ApplicationV8::init_chain` still refuses by name, the
receipt literal above, and the predecessor vector arguments.

**One docstring keeps a name that no longer resolves, deliberately.**
`tests/tools/test_registration_test.py` explains that "M3.13e added
`protocol_application_server_v7` and did not add it here", which is why the
build-flag registration check exists at all. The target is gone; the incident is
the reason for the test, and rewriting it would lose the lesson while keeping
the check.

**The build and sanitizer matrix stop carrying two economy kernels**, which is
the margin ADR 0065 spent for six slices and now returns.
