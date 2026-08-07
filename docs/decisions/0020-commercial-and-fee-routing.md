# ADR 0020: Commercial revenue and transaction-fee routing

- Status: Accepted for M2 simulation; not a consensus activation
- Date: 2026-08-04

## Context

`m2-founder-economy-proof.md` requirements 9 and 10 ask for commercial-payment routing of 45%
to eligible Founders, 45% to the creator side, and 10% to the System Creator,
including the 22.5/22.5 project and product case and explicit integer remainder
behavior, plus separate transaction-fee routing of 100% to eligible Founders
without burn or deduction from commercial revenue.

The Founder Constitution fixes the shares, the two creator cases, the rule that
offline seats do not dilute active seats, and the rule that fees are charged
separately, are not burned, and are not deducted before the commercial split. It
explicitly defers the exact rounding, remainder, claim, activity-snapshot, and
bounded-distribution rules to a deterministic specification, and it separately
reserves the activity metric, grace allowance, performance ranking, winner
count, and tie rule as founder decisions.

Five questions had to be settled before implementation:

1. where the integer remainder of a floored split goes;
2. how the 22.5/22.5 case is computed so the two legs always reconcile with the
   45% creator share;
3. how a share is computed without overflowing `u64` for a large amount;
4. what happens to a Founder share when the active population is empty or
   smaller than the amount to divide; and
5. whether routing extends an accepted model or is a separate one.

## Decision

### The routing remainder goes to the active Founder Seat share

Every share is floored. The shortfall between the payment and the sum of the
floored credits is added to the Founder pool, so one payment credits Founders
`floor(45 * amount / 100) + remainder`.

The remainder depends only on `amount mod 200` and on whether a product creator
supplies the item, so an exhaustive scan of the 200 residues in both cases
proves the bound completely: at most 2 atomic units with a single creator and
at most 3 with two, that is 3 x 10^-8 display units.

Three reasons select the Founder pool over the alternatives:

- The System Creator Company keeps an exact floor of 10%. The party holding
  protocol-release authority can never gain from a rounding rule it would also
  implement.
- Creator legs keep an exact floor. A creator cannot raise revenue by choosing a
  price whose residue is favourable, so the price schedule stays a product
  decision rather than an arbitrage surface.
- The Founder pool is the only bucket carrying an exact residue into the next
  cycle, so the unit is neither created, burned, nor stranded, and it does not
  inflate any single recipient.

This is a rounding rule inside the founder-directed beneficiary set, not a
change to the 45/45/10 routing. It is bounded, stated, and proved rather than
left to an implementation's division order.

### The creator sub-split halves the already-floored creator share

Compute the 45% creator share once, then halve it for the two-creator case,
rather than computing 22.5% of the payment directly with a denominator of
1,000.

Halving guarantees `project + product <= creator_share` with a difference of at
most one atomic unit, which joins the routing remainder. Computing each leg from
the payment would let the two legs disagree with the creator share by
construction, so a reconciliation between the constitutional 45% and the
constitutional 22.5% pair would have to be repaired after the fact.

### Shares are computed from the amount's quotient and remainder

`floor(n * amount / 100)` is computed as
`n * (amount / 100) + (n * (amount mod 100)) / 100`.

The identity is exact because `n * q` is an integer, so the floor distributes
over the sum. It matters because the direct form overflows: for `n = 45` the
product `45 * amount` leaves `u64` above roughly 4.1 x 10^17 atomic units, about
7.4% of the maximum supply, so the naive form would reject a representable
payment as an overflow. The decomposed form cannot overflow for any `u64`
amount, and it is still executed with checked arithmetic so the property is
enforced rather than assumed.

### An empty or small active population carries value forward

A distribution divides `pool + carry` by the snapshot size `K`, credits every
snapshot seat the same `floor` amount, and carries the residue to the next
cycle. When `K` is zero, nothing is distributed and the whole amount carries
forward.

Nothing is burned and nothing is redirected. The constitutional rule that
offline seats do not dilute active seats is undefined against a zero
population, so delaying the distribution is the only reading that neither
destroys value nor invents a substitute beneficiary. A pool smaller than the
population is the same case with `per_seat = 0`, and it is a required test
vector rather than an edge case left to chance.

### A separate model, not an economy-simulator extension

Implement `simulation/revenue_routing/` with its own schema, state, digests,
and vectors. `founder-economy-manifest-v1`,
`founder-economy-simulator-v1`, and `founder-seat-schedule-v1` are unchanged.

