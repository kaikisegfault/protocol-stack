# Current operational goal: Founder identity, seats, and authority

Status: active from 2026-09-27, when M3 closed. Drafted from the roadmap's M4
scope and the accepted identity decisions under the standing delegation; the
owner may revise it.

## Objective

Make a Founder's identity, seat, and authority real on a running network. A
test Founder must be able to:

- enroll;
- activate a node;
- add and revoke a manager;
- exercise eligible economic rights;
- recover an address;
- complete tested legacy flows.

**No wallet key alone may ever rewrite identity.**

M3 made the economy consensus behaviour.
[`goals/m3-founder-economy-devnet.md`](goals/m3-founder-economy-devnet.md) is
its retained contract, and
[`founder-economy-devnet-audit-v1.md`](founder-economy-devnet-audit-v1.md) is
its evidence.

## What M3 already delivers

The version-nine chain already executes most of the identity surface, specified
from the founder decisions of August 2026 (ADRs 0039 to 0044):

- a HUB registration under the ecosystem verifier's signature (kind 10), with
  the entry airdrop;
- keyless escrows an identity creates and deletes (kinds 13 and 14);
- signers it adds and revokes, including under the HUB key when every signer
  is lost (kinds 15 and 16);
- a security posture per escrow (kind 17);
- a seat purchased and activated under the owner's HUB signature (kinds 2 and
  3), tied to the identity, never to an address;
- the 1,000-seat-per-person bound.

**What has never happened is a person using that surface on a network.** The
four-validator devnet registers, sells and activates a seat, and transfers. It
has never:

- added a signer;
- lost one and recovered;
- minted.

## Required evidence

Completion requires all of the following:

1. **A test Founder's lifecycle on the four-validator devnet**, with every
   replica agreeing on every root through a restart:
   - enroll;
   - buy and activate a seat;
   - add a signer, create a holding escrow, and revoke the signer;
   - lose every signer and recover under the HUB key;
   - transact again.
2. **Eligible economic rights exercised on a network.** A kind-4 mint and a
   kind-18 mint must execute on a network, which needs one of ADR 0071's two
   routes to a network past the assignment lag.
3. **The per-machine attestation-key registry** that
   [ADR 0048](../decisions/0048-hub-verification-runs-locally-with-an-ai-integrity-monitor.md)
   decided, replacing genesis's single verifier key in a new contract version.
   A registration is valid only under a key of an active, attested machine,
   or under the company-held launch key until the chain retires it (ADR 0100).
4. **A deterministic test verifier** as a replaceable component. It produces the
   signed decision envelopes the chain checks, behind the interface a
   production verifier will later implement.
5. **Sensitive-action authorization.** A specified envelope says which actions
   need a fresh HUB decision, with expiry and replay protection.
6. **Legacy succession mechanics**, as the constitution states them:
   - permanent versioned legacy statements;
   - successor nomination with an evidence reference;
   - supersession without deletion;
   - authority that stays stuck when no valid successor exists;
   - the original founder's superior right to reclaim.
7. **The separate threat model for local HUB verification** that ADR 0048 and
   the constitution require, naming what goes to independent review.
8. **Storage bounds** for every new state entry at 100,000 seats and
   1,000,000 identities.
9. **Cross-language vectors** that the C++ kernel and the independent Python
   model both reproduce, with negative, boundary, replay, and atomicity cases
   for every new transition.
10. **Accepted ADRs** stating each new transition's shape, encoding,
    compatibility boundary, and remaining independent review.
11. **Risk-proportionate GitHub-hosted verification** on the exact accepted
    commit, and a clean handoff naming the first M5 implementation slice.

## Founder-decision gate

These are founder-reserved and must not be invented:

- **Legacy limits.** The constitution reserves "exact inactivity limits,
  dispute evidence, conflicting statement precedence, and reclaim transitions".
  Requirement 6 builds the record and its mechanics. It asks for these values
  at the point each becomes the nearest dependency.
- **Inactivity**, and what an inactive seat or identity loses or keeps.
- **The launch key's cutoff.** How many active machines retire it
  (ADR 0100).
- **Verifier key rotation**, and who holds the build-signing authority before
  ADR 0047's end of initialization.
- **Seat payment.** A seat purchase's external payment proof: which chains,
  which assets, which prices. That is bridge scope, M9, and M4 specifies no
  proof source.
- **Production biometrics.** Any camera verifier, capture threshold, or
  uniqueness commitment. ADR 0048 names the stabilization scheme as an open
  dependency needing independent cryptographic review, and nothing is built on
  it until that review exists.

## Explicitly out of scope

- Production biometric capture and matching, and any fuzzy extractor or secure
  sketch.
- Real BTC, ETH, or stablecoin payment, custody, or bridge proofs.
- The all-in-one Founder Node package (M5), the Ecosystem AI's runtime (M6), and
  the wallet (M10).
- Any change to supply, allocation, beneficiaries, channels, or the economy's
  settlement rules.
