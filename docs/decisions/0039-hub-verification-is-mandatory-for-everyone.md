# ADR 0039: HUB verification is mandatory, and an address is not an identity

- Status: Accepted
- Date: 2026-08-15

## Context

M3.9c closed by asking the owner one question about the recovery path version
five encodes: a person who has lost every address must obtain a small amount of
native currency on a fresh address before they can link it, because the sender
pays the fee and version five requires the sender to be the address being added.
The question offered three flows, two of which involved a helper submitting or
funding the transaction.

**The owner rejected the premise of all three.** The answer is not a choice
among helper flows; it is that the architecture underneath the question is
wrong, and the moment to correct it is now, before more contract versions are
built on it.

## The direction

Recorded as given on 2026-08-15.

**HUB verification is mandatory for anyone who wants to register, and for
interacting with any part of the ecosystem.** It is the single source of truth
for registration, account holding, and security. There is no unverified
participation.

**An address is not an identity root.** A wallet address becomes an additional
tool the owner holds for operations and transactions. The main verificator is
the person's HUB biometric facial data, recorded on chain permanently and
immutably.

**Recovery is direct, between the owner and their own recorded biometric data,
with no third party.** A person who has literally lost everything registers
again and goes through HUB verification; the system detects that this biometric
identity already exists on chain, and the person immediately regains access to
the existing account. They then attach a new wallet address to their HUB
identity and continue operating. No friend, no helper, no external funding step.

**Biometric confirmation is on by default for every financial transaction and
every mint**, as a one-time-password layer over the whole ecosystem.

**Users may customise that, and the customisation is theirs.** They may set a
minimum amount below which it is not required, set time windows, or turn it off
entirely, so each person configures their own security posture.

**The owner named the trade and accepted it.** This is less flexibility and a
higher barrier to entry. What it buys is more security, more simplicity, fewer
vulnerabilities, and one source of truth for who owns an account — and it
resolves, once, a family of account-related bugs and edge cases rather than
handling them one contract version at a time.

## Why the previous architecture produced the question

Version four made HUB the root of identity **for Founder Seats**, and left
ordinary participation rooted in addresses. Version five then had to decide who
may link an address to an identity, and every available answer was bad in some
direction: naming the account in the body opens squatting, and requiring the
sender to be the account means a person holding nothing cannot act.

That dilemma is a symptom. It exists only because an address can exist,
transact, and hold value without an identity behind it, so the chain has to
reason about linking two things that were separately real. **When registration
is HUB-first for everyone, the address is created under an identity that already
exists, and there is nothing to link in the sense version five had to solve.**

## What this does not change

**No accepted artifact is retracted.** `economy-transition-v2` through
`economy-transition-v5`, their models, vectors, verifiers, and the version-four
C++ codec stay in place, passing, and unedited, exactly as every superseded
version before them. Version five's evidence, merged the same day, is what makes
its successor's carryover check possible at all.

**The M1 devnet is untouched.** It runs `protocol-primitives-v1` transfers and
implements none of this.

## Consequences

**The next contract version is not the C++ codec.** The recorded next action was
M3.9d, updating the kernel codec from version four to version five. That is now
the wrong next step, on the precedent M3.8a set and M3.9b repeated: a kernel
written against a contract already known to be superseded is work that has to be
done twice. The next slice is the specification that encodes this direction.

**Three things this direction requires are not yet decided**, and they are
recorded in `founder-constitution.md` rather than invented here. The first
blocks the next slice.

1. **How a person who holds nothing pays for anything.** The direction says
   recovery involves no helper and no external funding. Every transaction on a
   chain costs a fee paid by a sender, so either identity transactions are
   fee-exempt, or the fee is drawn from value the identity already holds on
   chain, or registration and recovery are performed by the company-hosted HUB
   service rather than by the person's own wallet. Each answer changes what a
   participant must do and own, so none is engineering's to pick.
2. **How far "mandatory for any interaction" reaches into the transfer.** Whether
   an unverified address may still *receive* native units, or whether both ends
   of a transfer must be verified, decides whether the kind-1 byte identity
   carried unchanged since M1 gains an authorization condition.
3. **What "turn it off entirely" means for a seat.** Version three made
   biometric-on-mint a per-seat option with a deliberate asymmetry — enabling it
   needs only an address signature, disabling it needs a biometric approval, so
   a stolen key can neither mint against a protected seat nor remove the
   protection first. A user-configurable global policy has to preserve that
   asymmetry or knowingly drop it.

**Two consequences follow that are engineering's to work out**, and are recorded
so the next slice does not re-derive them: the per-identity security policy is
state rather than a per-seat flag, and a mandatory-verification chain makes the
genesis verifier key load-bearing for the very first account, which sharpens the
rotation question ADR 0032 already recorded as reserved.

## Compatibility and independent review

**Every guarantee in this direction rests on the ecosystem verifier's
attestation that a registration is a distinct, live human, and is exactly as
strong as it.** That was true of version four and is now true of the entire
ecosystem rather than of Founder Seats alone, because there is no longer an
unverified path. The constitution's existing threat-model, unlinkability,
retention, liveness, coercion, false-acceptance, and breach requirements apply
to the widened scope and remain unmet.

Three claims need independent review before value depends on them.

**That one biometric layer can carry both uniqueness and recovery.** Uniqueness
wants a binding that cannot move; recovery requires one that can. ADR 0036
recorded this for seats; it now applies to every participant.

**That a mandatory-verification ecosystem is reachable.** Requiring verification
of everyone means the verifier is on the critical path of every first
interaction, which is the containment property version four was careful to buy
back and this direction spends again — deliberately, and with the trade stated.

**That no transition rotates a HUB public key.** A person who loses the secret
behind their recorded key loses every proof the ecosystem depends on, and the
chain offers no remedy. This was a review item for seats; it is now a review
item for everyone.
