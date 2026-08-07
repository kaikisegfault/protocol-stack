# ADR 0023: Activity, performance, referrals, and the revised maximum supply

- Status: Accepted founder direction; supersedes the economic figures in ADR
  0017 and the unresolved markers in ADRs 0018 and 0022
- Date: 2026-08-07

## Context

M2 closed with four founder-reserved decisions recorded as unresolved and
supplied to the models as bound research inputs: whether an inactive referred
cycle creates the referral permission, direct-channel eligibility, the Founder
activity metric with its grace allowance and performance ranking, and the AI
funding framework.

The first M3 slice would have had to turn `evaluate_base_permission` into a
consensus transition, at which point a supplied fixture must become a rule. The
owner supplied the decisions on 2026-08-07 rather than let that boundary be
reached with an invented value.

One of them could not be accepted as stated without a second decision. Doubling
the referral channel to 10% of the operator benefit needs 1,250,010,000 native
units that the 55,743,940,100 maximum did not contain, so the owner was asked
where they come from and chose to raise the maximum.

## Decision

### The maximum supply becomes 56,993,950,100

```text
55,743,940,100  ->  56,993,950,100 display units
                    5,699,395,010,000,000,000 atomic units
```

The atomic maximum remains far inside `u64`, so the accepted eight-decimal
denomination is unchanged and no arithmetic widens.

The Founder Constitution calls this maximum permanent, and it remains so — from
genesis. The revision is available now only because the project is research
software: no native unit has been issued, no holder exists, no C++ consensus
enforces a supply figure, and the accepted M2 models activate nothing. This is
the last point at which such a change costs nothing, and the constitution now
says so explicitly rather than leaving "permanent" to be quietly reinterpreted
later.

The alternatives offered were funding the increase by cutting the operator leg
from 342 to 307.8, by removing the HUB-verified-user channel, or by halving
liquidity mining. Each preserved the old maximum at the cost of a programme or
of Founder income, and the owner selected the supply revision over all three.

### Founder referral doubles, becomes unconditional, and moves to direct-mint

The referral benefit is 34.2 units per cycle, 10% of the 342-unit operator leg
rather than 5%, lifting the channel cap to 2,500,020,000.

It no longer depends on the referred seat's activity. A referrer cannot
operate, repair, or influence someone else's machine, so a benefit that
evaporates when that machine fails would penalise the referrer for an event
outside their control.

It is therefore no longer part of the base permission and no longer settles
through the referred seat's cycle evaluation. It is a direct-mint channel whose
beneficiary mints on its own schedule. Its eligibility is the recorded referrer
relationship, which the ledger already holds, so unlike the other direct-mint
channels it needs no eligibility policy.

### Unreferred seats fund a monthly performance pool

A seat bought without a recorded referrer contributes its 34.2 units per cycle
to an unreferred performance pool, paid monthly to the best-performing nodes.

This is what makes the channel exact. Every seat contributes to exactly one of
the two destinations, so:

```text
100,000 seats x 731 cycles x 34.2 = 2,500,020,000
```

The channel is consumed to the unit with no leftover, which was the owner's
stated goal. The alternative — leaving unreferred allocations unissued — would
have made the realised maximum depend on how many buyers happened to arrive
through a referrer, so the stated maximum would have been unreachable in
practice.

### A cycle is met at 18 hours of fully operational uptime

A Founder Node is one enclosed all-in-one service with no partial mode. Fully
operational means every component healthy at once: the blockchain node,
validator duties, transaction servicing, application compute and storage and
delivery, and the workload and health agents. Any degraded component makes the
period downtime.

A cycle is met at 18 hours or more of cumulative fully operational uptime, and
fails when cumulative downtime exceeds 6 hours. The allowance is fragmentable,
so six one-hour outages and one six-hour outage are treated identically.

The owner stated the threshold as "more than 18 hours" and the allowance as
"6 hours", which leave the exact boundary ambiguous. It is resolved in the
operator's favour: exactly 6 hours of downtime passes, because an allowance a
founder cannot fully use is not the allowance they were promised.

### Performance reallocation goes to the highest uptime that cycle

The failed seat's 342-unit portion goes to the node or nodes with the highest
cumulative fully operational uptime in the same cycle — whatever that maximum
turns out to be, not a fixed perfection bar. Ties at the maximum share equally,
which is the ordinary outcome when many nodes reach a full 24 hours.

