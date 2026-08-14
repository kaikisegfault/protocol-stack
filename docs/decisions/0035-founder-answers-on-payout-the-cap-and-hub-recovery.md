# ADR 0035: Founder answers on mint payout, the cap, managers, and HUB recovery

- Status: Accepted
- Date: 2026-08-14

## Context

`economy-transition-v3` and
[ADR 0034](0034-economy-transition-v3-managers-cap-and-hub.md) were accepted on
2026-08-14. That slice settled two questions by deducing them from decided
principles rather than by choosing between answers, and both decide who is paid,
so both were put to the owner for confirmation rather than assumed. Two further
questions were asked in the same batch: an engineering default the slice had
already implemented, and one founder-reserved decision the slice had
deliberately left unenforced.

The owner answered all four the same day. Three confirm what version three
encodes. The fourth does not, and it reaches further than the question asked.

## Decision

### A mint credits the address that signed it

Confirmed as specified. Any recorded manager address may collect, and the value
lands on that address ready to spend. This is what makes adding a verified
address a working remedy for a lost key, and it is the reason version three
cannot keep version two's containment property that a stolen key could only ever
mint to the seat's own account. The optional biometric on minting is the
replacement, and its switch is asymmetric so a thief cannot remove it.

### A capped cycle is a failed cycle

Confirmed, and the owner's framing is better than the specification's. Version
three says the winner set is the seats at the highest uptime among those that
met the cycle **and are under the accumulation cap**, and separately that a
capped seat's permission is reallocated. The owner states it as one rule: a seat
that has hit the limit and cannot collect is treated, for that day, exactly as a
seat that failed the daily requirement.

Both consequences then follow from rules that already exist rather than from a
new predicate. The day's generation goes to the best performers, because that is
what happens to a failed cycle. And the capped seat cannot be one of those best
performers, because the Founder Constitution already says a winner must itself
have met the cycle and a failed seat never rewards another failed seat.

**The behaviour is identical and nothing is re-encoded.** The accrued set, the
winner set, the reallocated count, the split, the carry, and every recorded
vector are unchanged; version three's own derivation reached the same place by a
longer route. The specification and ADR 0034 adopt the shorter statement, which
is a wording change to an accepted document rather than a contract change — the
same class as the storage figure ADR 0034 repaired in version two.

**What the cap does not touch is what a seat has already earned.** The owner was
explicit that a capped seat is "sitting full": its accumulated unminted value is
intact and waiting, and what it loses is the new days it did not make room for.
One press of the button restores both the balance and the eligibility.

### Sixteen manager addresses per seat

Confirmed as an engineering default.

### HUB verification is the recovery layer, and it is what adds a seat address

This is new direction and it supersedes version three.

**HUB verification is the single source of truth for identity, and losing an
address does not lose it.** Once a person is registered, they can regain access
at any time by signing in through HUB, including when the address the
verification was originally tied to is gone. The owner described it as an
ecosystem-wide universal one-time-password layer: once registered, it is what
makes managing addresses, assets, and security matters straightforward across
the whole system.

**For ordinary ecosystem accounts, a verified person may add and remove their own
addresses through HUB.** That makes a HUB identity a set of addresses rather than
a single one, and makes HUB signing the authority over that set.

**Founder Seat addresses are the stated exception.** They are permanent, they can
never be removed, and HUB signing is what adds another. Version three already
refuses removal, which this confirms. What it does not do is admit the addition:
version three requires an existing manager's signature *and* a verifier
approval, so a founder who has lost every manager key has no path at all. That
is the gap this direction closes, and closing it is a change to an authorization
rule, which requires `economy-transition-v4`.

## Consequences

**`economy-transition-v3` is superseded in one place and needs a version four.**
It is not edited beyond the wording adopted above: its 579 vectors and their
digests are the accepted record of what the hosted matrix verified on
2026-08-14, and a changed authorization rule is a new version rather than an
edit — the rule ADR 0024 and ADR 0026 established.

**The kernel slice waits for that version four**, on the precedent M3.8a set
when the founder decisions of 2026-08-13 moved requirement 10's target: the
encoding revision comes before the implementation, because a kernel written
against a contract already known to be superseded is work that has to be done
twice.

**One founder-reserved question is answered and a different one is opened.**
Whether a person may hold more than one HUB registration is now effectively
settled in the negative — recovery removes the reason to re-register — but the
shape that replaces it is not specified. Two things must be decided before
version four can be written, and both change what a participant must do:

- **whether buying a Founder Seat requires HUB verification first**, so that the
  seat is tied to a HUB identity the chain can check a later address addition
  against; and
- **whether a HUB identity holds a set of addresses in consensus state**, which
  is what "add and remove your own addresses through HUB" means on a chain where
  an account is an address.

Both are recorded as blocking version four rather than answered here.

**The identity milestone widens again.** ADR 0033 made HUB an ecosystem-wide
identity layer serving every participant class. This adds recovery and address
management to it, which means HUB is not only an attestation the chain records
but an authority the chain honours. The threat model, unlinkability, retention,
and independent review requirements the constitution already records apply to
that widened role, and the coercion question sharpens: a HUB signature that can
add an address to a Founder Seat is a signature that can take one.

## Compatibility and independent review

No accepted artifact changes behavior. `economy-transition-v3`, its vectors, its
model, and every earlier contract remain in place, passing, and unedited except
for the capped-cycle wording, which changes no rule, byte, code, order, or
recorded value.

Two claims need review before value depends on them.

**That HUB recovery does not become a single point of compromise.** Version
three's manager rule needs two independent factors to add an authority: a key
the founder already holds and a fresh biometric approval. Making HUB signing
sufficient removes the first, deliberately, so that a founder who lost every key
is not locked out. A reviewer should establish what a coerced or spoofed HUB
signature can then do, because on a Founder Seat it can add an address and
addresses are permanent.

**That one identity layer can carry both recovery and uniqueness.** HUB is now
asked to prove that a human is distinct, to gate referral entry, to pay a
direct-mint channel, and to act as the recovery authority for addresses and
assets across the ecosystem. Those pull in different directions: uniqueness
wants a binding that cannot move, and recovery requires one that can.
