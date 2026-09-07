# ADR 0069: The version-eight node process and adapter, and the figure with no constant

- Status: Accepted
- Date: 2026-09-07
- Follows: [ADR 0060](0060-the-version-seven-node-process.md), [ADR 0061](0061-the-version-seven-abci-adapter.md), [ADR 0062](0062-the-version-seven-chain-fixture.md), [ADR 0068](0068-the-version-eight-application-layer.md)

## Context

[ADR 0068](0068-the-version-eight-application-layer.md) made a version-eight
chain **drivable**: seven operations, a staged block, a terminal latch, and
responses on version one's wire, exercised over a real Unix socket. It did not
make one **runnable**. `protocol-application` is version one's binary and
`protocol-application-v7` is version seven's, so nothing served `ApplicationV8`
on a socket; `adapter/cometbft` knew two ledger versions and neither was eight,
so nothing spoke to it. Step 6 of
[ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md)
is the pair, and it is the first slice in the whole migration whose failure mode
is not a unit test.

The three ADRs this follows already decided what a node process, an ABCI
adapter, and a chain fixture *are*. None of those decisions is
version-specific. What this ADR records is the small set of things that are —
and one class of figure the four preceding rebindings had not met.

## Decision

### The binary is version seven's with one figure, and the figure has a home

`protocol-application-v8` reads a genesis file, decodes it, opens or creates the
store, makes the application, binds a private Unix socket, and serves with a
`signalfd`. `--genesis-identity` prints the chain identity and the height-zero
application hash without touching a database. Opening is attempted before
creating. A `connection_failure` or a `protocol_failure` continues the loop.
Every one of those is [ADR 0060](0060-the-version-seven-node-process.md)'s and
none of them moved.

**The genesis width did.** A version-eight genesis is 142 octets rather than 110
because `dispute_authority_key` is a ninth field. The check remains an
*allocation bound* rather than a validity rule — the rule is stated once, in
`decode_genesis`, which re-encodes and compares — and the bound now reads
`v8::kGenesisPrefixBytes`, so the file states no width at all.

**Two error messages named the old literal, and neither is now a figure.** "not
the canonical 110 octets" became "not the canonical version-eight width". A
message is not compiled against anything, so a stale literal there survives
every test and lies to the first operator who hits it. Deleting the number
rather than updating it is what stops the next rebinding inheriting the same
problem.

### The Go client is version seven's, and the receipt version is named

`ClientV8` embeds `Client` and declares `FinalizeBlock`. `LocalV8` and `NewV8`
differ from version seven's by the codespace alone.

**That last point is the finding, not an omission.** Version eight changed what
a block *does* — a prologue, an issue step, an expiry step, two entry kinds, a
per-seat selection digest — and changed nothing about what a finalized block
*is*. It still carries a state root, the block identifier, and one
`{code, receipt}` pair per raw input. So the adapter needed no new shape, and
`FinalizedBlock`'s identifier stays a pointer for
[ADR 0061](0061-the-version-seven-abci-adapter.md)'s reason: absent must be
unmistakable, where a zero hash would be indexed as though it named something.

**The receipt version octet is named rather than written into the prefix
array.** Version seven's Go file writes `{'P','S','R','C', 0, 7}` as a literal,
which is the same shape that broke the C++ encoder the moment it was rebound
(ADR 0068). Go has no access to the kernel's headers, so it cannot derive the
figure; what it can do is give it one name one line above the array, which is
the difference between two copies of a number and one number used twice.

### A figure that moves with a version is one of three kinds, not two

[ADR 0067](0067-the-version-eight-owning-store.md) recorded the rule this
project reached after two slices: a moved figure is **either checked on the
happy path or it needs a boundary case, and there is no third kind**. This slice
found a third kind, and it is the dangerous one.

The four figures on the list behaved as the rule predicts. The genesis bound,
the app state, and the receipt version all break the happy path: left stale,
nothing starts, `init_chain` refuses, or no block decodes. The **result-code
count** does not. It moves from thirty-three to forty-five, and codes 33 through
44 appear in no fixture in this repository, so a stale 33 would narrow the
accepted range with every existing check passing — because each of them compares
the constant to itself and would pass at either value.

So the third kind is a figure that is **checked everywhere and pinned nowhere**.
The test for it is not a boundary input but an assertion against the literal,
plus one input on each side of it written by hand. `resultCodeCountV8` is
required to be 45, result 44 is required to be accepted, and result 45 is
required to be refused, with 44 and 45 written out rather than derived.

