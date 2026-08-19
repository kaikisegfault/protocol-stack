# Ecosystem AI authority

Status: long-term architecture; not part of the current operational goal

> **Reversed on 2026-08-19 by
> [ADR 0047](../decisions/0047-the-founder-machine-runs-the-ecosystem-ai.md).**
> This document was written when the ecosystem AI was company-hosted and Founder
> Nodes ran no models. That direction is withdrawn: every Founder Machine now
> serves an open-weight model continuously and the company hosts no AI
> infrastructure at all. The sections below are corrected where they stated the
> old placement; the containment, envelope, delegation, and availability
> reasoning is unaffected, because it was always about what a signed decision may
> authorize rather than about where inference happened.

## Meaning of local and singular

“Local AI” means hosted inside the ecosystem for the exclusive use of the
ecosystem — and as of 2026-08-19 that means **served by the Founder Machines
themselves**. A model runs on every Founder Machine, alongside its deterministic
blockchain and resource services. The company hosts none.

There is one logical Ecosystem AI authority. It may use several models,
specialized workflows, and serving replicas across the machine population, but
users do not face competing AI governments and Founders or community members do
not vote to replace an AI case decision. Singularity is of framework and policy,
not of process: **a judgment is made by the machine nearest the requester, after
reading the reasoning of up to six nearest neighbours — seven models in total.**
Neighbours advise; the assigned machine decides and signs.

Logical singularity does not imply one process, one unrestricted key, or one
failure domain. Biometric, moderation, venture, grant, developer, and other
roles use separately scoped protocol capabilities.

## Placement

Inference runs on the Founder Machines, on the unified memory
[ADR 0052](../decisions/0052-the-founder-machine-specification.md) requires. Model
choice, serving, retrieval, tools, training, evaluation, and policy execution
remain outside blockchain consensus, and no machine ever has to reproduce
another's probabilistic output — which is why moving inference onto the
machines changes nothing about determinism.

**A founder never chooses the model or the framework.** The company fixes both
during the initialization stage of roughly one to two years; afterwards the
ecosystem AI manages model selection, and at the end of initialization a
self-improving model is deployed and everyone including the company renounces
total control to it.

The chain receives only small, versioned, signed decision envelopes and
deterministically decides whether the requested action is authorized.

## Responsibility groups

### Founder biometric verification

**Corrected on 2026-08-19 by
[ADR 0048](../decisions/0048-hub-verification-runs-locally-with-an-ai-integrity-monitor.md):
the model never decides identity.** HUB verification runs as a deterministic,
sandboxed, offline process on the founder's own machine, and the local model is
that process's *integrity monitor* — it evaluates whether the run was initiated
fairly and fed genuine inputs, and may dispute it and force re-initialization.

For every other sensitive action — recovery, legacy claims, and sensitive
withdrawals — the AI evaluates the evidence as described here. The
decision must bind the seat, biometric identity record, requested action,
manager address, challenge, policy version, creation point, and expiry.

Raw biometric evidence and private identity linkage remain outside public
consensus state. The blockchain does not infer a face match.

### Venture and treasury management

The AI may:

- evaluate raw concepts and existing application builds;
- accept or reject an eligible project;
- propose a bounded milestone and funding-tranche plan;
- authorize a dedicated native venture escrow;
- review code, tests, artifacts, and delivery evidence;
- accept, reject, or request revision of a milestone;
- release a permitted tranche;
- pause or terminate future funding; and
- record reasons and evidence commitments for audit.

Equivalent bounded workflows manage community grants, developer incentives,
bug bounties, and later owner-approved treasury programs.

### Application admission and updates

The AI admits complete projects to the controlled runtime and evaluates later
versions. Creators never receive direct production mutation or delete access.
Product creation within an accepted project follows that project's approved
deterministic guardrails.

### Moderation

AI moderation controls presentation and service eligibility without rewriting
canonical history. The founder-directed initial content objective is to block
NSFW material rather than apply broad political or viewpoint filtering. The
complete policy, appeals, evidence retention, and legally required behavior
remain a future owner-approved framework.

## Protocol containment

Every AI action must name one exact capability and source. Native rules retain:

- the maximum supply and issuance-channel caps;
- Founder Seat capacity, price, identity, and economic rules;
- commercial and fee routing;
- separate treasury and escrow custody;
- per-decision, per-program, and per-period spending limits;
- milestone and tranche ceilings;
- policy, model, adapter, and evaluation-manifest versions;
- replay protection, expiry, delay, and failure atomicity;
- complete receipts and evidence roots; and
- upgrade and emergency powers outside ordinary AI capabilities.

Compromise of a moderation capability cannot release funds. Compromise of a
venture capability cannot mint, change a fee, enroll a seat, alter a model
policy, or upgrade the protocol.

## Decision envelope direction

A future canonical envelope should bind at least:

- chain, protocol, and envelope versions;
- unique decision, action, and replay identifiers;
- AI authority, role, and capability identifiers;
- policy, model, tool, adapter, and evaluation-manifest commitments;
- exact requested native action and maximum amount;
- project, program, treasury, escrow, milestone, and tranche identifiers;
- evidence and audit-log commitments;
- creation height, expiry height, and execution conditions;
- signer and verifier evidence; and
- any required delay or containment policy.

The exact bytes, cryptographic suite, key custody, limits, and state transitions
require a canonical specification and threat model.

## Establishment and delegation

The company selects models and controls AI policies initially. Authority moves
to AI in explicit stages:

1. offline evaluation against historical cases;
2. shadow recommendations with no execution capability;
3. bounded low-value actions with company-observed outcomes;
4. separately delegated production programs; and
5. later sole-AI authority for mature scopes where the constitution requires
   human decisions to disappear.

Delegation of one scope does not delegate another. An AI may recommend a
protocol upgrade but cannot authorize it through an ordinary program key.

Changing the AI model or framework remains a company responsibility during
establishment. Future AI approval of its own successor, irrevocable scope
delegation, and removal of company recovery are distinct founder decisions
requiring independent evidence.

## Availability behavior

If AI infrastructure is unavailable, AI-managed admission, moderation
decisions, biometric approvals, and escrow spending pause. The protocol keeps
validating deterministic transactions and preserves custody. It does not
silently lower authorization or transfer judgment to Founders, staff, or a
community vote.

Geographic replicas, versioned model artifacts, replayable tools, queues, and
disaster recovery reduce downtime without changing the authority model.

## Model-development direction

Do not hard-code a parameter count or vendor into consensus. Prefer measurable
capability, calibration, robustness, reproducibility, latency, and cost targets.
Model manifests should identify weights, license, datasets, adapters, retrieval
sources, tools, policies, evaluations, and serving configuration.

Ecosystem-specific retrieval and tools, parameter-efficient adaptation,
versioned evaluation suites, adversarial cases, and shadow operation precede
high-value authority. Model serving remains replaceable; signed protocol
capabilities remain stable.

## Unresolved production work

Before real authority, the project still needs:

- the owner-approved complete AI framework for each role;
- biometric, moderation, funding, and application threat models;
- decision-envelope encoding and reviewed cryptography;
- model and policy update, rollback, and recovery rules;
- measurable evaluation and failure thresholds;
- private evidence storage and access controls;
- incident containment and audit procedures; and
- independent AI-control and protocol review.
