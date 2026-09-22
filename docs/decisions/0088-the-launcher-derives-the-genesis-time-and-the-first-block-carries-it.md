# ADR 0088: The launcher derives the genesis time, and the first block carries it

- Status: Accepted
- Date: 2026-09-22
- Bounds: [ADR 0079](0079-the-version-nine-application-contract.md)
- Follows: [ADR 0087](0087-the-bridge-carries-the-engines-time.md)
- Corrects: [`economy-transition-v9`](../specifications/economy-transition-v9.md)'s
  "A genesis timestamp far from civil time", the height-one case of
  [`calendar-v1`](../specifications/calendar-v1.md)'s BFT-time argument under C5,
  and [`consensus-application-v2`](../specifications/consensus-application-v2.md)'s
  restatement of the first
- Relates to: `adapter/cometbft/internal/nodeconfig/protocol.go`,
  `adapter/cometbft/internal/nodeconfig/config.go`,
  `adapter/cometbft/internal/nodeconfig/devnet.go`,
  `adapter/cometbft/internal/devnet/application.go`,
  `adapter/cometbft/cmd/protocol-cometbft-init/main.go`

## Context

[`consensus-application-v2`](../specifications/consensus-application-v2.md)
gives a version-nine CometBFT genesis five derived values. The fifth,
`genesis_time`, is the canonical `genesis_timestamp` at exactly millisecond
precision, and the launcher must refuse an existing genesis that differs in it.
The bridge already converts it exactly (ADR 0087). Nothing wrote it: every
genesis `nodeconfig` produced carried the epoch, `ParseProtocolVersion` refused
9, and the devnet's identity parser refused any line but `chain_id` and
`app_hash`.

## Decision

### 1. A version-nine identity carries the stamp, and absence is not a number

`Identity` gains a `GenesisTimestamp`, a value whose zero is the absence of a
stamp. Versions one and eight carry none.

**Rejected: zero as absence.** `calendar-v1`'s range starts at zero, so zero is
a valid stamp, and a sentinel would make one real chain impossible to launch.
**Rejected: a pointer.** It would make `Identity` compare by address, and the
existing tests compare identities by value.

### 2. The pairing is refused in both directions, before anything is written

A version-nine home without a stamp and a version-one or version-eight home with
one are both refused, by `genesisTime`, which is the one place that maps a
version and a stamp to a genesis time.

Both `Ensure` functions check the pairing **before writing anything**, and the
devnet case is why. Its `preflight` requires each home's five files all present
or all absent. A refusal that came after the keys were generated would leave keys
without a genesis, and every later start would then be refused as an incomplete
home until someone deleted it by hand.

### 3. The identity parser's key set is exact per version

`parseIdentity` requires exactly `chain_id` and `app_hash`, plus
`genesis_timestamp` for a version that binds one. A version-eight binary started
as version nine is refused for the key it omits. A version-nine binary started as
version eight is refused for the key it adds. Both refusals happen before a home
is written.

**Rejected: reading the stamp whenever it is printed**, which is how the handoff
first put it. It would accept the second case and write a version-eight home.
The application would then refuse that home at InitChain, one step later and
with a less specific error.

### 4. An operator spells the stamp one way, inside C1's range

`ParseGenesisTimestamp` accepts only canonical decimal: digits, no sign, no
leading zero, no whitespace. That is exactly what identity mode prints. It
applies `calendar-v1`'s C1 range. The upper bound, `253402300799999`, is
9999-12-31T23:59:59.999Z, which is also the last instant CometBFT's RFC 3339
genesis encoding can write, so the protocol bound and the encoding bound are
the same bound.

`protocol-cometbft-init` takes the stamp as `-genesis-timestamp`. An empty flag
means no stamp, and `Ensure` decides whether that is refused.

### 5. Versions one and eight keep the epoch

Their genesis files do not change by a byte. `genesisValues` is shared by the
single-validator and the four-validator writers, so the five derived values are
decided in one place.

