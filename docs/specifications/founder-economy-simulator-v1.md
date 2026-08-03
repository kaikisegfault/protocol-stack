# Founder Economy simulator v1

Status: Accepted M2 research model contract; not a consensus transition

This document defines the deterministic input, transition, failure, and digest
contract for the independent standard-library Python Founder Economy
simulator. It realizes the abstract accounting state and transitions specified
in [`founder-economy-manifest-v1.md`](founder-economy-manifest-v1.md) as an
executable model.

The change is classified as economics, input encoding, and state-transition
shape. ADR 0018 records the alternatives and decision. It changes no M1 bytes,
C++ state, configured devnet supply, previously accepted simulator schema, or
state root.

## Scope

Version one defines:

- the strict manifest loader and its ordered failure codes;
- the canonical simulator event array;
- five state transitions and their exact reads, writes, and journals;
- the deterministic state, trace, events, and result digests; and
- the normative vector obligations.

It does not define serialized consensus transaction bytes, receipt bytes, a
state-root schema, a block result, an activation height, a chain epoch length,
an activity algorithm, a performance algorithm, or production direct-channel
eligibility. Those remain M3 work.

The model remains one native asset. Every amount is a count of that asset's
atomic unit. A channel, escrow, or typed custody bucket is an accounting
partition, not a second asset.

## Determinism rules

The simulator is a pure function of its two JSON inputs. It must not read a
wall clock, environment variable, locale, random source, network, hash seed
that affects output ordering, or any mutable external value. It must not use
floating-point arithmetic anywhere, including for intermediate derivations.

All monetary arithmetic is unsigned `u64` with checked addition,
subtraction, and multiplication as defined in
`founder-economy-manifest-v1.md`. Any checked operation that would leave the
range fails; it never wraps, saturates, or promotes to a wider type in an
accepted result.

## Canonical bytes and digests

Every digest preimage is produced by parsing duplicate-free I-JSON and
serializing it with the JSON Canonicalization Scheme in RFC 8785. Using `D(L)`
from `protocol-primitives-v1.md`:

```text
digest(label, value) = SHA-256( D(label) || jcs_bytes(value) )
```

Every monetary value inside a digest preimage is a canonical unsigned decimal
string matching `0` or `[1-9][0-9]*`. Only small exact counts — seat
identifiers, cycle indexes, trace indexes, channel counts, and array lengths —
appear as JSON numbers. No monetary value is ever serialized as a JSON number,
so no digest preimage depends on binary64 range.

The following labels are fixed for version one:

| Label | Preimage |
| --- | --- |
| `protocol-stack:founder-economy:manifest-v1` | the accepted manifest object |
| `protocol-stack:founder-economy:events-v1` | the parsed event array |
| `protocol-stack:founder-economy:state-v1` | the canonical state value |
| `protocol-stack:founder-economy:trace-v1` | the ordered trace records |
| `protocol-stack:founder-economy:result-v1` | the complete result object |

The manifest label, canonical byte length 2,297, and digest
`2a8923d40615589cc9c9ef90598c0cec56b72a7efa103cf8c05aceb5b54dc698` are
inherited unchanged from `founder-economy-manifest-v1.md`. The simulator must
reproduce them from the checked-in manifest file rather than restating them.

## Manifest loading

The loader accepts exactly the checked-in manifest. It is not a parameter
template: every identifier, order, kind, and amount is compared against the
fixed contract. The first applicable error is returned in this order.

