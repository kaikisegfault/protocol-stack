# ADR 0065: A kernel replacement may be staged across a stack migration

- Status: Accepted
- Date: 2026-09-03
- Amends: [ADR 0046](0046-the-version-six-kernel-codec-replaces-version-four.md)

## Context

[ADR 0046](0046-the-version-six-kernel-codec-replaces-version-four.md) fixed a
rule the repository has followed twice: **the C++ side compiles exactly one
economy contract.** `src/v6/` replaced `src/v4/` rather than joining it, and
`src/v7/` replaced `src/v6/` the same way. Its reasoning was that a superseded
codec kept "for now" is a codec kept forever — *"'Later' is the failure mode this
ADR exists to end"* — and that keeping two "would double the build, double the
sanitizer matrix's work, and place nothing between them but a version label."

`economy-transition-v8` is now specified, modelled, executed in Python, and
recorded in 183 contract vectors and 434 execution vectors. The recorded next
action is its C++20 kernel, and the recorded plan after it is "the snapshot, the
store, the application, the transport, the node process, and the adapter, each
its own slice."

**That plan does not survive contact with the dependency graph, and this ADR
exists because it did not.** When ADR 0046 was written, nothing above the kernel
named the kernel's version: the storage, application, and transport layers were
version one's and were indifferent to which economy contract was compiled. Since
M3.13a through M3.13g they are not. **Twenty-three files outside `src/v7/` and
`include/protocol/v7/` name `protocol::v7` today** — the snapshot, the owning
store, the application, the transport dispatcher and responses, the node binary,
two fuzz targets, and five test fixtures.

So a literal reading of ADR 0046 makes the version-eight kernel move atomic
across the whole stack: roughly 7,900 lines of kernel and kernel tests plus
roughly 6,400 lines of storage, application, and their tests, in one commit, with
nothing in the repository buildable until the last line of it. That is not a
slice. It is the opposite of the rule that a slice be the smallest unblocked
outcome that can be verified on its own.

## Decision

**A kernel replacement may be staged, and only under a stated end.** `src/v8/`
and `include/protocol/v8/` are added beside version seven's, and `src/v7/` and
`include/protocol/v7/` are deleted by the slice that migrates the last dependent
layer. Coexistence is permitted only while a stack migration is in flight, and
only when the removal is enumerated before the first slice of it lands.

The enumeration is this, and it is the contract this ADR is making:

1. **M3.13n** — the version-eight kernel codec, beside version seven's.
2. **M3.13o** — the version-eight kernel execution: the ledger, the four ordered
   block steps, the two transitions, and the schedule derivation.
3. **M3.13p** — `snapshot_v8`, which must encode the two entry kinds version
   eight adds or a version-eight ledger cannot be written down.
4. **M3.13q** — `SQLiteLedgerV8`.
5. **M3.13r** — `ApplicationV8` and the version-eight transport responses.
6. **M3.13s** — `protocol-application-v8` and the Go adapter's version-eight
   client.
7. **M3.13t** — **the deletion.** `src/v7/`, `include/protocol/v7/`, the
   version-seven storage, application, transport, and node sources, their tests,
   and their CTest entries are removed, and the repository compiles exactly one
   economy contract again.

**Step 7 is not optional and is not "later".** It is a numbered slice with its
content already written down, and `docs/project/current-state.md` carries it as
the recorded next action from step 6 onward. If the migration is abandoned
part-way, step 7 still runs — deleting `src/v8/` instead — because the outcome
this ADR refuses is a repository that compiles two economy contracts with no
decided end.

## Why this is not the thing ADR 0046 rejected

ADR 0046 rejected two options and this is neither.

**It rejected "keep both,"** on the ground that it "preserves a second
implementation of a superseded contract at a real cost in build time." Version
seven is not a superseded contract during the migration; it is **the contract six
live layers are written against**, and it is what makes the repository buildable
and verifiable at every intermediate step. What sits between the two is not "a
version label" but a six-slice migration with each step's evidence gate intact.

**It rejected "keep version four and add version six, retiring version four
later,"** on the ground that "later" never comes. The difference is the
enumeration above: the retirement is a numbered slice with stated content, not an
intention. ADR 0046's own sentence — *"Version four's codec was already
superseded on the day it merged"* — is the test, and version seven's is not: it
is the only kernel any running node in this repository can use until step 6.

## The cost, stated rather than discovered

**The build and the sanitizer matrix carry two economy kernels for six slices.**
On the last measured run the ctest suite was 158 entries at 148 seconds under
`clang-debug` and 166 at 295 seconds under `clang-sanitizers`, inside jobs of
about nine to eleven minutes against a twenty-minute timeout. A second economy
kernel and its tests are the largest single addition the matrix has taken, and
the margin M3.7a reclaimed is what absorbs it.

**If a job approaches the timeout, the response is to finish the migration
rather than to trim a gate.** Step 7 removes the duplication permanently, and
every step before it is a step closer to that. Splitting a test target or moving
one to a longer-running preset is available and is preferable to dropping
coverage, but neither should be needed.

**Nothing about the two kernels is consensus-visible.** They compile different
chain identities under different labels, and no state, root, receipt, or genesis
of one is readable as the other's — which is what
`economy-transition-v8.md`'s compatibility boundary already fixes and what the
version-eight vectors already record against all seven predecessors.

## Alternatives rejected

**Move the kernel and all six layers in one slice.** About 14,000 lines with no
verifiable intermediate state, and every evidence gate deferred to the end. It is
the shape of change this project's work loop exists to prevent.

**Make the layers version-agnostic first, then replace the kernel once.** It
means refactoring accepted, verified storage and application code for no protocol
reason, and templating six layers over an economy contract is a larger and
riskier change than the migration it would serve. It also erases the version
number from artifacts whose whole compatibility story is that they carry one.

**Leave the kernel at version seven and drive version eight from Python only.**
Requirement 13's *economic* four-node scenarios are blocked on exactly this: the
version-seven ABCI path hands `execute_block` a null uptime schedule, so a chain
driven through it writes no cycle assignment and accrues nothing to any seat.
Version eight is what removes the parameter, so the stack cannot run an economic
scenario until the stack is version eight.

## Consequences

The version-eight kernel becomes two slices rather than one, which is how
versions four and six were done and which the atomic reading had taken away:
`economy-transition-v8.txt`'s 183 contract vectors split cleanly at 121
reproducible by a codec and 62 needing a ledger.

**`docs/project/current-state.md` carries the enumeration.** A session that
reaches step 6 finds step 7 recorded as its next action, which is the mechanism
that makes the end real rather than intended.

**This ADR expires when step 7 lands.** After it, ADR 0046's rule applies
unamended: the repository compiles exactly one economy contract, and the next
kernel replacement re-opens this question rather than inheriting an answer.