## Finding: the first block's timestamp is the genesis time, exactly

This was found by reading the pinned engine rather than the contract. At
CometBFT `v0.39.4`:

- `state.MakeBlock` stamps the block at the initial height with
  `state.LastBlockTime`, which is the genesis time, and every later block with
  the median of the previous commit's vote times;
- `state.validateBlock` refuses an initial block whose time is not **equal** to
  the genesis time; and
- `Node.OnStart` sleeps until a future genesis time before it starts consensus,
  its RPC server, or anything else.

**So under this engine `t(1) = g`, always.** Nobody proposes that stamp. It is
fixed by the genesis every validator already agreed on. Three consequences
follow.

**C5 at height one reduces to `|g − own_clock| ≤ 60,000` ms.** A network that
has not decided its first block by `g + 60 s` never will. Every round
re-proposes a block stamped `g`, and every correct machine votes against it as
decision `5`, `TIMESTAMP_BEHIND_TOLERANCE`. **This is a permanent halt at height
one**, not a delay.

**Two claims in accepted documents are wrong about this engine.** Each now
carries a correction note that points here, and so does
`consensus-application-v2`'s restatement of the first:

- `economy-transition-v9` says a genesis far in the past "starts normally"
  because "the first block's stamp is near civil time". Under this engine the
  first block's stamp is `g`, so such a chain never starts. It also says a
  genesis in the future is refused at its first block as
  `TIMESTAMP_NOT_MONOTONIC`. That refusal cannot happen here, because no
  consensus runs before `g`. The analysis holds for an engine whose proposer
  stamps its own clock. It does not hold for this one.
- `calendar-v1` argues that CometBFT's BFT time satisfies C5 because a committed
  stamp is a median of correct validators' clocks. That is true at every height
  but the first. Block 1's stamp is not a median, so at height one C5 holds only
  when civil time is near `g`.

**What a launcher must therefore do:** set `g` at, or shortly ahead of, the
moment a quorum starts, and have that quorum online before `g + 60 s`. A missed
window costs a new genesis, and so a new chain ID. That happens before any block
exists, so no value is lost. It follows that **a recorded vector genesis cannot
start a real network**, because its stamp is fixed and long past. The devnet has
to mint its canonical genesis at run time, with a current stamp. It also has to
keep that stamp inside the supervisor's 90-second readiness bound, because a node
sleeping toward `g` serves no RPC.

**The accepted rule is unchanged.** `calendar-v1` says C5 governs every block,
and it does. This ADR records what that means under the pinned engine and
corrects two descriptions of it. It changes no behaviour.

**Named for later, not taken: exempting a first-block stamp equal to the agreed
genesis value from C5.** The argument for it is that such a stamp is not a
proposer's reading, so the reason C5 exists does not apply to it. It would make a
missed launch window recoverable and would make "a genesis far in the past starts
normally" true. It is not taken now, for three reasons:

- nothing yet needs it;
- the current rule keeps an invariant the exemption would give up: every
  committed stamp was accepted as near civil time by a quorum when it was
  proposed, whereas under the exemption block 1 could be committed years away
  from civil time; and
- `consensus-application-v2` freezes the acceptance rules for the version-nine
  network, so the exemption would be a new contract version rather than a change
  to this one.

If launching a network proves fragile in practice, this is the change to make.

## Consequences

- `protocol-cometbft-init` and `protocol-cometbft-devnet` accept version 9, and
  a version-nine home carries `"protocol-stack-v9"` and the stamp's
  `genesis_time`. Re-initialising it with a different stamp is refused and leaves
  the file untouched.
- `InspectIdentity` takes the protocol version, and the devnet supervisor passes
  the one it starts every bridge with, so the genesis, the identity, and the
  bridges are still one choice.
- **No accepted vector file, specification rule, manifest, encoding, or kernel
  source changes.** Three accepted documents gain correction notes. Versions one
  and eight write exactly the octets they did.
- The devnet slice inherits the launch constraint above. It is recorded in the
  handoff with that slice.
