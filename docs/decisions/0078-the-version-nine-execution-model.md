# ADR 0078: The version-nine execution model carries its clock in the ledger

- Status: Accepted
- Date: 2026-09-16
- Bounds: [ADR 0077](0077-the-version-nine-clock-and-monthly-settlement.md),
  [ADR 0064](0064-the-version-eight-execution-model.md)
- Relates to: `docs/specifications/economy-transition-v9.md`,
  `simulation/economy_transition_v9/`

## Context

[`economy-transition-v9`](../specifications/economy-transition-v9.md) defines a
block header timestamp, four state entries, a widened pool value, one
transaction kind, and a six-step prologue. M3.17b made its contract half
executable; this record covers the half that runs a chain, on the pattern
[ADR 0064](0064-the-version-eight-execution-model.md) set for version eight.

Most of the execution model is inherited and needed no decision: value movement,
the registry, the fee, version seven's settlement steps 1 through 7, the recovery
pool, the mint walk, the uptime carrier, and every carried transaction are
version eight's and are covered by their own accepted vectors. What follows is
the set of rules this slice had to settle, and the two findings worth more than
the code.

## Decision

### 1. The four new maps are typed fields projected into entries

`window_months`, `figures`, `claims` and `accumulating_month` are fields on the
ledger, and `economy_entries` encodes them. That is version six's and version
seven's pattern and **not** version eight's.

**Version eight's raw key-to-value map was right for version eight and is wrong
here.** It held its uptime evidence as one map over the real key space because
`uptime_transitions.Context` reads that space directly, so binding it made the
accepted measurement model's two transitions *the* implementation rather than a
sibling of one. Nothing in version nine reads the raw space: `settlement.py`
operates on plain decoded dicts, which is the seam the contract half already
fixed. A raw map here would mean decoding on every settlement and encoding back,
with no accepted model on the other side to be bound to.

`require_entry_shape` runs over the projection at the root, so a field that
encoded badly fails at the commitment rather than surviving as a value nothing
reads.

### 2. `advance_to` takes the timestamp as a required argument

Version six's shorthand stands in for a run of empty blocks, and version eight
refuses it once any seat is activated. Version nine keeps that refusal and adds a
required timestamp.

**It is required rather than optional because the failure it prevents is silent.**
A shorthand that advanced the height and left the stamp behind would commit a
root naming a height the stamp does not belong to, and **every later block would
still satisfy C2**, because a stale stamp is smaller than the next one. The
result is a wrong root rather than a refusal, which is the direction that hides.

The consequence is observable in exactly one place — the root the shorthand
leaves behind, which the next block carries as its `previous_state_root` — and
`test-vectors/economy-transition-v9-execution.txt` records it. **A probe found
that gap**: the defect was described in the commit that introduced the guard and
no vector caught it, which is what the probe is for.

### 3. The block calls the clockless path and cannot reach the other one

`block.py` binds `timeline.replay` and never binds `timeline.accept`. C5 is
applied once by a machine admitting a proposal, before it executes anything, and
`replay` takes no clock argument at all.

**Stating it as two entry points rather than as a flag is what makes it
structural.** A single function with a nullable clock would place the whole rule
on a caller passing `None`, and a machine that replayed history with its own
clock would reject the chain's own past one tolerance-width after producing it —
silently, and only for old blocks.

### 4. A timestamp failure rejects the whole block

C1 and C2 run before anything reads the field, and a failure raises the block
transition's own rejection, which restores the pre-block state exactly through
the snapshot `execute_block` already takes. They produce no transaction result,
exactly as `ledger-transition-v1`'s height rule does.

### 5. The trace runs at ninety seconds a block

At the commit target a window is exactly one day, so a month is about thirty
windows and 864,000 heights — more than a recorded trace can run. At ninety
seconds a window is exactly thirty days, every window opens in a new month, and a
settlement is reachable inside three.

**Nothing in the contract bounds the block rate from above**, which
`economy-transition-v9` states outright, and a seat's figure is
`credited_slots * SLOT_SECONDS` — a function of **heights**. So a slower chain
changes when a month closes and changes nothing about what a machine earned,
which is what makes the fixture a chain rather than a contrivance.

**Rejected: shortening the window or the month for the fixture.** Both are
accepted constants; a trace that changed one would be evidence about a different
contract.

## The two findings

### One of the two new orderings is observable and the other is not

**The payout before the accrual is observable.** The window being assigned
belongs to the new month, so its accrual belongs to the new month: letting it
land first pays the closing month one window of its successor's accrual, and the
resulting root differs. The vectors run the rejected order and record the
difference.

**The accumulation before the deletion is normative and unobservable.** The
specification's reason for the order — that the figures are computed from the
kind-19 records the deletion removes — is true of an implementation that reads
those records **lazily**, and vacuous for one that derives the window's seat
sequence **once** before either step. Every conforming implementation derives it
once, because the settlement needs the same sequence the assignment does, so the
two orders commit to the same root.

This is the shape ADR 0064 already recorded for version eight's
prologue-before-issue ordering: *normative and, under the accepted parameters,
unobservable*. The vector states what the shape of the prologue makes safe rather
than claiming an order the chain could observe, and it is where a later
implementation that read the records lazily would be noticed. **The alternative
— deleting the vector because it proves nothing — would remove the only place
that change is visible.**

### The pool pays, and it is the first time

The unreferred performance pool has accrued since `economy-transition-v3`: an
unreferred seat's 34.2 units per cycle route to it, version six gave it an entry
kind, version seven's genesis writes it, and **nothing has ever taken value out
of it**. The recorded trace does: February closes at the assignment of the window
that opens March, the machine that answered all 69 of its audits beats the one
that answered none of its 75, and it mints the whole balance with kind 22.

That is what makes the two pool identities testable rather than decorative. They
are checked after every block of both scenarios, and the second — that the pool's
`minted` equals the claims' minted total — could not have been false before,
because nothing could mint.

## Consequences

**The model is the contract's, not a second reading of it.** Three modules bind
an accepted model with a guard that keeps the binding honest, and the two
restatements the contract half could not avoid are each checked against the
artifact they restate. The execution half adds no new restatement.

**The kernel slice inherits a described seam rather than a shape to infer.**
`settlement.py` takes decoded dicts, `ledger.py` holds typed fields and projects
them, and `block.py` wires the two. A C++20 implementation may hold its state
however it likes; what it must reproduce is the projection, the root, and the
order.

**What is still owed is the stack.** A version-nine chain runs in Python and
nothing else runs it: the snapshot, the owning store, the application layer, the
transport, the node process and the ABCI adapter are all version eight's, and the
application contract cannot carry a timestamp at all until the version
`economy-transition-v9` names is accepted. **Nothing can run a version-nine
devnet until that exists.**
