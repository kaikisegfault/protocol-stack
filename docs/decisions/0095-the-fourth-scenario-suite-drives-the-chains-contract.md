# ADR 0095: The fourth scenario suite drives the chain's contract a window at a time

- Status: Accepted
- Date: 2026-09-27
- Closes: requirement 14's multi-year leg, which
  [`founder-economy-devnet-audit-v1.md`](../project/founder-economy-devnet-audit-v1.md)
  found unmet
- Specification: [`economy-scenario-suite-v4`](../specifications/economy-scenario-suite-v4.md)

## Context

The M2 standard for multi-year evidence is a population run over every seat's
731 cycles, checked against an independent closed form, with market and
property tests beside it. `economy-scenario-suite-v3` meets that standard, but
against `founder-economy-simulator-v3`. That simulator still keeps the
per-channel carry the recovery pool replaced. It also has neither measured
activity nor the monthly pool. The chain executes `economy-transition-v9`, and
no run had taken that contract over a whole distribution.

There were three ways to get there.

1. **Rebind a fourth simulator.** Write `founder-economy-simulator-v4` with the
   recovery pool, measured activity, and the monthly pool, and run the suite
   against it. This is how every earlier version was made. But it adds a fourth
   independent statement of rules the chain already executes, and the
   simulator would have to be kept equal to the contract by vectors, not by
   construction. The claim the audit needs is about the contract.
2. **Drive the chain.** Execute every height with `execute_block`. That is
   21 million blocks for one seat's life, because every height issues and
   expires challenges. Version nine's `advance_to` refuses to skip heights once
   a seat is active, for exactly that reason.
3. **Drive the contract's settlement a window at a time.** Every quantity the
   audit's four claims are about changes only at a window's opening, in the
   prologue. Transactions change them only when executed. Run the prologue at
   each window opening, execute each participant's signed transactions at
   their own heights, and supply what the skipped heights would have written:
   the kind-19 records of lost or voided slots.

## Decision

**Option 3.** The model gains one public function, `block.open_window`, which
calls `_prologue` with the accepted orders at a window-opening height the caller
has set. The composition is exposed, not copied. It is an evidence harness, and
`execute_block` remains the only path a chain runs.

**The kind-19 records are the only supplied input**, because they are the only
state the skipped heights write that the settlement reads. The challenge and
dispute machinery that writes them in a real chain is fixed by version eight's
execution vectors over targeted chains. Supplying the records keeps the
measurement a fixture, as it was in every earlier suite. The difference is that
it now enters through the contract's own carrier, not an event schema.

**Only scenario 1 is rebound.** The market scenarios import nothing from any
economy package, so version three's vectors are still their evidence. The escrow
drain binds `escrow-payout-v3`, which the chain does not execute.

**The closed form is a walk written from the specifications, and it is
parameterized.** `expected_v4.py` imports nothing from `simulation/`. Its
parameter object restates the fixture table field for field. That turns the
property tests into differential tests: 32 seeded populations run through the
contract, and every figure the walk derives must agree with each one. The draws
vary:

- the population and its referral graph;
- the uptime table and outages;
- collection periods on both sides of the cap, and lapses;
- genesis dates and block rates.

A defect in either model alone fails on some seed.

**The fixture is the commit target's calendar.** At three seconds a block, a
window is one day and a month holds 28 to 31 windows. So the monthly payout runs
on real calendar months, including a leap February. The version-nine execution
trace ran at ninety seconds a block to reach a month in three windows. This
suite can afford the real rate, because a window costs one prologue, not
28,800 blocks.

## Evidence

- The recorded run takes six seats through 1,068 windows, 4,386 seat-cycles,
  and 668 signed transactions in about two seconds. It checks the four claims
  at every window. All 263 recorded vectors agree with the walk except the
  seven state roots, which are pinned from the live run.
- It reaches:
  - 14 windows with no winner, and 200 with several;
  - 387 reallocated permissions;
  - a recovery pool that peaks at 344,580,000,000 and drains to zero at the
    drain window;
  - 47 cycles lost to the seat cap, and 100 referral legs forfeited to the
    unreferred pool;
  - 35 monthly settlements, one of them the six-way tie that February 2028
    forces;
  - a seat that collects all its monthly claims at the end.
- The verifier refuses seven mutations, each against the unmutated run as
  control. The one that matters most is ADR 0094's zero referral mark, restored
  in the model: the walk refuses it on the referral balances and the forfeited
  legs.
- Across the 32 property draws: 3,976 settled months, 2,065 settlements that
  skipped at least one empty month in a single pass, 85 carried remainders, 564 cycles lost to the cap, and 1,643
  forfeited referral legs. All of them agree with the walk.

**Designing this suite is what found ADR 0094's defect.** The walk needed a
closed form for what each referrer accrues, so the version-three rule was read
against the code that executes it.

## Consequences

**Requirement 14's multi-year leg is met against the contract the chain
executes**, with three limits:

- the uptime record is supplied;
- the population runs through the Python model, not the C++ kernel;
- the overflow limit the audit recorded still stands.

**Driving the C++ kernel over the same population is the natural next
evidence.** The vector file already pins the roots it would have to reach. It
is not required for M3's exit: requirement 11's cross-language agreement is met
by the version-nine contract and execution vectors.

**`open_window` is a second caller of the prologue**, so a change to the
prologue's contract now has two callers to keep correct. That is the price of
exposing rather than copying, and it is the right one: a copy would drift
silently, while a changed signature fails loudly here.
