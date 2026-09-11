# ADR 0071: A devnet cannot reach the uptime audit, and this milestone does not build a way

- Status: Accepted
- Date: 2026-09-11
- Bounds: [ADR 0063](0063-the-version-eight-uptime-carrier.md), [ADR 0064](0064-the-version-eight-execution-model.md)
- Relates to: `docs/project/first-goal.md` requirement 13

## Context

M3.14a put version eight's two seat transitions under a real consensus engine
for the first time: four independent replicas execute a purchase and an
activation from octets, agree on the roots, and report the same durable head.

The natural next sentence — that the run therefore exercises version eight's
uptime audit — is false, and this repository has written it down twice. It sat
in `docs/project/current-state.md` for two sessions as a claim about what the
next slice would observe, and a slice planned against it would have spent itself
discovering a constant.

**The constant.** A seat is in scope for a window only from the window *after*
the one it activated in. `slots.first_cycle_window` is
`window_of_height(activation_height) + 1`, which `cycle-boundary-v1` fixes for
the reason a seat activated mid-window has no evidence for the whole window. And
`CYCLE_BLOCKS` is **28,800**. So a seat activated anywhere in window 0 is first
audited at height 28,800, and activating later does not help: it moves the seat
into a later window, whose first height is further away still.

A four-node devnet begun at genesis has to propose, vote on, and commit every
one of those blocks. The recorded traces reach window 1 through a shorthand a
network does not have — `trace.py` sets an activation height near the window
boundary and calls `Ledger.advance_to`, which version eight overrides to
**refuse** once any seat is activated, precisely because a version-eight block
with no transactions still audits every in-scope seat. The shorthand is legal
exactly once, before any activation, because that is the only stretch of a
version-eight chain where a transaction-free block changes the height and
nothing else.

## Decision

**The devnet fixtures sell and activate a seat and do not reach the audit, and
they say so in a check rather than in a comment.**

`check_the_audit_is_out_of_reach` in `tests/integration/version_eight_chain_test.py`
and `check_the_seat_is_sold_and_unaudited` in
`tests/integration/cometbft_four_validator_v8_test.py` both derive the first
audited height from `first_cycle_window` and `window_first_height` and require it
to exceed the height the chain reached. Neither transcribes 28,800. A changed
constant is therefore reported as a changed constant, and a network that somehow
*did* reach its seat's first window fails the check rather than passing it while
the prose beside it goes quietly wrong.

**Neither mechanism that would cross the wall is adopted in this milestone.**
Both are real, both are someone's next slice, and each is refused here for its
own reason.

### A chain begun at a nonzero initial height

Starting a devnet near height 28,780 would put a seat in scope about twenty
blocks later. `initial_height` is already carried across the wire to the
application, so the plumbing exists. **Three layers refuse anything but 1, and
all three refuse it on purpose**: `nodeconfig.readGenesis` rejects a genesis
document whose `InitialHeight` is not 1, `ApplicationV8::init_chain` rejects the
value in the handshake, and version one's application rejects it identically.

That is not a harness restriction to relax. **The state root commits to the
height** — `state_root` takes the height as an input, and the genesis identity a
node is handed is the root at height zero. A chain whose first height is 28,780
has a different genesis root for the same genesis octets, so admitting one means
deciding what a genesis at a nonzero height *is*, which is a compatibility
change to the accepted contract. It needs `change-protocol`, a specification,
cross-language vectors, and its own ADR. It must not arrive as a test-harness
option, which is exactly the shape it would have taken had this slice reached
for it.

### A devnet stood up on a restored snapshot

`snapshot_v8` can already express a ledger at any height, and
[ADR 0066](0066-the-version-eight-state-snapshot.md)'s restore gates already run
`conservation_failures` over it, so the state a seeded network would need is
expressible and checkable today. What does not exist is any supported path to
*start* from one: `protocol-application-v8` takes a database, a genesis, and a
socket, and the snapshot code is a library with tests rather than an operator
entry point. Building that path is a node-process slice with its own operator
surface, its own refusals, and its own ADR.

**A third option — shortening `CYCLE_BLOCKS` for tests — is refused outright.**
The cycle length is derived in `cycle-boundary-v1` from the founder-directed
cycle duration and the target commit interval. A fixture that ran against a
different one would be agreeing with itself about a chain nobody operates.

## What requirement 13 actually asks

Requirement 13's words are "adversarial four-node economic scenarios through
restart and recovery, proving deterministic replica agreement on state roots".
A seat purchase, a seat activation, a confirmed transfer, and the fees they
charge are economic activity, and four replicas agreeing on the roots they
produce is the proof the requirement names. **The audit is a further claim, and
it is not this requirement's.**

What requirement 13 still lacks after M3.14a is the other half of the word
*adversarial*: a replica fed a block the others refuse, a partition, and a node
restarted mid-block. Nothing in this repository has yet observed a node *reject*
a peer's block, which is the property the whole deterministic-kernel argument
rests on. That gap has no dependency on the audit and is the next slice.

## Consequences

- The version-eight devnet fixtures execute five transactions and both seat
  transitions, and prove nothing about uptime measurement. The evidence for the
  measurement pipeline remains what it was: the recorded version-eight
  execution trace, which runs all 28,800 heights of a window in Python, and the
  C++ kernel's agreement with it on vectors.
- `first-goal.md` requirement 7's deterministic uptime record is **not**
  demonstrated end-to-end on a network by this milestone, and no document in
  this repository may say that it is.
- Two named slices are created rather than started: nonzero-initial-height
  chains, which is a `change-protocol` matter, and snapshot-seeded devnets,
  which is a node-process matter.
- The general lesson is one this repository has now recorded twice in two
  forms. A plan written before its dependencies landed must re-derive its own
  preconditions rather than trust the sentence that authorised it, and **a claim
  about what a fixture will observe is worth probing against the model before it
  is worth building.** Both checks named above exist so that this particular
  claim cannot rot again.
