# ADR 0036: Economy transition v4 — HUB as the identity root

- Status: Accepted
- Date: 2026-08-15

## Context

[ADR 0035](0035-founder-answers-on-payout-the-cap-and-hub-recovery.md) records
the founder direction that HUB verification is the ecosystem's single source of
truth for identity and its recovery layer, and that HUB signing is what adds a
Founder Seat address. It also records the two questions that had to be settled
before that direction could be encoded. The owner settled both on 2026-08-14:

- **buying a Founder Seat requires HUB verification first**, and the seat is
  tied to that HUB identity; and
- **a HUB identity's set of addresses lives in consensus state**, with HUB
  signing adding and removing members.

A third answer confirmed the accumulation limit as time since the last
collection, which is what `economy-transition-v3` already measures.

Together these decide `economy-transition-v4` completely. This ADR records what
follows, what was rejected, and what the change costs.

## Decision

### A HUB identity holds a public key, and that key is the proof of the person

A HUB registration records a 32-byte public key. Every later proof that a
particular person is acting — purchasing, activating, minting under protection,
removing that protection, adding a seat address, adding or removing an ordinary
address — is an Ed25519 signature by that key over a domain-separated message
that names the identity.

The Founder Constitution supplies the shape: "Each verification produces a
signature unique to that person, derived from their personal secret, usable
across ecosystem and blockchain operations," and states that the cryptographic
construction is engineering work. A recorded public key is the consensus-visible
form of that sentence.

**The alternative was to make every proof an ecosystem-verifier attestation**,
as version three does — the chain holds one verifier key and the verifier signs
each action after a fresh check. It was rejected for two reasons. It makes the
verifier a precondition for actions the constitution insists it must not gate,
which version three already had to concede for protected mints. And it cannot
express recovery: an attestation says "this person passed a check", not "this
person authorized *this*", so nothing distinguishes a founder recovering their
own seat from the verifier acting on their behalf.

**The verifier therefore signs exactly one thing: a HUB registration.** That is
the one judgement no chain can make — that a live, distinct human stands behind
an identity. Everything after it is the person's own key.

This is a stronger containment story than any earlier version. Version two could
say the verifier gated entry to the economy and never payment; version three
weakened that, because a seat with protection switched on made verifier
availability a precondition for its own income. Version four restores it in
full and widens it: an unavailable verifier stops new people joining and stops
no participant already inside from doing anything at all.

### The seat is owned by a person, not by an address

The seat record's `biometric_identity_hash` becomes `hub_identity_hash`, at the
same width. `purchaser_account_id` is retained as the historical record of which
address bought the seat and carries no authority: authority is the manager set,
ownership is the identity.

**A third party may still submit and pay for a purchase.** Version three allowed
it, with a verifier enrollment signature binding the purchaser; version four
allows it with the purchaser's own signature over the exact seat and account.
Requiring the sender to *be* the purchaser was considered and rejected: it
removes a capability nothing asked to remove, and the HUB signature already
prevents registering a seat against another person's identity.

**Purchase loses the 32-byte biometric identity hash.** The seat's identity is
the purchaser's HUB identity, which the chain reads from the registry rather
than being told, so the field has nothing left to carry. The 64-byte signature
stays and changes hands: the verifier's enrollment signature becomes the
purchaser's own. The largest transaction in the protocol falls from 325 bytes to
293.

### The per-human seat bound becomes enforceable, so it is enforced

`economy-transition-v3` records that the constitution's 1,000-seat limit "is not
enforced by any transition here, because enforcing it requires knowing that two
biometric hashes belong to one human, which is exactly what the chain cannot
see." With one identity per person in state, it can. The identity record carries
a `seat_count`, purchase increments it, and a purchase that would exceed 1,000
is `SEAT_LIMIT`.

**This is a founder-directed rule reaching consensus for the first time**, not a
new rule. It is the reason the answer to "must a buyer be HUB verified first"
was worth asking rather than assuming.

### Self-referral becomes checkable

Version three compares two account identifiers, so a buyer could refer
themselves from a second address they control. Version four compares two HUB
identities, and one person has exactly one, so the constitution's intent is
enforced rather than approximated.

### Referral earnings are keyed by identity

The referral balance moves from `account_id` to `hub_identity_hash`, and any of
a person's addresses may collect it.

This is forced rather than chosen. The whole point of the recovery direction is
that losing an address loses nothing; a balance keyed by an address would be the
one place it still did. It also means a referrer's accrued value survives every
address change, which is what a 731-cycle benefit needs.

