# Founder Economy manifest v2

Status: Accepted M3 economic input and liability contract; not a consensus
transition

This document fixes the integer denomination, issuance-channel manifest, exact
supply derivation, and permission-liability semantics of the economy the
Founder Constitution directs after the 2026-08-07 founder decisions. It is
normative for the M3 manifest and fixed vectors only. It changes no M1 bytes,
C++ state, configured devnet supply, accepted simulator schema, or state root.

The change is classified as economics, input encoding, state-transition shape,
and future compatibility.
[ADR 0024](../decisions/0024-founder-economy-manifest-v2.md) records the
alternatives and decision, and
[ADR 0023](../decisions/0023-founder-decisions-activity-referrals-and-supply.md)
records the founder direction it implements.

## Relationship to version one

[`founder-economy-manifest-v1.md`](founder-economy-manifest-v1.md) is not
edited, retracted, or reinterpreted. It states the contract the accepted M2
models implement and the M2 evidence proves. Version two is a separate accepted
contract with its own schema string, domain label, canonical bytes, and digest.

Three things changed, and nothing else did:

| | v1 | v2 |
| --- | ---: | ---: |
| Maximum supply, display units | 55,743,940,100 | 56,993,950,100 |
| Founder referral benefit, per cycle | 17.1 | 34.2 |
| `founder_referral` cap, display units | 1,250,010,000 | 2,500,020,000 |
| `founder_referral` issuance kind | `referral_permission` | `direct_mint` |

The other nine channel caps, the eight-decimal denomination, the seat capacity,
the per-person bound, the 731-cycle schedule, and every base-permission leg are
unchanged. The vectors prove this rather than asserting it: the maximum rose by
1,250,010,000 display units, the referral channel rose by exactly the same
amount, and the summed absolute change across all nine other channels is zero.

Version two removes the `referral_permission` issuance kind entirely, so a v2
manifest has exactly two kinds. The two loaders reject each other's manifests.

## Scope

Version two defines exactly one canonical input object:
[`founder-economy-manifest-v2.json`](../../test-vectors/founder-economy-manifest-v2.json).
It defines abstract state reads and writes that the revised simulator must
implement. It does not yet define serialized event bytes, a C++ transaction, a
receipt encoding, an activation height, a chain epoch length, the uptime record,
the activity threshold in chain terms, the performance winner computation, the
definition of a month in cycles, or direct-channel production eligibility.

The model remains one native asset. Every amount in this document is a count of
that asset's atomic unit; a channel or typed custody bucket is not a second
asset.

## Integer denomination

All monetary state uses unsigned `u64` atomic integers with checked addition,
subtraction, and multiplication.

| Property | Exact value |
| --- | ---: |
| Display decimal places | 8 |
| Atomic units per display unit | 100,000,000 |
| Maximum display units | 56,993,950,100 |
| Maximum atomic units | 5,699,395,010,000,000,000 |
| `u64` maximum | 18,446,744,073,709,551,615 |
| `u64` headroom above the maximum | 12,747,349,063,709,551,615 |

The revised maximum leaves more than twice its own size in `u64` headroom, so
the accepted eight-decimal denomination is unchanged and no arithmetic widens.

Consensus and accounting never parse a decimal display value. A fixed display
amount is converted only by multiplying its exact integer or tenth-unit
representation by the denomination using checked integer arithmetic. Nine
decimal places would require 56,993,950,100,000,000,000 atomic units and is an
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
referral_benefit
research_placeholders
```

Unknown, missing, or duplicate object fields are invalid at every depth.
Strings are compared as exact Unicode scalar sequences without normalization.
The fixed schema contains ASCII field names and values only.

`schema` is exactly `protocol-stack/founder-economy-manifest/v2`.
`research_only` is the JSON boolean `true`. The complete nested shape and
values are fixed by the checked-in manifest; it is not a parameter template.

`decimal_places`, `founder_seat_capacity`, `maximum_seats_per_person`, and
`issuance_cycles_per_seat` are JSON integers because they are small exact
counts. `referral_benefit.unconditional` is a JSON boolean. Every field ending
in `_atomic`, plus `atomic_units_per_display_unit` and
`maximum_supply_display`, is a JSON string matching either `0` or
`[1-9][0-9]*`. A value must parse to `u64`, and a positive manifest amount must
not be zero. Leading zeroes, a sign, decimal point, exponent, whitespace, or
JSON numeric representation are invalid.

### Canonical bytes and digest

Parse only duplicate-free I-JSON input, then serialize it with the JSON
Canonicalization Scheme in RFC 8785. JCS recursively sorts object properties,
preserves array order, emits UTF-8, and emits no insignificant whitespace.
Monetary strings remain strings throughout parsing and canonicalization.

Using `D(L)` from [`protocol-primitives-v1.md`](protocol-primitives-v1.md),
compute:

```text
manifest_digest =
  SHA-256(
    D("protocol-stack:founder-economy:manifest-v2") ||
    jcs_manifest_bytes
  )
