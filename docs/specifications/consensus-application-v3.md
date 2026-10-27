# Consensus application contract v3

Status: Accepted for M4 version ten

This document is normative for the version-ten boundary between an ordering
engine and the persistent protocol application. It does not change the canonical
genesis, transaction, execution, receipt, block, or state-root rules in
[`economy-transition-v10`](economy-transition-v10.md), and it changes no rule of
[`calendar-v1`](calendar-v1.md) or of where each one runs.

It remains an adapter-only compatibility contract. The ordering adapter supplies
a height, a timestamp, and ordered raw transaction bytes. The C++ application
remains the only authority for admission, execution, receipts, application
hashes, and durable state.

## Relationship to version two

[`consensus-application-v2`](consensus-application-v2.md) is version nine's
contract and remains accepted, unedited, and the record for the version-nine
network. Its own versioning rule is why this document exists: a change to
result codes or application hashes "requires a new accepted application-contract
version", and version ten changes both. It adds five result codes, and every
root it commits is a version-ten root.

**Everything version two fixes that version ten does not touch is inherited by
reference, and the list of changes below is closed.** That includes everything
version two itself inherits from
[`consensus-application-v1`](consensus-application-v1.md). The inherited set is
the boundary invariants, one to thirteen; the clock and its single read in
`ProcessProposal`; the timestamp conversion and what the bridge may refuse; the
ownership, staging, and serialization rules; the decision space `0` through `7`
and its evaluation order; the status space `1` through `8`; the crash-and-replay
table and its same-stamp rule; the local frame, its version, and every payload
shape; the unsupported-ABCI-feature list; the four-validator topology and its
three deltas; and the seeded-launch rule of
[ADR 0097](../decisions/0097-a-seeded-launch-takes-its-genesis-from-one-head.md).
Where a section below is silent, version two governs.

## What version three changes

| | Version two, for version nine | Version three, for version ten |
| --- | --- | --- |
| Ledger it drives | `economy-transition-v9` | `economy-transition-v10` |
| Canonical genesis file | 150 octets | 182 octets |
| Chain identity label | `protocol-stack:v9:chain-id` | `protocol-stack:v10:chain-id` |
| Info application version | ASCII `9.0.0` | ASCII `10.0.0` |
| Info application protocol version | `9` | `10` |
| CometBFT `app_state` | `"protocol-stack-v9"` | `"protocol-stack-v10"` |
| Execution results mapped | `1` to `44`, to ABCI `257` to `300` | `1` to `49`, to ABCI `257` to `305` |
| Codespace | `protocol-stack-v9` | `protocol-stack-v10` |
| Receipt version in a finalize result | `9` | `10` |
| Local frame version | `2` | `2`, unchanged |

Nothing else changes. The block header, the timestamp, and every rule about
proposals are version nine's, because `economy-transition-v10` keeps the header
schema at `9` and changes none of them.

## Deployment identity

Version two's configuration is unchanged except for what it is applied to. The
canonical genesis byte file is version ten's 182-octet genesis, and canonical
genesis validation still applies C1 and reads no clock.

The five derived CometBFT genesis values take their version-ten forms:

- `chain_id`: ASCII `ps-` and the unpadded URL-safe base64 of the version-ten
  chain ID;
- `initial_height`: decimal `1`;
- `app_hash`: the version-ten height-zero state root, as 64 uppercase hexadecimal
  characters;
- `app_state`: the exact UTF-8 JSON string bytes `"protocol-stack-v10"`,
  including the two quote bytes;
- `genesis_time`: version two's rule unchanged.

A seeded launch takes `initial_height`, `app_hash`, and `genesis_time` from the
head, as version two's extension says. The head is a `snapshot_v10` payload
([ADR 0108](../decisions/0108-the-version-ten-snapshot.md)).

## Application lifecycle

### Info

Info returns:

- application data: ASCII `protocol-stack`, unchanged;
- application version: ASCII `10.0.0`;
- application protocol version: unsigned integer `10`;
- the durable height, timestamp, and state root, as version two returns them.

