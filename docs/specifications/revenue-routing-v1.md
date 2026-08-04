# Revenue routing v1

Status: Accepted M2 research model contract; not a consensus transition

This document fixes the deterministic integer routing of native-asset
commercial payments and protocol transaction fees required by requirements 9
and 10 of [`first-goal.md`](../project/first-goal.md).

The change is classified as economics, input encoding, and state-transition
shape. ADR 0020 records the alternatives and decision. It changes no M1 bytes,
C++ state, configured devnet supply, or accepted simulator schema, and it
modifies neither `founder-economy-simulator-v1` nor `founder-seat-schedule-v1`.

## Scope

Version one defines what happens to native value that already exists: how one
commercial payment divides among Founder Seats, creators, and the System
Creator Company, how a transaction fee reaches Founder Seats, and how an
accounting cycle distributes the accumulated Founder share.

It creates no native units. No issuance channel, no channel cap, and no part of
the 55,743,940,100-unit maximum is touched, because routing moves value that a
constitutional channel already issued.

It does not define the payer, the payment's authorization, the price of any
approved product, the transaction-fee amount rule, project or product
admission, the activity metric that decides eligibility, or the cycle length in
heights. Those are consensus, application-admission, and founder-reserved work.

### Relationship to the other accepted models

This is a separate model with its own schema, state, and digests.
`founder-economy-manifest-v1`, `founder-economy-simulator-v1`, and
`founder-seat-schedule-v1` remain byte-for-byte unchanged, including their
event kinds, vectors, and digests.

The three models are still not joined. A seat identifier here is a supplied
member of an active-seat snapshot; it is not proved to be a seat purchased in
`founder-seat-schedule-v1` or activated in `founder-economy-simulator-v1`,
because the purchase-to-activation transition remains unsettled. Joining them
requires a later schema version and is recorded as remaining work.

## Determinism rules

The model is a pure function of its event input. It must not read a wall clock,
environment variable, locale, random source, network, or any mutable external
value, and must not use floating-point arithmetic anywhere.

All monetary arithmetic is unsigned `u64` with checked addition, subtraction,
and multiplication. Any checked operation that would leave the range fails; it
never wraps or saturates. Division is integer division that truncates toward
zero on non-negative operands, so it is exactly floor division.

## Denomination

Routing uses the native asset, so it uses the denomination already accepted in
`founder-economy-manifest-v1`.

| Property | Exact value |
| --- | ---: |
| Storage type | `u64` |
| Decimal places | 8 |
| Atomic units per display unit | 100,000,000 |
| Maximum supply in atomic units | 5,574,394,010,000,000,000 |

Seat sale proceeds are USD cents under `founder-seat-schedule-v1` and are a
different unit. They never appear here.

## Fixed split contract

| Property | Exact value |
| --- | ---: |
| Share denominator | 100 |
| Active Founder Seat numerator | 45 |
| Creator side numerator | 45 |
| System Creator Company numerator | 10 |
| Creator split parts | 2 |
| Founder seat capacity | 100,000 |

The three numerators sum to the denominator exactly, so the split is complete
before any rounding rule is applied.

### Overflow-free share arithmetic

A share must be `floor(numerator * amount / denominator)` for any `u64` amount.
Computing `numerator * amount` first would overflow for a large legitimate
amount, so the share is computed from the quotient and remainder of the amount:

```text
q, m   = amount / 100, amount mod 100
share  = numerator * q + (numerator * m) / 100
```

This is exact, not an approximation:

```text
numerator * amount / 100 = numerator * (100q + m) / 100
                         = numerator * q + numerator * m / 100
```

`numerator * q` is an integer, so the floor distributes over the sum. Because
`numerator <= 45` and `q <= u64_max / 100`, the product `numerator * q` cannot
leave `u64`, and `numerator * m <= 4,455` is trivially bounded. Every step is
still performed with checked arithmetic so the property is enforced rather than
assumed.

### Creator sub-split

The creator share is computed once, then divided:

```text
project_amount = creator_share                when no product creator supplies
project_amount = creator_share / 2            when a product creator supplies
product_amount = 0 | creator_share / 2
```

Halving the already-floored 45% share is what makes the two creators receive
22.5% each. Computing 22.5% directly would require a denominator of 1,000 and
would let the two creator legs disagree with the creator share by construction.

### Integer remainder

Every share is floored, so the four credits can be less than the payment. The
shortfall is the routing remainder:

```text
remainder = amount - (founder_share + project_amount + product_amount
                      + system_creator_share)
```

**The remainder is added to the active Founder Seat share.** The Founder credit
of one payment is therefore `founder_share + remainder`.

