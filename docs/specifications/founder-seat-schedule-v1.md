# Founder Seat schedule v1

Status: Accepted M2 research model contract; not a consensus transition

This document fixes the integer USD denomination, the 100,000-seat capacity,
the block price schedule, the per-principal ownership bound, and the seat sale
transition required by requirement 8 of
[`first-goal.md`](../project/first-goal.md).

The change is classified as economics, input encoding, and state-transition
shape. ADR 0019 records the alternatives and decision. It changes no M1 bytes,
C++ state, configured devnet supply, or accepted simulator schema, and it does
not modify `founder-economy-simulator-v1`.

## Scope

Version one defines the sale side of a Founder Seat: how many seats exist, what
each costs, who may own how many, and what one purchase writes.

It does not define seat activation, issuance cycles, biometric enrollment,
manager records, legacy succession, node operation, or any native-asset
transfer. Seat purchase proceeds are external USD-denominated value that goes
to the System Creator Company; they are not native units and never enter a
native issuance channel.

It also does not define the external payment itself. The stablecoin allowlist,
USD valuation proof, quote lifetime, external finality, reorganization,
refund, and custody rules are bridge-milestone work and are deliberately not
invented here.

### Relationship to the economy simulator

This is a separate model with its own schema, state, and digests.
`founder-economy-simulator-v1` remains byte-for-byte unchanged, including its
event kinds, `activate_seat` semantics, and frozen vectors.

The two are intentionally not yet joined. A purchased seat here is not
automatically an activated seat there, because the activation height rule, the
purchase-to-activation transition, and the referral recording point are not
settled. Joining them requires a version-two economy schema and is recorded as
later work, not implied by this document.

## Determinism rules

The model is a pure function of its event input. It must not read a wall
clock, environment variable, locale, random source, network, or any mutable
external value, and must not use floating-point arithmetic anywhere.

All monetary arithmetic is unsigned `u64` with checked addition, subtraction,
and multiplication. Any checked operation that would leave the range fails; it
never wraps or saturates.

## Integer USD denomination

Seat prices are USD-denominated, so they use a separate integer unit from the
native asset. They are never native atomic units and must not be added to
native supply.

| Property | Exact value |
| --- | ---: |
| USD cents per USD | 100 |
| First block price | 10,000 cents (USD 100) |
| Low-tier step | 1,000 cents (USD 10) |
| Tier boundary price | 100,000 cents (USD 1,000) |
| High-tier step | 10,000 cents (USD 100) |
| Final block price | 9,190,000 cents (USD 91,900) |
| Full-sale proceeds | 423,185,500,000 cents (USD 4,231,855,000) |

Every founder-stated amount is a whole number of USD, so cents represent the
complete schedule exactly with no rounding anywhere. The unit exists so a later
bridge quote can express sub-dollar precision without a new schema; it does not
imply that any current price has a fractional part.

Full-sale proceeds are far below `u64` maximum, so the complete sale cannot
overflow.

## Fixed schedule contract

| Property | Exact value |
| --- | ---: |
| Founder seat capacity | 100,000 |
| Seats per block | 100 |
| Block count | 1,000 |
| Maximum seats per person | 1,000 |

Seat identifiers are unsigned integers from `0` through `99,999`. Block indexes
are unsigned integers from `0` through `999`. A seat belongs to exactly one
block:

```text
block_index(seat_id) = seat_id / 100        (integer division)
```

Seats are sold strictly in ascending identifier order, so the next seat sold is
always `seats_sold`. There is no reservation, auction, gap, or out-of-order
allocation in this version.

### Block price

Let `L = (tier_boundary - first_block) / low_step = 90` be the last block index
priced by the low-tier rule. For a block index `b` in `0..999`:

```text
price(b) = first_block  + b * low_step          when b <= 90
price(b) = tier_boundary + (b - 90) * high_step  when b >  90
```

Block 90 is therefore priced at exactly the 100,000-cent tier boundary, and the
high-tier step first applies to block 91. This reading is confirmed by the two
founder-stated endpoints: it derives the USD 91,900 final block and the USD
4,231,855,000 full-sale total exactly, and it is the only reading that derives
both.

Every block price is distinct and strictly increasing. An implementation must
compute the price with checked integer arithmetic from these parameters rather
than storing a 1,000-entry table.

### Derived totals

Checked arithmetic must reproduce:

```text
price(0)   =    10,000 cents          price(1)   =    11,000 cents
price(89)  =    99,000 cents          price(90)  =   100,000 cents
price(91)  =   110,000 cents          price(999) = 9,190,000 cents

cumulative(90)  =     500,500,000 cents
cumulative(91)  =     511,500,000 cents
cumulative(999) = 423,185,500,000 cents
```

`cumulative(b)` is the total proceeds after every seat in blocks `0..b` is
sold, that is `100 * sum(price(0..b))`. The closed form must agree with
sequential accumulation:

```text
low_sum  = 91  * (first_block + tier_boundary) / 2
high_sum = 909 * ((tier_boundary + high_step) + price(999)) / 2
total    = 100 * (low_sum + high_sum) = 423,185,500,000 cents
```

## State

```text
seats_sold = u64
seats[seat_id] = {
  principal_id,
  price_usd_cents:u64,
  referrer_seat_id: seat_id | none
}
principal_seat_counts[principal_id] = u64
accepted_purchase_ids = set<purchase identifier>
proceeds_usd_cents = u64
```

Every value begins at zero or empty. There is no pre-sale, founder grant, or
reserved allocation.

### Invariants

At every accepted state:

```text
seats_sold <= 100,000
count(seats) = seats_sold
every seat_id in seats is in 0 .. seats_sold - 1
checked_sum(principal_seat_counts) = seats_sold
every principal count is in 1 .. 1,000
seats[s].price_usd_cents = price(block_index(s))
checked_sum(seats[*].price_usd_cents) = proceeds_usd_cents
proceeds_usd_cents <= 423,185,500,000
every recorded referrer is a seat sold strictly before its referred seat
no seat is its own referrer
```

The referrer ordering invariant is what makes the referral graph acyclic: a
seat can only name a seat that already existed when it was sold.

## Canonical bytes and digests

Digest preimages use RFC 8785 canonical bytes under the accepted `D(L)` domain
separation from `protocol-primitives-v1.md`, exactly as in
`founder-economy-simulator-v1`. Every monetary value in a preimage is a
canonical unsigned decimal string; only small exact counts appear as JSON
numbers, bounded at parse time by 9,007,199,254,740,991.

| Label | Preimage |
| --- | --- |
| `protocol-stack:founder-seat-schedule:events-v1` | the parsed event array |
| `protocol-stack:founder-seat-schedule:state-v1` | the canonical state value |
| `protocol-stack:founder-seat-schedule:trace-v1` | the ordered trace records |
| `protocol-stack:founder-seat-schedule:result-v1` | the complete result object |

### Canonical state value

```text
{
  "seats_sold": n,
  "proceeds_usd_cents": s,
  "seats": {
    "{seat:05d}": {
      "principal_id": t,
      "price_usd_cents": s,
      "referrer_seat_id": "{referrer:05d}" | null
    }
  },
  "principal_seat_counts": { "{principal_id}": s },
  "accepted_purchase_ids": [ t ]
}
```

`s` is a canonical unsigned decimal string, `n` a JSON integer, and `t` a
string. Seat keys are zero-padded to five digits so the map sorts identically
under numeric and lexicographic ordering. `accepted_purchase_ids` is sorted
ascending.

## Canonical event input

The events input is a JSON array. Each element is an object with exactly `id`,
`kind`, and the fields required by its kind. `id` matches
`^[a-z0-9][a-z0-9_-]{0,63}$` and must be unique across the array; a duplicate
`id` is an input-shape error that aborts the run.

| Kind | Additional fields |
| --- | --- |
| `purchase_seat` | `purchase_id`, `principal_id`, `referrer_seat_id`, `payment_result` |

`purchase_id` and `principal_id` match the identifier pattern.
`referrer_seat_id` is `null` or a seat identifier. `payment_result` is always
present; `null` models an absent research input.

### Research input

```text
payment_result = {
  purchase_id, principal_id, seat_id, price_usd_cents, settled:bool
}
```

The result is bound to the exact purchase it authorizes, including the seat
identifier the sale will allocate and the price that seat's block commands. A
result that names a different purchase, principal, seat, or price cannot
authorize the attempt.

This placeholder stands in for the unresolved external payment workflow. It is
a deterministic fixture, not proof that any external value moved, and it cannot
become a production consensus input by renaming.

## Purchase transition

A purchase allocates the next seat identifier, records its owner, price, and
optional referrer, and increases proceeds.

1. A previously accepted `purchase_id` is `REPLAY`.
2. `seats_sold` already at 100,000 is `CAPACITY_EXHAUSTED`.
3. A `referrer_seat_id` outside `0..99,999`, or not already sold, is
   `INVALID_REFERRER`. A seat cannot refer to itself because its own
   identifier is not yet sold when it is purchased.
4. A principal already holding 1,000 seats is `PRINCIPAL_SEAT_LIMIT`.
5. A `null` `payment_result` is `MISSING_RESEARCH_INPUT`.
6. A `payment_result` whose purchase, principal, seat identifier, or price
   differs from the attempted purchase is `INVALID_RESEARCH_INPUT`. The seat
   identifier it must name is `seats_sold`, and the price it must name is
   `price(block_index(seats_sold))`.
7. A `settled` value of false is `PAYMENT_NOT_SETTLED` and consumes no
   purchase identifier.
8. A checked increment of `seats_sold`, the principal count, or
   `proceeds_usd_cents` that leaves `u64` is `ARITHMETIC_OVERFLOW`.