**A version-ten bridge refuses an Info answer whose application protocol version
is not `10`**, as a protocol failure. This is new, and it is what names a
mismatched pairing. The engine calls Info first on every start, so a
version-ten bridge connected to a version-nine application is refused on its
first frame. The refusal names the fault, rather than surfacing as a receipt
version on some later block. See [Why the frame stays at version two](#why-the-frame-stays-at-version-two).

### Init chain

InitChain compares version two's four values against the validated version-ten
genesis. The expected application state is `"protocol-stack-v10"`, so a
version-nine deployment's `"protocol-stack-v9"` is an invalid request.
Initialization stays idempotent before the first committed block and reads no
clock.

### Check transaction

Unchanged in rule. Admission is version ten's: exact decoding, chain comparison,
sender derivation, and strict signature verification, mapped to codes `0` to `3`
as version one maps them. Kind 23 is admitted here like any other kind. A
version-nine kind 10 is four octets short of version ten's body, so it is refused
as `MALFORMED_TRANSACTION`, which is `economy-transition-v10`'s compatibility
boundary seen from the mempool.

### Prepare proposal and process proposal

Unchanged. The candidate execution is version ten's block transition against a
copy of the durable head. The kernel's timestamp-condition count is still 6, and
an implementation must still assert it.

### Finalize block

Per-transaction results are version one's scheme over version ten's result
space:

| Kernel outcome | ABCI code | Data |
| --- | ---: | --- |
| admitted and execution success | `0` | exact canonical receipt |
| malformed transaction | `1` | empty |
| wrong chain | `2` | empty |
| invalid signature | `3` | empty |
| admitted, execution result `r` in `1..49` | `256 + r` | exact canonical receipt |

The mapped range is `257` through `305`. Codes `257` through `300` keep their
version-nine meanings, and `301` through `305` are
[`economy-transition-v10`](economy-transition-v10.md#result-codes)'s five:

| Result | Name | ABCI code |
| ---: | --- | ---: |
| 45 | `LAUNCH_KEY_RETIRED` | `301` |
| 46 | `MACHINE_KEY_NOT_FOUND` | `302` |
| 47 | `MACHINE_NOT_ACTIVE` | `303` |
| 48 | `REGISTRATION_LIMIT` | `304` |
| 49 | `APPROVAL_LIFETIME_EXCEEDED` | `305` |

Code zero uses an empty codespace, and every nonzero code uses
`protocol-stack-v10`. **Each receipt is version ten's**: its version octets are
`10`, and its result byte stays at offset 39, because version ten keeps version
nine's receipt layout. A receipt whose version octets are not `10`, or whose
result byte does not produce the code beside it, is never written.

Statuses `7` and `8`, the separation of C5 from this path, and the absence of a
status for either tolerance condition are version two's, unchanged.

### Commit

Unchanged.

## Why the frame stays at version two

**The frame version names the frame's shape, and version ten changes no
shape.** Every request and response payload is version two's, octet for octet.
Version one's frame carried three ledger versions, one, seven, and eight. The
defect [ADR 0079](../decisions/0079-the-version-nine-application-contract.md)
found was a payload that changed shape while the field stayed still, and that is
not this case.

**The ledger is named by two fields that already exist.** Info's application
protocol version names it on the first frame of every start, and each receipt's
version octets name it on every executed transaction. Version two's lesson was
that a mismatch should be refused where it is first visible and in terms that
name it. The Info rule above does that for a version-ten bridge.

A version-nine bridge was built before this contract and does not check Info. So
a version-nine bridge serving a version-ten application is refused in three
places:

- a version-nine launcher takes the chain identity from
  `protocol-application-v9 --genesis-identity`, which refuses a 182-octet
  genesis, so it writes no CometBFT genesis for one;
- on a fresh chain, InitChain's `"protocol-stack-v9"` is refused by the
  application;
- on a restarted chain, the bridge refuses the first version-ten receipt by its
  version octets, as a protocol failure.

A block with no transactions carries no receipt, so the last of these is not the
first frame. The pairing exists only while both versions are built, and ADR 0104
step 7 ends that.

## Unsupported ABCI features

Version one's list is unchanged. Query returns code `1` with codespace
`protocol-stack-v10` and no state data.

## Versioning and migration

Application protocol version `10`, local frame version `2`, codespace
`protocol-stack-v10`, the decision space, the status space, and every
result-code mapping in this document are frozen for the version-ten network. A
change to any of the things version two names as requiring a new contract
version requires one here too.

**Versions one, two, and three coexist as documents.** Each remains the record
for the network it describes, and none is edited by a later one.

## Compatibility boundary

**Frames.** A version-two frame and a version-three frame are the same frame.
Which ledger an application drives is announced by Info, not by the header.

**Genesis and identity.** A version-nine canonical genesis is 150 octets and is
refused by a version-ten application, and the converse holds. The two chain
identities, roots, and application states differ.

**Results.** Codes `257` through `300` mean what they meant under version two.
Codes `301` through `305` are new, and a version-nine bridge refuses them, because
its receipt check admits 45 result codes and version nine's receipt version only.

**What is not claimed.** No accepted vector, digest, receipt, root, or recorded
devnet result of any earlier version changes, and none is recomputed under this
contract.

## The drift this document found

**Version two says Info's application version is ASCII `9.0.0`, and the Go
bridge has always sent `1.0.0`**, for version nine as for version one. Nothing
reads the value: it is informational, CometBFT does not use it in consensus,
and no devnet check compares it. So the drift was invisible. The slice that
accepts this document repairs the bridge to send `9.0.0` for version nine,
because the contract is the record and the code was what disagreed with it.
[ADR 0110](../decisions/0110-the-version-ten-application-contract.md) records
it beside ADR 0079's lesson: reconcile a contract against the code that
implements it, not against its own prose.

## The founder-decision gate this document ran

**Thirteen decisions were enumerated before any was judged**, and every one is
delegated.

**Seven are fixed by accepted specifications** and were cited rather than chosen:
the ledger, the 182-octet genesis, the chain-identity label, the five result
codes, and the receipt version are `economy-transition-v10`'s; the mapping
`256 + r` and everything inherited are version two's.

**Six are mechanism, framing, naming, and document shape**, which the founder
constitution places outside the reserved set: a new contract version rather than
a rebinding; the frame version; the application version string and protocol
version; the application-state string; the codespace; and the Info check a
version-ten bridge makes.

Nothing here sets or changes supply, allocation, beneficiaries, Founder
ownership, creator hierarchy, commercial routing, AI institutional authority,
bridge scope, content permanence, or what an end user must do, own, run, or
receive. The one participant-facing requirement at this boundary, a roughly
correct clock in order to vote, is version two's and is inherited unchanged.

## Required evidence

Version two's list applies, over a version-ten chain. Its C++ half is owed by
the application and transport, and the rest by the node, the Go adapter, and the
devnet, ADR 0104 step 6.

**The application and the transport:**

- the restart run's five contiguous blocks, driven through the application and
  over the wire across a restart before every block, reproduce every recorded
  root, block identifier, and stamp. Its fifth block's kind-23 registrations
  succeed, which shows the build authority key reached a reopened application;
- a version-ten result reaches the top of the range end to end, as result `49`
  under ABCI code `305` with its receipt;
- the encoder writes a receipt whose result is `49` under code `305` and refuses
  a version-nine receipt and a result byte of `50`;
- InitChain refuses version nine's application state;
- every decision, status, ordering, tolerance-boundary, clock-count, replay,
  and socket case version two lists for the C++ side.

**The node, the adapter, and the network:**

- the node process `protocol-application-v10` and its headless test;
- the Go client's conversions, its Info check, the codespace, the application
  version string, and the launcher's `app_state`;
- the version-ten devnet runs, with the HUB test verifier moved onto version
  ten.