**And a fifth figure of that kind is not a constant at all.** The two genesis
keys must be two keys. A genesis carrying the verifier key in both fields
encodes, derives a chain identity, and executes every block; the fixture, the
node, the adapter, and the engine all agree about it. Nothing observes the
difference, so the fixture test requires the verifier key followed by the
dispute authority key to appear in the encoded genesis **exactly once** — which
also pins the adjacency the specification states, since a decoder reading the
two at swapped offsets re-encodes identically only when they are equal.

### The two live versions must refuse each other's blocks

Versions one and seven fail closed against each other because their
finalized-block *shapes* differ: version one has no identifier, so each decoder
runs off the end of the other's payload. Versions seven and eight share a shape.
On a well-formed block with a successful result, the **only** octet that
separates them is the receipt's version.

That makes `-protocol-version` a trap rather than a flag unless it is checked,
so it is: version seven's decoder must refuse a version-eight receipt and
version eight's must refuse a version seven's, on payloads identical in every
other octet. Without it, a client dialled at the wrong one of the two live
versions would misread a chain rather than fail to read it.

## Evidence

Five new registered entries and two new hosted integrations.

- **`version-eight-headless-process`** — the binary in identity mode and as a
  process: it prints the two figures an operator configures, creates a database
  on first run, reopens it on the second, answers the wire on a private
  0600 socket, refuses a premature commit with a status rather than a broken
  connection, and takes its socket with it on `SIGTERM`. Four genesis refusals,
  two of which are the moved width's pair: a 142-octet file carrying a
  version-seven schema version, refused by `decode_genesis`, and a 110-octet
  file, refused by the bound. **Deleting the bound admits the second; folding
  the validity rule into the bound admits the first.**
- **`version-eight-chain-fixture`** — the fixture's own contract, including the
  two-keys check, in milliseconds rather than after a build and two process
  lifecycles.
- **`CometBFT version-eight integration`** — two registrations and a confirmed
  transfer through a real v0.39.4 node, with a restart at height 2 so the third
  block's root depends on a state read back out of SQLite. Every figure is one
  implementation against the other: the model derives the identity and the
  roots, the binary derives the identity from the same file, and the node
  derives the roots by executing the octets.
- **`CometBFT four-validator version-eight integration`** — four independent
  replicas, three transactions through three different nodes, a full restart,
  and four durable C++ audits per stop.
- The Go suites: the two moved figures pinned to their literals, the
  cross-version refusal pair, the three codespaces required to be distinct, the
  three application states required to be distinct, and `ParseProtocolVersion`
  admitting 8 while rejecting 264, which truncates to it in a byte.

**Six mutation probes ran and every one failed before being restored**, which is
the check that a passing probe has proved something: `resultCodeCountV8` at 33
(caught only by the new literal assertion), `receiptVersionV8` at 7 (caught by
the assertion *and* independently by the cross-version pair), the fixture
passing the verifier key twice (caught by the adjacency check, not by the
inequality — the session still held two keys, and only the encoded genesis was
wrong), `GENESIS_BYTES` at 110, and the fixture's receipt prefix at version
seven's.

## Consequences

The repository now compiles and runs two whole stacks, top to bottom, which
[ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md)
permits only while the migration is in flight. Step 7 removes version seven's
half of every layer, and it is the last step.

Requirement 13's *economic* adversarial scenarios are unblocked but not started.
This chain sells no seat, so the issue and expiry steps evaluate nothing at any
height: what the integrations establish is that the version-eight code path runs
under a real engine, not that the audit it performs is sound. The soundness
claims stay where ADR 0027, ADR 0028, and ADR 0048 put them, awaiting the
independent review `first-goal.md` requirement 15 names.

`dispute_authority_key` remains one key standing in for the per-machine
attestation registry ADR 0048 defers. Nothing in this slice narrows that.

## Alternatives considered

**A second `Application` in the bridge rather than a third constructor.** Six of
the seven ABCI conversions name no ledger version, and duplicating them would
have been about a hundred and fifty lines whose only difference is which copy a
later fix reaches. Rejected for ADR 0061's reason, unchanged.

**Deriving the Go receipt version from a shared artifact.** There is no shared
artifact: the adapter has no kernel headers and generating one for a single
`uint8` would add a build step to keep one number in step. Naming it beside its
only use, and requiring the literal in a test, achieves the same thing at the
cost of one assertion.

**Restating the genesis width as 142 in the binary's error message.** Rejected.
A message is compiled against nothing, so the literal would be a figure with no
test — precisely the class this ADR is about. The rule is what the operator
needs; the number is one line above, in the comparison.

**Waiting for step 7 to add the integrations.** Rejected. Step 7 deletes version
seven's integrations, so adding version eight's afterwards would leave a commit
range in which no integration covers the live stack at all.