```

The label is 42 ASCII bytes, so its `D` prefix begins with `0x2a`. The accepted
canonical JSON is 2,267 bytes and its digest is:

```text
84cca09865b6c62bf09d3f6bc3821a2527c7a4835652cffdc0ebefa34b314ce5
```

The checked-in pretty-print whitespace is not part of the digest, and neither
is the source field order. A parser must validate the schema and fixed values
before treating the digest as an accepted manifest identity.

## Fixed issuance channels

The `channels` array has exactly ten entries in the following order, which
follows the Founder Constitution's two allocation tables: the five Founder Node
distribution channels, then the five direct-mint channels. Each identifier
occurs once and each entry has exactly `id`, `issuance_kind`, and `cap_atomic`.

| Index | Channel ID | Issuance kind | Cap atomic |
| ---: | --- | --- | ---: |
| 0 | `founder_operator` | `base_permission` | 2,500,020,000,000,000,000 |
| 1 | `venture_escrow` | `base_permission` | 1,250,010,000,000,000,000 |
| 2 | `community_grants_escrow` | `base_permission` | 250,002,000,000,000,000 |
| 3 | `developer_incentives_escrow` | `base_permission` | 125,001,000,000,000,000 |
| 4 | `system_creator_issuance_royalty` | `base_permission` | 73,100,000,000,000,000 |
| 5 | `liquidity_mining` | `direct_mint` | 750,006,000,000,000,000 |
| 6 | `impermanent_loss_protection` | `direct_mint` | 375,003,000,000,000,000 |
| 7 | `founder_referral` | `direct_mint` | 250,002,000,000,000,000 |
| 8 | `hub_verified_user_incentives` | `direct_mint` | 125,001,000,000,000,000 |
| 9 | `initial_mystery_box_incentives` | `direct_mint` | 1,250,010,000,000,000 |

Checked addition must reproduce:

```text
Founder Node subtotal = 4,198,133,000,000,000,000 atomic  (41,981,330,000 display)
direct-mint subtotal  = 1,501,262,010,000,000,000 atomic  (15,012,620,100 display)
maximum supply        = 5,699,395,010,000,000,000 atomic  (56,993,950,100 display)
```

Because the referral channel left the Founder Node group, that group is now
exactly the base permission's complete schedule:

```text
57,430,000,000 * 100,000 * 731 = 4,198,133,000,000,000,000
```

This identity did not hold in v1 and is checked as a derivation rather than
recorded as a coincidence.

No implicit, unnamed, genesis, burn, bridge, rounding, or remainder channel
exists. Each issued atomic unit is attributed to exactly one of these channel
IDs forever.

## Seat and cycle arithmetic

Seat identifiers are unsigned integers from `0` through `99,999`. A human may
control at most 1,000 seats. The ownership and enrollment model that proves
that bound is outside this specification.

Each activated seat has exactly 731 issuance cycle indexes from `0` through
`730`. This zero-based index remains the replay key. A future protocol must
derive it from an accepted height or epoch schedule; local time and a supplied
calendar timestamp are invalid sources. This document does not choose a block
count per 24-hour-target cycle.

The complete seat-cycle population is `100,000 * 731 = 73,100,000`. Every full
schedule below is one per-cycle amount multiplied by that population.

### Base permission

One evaluated seat cycle creates one base permission with the following atomic
legs. The referral is no longer among them.

| Channel | Beneficiary kind | Atomic amount |
| --- | --- | ---: |
| `venture_escrow` | typed venture escrow | 17,100,000,000 |
| `community_grants_escrow` | typed community-grants escrow | 3,420,000,000 |
| `developer_incentives_escrow` | typed developer-incentives escrow | 1,710,000,000 |
| `system_creator_issuance_royalty` | System Creator Company | 1,000,000,000 |
| `founder_operator` | cycle founder or derived performance winners | 34,200,000,000 |
| **Total** | | **57,430,000,000** |

For the complete seat capacity and cycle schedule, checked multiplication
reproduces every base channel cap:

```text
34,200,000,000 * 73,100,000 = 2,500,020,000,000,000,000
17,100,000,000 * 73,100,000 = 1,250,010,000,000,000,000
 3,420,000,000 * 73,100,000 =   250,002,000,000,000,000
 1,710,000,000 * 73,100,000 =   125,001,000,000,000,000
 1,000,000,000 * 73,100,000 =    73,100,000,000,000,000