On success, in one atomic write: the seat record is created, `seats_sold`
increases by one, the principal's count increases by one, proceeds increase by
that seat's block price, and the purchase identifier is recorded. Any failure
performs none of these writes and consumes no purchase identifier.

Ordering the capacity and limit checks before the payment binding keeps a
supplied fixture from deciding whether a bound was reached.

## Journals and atomicity

An accepted purchase emits an ordered journal of
`{bucket, direction, amount_usd_cents}` entries with buckets
`remaining_seats`, `seats_sold`, `principal:{principal_id}`, and `proceeds`.
Counts appear in the same unsigned-decimal form as amounts so the journal never
carries a signed or zero value.

The engine requires:

```text
exactly four buckets are present
remaining_seats decreases by 1 and seats_sold increases by 1
exactly one principal bucket increases by 1, and it is the buying principal
proceeds increases by exactly price(block_index(allocated seat))
the allocated seat identifier equals the pre-state seats_sold
```

### Failure atomicity by construction

A handler is a pure function of the state and the event. It returns either a
rejection or a complete write set, and never holds a reference it can partially
write. The engine commits a write set only after the journal checks pass.
Atomicity is therefore a property of the transition's shape, not of a
compensating copy that must be remembered to be taken.

This is the deliberate difference from `founder-economy-simulator-v1`, which
obtains atomicity by cloning state before each event and comparing full state
digests around it. That is sound for its bounded scenarios, whose state stays
small, but here the founder-directed scenario is 100,000 purchases against a
monotonically growing state. Cloning and digesting per event would make the
complete sale quadratic and effectively unrunnable, which would leave the one
scenario this model exists to prove untested.

As defence in depth the engine also compares a constant-time state summary —
seats sold, proceeds, and the three collection sizes — around every rejection,
and the tests compare full state digests around rejections on bounded
scenarios.

Full state invariants are `O(seats sold)`, so a run asserts them before the
first event, after the last, and on a fixed stride of accepted purchases.
Every purchase is still individually checked against the journal rules above.

## Result and trace

One run produces `schema`, `events_digest`, `records`, `trace_digest`,
`final_state`, `state_digest`, `metrics`, and a `result_digest` over the result
without that field. The schema string is
`protocol-stack/founder-seat-schedule-result/v1`.

Each trace record contains the event index, event identifier, kind, acceptance
flag, result code, and the journal. A rejected record has an empty journal.
Records carry no per-event state digest: `trace_digest` already covers every
ordered record, and `state_digest` anchors the outcome, so a per-event
full-state digest would add cost proportional to the square of the run length
without adding evidence.

`metrics` reports the capacity and per-person bounds, seats sold, seats
remaining, proceeds, the full-sale total, the current and next block index and
price, the distinct principal count, and the largest single principal holding.
The next block fields are `null` once the sale is complete. Metrics are derived
views; no invariant depends on them.

## Resource limits

A purchase reads and writes only the seat, principal, and scalar entries it
names, so one purchase is constant time. No transition iterates over all seats,
all blocks, or all principals. The price of any block is computed in constant
time from the four schedule parameters rather than read from a table.

The complete sale is 100,000 purchases. It is a bounded scenario an
implementation must be able to run end to end, and it must derive exactly
423,185,500,000 cents.

## Versioning and compatibility

The schema strings, event kinds, field sets, research-input shape, state
shape, journal buckets, digest labels, error codes, and every schedule
parameter are immutable for version one. A changed price, capacity, bound, or
semantic rule requires a new schema and ADR.

Running this model has no effect on an M1 account, height, transaction root,
receipt, state root, SQLite database, ABCI response, CometBFT validator, or on
`founder-economy-simulator-v1` state, vectors, or digests.

Error codes here are simulator result codes. M3 must separately define
consensus receipts, numeric codes, and commitments before a C++ transition
exists.

## Required vectors and evidence

[`founder-seat-schedule-v1.txt`](../../test-vectors/founder-seat-schedule-v1.txt)
is normative. It fixes the denomination, every schedule parameter, the block
prices and cumulative proceeds at the first block, the tier boundary, the first
post-boundary block, and the final block, the full-sale total, the capacity and
ownership bounds, a research scenario trace and its digests, and every
rejection code.

The executed verifier must independently derive, not restate, every recorded
value, and must fail when a recorded key is never derived.

Test coverage must include the complete 100,000-seat sale, the per-principal
bound at exactly 1,000 seats, capacity exhaustion at exactly 100,000, both
tier-boundary blocks, replay, unbound and unsettled payment fixtures, referrer
ordering, overflow, and atomicity, plus byte-identical digests across repeated
runs.

Passing these checks establishes exact schedule arithmetic and ownership
accounting. It does not establish that any external payment, USD valuation,
custody, or refund behavior is safe, and it does not make a seat operable.
Those remain bridge and identity milestone work requiring independent review.
