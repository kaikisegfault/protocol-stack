# ADR 0106: Founder answer: the registration limit counts per founder

- Status: Accepted
- Date: 2026-10-20
- Amends: [ADR 0101](0101-founder-answers-on-the-launch-cutoff-an-active-machine-and-the-registration-limit.md),
  answer 3
- Revises, before any layer stores its state:
  [`economy-transition-v10`](../specifications/economy-transition-v10.md)
- Relates to: [`hub-verification-threat-model.md`](../architecture/hub-verification-threat-model.md)
  T5 and T8

## Context

ADR 0101's third answer limits each machine to 1,000 registrations a day. It
reasoned about one compromised machine: "a compromised machine can then admit
at most 1,000 false people a day, which is 1,710 units of entry airdrop".
`economy-transition-v10` keeps the count on each machine-key entry, so the
limit is per machine and nothing else.

On 2026-10-20 the owner forwarded a side agent's note pointing at the
aggregate. One person may hold 1,000 seats, so one founder's machines could
attest **1,000,000 registrations a day**, the whole first-million list, in a
single day. The code and the specification confirm it. Neither ADR 0101 nor the
threat model's T8 considered more than one machine.

ADR 0101 also understated what one false registration is worth. The first
million verified users earn 1.71 units a day for 731 days (ADR 0042), so each
false identity among them can collect up to **1,250.01 units**, not only the
1.71-unit airdrop. A full list of false identities is the whole
1,250,010,000-unit channel, and every real user it displaces loses the benefit.

The chain checks a machine's signature and never the capture, so the
registration limit is the only rate a compromised fleet meets on chain. Whether
to also count per founder changes how fast newcomers can join, which makes it
the owner's.

## The answer

**One founder's machines together register at most 1,000 people a day, however
many seats that founder holds.** The owner chose the recommended option on
2026-10-20. Two were rejected:

- **10,000 a day per founder**, which keeps ten machines' room for large
  holders and still lets a compromised large fleet fill the first million in
  about 100 days;
- **keeping the per-machine count alone**, which leaves one founder's
  compromised fleet able to admit 1,000,000 a day.

## What the answer means for the chain

These readings follow from the answer and ADR 0101 rather than being chosen
beside them. How they are encoded is the revision's work.

- **A founder is the HUB identity that owns the attesting seat**, read from
  the seat entry at the registration's height. Seats are not transferable, and
  legacy succession, the one path that changes a seat's identity, is not
  built.
- **"A day" stays one cycle window of 28,800 heights**, as ADR 0101 reads it.
  The 1,001st registration a founder's machines attest in one window is
  refused.
- **The per-machine limit is implied, not removed.** One machine's count can
  never exceed its founder's, so a cap of 1,000 per founder holds every machine
  to 1,000 as well. Whether the machine-key entry keeps its own count is the
  revision's to decide.
- **The launch key keeps no limit.** ADR 0101 left it unlimited because it is
  the single signer until it retires, and this answer is about founders'
  machines.
- **The limit is still checked after the signature**, so a forgery naming a
  founder whose machines are full is `UNAUTHORIZED`, which is the true reason.
- **Network capacity becomes 1,000 a day per founder with an active machine.**
  After the launch key retires, onboarding is slower when few founders run the
  first active machines. The owner accepted that, together with the rest of
  the trade.

## What it does not do

**It does not stop someone who registers extra founder identities through
machines they control and buys seats under each.** Seats cost the same however
they are spread across identities, so a planned attack is not made dearer.
That case rests on uniqueness and attestation, the threat model's T5 and T4,
both of which owe independent review. This answer bounds a single founder's
fleet, compromised from outside or misused by its owner, which is the case
ADR 0101 meant to bound for one machine.

## Consequences

- **`economy-transition-v10` is revised before anything stores its state.**
  Nothing has: no snapshot, store, application, or network carries a
  version-ten ledger. The order is the specification, then the Python model
  and its re-recorded vectors, then the C++ kernel. The founder count is new
  registry state, with a storage bound at 100,000 founders.
- **M4.3f, the version-ten snapshot, follows the revision**, so it encodes the
  revised registry once rather than twice.
- **ADR 0101's third answer is amended, not withdrawn.** Its figure of 1,000 a
  day stands, and it now holds for each founder as well as each machine.
