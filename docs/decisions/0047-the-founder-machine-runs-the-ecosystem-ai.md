# ADR 0047: The Founder Machine runs the ecosystem AI, and the company runs no backend

- Status: Accepted
- Date: 2026-08-19

## Context

The constitution has said since M1 that there is **one logical ecosystem AI**,
that it is **hosted by the company on centralized, self-operated AI
infrastructure**, and that **Founder Nodes do not run AI models**. `CLAUDE.md`
repeats the last clause as a standing architectural constraint: "Do not require
AI inference on Founder Nodes. The logical Ecosystem AI is a company-hosted
control plane with separately bounded capabilities."

That was a reasonable reading of 2026. Open-weight models were not good enough
to carry institutional judgment, and serving them needed data-centre hardware.

**The owner reversed it on 2026-08-19**, and the reason is that the premise
expired. Open-weight models are now strong enough, they keep improving, and a
local machine or a rented unified-memory server can host one continuously. A
company-operated AI data centre is therefore no longer a technical necessity —
it is only a centralization the ecosystem would have to live with.

The reversal is larger than where inference runs. It settles what a Founder
Machine *is*: not a validator with some services attached, but the **entire
infrastructure the ecosystem ever uses**.

## Decision

### 1. There is no company backend, and there never is one

**The company runs no server, no hosted service, and no external infrastructure
of any kind. The Founder Machine is the only infrastructure that exists.** Every
website, frontend, backend, application, dapp, ecosystem service, and AI
workload runs on Founder Machines.

This applies from the beginning rather than after a migration. Where the company
needs capacity to operate the ecosystem, it buys Founder Seats and runs Founder
Machines like anyone else — the owner's expectation is roughly the first 100
seats, used to run the system during its initialization.

**Rejected: a company backend that shrinks over time.** Every system that has
tried this kept the backend. The migration is always the next quarter's work,
the backend accumulates the features that are awkward to decentralize, and it
becomes the thing the ecosystem cannot be run without. Refusing to build the
first one is the only version of this decision that is enforceable.

### 2. Every Founder Machine runs an open-weight model continuously

A Founder Machine runs an open-weight model **24 hours a day**, inside the same
single atomic process as everything else it does. It is not an optional add-on
and not a separate product; it is part of what the machine is.

**Two districts, and they do not mix.**

**The founder's personal assistant.** Each *identity* has exactly one assistant:
one name the founder assigns, one profile, one accumulated understanding of that
person. It reaches them through their phone, connects whatever third-party
services they attach — email, Discord, Telegram, WhatsApp and the rest — for
context and communication, and it can make transactions in the ecosystem on
their behalf.

**Its concurrency is the seat count.** One identity holding 100 seats still has
**one assistant**, but may run **100 parallel live sessions** of it. One seat is
one continuous session. The distinction is deliberate: seats buy capacity, not
additional identities, so a founder never fragments into several assistants who
each know part of them.

**The ecosystem district.** The same model, under its framework, evaluates
everything the protocol cannot decide deterministically — the submissions,
deployments, funding judgments, and moderation decisions the constitution
already assigns to the Ecosystem AI.

### 3. A judgment is made by the nearest machine, after its neighbours reason

The machine nearest the requester is assigned. Before deciding it reads the
reasoning of its **nearest neighbours — up to six, so seven models reason in
total**. Neighbours know the decision is not theirs; they produce reasoning
reports. The assigned machine reads them alongside its own and issues one
signed, bounded decision.

Seven reasoners over an immediate neighbourhood is chosen for cost: a
one-hop neighbourhood rather than a transitive one keeps latency and compute
bounded while giving the deciding model several independent readings to weigh.

**AI still cannot decide consensus, and moving it onto the machines changes
nothing about that.** Two models will disagree — different weights,
quantization, hardware, and sampling — so an AI output can never *be* the
consensus state. It is a signed, bounded claim that deterministic rules verify.
That constraint predates this ADR and survives it unchanged.

### 4. The initialization stage, and what ends it

During an **initialization stage** of roughly one to two years the company fixes
the model, the framework, the protocol, and the update schedule. **A founder
never chooses which model or framework their machine runs**, at any point.

After it, one self-improving model is deployed and **everyone including the
company renounces total control to it**. Deterministic chain services stay
deterministic; the AI manages what needs managing, including protocol and
framework improvement once it is capable of carrying that responsibility.

The company holds development authority during initialization. It does **not**
hold biometric data, user data, or any backend at any point.

This is recorded as the direction of travel. Nothing is built toward it now.

### 5. The founder does nothing, and defects are the company's

The machine is **plug and play and has no intervention surface**. Founders run
it; they do not operate, configure, tune, or maintain it.

It follows that **a software defect is not the founder's fault**. If the machine
was running, the infrastructure requirements were met, and no intervention
occurred, then a failure caused by the software is auto-reported and logged, the
founder is **still paid for the cycle**, and the fix ships to the **whole fleet**
in the next update batch — because every machine runs the same software, so a
defect observed on one is a defect present on all. Intervention voids this.

## Consequences

**`founder-constitution.md`'s AI section is rewritten and `CLAUDE.md`'s
constraint is inverted.** "Founder Nodes do not run AI models" becomes its
opposite, and "the logical Ecosystem AI is a company-hosted control plane"
becomes "the ecosystem AI is the population of Founder Machines."

**The hardware floor rises and becomes founder-directed.** A machine that serves
an open-weight model continuously needs unified memory, which
[ADR 0052](0052-the-founder-machine-specification.md) fixes at 512 GB minimum.
That figure decides who can afford to participate, which is why it is founder
decided rather than derived.

**"Node" is the wrong word and the owner prefers "Founder Machine."** A node
implies a validator; this is a validator, a server, a host, an AI home, and the
ecosystem's only infrastructure. The preference is recorded here and the
repository is **not** renamed now — a mass rename across specifications,
vectors, and models would cost a slice and change no behaviour. New text uses
Founder Machine.

**Judgment latency now depends on a neighbourhood.** Seven models reasoning is
seven models' compute per decision, and the assigned machine waits on its
neighbours. Bounding the neighbourhood at one hop and six peers is what keeps
that affordable, and it is a figure a later measurement may revise.

**Nothing in the consensus kernel changes.** No transition, encoding, or state
entry is affected by this ADR. What changes is what a Founder Machine is
required to run and who is permitted to run it, which is constitution and
specification work rather than protocol work.
