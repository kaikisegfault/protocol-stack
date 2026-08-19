# ADR 0052: The Founder Machine specification

- Status: Accepted
- Date: 2026-08-19

## Context

Since M3.5 the repository has recorded an open founder-reserved question: **what
must a Founder Machine operator prove they hold in order to be paid?** The uptime
pipeline measures liveness of a responder rather than possession of a resource,
and every anti-gaming property it claims inherits that limit. The concrete
resource commitment was left unspecified because it decides who can participate.

[ADR 0047](0047-the-founder-machine-runs-the-ecosystem-ai.md) makes the question
urgent: a machine that serves an open-weight model continuously, holds the
identity set, runs the ecosystem's services, and validates the chain is not a
commodity virtual server.

The owner fixed the figures on 2026-08-19.

## Decision

### 1. The server-infrastructure baseline

Per machine, as the hosting and services tier:

| Element | Minimum |
| --- | --- |
| Architecture | x86_64, Xeon-class server processors |
| Compute | 8 vCPU |
| Memory | 64 GiB |
| Storage | 1 TB NVMe SSD, gp3-class performance |
| Network | 12.5 Gbps baseline |

This tier carries the backend, hosting, and ecosystem services, and may be
subdivided into many distinct micro-services. No operator reads or controls what
runs there; the AI is the live gate on anything deployed onto it.

### 2. Unified memory for the model: 512 GB minimum

**Separately from the tier above**, a Founder Machine provides at least **512 GB
of unified memory** for the open-weight model.

The figure is the owner's and is deliberately not the cheapest workable one. It
runs a frontier-class open model locally rather than a small one, and it is
chosen against a four-year horizon in which model quality keeps rising. It is
expected to rise during the first two years rather than fall.

**Rejected: 128 GB.** It was recommended here as a real product tier that runs a
70B-class model at 4-bit. The owner rejected it as too low for a machine whose
whole purpose is to be an AI home, and on the reasoning that 512 GB is already a
current standard and will be commodity within a year. The rejection is recorded
because the recommendation was wrong in the direction that matters: it optimized
for entry price against a requirement that exists to buy capability.

**A founder never chooses the model or the framework**, at any point. The company
fixes both during initialization and the ecosystem AI manages them afterwards.

### 3. Rented capacity satisfies the requirement

An operator may **rent** unified-memory capacity rather than own it. This is
explicit rather than implied: at the seat schedule's early prices the hardware
costs far more than the seat, and renting turns that into an operating cost. It
is the expected path for early founders.

### 4. Machines are distributed from pooled sale proceeds, not per-seat price

Every seat eventually receives **the same machine**, whether it cost USD 100 or
USD 91,900. Until then a founder self-provisions or rents; that is the trade-off
of being early.

The economics are pooled rather than per-seat. Full sale proceeds are
USD 4,231,855,000 across 100,000 seats — **USD 42,319 per seat on average** —
against a fully-loaded machine cost the owner estimates at no more than
USD 20,000 including production and delivery, leaving roughly half as company
revenue.

Physical production begins once the ecosystem has roughly 10,000 to 12,000 daily
active founders, and distribution is **staged over time in step with growth**:
first to the year's best performers, roughly the first thousand, and outward from
there.

## Consequences

**The obligation is linear and the revenue is quadratic, so they cross at seat
54,800.** Machines owed grow with seats sold; revenue grows with seats sold times
a rising price. Before the crossover the promise is underfunded, worst at about
30,000 seats:

| Seats sold | Revenue | Machines at USD 20,000 | Gap |
| ---: | ---: | ---: | ---: |
| 10,000 | USD 6.4M | USD 200M | −USD 194M |
| 30,000 | USD 245M | USD 600M | −USD 355M |
| 54,800 | USD 1,097M | USD 1,096M | breakeven |
| 90,000 | USD 3,362M | USD 1,800M | +USD 1,562M |

This is a business fact rather than a protocol one, and the owner has accepted it
knowingly: **staged distribution is what makes it work**, because machines ship
against later proceeds rather than to everyone at the production start. It is
recorded so the number is known now rather than discovered at 30,000 seats. The
owner also notes there is no secondary market for seats, so early sales are not
suppressed by resale supply.

**Requirement 12's open item is closed.** "What an operator must own to be paid"
now has an answer, and the duty measurement can be extended to prove the resource
rather than only the responder — which is what M3.5 recorded as missing.

**The floor decides the founder population.** A machine of this class is a serious
commitment, and that is the intent: founders are stakeholders in the ecosystem
rather than casual participants. The recorded consequence is that the ecosystem's
capacity is bounded by how many people will make it.

**One figure remains uncomputable.** Whether a machine pays for itself depends on
the native asset's price, and the asset has no price. No payback period is stated
here because any figure would be invented.
