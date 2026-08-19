# Founder Constitution

Status: founder-directed target for the complete ecosystem; not a claim of
current implementation or production readiness

Last affirmed: 2026-08-07

## Purpose and authority

This document preserves the owner's product, economic, and authority intent so
that a clean development session can continue without reconstructing it from
chat history. It governs what the project is trying to build from its current
research state through a complete public ecosystem.

The requirements here are constitutional project direction. A rule described
as fixed or permanent is intended to become immutable in the production
protocol, but it is not an accepted consensus rule until an exact
specification, deterministic model, adversarial evidence, compatibility
decision, and applicable independent review exist. Current runnable behavior
is recorded separately in `current-state.md`.

When documents disagree:

1. this constitution controls founder intent;
2. accepted specifications and ADRs control behavior already implemented;
3. `current-state.md`, tests, and Git history control claims about what works;
4. research fixtures never silently become production policy.

Claude may autonomously research and select technical mechanisms that realize
this constitution. It may not change a founder rule, fill a missing economic
beneficiary or authority with its own product preference, or represent a
deferred choice as settled. A missing decision that would change ownership,
value distribution, permitted content, or institutional authority must be
asked of the owner when it becomes the nearest implementation dependency.

## End-state in plain language

The ecosystem is one connected economic and application environment:

- one blockchain-native asset supports every internal payment and incentive;
- permanent Founder Seats operate one all-in-one node and resource network;
- approved creators publish useful projects and products with spendable
  elements;
- users spend and participate through simple interfaces without needing
  blockchain terminology;
- developers improve the ecosystem through AI-managed incentive programs;
- one self-hosted ecosystem AI evaluates matters that require judgment while
  deterministic protocol rules contain its authority;
- a narrow bridge connects the enclosed economy to BTC, ETH, and approved
  stablecoins without turning them into internal currencies; and
- approved applications and their history remain available through the
  Founder resource network without creators or the company receiving a delete
  switch.

The system is developed through independently verifiable milestones, but the
public production launch is not considered complete until its mutually
dependent node, economic, application, AI, bridge, liquidity, wallet, and
operational foundations are usable together.

## Participants and authorities

### Founders

Founders purchase permanent stakeholder positions recorded as Founder Seats.
They keep the required machine running; they do not manually judge projects,
treasury requests, blocks, or other participants. Their all-in-one service
provides the blockchain node, validator capability, and ecosystem application
infrastructure.

Founders receive the constitutionally assigned issuance, commercial-revenue,
and transaction-fee benefits only under the applicable active-node rules.

### Creators

A project creator may submit anything from an idea to a working application.
The ecosystem AI evaluates the submission, funding plan, milestones, releases,
and later updates. An accepted project receives controlled ecosystem execution
and hosting rather than an unrestricted public contract deployment right.

An accepted project may allow one product-creator layer beneath its project
creator. There is no deeper creator nesting. Product creation follows the
approved project's deterministic guardrails and does not repeat the complete
venture-approval process.

Every project or product must provide a genuine native-asset spendable element,
such as a purchase, subscription, feature, reward, or service. Purely passive
deployments are not creator-economy projects for revenue-routing purposes.

### Users

Users spend the native asset within approved projects and may participate in
bounded ecosystem programs such as liquidity provision, HUB biometric
verification, Founder referrals, and later programs accepted by the
constitution. These are subroles, not additional native currencies.

### Developers

Developers improve the ecosystem through bug bounties, community grants, and
developer incentives. They remain users where applicable but are a distinct
economic class so technical contribution receives dedicated attention and
funding.

### System Creator Company

The System Creator authority is expected to be exercised through the company.
It receives Founder Seat purchase proceeds, the system-creator commercial
share, and the fixed issuance royalty. During the establishment period it
manages protocol releases, the ecosystem AI model and policies, AI
infrastructure, and minimum Founder Node requirements.

This authority does not include rewriting ledger history, confiscating
ordinary balances, deleting accepted application history, or directly editing
immutable hosted content. Protocol upgrades may add new versions and
capabilities only through explicit, auditable compatibility rules.

### Ecosystem AI

The Ecosystem AI is a nonhuman authority for decisions that require
case-specific evaluation. Its responsibilities may include biometric
verification, venture evaluation, milestone review, treasury and escrow
spending, developer programs, code and evidence review, and content
moderation.

**Every Founder Machine runs an open-weight model continuously, and the company
runs no AI infrastructure of its own.** This reverses the original direction,
which placed one logical ecosystem AI on company-operated data centres and
stated that Founder Nodes do not run AI models. The premise of that direction
expired: open-weight models are now strong enough to carry this work, they keep
improving, and a unified-memory machine or rented equivalent hosts one
continuously. [ADR 0047](../decisions/0047-the-founder-machine-runs-the-ecosystem-ai.md)
records the reversal.

The ecosystem AI is therefore the population of Founder Machines rather than a
service. It remains one logical authority in the sense that matters — a single
framework, a single policy set, one decision per matter — while the inference
that produces a decision happens on whichever machine is assigned.

**A judgment is made by the machine nearest the requester, after its neighbours
reason.** Before deciding, that machine reads the reasoning of its nearest
neighbours, up to six, so seven models reason in total. Neighbours produce
reasoning reports and know the decision is not theirs; the assigned machine
weighs them with its own and issues one signed, bounded decision. Model
processes and serving replicas provide capacity and reliability without becoming
community or Founder voting.

**AI inference still cannot decide consensus.** Two models disagree — different
weights, quantization, hardware, and sampling — so an AI output is never the
consensus state. It is a signed, bounded claim that deterministic protocol rules
verify. Moving inference onto the machines does not change this and cannot.

**Each Founder identity also has one personal assistant.** It carries one name
the founder assigns, one profile, and one accumulated understanding of that
person; it reaches them on their phone, connects whatever third-party services
they attach for context and communication, and can transact in the ecosystem on
their behalf. **Its concurrency is the seat count**: an identity holding one
hundred seats still has one assistant and may run one hundred parallel live
sessions of it. Seats buy capacity, not additional identities, so a founder
never fragments into several assistants who each know part of them.