Routing is not issuance: it moves value that a constitutional channel already
created, so it shares no cap, no permission, and no supply term with the economy
simulator. Adding it there would break a frozen schema to co-locate two
accounting systems that have no common invariant.

### Separate pools, carries, and per-seat balances for fees

Commercial revenue and fees keep independent pools, independent carries,
independent per-seat balance maps, and independent conservation equations that
share no term.

This makes "fees are not deducted from commercial revenue" a structural
property. A defect in one path cannot move value in the other, because there is
no expression in which both appear.

### The active-seat snapshot is a bound research placeholder

`close_cycle` consumes a supplied snapshot bound to the cycle it closes. It
names only which seat identifiers were eligible; it never supplies an amount, a
share, or a bound.

The activity metric, grace allowance, performance ranking, winner count, and
tie rule are founder-reserved. Inventing any of them to make a test pass would
convert a research fixture into policy, so the snapshot is deliberately the
weakest input that still allows the distribution rule to be proved.

## Alternatives not selected

- **Remainder to the System Creator Company:** the conventional "dust to the
  protocol treasury" rule. Rejected because the company already holds release
  and AI-policy authority and receives the whole seat sale proceeds; giving it
  the rounding surplus as well makes the one party that would implement the
  rounding rule its beneficiary.
- **Remainder to the creator side:** would make a product's price residue worth
  optimising, and it is ambiguous in the two-creator case without a further
  tie-break.
- **Largest-remainder apportionment:** minimises per-payment bias, but requires
  comparing fractional parts and a documented tie-break among three shares to
  stay deterministic. That is more machinery and more divergence surface than a
  three-atomic-unit bound justifies.
- **A separate dust accumulator with its own later beneficiary:** conserves
  exactly and favours nobody, but it invents a new economic bucket the
  constitution does not list, and it defers the very question this ADR exists to
  answer.
- **Rounding to nearest instead of floor:** the shares could then sum above the
  payment, so the model would have to create up to two atomic units of supply
  out of a rounding rule. That is disqualifying in a fixed-maximum economy.
- **Compute 22.5% directly with a denominator of 1,000:** lets the two creator
  legs and the 45% creator share disagree, so the constitution's two statements
  about the same value would need reconciliation logic.
- **Reject amounts above `u64_max / 45` as overflow:** simpler code, but it
  would refuse a payment of about 7.4% of maximum supply for an arithmetic
  reason with no economic meaning.
- **Distribute the Founder share per payment instead of per cycle:** would make
  every payment `O(active seats)` and would require an activity snapshot per
  payment. The constitution specifies eligibility "for the applicable accounting
  cycle", so per-cycle accrual is both cheaper and the stated shape.
- **Burn or redirect an undistributable pool:** contradicts the constitutional
  no-burn rule and would need a substitute beneficiary that no founder decision
  supplies.
- **Extend `founder-economy-simulator-v1` with routing transitions:** breaks a
  frozen schema and its accepted vectors to add transitions that share no
  invariant with issuance.
- **Model the eligibility rule now:** would require selecting the activity
  metric, grace allowance, and performance ranking, all explicitly reserved to
  the owner.

## Consequences

- The 45/45/10 split, the 22.5/22.5 case, and 100% fee routing become executed
  derivations with an exhaustively proved remainder bound rather than reviewed
  prose.
- Conservation is checkable after every event: routed value is always either
  credited to a named beneficiary or waiting in a pool or carry, on both paths
  independently.
- No native units are created, so the 55,743,940,100-unit maximum, every
  channel cap, and the accepted economy and seat vectors are untouched.
- The rounding rule can never favour the System Creator Company or a creator,
  and is bounded at three atomic units per payment.
- An eligible population that is empty or smaller than the pool delays value
  rather than losing it, at the cost of a carry that a later consensus design
  must still bound in storage.
- A seat identifier here is not yet proved to be a purchased or activated seat.
  The three models remain unjoined, and this slice does not narrow that gap.
- The activity snapshot remains a fixture. Nothing here shows that any machine
  was online, that eligibility is gameable or fair, or that the transaction-fee
  amount rule is sound.

## Compatibility and independent review

This ADR accepts a research model contract. It activates no consensus
transition, creates no native units, and its error codes are simulator result
codes rather than consensus receipts.

M3 must separately define the accounting-cycle boundary in heights or epochs,
the activity proof, the claim or push mechanism that moves a credited balance to
a spendable account, the storage bound on per-seat balances at 100,000 seats,
and the consensus receipts and numeric codes. Exact routing arithmetic is not
economic safety, and independent economic and protocol review remains required
before any production revenue flow.
