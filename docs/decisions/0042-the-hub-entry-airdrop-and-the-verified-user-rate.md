# ADR 0042: The HUB entry airdrop, and the verified-user rate

- Status: Accepted
- Date: 2026-08-15

## Context

[ADR 0039](0039-hub-verification-is-mandatory-for-everyone.md) recorded one
blocking question: how a person who holds nothing pays for their first
transaction. [ADR 0040](0040-holder-addresses-and-revocable-signers.md) answered
it for recovery — regaining an identity regains escrows that already hold value
— and left the residue: **genuine first entry**, where no value exists yet.

The owner resolved it from the tokenomics that were already there.

## The direction

**The first million HUB-verified users already have a daily incentive allocated
to them for two years**, through the `hub_verified_user_incentives` direct-mint
channel. Nothing about the total changes. What changes is how the first day of
it is delivered.

**On completing HUB verification for the first time, the chain issues that
person their first day's portion immediately, as an entry airdrop.** It arrives
without a mint and without a fee-paying account existing beforehand, and it is
what makes the new account able to transact at all.

**From the second day onward it continues exactly as the economy already
works**: a daily mint permission for the verified-user incentive, minted when
the person chooses, subject to the same thirty-window accumulation cap as every
other permission.

**After the first million users the problem does not recur**, because by then
bridges, swaps, and direct card purchases exist, and acquiring native units on a
new account is ordinary.

## The rate, which is derived rather than chosen

The owner supplied the population and the period: **the first 1,000,000 verified
users, daily, for two years.** The channel cap is already founder-directed at
1,250,010,000 display units. Those three figures determine the fourth exactly:

```text
125,001,000,000,000,000 atomic / 1,000,000 users / 731 cycles
  = 171,000,000 atomic = 1.71 display units per user per day
```

**The division is exact, and 730 cycles is not**, leaving a remainder of
420,000,000 atomic. So the period is 731 — the same figure as a Founder Seat's
issuance period — and the per-user daily amount is 1.71, which sits in the same
family as the economy's other founder-directed legs (171.0, 34.2, 17.1, 3.42).

That the three supplied figures reproduce the accepted cap to the atomic unit is
the evidence that this is the intended reading rather than a plausible one. The
rate is therefore **derived from founder-directed values, not invented**, and
the `hub_verified_user_incentives` rate leaves the unresolved list.

## Pre-mint was considered and rejected

The direction first described a pre-minted pool the airdrop would be paid from,
then refined it to issuing only the first day at registration and continuing
with permissions. The refinement is also the only option the constitution
permits: a conforming chain opens with **zero supply and zero accounts**, which
`economy-transition-v2` recorded as forced by the no-genesis-allocation rule. A
fully pre-minted pool would be a genesis allocation under another name.

Issuing per registration also keeps the channel's accounting identical to every
other channel — issuance is bounded by the cap and counted as it happens, rather
than committed up front against users who may never arrive.

## What this settles

**The last founder-reserved question in the milestone is closed.** A brand-new
person's first action is funded by the protocol itself, from an allocation that
person is already entitled to, with no helper, no third party, and no external
funding step. That is the same standard ADR 0039 set for recovery, now met for
entry.

## What the specification must still settle, as mechanism

**The order of credit and fee inside registration.** The airdrop and the
registration are one atomic execution, so the credit must be applied before any
fee is assessed against it, or registration must be fee-exempt. Either satisfies
the direction; the first is the smaller change and keeps the fee path uniform,
and 1.71 units is far above any plausible fixed fee. This is recorded so the
next specification chooses deliberately rather than discovering it.

**Who submits a registration.** The ecosystem verifier signs registrations and
is the only party that can attest one, so submission by the company-hosted HUB
service is the natural reading. The direction does not require it, and a
self-submitted registration works equally well once the credit-before-fee order
is fixed.

**The one-per-person bound on the airdrop.** The airdrop is paid on *first*
verification. One identity per person is exactly what HUB establishes and what
`economy-transition-v4` already enforces for seats, so the entry payment
inherits that guarantee rather than needing a new one. A re-registration after
an identity already exists is a recovery, not an entry, and pays nothing.

## Consequences

**Requirement 12 gains a figure and loses nothing.** The verified-user channel's
per-participant issuance is now bounded and computable: 171,000,000 atomic per
day per identity for 731 days, capped at 1,000,000 identities.

**The channel keeps one cap and one conservation identity.** The entry airdrop
and the daily permissions are issuance from the same channel against the same
founder-directed ceiling, so nothing in the manifest, the subtotals, or the
maximum supply moves.

## Compatibility and independent review

No accepted artifact changes on this commit. Versions one through five, their
models, vectors, verifiers, and the version-four C++ codec remain in place,
passing, and unedited.

One claim needs review. **An entry payment is an anti-abuse surface, and the
protocol's whole defence is that HUB establishes one identity per living
person.** A million entry payments are a million reasons to attempt a false
registration, so the constitution's existing liveness, unlinkability, coercion,
and false-acceptance requirements for the verifier are load-bearing here in a
way they were not when verification only gated a seat purchase. Recording the
requirement does not establish that face verification meets it.
