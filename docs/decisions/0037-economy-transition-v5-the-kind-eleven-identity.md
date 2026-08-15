# ADR 0037: Economy transition v5 — the kind-eleven identity

- Status: Accepted
- Date: 2026-08-15

## Context

[`economy-transition-v4`](../specifications/economy-transition-v4.md) and
[ADR 0036](0036-economy-transition-v4-hub-as-the-identity-root.md) were accepted
on 2026-08-15, and the C++ codec for them merged the same day. The next slice
was the execution model — the first thing that would have to run the
transitions in their specified order rather than encode their bytes.

Writing it stopped at kind 11.

## The defect

`hub_add_address` carries `account_id(32) || hub_signature(64)` and nothing
else. Its ordered rejection conditions open with "an unregistered
`hub_identity_hash` is `NOT_HUB_VERIFIED`", and the message its signature covers
binds `chain_id || hub_identity_hash || account_id || u64(valid_until_height)`.

The transaction never carries that identity hash, and the chain cannot derive
it. Version four makes the sender deliberately unconstrained and states the
reason — "a person who holds none of their linked addresses can still act" — so
there is no linked sender to resolve. Trying every registered identity's public
key is neither canonical nor bounded.

**No conforming implementation of kind 11 exists.** The consequence is not a
missing convenience: a founder who has lost every address has no way back, which
is the exact guarantee the founder direction of 2026-08-14 was answered into the
contract to provide.

The defect is checkable from the accepted document alone — the body table has no
identity field and both the conditions and the message require one — so it needs
no model to demonstrate. What it needed was something that had to execute the
conditions in order.

### Why the codec slice could not have caught it

M3.9a implements bytes, not transitions, and its cross-language check compares
recorded bytes. The vectors fix `message.hex.address_add`, which is built from
an identity supplied as an argument, and nothing in a codec ever asks where a
transaction gets that argument. The gap was invisible to the encoder, to the
decoder, and to both implementations agreeing with each other.

**That is the general lesson and it is worth recording plainly.** Byte-level
cross-language agreement proves that two implementations encode the same thing.
It cannot prove that the thing is executable, because neither implementation
executes it. The repository's own order — specification, model, vectors, C++ —
is what surfaces this class of defect, and it surfaced this one at the first
step that runs anything.

## Decision

**Kind 11's 32-byte field is the HUB identity hash, and the account being linked
is the sender.** The body stays 96 octets, the message keeps its shape, and
kinds 11 and 12 still share a length. What changes is what the field means and
where the account comes from.

Rejection condition 2 changes with it: a **sender** already linked to any
identity is `REPLAY`.

### The rejected repair, and the second hole the chosen one closes

The obvious repair is to add an identity field beside the account, widening the
body to 128 octets and leaving everything else alone. It works.

It also leaves squatting open, and that is why it was rejected. With the account
named in the body and any sender permitted, anyone may link **another person's**
address to their own identity. Condition 2 then refuses that person's own
registration forever, and there is no removal transition they can call, because
removal is authorized by the identity the address is linked to — which is the
attacker's. A stranger could permanently deny an address its own identity.

Requiring the sender to be the address added makes that unrepresentable: a
person can only add an address they can sign from. Recovery is unaffected,
because a person creating a fresh account controls it by construction.

**The cost is that recovery needs a funded account**, since the sender pays the
fee. That is the bootstrap dependency version two recorded and the bridge
milestone owns. It is not new, and it is stated because recovery is the path it
now sits on.

### Kind 12 is unchanged

It names the account to unlink and derives the identity from that account's
existing entry, which is canonical and unambiguous. Symmetry with kind 11 was
considered and rejected: removal must not require signing from the address being
removed, because a compromised address is exactly the one an operator most wants
to unlink.

### A new version rather than a repair in place

Version four's versioning section says a changed field or semantic rule
"requires a new transition version and an ADR; it must not reinterpret a
version-four identifier". This reinterprets the 32-byte field at offset 80 of
kind 11, which is squarely what that sentence forbids.

The argument for repairing in place was considered: the field has no
implementable meaning, so there is no behaviour to preserve and nothing
deployed to break. It was rejected on the rule's own wording and on precedent.
ADR 0034 repaired a version-two figure in place and was careful to say why that
was allowed — "no byte, code, order, or rule moves" — and here a rule does move.
A rule written one slice ago, overridden the day after by its author to save a
version, is a worse precedent than the version costs.

**No recorded byte changes as a consequence.** Version four's vectors, model,
and C++ codec remain in place, passing, and unedited; version five's artifacts
are new files beside them.

## Consequences

**The version-four codec in the kernel now targets a superseded contract.**
Updating it is the next slice rather than this one, exactly as version four's
model preceded its codec. Nothing is wasted: the envelope, the messages, the
receipt, the state keys, the trees, the roots, and genesis are unchanged in
shape, and what moves is a set of labels and one field's meaning.

**The execution model this defect interrupted is still the slice after that**,
and it is now unblocked against a contract that can be implemented.

**Version five makes kind 11 implementable and demonstrates nothing about
recovery end to end**, because nothing executes any transition yet. That
demonstration is the transition trace, and it should exercise the recovery path
specifically: a person with an identity, no linked addresses, and a fresh funded
account adding one.

## Compatibility and independent review

No accepted artifact changes. Versions one through four, their vectors, models,
digests, and the C++ codec remain in place, passing, and unedited.

A version-five chain is a new chain: distinct genesis schema, chain-ID label,
state-root label and version field, economy tree prefix, and HUB message labels.
A version-four kind-11 transaction is a valid version-five kind-11 transaction
by shape and a different one by meaning, which is precisely why the chain
identity differs — a transaction is bound to one chain by the chain ID inside
its signature preimage.

Two claims need review.

**That requiring the sender to be the added address is the right trade.** It
closes squatting and it means recovery cannot be performed by a third party on
someone's behalf — a helper cannot add an address for a person who cannot
transact at all. Whether that matters depends on how a person reaches a first
payable balance, which is bridge work.

**That no comparable gap remains in the other eleven kinds.** Each was checked
against its own body while writing this: every identity a condition or a message
names is either carried by the transaction, derived from the sender's address
entry, or recorded in the seat the transaction names. Kind 11 was the only one
that could name none of those. That check was done by reading, and the execution
model is what will confirm it by running.