```

For one seat across all 731 cycles, the same checked products are:

```text
Founder operator                    = 25,000,200,000,000 atomic
venture escrow                      = 12,500,100,000,000 atomic
community-grants escrow             =  2,500,020,000,000 atomic
developer-incentives escrow         =  1,250,010,000,000 atomic
System Creator issuance royalty     =    731,000,000,000 atomic
base permission total               = 41,981,330,000,000 atomic
```

The `founder_operator` beneficiary is the evaluated seat when that seat met the
cycle, and otherwise the derived performance winner set for that same cycle.
The winner computation, the uptime record it reads, and the cycle boundary are
specified with the revised simulator, not here. This contract fixes only that
the leg is 34,200,000,000 atomic units and that its beneficiary is one of those
two, never a third.

### Referral benefit

The referral is a direct-mint accrual of 3,420,000,000 atomic units for each of
the referred seat's 731 cycles. It is unconditional: it does not depend on
whether the referred seat met the cycle, is not part of the base permission,
and does not settle through the referred seat's cycle evaluation.

`referral_benefit` has exactly these fields:

| Field | Fixed value |
| --- | --- |
| `channel` | `founder_referral` |
| `amount_atomic` | `3420000000` |
| `unconditional` | `true` |
| `referred_beneficiary_kind` | `recorded_referrer` |
| `unreferred_beneficiary_kind` | `unreferred_performance_pool` |

Every seat-cycle contributes its 3,420,000,000 atomic units to exactly one of
the two destinations: the recorded referrer when the seat has one, and the
unreferred performance pool when it does not. The channel is therefore consumed
exactly at full capacity, with no remainder:

```text
3,420,000,000 * 100,000 * 731 = 250,002,000,000,000,000
```

The benefit is exactly one tenth of the 34,200,000,000-atomic operator leg, and
exactly twice the superseded v1 amount.

The cap is a bound, not a prediction. It is reached only when all 100,000 seats
are sold and every seat completes its full 731-cycle window. Fewer sold seats or
incomplete windows issue less; nothing reallocates the difference.

This contract does not define when a referral accrual begins for a purchased but
never activated seat, whether a referrer must itself hold a Founder Seat, the
definition of a month for the unreferred pool, that pool's tie and remainder
rules, or the storage bound on accrued referral balances. Each is named as
remaining work in ADR 0023 and belongs to the revised simulator specification.

## Abstract accounting state

The revised simulator must expose state equivalent to:

```text
channels[channel_id] = {
  issued_atomic:u64,
  outstanding_atomic:u64
}

