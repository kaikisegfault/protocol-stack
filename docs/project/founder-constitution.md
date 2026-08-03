# Founder Constitution

Status: founder-directed target for the complete ecosystem; not a claim of
current implementation or production readiness

Last affirmed: 2026-08-03

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
55,743,940,100 native units
```

There is no discretionary inflation beyond the fixed channels below, no burn,
and no deflation mechanism. Unissued capacity is not circulating supply. There
is no founder-directed genesis allocation: native units enter circulation only
through Founder Node issuance permissions and capped direct-mint channels.

There is no founder-directed slashing, confiscation, or monetary penalty path.
Operational failure removes eligibility for the applicable benefit; it does
not burn or seize already owned native units. A future proposal for staking,
collateral, or economic penalties would require a new explicit founder
decision, not reuse of a generic research fixture.

An exact atomic denomination, integer representation, and cap in atomic units
must be accepted before these display-unit amounts become consensus values.

## Maximum-supply allocation

### Founder Node distribution channels

| Channel | Maximum native units |
| --- | ---: |
| Founder Node operator benefit | 25,000,200,000 |
| Venture escrow | 12,500,100,000 |
| Community-grants escrow | 2,500,020,000 |
| Developer-incentives escrow | 1,250,010,000 |
| Founder referral benefit | 1,250,010,000 |
| System Creator issuance royalty | 731,000,000 |
| **Founder Node channel subtotal** | **43,231,340,000** |

### Direct-mint channels

| Channel | Maximum native units |
| --- | ---: |
| Liquidity mining | 7,500,060,000 |
| Impermanent-loss protection | 3,750,030,000 |
| HUB-verified-user incentives | 1,250,010,000 |
| Initial mystery-box incentives | 12,500,100 |
| **Direct-mint subtotal** | **12,512,600,100** |

The two subtotals add exactly to the maximum supply. The channel caps are
founder-directed. Eligibility, proof, anti-abuse, timing, and per-participant
limits for each direct-mint channel remain to be specified and stress-tested.

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

A referred Founder Seat may additionally create a 17.1-unit permission for
the recorded referrer, subject to the fixed referral-channel cap.

Permissions may be exercised immediately or accumulated. Until a permission
is exercised, its units do not exist and are not circulating. Exercise is one
atomic distribution: every beneficiary is credited or none is.

If a seat fails an eligibility cycle, the complete 574.3-unit base permission
is retained. The escrow and System Creator portions keep their original
beneficiaries; only the 342-unit Founder portion changes beneficiary to the
deterministically selected best-performing active Founder Node or nodes for
that cycle. The original inactive seat cannot recover that benefit later.

The exact activity proof, grace allowance, performance metric, winner count,
tie handling, anti-gaming rules, referral behavior during an inactive cycle,
and bounded settlement method remain unresolved. They cannot be selected in a
way that changes the fixed channel totals or permits population-wide hidden
work in every transaction.

After a seat completes its 731 eligible cycles, its issuance period ends. The
seat remains permanent and may continue receiving active-seat commercial
revenue and transaction-fee shares.

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

- direct-mint channel eligibility and anti-abuse mechanics;
- Founder activity grace, performance ranking, winner count, and referral
  treatment for an inactive seat;
- exact legacy inactivity bounds and contested-successor behavior;
- stablecoin allowlist governance and any later bridge-asset change;
- complete AI funding, moderation, biometric, and succession frameworks; and
- any new treasury category, participant benefit, or application-content rule.

Claude should ask focused questions at those boundaries. All other mechanism,
encoding, storage, consensus scheduling, networking, testing, packaging, and
operational choices remain autonomous engineering work subject to the
repository's evidence gates.
