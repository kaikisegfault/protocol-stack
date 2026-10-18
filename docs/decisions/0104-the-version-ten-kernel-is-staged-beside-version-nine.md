# ADR 0104: The version-ten kernel is staged beside version nine's

- Status: Accepted
- Date: 2026-10-18
- Re-opens: [ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md),
  as its expiry requires the next kernel replacement to do
- Amends, for the length of this migration:
  [ADR 0046](0046-the-version-six-kernel-codec-replaces-version-four.md)
- Specification: [`economy-transition-v10`](../specifications/economy-transition-v10.md)

## Context

[ADR 0046](0046-the-version-six-kernel-codec-replaces-version-four.md) holds
that **the C++ side compiles exactly one economy contract**.
[ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md)
let the version-eight kernel arrive beside version seven's, under an
enumerated end, because twenty-three files above the kernel named version
seven. It expired when that deletion landed, and it said that "the next kernel
replacement re-opens this question rather than inheriting an answer". The
version-nine migration followed its enumeration through
[ADR 0092](0092-the-version-eight-deletion.md) without re-opening it in
writing. This record does.

`economy-transition-v10` is specified (ADR 0102), repaired once before anything
implemented it (ADR 0103), and executed by the Python model (M4.3b and M4.3c),
with 107 contract vectors and 141 execution vectors. The next action is its C++
kernel.

**The facts are ADR 0065's again.** On 2026-10-18, 26 C++ files outside
`src/v9/` and `include/protocol/v9/` name version nine: the snapshot, the
owning store, the application, the transport, the node process, the HUB test
verifier, two fuzz targets, and their tests. Fifteen Go files in the adapter do
too. Moving the kernel and every one of them in one commit would leave nothing
buildable until the last line of it, which is the shape of change ADR 0065
rejected.

## Decision

**The version-ten kernel is added beside version nine's, and version nine's
stack is deleted by the slice that migrates the last dependent layer.** The
enumeration is the contract this record makes:

1. **M4.3d**, the version-ten kernel codec. `include/protocol/v10/economy.hpp`
   and thirteen translation units under `src/v10/`, reproducing the contract
   vectors. Its CTest entry is `economy-transition-v10-cpp`.
2. **M4.3e**, the version-ten kernel execution: the ledger, kinds 10 and 23,
   the whole-transaction approval for every body-carried kind, the lifetime
   rule, the registry step, and a way to run the prologue alone at a window
   opening, which the population section of the execution vectors needs.
3. **The snapshot**, `snapshot_v10`, which must encode the three entries
   version ten adds or a version-ten ledger cannot be written down.
4. **The owning store**, `SQLiteLedgerV10`.
5. **The application**: `ApplicationV10`, the application contract that maps
   results 1 through 49 and reads a 182-octet genesis, and the transport.
6. **The node and the network**: `protocol-application-v10`, the Go adapter's
   version-ten client, and the version-ten devnet runs. The HUB test verifier
   moves to version ten here, and the network fixtures move onto it, because
   version ten changes what they build.
7. **The deletion.** Version nine's kernel, snapshot, store, application,
   transport, node process, and test verifier are removed with their tests,
   targets, CTest entries, and network runs. The repository compiles one
   economy contract again, and ADR 0046's rule applies unamended.

**A layer may take more than one slice**, as version nine's application and
transport did, and that changes nothing here. What is fixed is the end and its
content.

**Step 7 is not optional and is not "later".** From step 6 onward the handoff
carries it as the recorded next action. If the migration is abandoned part-way,
step 7 still runs, deleting `src/v10/` instead, because the outcome refused here
is a repository that compiles two economy contracts with no decided end.

**Step 7 must not take what version ten still needs.** ADR 0092 found five
things a deletion by filename would have broken. The same audit is owed here.
It has three named items already:

- the accepted version-nine vector files, which this codec's suite reads as
  carried sources;
- the version-nine Python model, which version ten's model imports throughout;
- `economy_v9_fuzz` and `storage_snapshot_v9_fuzz`, which need version-ten
  counterparts rather than removal, as `economy_v8_fuzz` did.

## Why the version-ten suite does not link version nine

ADR 0092 re-pinned nineteen cross-version checks that the version-nine suite
had executed against the live version-eight kernel. A pin against a live kernel
dies with the kernel.

So **no version-ten test includes `protocol/v9/`**. Every claim about what
version ten carries is compared with the accepted file that recorded it:

- the kind and entry tables, from version six's to version nine's files;
- the first forty-five result codes, from version six's and version eight's;
- version one's transfer bytes, from version six's file;
- version nine's chain identity, its nine roots, and its block header, from
  version nine's own file.

Step 7 then costs these checks nothing.

## The cost, stated rather than discovered

The build and the sanitizer matrix carry two economy kernels until step 7. On
the last full run, 38059175126, the four presets took 10:41 to 14:42 against a
twenty-minute timeout. At the peak of the version-eight and version-nine
coexistence, run 35946403883, the longest took 14:21. The version-ten codec is
about 4,000 lines, almost all of it version nine's copied, and one test target
of about 1,600.

**If a job approaches the timeout, the response is to finish the migration
rather than to trim a gate**, as ADR 0065 said.

**Nothing about the two kernels is consensus-visible.** They derive different
chain identities, roots, and economy trees under different labels. No genesis,
state, root, or receipt of one is readable as the other's. The version-ten
vectors record each of those non-collisions against all nine predecessors.

## Alternatives rejected

- **Move the kernel and every layer in one slice.** About 15,000 lines with no
  verifiable intermediate state. ADR 0065 rejected it for the same reason.
- **Build version ten on version nine's translation units**, as the Python
  model builds on version nine's modules. It works in Python because a carried
  function is version nine's own object, and version nine's model is kept for
  good. In C++ it would make version nine's kernel a permanent dependency of
  version ten's. Version nine's units also hard-code its labels, its result
  space, and its kind table. Step 7 could then never run, and ADR 0046's rule
  would never apply again.
- **Make the layers version-agnostic first.** ADR 0065 rejected this, and
  nothing has changed. It refactors accepted, verified storage and application
  code for no protocol reason, and it erases the version number from artifacts
  whose compatibility story is that they carry one.

## Consequences

- The C++ kernel arrives in two slices, as version nine's did in M3.18a and
  M3.18b. The contract vectors split cleanly: a codec reaches 99 of the 107,
  seven describe the Python package's own surface, and one is about what a
  ledger's genesis writes.
- `docs/project/current-state.md` carries the enumeration. A session that
  reaches step 6 finds step 7 recorded as its next action.
- **This record expires when step 7 lands.** After that, ADR 0046's rule
  applies unamended, and the next kernel replacement re-opens the question.