| Order | Error | Condition |
| ---: | --- | --- |
| 1 | `INVALID_JSON` | Invalid UTF-8 or JSON, duplicate field, non-object root, trailing data, or any floating-point token |
| 2 | `UNKNOWN_FIELD` | Missing, extra, or wrong nested field shape at any depth |
| 3 | `SCHEMA` | Wrong `schema` string or `research_only` is not the boolean `true` |
| 4 | `TYPE` | Wrong JSON type, or a monetary string that is not a canonical unsigned decimal |
| 5 | `RANGE` | A parsed count or unsigned integer is outside its allowed range, including above `u64` maximum |
| 6 | `MANIFEST_MISMATCH` | Any fixed identifier, array order, issuance kind, amount, beneficiary kind, or research placeholder differs |
| 7 | `ARITHMETIC_OVERFLOW` | A required checked derivation cannot fit `u64` |
| 8 | `SUPPLY_MISMATCH` | Legs, channel subtotals, per-seat schedules, full schedules, or the total maximum do not equal the fixed derivations |

`RANGE` applies before `MANIFEST_MISMATCH` so that an unrepresentable value is
reported as a range failure rather than a content difference. A value that is
representable but different is a `MANIFEST_MISMATCH`.

After the field checks pass, the loader recomputes and requires:

```text
sum(base leg amounts)                      = base_permission.total_atomic
sum(base_permission caps over 100000, 731) = each base channel cap
referral amount * 100000 * 731             = founder_referral cap
sum(base_permission channel caps)
  + founder_referral cap                   = 4323134000000000000
sum(direct_mint channel caps)              = 1251260010000000000
sum(all channel caps)                      = maximum_supply_atomic
maximum_supply_display * 10^8              = maximum_supply_atomic
```

A loaded manifest exposes its canonical byte length and digest so a caller
never recomputes the domain-separation rule independently.

## Simulator state

```text
seats[seat_id] = { referrer_seat_id: seat_id | none }

channels[channel_id] = {
  issued_atomic:u64,
  outstanding_atomic:u64
}

pending_permissions[(seat_id, cycle_index, kind)] = ordered legs
evaluated_permission_keys = set<(seat_id, cycle_index, kind)>
accepted_direct_decision_ids = set<decision identifier>
typed_custody[custody_key] = u64
```

`kind` is `base` or `referral`. Every channel begins at zero issued and zero
outstanding; there is no genesis allocation.

### Custody keys

A custody key is `{beneficiary_kind}:{beneficiary_id}` where the beneficiary
kind is resolved at permission creation, not at exercise:

| Manifest beneficiary kind | Resolved custody key |
| --- | --- |
| `venture_escrow` | `venture_escrow:global` |
| `community_grants_escrow` | `community_grants_escrow:global` |
| `developer_incentives_escrow` | `developer_incentives_escrow:global` |
| `system_creator_company` | `system_creator_company:global` |
| `cycle_founder_or_performance_result` | `founder_seat:{seat_id}` |
| `recorded_referrer` | `founder_seat:{referrer_seat_id}` |
| direct-channel beneficiary | `direct_beneficiary:{beneficiary_id}` |

Resolving the Founder beneficiary at creation is what makes an inactive cycle's
reallocation permanent: a later exercise cannot restore the original seat.

### Invariants

At every accepted state:

```text
for each channel:
  issued_atomic + outstanding_atomic <= cap_atomic

issued_supply            = checked_sum(channel.issued_atomic)
outstanding_permissions  = checked_sum(channel.outstanding_atomic)

issued_supply                            <= maximum_supply_atomic
issued_supply + outstanding_permissions  <= maximum_supply_atomic
checked_sum(typed_custody)                = issued_supply

every pending permission's legs sum to its recorded total
every pending permission key is in evaluated_permission_keys
no stored amount is zero
```

Outstanding permission units are liabilities against channel capacity. They are
not issued supply, circulating supply, an account balance, or spendable escrow
custody.

## Canonical event input

The events input is a JSON array. Each element is an object with exactly `id`,
`kind`, and the fields required by its kind. `id` matches
`^[a-z0-9][a-z0-9_-]{0,63}$` and must be unique across the array; a duplicate
`id` is an input-shape error that aborts the run rather than a modelled
rejection.

Seat identifiers and cycle indexes are JSON integers. Monetary values are
canonical unsigned decimal strings. A research-input field is always present;
the JSON value `null` models an absent research input and produces the
modelled `MISSING_RESEARCH_INPUT` rejection.

