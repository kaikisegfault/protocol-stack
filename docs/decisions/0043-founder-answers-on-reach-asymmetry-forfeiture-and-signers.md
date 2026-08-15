# ADR 0043: Founder answers on transfer reach, the asymmetry, forfeiture, and signer binding

- Status: Accepted
- Date: 2026-08-15

## Context

The founder-decision gate ran on M3.10a — the slice that specifies
`economy-transition-v6` — and **stopped it**. Thirty-six decisions were
enumerated before any was judged; thirty-two were delegated by
[ADR 0039](0039-hub-verification-is-mandatory-for-everyone.md) through
[ADR 0042](0042-the-hub-entry-airdrop-and-the-verified-user-rate.md) and the
constitution, six were deductions from decided principles, and four were
founder-reserved. Two of the four had been listed under **Explicitly unresolved
founder details** since the pivot was recorded, filed as blocking nothing on
their own; enumerating the slice is what showed they sit inside the contract
rather than beside it.

The owner answered all four on 2026-08-15.

## The direction

Recorded as given.

### 1. Verification is the entry point, and it reaches the recipient

**"If a user is not registered into the blockchain ecosystem and did not
complete HUB verification, they cannot interact with the ecosystem in any way —
no wallets, no transactions, nothing. It is the entry point."**

The question was specifically about the passive side: whether an unregistered
person may *receive* native units without doing anything themselves. The answer
covers it, because there is nothing to receive into — an unregistered person has
no wallet, so no account of theirs exists for a transfer to name.

**Version six therefore refuses a transfer whose recipient is not a registered
escrow.** `ledger-transition-v1` creates an absent recipient with nonce zero on
transfer, and versions two through five carried that unchanged; it is withdrawn
for version six, because it is the one remaining way an account could come into
existence with no identity behind it.

**No account exists in version-six state that is not an escrow beneath a
registered identity.** That is now a structural invariant rather than a
convention, and it is what makes "there is no unverified participation" a
property the chain enforces rather than a policy the ecosystem observes.

### 2. The security asymmetry generalises to every participant

Version three gave a Founder Seat's mint protection a deliberate asymmetry:
enabling it needs only an address signature, disabling it needs a biometric
approval, so a stolen key can neither mint against a protected seat nor remove
the protection first. ADR 0039 made the posture per-person and switchable off,
and the constitution required the new policy to preserve that asymmetry or
knowingly drop it.

**It is preserved, and widened to everyone.** One rule covers every escrow, every
operation, and every seat:

- **relaxing a posture requires a biometric approval** — turning confirmation
  off, raising the minimum amount below which it is not required, or widening a
  window in which it is not required;
- **tightening a posture requires only a signer signature.**

The asymmetry stops being a Founder Seat feature and becomes the ecosystem's
rule, which is the same direction of travel ADR 0041 took with the seat address:
a protection invented for seats turns out to be the general case.

### 3. A forfeited verified-user incentive is never issued

ADR 0042 subjects the verified-user daily permission to the same thirty-window
accumulation cap as every other permission, and the cap forfeits what is not
collected in time. Every other channel has a recorded destination for that
value — a failed or capped seat's permission goes to the day's best performers by
[ADR 0033](0033-founder-decisions-minting-hub-and-referral-entry.md), and a
capped referral routes to the unreferred pool by
[ADR 0034](0034-economy-transition-v3-managers-cap-and-hub.md).

**The verified-user channel has none, and none is invented.** Value a verified
user does not collect within the cap is **never issued**. Total supply ends below
the founder-directed maximum by exactly what was not collected.

`economy-transition-v6` records the mechanism this implies, which is narrower
than "the value sits somewhere unclaimed": the channel has no accrual step and
therefore no `outstanding` term at all, so uncollected value is never represented
in state rather than being represented and left alone. The channel satisfies an
inequality against its cap where every other channel satisfies an equality.

