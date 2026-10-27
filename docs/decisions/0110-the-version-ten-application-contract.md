# ADR 0110: Version ten's application contract is a third version at frame version two, and its application is version nine's rebound

- Status: Accepted
- Date: 2026-10-28
- Bounds: [ADR 0079](0079-the-version-nine-application-contract.md),
  [ADR 0083](0083-the-version-nine-application-reads-one-clock.md),
  [ADR 0084](0084-the-version-nine-transport.md)
- Follows: [ADR 0104](0104-the-version-ten-kernel-is-staged-beside-version-nine.md),
  step 5, and [ADR 0109](0109-the-version-ten-owning-store.md)
- Specification: [`consensus-application-v3`](../specifications/consensus-application-v3.md)
- Relates to: `include/protocol/application/application_v10.hpp`,
  `src/application/application*_v10*`, `src/application/dispatcher_v10.cpp`,
  `src/application/response_v10.cpp`, `src/application/unix_connection_v1.cpp`

## Context

`SQLiteLedgerV10` keeps a version-ten head across restarts (ADR 0109). Nothing
lets a consensus engine drive it, so no node process can run version ten.
`economy-transition-v10` says what the application contract must gain. It must
name the new ledger, map results 1 through 49, and read a 182-octet genesis. It
leaves open whether that is a new contract version or a stated rebinding of
`consensus-application-v2`, as ADR 0079 decided the question for version nine.

**The application needed almost no decision.** The clock, its single read, the
two reporting channels, the separation of C5, the staging and replay rules, and
the transport's signatures are ADRs 0079, 0083, and 0084's, and none of it is
version-specific. Version ten's kernel keeps version nine's timestamp entry
points, its condition space, its header, and its receipt layout.

## Decisions

### 1. A third contract document, inheriting the second by reference

`consensus-application-v3` is a new accepted document. It inherits all of
version two by reference and states a closed list of nine differences.

**Version two's own rule decides this.** It freezes its result mapping, its
codespace, and its protocol version for the version-nine network. It also says
a change to result codes or application hashes requires a new application
contract version. Version ten makes both changes.

**Rejected: a rebinding section added to version two.** It would edit an
accepted document that says it is frozen for another network. When ADR 0104
step 7 deletes version nine's code, the live contract would sit inside the
record of a network no code runs. Version two did not edit version one for the
same reason.

**Rejected: a standalone version three restating everything.** About 700 lines
of version two would be copied for nine changed values. A copy can drift from
its source, and this slice found that version two had already drifted from the
code (below).

### 2. The local frame stays at version two

The frame version names the frame's shape, and version ten changes no payload.
Version one's frame carried ledger versions one, seven, and eight. ADR 0079's
finding was a payload that changed shape while the field stayed still, which
does not happen here.

Two existing fields name the ledger. Info's application protocol version, now
`10`, names it on the first frame of every start. Each receipt's version octets
name it on every executed transaction. The contract adds one bridge rule: **a
version-ten bridge refuses an Info whose application protocol version is not
`10`.** So a version-ten bridge paired with a version-nine application is
refused on its first frame, in terms that name the fault.

**Rejected: frame version 3.** It would copy `wire_v2`'s decoder and encoder,
and the Go client's frame handling, to change one constant. It would make the
frame version track the ledger version, which it never has. And the pairing it
would catch at the header is already caught at Info, which is also the first
frame. The reverse pairing, a version-nine bridge and a version-ten application,
is refused at the launcher, at InitChain, or at the first version-ten receipt.
It exists only until step 7.

### 3. `ApplicationV10` is version nine's application rebound

`application_v10.hpp` and its three units are version nine's with the
namespace and the store rebound. ADR 0104 rejected shared or version-agnostic
layers, so nothing is shared with version nine's units. The differences are
these:

- the application protocol version is `10`;
- the expected application state is `"protocol-stack-v10"`, 20 octets;
- the candidate and decided paths call version ten's `execute_block`, and
  admission calls version ten's `admit`;
- the condition-count assertion is made against version ten's kernel.

### 4. The transport is version nine's, rebound, over the same wire

`response_v10` and `dispatcher_v10` are version nine's rebound.
`serve_connection(ApplicationV10&)` is a third overload of the one socket loop,
reading `WireV2`, as version nine's does.

The receipt check derives its prefix from `v10::kReceiptVersion` and its bound
from `v10::kResultCodeCount`. So a version-nine receipt is refused, a result of
`49` is written under `305`, and a result byte of `50` is refused.
`encode_timestamp_failure_v10` still takes no kind.

## The finding

**`consensus-application-v2` says Info's application version is ASCII `9.0.0`,
and the Go bridge has always sent `1.0.0`.** One constant serves both
constructors. Nothing reads the value: CometBFT reports it and does not use it
in consensus, and no devnet check compares it. So the drift was never visible.
The bridge now takes its version string from its constructor, as it already
takes its codespace. `NewV9` sends `9.0.0` and `New` still sends `1.0.0`.

It is the third time a contract's prose and its code disagreed with nothing to
notice. ADR 0068 found the receipt version in the receipt magic. ADR 0079 found
the block identifier in a finalize response. ADR 0079's lesson applies: reconcile
a contract against the code that implements it. This slice found the drift
because it read `bridge/application.go` before writing version three's Info
section.

## Evidence

`version-ten-application` and `version-ten-transport` are two CTest entries over
four translation units and a support header. Both replay the five-height
`restart.` run.

- **The pipeline.** All five blocks are driven through the application across a
  reopen before every block, and over the wire. Each reproduces its recorded
  root, block identifier, and stamp. The fifth block's two kind-23
  registrations succeed through an application reopened just before it, so the
  build authority key reached the application's head.
- **The top of the range.** A registration one block past its approval lifetime,
  offered beside the first block's inputs, returns result `49` under ABCI code
  `305` with a version-ten receipt.
- **Version nine's suites, carried.** Every decision, its ordering pairs, both
  sides of C5 at their exact boundaries, the counted clock, the two fatal
  statuses and their latch, the same-stamp replay, InitChain's four comparisons
  with version nine's application state refused, the clockless refusal, the
  encoder's refusals each beside an accepted control, and a real socket refusing
  a version-one frame.
- **The bridge.** A Go test pins each constructor's version string.

## Consequences

**ADR 0104 step 6 is next**: `protocol-application-v10`, the Go adapter's
version-ten client with the Info check, the codespace, the version string `10.0.0`,
the launcher's `"protocol-stack-v10"`, and the devnet runs with the HUB test
verifier moved onto version ten.

**Version nine is untouched in behaviour**, apart from the bridge's
informational version string.

## Owed

Version two's owed review items, the widened grinding surface and the
clock-discipline requirements, carry over unchanged. This slice adds none.
