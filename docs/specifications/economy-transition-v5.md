# Economy transition v5

Status: Accepted M3 consensus transition contract; model, vectors, and
implementation not yet recorded

This document defines the version-five Founder Economy consensus transition. It
is [`economy-transition-v4`](economy-transition-v4.md) with **one field's
meaning corrected**, because version four's kind 11 names an identity it does
not carry and therefore has no conforming implementation.

The change is classified as encoding and authority.
[ADR 0037](../decisions/0037-economy-transition-v5-the-kind-eleven-identity.md)
records the defect, the two candidate repairs, and why the chosen one closes a
second hole as well.

## Relationship to version four

[`economy-transition-v4.md`](economy-transition-v4.md) is not edited, retracted,
or reinterpreted, and `test-vectors/economy-transition-v4.txt` remains normative
and passing. Version four's own versioning section fixes its twelve kind
identifiers and their bodies as immutable and says that a changed field or
semantic rule "requires a new transition version and an ADR; it must not
reinterpret a version-four identifier". Correcting kind 11 reinterprets exactly
such a field, so it is a new version rather than a repair. That rule was written
one slice before it applied, and applying it to its author's own defect is the
point of having written it.

**Everything else in version four carries over unchanged and is incorporated by
reference**: the envelope factoring and the kind-1 byte identity, the shared
80-byte header and 16-byte trailer, the admission order and its three codes, all
twelve kind identifiers and every other body, the economy state key space and
its value encodings, the beneficiary space, the RFC 9162 tree shape, the genesis
field table and its 21,843-entry bound, the receipt layout, the twenty-six
result codes and their meanings, the accumulation cap and its window
measurement, the cycle-assignment record, the bounded mint walk, the carry
identity, and every ordered rejection condition of every kind but one.

## The defect

Version four's kind 11, `hub_add_address`, has this body:

| Offset | Size | Field |
| ---: | ---: | --- |
| 80 | 32 | account ID |
| 112 | 64 | HUB signature |

Its ordered rejection conditions open with "an unregistered `hub_identity_hash`
is `NOT_HUB_VERIFIED`", and the message its signature covers binds
`chain_id || hub_identity_hash || account_id || u64(valid_until_height)`.

**The transaction never carries that identity hash, and the chain cannot derive
it.** Version four makes the sender deliberately unconstrained, and says why:
"a person who holds none of their linked addresses can still act". So there is
no linked sender to resolve the identity from, and trying every registered
identity's public key is neither a canonical rule nor a bounded one.

No conforming implementation of kind 11 therefore exists, and the consequence is
precise: **a founder who has lost every address has no way back**, which is the
one guarantee the founder direction of 2026-08-14 was answered into the contract
to provide.

## The correction

Kind 11's 32-byte field is the **HUB identity hash**, and the account being
linked is the **sender**:

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 32 | HUB identity hash | 32 octets |
| 112 | 64 | HUB signature | Ed25519 over the address-add message |

The body stays 96 octets, the message keeps its shape, and kinds 11 and 12 still
share a length. What changes is what the field means and where the account comes
from.

```text
address_add_message =
  D("protocol-stack:v5:hub-address-add") ||
  chain_id || hub_identity_hash || sender_account_id || u64(valid_until_height)
```

Rejection conditions, in this order:

1. an unregistered `hub_identity_hash` is `NOT_HUB_VERIFIED`;
2. a **sender** already linked to any identity is `REPLAY`;
3. an identity already holding 16 addresses is `ADDRESS_LIMIT`;
4. a HUB signature that does not verify over the add message, against that
   identity's recorded public key, is `UNAUTHORIZED`.

On success the transition links the sender to the identity and increments
`address_count`.

**This closes a second hole, and that is why it beats the obvious repair.** The
obvious repair is to add an identity field beside the account, widening the body
to 128 octets. It works, and it leaves squatting open: with the account named in
the body and any sender permitted, anyone may link *another person's* address to
their own identity, after which condition 2 refuses that person's own
registration forever. Requiring the sender to be the address added makes
squatting unrepresentable — a person can only add an address they can sign
from — and recovery is unaffected, because a person creating a fresh account
controls it by construction.

**The cost is that recovery needs a funded account.** The sender pays the fee,
so `SENDER_NOT_FOUND` and `INSUFFICIENT_BALANCE` apply as they do to every
kind, and a person recovering from total address loss must reach a first payable
balance before they can act. That is the bootstrap dependency version two
recorded and the bridge milestone owns; it is not new here, and it is stated
because recovery is the path it now sits on.

