# Founder Economy manifest v3

Status: Accepted M3 economic input and liability contract; not a consensus
transition

This document fixes the integer denomination, issuance-channel manifest, exact
supply derivation, and permission-liability semantics of the economy after the
2026-08-19 founder pivot renames one issuance channel. It is normative for the
M3 manifest and fixed vectors only. It changes no M1 bytes, C++ state,
configured devnet supply, accepted simulator schema, or state root.

The change is classified as economics, input encoding, and future
compatibility.
[ADR 0053](../decisions/0053-founder-economy-manifest-v3-the-channel-rename.md)
records the alternatives and decision, and
[ADR 0049](../decisions/0049-the-recovery-pool-and-permanent-best-performer-ranking.md)
records the founder direction it implements.

## Relationship to version two

[`founder-economy-manifest-v2.md`](founder-economy-manifest-v2.md) is not
edited, retracted, or reinterpreted. It states the contract the accepted M3.1
through M3.10 models implement and that evidence proves. Version three is a
separate accepted contract with its own schema string, domain label, canonical
bytes, and digest.

**Exactly one thing changed, and it is an identifier:**

| | v2 | v3 |
| --- | --- | --- |
| Channel 9 identifier | `initial_mystery_box_incentives` | `mini_gamified_incentives` |

Every cap, every issuance kind, the channel order, the denomination, the seat
schedule, the base permission and all five of its legs, the referral benefit and
both of its destinations, the two subtotals, the maximum supply, and the single
research placeholder are unchanged.

The vectors prove this rather than asserting it. Version three's contract table
is *derived* from version two's by applying the one rename, so a moved cap
cannot be expressed; the verifier then accounts for the difference between the
two accepted manifests in both directions, and its expectations are converted by
hand from the Founder Constitution rather than read from either model.

## Why a version rather than an edit

A channel identifier is a string inside the manifest JSON. The manifest digest
is a hash over that JSON. The digest is a genesis field. The chain ID is a hash
of genesis. So the rename moves the manifest digest, then genesis bytes, then
the chain ID, then every recorded vector that embeds any of them.

Version two additionally fixes its schema string, identifiers, values, domain
label, and digest as immutable and requires a new schema and ADR for any change
to them. Renaming in place would silently reinterpret an accepted digest, which
is the one thing that clause exists to prevent.

## Scope

Version three defines exactly one canonical input object:
[`founder-economy-manifest-v3.json`](../../test-vectors/founder-economy-manifest-v3.json).
It carries the same abstract state reads and writes version two defines.

It does **not** define the recovery pool, the contributing and eligible winner
sets, the permanence of best-performer ranking, the deletion of entry kind 7, or
the calendar month. Those are settlement and state-transition rules, and the
manifest holds neither. They belong to the settlement respecification and to
`economy-transition-v7`, which are separate slices.

The model remains one native asset. Every amount in this document is a count of
that asset's atomic unit; a channel or typed custody bucket is not a second
asset.

## Integer denomination

Unchanged from version two, and restated here because a contract that forwards
its own denomination to another document is not self-contained.

| Property | Exact value |
| --- | ---: |
| Display decimal places | 8 |
| Atomic units per display unit | 100,000,000 |
| Maximum display units | 56,993,950,100 |
| Maximum atomic units | 5,699,395,010,000,000,000 |
| `u64` maximum | 18,446,744,073,709,551,615 |
| `u64` headroom above the maximum | 12,747,349,063,709,551,615 |

All monetary state uses unsigned `u64` atomic integers with checked addition,
subtraction, and multiplication. Consensus and accounting never parse a decimal
display value. Nine decimal places would require 56,993,950,100,000,000,000
atomic units and is an overflow, not an alternative encoding of the same amount.

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

`schema` is exactly `protocol-stack/founder-economy-manifest/v3`.
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
    D("protocol-stack:founder-economy:manifest-v3") ||
    jcs_manifest_bytes
  )