The company controls the model, the framework, the protocol, and the update
schedule during an initialization stage of roughly one to two years. **A founder
never chooses which model or framework their machine runs, at any point.**
Authority is delegated gradually by explicit scope as the system, policies,
models, and evidence mature; at the end of initialization a self-improving model
is deployed and everyone including the company renounces total control to it,
while deterministic chain services remain deterministic. Human operators do not
substitute ad hoc funding votes for a delegated AI decision.

### The company runs no backend

**The Founder Machine is the only infrastructure the ecosystem ever uses.** The
company operates no server, no hosted service, and no external infrastructure of
any kind, from the beginning rather than after a migration. Every website,
frontend, backend, application, and ecosystem service runs on Founder Machines.
Where the company needs capacity to operate the ecosystem it buys Founder Seats
and runs Founder Machines like anyone else.

The refusal is absolute because a shrinking backend never shrinks. It accretes
the features that are awkward to decentralize and becomes the thing the
ecosystem cannot run without, and the migration is always next quarter's work.
Not building the first one is the only enforceable version of this rule.

**"Founder Machine" is the preferred term for what this document still mostly
calls a Founder Node.** A node implies a validator; this is a validator, a
server, an application host, an AI home, and the ecosystem's only
infrastructure. Existing text is not renamed, because a rename across
specifications, vectors, and models would change no behaviour; new text uses
Founder Machine.

## One native asset

The ledger recognizes exactly one native asset. There is no native stablecoin,
public asset-creation operation, unrestricted wrapped-asset balance, public EVM,
or arbitrary public smart-contract deployment.

All internal prices, payments, fees, rewards, royalties, escrows, grants,
ventures, and application activity use the native asset. Foreign assets at the
bridge boundary never become generally transferable internal balances.

The intended permanent maximum supply is exactly:

```text
56,993,950,100 native units
```

There is no discretionary inflation beyond the fixed channels below, no burn,
and no deflation mechanism. Unissued capacity is not circulating supply. There
is no founder-directed genesis allocation: native units enter circulation only
through Founder Node issuance permissions and capped direct-mint channels.

This maximum was revised on 2026-08-07, from 55,743,940,100, to fund the
doubled Founder referral channel described below. The revision was made while
the project is research software: no native unit has been issued, no holder
exists, no C++ consensus enforces a supply figure, and the accepted M2 models
activate nothing. "Permanent" binds the production protocol from genesis
onward. After genesis the maximum is immutable, and no later revision of this
kind is available.

There is no founder-directed slashing, confiscation, or monetary penalty path.
Operational failure removes eligibility for the applicable benefit; it does
not burn or seize already owned native units. A future proposal for staking,
collateral, or economic penalties would require a new explicit founder
decision, not reuse of a generic research fixture.

An exact atomic denomination, integer representation, and cap in atomic units
must be accepted before these display-unit amounts become consensus values.

## Maximum-supply allocation

### Founder Node distribution channels

These channels are funded by a Founder Seat's own eligible cycles.

| Channel | Maximum native units |
| --- | ---: |
| Founder Node operator benefit | 25,000,200,000 |
| Venture escrow | 12,500,100,000 |
| Community-grants escrow | 2,500,020,000 |
| Developer-incentives escrow | 1,250,010,000 |
| System Creator issuance royalty | 731,000,000 |
| **Founder Node channel subtotal** | **41,981,330,000** |

### Direct-mint channels

These channels are not funded by a seat's cycle evaluation, and their
beneficiaries mint on their own schedule.

| Channel | Maximum native units |
| --- | ---: |
| Liquidity mining | 7,500,060,000 |
| Impermanent-loss protection | 3,750,030,000 |
| Founder referral benefit | 2,500,020,000 |
| HUB-verified-user incentives | 1,250,010,000 |
| Initial mini-gamified incentives | 12,500,100 |
| **Direct-mint subtotal** | **15,012,620,100** |

The two subtotals add exactly to the maximum supply. The channel caps are
founder-directed. Eligibility, proof, anti-abuse, timing, and per-participant
limits for the liquidity-mining, impermanent-loss, and mini-gamified channels
remain to be specified and stress-tested; the referral channel's eligibility is
the recorded referrer relationship itself, which the ledger already holds.

**The HUB-verified-user channel is fully determined as of 2026-08-15.** Its
eligibility was decided on 2026-08-14 — being HUB verified — and the owner
supplied its population and period: the **first 1,000,000 verified users**,
**daily**, for **two years**. Those three figures and the founder-directed cap
determine the rate exactly, with no remainder:

```text
125,001,000,000,000,000 atomic / 1,000,000 users / 731 cycles
  = 171,000,000 atomic = 1.71 native units per user per day
```

**The first day is paid as an entry airdrop rather than as a mint permission.**
On completing HUB verification for the first time, the chain issues that
person's first day's portion immediately, so a brand-new account can transact at
all; from the second day it continues as an ordinary daily mint permission under
the same thirty-window accumulation cap as every other permission. After the
first million users the entry problem does not recur, because bridges, swaps,
and direct purchases exist by then.
[ADR 0042](../decisions/0042-the-hub-entry-airdrop-and-the-verified-user-rate.md)
records the direction, the derivation, and why a fully pre-minted pool was
rejected: it would be a genesis allocation under another name.

**What a verified user does not collect in time is never issued, decided on
2026-08-15.** Every other channel sends forfeited value somewhere — a failed or
capped seat's permission to the day's best performers, a capped referral to the
unreferred pool — and this channel has no second destination, so none is
invented. Value left uncollected past the accumulation cap is never issued, and
total supply ends below the maximum by exactly that amount. It is the same
collect-or-lose rule, applied where there is nobody to give the forfeited value
to.
[ADR 0043](../decisions/0043-founder-answers-on-reach-asymmetry-forfeiture-and-signers.md)
records it.