**Kind 12 is unchanged.** It names the account to unlink and derives the
identity from that account's existing entry, which is canonical and
unambiguous — and removal must not require signing from the address being
removed, because a compromised address is exactly the one an operator most wants
to unlink.

## Version identity

Version five is a different chain from version four, as version four is from
version three. Every label and schema version that separates one contract's
commitments from another's takes `v5`:

| Construction | Version five |
| --- | --- |
| chain ID | `protocol-stack:v5:chain-id` |
| state root | `protocol-stack:v5:state-root`, version field `5` |
| economy tree | `protocol-stack:v5:economy` |
| genesis schema version | `5` |
| receipt version | `5` |
| HUB message labels | `protocol-stack:v5:…`, all eight |

The two transaction signing labels stay at `protocol-stack:v1:` for the reason
every version since two has given: the kind byte and the chain ID are inside
every signature preimage, and re-versioning would destroy the kind-1 byte
identity for separation the preimage already carries.

## Compatibility boundary

**Transaction bytes.** A version-one signed transfer is a version-five kind-1
transaction, byte-for-byte, with the same signing message, transaction ID, and
execution result numbers. A version-one node presented with kinds 2 through 12
rejects them at admission step 1 as `MALFORMED_TRANSACTION`.

**A version-four kind-11 transaction is a valid version-five kind-11
transaction by shape and a different one by meaning**, which is precisely why
the chain identity differs: the two are alternative chains, a transaction is
bound to one by the chain ID inside its signature preimage, and no version-four
byte sequence is ever executed under version-five rules.

**Roots and genesis.** The version-five state root and chain ID have distinct
labels and version fields from all four predecessors, so no earlier root is
reinterpreted and no version-five root collides with one. There is no upgrade
block and no state translation.

**What is not claimed.** No accepted M1, version-two, version-three, or
version-four vector, digest, receipt, root, or recorded devnet result changes,
and none is recomputed under this specification.

## Versioning and compatibility of this document

Everything version four fixes as immutable is immutable here too, with kind 11's
field taking its corrected meaning. A changed field, code, order, or semantic
rule requires a new transition version and an ADR.

Versions one through five coexist as documents; every earlier artifact remains
in place, passing, and unedited.

## What this specification does not establish

Everything version four does not establish is inherited unchanged: direct-channel
eligibility and the refusal of kind 6; that a HUB identity is a distinct human,
which rests entirely on the ecosystem verifier's attestation; what a coerced HUB
signature can do; that removal moves no value; verifier key rotation; the
payment behind a seat purchase; the bootstrap; distribution; the unreferred
pool's payout; and that any of it executes.

**One further limit is new and belongs to this version.** Version five makes
kind 11 implementable; it does not demonstrate that the recovery path works end
to end, because nothing executes any transition yet. That demonstration is the
execution model and the transition trace, and it is the slice this defect
interrupted.

## Required vectors and evidence

`test-vectors/economy-transition-v5.txt` is normative. It fixes everything
version four's file fixes, under version five's labels, and adds the three
things this version exists to record:

- **kind 11's corrected body**, with its 32-byte field read as an identity hash
  and its width unchanged at 96 octets;
- **the address-add message**, built from the identity and the sender rather
  than from the identity and a body field; and
- **that the version-four and version-five constructions differ everywhere a
  chain is separated from another** — chain ID, state root, economy tree — over
  identical inputs, each version-four construction first required to reproduce
  its own accepted vectors so the comparison is against the real one.

The kind-1 identity is checked against `test-vectors/protocol-primitives-v1.txt`
as in every version since two, and the settlement is checked against
`test-vectors/economy-transition-v3.txt`, which version four already established
as the file that keeps an imported settlement honest.

**None of that is recorded yet, and this document is accepted without it.**
Every earlier transition contract arrived with its model and its vectors in one
slice; this one does not, because it exists to correct a defect in the contract
the repository currently calls newest, and recording that correction is more
urgent than recording it with its evidence. The model, the vector file, its
verifier, and the C++ codec update are the next slice, and until they exist
version five is a specification whose claims rest on reading rather than on a
passing check.

Acceptance of those artifacts requires full GitHub-hosted verification on the
exact commit that adds them.
