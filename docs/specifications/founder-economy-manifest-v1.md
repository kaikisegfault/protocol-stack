# Founder Economy manifest v1

Status: Accepted M2 economic input and liability contract; not a consensus
transition

> **Superseded on 2026-08-07 by
> [ADR 0023](../decisions/0023-founder-decisions-activity-referrals-and-supply.md).**
> The maximum supply became 56,993,950,100 display units, the referral channel
> cap doubled to 2,500,020,000, and that channel moved from the Founder Node
> group to the direct-mint group. The replacement contract is
> [`founder-economy-manifest-v2.md`](founder-economy-manifest-v2.md), accepted
> on 2026-08-08 by
> [ADR 0024](../decisions/0024-founder-economy-manifest-v2.md). This document is
> not edited: it states the contract that the accepted M2 models implement and
> that the M2 evidence proves.

This document fixes the integer denomination, issuance-channel manifest,
exact supply derivation, and permission-liability semantics required before
the Founder Economy simulator is implemented. It is normative for the M2
manifest and fixed vectors only. It changes no M1 bytes, C++ state, configured
devnet supply, accepted simulator schema, or state root.

The change is classified as economics, input encoding, state-transition shape,
and future compatibility. ADR 0017 records the alternatives and decision.

## Scope

Version one defines exactly one canonical input object:
[`founder-economy-manifest-v1.json`](../../test-vectors/founder-economy-manifest-v1.json).
It defines abstract state reads and writes that the next independent simulator
must implement. It does not yet define serialized event bytes, a C++
transaction, a receipt encoding, an activation height, a chain epoch length,
an activity algorithm, a performance algorithm, or direct-channel production
eligibility.

The model remains one native asset. Every amount in this document is a count
of that asset's atomic unit; a channel or typed custody bucket is not a second
asset.

## Integer denomination

All monetary state uses unsigned `u64` atomic integers with checked addition,
subtraction, and multiplication.

| Property | Exact value |
| --- | ---: |
| Display decimal places | 8 |
| Atomic units per display unit | 100,000,000 |
| Maximum display units | 55,743,940,100 |
| Maximum atomic units | 5,574,394,010,000,000,000 |
| `u64` maximum | 18,446,744,073,709,551,615 |

Consensus and accounting never parse a decimal display value. A fixed display
amount is converted only by multiplying its exact integer or tenth-unit
representation by the denomination using checked integer arithmetic. Nine
decimal places would require 55,743,940,100,000,000,000 atomic units and is an
overflow, not an alternative encoding of the same amount.

## Canonical manifest representation

### JSON shape

The manifest is one UTF-8 JSON object with exactly these top-level fields:

```text
schema
research_only
denomination
seat_schedule
channels
base_permission
referral_permission
research_placeholders
```

Unknown, missing, or duplicate object fields are invalid at every depth.
Strings are compared as exact Unicode scalar sequences without normalization.
The fixed schema contains ASCII field names and values only.

`schema` is exactly
`protocol-stack/founder-economy-manifest/v1`. `research_only` is the JSON
boolean `true`. The complete nested shape and values are fixed by the checked-in
manifest; it is not a parameter template.

`decimal_places`, `founder_seat_capacity`, `maximum_seats_per_person`, and
`issuance_cycles_per_seat` are JSON integers because they are small exact
counts. Every field ending in `_atomic`, plus
`atomic_units_per_display_unit` and `maximum_supply_display`, is a JSON string
matching either `0` or `[1-9][0-9]*`. A value must parse to `u64`, and a positive
manifest amount must not be zero. Leading zeroes, a sign, decimal point,
exponent, whitespace, or JSON numeric representation are invalid.

### Canonical bytes and digest

Parse only duplicate-free I-JSON input, then serialize it with the JSON
Canonicalization Scheme in RFC 8785. JCS recursively sorts object properties,
preserves array order, emits UTF-8, and emits no insignificant whitespace.
Monetary strings remain strings throughout parsing and canonicalization.

Using `D(L)` from `protocol-primitives-v1.md`, compute:

```text
manifest_digest =
  SHA-256(
    D("protocol-stack:founder-economy:manifest-v1") ||
    jcs_manifest_bytes
  )
```

The label is 42 ASCII bytes, so its `D` prefix begins with `0x2a`. The accepted
canonical JSON is 2,297 bytes and its digest is:

```text
2a8923d40615589cc9c9ef90598c0cec56b72a7efa103cf8c05aceb5b54dc698
```

The checked-in pretty-print whitespace is not part of the digest. A parser
must validate the schema and fixed values before treating the digest as an
accepted manifest identity.