pending_permissions[(seat_id, cycle_index)] = ordered legs
evaluated_permission_keys = set<(seat_id, cycle_index)>
referral_accrual_keys = set<(referred_seat_id, cycle_index)>
accepted_direct_decision_ids = set<bounded identifier>
typed_custody[(beneficiary_kind, beneficiary_id)] = u64
```

There is no permission `kind` discriminator, because the referral is no longer
a permission. An implementation may use a more compact aggregate representation
only if it preserves the exact per-seat, per-cycle replay decision, every
beneficiary liability, and identical observable results. It may not iterate over
all 100,000 seats inside an unrelated transition.

The abstract resource ceiling is 73,100,000 base evaluation keys and at most
73,100,000 referral accrual keys. A production encoding and bounded settlement
mechanism remain M3 work. The derived performance winner set replaces v1's
supplied allocation list, so its bound is now a consequence of the winner rule
rather than an open question; the rule itself is still unspecified.

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

Outstanding permission units are liabilities against channel capacity. They are
not issued supply, circulating supply, an account balance, or spendable escrow
custody.

## Research inputs and derived inputs

Version one carried four research placeholders. Version two carries one.

| v1 placeholder | v2 disposition |
| --- | --- |
| `activity_eligibility_result` | Derived from the cycle uptime record |
| `inactive_performance_allocation_result` | Derived from the same-cycle winner set |
| `inactive_referral_eligibility_result` | Removed; the referral is unconditional |
| `direct_channel_eligibility_result` | Retained |

`research_placeholders` is therefore the single-entry array
`["direct_channel_eligibility_result"]`. It applies to the four direct-mint
channels whose eligibility the owner has not yet decided: `liquidity_mining`,
`impermanent_loss_protection`, `hub_verified_user_incentives`, and
`initial_mystery_box_incentives`. It does not apply to `founder_referral`,
whose eligibility is the recorded referrer relationship the ledger already
holds.

The two derived inputs are not production consensus inputs yet. Removing a
placeholder records that a supplied fixture is no longer the intended source; it
does not by itself supply the computation. The uptime record, its challenge
construction and sampling rate, the AI dispute window, and the cycle boundary in
heights or epochs are all unspecified, and no part of this contract may be read
as evidence that they are sound.

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

The order is normative and is proved by executing manifests that carry two
defects at once: each such manifest must report the earlier stage.

Stages 7 and 8 are reachable through the loader only for a manifest that
already matches the fixed contract table, which by construction is
arithmetically correct. They are implemented as a separate derivation module so
they can be exercised directly, which is what proves that a self-consistent but
arithmetically wrong manifest is still rejected rather than accepted by a table
comparison alone.

The revised simulator must preserve the following ordinary semantic failures and
their no-write behavior, though its serialized event schema and numeric codes
remain a separate acceptance step:

| Error | Meaning |
| --- | --- |
| `CYCLE_RANGE` | Seat or cycle index is outside the manifest bounds |
| `REPLAY` | Permission key, referral accrual key, or direct decision was already accepted |
| `MISSING_RESEARCH_INPUT` | A required explicit placeholder result is absent |
| `INVALID_RESEARCH_INPUT` | A placeholder is not bound to the exact attempted action |
| `CHANNEL_CAP` | Issued plus outstanding plus requested value exceeds one channel cap |
| `PERMISSION_NOT_FOUND` | Exercise names no pending permission |
| `ARITHMETIC_OVERFLOW` | Any checked intermediate exceeds `u64` |
| `INVARIANT` | A pre-state or proposed journal violates conservation |

`INVALID_PERFORMANCE_ALLOCATION` is not carried forward. It validated a supplied
allocation list, and there is no longer one to validate; the winner set is
computed, so its failures belong to the uptime and winner rules.

## Receipts, commitments, and M1 effects

This specification assigns no canonical transaction bytes, receipt bytes,
state-root schema, or block result. The revised simulator specification must
define deterministic input, trace, and final-state digests around these exact
values. M3 must separately define consensus receipts and commitments before a
C++ transition exists.

Loading or modeling this manifest has no effect on an M1 account, fee pool,
height, transaction root, receipt, state root, SQLite database, ABCI response,
or CometBFT validator. The existing M1 nine-decimal supply remains conserved.

## Versioning and compatibility

The schema string, field set, array order, identifiers, values, JCS rules,
domain label, and digest are immutable for version two. A changed amount,
precision, field, placeholder, or semantic rule requires a new manifest schema
and ADR; it must not reinterpret this digest.

Version one and version two coexist. The v1 artifacts are the accepted M2
evidence and remain in place, passing, and unedited. Neither loader accepts the
other's manifest, and the two domain labels differ, so no digest computed under
one version can be replayed as the other.

The eight-decimal Founder target is not an in-place reinterpretation of M1
nine-decimal atomic balances. A future implementation must choose a new genesis
or explicit versioned migration and activation rule. It must provide fixed
old/new state vectors, replay behavior across the boundary, rollback handling,
C++/Python agreement, and independent review.

The Founder Constitution calls the revised maximum permanent from genesis. It is
revisable now only because no native unit has been issued, no holder exists, and
no C++ consensus enforces a supply figure. This specification does not create a
precedent for a later revision, and no such revision is available after genesis.

The remaining research placeholder cannot become a production consensus input by
renaming a fixture. It requires a canonical result envelope, authorization,
resource bound, failure policy, and the founder decision that is still reserved.

## Required vectors and evidence

[`founder-economy-manifest-v2.txt`](../../test-vectors/founder-economy-manifest-v2.txt)
is normative. It fixes:

- the denomination fit, `u64` headroom, and nine-decimal overflow boundary;
- canonical manifest byte length and digest, and the superseded v1 identity;
- every channel cap, subtotal, and total in atomic and display units;
- every per-cycle leg, per-seat product, and complete 100,000-seat product;
- the referral channel's exact consumption with a recorded zero remainder;
- the supply revision accounted to the referral channel alone, with a recorded
  zero unexplained increase and zero change across the other nine channels;
- the single remaining research placeholder and the four channels it covers; and
- every ordered acceptance failure, each produced by a live loader run over a
  minimally mutated manifest, plus the stage-ordering pairs.

`tools/founder-economy-v2-vectors/verify.py` derives every recorded value and
fails closed when a recorded key is never derived, when a derived key is absent
from the file, or when any recorded value is tampered with. Its independence is
`expected.py`, which imports nothing from `simulation/` and restates the Founder
Constitution's two allocation tables by hand. Because the constitution states
the economy both as per-cycle amounts and as channel totals without deriving
either from the other, requiring them to agree checks the manifest against the
constitution rather than against a second reading of this document. A forged
manifest that is self-consistent enough to pass every loader stage is still
rejected by that comparison.

Acceptance requires independent exact-integer reproduction of the vectors, full
GitHub-hosted repository verification on the exact commit, the revised
standard-library Python simulator and adversarial scenarios in the next slice,
and independent economic and protocol review before any production activation
claim.
