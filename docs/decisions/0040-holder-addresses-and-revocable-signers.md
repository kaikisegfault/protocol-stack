# ADR 0040: Holder addresses, revocable signers, and the identity as admin

- Status: Accepted as founder direction; one conflict unresolved
- Date: 2026-08-15

## Context

[ADR 0039](0039-hub-verification-is-mandatory-for-everyone.md) made HUB
verification mandatory and recorded one blocking question: how a person who
holds nothing pays for their first transaction. The owner's answer replaces the
account model the question assumed.

## The direction

Recorded as given on 2026-08-15.

**A HUB-verified identity may hold as many fund-holding addresses as the person
wants.** They are the place assets accumulate, and **they never change**.

**A holding address has no key of its own.** Signers are generated separately.
A person assigns one or more signer keys to any holding address, and may assign
new ones or several at once.

**The HUB identity is the admin.** It can add, remove, revoke, and modify
signers on any holding address beneath it. Regaining access on a new device
means regaining control of the holding addresses directly under the verified
identity; the person then revokes old signers and registers new ones as they
decide.

**Security posture is the user's to configure, per holding address and per
transaction.** They may turn biometric signing on or off, require multiple
signers, set thresholds, and set whatever other conditions the protocol offers.

**Registration is the mandatory step for account creation**, and the verified
identity is the single source of truth for registering, modifying, and managing
anything, with admin access. A person reaches their funds with their face from
any device.

## What this settles

**The recovery fee question ADR 0039 recorded as blocking is answered for
recovery.** Maria does not arrive at an empty address. Regaining her identity
regains her holding addresses, which already hold value, so there is something
to pay from and no third party is involved. That was the whole difficulty and it
dissolves.

**The version-five dilemma dissolves too, for a second reason.** Version five
had to decide who may link an address to an identity. Here an address is created
*beneath* an identity that already exists and is never relinked, so there is
nothing to link and nothing to squat.

## What it does not settle

**A brand-new person's very first action still costs something.** Registration
itself, and the first holding address, come before any value exists. This is the
narrow residue of ADR 0039's question: not recovery, only genuine first entry.
The candidate answers are unchanged — a fee-exempt registration with a
non-monetary limit, or registration performed by the company-hosted HUB service.

**A keyless holding address is not an address in the version-one sense, and this
is the first direction that reaches the M1 compatibility boundary.**
`protocol-primitives-v1` derives an account identifier as
`H(D("protocol-stack:v1:account") || 0x01 || ed25519_public_key)` — an address
*is* a public key hash, and four contract versions have preserved that
byte-for-byte along with the kind-1 transfer. A holding address with no key must
be derived from something else, most plausibly the identity and an index. That
is engineering work, but it changes an accepted primitive rather than extending
one, and it should be specified deliberately rather than discovered.

**Two signers on one holding address need an ordering rule.** Version one gives
each account a single nonce sequence. Two signers acting concurrently on one
holding address race for it. Engineering, not founder, but it must be settled
before the encoding.

**Turning biometric confirmation off moves risk to the user, and the
constitution should say so plainly.** With it off and signer keys stolen, the
thief can move funds and the person's only recourse is HUB revocation, which is
a race against the thief. That is a legitimate posture for the person to choose;
it should be an informed one.

## The conflict this raises, which is founder-reserved

**Founder Seat addresses are permanent and add-only. Signers are revocable.
These are two rules for the same thing.**

The constitution states that a recorded manager address "remains in the
historical ledger forever", that Founder Seat addresses "are permanent, can
never be removed, and are add-only", and ADR 0035 records HUB signing as what
adds one — deliberately, so that a founder who lost every address still has a
path back to their seat. This direction says the identity may revoke a signer at
any time.

Both cannot hold for a Founder Seat. The reconciliation is not obvious and is
not engineering's to choose, because it decides what a founder can lose:

- if seat addresses become revocable signers like everything else, the
  permanence guarantee is withdrawn and a compromised HUB signature can remove a
  legitimate manager, not merely add one; or
- if seats keep permanent add-only addresses, the ecosystem has two address
  models and a person's seat behaves differently from the rest of their account;
  or
- the seat's *historical record* stays permanent while a signer's *authority*
  becomes revocable, which may be what "remains in the historical ledger
  forever" always meant — the ledger never forgets, but the key stops working.

The third reading is the one that appears to satisfy both sentences, and it is
recorded as a reading rather than adopted, because the owner fixed the original
rule.

## Consequences

No specification, model, vector, or implementation changes on this commit. The
direction is recorded so it is repository state rather than chat history; the
contract that encodes it is the next slice, and it is blocked on the conflict
above plus the narrowed first-entry question.

Every accepted artifact remains in place, passing, and unedited.
