# ADR 0089: A version-nine chain under one node, and why it resumes only inside the tolerance

- Status: Accepted
- Date: 2026-09-24
- Bounds: [ADR 0079](0079-the-version-nine-application-contract.md)
- Follows: [ADR 0088](0088-the-launcher-derives-the-genesis-time-and-the-first-block-carries-it.md)
- Extends: ADR 0088's finding from height one to every height
- Relates to: `tests/integration/cometbft_version_nine_test.py`,
  `tests/integration/version_nine_chain.py`,
  `tests/integration/version_nine_chain_test.py`,
  `tests/integration/cometbft_process.py`, `tests/integration/cometbft_rpc.py`,
  `tools/verify.sh`

## Context

Every piece of a version-nine node existed and could be launched after M3.20g,
and none of it had met a consensus engine. The recorded next action was version
eight's single-node run rebound to version nine, and the handoff named two
reasons it could not be a plain rebind. A recorded genesis never produces a block
under CometBFT `v0.39.4`, because block 1 carries the genesis stamp and C5
refuses it a minute later (ADR 0088). And a version-nine root commits to the
head's timestamp, which the engine chooses, so no block's root is known before
the block commits.

## Decision

### 1. The fixture is a live ledger over a caller-stamped genesis

`version_nine_chain.Session` takes the genesis stamp as an argument and has no
frozen list of blocks. `apply` and `apply_empty` take the stamp the block
carried. The transactions are fixed in advance, because they bind the chain
identity and nothing about any block.

**Rejected: rebinding version eight's `build_chain`**, which freezes a chain
before any node runs. Version nine has nothing to freeze it with.

### 2. The genesis is stamped with the harness's clock when the run starts

The stamp is the current time in milliseconds, taken immediately before the
genesis is written. The node starts a few seconds later, so the stamp is a few
seconds in the past when block 1 is proposed. C5 admits that, because it is
two-sided within 60 seconds.

**Rejected: a stamp a few seconds ahead of the node's start**, which is how the
handoff first put it. `Node.OnStart` sleeps until a future genesis time before it
starts its RPC server, so every readiness check would have to be widened by the
lead. Nothing is gained, because C5's behind side leaves 60 seconds.

### 3. Every block is computed after it commits, from the header's time

Each step commits first. It then reads the committed header's time and converts
it by `consensus-application-v2`'s rule: seconds times 1000, plus nanoseconds
over a million, truncating. Only then does it ask the model what that block
produces. The receipt, the state root, the header hash, and the published block
identifier are all compared with the model's.

**The conversion is restated in Python rather than trusted from the bridge.** A
root the model derives agrees with the node's only if both derived the same
millisecond. So every comparison checks the bridge's conversion end to end.

Block 1 is additionally required to carry the genesis stamp to the nanosecond.
It is the one stamp nobody proposed, and the bridge converts it exactly rather
than by truncation.

### 4. One block is deliberately empty

After a block that moved the app hash, CometBFT proposes without waiting for a
transaction (`needProofBlock`). A version-nine block always moves it, because the
root commits to the height and the stamp. The harness therefore waits for one
such block after the registrations and checks it like any other.

**It is the sharpest check of the stamp there is.** An empty block's root depends
on its height, its stamp, and the state before it, and on nothing else. No
transaction can be blamed for a difference.

### 5. A closed window is refused by name

The harness checks, after starting a node, that the head's stamp is still at
least 15 seconds inside the tolerance. It does this at the launch and again at
the restart. The next block's stamp is at least the head's, so a run that fails
this check has missed its window for good rather than being slow. It is reported
as that, not as a broadcast timeout.

### 6. The helpers learn version nine without changing versions one and eight

- `inspect_identity_v9` requires exactly `chain_id`, `app_hash`, and
  `genesis_timestamp`, and reads the stamp as canonical decimal. The key set is
  exact per version, as the Go parser's is. A repeated key is now refused for
  every version.
- `initialize_home` passes `-genesis-timestamp` only when given one, so the
  initializer decides what a missing or unexpected stamp means.
- `application_info` speaks the version-two frame to a version-nine application,
  which refuses version one's at the header. It returns the height and the root.
  The durable stamp is not returned, because the root commits to it.
- `commit_transaction` returns the committed height and receipt rather than
  comparing them, and `broadcast` is now written in terms of it.