| Kind | Additional fields |
| --- | --- |
| `activate_seat` | `seat_id`, `referrer_seat_id` |
| `evaluate_base_permission` | `seat_id`, `cycle_index`, `activity_result`, `performance_allocation` |
| `evaluate_referral_permission` | `seat_id`, `cycle_index`, `activity_result`, `inactive_referral_result` |
| `exercise_permission` | `seat_id`, `cycle_index`, `permission_kind` |
| `direct_issue` | `channel`, `decision_id`, `beneficiary_id`, `amount_atomic`, `eligibility_result` |

`referrer_seat_id` is `null` for an unreferred seat or a seat identifier that
is not the activating seat. `permission_kind` is `base` or `referral`.
`channel` must be one of the four `direct_mint` channel identifiers.
`decision_id` and `beneficiary_id` match the identifier pattern.

### Research input objects

Each research input is bound to the exact action it authorizes. A well-formed
object whose binding fields differ from the attempted action produces
`INVALID_RESEARCH_INPUT`; it is never silently reinterpreted.

```text
activity_result           = { seat_id, cycle_index, active:bool }
performance_allocation    = { seat_id, cycle_index,
                              allocations:[ { seat_id, amount_atomic } ] }
inactive_referral_result  = { seat_id, cycle_index, create:bool }
eligibility_result        = { channel, decision_id, beneficiary_id,
                              amount_atomic, eligible:bool }
```

`performance_allocation.seat_id` binds to the inactive source seat.
`allocations` is a non-empty array in the order supplied; that order is
preserved in the journal and trace.

These four objects are the research placeholders named by the manifest. They
are deterministic stand-ins. Their authenticity, authorization, resource
bound, and real policy are unresolved and cannot become production consensus
inputs by renaming a fixture.

## Transitions

### Seat activation

Reads the seat bounds and the seat table. Writes one seat record.

1. `seat_id` outside `0..99,999` is `CYCLE_RANGE`.
2. A `referrer_seat_id` outside the bounds, or equal to `seat_id`, is
   `INVALID_REFERRER`.
3. An already-activated `seat_id` is `REPLAY`.
4. A `referrer_seat_id` that is not itself activated is `SEAT_NOT_ACTIVATED`.

Activation issues nothing, reserves nothing, and emits an empty journal. This
version models the seat graph only; enrollment, payment proof, biometric
identity, manager records, and the 1,000-seats-per-person bound belong to M4
and are explicitly not modelled here.

### Base permission evaluation

Creates one base permission for `(seat_id, cycle_index, base)`.

1. `seat_id` or `cycle_index` outside `0..99,999` and `0..730` is
   `CYCLE_RANGE`.
2. An unactivated seat is `SEAT_NOT_ACTIVATED`.
3. An already-evaluated key is `REPLAY`.
4. A `null` `activity_result` is `MISSING_RESEARCH_INPUT`.
5. An `activity_result` not bound to this seat and cycle is
   `INVALID_RESEARCH_INPUT`.
6. If `active` is true, `performance_allocation` must be `null`; otherwise it
   is `INVALID_RESEARCH_INPUT`. The `founder_operator` leg resolves to
   `founder_seat:{seat_id}`.
7. If `active` is false, a `null` `performance_allocation` is
   `MISSING_RESEARCH_INPUT` and one not bound to this seat and cycle is
   `INVALID_RESEARCH_INPUT`.
8. An allocation list that is empty, contains a repeated recipient, contains
   the inactive source seat, contains an unactivated or out-of-range recipient,
   contains a zero or non-`u64` amount, or whose checked sum is not
   34,200,000,000 atomic is `INVALID_PERFORMANCE_ALLOCATION`.
9. Every resulting leg is proved against its channel: a checked
   `issued + outstanding + amount` above `cap_atomic` is `CHANNEL_CAP`, and a
   checked intermediate outside `u64` is `ARITHMETIC_OVERFLOW`.

