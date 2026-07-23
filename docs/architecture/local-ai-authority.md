# Local AI authority

Status: long-term architecture; not part of M1.

## Objective

Operate venture selection and ecosystem management using self-hosted,
purpose-adapted models and node-owned infrastructure while protecting funds and
consensus with deterministic protocol rules.

The design must not require a permanent commercial model API or a fixed model
vendor.

## Feasibility boundary

A dense one-trillion-parameter model requires approximately:

- 2 TB for 16-bit weights;
- 1 TB for 8-bit weights;
- 500 GB for 4-bit weights.

Runtime state, caches, activations, redundancy, and serving overhead add to
those figures. Tightly coupled tensor or expert parallel inference requires
fast, reliable interconnects and homogeneous execution environments. It is not
a suitable workload to stripe across tens of thousands of unrelated,
high-latency internet nodes for each token.

Collaborative inference across consumer machines is a valid research
direction, but it is not an acceptable foundation for time-critical consensus
or unilateral control of funds.

## Target topology

### AI inference clusters

Small numbers of high-bandwidth, GPU-rich node clusters host the largest
models. Multiple independent clusters provide redundancy and disagreement
detection.

### General resource nodes

The broader node network may store content-addressed model shards, process
batch tasks, evaluate proposals, contribute training data or adapters, and
provide asynchronous compute. These workloads tolerate latency and churn.

### Local verifier models

Validators and other important nodes may run smaller specialized models that
check policy compliance, classify risk, compare evidence, or challenge large
model decisions. They do not need to reproduce the full large-model inference.

### Deterministic protocol kernel

The blockchain verifies signed decision envelopes and applies native limits. It
does not execute model inference.

## Venture authority

Community members may submit projects and inspect the resulting evidence, but
they and node operators do not vote on venture acceptance or funding.

The future AI authority is responsible for:

- initial eligibility and quality review;
- acceptance or rejection;
- defining a milestone and funding-tranche plan within allowed policy;
- authorizing a dedicated native venture escrow;
- reviewing source, tests, artifacts, and other milestone evidence;
- accepting or rejecting milestones;
- releasing the next funding tranche;
- pausing, revising within delegated limits, or terminating funding;
- recording reasons and evidence for every decision.

Constitutional protocol changes, supply rules, and emergency recovery are
separate from venture selection. They are not silently delegated merely
because the AI controls venture funding.

## Decision envelope

An AI-authorized action should eventually bind at least:

- unique proposal and replay-protection identifiers;
- authority and capability identifiers;
- policy, model, adapter, and evaluation-manifest hashes;
- requested native action and maximum amount;
- venture, treasury, escrow, milestone, and tranche identifiers;
- evidence and audit-log roots;
- creation height, expiry height, and execution conditions;
- signatures or threshold attestations;
- delay or emergency-containment policy where applicable.

The exact format will be specified and versioned before implementation.

## Authority model

“AI-only venture management” means venture decisions originate only from
accepted AI authority processes. It does not mean a model receives an
unbounded private key.

Native rules retain:

- constitutional supply and mint limits;
- per-capability and per-period spending limits;
- treasury separation and escrow conservation;
- milestone and tranche ceilings;
- timelocks for high-impact actions;
- threshold requirements and independent model diversity;
- deterministic rejection of unauthorized actions;
- complete auditability and emergency containment.

Early research phases retain an owner-controlled recovery path. Removing it is
a separate production decision requiring independent review.

## Model development

Do not hard-code a 700B or 1T parameter target into the protocol. Capability,
latency, energy, reproducibility, calibration, and adversarial robustness are
the relevant requirements.

Prefer:

- an open-weight base model with a documented license;
- ecosystem-specific retrieval and tools;
- parameter-efficient fine-tuning or adapters before full retraining;
- versioned datasets, policies, evaluations, and model manifests;
- benchmark examples of acceptable and unacceptable ventures;
- shadow operation before any authority is granted;
- multiple independent models for high-value decisions.

Model selection and compute scheduling belong outside the consensus protocol so
they can improve without a chain migration.