The Founder referral benefit moved from the Founder Node channels to the
direct-mint channels on 2026-08-07, and doubled. Both changes are explained
under [Founder referrals](#founder-referrals).

## Founder Node issuance

Each Founder Seat receives 731 eligible 24-hour-target cycles beginning with
that seat's first activation. Seats activated on different dates therefore
have different issuance windows. A chain-defined height or epoch rule must
later represent the cycle deterministically; local wall clocks cannot decide
consensus.

For an eligible cycle, the base permission is 574.3 native units:

| Beneficiary | Native units per eligible cycle |
| --- | ---: |
| Venture escrow | 171.0 |
| Community-grants escrow | 34.2 |
| Developer-incentives escrow | 17.1 |
| System Creator issuance royalty | 10.0 |
| Founder Node operator | 342.0 |
| **Total** | **574.3** |

The base permission is the whole of a seat's cycle entitlement. The referral
benefit is no longer part of it; it is a direct-mint channel described under
[Founder referrals](#founder-referrals).

Permissions may be exercised immediately or accumulated. Until a permission
is exercised, its units do not exist and are not circulating. Exercise is one
atomic distribution: every beneficiary is credited or none is.

**Accumulation is bounded, decided on 2026-08-14.** A seat may hold at most
about thirty days of uncollected cycles. Once it is full, **a day it cannot
collect is treated exactly as a day it failed**: that day's generation goes to
the best-performing nodes, and the full seat is not one of them, because a
failed seat never rewards another failed seat. What the seat has already earned
is untouched and waiting; one collection restores both the room and the
eligibility. This is a collect-or-lose rule rather than a penalty — an
uncollected permission's units do not exist — and the same bound applies to
referral earnings, whose forfeited value routes to the unreferred performance
pool.

If a seat fails an eligibility cycle, the complete 574.3-unit base permission
is retained. The escrow and System Creator portions keep their original
beneficiaries; only the 342-unit Founder portion changes beneficiary to the
best-performing active Founder Node or nodes for that cycle, as defined under
[Performance reallocation](#performance-reallocation). The original inactive
seat cannot recover that benefit later.

After a seat completes its 731 eligible cycles, its issuance period ends. The
seat remains permanent and may continue receiving active-seat commercial
revenue and transaction-fee shares.

**The 731 cycles bound the native asset distribution and nothing else.** A
Founder Machine's operating life is not 731 cycles. The distribution exists so
that founders have income during the roughly two years before the ecosystem
generates real revenue; a founder's enduring incentive is the seat itself, which
is a stakeholder's share of the ecosystem. So a machine whose distribution has
finished **keeps operating, keeps being ranked, and remains eligible to win any
pool that still holds value** — the daily reallocation, the recovery pool, and
the monthly unreferred pool alike. Because activation dates differ, machines
finish at different times and a contributing population always remains.

Two sets are therefore distinct. The **contributing set** is the seats inside
their own 731 cycles, which generate base permissions. The **eligible set** is
every operational seat that met the cycle's duty, in span or not, which competes
for what is distributed. **The best-performer mechanism never deprecates**: it is
infrastructure later incentive programmes attach to, not an artifact of this
distribution. A pool that has been fully consumed and can receive no further
inflow is marked consumed and then archived, never deleted, so its history stays
queryable.

### What counts as an eligible cycle

A Founder Node is a single enclosed all-in-one service. It is not configurable,
tunable, or partially operable by its founder: it either runs with every
component healthy or it does not. There is no partial-credit mode, and no
founder-side setting can change what is measured.

A node is **fully operational** for a period only when every service it
provides is healthy at once:

- the full blockchain node;
- validator duties under the deterministic active-set protocol;
- transaction servicing;
- application compute, storage, caching, and delivery; and
- the workload and health agents.

If any one component is degraded, failing, or absent, the node is not fully
operational for that period, and the period counts as downtime.

A cycle is **met** when cumulative fully operational uptime within the
24-hour-target cycle is **18 hours or more**. Equivalently, a cycle fails when
cumulative downtime exceeds **6 hours**.

The 6-hour grace allowance is cumulative and may be fragmented. One outage of
6 hours, or six separate outages of 1 hour, or any other combination summing
to 6 hours or less, all leave the cycle met. The allowance exists so ordinary
restarts, updates, and brief network faults do not punish an honest operator.

### Performance reallocation

When a seat fails a cycle, that cycle's 342-unit Founder portion is reallocated
to the Founder Node or Nodes with the **highest cumulative fully operational
uptime in that same cycle**.

- The winner is the single highest uptime achieved that cycle, whatever value
  that turns out to be. A perfect 24 hours is expected to be common, but it is
  not a requirement; if the best any node reached was 19 hours, the 19-hour
  nodes win.
- When several nodes are tied at exactly that maximum — the ordinary case at a
  perfect cycle — they share the 342 units equally.
- A winner must itself have met the cycle. A failed seat never rewards another
  failed seat.
- The integer remainder of **each leg's** equal split goes to the **recovery
  pool** rather than being burned or carried in a channel. Every leg is divided
  among the winners, because the whole permission settles at the winner's mint.
- If no node met the cycle at all, the **whole 574.3-unit permission** goes to
  the recovery pool — all five legs, not only the Founder portion.

**The recovery pool exists so that 100% of the node distribution's mint
permissions are assigned and nothing is ever stranded.** It accumulates the two
amounts above across as many cycles as it needs to, and **the earliest
subsequent cycle that has any winner takes 100% of it**, on top of that cycle's
own reallocation and distributed to that cycle's winner set. It therefore needs
no ranking, tie, or remainder rule of its own: the winner set already splits an
exact tie equally, and the pool's own dust simply returns to it for the cycle
after. It replaces the per-channel carry, which was only ever added to and so
accumulated value no participant could reach.
[ADR 0049](../decisions/0049-the-recovery-pool-and-permanent-best-performer-ranking.md)
records it.

Whether a founder then mints is their own business — an uncollected permission
is a choice. A permission that is never *created*, or created and then stranded,
is a defect, and this is the rule that closes it.

Each failed cycle resolves independently against its own cycle's winners. A
seat that fails four consecutive cycles produces four separate reallocations,
each to whoever led on that day.

**Reallocation settles at the winner's mint, decided on 2026-08-13.** The whole
574.3-unit permission moves to that cycle's winners when the cycle is assigned,
and each winner collects it when it next mints: the winners take the Founder
portion into their own balances, and the escrows and the System Creator receive
their four legs from that same mint. The four institutional legs keep their
beneficiaries — only the Founder portion changes whose it is — but they no
longer wait on the seat that failed.
[ADR 0033](../decisions/0033-founder-decisions-minting-hub-and-referral-entry.md)
records the direction.

This replaced an earlier rule that settled reallocation at the *failed* seat's
next exercise, under which a founder who never minted again withheld the
escrows' and the System Creator's value indefinitely. A seat that never mints
now forfeits only its own portion. The failed founder can still see which seats
received the value, and an uncollected permission's units still do not exist.

Longer leaderboards over 7, 30, and 90 days and all time are reporting views
for later incentive programmes. They carry no entitlement under this section,
and they outlive every distribution period, because ranking is permanent
infrastructure rather than a feature of the initial issuance.

### How uptime is established

Uptime must reach consensus without trusting a founder's own machine. Software
running on hardware its operator controls can be patched, replayed, or
simulated, so a self-reported "all green" is never sufficient on its own.

- Validator participation and transaction servicing are **derived from
  on-chain records**. The chain already observes votes, proposals, and serviced
  transactions, so this part needs no attestation and cannot be forged.
- Resource provision is proved by **challenge-response**. Random retrieval and
  compute challenges are issued and the responses recorded, so a node must
  actually hold and serve what it claims rather than assert that it did.
- The Ecosystem AI **reviews and may dispute**. It may file a bounded, signed
  dispute against a cycle result within a fixed window. Silence finalises the
  result.

The AI's signature is deliberately not required for payment. If it were, an AI
outage or a company decision would freeze every Founder's income, which would
make the company the effective owner of the reward path. A dispute window
inverts that failure mode: when the AI is unavailable, results stand and
founders are paid.

Hardware-backed attestation is not available until dedicated Founder machines
exist, so until then the challenge-response and dispute layers carry the
anti-gaming burden. The exact challenge construction, sampling rate, dispute
window length, dispute resolution, and settlement bounds require a
specification and independent review. They cannot be selected in a way that
changes the fixed channel totals or that puts population-wide hidden work into
every transaction.

## Founder referrals

A Founder Seat purchased through a recorded referrer creates a **34.2-unit
per-cycle benefit** for that referrer, for the referred seat's 731 cycles.

Three properties are founder-directed:

**It is unconditional.** The referrer earns the full 34.2 units for every one
of the referred seat's 731 cycles regardless of whether that seat met the
cycle. A referrer cannot operate, repair, or influence someone else's machine,
so making the referrer's benefit depend on it would be unfair.

**It is a direct-mint channel, not part of the base permission.** The referrer
mints and withdraws on its own schedule and is never blocked by the referred
seat's behavior. This is why the channel moved out of the Founder Node
distribution table.

**Unreferred seats do not waste their allocation.** A seat purchased without a
recorded referrer contributes its 34.2 units per cycle to the **unreferred
performance pool** instead. Nothing is left unissued merely because a buyer
arrived without a referrer.

The pool is paid to **monthly** best-performing Founder Machines, ranked by the
same cumulative fully operational uptime, and only one month's accrual is
distributed per month. **A month is a real calendar month beginning on the 1st**,
derived from the consensus timestamp in the block header rather than from a
count of cycles, so participants read the same boundary the rest of the world
does. [ADR 0050](../decisions/0050-the-block-timestamp-is-the-ecosystem-clock.md)
records the construction. The pool's accrual rate rises as more unreferred seats
are sold and never falls, so a later month never distributes less than the
seats then sold have earned.

Because every seat contributes 34.2 units per cycle to exactly one of the two
destinations, the channel is consumed precisely:

```text
100,000 seats x 731 cycles x 34.2 = 2,500,020,000 native units
```

The referral benefit is 10% of the 342-unit operator leg. It was 17.1 units,
or 5%, until 2026-08-07.

**A referrer must be HUB verified.** Human Uniqueness Biometric verification is
the entry requirement for referring anyone, decided on 2026-08-14. Holding a
Founder Seat is neither required nor relevant. The requirement serves the
referrer as well as the system: HUB-verified participants earn from their own
direct-mint channel, and a verified referrer cannot be a mistyped address that
strands 731 cycles of benefit where nobody can reach it.

The pool is paid to the **single best-performing** Founder Seat of the month.
Where several seats stand at exactly the same top figure — whatever that figure
is — they share it equally. The rule is one winner unless there is an exact tie
for first, which is the same shape as the daily failed-cycle reallocation.

These details require a specification and are engineering work rather than
founder decisions:

- the pool's remainder rule;
- when a referral benefit begins for a seat that is purchased but never
  activated, since a seat's 731 cycles start at its first activation and an
  unactivated seat has no cycles to count; and
- the storage bound on accrued referral balances at 100,000 seats.

## Commercial revenue and transaction fees

Every native-asset commercial payment to an approved project or product is
split independently of its transaction fee:

| Beneficiary | Share of commercial payment |
| --- | ---: |
| Active Founder Seats | 45% |
| Creator side | 45% |
| System Creator Company | 10% |

When the project creator directly supplies the purchased item, the project
creator receives the full creator share. When a separate product creator
supplies it, the project creator receives 22.5% and the product creator
receives 22.5%. Creators may set approved product prices but may not redefine
the constitutional split.

The Founder share is divided among sold Founder Seats that are online and meet
the active requirements for the applicable accounting cycle. Offline seats do
not dilute active seats.

Every protocol transaction fee is charged separately from any commercial
payment and routes 100% to eligible active Founder Seats. This applies whether
the transaction is a purchase, transfer, issuance exercise, or another
accepted state transition. Fees are not burned and are not deducted before
the 45/45/10 commercial split.

Exact rounding, remainder, claim, activity-snapshot, and bounded-distribution
rules require a deterministic specification.

## Founder Seats

### Capacity and concentration

- Exactly 100,000 Founder Seats may ever be sold.
- Each seat corresponds to one independently measured Founder Node service.
- One human may control no more than 1,000 seats.
- Seats are not resalable, voluntarily surrenderable, or transferable through
  an ordinary wallet transaction.
- A seat's historical identity and manager-address records are never erased.

### Price schedule

Seat prices are denominated in USD and advance after each block of 100 sold
seats:

1. seats 1 through 100 cost USD 100 each;
2. the price rises by USD 10 for each next 100-seat block until a block price
   of USD 1,000 is reached; and
3. after that block, the price rises by USD 100 for each next 100-seat block
   until all 100,000 seats are sold.

Under that tier boundary, the final 100 seats cost USD 91,900 each and the
derived full-sale proceeds are USD 4,231,855,000. These derived values must be
fixed as test vectors before implementation.

Founder Seat purchases use BTC, ETH, or an explicitly approved stablecoin such
as USDT or USDC through the restricted bridge workflow. The complete external
purchase proceeds go to the System Creator Company. The exact stablecoin
allowlist, USD valuation proof, quote lifetime, external finality, refund, and
accounting rules require a bridge specification.

### Permanent biometric identity and managers

A seat is bound to the founder's biometric identity at enrollment. Wallet
signatures identify tools and manager addresses but are not sufficient for a
sensitive Founder action such as adding a manager or withdrawing Founder
funds. Those actions require both an accepted signature and a fresh,
action-bound biometric approval from the ecosystem verifier.

A recorded manager address remains in the historical ledger forever. Another
registered manager may initiate an addition, but the new authority becomes
usable only after deep biometric verification matches the permanent Founder
identity. Loss of an address is handled by adding a new verified manager, not
by rewriting ownership history.

**A Founder Seat has no address, decided on 2026-08-15.** It is tied
permanently to the owner's HUB verified data itself. The earlier rule — that a
seat's addresses are permanent, can never be removed, and are add-only — is
superseded together with the concept it governed, and so is the 16-manager
limit.

**That rule existed to make a seat non-sellable**, and tying the seat to the
identity serves the purpose better than tying it to an address ever did. A
biometric identity is not assignable, so seat ownership cannot move. Two parties
may still privately negotiate management, and they cannot take over: the
HUB-verified owner remains in charge and in full control, and may revoke any
signer at any time. Legacy succession is the one path by which a seat's identity
changes, and it runs through the recorded legacy instruction rather than through
an address.
[ADR 0041](../decisions/0041-the-seat-is-tied-to-the-identity-not-an-address.md)
records the resolution.

**Minted value lands in one of the owner's asset-holding addresses.** The
earlier rule sent it to the address that signed the mint, so that a recovered
address could receive; a signer now holds no funds, and regaining an identity
regains its holding addresses, so that purpose is served without the rule. Which
holding address a mint credits is specification work recorded in ADR 0041.

### HUB verification is one ecosystem-wide layer

Human Uniqueness Biometric verification — **HUB** — is a foundational service of
the whole ecosystem, decided on 2026-08-14. It is not a Founder Seat feature.

**HUB verification is mandatory, decided on 2026-08-15.** Anyone who wants to
register must complete it, and it is required to interact with any part of the
ecosystem. It is the single source of truth for registration, account holding,
and security. There is no unverified participation.

That supersedes the earlier framing, in which verification was available to
every participant class and the company switched it on where it judged
verification reasonable. The owner named the trade and accepted it: less
flexibility and a higher barrier to entry, in exchange for more security, more
simplicity, fewer vulnerabilities, one source of truth for who owns an account,
and a single resolution of a family of account-related failure modes rather
than one contract version at a time.
[ADR 0039](../decisions/0039-hub-verification-is-mandatory-for-everyone.md)
records the direction and what it leaves open.

**An address is not an identity root.** A wallet address is an additional tool
its owner holds for operations and transactions. The verificator is the person's
HUB biometric facial data, recorded on chain permanently and immutably.

**Verification is the entry point, and it reaches the recipient of a payment,
decided on 2026-08-15.** A person who has not registered and completed HUB
verification cannot interact with the ecosystem in any way: no wallet, no
transaction, nothing. There is therefore no account for a payment to reach, and
**a transfer naming a recipient that is not a registered holding address is
refused** rather than creating one. Native units cannot be sent to a person who
has not joined; joining is free and self-funding, because the entry airdrop pays
for it.
[ADR 0043](../decisions/0043-founder-answers-on-reach-asymmetry-forfeiture-and-signers.md)
records this and the three answers alongside it.

**Recovery is direct, between the owner and their own recorded biometric data.**
A person who has lost everything registers again and completes HUB verification;
the system detects that this biometric identity already exists on chain and the
person immediately regains access to the existing account. They then attach a
new wallet address and continue. No friend, no helper, and no third party at any
step.

**Biometric confirmation is on by default for every financial transaction and
every mint**, as an ecosystem-wide one-time-password layer. Each person may
customise their own posture: a minimum amount below which it is not required,
time windows, or turning it off entirely.

**Changing that posture is asymmetric, decided on 2026-08-15.** Relaxing it —
turning confirmation off, raising the minimum amount, or widening a window in
which it is not required — requires a biometric approval. Tightening it requires
only a signer signature. The rule that protected a Founder Seat's minting since
version three now covers every participant, every holding address, and every
operation, so a stolen signer key can never weaken the protection it is stealing
against.

**A verified identity holds fund-holding addresses, and those hold no keys,
decided on 2026-08-15.** A person may have as many as they want; they are where
assets accumulate and they never change. Signing keys are separate and
revocable: a person assigns one or more signers to any holding address, and the
HUB identity is the admin that may add, remove, revoke, or modify them. Regaining
an identity on a new device regains the holding addresses directly, so the person
can revoke old signers and register new ones with no funds and no third party
needed. Each person configures their own signing logic and security options per
address and per transaction.

[ADR 0040](../decisions/0040-holder-addresses-and-revocable-signers.md) records
the direction, what it settles, and the one conflict it raises with the Founder
Seat address rule.

**A signer key belongs to exactly one holding address, decided on 2026-08-15.**
A person with several holding addresses holds a signer key for each, which a
wallet derives without their involvement. A stolen or revoked key therefore
reaches exactly one holding address and nothing else.

Any participant who registers is therefore HUB verified: Founder Seat holders,
project and product creators, ordinary users, and developers.

Each verification produces a signature unique to that person, derived from their
personal secret, usable across ecosystem and blockchain operations. The
cryptographic construction is engineering work; what is founder-directed is the
shape — one identity layer, one source of truth, switchable per integration
point, serving every participant class.

**HUB verification survives the loss of any address, decided on 2026-08-14.**
Once a person is registered, they can regain access at any time by signing in
through HUB, including when the address the verification was tied to is gone.
It is an ecosystem-wide universal one-time-password layer: once registered, it
is what makes managing addresses, assets, and security matters straightforward
across the whole system.

**A verified person may add and remove their own addresses through HUB.** A HUB
identity is therefore a set of addresses rather than a single one, and HUB
signing is the authority over that set. **There is no longer a Founder Seat
exception to this**: the permanent add-only seat address was superseded on
2026-08-15 together with the concept it governed, because a seat has no address
at all.

The two consequences this raised are both decided. Buying a Founder Seat
requires HUB verification first and ties the seat to that identity, and the chain
holds a HUB identity's address set in consensus state; both were answered on
2026-08-14 and are recorded under
[Explicitly unresolved founder details](#explicitly-unresolved-founder-details)
as resolved.

HUB-verified users earn from the `hub_verified_user_incentives` direct-mint
channel. Verification is therefore both an identity primitive and a participant
benefit, and it is the mandatory entry requirement for referring a Founder Seat
buyer.

**The three consequences of the mandatory direction are all decided.** How a
person holding nothing pays for their first transaction is the entry airdrop of
ADR 0042; how far the requirement reaches into a native transfer and what turning
the confirmation off entirely means for a seat's protection asymmetry are both
answered above and recorded in ADR 0043.

**Biometric capture and evaluation run locally, on the founder's own Founder
Machine, in a fully sandboxed offline environment.** No remote verifier, no
company service, and no other network participant is in the loop. The verdict is
produced by deterministic software; sensitive material stays in the machine's
multisignature vaults and never leaves the sandbox.

**The local model is the process's integrity monitor rather than its verifier.**
It never decides whether a person is who they claim to be. It evaluates whether
verification was initiated fairly and whether the inputs supplied to it were
genuine and unmanipulated, and it holds authority to dispute a run, reject it,
and force re-initialization with correct inputs. A deterministic verdict
supervised by a non-deterministic monitor is the right division: "is this the
enrolled person" is a measurement, and "did this process run honestly" is a
judgment.

Every identity's uniqueness commitment is replicated to every Founder Machine,
so uniqueness is compared locally against the whole population with no lookup
service anywhere. [ADR 0048](../decisions/0048-hub-verification-runs-locally-with-an-ai-integrity-monitor.md)
records the architecture and names the one open dependency: a biometric cannot
be hashed, so making a capture produce the same commitment every time requires a
stabilization scheme that must pass independent cryptographic review before
anything rests on it.

Raw images, video, and private linkage data do not become ordinary public
blockchain data. Their encrypted storage, unlinkability, retention, decoy
strategy, liveness protection, coercion limits, false-acceptance targets, and
breach behavior require a separate threat model and independent review.
Recording this requirement does not itself establish that face verification is
secure — and two residual risks are stated rather than solved. Both the verifier
and its monitor run on the founder's own machine, so defeating that machine's
attestation defeats both, which is the strongest argument for the physical
machine phase. And checking one capture against a whole population is 1:1
matching applied N times, so false accepts accumulate with population size and
the parameters must be chosen against a target population.

### Offline behavior

An offline machine does not participate as a live network member and does not
count toward active-seat revenue or fee distribution. The permanent Founder
Seat record remains. Returning online restores future eligibility after the
deterministic recovery conditions are met; it does not restore missed Founder
benefits.

Downtime within a cycle's 6-hour grace allowance does not fail that cycle, so
brief outages, restarts, and updates cost nothing. Downtime beyond the
allowance fails only the cycles it falls in; it never removes the seat, its
history, or units already owned. A seat that fails every cycle of its issuance
window still keeps its referral benefit to its own referrer, because that
benefit is unconditional and does not depend on this seat's operation.

### Legacy succession

A founder may record one or more permanent, versioned legacy statements,
nominate a successor, provide evidence identifying that person, and set an
inactivity trigger within future protocol bounds. Earlier statements are never
deleted; a later statement may supersede their active instruction.

The successor must know to start the node and complete biometric verification.
The Ecosystem AI evaluates the founder's retained instructions and the
claimant evidence. If no valid successor exists or verification cannot
complete, authority remains stuck rather than being reassigned by a human
administrator.

A successor may later nominate another successor. The original founder retains
the superior right to return and reclaim active authority at any future time;
an apparent succession cannot be used as a trustworthy sale mechanism. Exact
inactivity limits, dispute evidence, conflicting statement precedence, and
reclaim transitions remain founder-reserved details for the legacy milestone.

## Founder Node and resource network

Every Founder service provider runs one integrated service. It includes:

- a full blockchain node;
- validator capability under the deterministic active-set protocol;
- application compute, storage, caching, and delivery services;
- an open-weight model served continuously, for both the ecosystem's judgment
  and the founder's personal assistant;
- the local HUB verification service and its vaults;
- workload and health agents; and
- later, the immutable NodeOS and dedicated physical Founder hardware.

Validator service is not an optional commercial add-on, but this does not
require all 100,000 machines to vote on every block. The protocol must select
and rotate a bounded live signing set while every eligible Founder Node carries
the same software capability. AI inference cannot decide consensus.

**The operator's responsibility is to run the software, and nothing else.** The
Founder Machine is one atomic, sealed, plug-and-play process with no intervention
surface: founders do not operate, configure, tune, or maintain it. It follows
that a software defect is not the founder's fault. If the machine was running,
the infrastructure requirements were met, and no intervention occurred, then a
failure caused by the software is auto-reported and logged, **the founder is
still paid for the cycle**, and the fix ships to the whole fleet in the next
update batch — every machine runs the same software, so a defect observed on one
is present on all. Intervention voids this.

The machine specification is founder-directed, because it decides who can afford
to participate. Per machine: an x86_64 Xeon-class server tier of at least 8
vCPU, 64 GiB memory, 1 TB NVMe storage, and 12.5 Gbps of network for hosting and
services; and **separately, at least 512 GB of unified memory for the open-weight
model**. An operator may rent unified-memory capacity rather than own it, which
is the expected path for early founders.
[ADR 0052](../decisions/0052-the-founder-machine-specification.md) records the
figures and their consequences.

**Every seat eventually receives the same machine**, whether it cost USD 100 or
USD 91,900, funded from pooled sale proceeds rather than from its own seat price.
Physical production begins once the ecosystem has roughly 10,000 to 12,000 daily
active founders, and distribution is staged over time in step with growth,
beginning with the year's best performers.

There is no general public EC2-style rental market. Founder resources serve
only approved ecosystem applications and system workloads. Deterministic
scheduling selects available nodes near the requesting location and may
compose several machines into one application workload. Caching, load
balancing, replication, cold backup, and replacement provide availability.
Not every node stores every application's complete live dataset.

## Approved applications and permanent history

Arbitrary users cannot deploy public contracts, create assets, or directly
place server workloads. The Ecosystem AI is the admission gate for complete
projects. Accepted applications use a controlled runtime and versioned
interfaces whose capabilities cannot bypass native economics.

Creators have no direct production delete or edit access. Updates are prepared
outside the network, resubmitted, reviewed, and published as new accepted
versions. Previous accepted versions and ledger history remain immutable.
Moderation may prevent disallowed material from being served or presented; it
does not silently rewrite canonical history.

The initial founder-directed moderation boundary is to prevent NSFW material,
not to impose general political or viewpoint filtering. Complete moderation,
legal-response, user-safety, and evidence-retention policies require a later
owner-approved AI framework.

## AI-managed treasuries and escrows

Founder issuance funds separate venture, community-grant, and developer-
incentive escrows. Additional future treasury programs must receive an
explicit source and cap before they can exist.

Unused escrow value remains available indefinitely for a later eligible
decision. It is not burned, expired, or swept merely because the AI did not
find a suitable use during an accounting period.

The Ecosystem AI may evaluate proposals, negotiate scope, define milestone and
tranche plans, approve or reject evidence, release bounded funds, pause work,
and terminate future funding. It can spend only native units already held by
the exact delegated escrow. If funds are insufficient, it must reduce,
counteroffer, queue, or reject the request; it cannot create supply.

The AI cannot by itself:

- change the maximum supply or an issuance-channel cap;
- change the commercial split, fees, seat price schedule, or Founder rules;
- approve more than the deterministic seat capacity;
- upgrade the protocol;
- alter its own capability framework; or
- spend from an escrow or amount outside its delegated envelope.

If the AI is unavailable, AI-managed decisions and spending pause. Founders,
users, community voters, and company staff do not become substitute case-by-
case treasury voters. Initially the company may replace models and update
policies; later AI self-succession and irrevocable delegation require explicit
founder direction, staged evidence, and independent review.

One logical AI authority does not mean one unrestricted private key. Each role
must have a separate, amount-bounded, replay-safe protocol capability so that a
failure in moderation cannot authorize a withdrawal and a compromised venture
workflow cannot change supply.

## Controlled external bridge and liquidity boundary

**The bridge runs on Founder Machines and depends on nothing outside them.**
Each participating machine runs the bridge's components and its own **light
client** for the external chain — headers and Merkle proofs verified against
that chain's own consensus, never a third-party endpoint or event subscription,
because an input arriving from a company outside the ecosystem is exactly the
dependency this architecture refuses, reintroduced where it does the most
damage. Inbound value is observed independently by a quorum of machines, each
against its own light client, and the wrapped asset is minted on that quorum.
Outbound value is the user's own transaction, which the native wallet broadcasts
alongside the local one. The attesting set is the validator set, so the bridge
introduces no new class of trusted party.
[ADR 0051](../decisions/0051-bridges-run-on-founder-machines.md) records it.

The bridge supports BTC, ETH, and explicitly approved mainstream stablecoins,
including USDT and USDC at launch. It exists only to connect the enclosed
native economy to outside value.

An inbound foreign-asset action is valid only as part of one user-level
workflow:

- purchase a Founder Seat;
- provide permitted swap liquidity; or
- swap into the native asset.

An outbound action swaps native value and withdraws the corresponding foreign
asset. There is no standalone foreign-asset deposit for internal use, no
foreign-asset transfer between ecosystem users, no foreign-asset payment to an
application, and no general wrapped balance.

Foreign assets remain in external custody or escrow. The blockchain records
only the native side, narrow bridge commitments, and non-transferable
operation-specific accounting needed to complete or recover the workflow.
Liquidity accounting may not create a secondary general-purpose currency.

The bridge receives no additional genesis allocation outside the fixed maximum
supply table. Initial native liquidity must come from units already issued
through a constitutional channel; the bootstrap auction, quote, or pool
mechanism remains an engineering and economic study for the bridge milestone.

The interface should feel atomic to the user: one operation either completes
both intended sides or enters a defined retry, expiry, refund, or recovery
path. Cross-network finality, custody, pricing, proofs, reorganization,
liquidity insolvency, key compromise, and emergency shutdown require an exact
specification, threat model, and independent audits before real assets are
accepted.

## Milestone and launch discipline

The current repository is research software. Its runnable four-validator
devnet proves deterministic native transfers, fees, persistence, restart, and
replica agreement; it does not implement this Founder economy, biometric
identity, production AI, application hosting, bridge, liquidity, wallet, or
public network.

Development order is governed by `roadmap.md`. Protocol-facing boundaries for
later systems are documented early, while expensive or security-critical
services are implemented only after their dependencies are stable. Public
testnets may use deterministic stand-ins for external payments, biometrics,
AI, and resource proofs, but must label them as stand-ins.

The complete public launch requires the integrated system-level foundation:
native economics, Founder enrollment and nodes, controlled applications,
treasury and AI workflows, bridge and liquidity, wallet and user interfaces,
monitoring, recovery, and independent production reviews.

Early ecosystem success is measured in real use, not token price alone. The
founder target is at least 10,000 daily active Founder Nodes, dozens of useful
deployed projects, USD 100,000 equivalent daily application revenue, and ten
daily active advanced developers. These are adoption indicators, not a claim
that technical production readiness follows automatically.

## Explicitly unresolved founder details

The owner has intentionally deferred these value-bearing details until their
milestone supplies enough evidence and context:

- eligibility and anti-abuse mechanics for the liquidity-mining,
  impermanent-loss, and mini-gamified direct-mint channels;
- exact legacy inactivity bounds and contested-successor behavior;
- stablecoin allowlist governance and any later bridge-asset change;
- complete AI funding, moderation, biometric, and succession frameworks;
- whether the assistant's one-profile-per-identity and seats-as-parallel-sessions
  entitlement is enforced by the protocol or is application policy; and
- any new treasury category, participant benefit, or application-content rule.

Resolved on 2026-08-07, and no longer open: the activity definition and its
grace allowance, performance ranking and tie handling, referral treatment for
an inactive seat, and referral-channel eligibility. Their remaining detail —
challenge construction and dispute window length — is specification work, not a
founder decision. The definition of a month was open until 2026-08-19 and is now
decided: a month is a real calendar month beginning on the 1st.

Resolved on 2026-08-13 and 2026-08-14, and recorded in
[ADR 0033](../decisions/0033-founder-decisions-minting-hub-and-referral-entry.md):
seat purchase and activation as biometric-gated transactions, daily
chain-written mint permissions, a mint that takes everything with no quantity
choice, minted value landing on the seat's own spendable address, optional
biometric verification on minting, a bounded accumulation of unminted
permissions whose excess reallocates to the day's best performers, the
single-best-plus-exact-ties rule for the unreferred pool, and HUB verification
as the referrer requirement. `hub_verified_user_incentives` eligibility is
decided — being HUB verified — while its rate remains open.

Also resolved on 2026-08-14, in the second round recorded in
[ADR 0035](../decisions/0035-founder-answers-on-payout-the-cap-and-hub-recovery.md):
minted value lands on the address that signed the mint; a cycle a seat cannot
collect because it is at the accumulation limit is treated exactly as a cycle it
failed, so the day's generation goes to the best performers and the capped seat
is not one of them; sixteen manager addresses per seat; and HUB verification as
a recovery layer that survives the loss of any address, with HUB signing as what
adds a Founder Seat address.

Resolved on 2026-08-15, and recorded in
[ADR 0043](../decisions/0043-founder-answers-on-reach-asymmetry-forfeiture-and-signers.md),
which the founder-decision gate for `economy-transition-v6` asked for after
enumerating that slice showed two of these were inside the contract rather than
beside it: verification is the entry point and reaches the recipient, so a
transfer to an unregistered holding address is refused rather than creating one;
relaxing a security posture requires a biometric approval while tightening it
requires only a signer signature, for every participant rather than for Founder
Seats alone; a verified user's uncollected incentive is never issued; and a
signer key belongs to exactly one holding address. **The first two of those had
been listed here as unresolved since the mandatory-verification pivot.**

Resolved on 2026-08-15, and recorded in
[ADR 0042](../decisions/0042-the-hub-entry-airdrop-and-the-verified-user-rate.md):
the HUB-verified-user channel pays the first 1,000,000 verified users 1.71
native units a day for 731 days, the first day arriving as an entry airdrop at
registration so a brand-new account can transact, and every later day as an
ordinary mint permission. That closes the last founder-reserved question of the
milestone.

Resolved on 2026-08-15, and recorded in
[ADR 0041](../decisions/0041-the-seat-is-tied-to-the-identity-not-an-address.md):
a Founder Seat is tied to the owner's HUB verified data rather than to any
address, which supersedes the permanent add-only seat-address rule and the
16-manager limit by serving their purpose — non-sellability — better than they
did. One uniform model now covers every participant: HUB verified data as the
single source of truth for authentication, asset-holding addresses that behave
like personal escrows and may be created, managed, and deleted, signer keys
assigned to those escrows separately and revocably, and security options
customisable per escrow and per financial operation.

Resolved on 2026-08-15, and recorded in
[ADR 0039](../decisions/0039-hub-verification-is-mandatory-for-everyone.md):
HUB verification is mandatory for anyone who registers and for interacting with
any part of the ecosystem; an address is an operational tool rather than an
identity root; recovery is direct between the owner and their recorded biometric
data with no third party at any step; and biometric confirmation is on by
default for every financial transaction and every mint, with each person free to
set a minimum amount, set time windows, or turn it off entirely. The direction
supersedes the earlier framing in which the company switched verification on
where it judged it reasonable.

Claude should ask focused questions at those boundaries. All other mechanism,
encoding, storage, consensus scheduling, networking, testing, packaging, and
operational choices remain autonomous engineering work subject to the
repository's evidence gates.
