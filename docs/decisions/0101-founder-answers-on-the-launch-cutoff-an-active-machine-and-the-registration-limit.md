# ADR 0101: Founder answers on the launch cutoff, an active machine, and the registration limit

- Status: Accepted
- Date: 2026-10-09
- Completes: [ADR 0100](0100-founder-answers-on-who-verifies-and-how-registration-starts.md)
- Relates to: [`first-goal.md`](../project/first-goal.md) requirement 3,
  [`hub-verification-threat-model.md`](../architecture/hub-verification-threat-model.md)
  T8

## Context

ADR 0100 left one founder value open: how many active machines retire the
company's launch key. Running the founder-decision gate for
`economy-transition-v10`, the contract version that will carry requirement 3,
found two more decisions the accepted documents do not distinguish between:

- **What counts as an active machine.** It decides who may verify people, and
  it is what the cutoff counts.
- **Whether one machine's registrations are capped, and at what.** The threat
  model's T8 named this as a candidate whose value is the owner's, because a cap
  changes how fast newcomers near a busy machine can join.

## The answers

The owner answered all three on 2026-10-09, choosing the recommended option
each time.

1. **The launch key retires for good once 100 machines are active.** That is
   the first price block of 100 seats at USD 100 each. The company's direct
   signing ends as early as availability allows. 1,000 and 10,000 were
   rejected, because each keeps the company as the chokepoint longer.
2. **An active machine is one whose seat met its most recently assigned cycle,
   read from the chain's own uptime record.** A failing or abandoned machine
   stops verifying on its own and resumes when it meets a cycle again, and no
   one needs authority to revoke it. Two options were rejected. "Any activated
   seat" would leave an abandoned machine verifying until someone with
   revocation authority acted. A count over recent cycles would be slower to
   drop a machine that has gone bad.
3. **Each machine may register at most 1,000 people a day.** A compromised
   machine can then admit at most 1,000 false people a day, which is 1,710
   units of entry airdrop. An honest machine would not reach it: that would be
   one verification every 86 seconds, around the clock. A cap of 100 and no cap
   were rejected.

## What the answers mean for the chain

These readings are mechanism, derived from the answers rather than chosen
beside them.

- **"Met" is the uptime test: 18 hours of fully operational time.** The
  accumulation cap does not change it. The cap treats a capped day as failed
  only for distributing that day's generation, and the answer reads the uptime
  record, not the distribution. So a seat at the cap whose machine ran all day
  is active. A seat past its 731 cycles is active too, because ADR 0049 keeps
  it ranked and measured.
- **Version nine does not store it.** A cycle-assignment record's `accrued` bit
  means met, in span, and under the cap. Its `winner` bit means won. Each
  window's uptime records are deleted once it is assigned. So
  `economy-transition-v10` must record, for each registered machine, the last
  window in which its seat met the cycle. It must also keep a count of active
  machines, which the cutoff reads.
- **A new machine is not active until its first cycle is assigned and met.**
  A seat is in scope from the window after its activation, and a window is
  assigned two windows after it opens. So a newly activated seat's machine
  verifies nobody for its first two to three days.
- **The cutoff is reached at an assignment.** When the active count first
  reaches 100, the chain records the launch key as retired in that same block.
  A later fall below 100 never revives it, which is how ADR 0100 reads "for
  good".
- **"A day" is one cycle window of 28,800 heights.** The limit counts the
  registrations a machine's key signed that executed in the current window, and
  the 1,001st is refused. The launch key has no daily limit, because ADR 0100
  makes it the single signer until it retires.

## Consequences

**`economy-transition-v10` is fully determined at the founder level for
requirement 3.** Every rule a participant would feel is now an answer. What
remains is specification: the registry's entries and transactions, the
attestation that admits a machine key, the single-use approval construction
for requirement 5, and the storage bounds.

**The cutoff is reachable only after real operation.** One hundred machines
must each meet a cycle, which is a measured day. So the launch key signs at
least through the network's first measured windows, whatever sells first.
