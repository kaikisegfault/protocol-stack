# ADR 0086: The Go local client names its frame version once

- Status: Accepted
- Date: 2026-09-21
- Bounds: [ADR 0079](0079-the-version-nine-application-contract.md),
  [ADR 0082](0082-the-version-two-application-frame.md)
- Follows: [ADR 0084](0084-the-version-nine-transport.md),
  [ADR 0085](0085-the-version-nine-node-process-binds-the-platform-clock.md)
- Relates to: `adapter/cometbft/internal/localapp/wire.go`,
  `adapter/cometbft/internal/localapp/client.go`,
  `adapter/cometbft/internal/localapp/wire_v9.go`,
  `adapter/cometbft/internal/localapp/client_v9.go`

## Context

`protocol-application-v9` answers the version-two frame. The Go adapter's local
client wrote and required version one's: `wireVersion = 1` was a constant that
`encodeFrame` wrote and `decodeHeader` compared against. Nothing in Go could
talk to version nine.

This is the first of the adapter's three version-nine slices. The ABCI
conversion and the devnet call what it adds.

## Decision

### 1. The frame version is a field of the client, set once at construction

`Client` gains a `version` field. `Dial` and `newClient` set version one's, so
every existing caller writes and requires the octets it did before.
`newClientV9` sets version two's before the client is shared or called, so no
frame a version-nine client writes or reads is ever checked at version one.
`encodeFrame` and `decodeHeader` keep their version-one signatures and delegate
to `encodeFrameAt` and `decodeHeaderAt`, which take the version.

This is the Go form of what `application_driver.py` did in M3.20d: one class
attribute there, one field here, and nothing else copied.

**Rejected: a second client type with its own connection code.** The
connection, the request-identifier discipline, the terminal latch, and the
envelope carry no ledger version, and a copy of them would be a second place for
a framing rule to be wrong.

**Rejected: a package-level version switch.** The adapter must be able to hold a
version-eight client and a version-nine client in one process while the devnet
migrates, and a global would make that impossible.

### 2. Statuses 7 and 8 are a decoder rule over the version and the kind

`maximumStatus(version, kind)` returns 8 for a finalize over version two and 6
for everything else. The envelope decoder refuses any status above it. So a
status 7 or 8 on a proposal, on a commit, or on a version-one connection is not
an `*ApplicationError` the caller can hold. It is a protocol failure that ends
the connection. That is the client's side of ADR 0084's first decision: the C++
encoder cannot write those statuses on any kind but 6, and this client does not
believe them on any other.

### 3. A decision is a value, and a ninth is a protocol failure

`ClientV9.ProcessProposal` returns a `Decision` and no error for every value
`0` through `7`. A nonzero decision is a peer's bad proposal, which is ordinary,
and it must not look like a failure of this node. A value past `7` would still
vote REJECT and would report an outcome the contract does not name. So it is
refused rather than passed on.

### 4. The version-nine decoders are their own, as version eight's were

`decodeFinalizeV9` is version eight's with version nine's receipt prefix.
`decodeInfoV9` and `decodeCommitV9` read the stamp between the height and the
root. They sit beside version eight's rather than generalising them, because
ADR 0065's staged replacement deletes version eight's next, and a shared helper
would have to be unwound when that happens.

## Evidence

In `internal/localapp`:

- a frozen version-two Info frame, and each header decoder refusing the other
  version's frame beside accepting its own;
- statuses 7 and 8 on kind 6 over version two, refused on the six other kinds and
  over version one, and status 9 refused;
- all eight decisions, with 8, 255, an empty body, and two octets refused;
- Info and Commit refused when cut at every octet and when followed by one;
- all three admission failures and all 45 results through the finalize
  decoder. The refusals each sit beside an accepted control: a version-eight
  receipt, a result out of range, a code that disagrees with its receipt, a
  wrong receipt length, admission data, a wrong count, and trailing octets.
  Version eight's decoder refuses a version-nine block.
- Pipe tests whose expected request octets are **written by hand** rather than
  by the encoder under test, over finalize, proposal, commit, InitChain, Info,
  and CheckTx. Status 8 on a finalize comes back as the application's answer,
  status 7 on a proposal ends the connection, and a version-one response is
  refused.
- a fuzz target over the version-nine decoders.

**Ten mutation probes were run against the finished suite, and all ten were
caught.** The first draft's pipe tests computed their expected request with the
encoder under test, so a swapped height and stamp would have passed. That was
found by reading the tests with the probes in mind, before they were run.
The first probe run hung and was stopped. A probe that made the fake server
refuse a request left the client blocked on a pipe until `go test`'s ten-minute
default timeout. The probes were re-run under a 20-second timeout, and the
helper now closes its end on a mismatch, so such a probe fails in under a second.

The package is standard-library-only, so it was built and tested locally with
the local Go 1.23 toolchain in a scratch module, without downloading the
module's pinned toolchain or its dependency graph. The hosted matrix runs it with
the pinned toolchain inside the module.

## Consequences

**The next slice is the ABCI conversion**: the bridge's version-nine local
application, the `Timestamp` to millisecond conversion and its three refusals,
InitChain's fourth compared value, the `"protocol-stack-v9"` app state,
`genesis_time` from identity mode, and `--protocol-version 9`. After it comes
the devnet.
