# ADR 0058: The version-seven application layer, and why finalize writes nothing

- Status: Accepted
- Date: 2026-08-31

## Context

[ADR 0057](0057-the-version-seven-owning-store.md) made a version-seven state
durable: a chain can be stopped in the middle of its history and resumed on the
same trajectory. **A store is not a node.** Nothing turned a block a network
agreed on into a block the store commits, so requirement 13 of
[`first-goal.md`](../project/first-goal.md) — adversarial four-node economic
scenarios — still could not begin.

Version one already has the layer that does it:
`protocol::application::ApplicationV1` over `SQLiteLedger`, with the wire, the
dispatcher, the Unix server, and the Go ABCI adapter beside it. Version seven had
none of it.

This ADR records `ApplicationV7`, the first of those pieces.

## Decision

### The seven operations are version one's

`info`, `init_chain`, `check_transaction`, `prepare_proposal`,
`process_proposal`, `finalize_block`, and `commit`, with the version-seven kernel
and store underneath and version one's `ApplicationError` unchanged. Its six
codes describe the *application protocol* — a malformed request, an operation out
of sequence, a kernel refusal, a storage failure — and none of them names a
ledger version, so a second copy would be six more numbers meaning the same six
things.

### `finalize_block` writes nothing, and `commit` requires the store to agree

This is the whole of the layer's safety argument. CometBFT calls the two
separately; `SQLiteLedgerV7::apply_block` writes the head and the block row
together and takes no target height beyond `current + 1`. They are reconciled the
way version one reconciles them:

`finalize_block` copies the durable head, executes the block against the copy,
writes nothing, and **stages** the root, the block identifier, the per-input
results, and the commit record it expects. An identical repeat returns the same
staged response, because CometBFT may ask twice and a second execution that
disagreed with the first is precisely what this layer must not hide.

`commit` replays that block through the store and **requires the store to
reproduce exactly what was staged** — the same commit record, then the same root
at the same height on the durable head. Anything else is terminal. That equality
is what makes "the root this node told the network" and "the root this node
persisted" one fact rather than two.

**The candidate ledger is deliberately not kept.** The stage holds the candidate
*root*, not the candidate state. The root commits to every entry, so comparing
roots is comparing states, and holding a second ledger would invite a later
change to commit *it* instead of replaying the block — which would delete the
only check that the store and the kernel agree.

### Any refusal after the chain is ready latches

A deterministic application that has told the network one thing and found another
cannot continue and be trusted, so it stops answering. Two refusals are
deliberately *not* faults: an admission failure in `check_transaction` is a
mempool answer, and a `process_proposal` that votes against a block is an
ordinary answer about a peer's proposal. Neither latches, and both are tested for
it, because a node that bricked itself on a peer's bad proposal would be a
liveness hole rather than a safety property.

### `process_proposal` executes; version one's does not

Version one checks the height and the byte bounds. Version seven also executes
the block against a candidate copy, and the reason is the kernel rather than
taste: `execute_block` has whole-block rejections version one's transfer kernel
does not have — an invariant failure, a conservation failure, an admitted count
past its bound — and reaching one at `finalize_block` **halts the node
permanently**. A block this node cannot execute must be voted against.

It is affordable here in a way it was not for version one: `read_head` already
hands back a whole `v7::Ledger` by value, so no restore is needed and **the store
needs no dry-run operation added to it**. Adding one would be a second way to
execute a block, which is a second opinion about what a block does.

**No constructible input reaches that execution's own refusal today, and this ADR
records that rather than implying otherwise.** Every whole-block rejection
`execute_block` can raise is either already refused by the bounds check —
`kMaxRawInputs` and `kMaxAdmitted` are the same figure — or is an internal
invariant violation no conforming sequence reaches. The execution is insurance
against a kernel defect, and it is kept because the failure it prevents is a
permanent halt while its cost is one execution of a block this node is about to
execute anyway.

**That cost is three executions per committed block** — the proposal, the
finalize, and the store's own — and each answers a different question. The store
must execute the block itself because it is the store that commits the head;
handing it a pre-executed candidate would make it trust the caller's state, which
is the thing the equality check exists to refuse. If the cost ever matters, the
place to fix it is a measurement, not a shortcut through that check.

### `prepare_proposal` keeps the order it was handed

The proposal is a prefix of what arrived, truncated at the byte budget and the
input bound. Reordering is a policy with economic consequences and nothing in the
accepted contracts asks for one.