## Fixed issuance channels

The `channels` array has exactly ten entries in the following order. Each
identifier occurs once and each entry has exactly `id`, `issuance_kind`, and
`cap_atomic`.

| Index | Channel ID | Issuance kind | Cap atomic |
| ---: | --- | --- | ---: |
| 0 | `founder_operator` | `base_permission` | 2,500,020,000,000,000,000 |
| 1 | `venture_escrow` | `base_permission` | 1,250,010,000,000,000,000 |
| 2 | `community_grants_escrow` | `base_permission` | 250,002,000,000,000,000 |
| 3 | `developer_incentives_escrow` | `base_permission` | 125,001,000,000,000,000 |
| 4 | `founder_referral` | `referral_permission` | 125,001,000,000,000,000 |
| 5 | `system_creator_issuance_royalty` | `base_permission` | 73,100,000,000,000,000 |
| 6 | `liquidity_mining` | `direct_mint` | 750,006,000,000,000,000 |
| 7 | `impermanent_loss_protection` | `direct_mint` | 375,003,000,000,000,000 |
| 8 | `hub_verified_user_incentives` | `direct_mint` | 125,001,000,000,000,000 |
| 9 | `initial_mystery_box_incentives` | `direct_mint` | 1,250,010,000,000,000 |

Checked addition must reproduce:

```text
Founder Node subtotal = 4,323,134,000,000,000,000 atomic
direct-mint subtotal  = 1,251,260,010,000,000,000 atomic
maximum supply        = 5,574,394,010,000,000,000 atomic
```

No implicit, unnamed, genesis, burn, bridge, rounding, or remainder channel
exists. Each issued atomic unit is attributed to exactly one of these channel
IDs forever.

## Seat and cycle arithmetic

Seat identifiers are unsigned integers from `0` through `99,999`. A human may
control at most 1,000 seats. The ownership and enrollment model that proves
that bound is outside this specification.

Each activated seat has exactly 731 issuance cycle indexes from `0` through
`730`. This zero-based index is the replay key for M2. A future protocol must
derive it from an accepted height or epoch schedule; local time and a supplied
calendar timestamp are invalid sources. This document does not choose a block
count per 24-hour-target cycle.

### Base permission

One evaluated seat cycle creates one base permission with the following
atomic legs:

| Channel | Beneficiary kind | Atomic amount |
| --- | --- | ---: |
| `venture_escrow` | typed venture escrow | 17,100,000,000 |
| `community_grants_escrow` | typed community-grants escrow | 3,420,000,000 |
| `developer_incentives_escrow` | typed developer-incentives escrow | 1,710,000,000 |
| `system_creator_issuance_royalty` | System Creator Company | 1,000,000,000 |
| `founder_operator` | cycle founder or supplied performance allocation | 34,200,000,000 |
| **Total** | | **57,430,000,000** |

For the complete seat capacity and cycle schedule, checked multiplication
reproduces every base channel cap:

```text
34,200,000,000 * 100,000 * 731 = 2,500,020,000,000,000,000
17,100,000,000 * 100,000 * 731 = 1,250,010,000,000,000,000
 3,420,000,000 * 100,000 * 731 =   250,002,000,000,000,000
 1,710,000,000 * 100,000 * 731 =   125,001,000,000,000,000
 1,000,000,000 * 100,000 * 731 =    73,100,000,000,000,000
```

The full base schedule is 4,198,133,000,000,000,000 atomic units.

For one seat across all 731 cycles, the same checked products are:

```text
Founder operator                    = 25,000,200,000,000 atomic
venture escrow                      = 12,500,100,000,000 atomic
community-grants escrow             =  2,500,020,000,000 atomic
developer-incentives escrow         =  1,250,010,000,000 atomic
System Creator issuance royalty     =    731,000,000,000 atomic
base permission total               = 41,981,330,000,000 atomic
```

### Referral permission

A referred active seat cycle additionally creates a separate referral
permission of 1,710,000,000 atomic units for the recorded referrer. The
complete all-seats, all-cycles bound is:

```text
1,710,000,000 * 100,000 * 731 = 125,001,000,000,000,000
```

This equals the referral-channel cap. An inactive referred cycle uses the
explicit `inactive_referral_eligibility_result` research input; this contract
does not decide whether that cycle creates the referral permission.

One fully referred seat reserves at most 1,250,010,000,000 referral-channel
atomic units across 731 cycles. Its base plus referral maximum is therefore
43,231,340,000,000 atomic units.

## Abstract accounting state

