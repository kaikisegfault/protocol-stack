# ADR 0041: A Founder Seat is tied to the identity, not to an address

- Status: Accepted
- Date: 2026-08-15

## Context

[ADR 0040](0040-holder-addresses-and-revocable-signers.md) was accepted with one
conflict left open: Founder Seat addresses are permanent and add-only, signers
are revocable, and both cannot hold for a seat. Three readings were recorded and
none recommended, because the choice appeared to decide what a founder can lose.

The owner resolved it by naming what the add-only rule was *for*.

## The resolution

**The add-only rule was never about addresses. It was about non-sellability.**
Seat addresses were made permanent so a seat could not be handed to someone
else. That was the purpose; permanence of an address was the mechanism chosen
to serve it at a time when an address was the only durable thing a seat could be
attached to.

**Mandatory HUB verification supplies a better mechanism for the same purpose.**
The seat is permanently tied to the HUB verified data itself. **There is
therefore no address related to a Founder Seat at all**, and with no seat
address there is nothing for the add-only rule to govern. The conflict does not
need resolving between two rules; one of them has no subject.

**A person cannot sell what they cannot transfer.** A biometric identity is not
assignable, so seat ownership cannot move. Two parties may still privately
negotiate management, and the direction states the limit plainly: **they cannot
take over.** The HUB-verified owner remains in charge and in full control, and
can revoke any signer at any time. What the protocol prevents is transfer of
ownership; what it does not and should not try to prevent is a private
arrangement between consenting people.

**Legacy succession is the one path by which a seat's identity changes**, and it
runs through the recorded legacy instruction on the HUB record rather than
through an address.

## The uniform model

There is now one model for every participant — Founder Seat owner, user,
developer, or creator — and it is the foundational layer for authentication,
security, and wallet and transaction management:

- **HUB verified data is the single source of truth** for authentication into
  the ecosystem, and the mandatory entry step for account creation.
- **Asset-holding addresses behave like personal escrows.** A person creates,
  manages, and deletes as many as they want. They are not tied to a seat and
  carry no ownership meaning.
- **Signer keys are assigned to those escrows separately** and are fully
  flexible — several per escrow, revocable at any time.
- **Security options are per escrow and per financial operation**, and fully
  customisable by the person.

## Consequences

**Two accepted rules are superseded, and both are superseded by having their
purpose served better rather than by being reversed.** The permanence and
add-only nature of seat addresses is gone with the concept, and the 16-manager
limit goes with it — a seat has no manager set, only an owning identity whose
escrows and signers are bounded like everyone else's.

**One accepted rule needs restating rather than superseding, and the next
specification must settle it.** ADR 0033 fixed that minted value lands on the
address that signed the mint, so that a recovered address could receive. Under
this model a signer holds no funds, so "the address that signed" is no longer a
destination. The purpose that rule served — a founder who regains access can
receive — is now served automatically, because regaining an identity regains its
escrows. What must be specified is which escrow a mint credits. **The derivation
is that the mint names a destination escrow and the chain checks it belongs to
the minting identity**, which follows from a person having many escrows and none
being privileged. It is recorded as a derivation rather than adopted silently,
because ADR 0033 fixed the original by founder decision.

**Requirement 12's storage bounds move.** Per-seat manager entries disappear;
per-identity escrow and signer entries replace them, and their bound is now a
per-person figure rather than a per-seat one.

**What is still open is unchanged by this ADR**: how a brand-new person pays for
their genuine first action, the derivation of a keyless holding address against
`protocol-primitives-v1`'s public-key-hash account identifier, and an ordering
rule for two signers on one escrow.

## Compatibility and independent review

No accepted artifact changes on this commit. Versions one through five, their
models, vectors, verifiers, and the version-four C++ codec remain in place,
passing, and unedited.

Two claims need review.

**That non-sellability actually holds.** It holds against transfer of ownership,
which is what a chain can enforce. It does not prevent a founder from handing
signer keys to a buyer and biometrically approving whatever that buyer asks, and
the direction accepts this: the owner stays in control and can revoke, so the
arrangement is revocable rather than final. Whether a revocable private
arrangement is materially different from a sale is a question about people, not
about the protocol.

**That tying a seat to a biometric identity does not strand it.** A seat now
depends entirely on one identity remaining provable. No transition rotates a HUB
public key, so a person who loses the secret behind it loses the seat with it,
and legacy succession is the only recorded path by which a seat's identity ever
changes. That was a review item for identity generally; it is sharper here,
because a seat is a 731-cycle entitlement rather than a balance.
