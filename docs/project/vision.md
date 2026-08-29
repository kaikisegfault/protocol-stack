# Vision

## North star

Build the complete sovereign ecosystem defined by the
[Founder Constitution](founder-constitution.md): one internal native economy,
permanent Founder infrastructure that is the ecosystem's **only**
infrastructure, approved immutable applications, bounded AI authority running on
that same infrastructure, and a narrow connection to outside value.

The project owns the complete path from deterministic protocol rules through
the reference node, ecosystem services, public interfaces, and operational
release. It advances through independently runnable milestones rather than
pretending that every layer already exists.

## What sovereignty means

Sovereignty means owning:

- the canonical state transition and one-native-asset guarantees;
- Founder Seat, issuance, revenue, treasury, escrow, and authority rules;
- controlled application admission and execution;
- reproducible builds, releases, upgrades, recovery, and compatibility;
- replaceable consensus, storage, networking, AI, bridge, and hardware
  boundaries;
- the ability to replace infrastructure without rewriting valid economic or
  application history; and
- the ecosystem's entire operating surface, with no company-operated server or
  hosted service anywhere inside it.

It does not mean inventing cryptography, databases, compilers, or every
infrastructure primitive from scratch. Original protocol meaning is combined
with audited and replaceable lower-level components.

## Economic direction

The ledger recognizes one native asset with an intended permanent maximum of
56,993,950,100 display units. It provides no public asset creation, burn,
unrestricted contract deployment, or general wrapped-asset balance.

That maximum was revised upward from 55,743,940,100 on 2026-08-07 to fund the
doubled Founder referral channel, while the project is still research software
and nothing has been issued. The figure becomes immutable at genesis.

Founder Node issuance, capped direct-mint programs, commercial revenue,
transaction fees, treasuries, and escrows follow the founder-directed channels
in the constitution. Exact consensus behavior is specified, simulated, and
reviewed before implementation; a direction document is not a production
parameter activation.

**100% of the node distribution's mint permissions are assigned and nothing is
ever stranded.** An indivisible remainder and a cycle nobody won enter a
recovery pool, and the earliest subsequent cycle with any winner takes the whole
of it. Whether a founder then mints is their own business; an uncollected
permission is theirs to leave uncollected.

**Ranking the best performers is permanent infrastructure rather than an
artifact of the 731-cycle distribution.** A machine whose distribution has
finished keeps operating, keeps being ranked, and stays eligible for any pool
that still holds value. The seats inside their own 731 cycles generate the
permissions; every operational seat that met its duty competes for them. Periods
that a participant experiences as months are real calendar months.

## Founder infrastructure direction

Exactly 100,000 permanent Founder Seats may be sold. Every active Founder
service runs the same integrated Linux-delivered stack:

- a full blockchain node;
- validator capability under the deterministic active-set protocol;
- application compute, storage, caching, and delivery services;
- an open-weight model served continuously, for both the ecosystem's judgment
  and the founder's personal assistant;
- the local HUB verification service and its vaults;
- workload and health agents; and
- later, the immutable NodeOS and dedicated physical Founder hardware.

Consensus signing remains bounded and deterministic even though every Founder
Machine carries validator capability. Resource scheduling places approved
application workloads across suitable nearby machines with replication,
caching, backup, and recovery. There is no general public infrastructure rental
market.

**The operator's responsibility is to run the software, and nothing else.** The
machine is one sealed plug-and-play process with no intervention surface, so a
software defect is not the founder's fault: if the machine was running and the
requirements were met, the founder is still paid for the cycle and the fix ships
to the whole fleet. Intervention voids this.

**The machine specification is founder-directed, because it decides who can
afford to participate.** Per machine: a Xeon-class server tier for hosting and
services, and separately at least 512 GB of unified memory for the open-weight
model, which an operator may rent rather than own. Every seat eventually
receives the same machine whatever its seat price was, funded from pooled sale
proceeds rather than from that price.

## Company infrastructure direction