The remainder depends only on `amount mod 200` and on whether a product creator
supplies the item, so an exhaustive scan of the 200 residues in both creator
cases is a complete proof of its bound:

| Case | Maximum remainder | Smallest amount reaching it |
| --- | ---: | ---: |
| No product creator | 2 atomic units | 2 |
| Product creator | 3 atomic units | 4 |

Three atomic units is 3 x 10^-8 display units, so the rule cannot move a
meaningful amount of value. It is specified exactly anyway, because an
unspecified remainder is a consensus divergence rather than a rounding
nuisance.

Sending the remainder to the Founder pool has three consequences worth stating.
The System Creator Company's 10% is always an exact floor, so the party that
holds protocol-release authority can never gain from the rounding rule. The
creator legs are always an exact floor, so a creator cannot raise revenue by
choosing a price with a favourable residue. And the remainder joins the one
bucket that carries an exact residue to the next cycle, so no atomic unit is
created, burned, or stranded.

## Transaction fees

A protocol transaction fee is a separate event with its own amount. Its whole
amount routes to the active Founder Seat fee pool.

Fees are never burned, never split, never reduced, and never subtracted from a
commercial payment before or after the 45/45/10 rule. The two paths use
separate pools, separate carries, separate per-seat balances, and separate
conservation equations, so neither can silently draw on the other.

## Accounting cycles and distribution

Value accrues into the open cycle's pools and is distributed when that cycle is
closed against a supplied active-seat snapshot.

For each of the two independent pools, with `K` the number of seats in the
snapshot:

```text
pool_in   = pool + carry
per_seat  = pool_in / K          and   carry' = pool_in mod K      when K > 0
per_seat  = 0                    and   carry' = pool_in           when K = 0
pool'     = 0
```

Every seat in the snapshot receives exactly `per_seat`. The undistributed
residue becomes the next cycle's carry, so `carry' < K` whenever `K > 0`.

A cycle with no eligible seat distributes nothing and carries the whole pool
forward. Nothing is burned and nothing is redirected: an absent active
population delays a distribution rather than destroying it. This is also the
only shape consistent with the constitutional rule that offline seats do not
dilute active seats, since diluting against a zero population is undefined.

The cycle index is a `u64` counter starting at zero. `close_cycle` must name
the currently open cycle, which makes replaying or skipping a close a
deterministic rejection rather than a silent reordering.

## State

```text
current_cycle              = u64
commercial_pool            = u64
fee_pool                   = u64
commercial_carry           = u64
fee_carry                  = u64
commercial_routed_total    = u64
fee_routed_total           = u64
system_creator_balance     = u64
creator_balances[creator_id]           = u64
founder_commercial_balances[seat_id]   = u64
founder_fee_balances[seat_id]          = u64
accepted_payment_ids       = set<payment identifier>
accepted_fee_ids           = set<fee identifier>
```

Every value begins at zero or empty. There is no opening balance, float, or
reserve. A balance map never stores a zero entry, so the canonical state has one
representation per logical state.

### Invariants

At every accepted state:

```text
commercial_routed_total = system_creator_balance
                        + checked_sum(creator_balances)
                        + checked_sum(founder_commercial_balances)
                        + commercial_pool + commercial_carry

fee_routed_total = checked_sum(founder_fee_balances) + fee_pool + fee_carry

