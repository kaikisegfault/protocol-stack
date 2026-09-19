# ADR 0082: The version-two frame is the first to use the field that announces a shape change

- Status: Accepted
- Date: 2026-09-19
- Bounds: [ADR 0079](0079-the-version-nine-application-contract.md)
- Follows: [ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md),
  [ADR 0081](0081-the-version-nine-owning-store.md)
- Relates to: `include/protocol/application/wire_v2.hpp`,
  `src/application/wire_v2.cpp`

## Context

[`consensus-application-v2`](../specifications/consensus-application-v2.md)
moves the local protocol version to `2`. That is one octet, and it would not
deserve an ADR except for what M3.19a found while writing the contract: **the
field has never been used.**

Version seven added a block identifier to the finalized-block response. Version
eight kept it. The protocol version stayed at `1` through both, and no contract
document recorded the change. The consequence is not a misparse — both decoders
are correct — but the refusal lands in the wrong place. A version-one reader
paired with a version-eight writer refuses the finalize response **at the result
count, as a generic protocol failure, on the first block**, rather than at the
header, as an unsupported version, on the first frame.

So version two is the first version of this protocol whose version field does the
job the field exists for, and this slice is where that becomes true rather than
merely written down.

## Decision

### 1. The version becomes `2` and the header does not otherwise move

The magic stays `PSAP`, the header stays 20 octets, and the direction,
request-id, payload-cap, kind, and error rules are version one's. The version is
a value in a field, not a new frame.

The frozen header bytes are pinned as **bytes** in the suite rather than compared
against the constant that produced them. A test that encoded with
`kWireVersionV2` and then asserted the octet equalled `kWireVersionV2` would pass
against any value, including `1`.

### 2. Two request payloads gain a timestamp, and a third deliberately does not

Kind 2 gains `genesis_timestamp:u64` **before** `app_state`, because every
fixed-width field precedes the one variable-length field — version one's own
layout rule, and what lets a decoder bound a frame before it allocates. Kinds 5
and 6 gain `timestamp:u64` after `height`, in the order the durable head reports
the two.

**Kind 4 does not gain one, and the suite checks that it did not.** PrepareProposal
names no block: under CometBFT the stamp is the engine's, and
`economy-transition-v9` requires the proposer's algorithm for choosing a value to
stay unconstrained. A port that added a stamp to every block-shaped payload would
have added one here, so the absence is a case rather than an omission.

### 3. Version two is a module of its own, not a version parameter on version one

The obvious alternative was to parameterise `wire_v1` by accepted version and
call it twice. It is refused because version one and version eight are
**delivered and frozen**, and parameterising their decoder means editing it: the
change that makes version two reachable is the same change that could make
version one accept a frame it did not accept before. A staged migration
([ADR 0065](0065-a-kernel-replacement-may-be-staged-across-a-stack-migration.md))
already pays for coexistence, and this is the form the payment takes here.

**What is shared is everything that is genuinely one fact.** The header size, the
magic's meaning, the direction and kind enumerations, the wire-error set, the
frame and header structs, and the three unchanged request payloads are declared
once in `wire_v1.hpp` and used from `wire_v2.hpp`. A second declaration of any of
them would be a second place for a framing rule to be wrong — which is the
argument `response_v8.hpp` already makes about this same frame, and it still
holds for the parts that did not change.

What is copied is the primitive reader and the payload decoder, because those are
what version two edits. The duplication is bounded by the deletion already owed:
`wire_v1` goes when `src/v8/` does.

### 4. The raw-input bound is derived from the kernel, not restated

`kMaximumBlockInputsV2` is `v9::kMaxRawInputs`, with a static assertion that it
still equals version one's `kMaximumBlockInputs`. The two are the same number
today. Deriving it means that a version which moved the kernel's bound stops this
file compiling instead of leaving a transport that admits a block the kernel will
refuse.

This is [M3.13r](../project/delivery-log.md)'s receipt-prefix lesson applied
before the fact rather than after: a figure that moves with a version is either
checked on the happy path or it needs a boundary case, and a figure *derived*
from its source needs neither.

## The finding

**The cross-version refusal had to be tested in both directions, and only one of
them is the direction this slice created.**

That version two refuses a version-one frame is the new behavior and the obvious
case. That version one refuses a version-two frame is the behavior that makes the
change *useful* — it is the deployment failure the field exists to name — and it
required no code at all, because version one already compares against its own
constant.

A suite that tested only the new direction would have proved that version two is
strict and proved nothing about whether the drift is closed. The pair is checked,
including a version-one finalize frame carrying a whole well-formed version-one
block body, which is refused on its **sixth octet** rather than at the result
count several fields later. That case is the one that states the whole point of
the version: the body never reaches a payload decoder.

## Consequences

**The next slice is `ApplicationV9`, `response_v9`, and `dispatcher_v9`**, which
are what version eight delivered as one piece in M3.13r and what this frame now
has somewhere to carry. `consensus-application-v2`'s required-evidence section is
their acceptance criteria.

**Nothing about version seven's or version eight's recorded behavior, vectors, or
committed roots changes.** The drift was in the document, not in the bytes, and
this slice adds a module rather than editing one. `wire_v1` is untouched.

**Two wire fuzz targets run where there was one.** Version two's seeds a *block
request* rather than version one's empty Info frame, because that is the payload
that gained a field and therefore the one whose decoder has something to get
wrong.

## Owed

**A response encoder.** This slice delivers the request half of the frame — the
decoder a server needs. The four changed responses, the `decision:u8` byte, and
statuses `7` and `8` belong to `response_v9`, which needs `ApplicationV9`'s types
to exist and is therefore the next slice's rather than a gap in this one.
