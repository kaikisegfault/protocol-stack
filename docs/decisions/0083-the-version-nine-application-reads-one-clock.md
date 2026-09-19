# ADR 0083: The version-nine application reads a clock in one operation

- Status: Accepted
- Date: 2026-09-19
- Bounds: [ADR 0079](0079-the-version-nine-application-contract.md),
  [ADR 0058](0058-the-version-seven-application-layer.md)
- Follows: [ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md),
  [ADR 0081](0081-the-version-nine-owning-store.md),
  [ADR 0082](0082-the-version-two-application-frame.md)
- Relates to: `include/protocol/application/application_v9.hpp`,
  `src/application/application_v9.cpp`, `src/application/application_block_v9.cpp`

## Context

[ADR 0079](0079-the-version-nine-application-contract.md) settled what this
layer must do; this is the layer. The seven operations, the ownership and
staging rules, and the terminal-refusal rule are version eight's and carry over
unchanged.

**What version nine adds is a clock, and it is the first non-deterministic input
this repository has ever admitted into a consensus-adjacent path.** Nearly every
decision below is about keeping it in one place and being able to prove that it
is there.

## Decision

### 1. The clock is bound at construction, has no default, and is read once

`make_application_v9` takes a `ClockSourceV9` and **refuses an empty one**. A
defaulted system clock would make "this deployment cannot read a clock"
unrepresentable, and the contract requires such a deployment to fail to start
rather than vote on an assumed value — an assumed clock makes C5 pass on every
proposal, silently.

`process_proposal` reads it exactly once. Reading twice would let two conditions
of one evaluation disagree about the time.

### 2. `finalize_block` cannot apply C5, and the enforcement is a signature

`finalize_block` calls `v9::replay_timestamp`, which **takes no clock argument**.
There is no value a caller could pass and no branch a maintainer could add
without changing a signature. A machine that re-applied the tolerance on the
decided-block path would reject the chain's own past one tolerance-width after
producing it, and every correct replica would do so at a different moment.

The kernel had already made this structural by offering two entry points that
differ in exactly this respect. This layer's contribution is to call the right
one and to prove, by counting, that it reaches no other.

### 3. The decision space is `calendar-v1`'s numbering, so the mapping is a cast

`decision_of` is `static_cast`, not a translation table, because decisions `0`
through `5` *are* the kernel's condition values. `6` and `7` are this contract's
own and are numbered after the last kernel condition, and
`static_assert(kTimestampConditionCount == 6)` makes a sixth kernel condition a
build failure rather than a silent alias of `RESOURCE_BOUND`.

**The ordered conditions run before the resource bounds.** The vote is identical
under either order, so this decides only what is *reported* — see the second
finding.

### 4. There is no status for either C5 condition, and the absence is asserted

`TimestampFailureV9` has exactly two values, `7` and `8`, for C1 and C2 on a
decided block. A status space containing a tolerance value would be a status
space with a tolerance reachable on the replay path, which is the defect the
separation exists to prevent, so the suite asserts the absence rather than a
presence.

### 5. `init_chain` compares four values and stores none of them

Version nine adds the genesis timestamp to the three version one compared. **It
is read from the durable head rather than kept as a member**: `init_chain` is
only reachable while the durable height is zero, and at height zero the head's
own stamp *is* the genesis stamp. So the comparison reads the head it already
read, and there is no second copy to drift.

[ADR 0080](0080-the-version-nine-snapshot.md) reached the same answer for the
snapshot. Here the reason is sharper: the one operation that needs the value is
the one operation that can only run where the value is still in the head.

### 6. `prepare_proposal` does not gain a timestamp, and the omission is a rule

Under CometBFT the block time is the engine's, produced by BFT time from vote
timestamps, and `economy-transition-v9` requires the proposer's algorithm for
choosing a value to stay unconstrained. An application that selected the stamp
would constrain exactly that and would foreclose the deployment in which BFT
time supplies it.

## The findings

### `NOT_EXECUTABLE` is not reachable from a proposal's contents

[`consensus-application-v2`](../specifications/consensus-application-v2.md)'s
required evidence asks for a vector for **every** decision `0` through `7`, each
produced on its own. Seven of the eight are straightforward. The eighth is not
reachable, and establishing that took a probe rather than a reading.

Decision `7` is `execute_block` rejecting a block whole. The kernel's
transaction path turns every transaction-level problem into a **result** instead:
a malformed input, a wrong chain, a bad signature, an unknown seat, a debit that
overflows, and a balance below the fee are all results inside an accepted block.
`debit_of` returning `nullopt` becomes `Result::debit_overflow`; `envelope_checks`
refuses `insufficient_balance` **before** `charged` runs, so `collect_fee` cannot
fail afterwards. The remaining whole-block rejections — a prologue, issue,
expiry, or conservation failure — are chain-state failures that no peer can
induce by choosing bytes. The two bounds that could disagree, the application's
`kMaximumBlockInputsV9` and the kernel's `kMaxRawInputs`, are the same constant
by construction, so the bound is always reported as `6`.

Four candidate transactions were built and offered to `execute_block` directly —
a transfer at the `u64` maximum, a node mint with nothing to collect, a node mint
naming a seat that does not exist, and a monthly pool mint with no claim. **All
four were accepted as blocks and refused as results.**

So the suite records the absence as a measurement rather than skipping it: a
block of transactions the kernel refuses for several different reasons is offered
and required to be `ACCEPTED`. Decision `7` remains implemented, because the
chain-state failures it guards are real; what is now written down is that it is
defence in depth rather than a vote a peer can provoke.

### A probe that passed was the useful one

Seven mutation probes were run against the finished suite. Six failed it
immediately. **The seventh — moving the resource-bound check in front of
`calendar-v1`'s ordered conditions — passed**, which meant the suite did not test
the one property the contract's own sentence about that ordering is *about*: the
vote is identical either way, so the order decides only what is reported, and
nothing reported was being compared.

Four cases were added, each violating a bound and a timestamp rule at once and
each required to report the timestamp rule. The probe then failed as it should.
**A rule whose whole justification is "this is what makes it testable" is a rule
whose test is worth checking for existence**, and the reading that produced the
implementation did not produce the test.

## Consequences

**The next slice is `response_v9` and `dispatcher_v9`**, which now have this
layer's types to encode and `wire_v2` to carry them. After them the node process
and the ABCI adapter, and then the deletion of `src/v8/`.

**Version eight's application is untouched and still green.** Both are compiled,
which is ADR 0065's staged coexistence.

**One behaviour is worth stating because a reader will meet it as a surprise.** A
chain whose first block was finalized but never committed comes back at height
zero, so the next process must call `init_chain` again. That is correct —
`init_chain` happens once per chain, and a chain whose first block never
committed has not had one — and a CometBFT node in exactly that state does call
it again. It is recorded because the suite's first draft assumed otherwise and
failed.

## Owed

**The response encoder, and everything that needs it.** This layer produces
`ApplicationInfoV9`, `FinalizedBlockV9`, `CommittedHeadV9`, and a
`ProposalDecision`; nothing yet turns them into version-two frames. That is
`response_v9`'s, and it is the recorded next action rather than a gap in this
one.