That is the collect-or-lose rule the owner already chose for referrals, applied
where there is nobody to give the forfeited value to. It rules out the two
alternatives on their costs: splitting among that day's collecting users would
require ranking a population of up to 1,000,000 identities inside a block, which
is the one place this economy has no bounded winner set; and routing to the
unreferred pool would issue value allocated against one channel's cap under
another channel's accounting.

### 4. One signer key is assigned to exactly one escrow

ADR 0040 said signers are generated separately, assigned to holding addresses,
and revocable, without settling whether one key may serve several escrows.

**It may not.** A signer key belongs to exactly one escrow.

## What this settles

**All four blockers, and the constitution's unresolved list loses two entries.**
M3.10a is unblocked and no founder question stands between the repository and
`economy-transition-v6`.

**The kind-1 transaction bytes survive a fifth version, and its behavior does
not.** Answer 4 lets the chain resolve the paying escrow from the signer alone,
so the version-one 80-byte header needs no escrow field and kind 1's body stays
40 octets — the accepted 136-byte unsigned and 200-byte signed transfer are
still reproduced byte-for-byte. Answer 1 then gives that unchanged byte sequence
a new rejection condition. **The two facts must be stated together in the
specification**: a version-one transfer to a fresh recipient succeeds under
version one and is refused under version six, so the byte identity is preserved
while the execution identity is not, and the compatibility boundary must say so
in those terms rather than claiming the transfer carried over.

**Answer 4 also bounds a compromise.** A stolen signer key reaches exactly one
escrow, and revocation of that key affects nothing else. The cost is that a
wallet holds one key per escrow; it is derived automatically and invisible in
use, but it is a rule about what a participant must hold, which is why it was
asked rather than assumed.

## What it does not settle

**Everything already open stays open**: eligibility and anti-abuse for the
liquidity-mining, impermanent-loss, and mystery-box channels, which keeps kind 6
specified and refused; legacy inactivity bounds and contested-successor
behavior; stablecoin allowlist governance; the AI frameworks; and verifier key
rotation.

**How a posture change is encoded is engineering**, and so is the rule that
decides whether a particular change relaxes or tightens. The specification must
make that decidable from the two stored postures alone rather than from intent,
because a chain cannot read intent: a change is a relaxation when it could
reduce the set of operations that require confirmation.

**Answer 3's accounting statement is made precisely in
`economy-transition-v6`**, and it came out narrower than this ADR first put it:
the channel has no `outstanding` term to leave value in, so the identity is
`outstanding = 0` and `issued <= cap` rather than a conservation equality.

## Consequences

**Version six gains one structural invariant and one rejection condition.** Every
account is an escrow beneath a registered identity; a transfer naming a recipient
that is not one is refused, most naturally with the existing `NOT_HUB_VERIFIED`
code rather than a new one.

**The per-seat `mint_requires_biometric` flag disappears** into the per-identity
posture, which is where ADR 0039 already said the policy belongs. The asymmetry
that flag carried survives as a general rule, so nothing is lost by removing it.

**No accepted artifact changes on this commit.** Versions one through five, their
models, vectors, verifiers, and the version-four C++ codec remain in place,
passing, and unedited.

## Compatibility and independent review

Two claims need review before value depends on them.

**That refusing an unregistered recipient is reachable in practice.** It makes
the ecosystem verifier's availability load-bearing for the first interaction of
every participant, which ADR 0039 already recorded and this sharpens: there is
now no path by which value reaches a person who is not already inside, so a
verifier outage stops onboarding completely rather than mostly. The entry airdrop
is what keeps the barrier low; it does not make the verifier optional.

**That the generalised asymmetry does not strand a person.** Relaxing a posture
requires a biometric approval, and no transition rotates a HUB public key. A
person who has locked themselves into a strict posture and then loses the secret
behind their HUB key cannot loosen it, and their escrows keep requiring a
confirmation they can no longer produce. That is the same review item ADR 0039
and ADR 0041 both record, reached from a third direction, and it is the strongest
argument that HUB key rotation eventually needs a founder answer.
