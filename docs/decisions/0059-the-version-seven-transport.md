# ADR 0059: The version-seven transport, and why the wire is version one's

- Status: Accepted
- Date: 2026-08-31

## Context

[ADR 0058](0058-the-version-seven-application-layer.md) made a block a consensus
engine decided into a block the store commits. Nothing carried those calls: the
version-seven application could only be driven in-process, so no adapter could
speak to it and requirement 13's four-node scenarios still had nothing to run.

Version one has the whole transport — `wire_v1`, `dispatcher_v1`, `response_v1`,
`unix_server_v1`, and the Go ABCI adapter under `adapter/cometbft`.

## Decision

### The frame format is version one's, reused unchanged

The 20-octet header, the seven message kinds, the seven wire errors, and the
five request payloads carry **no ledger-version meaning**: a height, a
transaction list, a byte budget, an app state, a raw transaction. A second frame
format would be a second place for a framing rule — the magic, the version, the
direction, the duplicate-request-identifier rule, the resource bounds — to be
wrong, and both would have to be kept in step by discipline alone.

So version seven adds no wire. What it adds is the half that is genuinely
version-specific.

### The responses are the version-specific half

Three differ. `finalize_block` carries a **block identifier** version one's does
not, because an adapter that could not name the block it just executed could not
tell a peer which one it agreed to. Its per-transaction receipts are version
seven's fifty-six octets with a version field of 7, not version one's
forty-seven. And the result codes an executed transaction can carry are version
seven's thirty-three rather than version one's.

Everything else — the status-and-reserved prefix, the info shape, the prepared
proposal, the single byte of a proposal vote, the committed head — is version
one's layout with version seven's values.

### Every response is validated on the way out, not merely serialised

A receipt whose declared code and encoded result byte disagree, a mempool answer
carrying a receipt it could not have produced, a finalized block with more
results than the block could have held, a response of the wrong type for its
kind: each is refused as `invalid_payload` rather than written.

**The adapter on the other side has no way to tell a wrong answer from a right
one.** It has no ledger, no kernel, and no vectors; it forwards what it is
given. So the last place a disagreement between a declared code and the receipt
beside it can be caught is the encoder, and catching it there costs one
comparison per result.

### One socket, one connection loop, two dispatchers

`UnixSocketServerV1::serve_connection` gains an overload taking an
`ApplicationV7&`. Everything in the loop — accepting, framing, the
duplicate-request-identifier rule, the shutdown descriptor, the clean-EOF path —
is a property of the wire rather than of a ledger version, so the loop is one
function over a dispatcher and the only version-specific step is which
dispatcher a decoded request is handed to.

**The `V1` in that class's name is the wire's version, not the ledger's**, and
the header now says so. Renaming it would touch version one's tests, its server
binary, and its adapter to express something a comment expresses exactly as
well.

### The chain identity is converted explicitly

`InitChainRequest::chain_id` is a `protocol::v1::ChainId`, a `TaggedHash` and
therefore a distinct type from version seven's `Octets32` even though both are
thirty-two octets. The dispatcher converts it in one place rather than either
type being loosened: the tag is what stops a state root being passed where a
chain identity belongs, and it is worth more than the copy costs.

## Evidence

**The `carried` scenario's four contiguous blocks are driven through the whole
frame pipeline** — `process_proposal`, `finalize_block`, `commit`, `info` — as
the octets an adapter would send, decoded by the shared wire, dispatched, and
read back out of the response payload by a reader that refuses to finish with
anything left over. Every block must reproduce its **recorded**
`resulting_state_root` and `block_id`, and every response's header must answer
the kind and the request identifier it was asked about with a declared payload
size equal to what arrived.

**Each admitted input's framed code must be its own receipt's.** The receipt is
decoded back through `decode_receipt` and its result code run through
`application_code`, so the pair the encoder validated is the pair the test reads.

**And the same frames go over a real socket**, which is the only thing that
exercises the version-seven overload: a server is bound, a client connects,
`init_chain` and a whole block are driven through it, and the recorded root and
identifier must come back down the socket. A client that closes cleanly must end
the connection without an error, because that is what an adapter restarting
looks like from this side.

The refusals are exercised on both sides of the boundary. An application error
becomes a **status in a well-formed response frame** — a commit before
`init_chain` answers `sequence_failure` with an empty body — while a malformed
*frame* never reaches the application at all: a commit carrying a block payload,
a truncated frame, an unknown kind, and a zero request identifier are all
refused by the wire.

**Four mutation probes, and two of them found missing tests.**

- Omitting the block identifier from the finalize response is caught by the
  recorded-identifier comparison.
- Removing the encoder's check that a declared code matches its receipt is
  caught by the encoder-refusal case.
- **A `process_proposal` that ignores the application and always answers `true`
  passed at first.** The transport suite only ever sent proposals that should be
  accepted, so the dispatcher could have discarded the application's answer
  entirely. The fix was a test, not a probe: a proposal one height ahead of the
  head must come back as a vote against — status zero, body zero — and it must be
  sent *before* the block is staged, because a staged block makes the same call a
  sequence failure for a different reason.
- **A socket that hands the request to the wrong dispatcher passed as a crash
  rather than a failure**, which was a defect in the test rather than in the
  code: an assertion inside the client block left the server thread unjoined and
  `std::thread`'s destructor called `std::terminate`, hiding the message. The
  block now captures the exception, lets the client's destructor close the socket
  so the server returns, joins, and rethrows. With that fixed the probe reports
  what it should.

## Consequences

- A version-seven application can be spoken to over a Unix socket, which is what
  a Go ABCI adapter needs and the last C++ piece before one.
- `protocol_application` gains two translation units and no new dependency.

## Owed, and recorded rather than implied

- **No version-seven server binary.** `src/application/main.cpp` builds
  `protocol-application` over version one. A version-seven binary needs its
  genesis source, its socket path, and its shutdown handling settled, which are
  operational questions rather than protocol ones, and it is the next slice.
- **The Go ABCI adapter**, which must also answer the replay handshake ADR 0058
  records: the application refuses, terminally, a `finalize_block` at any height
  that is not `current + 1`, including one it has already committed.
- **The uptime schedule**, still `nullptr`. Nothing in this layer changes it: a
  chain driven over this wire writes no cycle assignment and no seat accrues.
- **The socket pathname bound.** `sun_path` caps a socket pathname near 108
  octets, which is why the registered test's directory name is short. A
  version-seven binary will need to state the same constraint rather than
  discover it.

## Alternatives considered

**A version-seven frame format.** Rejected: the request payloads carry no
version-seven meaning, so the second format would differ from the first in
nothing but its name while doubling the places a framing rule can be wrong.

**A second connection loop for version seven.** Rejected for the same reason at
a smaller scale: accepting, framing, and the duplicate-identifier rule are
properties of the wire.

**Renaming `UnixSocketServerV1`.** Rejected: it would touch version one's tests,
its binary, and its adapter to express what one header comment expresses — that
the version in the name is the wire's.
