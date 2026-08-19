# ADR 0050: The block timestamp is the ecosystem's clock, and months are calendar months

- Status: Accepted
- Date: 2026-08-19

## Context

The owner directed on 2026-08-19 that periods be **real calendar months**: the
1st of each month begins a month, for the monthly best-performer ranking and for
everything else that will later hang off a month boundary. The reason is that
end users understand calendar months and do not understand a rolling count of 30
cycles that drifts against the wall.

Every period in the protocol today is counted in **block heights**, deliberately.
`cycle-boundary-v1` maps windows to heights and M3.4 existed to remove wall-clock
dependence entirely, because two machines must agree on which window a
transaction executed in without agreeing on what time it is.

The owner's further point is that the Founder Machine changes the picture: chain,
server infrastructure, services, and AI are one machine, so the chain has native,
permanent, trustless access to real computation — including a clock — and needs
no external oracle.

**That is right about the architecture and wrong about one mechanism**, and the
distinction is what this ADR records.

## Decision

### 1. The clock is a consensus input, not a read

**No deterministic execution ever reads a clock, a microservice, or anything else
that moves.** Not because chains are traditionally limited, but because of what
replication means: two machines reading their own clocks at the same instant get
different values and would produce different blocks, and a machine replaying
history next year would read *next year's* clock and compute a different state.
Determinism is what makes the history verifiable.

The construction that delivers what was asked:

1. the proposing machine **stamps the time into the block header**;
2. other machines accept it only if it is **monotonic and within tolerance** of
   their own clocks, so a lying proposer is rejected by the honest majority;
3. execution reads **the agreed header field**, never a clock.

The clock is consumed once by consensus and then read deterministically forever.
CometBFT, already this repository's consensus adapter, provides exactly this as
BFT block time, so the mechanism exists and is unused.

### 2. This is the general rule for every real-world input

Every real-world input — the clock, external chain events, uptime measurements,
resource proofs — enters as an **attested claim that consensus agrees on**, then
is read deterministically. Never live, never during execution.

The Founder Machine architecture makes this *better* rather than merely
possible: the attesting set is the validator set, so the ecosystem depends on no
outside service for any of it. That is the substance of "native permanent
oracle", and it is a real improvement over a chain calling out to an oracle
network. What it does not change is that the value must be agreed before it can
be executed against.

### 3. Months are calendar months, derived from the agreed timestamp

A month is the real calendar month. The 1st begins it. Month boundaries are
computed from the consensus timestamp in the header, so every machine agrees on
which month a height falls in by reading a field rather than a clock.

A `calendar-v1` specification will fix the mapping, the boundary rule, the
acceptance tolerance, and the derivation from the header field. It is a separate
slice with its own model and vectors; this ADR fixes only the decision.

**Rejected: a genesis-anchored calendar counting 28,800-block days.** It was
proposed here first and it is deterministic, but the chain's day only equals a
real day if block production hits its 3-second target exactly. At 1% slow it
drifts about a week over a two-year distribution, so "the 1st" would slide
against the world's 1st and keep sliding. The owner's push to use the machine's
own clock removes this entirely, because a consensus timestamp is corrected every
block instead of accumulating error from genesis. **The rejected option is
recorded because it is the obvious one and it is worse.**

**Rejected: a time oracle.** An external service that tells the chain the date is
precisely the outside dependency the architecture forbids.

## Consequences

**Month boundaries are exact rather than approximate.** This is the direct gain
over the genesis-anchored alternative, and it is why the decision improves on
what this ADR was originally going to say.

**The consensus adapter now carries a consensus-critical field.** The header
timestamp, its monotonicity rule, and its acceptance tolerance become
consensus-visible, so they belong in the specification rather than in adapter
configuration. Initial consensus integrations remain replaceable adapters, so the
rule must be stated in a way any adapter can satisfy rather than by deferring to
CometBFT's implementation.

**Cycle windows stay in block heights.** Nothing about the 28,800-block window,
the 24 hourly slots, `slot_of`, or the posture predicate changes. Heights remain
the unit for everything that must be indifferent to the clock; the timestamp is
introduced only where a human-facing period is required. Mixing the two units is
the mistake this separation exists to prevent.

**The tolerance is a new attack surface, bounded rather than eliminated.** A
proposer can move the stamp within the accepted tolerance, so a month boundary
can be nudged by at most that tolerance by whoever proposes the block at the
boundary. The tolerance must therefore be small relative to a month, and the
specification must state it as a consensus parameter rather than leave it to an
adapter default.
