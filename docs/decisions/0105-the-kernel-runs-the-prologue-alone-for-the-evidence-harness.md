# ADR 0105: The kernel runs the prologue alone for the evidence harness

- Status: Accepted
- Date: 2026-10-20
- Carries into C++: [ADR 0095](0095-the-fourth-scenario-suite-drives-the-chains-contract.md)'s
  `block.open_window`
- Settles: the open question in step 2 of
  [ADR 0104](0104-the-version-ten-kernel-is-staged-beside-version-nine.md)'s
  enumeration
- Specification: [`economy-transition-v10`](../specifications/economy-transition-v10.md)

## Context

`test-vectors/economy-transition-v10-execution.txt` has two fixtures. The chain
is a chain of blocks, which the kernel already runs. The population is 101
machines driven through version nine's evidence harness, because the launch
key's retirement needs 100 machines to meet one window, and no recorded chain of
blocks reaches that. Every in-scope seat is audited at every height, so a chain
that got there would be millions of challenge selections and thousands of
response blocks. The harness instead:

- executes transactions one at a time, at heights the run sets;
- opens each window by running the prologue alone, with the registry step;
- supplies a closed window's kind-19 records, the only state the skipped
  heights write that the prologue reads.

The model does this through `block.open_window`, which ADR 0095 added for
`economy-scenario-suite-v4`. The C++ kernel had no way to run its prologue
without the rest of a block. The handoff named the gap and left the shape to
this slice, because driving the kernel over the scenario suite needs the same
thing.

## Decision

**`protocol/v10/ledger.hpp` declares `open_window(Ledger&)`, the kernel's
counterpart of the model's `block.open_window`.** At a window-opening height and
stamp the caller has set, it:

1. runs the prologue with the accepted orders, registry step included;
2. checks invariant 7 and every conservation identity, as a block would;
3. restores the ledger and returns `nullopt` on any failure, as a block would.

It refuses a height that opens no window and a stamp outside `calendar-v1`'s
range. It runs no issue step, no transactions, no expiry step, no roots, and no
header. So its outcome carries the prologue's fields and nothing a block
commits to.

**No chain calls it, and no node may.** `execute_block` stays the only path a
chain runs. The declaration says so, and its comment names this record. The
application, the node, and every layer ADR 0104 migrates onto version ten call
`execute_block` and never `open_window`.

## Alternatives rejected

- **The test reaches into `src/v10/` for the file-private prologue.** No test
  includes an internal header today, and the scenario suite's driver would have
  to do it too. A second caller of an internal function is an interface either
  way, so it should be declared as one.
- **A flag on `execute_block` that skips everything but the prologue.** The
  chain's own path would then carry a harness mode. `BlockOrder` already
  carries three demonstration flags, and each one runs a rejected *reading* of
  the block. Skipping the issue and expiry steps is not a reading of the block.
  It is a different operation.
- **Running every height through `execute_block`.** The population's roots are
  the model's, and the model reached them through the harness. A chain of
  blocks would supply its uptime through challenges, so it would reach other
  roots. The plan's exact credited slots could only be approximated, because a
  slot is lost only where a challenge happens to fall.
- **Copying the prologue into the test.** The copy would drift silently, which
  is the risk ADR 0095 accepted exposure to avoid.

## Consequences

- The version-ten execution vectors' population section runs in C++ against
  the same supplied records the model used, and reaches the model's roots.
- **The prologue now has two callers in the kernel, as it has in the model.** A
  change to the prologue's contract has to keep both correct, and a changed
  signature fails loudly in both.
- The harness can drive the kernel over `economy-scenario-suite-v4`. But the
  suite's pinned roots are version nine's, and version nine's kernel does not
  gain this entry point, because ADR 0104 deletes it. So that evidence needs
  the suite rebound to version ten first.
- Version nine's kernel is unchanged.
