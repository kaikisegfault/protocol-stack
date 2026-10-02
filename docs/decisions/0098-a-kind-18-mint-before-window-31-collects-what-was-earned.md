# ADR 0098: A kind-18 mint before window 31 collects what was earned

- Status: Accepted
- Date: 2026-10-03
- Repairs: the version-nine C++ kernel, `verified_user_collection` in
  `src/v9/economy_settlement.cpp`
- Rule repaired to: [`economy-transition-v6`](../specifications/economy-transition-v6.md)
  §Kind 18, carried unchanged by versions seven through nine
- Found by: M4.2c, the first network to mint

## Context

Version six states the kind-18 collection over integers:

```text
last_completed_window = window_of_height(h) - 1
collectable_end       = min(last_completed_window, enrollment_last_window)
window_start          = max(minted_through_window, collectable_end - 30)
count                 = collectable_end - window_start     when positive, else 0
```

Before window 31, `collectable_end - 30` is negative, so the mark wins the
maximum. **The C++ kernel computed it in unsigned arithmetic.** The subtraction
wrapped to a value near `2^64`, which then won the maximum, and `count` came out
as exactly 30, modulo `2^64`. So every kind-18 mint before window 31 collected
thirty daily permissions, 5,130,000,000 atomic, whatever the identity had
earned. On a chain at the commit target that is every verified-user mint in
the network's first month. The independent Python model computes over Python
integers and was right.

**M4.2c found it.** Four replicas seeded at height 86,400 executed Alice's
kind-18 mint at window 3, and every replica's root differed from the model's.
Driving the built application directly over the same seeded store, with no
consensus engine, isolated it in one block: 5,130,000,000 atomic issued in C++
and 342,000,000 in the model, two windows.

**No recorded vector reaches it.** Version six's trace records a kind-18 mint
in window 0, before any window completes, which the kernel returns early from.
It also records a forfeiting collection after the cap. No recorded kind-18 mint
at any version executes in windows 1 to 30. The four-validator runs before
M4.2c never reached a window past 0, so none could mint.

## Decision

**Repair the kernel to the accepted rule, inside version nine.** The capped
start is `collectable_end - 30` when that is positive and zero otherwise. Zero
can never win the maximum against a mark, which is never negative, so this is
the specification's maximum in unsigned arithmetic.

**This is a conformance repair and not a new version**, for ADR 0094's reasons.
No field, code, order, or rule changes. The rule is the one version six already
states, and the model already executes it. No persistent network exists to
migrate. The devnet runs are CI fixtures, and before M4.2c none minted.

**The other subtractions in the version-nine kernel's window arithmetic were
checked and are guarded:**

- `last_assigned_window` and the prologue compare against the assignment lag
  first;
- a referral balance's first mark refuses a zero window (ADR 0094);
- `last_completed` is reached only after an executing window of zero has
  returned.

The cap additions, `mark + 30`, cannot leave `u64` for any window a chain can
reach.

## Evidence

- `tests/kernel/economy_v9_verified_user_collection.cpp`, run by
  `economy-transition-v9-execution-cpp`, checks eleven collections against
  figures the Python model produced, written out as literals: windows 0 to 3,
  one below the cap, exactly the cap, one window forfeited, a later enrollment, a
  mark inside the cap, the period's last window, and after it. Built against the
  unrepaired kernel it fails on "one window completed".
- With the repaired application driven directly over M4.2c's seeded store, the
  launch block, twenty-five empty blocks, both mints, and all three refusals
  each land on the model's root. Kind 18 issues 342,000,000 atomic and kind 4
  issues 57,430,000,000.
- `cometbft_seeded_mints_v9_test.py` asks the same of four replicas under
  CometBFT.

## Consequences

**A verified user's first month collects what it earned**, as version six
specified. Nothing else about the channel changes: the thirty-window cap still
forfeits from window 31, and the mark still advances to `collectable_end`.

**This is the third defect in this lineage that no recorded vector could see**,
after ADR 0093's orphan balance and ADR 0094's referral mark. It is the first
found by a network rather than by a model. Every earlier network run executed
blocks that a seat's first windows never reach. A network running past the
assignment lag is therefore evidence the vector files cannot replace, and
M4.2c's run stays in `tools/verify.sh` to keep it.

**Independent review.** Unsigned window arithmetic is a recurring trap in this
kernel: ADR 0094 refused a zero window rather than wrapping it, and this
repairs a wrap. Review of the kernel's window arithmetic is added to the
independent review already owed.