The next M2 simulator must expose state equivalent to:

```text
channels[channel_id] = {
  issued_atomic:u64,
  outstanding_atomic:u64
}

pending_permissions[(seat_id, cycle_index, kind)] = ordered legs
evaluated_permission_keys = set<(seat_id, cycle_index, kind)>
accepted_direct_decision_ids = set<bounded identifier>
typed_custody[(beneficiary_kind, beneficiary_id)] = u64
```

`kind` is `base` or `referral`. An implementation may use a more compact
aggregate representation only if it preserves the exact per-seat,
per-cycle replay decision, every beneficiary liability, and identical
observable results. It may not iterate over all 100,000 seats inside an
unrelated transition.

The abstract resource ceiling is 73,100,000 base evaluation keys and at most
73,100,000 referral evaluation keys. A production encoding and bounded
settlement mechanism remain M3 work. The unresolved performance winner count
means this M2 contract cannot yet select a safe production allocation-list
bound smaller than the seat capacity.

At every accepted state:

```text
for each channel:
  issued_atomic + outstanding_atomic <= cap_atomic

issued_supply = checked_sum(channel.issued_atomic)
outstanding_permissions = checked_sum(channel.outstanding_atomic)

issued_supply <= maximum_supply_atomic
issued_supply + outstanding_permissions <= maximum_supply_atomic

checked_sum(typed_custody) = issued_supply
```

Outstanding permission units are liabilities against channel capacity. They
are not issued supply, circulating supply, an account balance, or spendable
escrow custody.

## Permission creation

### Required deterministic inputs

Cycle evaluation identifies an existing activated seat and one cycle index.
It consumes a supplied `activity_eligibility_result` bound to that exact seat
and cycle. The result is a research fixture until the activity verifier and
canonical envelope are specified.

If the result says active, the `founder_operator` leg belongs to the evaluated
seat. If it says inactive:

1. the other four base legs retain their fixed beneficiaries and amounts;
2. an `inactive_performance_allocation_result` bound to the same cycle must
   provide one or more unique active Founder Seat recipients;
3. every allocation must be positive and fit `u64`;
4. checked addition of the allocations must equal 34,200,000,000 atomic; and
5. the inactive source seat must not be a recipient.

The supplied allocation is a deterministic stand-in for the unresolved
best-performer policy. Its recipient count, metric, tie behavior, and
authenticity are not production decisions.

### Atomic creation

For a base permission key `(seat_id, cycle_index, base)`:

1. read the seat and cycle bounds, evaluated-key set, fixed manifest, activity
   result, and any required performance result;
2. construct every fixed leg and resolved Founder allocation;
3. read issued and outstanding values for every involved channel;
4. prove each checked new outstanding value leaves
   `issued + outstanding <= cap`;
5. insert the complete pending permission, add the evaluated key, and increase
   every channel outstanding amount atomically.

No beneficiary receives issued custody during creation. Any failure performs
none of step 5 and does not consume the key.

Referral evaluation uses `(seat_id, cycle_index, referral)`. An active referred
seat creates the fixed referral leg. An inactive referred seat must supply the
placeholder boolean result; a false result records the referral key as
evaluated without reserving value so later replay cannot change the outcome.
An unreferred seat creates no referral permission.

Base and referral evaluation are independent. Failure or exhaustion in the
referral path cannot remove or modify an accepted base permission.

## Permission exercise

Exercise references one pending permission key. Authorization is an explicit
M2 simulator capability and is not accepted as a production authority by this
document.

For one exercise:

1. read the complete ordered permission legs and all affected channel and
   custody values;
2. prove every outstanding subtraction is valid;
3. prove every issued and custody addition fits `u64`, preserves the channel
   cap, and preserves total conservation;
4. decrease every affected channel outstanding value;
5. increase every affected channel issued value;
6. credit every typed beneficiary; and
7. remove the pending permission while retaining its evaluated replay key.

Steps 4 through 7 are one atomic journal. Partial exercise, per-leg exercise,
implicit expiry, burn, sweep, beneficiary substitution, and issue-now/pay-later
accounting are invalid. A failure changes no state. A second exercise finds no
pending permission and cannot issue value again.

## Direct-channel issuance

A direct transition selects exactly one of the four `direct_mint` channel IDs,
a positive atomic amount, one beneficiary, and a unique decision identifier.
It must include a `direct_channel_eligibility_result` bound to the same channel,
amount, beneficiary, and decision identifier.

The M2 result is an explicit deterministic fixture. This contract does not
define proof, anti-abuse, timing, per-participant limit, or real eligibility.