### The verifier comes from the store

`check_transaction` admits a transaction before it is ever proposed, and it must
use the rule the block will be executed under. `SQLiteLedgerV7::verifier()` hands
it back, so the mempool check and the execution cannot be separately configured —
the same reason [ADR 0045](0045-the-version-six-execution-model-and-three-derived-rules.md)
gives for the kernel taking a verifier at all.

### `init_chain` is idempotent at genesis

It requires the durable height to be zero, the chain identity to match the one
the genesis produced, an initial height of one, and the app state
`"protocol-stack-v7"`. It does not refuse a second call at height zero, because
CometBFT calls `InitChain` again on a node that crashed before its first block. A
store already past genesis was initialised by an earlier process, so the
application comes back ready without it: `init_chain` happens once in a chain's
life, not once per process.

The app state is what stops a node started against a version-one genesis and a
version-seven engine: it refuses at `init_chain` rather than at the first block.

### Response codes keep version one's scheme

An admission failure carries its own small number and an execution result is
offset by 256, so a reader can tell "never entered the block" from "entered and
was refused" without a second field. The scheme is pinned by `static_assert`
rather than observed at run time, because it is a contract with the adapter.

## Evidence

**The `carried` scenario's four contiguous blocks are driven as `process_proposal`
→ `finalize_block` → `commit`, with the application and its store destroyed and
reopened between every pair**, and every block must reproduce its **recorded**
`block_id` and `resulting_state_root`. Each block is finalized twice and the two
responses must be identical. After each commit, `info` must report the recorded
root at the recorded height.

**A raw input the kernel refuses at admission must be invisible to consensus.**
Appending eight zero octets to a recorded block's inputs must reproduce the
*same* recorded root and the *same* recorded block identifier, and differ only by
one more result row carrying the admission code and no receipt. **That test
exists because a probe found it missing**: none of the recorded blocks contains a
rejected admission, so a `finalize_result` that silently dropped rejected inputs
passed everything else in the suite. Re-aimed against the new case, the same
probe fails, and so does one that offsets the rejected input's code into the
execution range.

Four more probes were run and each is caught by the check that names it: a
`commit` that does not replay the block through the store is refused by the
head-equality check; a repeated `finalize_block` that re-executes rather than
returning the stage is refused by the identical-response check; a
`process_proposal` that accepts everything is refused by the wrong-height case;
and a `finalize_result` that drops rejected inputs is refused by the
one-result-per-input case.

The refusals are exercised in full: `init_chain` under another chain identity, at
an initial height that is not one, and with version one's app state; committing
with nothing staged; finalizing a block this chain cannot be at; finalizing a
second, different block at one height; proposing while a block is staged; and the
terminal latch after each.

## Owed, and recorded rather than implied

- **The uptime schedule is `nullptr`.** `execute_block` takes one and this layer
  does not supply it, so a chain driven entirely through `ApplicationV7` writes
  **no cycle assignment record and accrues nothing to any seat**. Blocks execute
  correctly and every root is the recorded one, because the recorded contiguous
  run opens no window — but the layer cannot yet run a chain past a cycle
  boundary and mean it. Where an uptime measurement enters consensus is
  [ADR 0028](0028-uptime-measurement-pipeline.md)'s attested-claim pipeline, and wiring it
  to this layer is the dependency between here and a chain that pays anyone.
- **The wire, the dispatcher, the Unix server, and the Go ABCI adapter**, each
  its own slice. Nothing yet speaks to CometBFT.
- **Fault injection over the application's storage failures.** The seams exist in
  the storage layer; nothing drives them through this one, so the terminal path
  after a storage failure is reasoned about rather than exercised.
- **Recovery after a terminal latch.** There is none: the process must restart.

## Alternatives considered

**Execute once and commit the candidate.** Rejected: the store would have to
trust a state handed to it, and the equality between what was announced and what
was persisted would have nothing left to compare.

**Follow version one exactly and leave `process_proposal` a bounds check.**
Rejected above: version seven's kernel rejects whole blocks for reasons version
one's cannot, and the consequence of meeting one at `finalize_block` is a
permanent halt.

**Give `SQLiteLedgerV7` a dry-run operation.** Rejected: `read_head` already
returns a ledger by value, so the application can execute a candidate with no new
store surface, and a second execution path in the store would be a second opinion
about what a block does.
