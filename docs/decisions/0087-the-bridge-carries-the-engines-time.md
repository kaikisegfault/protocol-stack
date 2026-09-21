# ADR 0087: The bridge carries the engine's time, and only version nine reads it

- Status: Accepted
- Date: 2026-09-21
- Bounds: [ADR 0079](0079-the-version-nine-application-contract.md)
- Follows: [ADR 0084](0084-the-version-nine-transport.md),
  [ADR 0086](0086-the-go-local-client-speaks-the-version-two-frame.md)
- Relates to: `adapter/cometbft/internal/bridge/application.go`,
  `adapter/cometbft/internal/bridge/local.go`,
  `adapter/cometbft/internal/bridge/timestamp.go`,
  `adapter/cometbft/cmd/protocol-cometbft-bridge/main.go`

## Context

`localapp.ClientV9` speaks version nine's frame
([ADR 0086](0086-the-go-local-client-speaks-the-version-two-frame.md)). The
bridge that turns ABCI into local calls discarded the engine's block time,
because no version before nine read one. Version nine reads it on three
operations, and
[`consensus-application-v2`](../specifications/consensus-application-v2.md)
fixes how it is converted and what the bridge may refuse.

## Decision

### 1. The interface carries the engine's time, and versions one and eight ignore it

`InitChain`, `ProcessProposal`, and `FinalizeBlock` on the bridge's
local-application interface take a `time.Time`: the genesis time, and the
block time the engine agreed on. `LocalV1` and `LocalV8` accept it and discard
it, which is exactly what they did before the parameter existed.

**Rejected: a second bridge application for version nine.** The seven ABCI
operations, the replay handshake, the committed-height guard, and the
prepare-proposal prefix rule are the same for every version, and a copy of the
bridge would be a copy of all of them.

### 2. The conversion happens in `LocalV9`, not in the bridge

The rule is one pure function, `millisFromTimestamp(seconds, nanos)`, in
`timestamp.go`. It is `seconds * 1000 + nanos / 1000000`, checked, with the
contract's three refusals: a negative `seconds`, a `nanos` outside
`[0, 999999999]`, and an overflowing multiplication. `blockMillis` truncates a
block time. `genesisMillis` refuses a genesis time with a sub-millisecond
remainder, because the launcher controls that value and an exact comparison
keeps the CometBFT genesis and the canonical genesis one-to-one.

It is called from `LocalV9` because version nine is the only version that reads
the result. Calling it for every version would give versions one and eight a
refusal they never had. No engine this adapter is pinned to produces a
pre-epoch time, so the refusal would be unreachable, but it would still be a
behaviour change with no reason behind it.

**Everything representable is passed through.** A stamp above
`MAX_TIMESTAMP_MILLIS` reaches the application and is refused there as decision
`2` or status `7`. A bridge that pre-filtered the range would make
`calendar-v1`'s first condition unreachable end to end.

Go's ABCI types deliver `time.Time`, which cannot hold an out-of-range
nanosecond, so that refusal cannot be reached from a request. It is tested on
the pure function, which is where the contract's rule lives.

### 3. A proposal's answer is a vote with a reason

`ProcessProposal` returns a `Vote`: whether to accept, and a reason. Version
nine's reason is its decision's name in the contract's table; versions one and
eight have none. The bridge votes ACCEPT only on decision `0`. On a rejection
with a reason, it logs `rejected proposal` with the height and the decision at
info level, because a vote against is ordinary on a live network.

This is what `consensus-application-v2` means by "an operator diagnoses it from
decision `4` or `5` in the application log". The C++ application writes no
log, and the bridge is the first process that holds the decision and a logger.

### 4. Info and Commit drop the stamp at the bridge

ABCI's `ResponseInfo` has no field for a timestamp and `ResponseCommit` carries
no head at all, so `LocalV9` maps the version-nine head onto the version-one
shape. The stamp is still reported by the local application and committed by
the root. Whatever the devnet compares across replicas will have to read it
from the local application or from CometBFT's block header. That is the devnet
slice's decision.

## Evidence

In `internal/bridge`:

- the conversion's three refusals, the largest representable stamp, a
  sub-millisecond block time truncating downward, a sub-millisecond genesis
  time refused beside an exact one accepted, and Go's zero time refused;
- a stamp one millisecond past the calendar converted rather than refused;
- over a **real Unix socket**, against a stand-in application that speaks the
  version-two frame by hand and records every request:
  - InitChain sends the exact genesis stamp. One with a sub-millisecond
    remainder is refused before anything is sent.
  - ProcessProposal sends a truncated block stamp. Decision `5` votes REJECT
    and logs `TIMESTAMP_BEHIND_TOLERANCE`, and decision `0` votes ACCEPT.
  - FinalizeBlock sends a stamp past the calendar unchanged, and turns the
    status `7` it answers into an ABCI error.
  - A version-nine result code is named in `protocol-stack-v9`, and the block
    identifier reaches the event.
- versions one and eight pass their existing bridge tests, with the test fake
  moved to the new interface.

In `internal/localapp`, the eight decision names are pinned, and a ninth value
is named by number rather than mistaken for one of them.

**The bridge package imports CometBFT**, so it could not be built locally
without resolving that dependency graph, which the owner's resource rules keep
on hosted runners. It is type-checked and tested by the hosted matrix only.

## Consequences

**The next slice is `nodeconfig` and the identity.** It covers the
`"protocol-stack-v9"` app state, `genesis_time` from identity mode's
`genesis_timestamp=` line, the four-validator genesis that carries it,
`ParseProtocolVersion` accepting 9, and `devnet.InspectIdentity` reading three
keys. After it comes the devnet itself.
