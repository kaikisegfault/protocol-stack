# Economy scenario suite v4

Status: Accepted M3 evidence contract. It is not a consensus transition and not
a new model.

This document fixes the multi-year population scenario that the contract the
chain executes, [`economy-transition-v9`](economy-transition-v9.md), must
survive. It closes the gap
[`founder-economy-devnet-audit-v1.md`](../project/founder-economy-devnet-audit-v1.md)
found in requirement 14.
[ADR 0095](../decisions/0095-the-fourth-scenario-suite-drives-the-chains-contract.md)
records the alternatives and the decision.

It changes no M1 bytes, C++ state, configured devnet supply, accepted schema,
vector, or digest of any earlier contract. It adds one public function to the
version-nine model, `block.open_window`, which runs the prologue that already
exists.

## Why a fourth version

`economy-scenario-suite-v3` drives `founder-economy-simulator-v3`. That
simulator still keeps the per-channel carry, and it has none of the three rules
the chain gained since:

- the recovery pool (ADR 0049, ADR 0054);
- activity decided from measured uptime (version eight);
- the unreferred pool paid by calendar month (`unreferred-pool-payout-v1`,
  version nine).

So the M2 standard's central claim — every channel ends where the manifest says,
across every seat's whole life — had not been made for the rules the chain
executes. Version four makes it.

## Relationship to version three

[`economy-scenario-suite-v3.md`](economy-scenario-suite-v3.md) is not edited, and
`test-vectors/economy-scenario-suite-v3.txt` remains normative and passing.

**Only scenario 1 is rebound.** Version three's other three scenarios stay
there, for these reasons:

- **Scenarios 2 and 3**, seat concentration and routing population, are the
  market leg. The Founder Seat sale and revenue routing models import nothing
  from any economy package, so they are the same evidence under any economy
  contract. Their ctest entries, `scenario-market` among them, keep running.