## Finding: a version-nine chain resumes only inside the tolerance, at every height

ADR 0088 found that under this engine a network that has not decided its first
block within 60 seconds of its genesis stamp never will. **The same holds after
every block, for any outage of a quorum.** This was found by reading the pinned
engine for this slice's restart. At CometBFT `v0.39.4`:

- `state.MakeBlock` stamps every block after the initial height with
  `MedianTime(lastCommit, state.LastValidators)`, the weighted median of the
  previous height's precommit times, and `state.validateBlock` refuses a block
  whose time differs from it;
- after a restart, `reconstructLastCommit` rebuilds `LastCommit` from the stored
  seen commit, so its votes carry the times they were cast;
- `addVote` adds a precommit for the previous height only during
  `RoundStepNewHeight`, and no validator signs a second precommit for a height
  it has committed; and
- `defaultDoPrevote` calls `ProcessProposal` on every validator, the proposer
  included.

So the first block after an outage carries a stamp taken **before** the outage,
in every round, from every proposer. **Once the outage is longer than the
tolerance, every correct machine refuses that block as decision `5`,
`TIMESTAMP_BEHIND_TOLERANCE`, and the chain never produces another.** Height one
is the case where the "outage" is the time before the network first starts.

It applies to any loss of liveness, not only to a stop. A network that loses its
quorum for more than a minute — a partition, a correlated power loss, a bad
release rolled back — halts permanently at the next height. The committed state
is intact, but under the accepted rules nothing can extend it. The only recovery
available is to start a new chain from a new genesis, which would mean a new
chain ID and none of the old state.

**What it means for the evidence.** This slice restarts one node within seconds,
well inside the window, and checks the window by name. A devnet may stop one
replica for as long as it likes, because the other three keep the chain live, and
a returning replica catches up through block sync, which never calls
`ProcessProposal`. **A devnet that stops every replica must restart them inside
the tolerance.** An audit that needs the whole network down must therefore run
after the restart, or against copies of the stores.

**What it means for the product.** A network of consumer machines in homes will
lose a quorum for more than a minute at some point. The accepted rules make that
fatal. **This must be settled before any network is expected to survive an
outage.** It is not settled here, for three reasons. `consensus-application-v2`
freezes the acceptance rules, so any fix is a new contract version. The candidate
fixes have different costs and deserve their own record. And no current slice
depends on the answer. The candidates:

- **Take the behind side of C5 from BFT time instead of the machine's clock.**
  Under this engine a proposer does not choose the stamp. The engine fixes it as
  the median of more than two thirds of the voting power's own precommit times,
  and refuses anything else before `ProcessProposal` runs. `calendar-v1`'s case
  for a two-sided rule was a colluding proposer set stamping far behind. The
  median already bounds that by the correct validators' readings. Whether it
  bounds it enough, and with what fraction of the voting power, needs its own
  analysis.
- **Move to an engine whose proposer stamps its own clock.** CometBFT's
  proposer-based timestamps do this, and the first block after an outage then
  carries a current stamp. `v0.39.4` does not have them, so this is a pinned
  dependency change with its own ADR.
- **ADR 0088's named exemption, generalised.** It would admit the engine's stamp
  when it equals the median of the previous commit. The application cannot check
  that, because ABCI's `ProposedLastCommit` carries no vote times. It would
  collapse into the first candidate.

Recovering by moving every operator's clock back and walking it forward 60
seconds a block is possible in principle. It is ruled out for a network whose
operators are not expected to operate anything.

**The accepted rule is unchanged.** C5 governs every block, and the chain run
here satisfies it. This ADR records what the rule costs under the pinned engine
and changes no behaviour.

## Consequences

- A version-nine chain has now been proposed, voted on, finalized, and committed
  by CometBFT. Every figure the node reported agreed with the independent Python
  model, for stamps the engine chose.
- `version-nine-chain-fixture` is a new ctest entry, and
  `cometbft_version_nine_test.py` runs in `tools/verify.sh` in every preset.
- **No accepted vector file, specification rule, manifest, encoding, kernel
  source, or Go source changes.** Versions one and eight run exactly as before;
  their helpers gained only a stricter refusal of a repeated identity key.
- The devnet slice inherits the launch window and the restart window. The
  handoff records both, and records this finding as the gap to settle before a
  network is expected to survive an outage.