An accepted direct transition:

1. rejects a previously accepted decision identifier;
2. uses checked arithmetic to prove `issued + outstanding + amount <= cap`;
3. increases that channel's issued amount and the beneficiary's typed custody
   by the same amount; and
4. records the decision identifier atomically.

It does not create a general public mint capability. Any failure changes no
state and does not consume the decision identifier.

## Validation and failure order

A manifest loader returns the first applicable error in this order:

| Order | Error | Condition |
| ---: | --- | --- |
| 1 | `INVALID_JSON` | Invalid UTF-8 or JSON, duplicate field, non-object root, or trailing data |
| 2 | `UNKNOWN_FIELD` | Missing, extra, or wrong nested field shape |
| 3 | `SCHEMA` | Wrong schema string or `research_only` is not `true` |
| 4 | `TYPE` | Wrong JSON type or non-canonical unsigned decimal string |
| 5 | `RANGE` | Count or parsed unsigned integer is outside its allowed range |
| 6 | `MANIFEST_MISMATCH` | Any fixed identifier, order, kind, amount, beneficiary kind, or placeholder differs |
| 7 | `ARITHMETIC_OVERFLOW` | A required checked derivation cannot fit `u64` |
| 8 | `SUPPLY_MISMATCH` | Legs, channel subtotals, full schedules, or total maximum do not equal the fixed derivations |

The future simulator must preserve the following ordinary semantic failures
and their no-write behavior, though its serialized event schema and numeric
codes remain a separate acceptance step:

| Error | Meaning |
| --- | --- |
| `CYCLE_RANGE` | Seat or cycle index is outside the manifest bounds |
| `REPLAY` | Permission key or direct decision was already accepted |
| `MISSING_RESEARCH_INPUT` | A required explicit placeholder result is absent |
| `INVALID_RESEARCH_INPUT` | A placeholder is not bound to the exact attempted action |
| `INVALID_PERFORMANCE_ALLOCATION` | Recipients are invalid or amounts do not sum to the Founder leg |
| `CHANNEL_CAP` | Issued plus outstanding plus requested value exceeds one channel cap |
| `PERMISSION_NOT_FOUND` | Exercise names no pending permission |
| `ARITHMETIC_OVERFLOW` | Any checked intermediate exceeds `u64` |
| `INVARIANT` | A pre-state or proposed journal violates conservation |

Shape-invalid serialized simulator input may abort its run. A well-shaped
ordinary failure must produce a deterministic rejected trace item, perform no
state write, and consume no new replay identifier.

## Receipts, commitments, and M1 effects

This specification assigns no canonical transaction bytes, receipt bytes,
state-root schema, or block result. The next M2 simulator specification must
define deterministic input, trace, and final-state digests around these exact
values. M3 must separately define consensus receipts and commitments before a
C++ transition exists.

Loading or modeling this manifest has no effect on an M1 account, fee pool,
height, transaction root, receipt, state root, SQLite database, ABCI response,
or CometBFT validator. The existing M1 nine-decimal supply remains conserved.

## Versioning and compatibility

The schema string, field set, array order, identifiers, values, JCS rules,
domain label, and digest are immutable for version one. A changed amount,
precision, field, placeholder, or semantic rule requires a new manifest schema
and ADR; it must not reinterpret this digest.

The eight-decimal Founder target is not an in-place reinterpretation of M1
nine-decimal atomic balances. A future implementation must choose a new
genesis or explicit versioned migration and activation rule. It must provide
fixed old/new state vectors, replay behavior across the boundary, rollback
handling, C++/Python agreement, and independent review.

The four research placeholders cannot become production consensus inputs by
renaming a fixture. Each requires a canonical result envelope, authorization,
resource bound, failure policy, and founder decision where reserved.

## Required vectors and evidence

[`founder-economy-manifest-v1.txt`](../../test-vectors/founder-economy-manifest-v1.txt)
is normative. It fixes:

- the denomination fit and nine-decimal overflow boundary;
- canonical manifest byte length and digest;
- every channel cap, subtotal, and total;
- every per-cycle leg and complete 100,000-seat, 731-cycle product;
- active, inactive-allocation, referral, permission reserve/exercise, and
  direct-channel examples; and
- manifest, replay, cap, placeholder, overflow, and atomicity rejections.

Acceptance requires independent exact-integer reproduction of the vectors,
full GitHub-hosted repository verification on the exact commit, the separate
standard-library Python simulator and adversarial scenarios in the next
slice, and independent economic and protocol review before any production
activation claim.