On success the four fixed legs and the resolved Founder leg or legs are stored
as one ordered pending permission, the key is recorded as evaluated, and every
involved channel's outstanding amount increases. No beneficiary receives
issued custody. Any failure performs none of these writes and does not consume
the key.

The inactive path retains the complete 574.3-unit permission: the four
non-Founder legs keep their fixed beneficiaries and amounts, and only the
34,200,000,000-atomic Founder leg changes beneficiary.

An M2 allocation recipient must be an activated seat distinct from the source.
Proving that each recipient was *active in that same cycle* requires the
unresolved performance policy and its evidence envelope; that stronger check is
an M3 obligation and is deliberately not invented here.

### Referral permission evaluation

Creates one referral permission for `(seat_id, cycle_index, referral)`.

1. Bounds, activation, and replay behave as above.
2. A seat with a `null` recorded referrer is `SEAT_NOT_REFERRED`.
3. The `activity_result` rules are identical.
4. If `active` is true, `inactive_referral_result` must be `null`; the fixed
   1,710,000,000-atomic leg is created for `founder_seat:{referrer_seat_id}`.
5. If `active` is false, a `null` `inactive_referral_result` is
   `MISSING_RESEARCH_INPUT`, and one not bound to this seat and cycle is
   `INVALID_RESEARCH_INPUT`.
6. A false `create` result records the key as evaluated and reserves no value,
   so a later replay cannot change the outcome. This is an accepted event with
   an empty journal, not a rejection.
7. Channel proof behaves as above against `founder_referral`.

Base and referral evaluation are independent. Failure or cap exhaustion in the
referral path can never remove, modify, or block an accepted base permission.

Whether an inactive referred cycle creates the referral permission is a
founder-reserved policy. This contract requires the answer to be supplied per
cycle and records it; it does not choose one.

### Permission exercise

References one pending permission key.

1. Bounds failures are `CYCLE_RANGE`.
2. No pending permission for the key is `PERMISSION_NOT_FOUND`. A second
   exercise therefore cannot issue value again.
3. A pending permission whose legs do not sum to its recorded total is
   `INVARIANT`. Partial exercise, per-leg exercise, implicit expiry, burn,
   sweep, and beneficiary substitution are not expressible in this schema and
   are invalid.
4. Every outstanding subtraction must be valid, every issued and custody
   addition must fit `u64`, and every channel cap must hold. A violation is
   `ARITHMETIC_OVERFLOW` or `CHANNEL_CAP`.

On success, in one atomic journal: every affected channel's outstanding amount
decreases, its issued amount increases by the same value, every typed
beneficiary is credited, and the pending permission is removed while its
evaluated replay key is retained. A failure changes no state.

Authorization is an explicit simulator capability. This document does not
accept it as a production authority.

### Direct-channel issuance

Selects one `direct_mint` channel, a positive amount, one beneficiary, and a
unique decision identifier.

1. A channel identifier that is unknown or is not `direct_mint` is
   `INVALID_CHANNEL`.
2. A zero amount is `ZERO_AMOUNT`; an amount above `u64` is a `TYPE` input
   error at parse time.
3. A previously accepted `decision_id` is `REPLAY`.
4. A `null` `eligibility_result` is `MISSING_RESEARCH_INPUT`.
5. A result whose channel, decision identifier, beneficiary, or amount differs
   from the attempted action is `INVALID_RESEARCH_INPUT`.
6. A false `eligible` result is `NOT_ELIGIBLE` and consumes no decision
   identifier.
7. A checked `issued + outstanding + amount` above `cap_atomic` is
   `CHANNEL_CAP`.

On success the channel's issued amount and the beneficiary's typed custody
increase by the same amount and the decision identifier is recorded, all
atomically. Direct issuance creates no permission and never shares the Founder
permission authority. Any failure changes no state and does not consume the
decision identifier.

## Journals and atomicity