```

The label is 42 ASCII bytes, so its `D` prefix begins with `0x2a`. The accepted
canonical JSON is 2,261 bytes and its digest is:

```text
af153c99adf7c49e5a92563946cf0e60dfd7a58785462530988f661aa68faaa7
```

The checked-in pretty-print whitespace is not part of the digest, and neither
is the source field order. A parser must validate the schema and fixed values
before treating the digest as an accepted manifest identity.

**The canonical length is 6 bytes shorter than version two's 2,267, and that is
a checked identity rather than an observation.** The retired identifier is 30
bytes and the current one is 24, and the two schema strings and the two domain
labels are each the same length as their counterpart. So the entire change in
canonical bytes is the identifier's own change in length, and a manifest that
also gained or lost a byte anywhere else fails that check.

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
| 9 | `mini_gamified_incentives` | `direct_mint` | 1,250,010,000,000,000 |

Checked addition must reproduce:

```text
Founder Node subtotal = 4,198,133,000,000,000,000 atomic  (41,981,330,000 display)
direct-mint subtotal  = 1,501,262,010,000,000,000 atomic  (15,012,620,100 display)
maximum supply        = 5,699,395,010,000,000,000 atomic  (56,993,950,100 display)
```

The Founder Node group is exactly the base permission's complete schedule:

```text
57,430,000,000 * 100,000 * 731 = 4,198,133,000,000,000,000
```

No implicit, unnamed, genesis, burn, bridge, rounding, remainder, carry, or
recovery-pool channel exists. Each issued atomic unit is attributed to exactly
one of these channel IDs forever.

### The renamed channel

Channel 9's identifier is `mini_gamified_incentives`. The Founder Constitution
names it "Initial mini-gamified incentives" in the direct-mint allocation table;
the identifier drops the leading descriptive word the same way "Liquidity
mining" gives `liquidity_mining`.

`initial_mystery_box_incentives` is **retired**. It is not an alias, and a
manifest carrying it is rejected with `MANIFEST_MISMATCH` rather than accepted
as an older spelling. The accepted canonical bytes contain the retired
identifier zero times, which the vectors record.

The rename changes no eligibility. Channel 9 remains one of the four direct-mint
channels the `direct_channel_eligibility_result` placeholder covers, and that
decision is still founder-reserved.

## Seat and cycle arithmetic

Unchanged from version two. Seat identifiers are unsigned integers from `0`
through `99,999`, a human may control at most 1,000 seats, and each activated
seat has exactly 731 issuance cycle indexes from `0` through `730`. The complete
seat-cycle population is `100,000 * 731 = 73,100,000`.

**731 cycles bound the native asset distribution and nothing else.** ADR 0049
fixes that a Founder Machine keeps operating and keeps competing after its own
distribution window closes. That has no effect on this contract, which states
how much a seat's cycles create and not who competes for it, but it is stated
here so a reader does not infer an operating life from an issuance schedule.

### Base permission

One evaluated seat cycle creates one base permission with the following atomic
legs. The referral is not among them.

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
This contract fixes only that the leg is 34,200,000,000 atomic units and that
its beneficiary is one of those two, never a third. **Which seats form that
winner set changed on 2026-08-19** — ADR 0049 separates the contributing set
from the eligible set — and the winner computation is specified with the revised
simulator, not here.

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
the two destinations, so the channel is consumed exactly at full capacity with
no remainder:

```text
3,420,000,000 * 100,000 * 731 = 250,002,000,000,000,000
```

The benefit is exactly one tenth of the 34,200,000,000-atomic operator leg.

The cap is a bound, not a prediction. It is reached only when all 100,000 seats
are sold and every seat completes its full 731-cycle window.

This contract does not define when a referral accrual begins for a purchased but
never activated seat, whether a referrer must itself hold a Founder Seat, the
unreferred pool's payout, tie, and remainder rules, or the storage bound on
accrued referral balances.

## Abstract accounting state

Unchanged from version two:

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

The abstract resource ceiling is 73,100,000 base evaluation keys and at most
73,100,000 referral accrual keys.

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

**This contract states no per-channel carry.** Version two did not either; the
carry lives in `economy-transition-v6`'s state, which ADR 0049 replaces with a
recovery pool. Nothing here needs to change for that, and nothing here supplies
it.

## Research inputs and derived inputs

`research_placeholders` is the single-entry array
`["direct_channel_eligibility_result"]`. It applies to the four direct-mint
channels whose eligibility the owner has not yet decided: `liquidity_mining`,
`impermanent_loss_protection`, `hub_verified_user_incentives`, and
`mini_gamified_incentives`. It does not apply to `founder_referral`, whose
eligibility is the recorded referrer relationship the ledger already holds.

The rename changes which identifier that placeholder names and not how many
channels it covers, which the vectors record as a count derived from the renamed
table rather than as a repeated literal.

The remaining placeholder cannot become a production consensus input by renaming
a fixture. It requires a canonical result envelope, authorization, resource
bound, failure policy, and the founder decision that is still reserved.

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
comparison alone. **The recorded `order.mismatch_before_supply` pair therefore
reports `MANIFEST_MISMATCH` for both of its defects; it records that the table
comparison runs first, and the derivation stage's own rejections are recorded
separately under `negative.derivation.`.**

The revised simulator must preserve version two's ordinary semantic failures and
their no-write behavior.

## Implementation

The ordered loader, its field inventory, and its checked-arithmetic derivation
stage carry no founder-directed value; only the table they compare against is
version-specific. One implementation in
`simulation/founder_economy_manifest/` is therefore bound to each version's
contract table, rather than copied per version, because two copies of one
acceptance order would drift silently — each agreeing with itself.

Version three's contract table in `simulation/founder_economy_manifest_v3/` is
derived from version two's by applying the one rename. Independence comes from
outside the models: the verifier's `expected.py` converts the Founder
Constitution's two allocation tables by hand and imports nothing from
`simulation/`.

## Receipts, commitments, and M1 effects

This specification assigns no canonical transaction bytes, receipt bytes,
state-root schema, or block result. Loading or modeling this manifest has no
effect on an M1 account, fee pool, height, transaction root, receipt, state
root, SQLite database, ABCI response, or CometBFT validator.

## Versioning and compatibility

The schema string, field set, array order, identifiers, values, JCS rules,
domain label, and digest are immutable for version three. A changed amount,
precision, field, placeholder, or semantic rule requires a new manifest schema
and ADR; it must not reinterpret this digest.

Versions one, two, and three coexist. The v1 and v2 artifacts remain in place,
passing, and unedited, and each records what a particular body of accepted
evidence proves. No loader accepts another version's manifest, and the three
domain labels differ, so no digest computed under one version can be replayed as
another.

Because versions two and three have identical field shapes, the schema string is
what separates them at the loader. A version-two manifest relabelled with
version three's schema string is still rejected, at `MANIFEST_MISMATCH`, by the
retired channel identifier — which the tests exercise directly.

The eight-decimal Founder target is not an in-place reinterpretation of M1
nine-decimal atomic balances. A future implementation must choose a new genesis
or explicit versioned migration and activation rule.

The Founder Constitution calls the maximum permanent from genesis. It is
revisable now only because no native unit has been issued, no holder exists, and
no C++ consensus enforces a supply figure. Version three does not revise it.

## Required vectors and evidence

[`founder-economy-manifest-v3.txt`](../../test-vectors/founder-economy-manifest-v3.txt)
is normative. It fixes:

- the denomination fit, `u64` headroom, and nine-decimal overflow boundary;
- canonical manifest byte length and digest, and the superseded v2 identity;
- every channel cap, subtotal, and total in atomic and display units;
- every per-cycle leg, per-seat product, and complete 100,000-seat product;
- the referral channel's exact consumption with a recorded zero remainder;
- the rename accounted for in both directions — exactly one changed identifier,
  zero changed caps, kinds, legs, and totals, zero occurrences of the retired
  identifier in the accepted bytes, and a canonical-length change equal to the
  identifier's own length change;
- that neither the v1, v2, nor v3 loader accepts another version's manifest;
- the single remaining research placeholder and the four channels it covers; and
- every ordered acceptance failure, each produced by a live loader run over a
  minimally mutated manifest, plus the stage-ordering pairs.

Every superseded figure the file records is read from the retained v2 contract
table and required to agree with this document's account of it, so the claim
that version two is unchanged is checked rather than asserted.

`tools/founder-economy-manifest-v3-vectors/verify.py` derives every recorded
value and fails closed when a recorded key is never derived, when a derived key
is absent from the file, or when any recorded value is tampered with. Its
independence is `expected.py`, which imports nothing from `simulation/` and
restates the Founder Constitution's two allocation tables by hand. Because the
constitution states the economy both as per-cycle amounts and as channel totals
without deriving either from the other, requiring them to agree checks the
manifest against the constitution rather than against a second reading of this
document.

**Seven mutation probes establish that the checks fail closed**, and they are
recorded in ADR 0053 with what each one reached, because three of them were
caught by an earlier stage than the one under test and therefore said nothing
about it.

Acceptance requires independent exact-integer reproduction of the vectors, full
GitHub-hosted repository verification on the exact commit, the settlement
respecification and `economy-transition-v7` in later slices, and independent
economic and protocol review before any production activation claim.