every stored balance is in 1 .. u64_max
every seat identifier is in 0 .. 99,999
every scalar is in 0 .. u64_max
```

The two conservation equations are the substance of this model. The first says
every atomic unit of commercial revenue is either credited to a named
beneficiary or still waiting in the Founder pool or carry. The second says the
same for fees and shares no term with the first, which is what makes "not
deducted from commercial revenue" a structural property rather than a promise.

Neither equation permits creation: routed totals only increase by the exact
amount an accepted event supplied.

## Canonical bytes and digests

Digest preimages use RFC 8785 canonical bytes under the accepted `D(L)` domain
separation from `protocol-primitives-v1.md`, exactly as in
`founder-seat-schedule-v1`. Every monetary value in a preimage is a canonical
unsigned decimal string; only small exact counts appear as JSON numbers,
bounded at parse time by 9,007,199,254,740,991.

| Label | Preimage |
| --- | --- |
| `protocol-stack:revenue-routing:events-v1` | the parsed event array |
| `protocol-stack:revenue-routing:state-v1` | the canonical state value |
| `protocol-stack:revenue-routing:trace-v1` | the ordered trace records |
| `protocol-stack:revenue-routing:result-v1` | the complete result object |

### Canonical state value

```text
{
  "current_cycle": n,
  "commercial_pool": s,       "fee_pool": s,
  "commercial_carry": s,      "fee_carry": s,
  "commercial_routed_total": s, "fee_routed_total": s,
  "system_creator_balance": s,
  "creator_balances": { "{creator_id}": s },
  "founder_commercial_balances": { "{seat:05d}": s },
  "founder_fee_balances": { "{seat:05d}": s },
  "accepted_payment_ids": [ t ],
  "accepted_fee_ids": [ t ]
}
```

`s` is a canonical unsigned decimal string, `n` a JSON integer, and `t` a
string. Seat keys are zero-padded to five digits so the maps sort identically
under numeric and lexicographic ordering, matching
`founder-seat-schedule-v1`. Both identifier lists are sorted ascending.

## Canonical event input

The events input is a JSON array. Each element is an object with exactly `id`,
`kind`, and the fields required by its kind. `id` matches
`^[a-z0-9][a-z0-9_-]{0,63}$` and must be unique across the array; a duplicate
`id` is an input-shape error that aborts the run.

| Kind | Additional fields |
| --- | --- |
| `route_commercial_payment` | `payment_id`, `amount_atomic`, `project_creator_id`, `product_creator_id` |
| `route_transaction_fee` | `fee_id`, `amount_atomic` |
| `close_cycle` | `cycle_index`, `active_seats_result` |

`payment_id`, `fee_id`, `project_creator_id`, and `product_creator_id` match
the identifier pattern; `product_creator_id` may be `null`. `amount_atomic` is a
canonical unsigned decimal string within `u64`. `cycle_index` is an exact
unsigned JSON integer. `active_seats_result` is always present; `null` models an
absent research input.

### Research input

```text
active_seats_result = { cycle_index, seat_ids: [ seat_id ] }
```

The snapshot is bound to the cycle it describes. Seat identifiers must be
strictly ascending, unique, and within `0 .. 99,999`, and the list may not be
longer than the 100,000-seat capacity. An empty list is a valid snapshot and
means no seat was eligible.

This placeholder stands in for the unresolved activity proof. The activity
metric, grace allowance, performance ranking, winner count, tie rule, and
anti-gaming behavior are founder-reserved and are deliberately not invented
here. A supplied snapshot is a deterministic fixture, not evidence that any
machine was online, and it cannot become a production consensus input by
renaming.

The snapshot decides only *who* is eligible. It never decides an amount, a
share, or whether a founder-directed bound was reached.

## Transitions

### `route_commercial_payment`

1. A previously accepted `payment_id` is `REPLAY`.
2. An `amount_atomic` of zero is `ZERO_AMOUNT`; it would route nothing and emit
   an empty journal.
3. A `product_creator_id` equal to `project_creator_id` is `DUPLICATE_CREATOR`.
   The constitutional case is two distinct parties, and collapsing them into one
   balance would make the 22.5/22.5 case unobservable.
4. A checked share, remainder, pool, or balance step that leaves `u64` is
   `ARITHMETIC_OVERFLOW`.

On success, in one atomic write: the three shares and the remainder are
computed as specified above, `commercial_pool` increases by
`founder_share + remainder`, the project creator's balance increases by
`project_amount`, the product creator's balance increases by `product_amount`
when one supplies, `system_creator_balance` increases by the System Creator
share, `commercial_routed_total` increases by the whole amount, and the payment
identifier is recorded.

### `route_transaction_fee`

1. A previously accepted `fee_id` is `REPLAY`.
2. An `amount_atomic` of zero is `ZERO_AMOUNT`.
3. A checked step that leaves `u64` is `ARITHMETIC_OVERFLOW`.

On success `fee_pool` and `fee_routed_total` both increase by the whole amount
and the fee identifier is recorded. No commercial value is read or written.

### `close_cycle`

1. A `cycle_index` that is not the currently open cycle is `CYCLE_MISMATCH`.
   This covers replaying a closed cycle and skipping ahead.
2. A `null` `active_seats_result` is `MISSING_RESEARCH_INPUT`.
3. An `active_seats_result` whose `cycle_index` differs from the closing cycle
   is `INVALID_RESEARCH_INPUT`.
4. A checked step that leaves `u64` is `ARITHMETIC_OVERFLOW`.

On success, in one atomic write: both pools are distributed as specified, the
per-seat credits are added to the two founder balance maps, both carries are
replaced by their residues, both pools become zero, and `current_cycle`
increases by one.

Any failure of any transition performs none of its writes and consumes no
identifier.

## Journals and atomicity

An accepted event emits an ordered journal of
`{bucket, direction, amount_atomic}` entries. A zero-valued entry is never
emitted, so a bucket that receives nothing simply does not appear.

| Transition | Buckets |
| --- | --- |
| `route_commercial_payment` | `payment` out; `commercial_pool`, `creator:{id}`, `system_creator` in |
| `route_transaction_fee` | `fee` out; `fee_pool` in |
| `close_cycle` | `commercial_distribution` and `fee_distribution` out; `seat:{seat:05d}:commercial`, `seat:{seat:05d}:fee`, `commercial_carry`, `fee_carry` in |

The engine requires of every accepted journal:

```text
no entry has amount zero
total decreases equal total increases
no bucket appears twice in the same direction
```

and additionally per transition:

```text
route_commercial_payment: the payment decrease equals amount_atomic,
  the system_creator increase equals floor(10 * amount / 100),
  the creator increases equal the specified project and product amounts, and
  the commercial_pool increase equals amount minus every other increase
