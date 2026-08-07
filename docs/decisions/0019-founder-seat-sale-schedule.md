# ADR 0019: Founder Seat sale denomination, schedule, and model boundary

- Status: Accepted for M2 simulation; not a consensus activation
- Date: 2026-08-03

## Context

`m2-founder-economy-proof.md` requirement 8 asks for exact 100,000-seat and
1,000-seats-per-person limits plus price-schedule test vectors, including the
USD 100 first block, the USD 1,000 boundary, the USD 91,900 final block, and
the USD 4,231,855,000 derived full-sale proceeds.

The Founder Constitution states the schedule in prose: seats 1 through 100 cost
USD 100; the price rises by USD 10 per next 100-seat block until a block price
of USD 1,000 is reached; after that block it rises by USD 100 per block. It
also fixes the 100,000-seat capacity and the 1,000-seat per-human bound, and
routes the complete external proceeds to the System Creator Company.

Three questions had to be settled before implementation:

1. how USD amounts are represented as integers, given that the native
   eight-decimal denomination is for the native asset only;
2. exactly where the tier boundary falls, since "until a block price of USD
   1,000 is reached" could be read as including or excluding that block; and
3. whether seat sale extends `founder-economy-simulator-v1` or is a separate
   model.

## Decision

### USD cents as the integer sale unit

Represent every seat price and proceeds total as an unsigned integer count of
USD cents, with `100` cents per USD stated explicitly, mirroring the
`atomic_units_per_display_unit` shape already accepted for the native asset.

Sale amounts are a distinct unit from native atomic units. They are never added
to native supply, never enter an issuance channel, and never appear in a native
custody bucket. Full-sale proceeds are 423,185,500,000 cents, far below `u64`
maximum, so the complete sale cannot overflow.

### The tier boundary is block 90 zero-based

Block index 90 is priced at exactly the 100,000-cent boundary, and the
high-tier step first applies to block 91:

```text
price(b) = 10,000  + b * 1,000        when b <= 90
price(b) = 100,000 + (b - 90) * 10,000 when b >  90
```

This is not a preference. It is the reading that derives both founder-stated
endpoints exactly: the final block at 9,190,000 cents and the full-sale total
at 423,185,500,000 cents. A schedule that switched one block earlier or later
would contradict at least one of them, so the constitution's two derived
figures uniquely determine the rule.

The price is computed in constant time from four parameters rather than stored
as a 1,000-entry table, so the schedule cannot drift row by row.

### A separate model, not an economy-simulator extension

Implement `simulation/founder_seats/` with its own schema, state, digests, and
vectors. `founder-economy-simulator-v1` is unchanged.

The natural integration — a `purchase_seat` transition that creates a seat and
an `activate_seat` that requires a prior purchase — is a semantic change to an
event kind that ADR 0018 froze one slice earlier. Taking it now would force a
version-two economy schema and invalidate the vectors and digests just
accepted, in exchange for an integration whose activation height rule and
purchase-to-activation transition are still unsettled.

Requirement 8 is about capacity, ownership, and price arithmetic, none of which
depends on issuance. Joining the two models is recorded as later work with its
own schema version.

### Pure handlers instead of clone-and-compare atomicity

Obtain failure atomicity from the shape of the transition: a handler is a pure
function returning either a rejection or a complete write set, and the engine
commits that write set only after the journal checks pass. A rejected purchase
cannot write because no handler ever holds a reference it can partially write.

`founder-economy-simulator-v1` instead clones state before each event and
compares full state digests around it. That was measured here and is quadratic:
500, 1,000, and 2,000 purchases took 0.96, 3.82, and 16.45 seconds, which
extrapolates to roughly eleven hours for the complete sale. The founder-directed
100,000-seat scenario is the single most important thing this model must prove,
so a design that cannot run it is not acceptable. With pure handlers the
complete sale runs in about ten seconds.

Per-event state digests are dropped from trace records for the same reason.
`trace_digest` already covers every ordered record and `state_digest` anchors
the final outcome, so a per-event full-state digest costs time proportional to
the square of the run length without adding evidence.

### Sequential allocation and a bound payment placeholder

Seats are allocated strictly in ascending identifier order, so the next seat is
always `seats_sold`. There is no reservation, auction, or gap.

The external payment is a research placeholder bound to the exact purchase
identifier, principal, allocated seat identifier, and block price. Capacity and
ownership checks run before the payment binding, so a supplied fixture can
never decide whether a founder-directed bound was reached.

## Alternatives not selected

- **Whole USD integers:** every current amount is a whole dollar, so this would
  work today and read closer to the constitution. It was rejected because a
  bridge quote in a volatile asset will need sub-dollar precision, and changing
  the unit later is a schema break for a saved cost of one factor of 100.
- **Reuse the native eight-decimal atomic unit for USD:** would invite adding a
  USD amount to a native balance and would imply an exchange rate the protocol
  does not have. Sale value and native value must not share a unit.
- **Store the 1,000 block prices as a table:** a table is auditable but lets one
  wrong row survive review, and it cannot be checked against the rule it came
  from. A constant-time formula plus derived vectors is falsifiable.
- **Extend `founder-economy-simulator-v1` with a purchase transition:** breaks
  a schema frozen one slice earlier and invalidates its vectors and digests,
  before the activation rule that would justify the break is settled.
- **Let the payment fixture supply the seat identifier or price:** a research
  stand-in could then choose which seat it bought or what it paid. Deriving
  both from state and requiring the fixture to match is what keeps the schedule
  founder-directed rather than fixture-directed.
- **Allow out-of-order or reserved seat allocation:** would make the price a
  function of a choice rather than of position, and would require a reservation
  expiry policy the constitution does not define.
- **Model per-human identity now:** the constitution bounds seats per *human*,
  but proving humanness is biometric M4 work. This model bounds seats per
  supplied principal identifier and records that the identity binding is not
  yet proved.
- **Keep clone-and-compare atomicity for consistency with the economy
  simulator:** consistency is worth less than being able to run the scenario
  the model exists to prove. The two models are separate schemas, and the
  difference is recorded in both documents rather than left as an unexplained
  divergence.
- **Reduce the complete sale to a sampled scenario:** would have made the
  quadratic design survivable while quietly never deriving the founder-stated
  full-sale total end to end. The total is the requirement, not an illustration.

## Consequences

- Every founder-stated price vector, the capacity, and the full-sale total
  become executed derivations rather than reviewed prose.
- The per-principal bound is enforced at exactly 1,000 and capacity at exactly
  100,000, both testable at their boundaries.
- Sale proceeds are visibly outside native supply, so no seat sale can affect
  the 55,743,940,100-unit maximum.
- `founder-economy-simulator-v1` keeps its accepted vectors and digests
  unchanged, and the integration that would change them is deferred with a
  stated reason rather than taken opportunistically.
- The per-principal bound is not yet a per-human bound. A principal identifier
  is supplied, so this model constrains concentration only as strongly as
  identity is proved, which in M2 is not at all. This is recorded rather than
  overclaimed.
- The external payment remains a bound fixture. Nothing here shows that USD
  valuation, custody, finality, refund, or stablecoin governance is safe.

## Compatibility and independent review

This ADR accepts a research model contract. It activates no consensus
transition, creates no native units, and its error codes are simulator result
codes rather than consensus receipts.

M3 and the bridge milestone must separately define the external payment proof
interface, USD valuation and quote lifetime, external finality and
reorganization handling, refunds, the purchase-to-activation transition, and
the per-human identity binding. Exact schedule arithmetic is not economic or
custodial safety, and independent economic, bridge, and protocol review remains
required before any production sale.
