# ADR 0051: Bridges run on Founder Machines, with light clients and a machine quorum

- Status: Accepted
- Date: 2026-08-19

## Context

The bridge is the only door value enters and leaves by, and it was the last place
in the design that appeared to need something outside the ecosystem. The question
is narrow and old: **how does the local chain learn that a deposit happened on an
external chain?** Most bridges answer with an oracle network, which is a
centralization and a repeatedly exploited one.

The owner's proposal on 2026-08-19: put the bridge on the Founder Machine. A
Founder Machine is already server infrastructure — capable of running services,
listeners, and broadcasters — so the oracle can be an ecosystem service rather
than an external dependency, and the ecosystem never reaches outside itself.

## Decision

### 1. The bridge runs on Founder Machines, and reads the external chain itself

Each participating Founder Machine runs the bridge's own components, including
its own connection to the external chain.

**It runs a light client, not a subscription.** The owner's first framing was a
webhook or event subscription on the external contract. A webhook is a push from
somewhere, and if that somewhere is a third-party RPC provider then the
ecosystem's most security-critical input arrives from a company that is not part
of it — which is exactly the dependency the architecture forbids, reintroduced
where it does the most damage.

A light client is the version that stays self-contained and is still cheap:
headers plus Merkle proofs, verified against the external chain's own consensus.
For Ethereum the sync-committee light client is small in state and bandwidth, so
the owner's requirement that this not be heavy is met by the mechanism rather
than by trusting somebody's endpoint.

### 2. Inbound value is attested by a quorum of machines

A deposit into the external contract is observed independently by **k of n**
Founder Machines, each verifying it against its own light client and signing an
attestation. The local chain mints the wrapped asset on the quorum, under
`ledger-transition-v1`'s ordinary rules.

This is the same trust model as everything else in the ecosystem — the attesting
set is the validator set — so the bridge introduces no new class of trusted
party. It is [ADR 0050](0050-the-block-timestamp-is-the-ecosystem-clock.md)'s
general rule applied to a second kind of real-world input.

### 3. Outbound value is the user's own transaction, broadcast by their wallet

A withdrawal is the user's transaction on the external chain, and the native
wallet broadcasts both sides — the local burn and the external release — in one
or two clicks, signing each.

This is a genuine ergonomic gain and it is worth building. It is recorded here
that it is **not** a security mechanism: the outbound half is authorized by the
user's own key and needs no attestation. The inbound half is the trust-bearing
one and the quorum is what secures it.

## Consequences

**A bridging Founder Machine runs an external-chain client per bridged chain.**
That is a real, recurring resource cost — state, bandwidth, and sync — and it
belongs in the machine specification rather than being discovered later. Not
every machine need bridge; the quorum is over participating machines.

**The stablecoin allowlist stays a policy decision.** Which assets are bridgeable
is a governance choice, and no amount of renouncement or automation answers it.
It remains open in the constitution.

**Nothing here is built now.** The bridge is a later milestone. This ADR fixes the
architecture so that the milestone does not arrive and quietly adopt an oracle
network for want of a decision. It also sits under a recorded sequencing
constraint: external purchasability must exist before the millionth identity
registers, because until then the entry airdrop is the only way a newcomer with
nothing can transact.