route_transaction_fee: the fee decrease equals amount_atomic and the
  fee_pool increase equals it
close_cycle: for each side, the decrease equals pool + carry before the event,
  every seat increase equals the same per-seat amount, the seat increases
  number K when per_seat > 0 and none otherwise, and the carry increase is
  strictly below K when K > 0
```

A `close_cycle` with nothing accrued and no carry emits an empty journal. That
is accepted: the cycle still advances, and the balance rule holds trivially.

### Failure atomicity by construction

A handler is a pure function of the state and the event. It returns either a
rejection or a complete write set, and never holds a reference it can partially
write. The engine commits a write set only after the journal checks pass.
Atomicity is therefore a property of the transition's shape, not of a
compensating copy that must be remembered to be taken.

This follows `founder-seat-schedule-v1` rather than
`founder-economy-simulator-v1`, whose clone-and-compare approach is quadratic
in the run length. As defence in depth the engine compares a constant-time state
summary around every rejection, and the tests compare full state digests around
rejections on bounded scenarios.

Full state invariants are `O(creators + credited seats)`, so a run asserts them
before the first event, after the last, and on a fixed stride of accepted
events.

## Result and trace

One run produces `schema`, `events_digest`, `records`, `trace_digest`,
`final_state`, `state_digest`, `metrics`, and a `result_digest` over the result
without that field. The schema string is
`protocol-stack/revenue-routing-result/v1`.

Each trace record contains the event index, event identifier, kind, acceptance
flag, result code, and the journal. A rejected record has an empty journal.

`metrics` reports the split numerators, denominator, and creator split parts,
both proved remainder bounds, both routed totals, both pools, both carries, the
System Creator balance, the creator and credited-seat counts, the closed-cycle
count, and the largest single creator, commercial seat, and fee seat balances.
Metrics are derived views; no invariant depends on them.

## Resource limits

A commercial payment and a fee read and write only the scalar and named
identifier entries they touch, so both are constant time. A cycle close is
`O(K)` in the snapshot size, bounded by the 100,000-seat capacity, and happens
once per cycle. No transition iterates over all payments, all creators, or all
historical cycles.

## Versioning and compatibility

The schema strings, event kinds, field sets, research-input shape, state shape,
journal buckets, digest labels, error codes, share numerators, creator split
parts, remainder rule, and distribution rule are immutable for version one. A
changed share, rounding rule, or semantic rule requires a new schema and ADR.

Running this model has no effect on an M1 account, height, transaction root,
receipt, state root, SQLite database, ABCI response, CometBFT validator, or on
`founder-economy-manifest-v1`, `founder-economy-simulator-v1`, or
`founder-seat-schedule-v1` state, vectors, or digests.

Error codes here are simulator result codes. M3 must separately define consensus
receipts, numeric codes, and commitments before a C++ transition exists.

## Required vectors and evidence

[`revenue-routing-v1.txt`](../../test-vectors/revenue-routing-v1.txt) is
normative. It fixes the denomination, the split numerators, the derived shares
of several anchor amounts in both creator cases, the exhaustive remainder bound
over all 200 residues, a distribution with and without a carry, the empty
snapshot case, a research scenario trace and its digests, and every rejection
code.

The executed verifier must independently derive, not restate, every recorded
value, and must fail when a recorded key is never derived.

Test coverage must include both creator cases, the maximum-remainder amounts in
each, an amount smaller than one share unit, a pool smaller than the active
population, an empty active-seat snapshot, replay of a payment, a fee, and a
cycle, an unbound snapshot, overflow of a pool near `u64` maximum, conservation
after every accepted event, the independence of the fee and commercial paths,
atomicity of every rejection, and byte-identical digests across repeated runs.

Passing these checks establishes exact routing arithmetic and conservation. It
does not establish that the activity metric is fair, that a snapshot reflects
any real machine, that a creator or product is legitimately approved, or that
the fee amount rule is sound. Those remain founder-reserved decisions and later
milestone work requiring independent review.