- **Scenario 4**, the escrow drain, binds `escrow-payout-v3`. The chain does not
  execute escrow payout; it is founder-reserved later-milestone work (the
  audit's independent-review item 7). No current-contract state exists to bind
  it to.

## What is driven and what is supplied

**The chain itself cannot be driven over a whole distribution.** Every height
issues and expires challenges, so 731 windows are 21 million blocks.
`advance_to` refuses to skip heights once a seat is active, for that reason.

**The settlement can be driven.** `simulation/economy_transition_v9/block.py`
now exports `open_window(ledger)`. It runs version nine's prologue at a
window-opening height the caller has set, in the accepted orders:

- the assignment, with version seven's recovery pool;
- the monthly settlement;
- the referral accrual;
- the figure accumulation;
- the deletion;
- the window-month write.

It calls `_prologue`; nothing is copied out of it. `execute_block` remains the
only thing a chain runs.

**Every participant action is a signed transaction.** Admission and execution
use the version-nine model at the height the schedule names. That covers kinds
10 (register), 2 (purchase), 3 (activate), 4 (mint node), 22 (mint monthly
pool), and 5 (mint referral).

**What is supplied is exactly what a window's challenges would have written:**
the kind-19 record of each in-scope seat that lost a slot or had one voided. It
is written once the window closes and before its assignment reads it. A seat
with a full credit gets no record, which is how the contract reads absence.
Everything else is derived by the contract: who met, who won, what the pool
took, where a referral leg went, which month a window belongs to, and who a
month paid.

## The fixture

**Every value in this section is research, not a founder value.** The legs, the
threshold, the cap, the lag, and the 731 cycles are read from the contract.

| Field | Value | Why |
| --- | --- | --- |
| Genesis | 2027-01-01T00:00:00Z | window `w` opens at the start of day `w` |
| Block rate | 3,000 ms | the commit target, so a window is one day |
| People | 6 | person 5 owns no seat and only refers |
| Seats | 0:(0), 1:(1, by 0), 2:(2, by 5), 3:(0), 4:(3, by 5), 5:(4, by 1) | `seat:(owner, by referrer)`; person 0 owns two seats and refers a third |
| Activation | window `61k`, height `61k·28,800 + 100 + k` | six lives in six phases |
| Keeper | seat 0 | the one machine at 24 hours after every life ends |
| Tail | 20 hours for every other seat | so the drain window has one winner |
| Outage | every window with `w mod 101 = 57` | nobody credited, nobody meets |
| Kind 4 | every 20 windows, phase 3 from activation | under the cap |
| Kind 22 | with kind 4, except seat 3 | seat 3 collects every month's claim at the end |
| Kind 5 | every 20 windows, phase 10, from the referrer's first accrual plus 2 | under the cap |
| Seat lapse | seat 2 skips kind 4 in windows 400–459 | exceeds the cap |
| Referrer lapse | person 5 skips kind 5 in windows 500–559 | exceeds the cap |
| Last round | window 1,067 | every seat, claim, and referrer collects |

Seat `k`'s first cycle is window `61k + 1`, and its last is `61k + 731`. The last
life ends in window 1,036, and window 1,037 is the drain. The run ends at the
first window whose opening settles the drain window's month, November 2029. That
is window 1,067, and every window from 0 to 1,067 is checked.

**Every referrer's first accrual lands after window 30**, at windows 62, 123,
and 306. That is the case ADR 0094 repaired, run at population scale.

### The uptime pattern

In window `w` up to 1,036, seat `s`'s residue is `(7w + 11s) mod 29`:

| Residue | Credited slots | Disputed | Hours | Meets |
| ---: | ---: | ---: | ---: | --- |
| 0 | 12 | 0 | 12 | no |
| 1 | 17 | 0 | 17 | no, one hour short |
| 2–9 | 18 | 0 | 18 | exactly the threshold |
| 10–17 | 22 | 1 | 21 | yes |
| 18–24 | 23 | 0 | 23 | yes |
| 25–27 | 24 | 0 | 24 | yes, no record written |
| 28 | 24 | 6 | 18 | a maximal dispute of a perfect record |

Credited slots are the low bits of the 24-slot bitmap. The disputed ones are the
lowest of those, so the disputed set is always a subset.

**February 2028 has 29 windows, and 29 is the pattern's modulus.** Every seat
passes through every residue exactly once that month, so all six have the same
figure and the month's pool is split six ways. Leap months and ties are
therefore on the path together.

## The four claims

Each is checked at every window, not once at the end, because a unit lost and
later restored is still a defect.

1. **Every Founder Node channel delivers what the manifest promised for the
   cycles that ran.** At every window, each leg's issued plus outstanding is the
   leg times the permissions assigned. At the end, nothing is outstanding and
   the recovery pool is zero, so each channel issued exactly 4,386 times its
   leg.
2. **The referral channel's identity holds.** At every window, its issued plus
   outstanding is the referral leg times the permissions assigned. Every
   referrer's accrual plus the unreferred pool's equals the same figure.
3. **Every month's pool reaches that month's best performers.** At every
   settlement, the winners are ranked independently of `close_month`. The
   ranking uses the figures the ledger held before the prologue deleted them,
   and the candidate set the schedule puts in scope. A candidate with no
   figure ranks at zero.
4. **No unit is issued twice or lost.** At every window:
   - supply is the sum of what the channels issued;
   - no channel is over its cap;
   - the model's own identities hold, including balances plus fee pool plus
     custody equal to supply, and both pool identities.

Every transaction is also checked for atomicity: a refused one must leave the
state root exactly where it found it.

## Required vectors and evidence

[`economy-scenario-suite-v4.txt`](../../test-vectors/economy-scenario-suite-v4.txt)
is normative, and `tools/scenario-suite-vectors/verify_v4.py` checks it.

**Every value but the state roots must agree with
`tools/scenario-suite-vectors/expected_v4.py` before it is compared with the
file.** That module imports nothing from `simulation/`. It takes its literals
from `expected_v2.py`, the window grid from `tools/cycle-boundary-vectors`, and
the civil calendar from `tools/calendar-vectors`. It restates the fixture from
this document and walks the settlement from the specifications:

- the winner and accrued sets, the recovery pool's absorption and residual;
- both caps, with a new referral balance marked at the window before its first
  accrual;
- the monthly pool by calendar month, ties split, remainders carried;
- the mints.

The state roots at windows 2, 100, 430, 731, 1,036, 1,037, and 1,067 are pinned
from the live run alone. They fail if the contract's state shape changes under
the run.

**The verifier must fail closed in seven ways**, each confirmed with the
unmutated run as control:

1. a tampered recorded value;
2. a recorded key nothing derives;
3. a derived key the file does not carry;
4. the version-three vector file;
5. the model with ADR 0094's zero referral mark restored;
6. a closed form that ignores the accumulation cap;
7. a disagreement between the live run and the walk, which `--emit` refuses to
   record.

**The sixth is the informative one.** Ignoring the cap reproduces every
channel total, because a capped seat's permission is reallocated rather than
lost. It is refused anyway, because the run loses 47 cycles to the cap and
`windows.over_cap_seat_windows` records it.

**The property tests are differential.** `scenario_v4_property_test.py` draws
32 populations. Each one varies:

- the number of people and seats, and the referral graph;
- the stagger and the uptime table;
- outages, and collection periods on both sides of the cap;
- lapses and genesis dates;
- block rates from a window a day to a window every 200 days.

Each population runs through the contract with every per-window check. Then
every figure the walk derives must agree. The draws are required to reach both
mint refusals, skipped months, a carried monthly remainder, the cap, forfeits,
and windows with no winner.

**Restart equivalence** is a replayed prefix reaching the root the whole run
held at the same window.

Every test is a ctest entry: `scenario-suite-v4-vectors`, `scenario-v4`, and
`scenario-v4-properties`.

## Open gaps this suite does not close

- **The uptime record is supplied.** Kinds 20 and 21 are not run at population
  scale. Challenge selection, response, expiry, and dispute are fixed by
  `economy-transition-v8-execution.txt` over targeted chains.
- **The population runs through the Python model of version nine, not the C++
  kernel.** The kernel's agreement with the model rests on the version-nine
  contract and execution vectors, and on ADR 0094's targeted check. Driving the
  kernel over this population is the natural next step: this file already pins
  roots it could be compared against.
- **Overflow** stays the limit the audit recorded: no version-nine vector
  exercises overflow in version nine's own additions.
- **The monthly remainders are all zero here**, because the referral leg
  divides by every winner count six seats can produce. The property tests'
  draws reach nonzero remainders and are required to.
  `economy-transition-v9-execution.txt` records only zero remainders.
- A long run that conserves value proves accounting. It proves nothing about
  activity fairness, snapshot honesty, or whether a supplied measurement
  reflects a real machine.

## The founder-decision gate

It held. Every value this suite chooses is a research fixture, and each is named
as one:

- the population, the referral graph, and the stagger;
- the uptime pattern and the outages;
- the collection schedule and the lapses;
- the genesis date and the block rate.

No supply, allocation, beneficiary, channel, threshold, cap, or rule of what a
participant must do to be paid is chosen here.