### An address set, with the forward direction in state

A HUB address entry maps an account to its identity. That is the direction every
transition needs — is this account verified, and whose is it — and it is one
lookup. The reverse, enumerating a person's addresses, is not needed by any
transition and is left to a read-side index; a node can scan.

**Removal unlinks and moves no value.** The account keeps its balance, its
nonce, and its ability to transact. Making removal move assets was rejected
outright: it would make a HUB signature able to take funds from any address it
names, which is a far larger authority than the direction grants and which
nobody asked for.

**Removing an address does not remove it from a Founder Seat.** Seat addresses
are permanent and add-only by founder direction. The two sets are separate, and
an address unlinked from its identity keeps whatever seat authority it held.
This is stated in the specification because it is surprising, directed, and not
inferable.

**Three kinds accept any sender**, which is deliberate: kinds 9, 11, and 12 are
exactly the transactions a person must be able to make when they hold none of
their own addresses. The signature is the authority and the sender only pays
the fee.

**Sixteen addresses per identity**, matching the manager bound the owner
approved, and an identity may hold zero — a person who has removed every address
can still add one, because kind 11 is authorized by the HUB key rather than by
an address. Both counts are state rather than derived, for the reason ADR 0034
gives for `manager_count`: a bound enforced by iterating a key prefix inside a
transition is an implicit cost two implementations disagree about.

### Everything the settlement does is unchanged

The accumulation cap and its window measurement, the cycle-assignment record and
its seat-ID-indexed bitmaps, the bounded mint walk, the carry identity, the
empty-winner rule, and the two-cycle lag are version three's, field for field.
The owner's third answer confirmed the cap's measurement, so nothing there
moves.

The founder's own statement of the capped cycle is adopted in the assignment
prose: a cycle a seat cannot collect because it is full **is** a cycle it
failed, which makes both consequences follow from rules already written.

## Consequences

**`economy-transition-v3` stays in place, passing, and unedited.** Its 579
vectors and their digests remain the accepted record of 2026-08-14, and
`simulation/economy_transition_v3/` continues to implement it. A version-four
model is a sibling package on the test ADR 0029 states.

**Requirement 10's target is now settled and the kernel is unblocked.** The C++
implementation targets version four. Nothing further is expected to move it: the
two questions that blocked version four were the last founder-reserved items on
this surface apart from `direct_issue_authority`, which refuses one transaction
kind rather than blocking a milestone.

**The identity milestone inherits a specified interface rather than a blank
page.** M4 must build HUB capture, liveness, unlinkability, retention, and the
construction of a person's key. What it no longer has to invent is what the
chain expects: a registration attested by the verifier, a per-person public key,
and eight message constructions.

**Every guarantee version four adds rests on the verifier's attestation.** One
person one identity, the per-human seat bound, and self-referral refusal are all
exactly as strong as the claim that the verifier registered a distinct live
human. The specification says so plainly rather than presenting them as
properties of the chain.

## Compatibility and independent review

No accepted artifact changes. Versions one through three, their vectors, models,
and digests remain in place, passing, and unedited. A version-four chain is a
new chain: distinct genesis schema, distinct chain-ID label, distinct state-root
label and version, and a root required to collide with none of its three
predecessors.

Four claims need review before value depends on them.

**That removing the second factor for a seat address is an acceptable trade.**
Version three requires a key the founder already holds *and* a fresh biometric
approval to add a seat authority. Version four requires only the HUB signature,
so that a founder holding no keys is not locked out. A coerced or spoofed HUB
signature can therefore add an address to a seat, and seat addresses are
permanent. This is the sharpest new risk in the contract.

**That one identity layer can carry uniqueness and recovery at once.** ADR 0035
raises this and version four makes it concrete: the same key proves a person is
distinct, gates referral entry, bounds seats per human, and recovers a lost
seat. Uniqueness wants a binding that cannot move; recovery requires one that
can.

**That the HUB key's own loss is survivable.** The chain has no transition that
rotates a HUB public key. A person who loses the secret behind it loses every
proof version four depends on — their seats' recovery path included — and the
only remedy the chain offers is none. Whether rotation belongs in consensus, and
under what authority, is a founder decision that version four does not make and
that a reviewer should raise early.

**That the ecosystem verifier's narrower reach is the right narrowing.** It now
signs registrations alone, so a compromised verifier key admits false people and
cannot touch anyone already inside. The mirror of that is that it cannot help
anyone either: there is no verifier-assisted recovery for a lost HUB key,
because there is no path by which the verifier can act for an existing identity.
