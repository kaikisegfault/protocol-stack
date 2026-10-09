# ADR 0100: Founder answers on who verifies a person and how registration starts

- Status: Accepted
- Date: 2026-10-09
- Bounds: [ADR 0048](0048-hub-verification-runs-locally-with-an-ai-integrity-monitor.md),
  [ADR 0047](0047-the-founder-machine-runs-the-ecosystem-ai.md)
- Relates to: [`first-goal.md`](../project/first-goal.md) requirement 3,
  [`hub-verification-threat-model.md`](../architecture/hub-verification-threat-model.md)
  T3 and T8

## Context

ADR 0048 replaces genesis's single verifier key with a registry of per-machine
attestation keys. A registration is then valid only when an active, attested
Founder Machine signs it, and capture runs on the founder's own machine.

Two questions followed that the accepted documents do not distinguish between.
Each decides what a participant must do or own in order to join, so both are
founder-reserved. They were raised when requirement 3 became the nearest
dependency:

1. **Who verifies a person who owns no Founder Machine?** Ordinary users,
   creators, and developers must all be verified (ADR 0039), and most will own
   no machine. The threat model's T3 sharpened this. A HUB key derived from a
   face alone is only as secret as the face, so the derivation must also depend
   on a secret only an attested sandbox holds. The answer therefore also decides
   where that secret lives.
2. **How do the first registrations happen before any machine is active?**
   Buying a seat requires HUB verification first, and verification requires an
   active, attested machine, which requires a bought and activated seat.
   Something has to break that loop at launch.

## The answers

The owner answered both on 2026-10-09, choosing the recommended option each
time.

### 1. The nearest active machine verifies, and the secret is split

**A person who owns no Founder Machine is verified by the nearest active,
attested machine**, assigned the way an AI judgment is assigned under ADR 0047.
**Their vaulted key secret is split across several machines**, so they can
recover on any machine and no single machine holds it.

Rejected: a machine the person picks, which would let a dishonest founder create
false identities for everyone they onboard. Several machines agreeing, which is
slower and costlier and shows the capture to each. Company machines only, which
restores the chokepoint ADR 0048 removed.

### 2. Registration starts under an expiring launch key

**The chain launches with one company-held verifier key that signs the first
registrations.** Once a set number of machines are active and attested, the
chain refuses it for good. The owner chooses that number, and it is still open.

Rejected: letting the first founders verify themselves, with no outside check.
Starting from company seats, which still needs some first verification of the
company's own identity.

## What the answers mean for the chain

- **Any active, attested machine's registry key may sign a registration.**
  "Nearest" is an assignment made off chain, as an AI judgment's is. The chain
  cannot observe proximity and does not check it. A founder still verifies on
  their own machine, as ADR 0048 decided.
- **The split secret is not consensus-visible.** The chain sees only the HUB
  public key a verification produces. The threshold scheme belongs to the
  production verifier, and the threat model already lists it for independent
  cryptographic review. How many machines hold a share, and how many must
  cooperate, is specification work under that review.
- **The launch key is a genesis key with an on-chain end.** Registrations
  under it are valid until the count of active, attested registry machines
  first reaches the owner's number. At that moment the chain records the key as
  retired, so a later fall below the number never revives it. Version nine's
  `verifier_key` is that key's precursor, and the contract version that carries
  requirement 3 states the rule.

## What stays open

- **The number of active machines that retires the launch key.** It is asked
  when that contract version is specified, and no fixture value stands in for
  it in any accepted artifact.
- **A per-machine registration bound**, if the contract version adopts one
  (threat model T8). Its value is asked as well.
- Who holds and rotates the launch key and the build-signing key until then. It
  stays founder-reserved under `first-goal.md`'s gate.

## Consequences

**Until the launch key retires, it is the single chokepoint ADR 0048 set out to
remove.** Its compromise in that period admits people who do not exist, each
drawing the entry airdrop (threat model T8). The answer accepts that cost and
gives it a hard end the chain enforces, rather than an end someone must
remember to announce.

**Recovery never depends on one machine.** A person verified by a stranger's
machine can lose that machine and still recover, because the secret was never
on it alone. This is what makes "the nearest machine" safe to use for people
who own none.