Two bounds are added that the owner's statement implies but does not say. A
winner must itself have met the cycle, so a failed seat never rewards another
failed seat; and the integer remainder of an equal split carries forward rather
than being burned, matching the residue rule `revenue-routing-v1` already uses.

Settlement occurs when the failed seat next exercises a permission, in the same
atomic transition that credits the escrows and the System Creator. A seat that
never exercises never triggers the reallocation and the units are never
created, which is consistent with the accepted rule that unexercised
permissions do not exist.

### Uptime is derived and challenged, not self-reported, and the AI cannot freeze payment

Software running on hardware its operator controls can be patched, replayed, or
simulated. An enclosed non-configurable binary raises the cost of forging a
health report but does not make the report trustworthy, because the adversary
owns the machine it runs on.

The design therefore separates what can be proved from what cannot:

- validator participation and transaction servicing are derived from on-chain
  records, which the chain already observes and which cannot be forged;
- resource provision is proved by challenge-response, so a node must actually
  hold and serve what it claims; and
- the Ecosystem AI reviews results and may file a bounded signed dispute within
  a fixed window, with silence finalising the result.

The AI's signature is deliberately not a precondition for payment. The owner's
initial framing had the AI perform "final signing", which would have made an AI
outage or a company decision freeze every Founder's income and would have made
the company the effective owner of the reward path. A dispute window inverts
the failure mode: when the AI is unavailable, results stand and founders are
paid.

Hardware-backed attestation is unavailable until dedicated Founder machines
exist in M12, so until then challenge-response and the dispute layer carry the
anti-gaming burden. That gap is stated rather than closed.

### AI capacity is sized by request rate, not by seat count

The owner proposed provisioning the company data centre for one dedicated AI
instance per seat plus 25%, on the assumption that 100,000 seats implies 100,000
parallel models.

One check per node per day is a small workload. At roughly 3,000 input and 300
output tokens per check, 100,000 daily checks are about 350 output tokens per
second sustained, which a single well-configured multi-GPU serving node handles
with headroom. The correct sizing unit is peak concurrent request rate times
latency, not seat count; sizing by seat count would over-provision by orders of
magnitude.

Model selection is deferred to M6. Frontier open-weight mixture-of-experts
models are the right category, but the landscape will move before that
milestone and the choice should be benchmarked then rather than pinned now.

## Consequences

- `founder-economy-manifest-v1` and every model, vector, and digest derived
  from it are superseded as founder direction. They remain accurate records of
  what was built and verified against the previous direction, and are not
  rewritten. The M2 proof stands as evidence about v1.
- A `founder-economy-manifest-v2` and a revised simulator are now the first M3
  work, ahead of the canonical encoding specification, because the referral
  relocation and the derived activity rule change which transitions exist
  rather than only their parameters.
- The referral is no longer a permission created by a seat's cycle evaluation,
  so the `evaluate_referral_permission` transition and its
  `inactive_referral_result` research input both disappear in v2.
- `evaluate_base_permission` gains a derived activity input and a derived
  winner set, replacing two supplied research placeholders with consensus
  computation over on-chain records and challenge responses.
- The unreferred performance pool is a new beneficiary inside the referral
  channel rather than a new channel, so the cap arithmetic stays exact.
- Three of the four recorded founder-reserved decisions are closed. Only the
  remaining direct-mint channel eligibility and the AI funding framework stay
  open, and neither blocks M3's first slices.
- Nothing in this ADR changes running behavior. No C++, consensus, devnet,
  model, vector, or digest is modified by the slice that records it.

## Compatibility and independent review

This ADR records founder direction and activates nothing. The revised figures
are not consensus values until a `founder-economy-manifest-v2` specification,
model, vectors, and verifier are accepted.

M3 must separately specify the challenge construction and sampling rate, the
dispute window length and resolution, the definition of a month in cycles for
the unreferred pool, whether a referrer must itself hold a Founder Seat, the
storage bound on per-cycle uptime records, and the cycle boundary in heights or
epochs.

The anti-gaming position stated here is a design intent, not a proof. An uptime
scheme that survives adversarial founders with physical machine access requires
independent security review, and no such review has occurred.
