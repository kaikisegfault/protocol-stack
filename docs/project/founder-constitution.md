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

There is one logical ecosystem AI. It is hosted by the company on centralized,
self-operated AI infrastructure in several suitable geographic locations.
Founder Nodes do not run AI models. Multiple model processes or serving
replicas may provide capacity and reliability without becoming community or
Founder voting.

The company controls the AI initially. Authority is delegated to it gradually
by explicit scope as the system, policies, models, and evidence mature. Human
operators do not substitute ad hoc funding votes for a delegated AI decision.

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
| Initial mystery-box incentives | 12,500,100 |
| **Direct-mint subtotal** | **15,012,620,100** |

The two subtotals add exactly to the maximum supply. The channel caps are
founder-directed. Eligibility, proof, anti-abuse, timing, and per-participant
limits for each direct-mint channel other than the referral channel remain to
be specified and stress-tested; the referral channel's eligibility is the
recorded referrer relationship itself, which the ledger already holds.

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
- The integer remainder of an equal split is carried forward rather than
  burned.
- If no node met the cycle at all, nothing is reallocated and the value is
  carried forward.

Each failed cycle resolves independently against its own cycle's winners. A
seat that fails four consecutive cycles produces four separate reallocations,
each to whoever led on that day.

Reallocation is settled when the failed seat next exercises a permission. That
exercise is one atomic transaction: the escrows and the System Creator receive
their portions, and the reallocated Founder portion reaches that cycle's
winners in the same transition. The failed founder can see which seats received
the value. A seat that never exercises never triggers the reallocation, and the
units are never created, consistent with the rule that unexercised permissions
do not exist.

Longer leaderboards over 7, 30, and 90 days and all time are reporting views
for later incentive programmes. They carry no entitlement under this section.

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

The pool is paid to **monthly** best-performing Founder Nodes, ranked by the
same cumulative fully operational uptime, and only one month's accrual is
distributed per month. The pool's accrual rate rises as more unreferred seats
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

- the exact definition of a month in cycles, given that 731 cycles is not a
  whole number of 30-cycle months;
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

**HUB signing is what adds a manager address, decided on 2026-08-14.** A
Founder Seat's addresses are permanent, can never be removed, and are add-only;
a HUB-verified founder may add more at any time by signing with HUB. This is
the exception to the ordinary ecosystem rule below, where a verified person may
both add and remove their own addresses. It exists so that a founder who has
lost every address they hold still has a path back to their seat, and it is
recorded in
[ADR 0035](../decisions/0035-founder-answers-on-payout-the-cap-and-hub-recovery.md).

At most 16 manager addresses may be recorded for one seat. That figure is an
engineering resource limit rather than a founder-directed value.

**Minted value lands on the address that signed the mint.** Any recorded manager
may collect, and the value arrives on that address ready to spend, which is what
makes adding a verified address a working remedy for a lost key.

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
signing is the authority over that set. Founder Seat addresses are the stated
exception: they are permanent and add-only, as described under
[Permanent biometric identity and managers](#permanent-biometric-identity-and-managers).

Two consequences of this are not yet decided and are listed under
[Explicitly unresolved founder details](#explicitly-unresolved-founder-details):
whether buying a Founder Seat requires HUB verification first, and whether the
chain holds a HUB identity's address set in consensus state.

HUB-verified users earn from the `hub_verified_user_incentives` direct-mint
channel. Verification is therefore both an identity primitive and a participant
benefit, and it is the mandatory entry requirement for referring a Founder Seat
buyer.

**Three consequences of the mandatory direction are not yet decided** and are
listed under
[Explicitly unresolved founder details](#explicitly-unresolved-founder-details):
how a person holding nothing pays for their first transaction, how far the
requirement reaches into a native transfer, and what turning the confirmation
off entirely means for a Founder Seat's existing protection asymmetry.

Biometric capture and evaluation use an ecosystem-owned camera-verification
system and the company-hosted Ecosystem AI. Raw images, video, and private
linkage data do not become ordinary public blockchain data. Their encrypted
storage, unlinkability, retention, decoy strategy, liveness protection,
coercion limits, false-acceptance targets, and breach behavior require a
separate threat model and independent review. Recording this requirement does
not itself establish that face verification is secure.

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
- workload and health agents; and
- later, the immutable NodeOS and dedicated physical Founder hardware.

Validator service is not an optional commercial add-on, but this does not
require all 100,000 machines to vote on every block. The protocol must select
and rotate a bounded live signing set while every eligible Founder Node carries
the same software capability. AI inference cannot decide consensus.

The operator's responsibility is to run the software on a minimum-spec Linux
machine or server. The target experience is one executable or one managed
installation with start, update, health, recovery, and migration workflows;
later dedicated machines become plug-and-run.

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

- **how a person who holds nothing pays for their first transaction.** The
  mandatory-verification direction of 2026-08-15 says registration and recovery
  involve no helper and no third party, and every transaction on a chain costs
  a fee paid by a sender. Either identity transactions are fee-exempt, or the
  fee is drawn from value the identity already holds on chain, or registration
  and recovery are performed by the company-hosted HUB service rather than by
  the person's own wallet. Each changes what a participant must do and own.
  **This blocks the contract version that encodes the direction;**
- **how far mandatory verification reaches into a native transfer** — whether an
  unverified address may still receive native units, or whether both ends must
  be verified, which decides whether the kind-1 byte identity carried unchanged
  since M1 gains an authorization condition;
- **what turning biometric confirmation off entirely means for a Founder Seat.**
  Version three made biometric-on-mint a per-seat option with a deliberate
  asymmetry — enabling needs only an address signature, disabling needs a
  biometric approval, so a stolen key can neither mint against a protected seat
  nor remove the protection first. A user-configurable global policy must either
  preserve that asymmetry or knowingly drop it;
- eligibility and anti-abuse mechanics for the liquidity-mining,
  impermanent-loss, and mystery-box direct-mint channels, and the *rate* of the
  HUB-verified-user channel, whose eligibility was decided on 2026-08-14;
- whether buying a Founder Seat requires HUB verification first, so that the
  seat is tied to a HUB identity the chain can check a later address addition
  against;
- whether a HUB identity's set of addresses is held in consensus state, which is
  what "add and remove your own addresses through HUB" means on a chain where an
  account is an address;
- exact legacy inactivity bounds and contested-successor behavior;
- stablecoin allowlist governance and any later bridge-asset change;
- complete AI funding, moderation, biometric, and succession frameworks; and
- any new treasury category, participant benefit, or application-content rule.

Resolved on 2026-08-07, and no longer open: the activity definition and its
grace allowance, performance ranking and tie handling, referral treatment for
an inactive seat, and referral-channel eligibility. Their remaining detail —
challenge construction, dispute window length, and the definition of a month in
cycles — is specification work, not a founder decision.

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