**The Founder Machine is the only infrastructure the ecosystem ever uses.** The
company operates no server, no hosted service, and no external infrastructure of
any kind, from the beginning rather than after a migration. Every website,
frontend, backend, application, and ecosystem service runs on Founder Machines.
Where the company needs capacity it buys Founder Seats and runs Founder Machines
like anyone else.

The refusal is absolute because a shrinking backend never shrinks. Not building
the first one is the only enforceable version of this rule.

## Application direction

The ecosystem admits complete projects through AI review and supports at most
one product-creator layer within each project. Applications use a controlled
runtime and native protocol capabilities. Arbitrary public contracts and
secondary assets are excluded.

Creators publish updates through reviewed new versions rather than direct
production access. Ledger and accepted application history are not deleted.
Every creator-economy project or product includes a useful native-asset
spendable element.

## AI direction

**Every Founder Machine runs an open-weight model continuously, and the company
runs no AI infrastructure of its own.** This reverses the original direction,
which placed one logical ecosystem AI on company-operated data centres and said
Founder Nodes do not run AI models. The premise of that direction expired:
open-weight models now carry this work, and a unified-memory machine or rented
equivalent hosts one continuously.

The Ecosystem AI is therefore the population of Founder Machines rather than a
service. It stays one logical authority in the sense that matters — one
framework, one policy set, one decision per matter — while the inference that
produces a decision happens on whichever machine is assigned. A judgment is made
by the machine nearest the requester after its nearest neighbours reason, up to
six of them, so seven models reason and one signs. It performs delegated
case-specific work such as venture and grant review, milestone evaluation,
bounded escrow management, developer programs, and moderation.

**Biometric verification also runs locally**, on the founder's own machine in a
sandboxed offline environment, and the local model is the process's integrity
monitor rather than its verifier: the verdict is deterministic software, and the
model judges whether the run was honest.

**AI inference still cannot decide consensus**, and moving it onto the machines
cannot change that. Two models disagree, so an AI output is never the consensus
state; it is a signed, bounded claim that deterministic protocol rules verify by
scope, source, amount, policy version, expiry, and replay. AI outage pauses
AI-managed decisions rather than transferring judgment to a human or community
vote.

**Each Founder identity also has one personal assistant**, with one name, one
profile, and one accumulated understanding of that person. Its concurrency is
the seat count: a hundred seats buy a hundred parallel sessions of one
assistant, not a hundred identities.

The company controls the model, the framework, the protocol, and the update
schedule during an initialization stage of roughly one to two years, and a
founder never chooses which model or framework their machine runs at any point.
Authority is delegated gradually by explicit scope; at the end of initialization
a self-improving model is deployed and everyone including the company renounces
total control to it, while deterministic chain services stay deterministic.

## External-value direction

One controlled bridge joins Founder Seat purchase, liquidity provision,
native-asset swaps, and withdrawals to BTC, ETH, and approved stablecoins.
Foreign assets remain outside the internal economy and cannot be transferred
or spent as ledger currencies.

**The bridge runs on Founder Machines and depends on nothing outside them.**
Each participating machine runs its own light client for the external chain —
headers and proofs verified against that chain's own consensus, never a
third-party endpoint, because an input arriving from a company outside the
ecosystem is exactly the dependency this architecture refuses. Inbound value is
observed independently by a quorum of machines, each against its own light
client. The attesting set is the validator set, so the bridge introduces no new
class of trusted party.

The bridge is a required end-state component but a late production
implementation because external custody needs a dedicated threat model and
independent audits.

## Program boundaries

`protocol-stack` owns protocol specifications, the deterministic kernel,
reference node, economic and authority models, adapters, controlled runtime
interfaces, and operational tooling.

Large service implementations may later live in separate repositories when a
clear versioned boundary improves safety or maintainability. NodeOS, dedicated
machines, custom hardware, and independent connectivity are later programs;
they remain part of the complete direction without turning the current
monorepo into an undifferentiated codebase.