An accepted transition emits an ordered journal of `{bucket, delta}` entries.
Buckets are `capacity:{channel}`, `outstanding:{channel}`, `issued:{channel}`,
and `custody:{key}`. No entry has a zero delta.

`capacity:{channel}` is the derived remaining capacity
`cap - issued - outstanding`. The engine requires both:

```text
sum(capacity deltas) + sum(outstanding deltas) + sum(issued deltas) = 0
sum(custody deltas) = sum(issued deltas)
```

Permission creation therefore moves value from capacity to outstanding,
exercise moves it from outstanding to issued and mirrors it into custody, and
direct issuance moves it from capacity to issued and mirrors it into custody.

Every transition is applied to a clone of the accepted state. An accepted
outcome is committed only after its journal balances and the full state
invariants hold. A rejected outcome discards the clone, must emit no journal,
and must leave the state digest unchanged; the engine asserts both.

Because rejection is checked by comparing state digests before and after, a
silent partial write is a test failure rather than a documentation claim.

## Result and trace

One run produces:

```text
schema           = protocol-stack/founder-economy-simulation-result/v1
manifest_digest  = the accepted manifest digest
manifest_canonical_length = 2297
events_digest    = digest over the parsed event array
records          = ordered trace records
trace_digest     = digest over records
final_state      = canonical state value
state_digest     = digest over final_state
metrics          = derived totals
result_digest    = digest over the result object without this field
```

Each trace record contains the event index, event identifier, kind, acceptance
flag, result code, the state digest before and after, and the journal. A
rejected record has an empty journal and equal before and after digests.

`metrics` reports issued supply, outstanding permissions, remaining capacity,
per-channel issued and outstanding amounts, pending permission count,
evaluated key count, and accepted decision count. Metrics are derived views; no
invariant depends on them.

## Resource limits

The abstract ceiling is 73,100,000 base evaluation keys and at most 73,100,000
referral evaluation keys. A transition reads and writes only the seat, cycle,
channel, permission, and custody entries it names; no transition iterates over
all seats or all cycles.

Simulation scenarios are bounded by their event arrays. A production encoding
and bounded settlement mechanism remain M3 work. The unresolved performance
winner count means this contract cannot yet select a safe production
allocation-list bound smaller than the seat capacity, so the simulator accepts
any list satisfying the checks above and records that limitation.

## Versioning and compatibility

The schema strings, event kinds, field sets, research-input shapes, custody-key
format, journal buckets, digest labels, and error codes are immutable for
version one. A changed transition, field, or semantic rule requires a new
simulator schema and ADR.

Loading or running this model has no effect on an M1 account, fee pool, height,
transaction root, receipt, state root, SQLite database, ABCI response, or
CometBFT validator. The existing M1 nine-decimal supply remains conserved. The
eight-decimal Founder target is not an in-place reinterpretation of M1
balances; the migration or new-genesis requirement in ADR 0017 is unchanged.

Error codes here are simulator result codes. M3 must separately define
consensus receipts, numeric codes, and commitments before a C++ transition
exists.

## Required vectors and evidence

[`founder-economy-manifest-v1.txt`](../../test-vectors/founder-economy-manifest-v1.txt)
remains normative and must now be reproduced by an executed verifier rather
than by review alone. The verifier must independently derive, not merely
compare, the denomination fit and nine-decimal overflow, canonical byte length
and digest, every channel cap and subtotal, every per-cycle leg, every
per-seat 731-cycle product, every full-schedule product, the active,
inactive-allocation, referral, exercise, and direct-channel fixtures, and every
listed rejection.

Test coverage must include positive, negative, boundary, replay, overflow,
atomicity, cap-exhaustion, inactivity, and complete 731-cycle scenarios, plus
byte-identical digests across repeated runs.

Acceptance requires full GitHub-hosted verification on the exact commit.
Passing these checks establishes exact accounting, not economic safety or
production readiness. The four research placeholders and the founder-reserved
policies they stand in for still require owner decisions, adversarial
economic simulation, and independent review before any activation claim.
