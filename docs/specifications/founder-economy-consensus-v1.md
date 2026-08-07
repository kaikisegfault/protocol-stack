# Founder Economy consensus v1

Status: Accepted M3 consensus contract; no implementation exists yet

This document is normative for the chain-defined Founder issuance cycle, the
canonical Founder economy state and its commitment, the version-two genesis and
transaction encodings, and the numeric consensus receipt codes that carry the
accepted M2 economy into a deterministic state machine.

It extends [`protocol-primitives-v1.md`](protocol-primitives-v1.md) and
[`ledger-transition-v1.md`](ledger-transition-v1.md); definitions there govern
unless this document imposes a narrower rule. It realizes the accounting fixed
by [`founder-economy-manifest-v1.md`](founder-economy-manifest-v1.md) and
modelled by
[`founder-economy-simulator-v1.md`](founder-economy-simulator-v1.md).

The change is classified as primitive extension, encoding, validation, state
transition, economics, and compatibility. ADR 0023 records the alternatives and
the decision.

## Scope

Two version numbers appear throughout and mean different things. This document
is version one of the Founder economy consensus contract. The bytes it defines
are schema version **two** of the chain encodings, because schema version one is
the accepted M1 genesis, transfer, state root, and receipt, which this document
leaves untouched.

Version one of this contract defines:

- the eligible issuance cycle as a function of block height alone;
- version-two canonical genesis and its immutable chain parameters;
- the canonical Founder economy state records, their commitment, and the
  version-two state root;
- five version-two transaction encodings and their exact reads, writes,
  authorization, replay keys, and resource bounds;
- the version-two receipt and the complete numeric result-code space; and
- the compatibility boundary against accepted M1 bytes and frozen M2 schemas.

It does not define commercial or transaction-fee distribution, escrow payout
capabilities, the claim path from typed custody to a spendable account, seat
purchase or its join to activation, biometric enrollment, manager records,
legacy succession, the AI decision receipt and audit trail, or persistence and
crash-consistency. Those remain later M3 and M4 slices.

No implementation exists at acceptance. The C++20 kernel, the extended
independent Python model, and the normative cross-language vector file follow
this specification in a later slice.

The model remains one native asset. Every amount is a count of that asset's
atomic unit. A channel, escrow, or typed custody bucket is an accounting
partition, not a second asset.

## The eligible cycle

The Founder Constitution states that each seat receives 731 eligible
24-hour-target cycles beginning with that seat's first activation, that seats
activated on different dates have different windows, and that local wall clocks
cannot decide consensus.

Version two therefore derives every cycle from block height alone. `epoch_blocks`
is an immutable genesis parameter in the range 1 through 4,294,967,295.

```text
epoch_index(h) = h / epoch_blocks          integer division, h is block height

activation_epoch(seat) = epoch_index(h_a)  h_a is the height of the block that
                                           executed the seat's activation

cycle k of a seat occupies epoch  activation_epoch + 1 + k,  for k in 0..730

cycle k is closed at height h  iff  epoch_index(h) > activation_epoch + 1 + k
```

A seat's window is the 731 epochs from `activation_epoch + 1` through
`activation_epoch + 731`. A cycle becomes evaluable only after its epoch has
fully elapsed, so no evaluation ever depends on a partially observed epoch.

Cycle zero begins at the next epoch boundary rather than at the activation
height. If it began at the activation height, the first cycle's length would
depend on where inside an epoch the seat happened to activate, and two seats
with the same window length would measure different numbers of blocks. Starting
at the boundary makes all 731 cycles exactly `epoch_blocks` blocks long for
every seat, while preserving the constitutional rule that seats activated at
different times have different windows.

At activation, `activation_epoch + 732` must fit `u64`; otherwise the activation
fails with `WINDOW_OVERFLOW`. The condition is unreachable at any attainable
height and is checked so that the guard is proved present rather than assumed.

### What the block-count rule does and does not guarantee

The protocol counts blocks. The 24-hour figure in the Founder Constitution is a
target realized by choosing `epoch_blocks` against the accepted block interval;
it is not a guarantee. A halt, a slow period, or a change in the practical block
interval lengthens or shortens the wall-clock duration of a cycle, and no
consensus rule detects that. The constitution's own wording — a
"24-hour-target" cycle — is satisfied by targeting, and this specification
claims nothing stronger.

The M3 devnet configuration uses `epoch_blocks = 20`, roughly one minute at the
pinned `timeout_commit = "3s"`, chosen so that a complete 731-cycle window is
reachable inside a bounded integration run. A 24-hour target at that same
interval would be 28,800. Neither number is a protocol constant; both are
genesis configuration.

## Version-two genesis

The version-two canonical genesis bytes are exactly 157 octets:

| Offset | Size | Field | Required value or range |
| ---: | ---: | --- | --- |
| 0 | 4 | magic | ASCII `PSGN` |
| 4 | 2 | schema version | `2` |
| 6 | 4 | network ID | configured, nonzero |
| 10 | 8 | supply limit | exactly 5,574,394,010,000,000,000 |
| 18 | 8 | total supply | exactly `0` |
| 26 | 8 | fixed transfer fee | configured, nonzero |
| 34 | 8 | initial fee pool | exactly `0` |
| 42 | 8 | epoch blocks | 1 through 4,294,967,295 |
| 50 | 1 | max performance recipients | 1 through 64 |
| 51 | 2 | seat registrar policy ID | nonzero |
| 53 | 32 | seat registrar public key | canonical Ed25519 key |
| 85 | 2 | activity policy ID | nonzero |
| 87 | 32 | activity attester public key | canonical Ed25519 key |
| 119 | 2 | direct eligibility policy ID | nonzero |
| 121 | 32 | direct eligibility public key | canonical Ed25519 key |
| 153 | 4 | account count | exactly `0` |

Total supply, the initial fee pool, and the account count are fixed at zero
because the Founder Constitution states that there is no founder-directed
genesis allocation and that native units enter circulation only through Founder
Node issuance permissions and capped direct-mint channels. Version two makes
that rule a decoder check rather than a promise.

The three public keys must be distinct. A single key holding more than one
evidence authority would violate the charter requirement that one logical
authority never receives a combined capability.

The chain identifier derivation is unchanged:

```text
chain_id = H(D("protocol-stack:v1:chain-id") || canonical_genesis_bytes)
```

Because the genesis bytes differ, a version-two chain has a different chain
identifier than any version-one chain. It is a new chain, not a migration of the
M1 devnet. The initial state has height zero, an empty accounts tree, an empty
economy tree, and its state root uses the version-two construction below.

The configured address HRP remains a chain parameter. Version-one transfers
remain valid on a version-two chain, so text addresses are unchanged.

## Canonical economy state

A valid version-two ledger state consists of the version-one state — chain
identifier, supply limit, total supply, fixed transfer fee, height, fee pool,
and the ordered account map — extended with the immutable version-two chain
parameters and an ordered map of Founder economy records.

An economy record is a `record_type` tag, a fixed-width key, and a value. The
canonical leaf is:

```text
economy_leaf = record_type:u8 || key_bytes || value_bytes
```

Records are sorted by the unsigned lexicographic order of
`record_type || key_bytes` and must not contain duplicates. Because every key is
fixed width within its record type, this order is total and unambiguous.

| Tag | Record | Key | Value |
| ---: | --- | --- | --- |
| 1 | seat | `seat_id:u32` | 21 bytes, below |
| 2 | channel | `channel_index:u8` | `issued:u64 \|\| outstanding:u64` |
| 3 | reallocation | `seat_id:u32 \|\| cycle_index:u16` | `count:u8` then `count` entries |
| 4 | typed custody | `custody_kind:u8 \|\| custody_ref:bytes<32>` | `amount:u64` |
| 5 | direct sequence | `channel_index:u8` | `next_sequence:u64` |
| 6 | referral skip | `seat_id:u32 \|\| cycle_index:u16` | none |

The seat value is exactly 21 octets:

```text
activation_epoch:u64 || referrer_present:bool || referrer_seat_id:u32 ||
base_evaluated_next:u16 || base_exercised_next:u16 ||
referral_evaluated_next:u16 || referral_exercised_next:u16
```

`referrer_seat_id` must be zero when `referrer_present` is `0x00`. Every
watermark is in the range 0 through 731, and for each kind the exercised
watermark is at most the evaluated watermark.

A reallocation entry is `recipient_seat_id:u32 || amount:u64`, 12 octets, and
`count` is in the range 1 through `max_performance_recipients`.

`channel_index` is the manifest index, 0 through 9. A channel record exists for
all ten channels in every state, including those still at zero, so that channel
accounting is never implicit. Channel caps are fixed constants from the accepted
manifest and are never stored.

Custody kinds are:

| Kind | Meaning | `custody_ref` |
| ---: | --- | --- |
| 1 | venture escrow | 32 zero octets |
| 2 | community-grants escrow | 32 zero octets |
| 3 | developer-incentives escrow | 32 zero octets |
| 4 | System Creator Company | 32 zero octets |
| 5 | Founder seat | 28 zero octets then `seat_id:u32` |

A custody entry is absent rather than zero. Direct-mint beneficiaries are
ordinary accounts and never appear in typed custody; see the compatibility
section for why this narrows the M2 model.

### Pending permissions are watermarks, not records

For each seat and each permission kind, the cycles in
`[exercised_next, evaluated_next)` are exactly the pending permissions. The four
non-Founder base legs and the referral leg are fixed constants, so a pending
permission carries no information beyond its cycle index except in two cases:

- a base cycle evaluated inactive carries a reallocation record naming the
  recipients of its 34,200,000,000-atomic Founder leg; and
- a referral cycle evaluated inactive whose supplied policy result declined to
  create the permission carries a referral-skip record.

Both evaluation and exercise are therefore required to proceed in cycle order.
Four `u16` watermarks per seat replace what the M2 model represents as up to
1,462 evaluated keys and 1,462 pending permissions per seat. In the common case
where every cycle is active and every permission is exercised, the entire
accumulation history of a seat costs 8 octets of state.

Requiring cycle order costs nothing the constitution grants. Permissions may
still be exercised immediately or accumulated for the whole window; only the
order of settlement is fixed. Evidence that arrives out of order is rejected
with a distinct code and succeeds on resubmission after the preceding cycle
settles.

### Base permission legs

A base permission's legs are fixed by the accepted manifest:

| Channel index | Channel | Atomic amount | Custody destination |
| ---: | --- | ---: | --- |
| 0 | `founder_operator` | 34,200,000,000 | custody kind 5, for the evaluated seat or the reallocation recipients |
| 1 | `venture_escrow` | 17,100,000,000 | custody kind 1 |
| 2 | `community_grants_escrow` | 3,420,000,000 | custody kind 2 |
| 3 | `developer_incentives_escrow` | 1,710,000,000 | custody kind 3 |
| 5 | `system_creator_issuance_royalty` | 1,000,000,000 | custody kind 4 |

Checked addition reproduces the 57,430,000,000-atomic total, which is 574.3
display units at eight decimals. A referral permission has the single leg of
1,710,000,000 atomic units on channel index 4, credited to custody kind 5 for
the recorded referrer.

The Founder beneficiary is resolved at evaluation and stored, never at exercise.
That is what makes an inactive cycle's reallocation permanent: no later
transition can restore the original seat.

### Commitment and state root

The economy tree uses the accepted RFC 9162 shape:

```text
economy_tree({})      = H(D("protocol-stack:v2:economy-empty"))
economy_tree({e})     = H(D("protocol-stack:v2:economy-leaf") || e)
economy_tree(L || R)  = H(D("protocol-stack:v2:economy-node") || L_root || R_root)
```

The accounts tree, its three version-one labels, and the 48-octet account entry
layout are reused verbatim. The version-two state root is:

```text
H(
  D("protocol-stack:v2:state-root") ||
  u16(2) ||
  chain_id ||
  height:u64 ||
  supply_limit:u64 ||
  total_supply:u64 ||
  fee_pool_balance:u64 ||
  account_count:u64 ||
  accounts_tree_root ||
  economy_record_count:u64 ||
  economy_tree_root
)
```

Immutable chain parameters are already committed through the chain identifier
and are not repeated in the root preimage.

### Invariants

Before computing a state root, the caller must establish:

```text
total_supply = checked_sum(channel.issued)

checked_sum(account balances) + fee_pool + checked_sum(typed_custody)
  = total_supply

for each channel:  issued + outstanding <= cap

checked_sum(channel.issued) + checked_sum(channel.outstanding) <= supply_limit

supply_limit = 5,574,394,010,000,000,000
```

together with the version-one requirements that account IDs are strictly
increasing, every value fits `u64`, and height never decreases.

Outstanding permission units are liabilities against channel capacity. They are
not issued supply, circulating supply, an account balance, or spendable escrow
custody.

Version one of the ledger transition required total supply and the fixed fee
never to change. Version two replaces the first of those: total supply rises
with every exercise and every accepted direct issuance, bounded by the channel
caps whose checked sum is exactly the supply limit. The fixed fee remains
immutable. There is still no burn, no confiscation, and no public
asset-creation operation.

## Evidence attestations

Three of the five transitions carry a decision that consensus cannot compute:
whether a seat is entitled to activate, whether a seat was active in a cycle and
who should receive a reallocated Founder leg, and whether a direct-channel
beneficiary is eligible. Each is an explicitly deferred founder decision or an
M4 identity obligation.

Version two specifies the carrier, not the policy. An attestation is exactly 106
octets appended to the transaction:

| Offset | Size | Field |
| ---: | ---: | --- |
| 0 | 2 | policy ID |
| 2 | 32 | attester public key |
| 34 | 8 | attestation valid-until height |
| 42 | 64 | attester signature |

The signature covers:

```text
D("protocol-stack:v2:attest") ||
chain_id || u8(transaction_kind) || u16(policy_id) ||
u64(attestation_valid_until) || attested_payload
```

where `attested_payload` is exactly the transaction's kind-specific payload
octets, defined per kind below. Because the attestation signs the payload
itself, there is no separate subject field and no subject-mismatch failure: an
attestation either authorizes these exact bytes on this exact chain for this
exact kind, or it does not verify.

Consensus requires the policy ID and the attester public key to equal the pair
configured in genesis for that transaction kind, and requires
`attestation_valid_until >= executing block height`. Nothing else about the
decision is interpreted.

**These authorities are labelled devnet stand-ins.** A configured attester can
declare any seat active or inactive, name any activated seat as a performance
recipient, admit any seat, and approve any direct-channel beneficiary. That is
the full extent of what the unresolved policies would decide, held by a key
instead of by a rule. No production or public network may configure them, and
this specification does not propose them as production authorities. The Founder
Constitution permits deterministic stand-ins on a testnet provided they are
labelled as stand-ins; this is that label.

What consensus does contain, regardless of the attester, is stated positively:

- an attester cannot change any leg amount, the 57,430,000,000-atomic base
  total, a channel cap, or the supply limit;
- an attester cannot create a permission for a cycle that has not elapsed, for
  a cycle out of order, or for a seat outside its 731-cycle window;
- an attester cannot name a recipient that is not an activated seat, repeat a
  recipient, or produce allocations whose checked sum is not exactly the Founder
  leg;
- an attester cannot exceed a direct-channel cap or reuse a channel sequence;
  and
- an attester cannot spend typed custody, because no version-two transition
  spends it.

The activity attester holds both the activity result and the performance
allocation because the Founder Constitution treats them as one unresolved policy
area. Splitting them across two keys later is a compatible change to the genesis
schema.

## Version-two transactions

Every version-two transaction begins with the same 39-octet prefix:

| Offset | Size | Field | Required value |
| ---: | ---: | --- | --- |
| 0 | 4 | magic | ASCII `PSTX` |
| 4 | 2 | schema version | `2` |
| 6 | 1 | transaction kind | 2 through 6 |
| 7 | 32 | chain ID | configured chain |

Kind `1` remains the unchanged 200-octet version-one transfer and is valid on a
version-two chain exactly as specified in `ledger-transition-v1.md`. Kinds `0`
and 7 through 255 are invalid.

Transactions that carry their own signature use:

```text
signing message = D("protocol-stack:v2:tx-sign") || unsigned_transaction
transaction_id  = H(D("protocol-stack:v2:tx-id") || signed_transaction)
```

Version-one transfers keep their version-one labels and therefore their exact
transaction identifiers. Both derivations produce 32-octet identifiers that
enter the same ordered transaction tree.

### Kind 2 — seat activation

Exactly 154 octets. The attested payload is offsets 39 through 47.

| Offset | Size | Field |
| ---: | ---: | --- |
| 39 | 4 | seat ID |
| 43 | 1 | referrer present |
| 44 | 4 | referrer seat ID |
| 48 | 106 | seat registrar attestation |

`referrer_seat_id` must be zero when `referrer_present` is `0x00`; a nonzero
value there is `MALFORMED_TRANSACTION`.

Checks apply in this order and return the first failure:

| Order | Result | Condition |
| ---: | --- | --- |
| 1 | `ATTESTATION_UNAUTHORIZED` | policy ID or attester key is not the configured seat registrar pair |
| 2 | `ATTESTATION_EXPIRED` | attestation valid-until is below the executing height |
| 3 | `SEAT_RANGE` | seat ID above 99,999 |
| 4 | `INVALID_REFERRER` | referrer present and its ID is above 99,999 or equals the seat ID |
| 5 | `SEAT_ALREADY_ACTIVATED` | a seat record already exists |
| 6 | `REFERRER_NOT_ACTIVATED` | referrer present and not itself activated |
| 7 | `WINDOW_OVERFLOW` | `activation_epoch + 732` does not fit `u64` |

Reads the chain parameters and the seat records. Writes one seat record with
`activation_epoch = epoch_index(current height)` and all four watermarks at
zero. Activation issues nothing and reserves nothing.

This transition models the seat graph and its issuance window only. Seat
purchase and its proceeds, biometric enrollment, manager records, the
1,000-seats-per-person bound, and the join from the accepted
`founder-seat-schedule-v1` sale to activation are M4 obligations and are
deliberately not modelled here. The registrar attestation is the stand-in for
all of them.

### Kind 3 — base permission evaluation

Variable length, `47 + 12 * count + 106` octets, from 153 to 921. The attested
payload is offsets 39 through `47 + 12 * count`.

| Offset | Size | Field |
| ---: | ---: | --- |
| 39 | 4 | seat ID |
| 43 | 2 | cycle index |
| 45 | 1 | active |
| 46 | 1 | allocation count |
| 47 | 12 × count | allocation entries |
| … | 106 | activity attestation |

An allocation entry is `recipient_seat_id:u32 || amount:u64`. When `active` is
`0x01` the allocation count must be zero. When `active` is `0x00` the count must
be 1 through `max_performance_recipients`.

Checks apply in this order and return the first failure:

| Order | Result | Condition |
| ---: | --- | --- |
| 1 | `ATTESTATION_UNAUTHORIZED` | policy ID or attester key is not the configured activity pair |
| 2 | `ATTESTATION_EXPIRED` | attestation valid-until is below the executing height |
| 3 | `SEAT_RANGE` | seat ID above 99,999 |
| 4 | `CYCLE_RANGE` | cycle index above 730 |
| 5 | `SEAT_NOT_ACTIVATED` | no seat record exists |
| 6 | `CYCLE_NOT_NEXT` | cycle index is not `base_evaluated_next` |
| 7 | `CYCLE_NOT_ELAPSED` | `epoch_index(height)` is not above `activation_epoch + 1 + cycle_index` |
| 8 | `ALLOCATION_COUNT_RANGE` | count is nonzero while active, or zero or above `max_performance_recipients` while inactive |
| 9 | `INVALID_ALLOCATION_RECIPIENT` | a recipient is above 99,999, equals the source seat, repeats, or is not activated |
| 10 | `ALLOCATION_SUM_MISMATCH` | any allocation amount is zero, or the checked sum is not exactly 34,200,000,000 |

Creates the pending base permission for `(seat_id, cycle_index)` by advancing
`base_evaluated_next`, writing a reallocation record when the cycle is inactive,
and increasing the outstanding amount of channels 0, 1, 2, 3, and 5 by their
fixed legs. No beneficiary receives issued custody.

The inactive path retains the complete 574.3-unit permission: the four
non-Founder legs keep their fixed beneficiaries and amounts, and only the
34,200,000,000-atomic Founder leg changes beneficiary. The original inactive
seat cannot recover that benefit later, because the beneficiary is stored at
evaluation.

Consensus verifies that every recipient is an activated seat, that recipients
are distinct, that the source seat is not among them, that every amount is
nonzero, and that the checked sum is exactly 34,200,000,000. It does not verify
that a recipient was active in that same cycle. That stronger check requires the
unresolved performance policy and is exactly what the activity attestation
stands in for; the M2 model recorded the same boundary and this specification
does not close it.

Evaluation is permissionless: the transaction carries no submitter signature and
charges no fee. An inactive seat cannot submit its own evaluation, so making the
transition depend on the seat's participation would strand the reallocated
Founder leg of every offline seat. Anyone holding a valid attestation may relay
it, and the outcome does not depend on who does.

### Kind 4 — referral permission evaluation

Exactly 153 octets. The attested payload is offsets 39 through 47.

| Offset | Size | Field |
| ---: | ---: | --- |
| 39 | 4 | seat ID |
| 43 | 2 | cycle index |
| 45 | 1 | active |
| 46 | 1 | create |
| 47 | 106 | activity attestation |

`create` must be `0x01` when `active` is `0x01`. When `active` is `0x00`,
`create` carries the supplied policy result for an inactive referred cycle.

Checks apply in this order and return the first failure:

| Order | Result | Condition |
| ---: | --- | --- |
| 1 | `ATTESTATION_UNAUTHORIZED` | policy ID or attester key is not the configured activity pair |
| 2 | `ATTESTATION_EXPIRED` | attestation valid-until is below the executing height |
| 3 | `SEAT_RANGE` | seat ID above 99,999 |
| 4 | `CYCLE_RANGE` | cycle index above 730 |
| 5 | `SEAT_NOT_ACTIVATED` | no seat record exists |
| 6 | `SEAT_NOT_REFERRED` | the seat record has no recorded referrer |
| 7 | `CYCLE_NOT_NEXT` | cycle index is not `referral_evaluated_next` |
| 8 | `CYCLE_NOT_ELAPSED` | `epoch_index(height)` is not above `activation_epoch + 1 + cycle_index` |
| 9 | `REFERRAL_DECISION_INVALID` | `active` is `0x01` and `create` is `0x00` |

Advances `referral_evaluated_next`. When `create` is `0x01` it increases the
outstanding amount of channel 4 by 1,710,000,000. When `create` is `0x00` it
writes a referral-skip record and reserves nothing, so a later replay cannot
change the outcome.

Whether an inactive referred cycle creates the referral permission is a
founder-reserved policy. This contract requires the answer to be supplied per
cycle and records it; it does not choose one.

Base and referral evaluation are independent. Failure in the referral path can
never remove, modify, or block an accepted base permission. Like kind 3, this
transition is permissionless and feeless.

### Kind 5 — permission exercise

Exactly 166 octets, signed by an explicit fee payer. The unsigned transaction is
offsets 0 through 102.

| Offset | Size | Field |
| ---: | ---: | --- |
| 39 | 32 | fee payer public key |
| 71 | 8 | nonce |
| 79 | 8 | fee limit |
| 87 | 8 | valid-until height |
| 95 | 4 | seat ID |
| 99 | 2 | cycle index |
| 101 | 1 | permission kind |
| 102 | 64 | fee payer signature |

`permission_kind` is `0` for base or `1` for referral; any other value is
`MALFORMED_TRANSACTION`.

Checks apply in this order and return the first failure. The fee-payer checks
precede the economy checks, and within them the version-one transfer ordering is
preserved:

| Order | Result | Condition |
| ---: | --- | --- |
| 1 | `FEE_LIMIT_TOO_LOW` | fee limit is below the fixed fee |
| 2 | `EXPIRED` | valid-until height is below the executing height |
| 3 | `FEE_PAYER_NOT_FOUND` | fee payer account does not exist |
| 4 | `NONCE_EXHAUSTED` | stored fee payer nonce is `u64` maximum |
| 5 | `NONCE_MISMATCH` | transaction nonce is not stored nonce plus one |
| 6 | `INSUFFICIENT_BALANCE` | fee payer balance is below the fixed fee |
| 7 | `SEAT_RANGE` | seat ID above 99,999 |
| 8 | `CYCLE_RANGE` | cycle index above 730 |
| 9 | `SEAT_NOT_ACTIVATED` | no seat record exists |
| 10 | `CYCLE_NOT_NEXT` | cycle index is not the exercised watermark for the named kind |
| 11 | `PERMISSION_NOT_PENDING` | the exercised watermark equals the evaluated watermark |

`DEBIT_OVERFLOW` cannot arise here because the only debit is the fixed fee.

The Founder Constitution states that every protocol transaction fee is charged
separately and names issuance exercise explicitly, so this transition bears the
fixed transfer fee. The fee is debited from the fee payer and added to the fee
pool exactly as in version one, and the fee payer's nonce advances. Fee-pool
distribution to eligible active Founder Seats is a later M3 slice; until it
exists, the pool accumulates.

On success, in one atomic journal: every affected channel's outstanding amount
decreases, its issued amount increases by the same value, total supply increases
by the same value, every typed beneficiary is credited, the exercised watermark
advances, and any reallocation or referral-skip record for that cycle is
removed. A referral cycle carrying a skip record exercises to an empty journal:
the record is removed and the watermark advances with no value movement, because
the accepted policy result reserved nothing.

Exercise requires no authorization beyond the fee. It has no discretion: the
beneficiaries and amounts were fixed at evaluation, and the result is identical
regardless of who submits it. Requiring the seat's own authorization would let a
seat withhold a Founder leg that an inactive cycle already reallocated to
someone else, and would be authority without a decision to make. If a later rule
makes the timing of exercise valuable — a claim mechanism with time-dependent
effects, for instance — this becomes discretionary and requires a new version.

Partial exercise, per-leg exercise, implicit expiry, burn, sweep, and
beneficiary substitution are not expressible in this encoding and are invalid.

### Kind 6 — capped direct issuance

Exactly 194 octets. The attested payload is offsets 39 through 88.

| Offset | Size | Field |
| ---: | ---: | --- |
| 39 | 1 | channel index |
| 40 | 32 | beneficiary account ID |
| 72 | 8 | amount |
| 80 | 8 | channel sequence |
| 88 | 106 | direct eligibility attestation |

`channel_index` must be 6, 7, 8, or 9 — the four `direct_mint` channels — and
`channel_sequence` must equal that channel's stored `next_sequence`.

Checks apply in this order and return the first failure:

| Order | Result | Condition |
| ---: | --- | --- |
| 1 | `ATTESTATION_UNAUTHORIZED` | policy ID or attester key is not the configured direct eligibility pair |
| 2 | `ATTESTATION_EXPIRED` | attestation valid-until is below the executing height |
| 3 | `INVALID_CHANNEL` | channel index is not 6, 7, 8, or 9 |
| 4 | `ZERO_ISSUANCE_AMOUNT` | amount is zero |
| 5 | `SEQUENCE_MISMATCH` | channel sequence is not the channel's `next_sequence` |
| 6 | `CHANNEL_CAP` | checked `issued + outstanding + amount` exceeds the channel cap |

On success the channel's issued amount, the beneficiary account's balance, and
total supply each increase by `amount`, the beneficiary account is created with
nonce zero if absent, and the channel's `next_sequence` advances by one, all
atomically. Direct issuance creates no permission and never shares the Founder
permission authority.

This is the only transition that credits a spendable balance, and therefore the
only path by which a version-two chain with zero genesis supply acquires the
first units able to pay a fee. It is consequently feeless: no fee payer can
exist before it executes. That is a deliberate deviation from the
constitution's fee sentence, bounded by the attestation, the strict per-channel
sequence, and the channel cap. ADR 0023 records it and the alternative of
deducting the fee from the issued amount, which is a founder-reserved monetary
choice this slice does not make.

Direct-mint beneficiaries are accounts rather than typed custody because the
four direct channels pay users — liquidity providers, verified users, incentive
recipients — who hold ordinary balances, and because nothing in the constitution
requires their proceeds to be held unspendable. The typed custody buckets exist
for the escrows, whose balances must not be spendable through the issuance
capability, for the System Creator royalty, and for Founder seat benefits whose
manager records are an M4 obligation.

## Admission

Admission operates on raw transaction bytes before ledger state is read. Apply
these checks in order:

1. decode exactly one version-one or version-two transaction with no trailing
   bytes, of the exact length its kind and declared counts require;
2. require the configured chain ID;
3. for kind 1 and kind 5, derive the signer account ID and strictly verify the
   Ed25519 signature over the applicable signing message;
4. for kinds 2, 3, 4, and 6, strictly verify the attester Ed25519 signature over
   the attestation preimage.

| Code | Name |
| ---: | --- |
| 1 | `MALFORMED_TRANSACTION` |
| 2 | `WRONG_CHAIN` |
| 3 | `INVALID_SIGNATURE` |
| 4 | `INVALID_ATTESTATION` |

Step 1 classifies a wrong length, magic, schema version, transaction kind,
signature scheme, reserved-field violation, invalid boolean, invalid enum, or an
allocation count above the protocol ceiling of 64 as `MALFORMED_TRANSACTION`.
The ceiling is a decoder bound applied before any allocation array is read; the
narrower genesis `max_performance_recipients` bound and the correlation between
the allocation count and the `active` flag are execution checks that produce
`ALLOCATION_COUNT_RANGE`.

The fixed-width public key and signature fields remain uninterpreted bytes
during shape decoding. At steps 3 and 4, a non-canonical or small-order public
key or `R`, a non-canonical `S`, or a failed signature equation all return the
single applicable code; these cryptographic distinctions are never
malformed-transaction results.

Admission failures perform no state read or write, produce no receipt, and do
not enter the application transaction root. This preserves the version-one rule
exactly.

## Execution and result codes

An admitted transaction executes against the current tentative block state. Each
kind applies its checks in the order listed in its section and returns the first
failure. Every non-success result performs no state write and charges no fee, and
still produces a receipt and enters the application transaction root.

Every attested kind checks its authority before any parameter, following the
authority-before-funds ordering accepted in ADR 0021, so an unauthorized
submitter never learns which parameter would have failed. Each kind then checks
static ranges before state lookups, and state lookups before arithmetic. Kind 5
is the one exception: it completes the version-one fee-payer sequence first, so
that a transfer and an exercise fail identically on a fee, nonce, or expiry
problem.

Codes 0 through 8 keep their version-one numbers and meanings so that a
version-one transfer produces the same numeric result on either chain. Code 4 is
renamed to cover a fee payer generally. Codes 9 through 15 are reserved and
invalid.

| Code | Name | Kinds |
| ---: | --- | --- |
| 0 | `SUCCESS` | all |
| 1 | `ZERO_AMOUNT` | 1 |
| 2 | `FEE_LIMIT_TOO_LOW` | 1, 5 |
| 3 | `EXPIRED` | 1, 5 |
| 4 | `FEE_PAYER_NOT_FOUND` | 1, 5 |
| 5 | `NONCE_EXHAUSTED` | 1, 5 |
| 6 | `NONCE_MISMATCH` | 1, 5 |
| 7 | `DEBIT_OVERFLOW` | 1 |
| 8 | `INSUFFICIENT_BALANCE` | 1, 5 |
| 16 | `ATTESTATION_UNAUTHORIZED` | 2, 3, 4, 6 |
| 17 | `ATTESTATION_EXPIRED` | 2, 3, 4, 6 |
| 18 | `SEAT_RANGE` | 2, 3, 4, 5 |
| 19 | `SEAT_ALREADY_ACTIVATED` | 2 |
| 20 | `SEAT_NOT_ACTIVATED` | 3, 4, 5 |
| 21 | `INVALID_REFERRER` | 2 |
| 22 | `REFERRER_NOT_ACTIVATED` | 2 |
| 23 | `WINDOW_OVERFLOW` | 2 |
| 24 | `SEAT_NOT_REFERRED` | 4 |
| 25 | `CYCLE_RANGE` | 3, 4, 5 |
| 26 | `CYCLE_NOT_ELAPSED` | 3, 4 |
| 27 | `CYCLE_NOT_NEXT` | 3, 4, 5 |
| 28 | `ALLOCATION_COUNT_RANGE` | 3 |
| 29 | `INVALID_ALLOCATION_RECIPIENT` | 3 |
| 30 | `ALLOCATION_SUM_MISMATCH` | 3 |
| 31 | `REFERRAL_DECISION_INVALID` | 4 |
| 32 | `PERMISSION_NOT_PENDING` | 5 |
| 33 | `INVALID_CHANNEL` | 6 |
| 34 | `ZERO_ISSUANCE_AMOUNT` | 6 |
| 35 | `SEQUENCE_MISMATCH` | 6 |
| 36 | `CHANNEL_CAP` | 6 |

`SEAT_RANGE` is a `seat_id` above 99,999. `CYCLE_RANGE` is a `cycle_index` above
730. `INVALID_REFERRER` is a referrer equal to the activating seat or above
99,999.

Because the evaluated watermark is a single value, an already-evaluated cycle
and an out-of-order cycle are the same condition and share `CYCLE_NOT_NEXT`.
Replay of an accepted evaluation therefore fails on the ordering check rather
than on a separate replay set.

### Unreachable cap failures are invariant failures

The base and referral channel caps are exactly 100,000 seats times 731 cycles
times their per-cycle legs. Each `(seat, cycle, kind)` reserves at most once,
bounded by the seat capacity and the window length, so permission evaluation can
never exhaust a channel. Exercise moves value from outstanding to issued, and
`issued + outstanding <= cap` already held at reservation, so exercise can never
exhaust one either.

`CHANNEL_CAP` is therefore a receipt code for kind 6 alone. A cap violation
reached through kind 3, 4, or 5, or any checked-arithmetic violation outside
`DEBIT_OVERFLOW`, `WINDOW_OVERFLOW`, and `CHANNEL_CAP`, indicates corrupted
state rather than a transaction outcome. It is an internal invariant failure
that invalidates the proposed block and preserves the pre-block state, exactly as
version one treats an impossible recipient or fee-pool overflow.

### Atomicity and write order

Every check for a transition completes before any write. A transition's writes
are therefore all-or-nothing, and because the committed state is a sorted map
whose commitment is order-independent, the order in which the writes are applied
does not affect the resulting root. An implementation must still use checked
arithmetic throughout.

## Receipts

Each admitted transaction produces exactly one 49-octet receipt:

| Offset | Size | Field |
| ---: | ---: | --- |
| 0 | 4 | ASCII `PSRC` |
| 4 | 2 | receipt version `2` |
| 6 | 32 | transaction ID |
| 38 | 1 | transaction kind |
| 39 | 2 | result code |
| 41 | 8 | fee charged |

The transaction kind is included so that a result code is read against the kind
that produced it. Unknown result codes, a code not assigned to the recorded
kind, and a nonzero fee on any failed or feeless transaction are invalid.
Receipt order is the admitted transaction order. Receipts are deterministic
outputs and are not part of the state-root preimage.

Version-one receipts remain the receipt format for a version-one chain. A
version-two chain emits version-two receipts for every kind, including kind 1.

## Ordered block execution

Version-one block execution is unchanged: the only valid next height is `h + 1`,
raw inputs execute in their provided order, admission failures are omitted from
application execution, each admitted transaction identifier is appended to the
commitment list, each receipt is appended whether execution succeeds or fails,
and the state height is set after all inputs. Version two permits at most 65,535
raw inputs and at most 65,535 admitted transactions per block.

`epoch_index` is evaluated against the executing block height, so every
transaction in a block observes the same epoch.

## Resource limits

| Bound | Value |
| --- | ---: |
| Seat records | 100,000 |
| Channel records | 10 |
| Direct sequence records | 4 |
| Typed custody records | 100,004 |
| Reallocation records | at most 73,100,000 |
| Referral-skip records | at most 73,100,000 |
| Largest version-two transaction | 921 octets |
| Allocation entries per transaction | `max_performance_recipients`, at most 64 |

The first four bounds are unconditional: 200,018 records and 6,800,388 octets of
leaf bytes at full seat capacity. Every seat's complete accumulation history is
inside that figure, because the active path costs only its four watermarks.

The two exception record types are what the worst case turns on, and it is
large. Each requires a seat to have been evaluated inactive in a cycle and not
yet to have exercised it. With every seat inactive for its entire window and no
exercise at all, single-recipient reallocations plus skip records reach
1,973,700,000 octets, and reallocations at the 64-recipient ceiling reach
57,237,300,000. The second figure is well beyond a minimum-spec Founder Node.

Three things bound it in practice, and none of them is a consensus rule:

- reaching it takes 731 epochs during which a stand-in authority declares the
  entire population inactive every cycle;
- every reallocation recipient must be an activated seat, and each is credited
  34,200,000,000 atomic units by the exercise that deletes the record, so the
  records that accumulate are exactly the ones someone is paid to clear; and
- exercise is permissionless, so a recipient never depends on the inactive seat
  to collect.

Incentive is not containment. A consensus bound on the exception records — a
per-seat limit on unexercised reallocations, a smaller ceiling once the
performance winner count is decided, or a cheaper reallocation encoding — must
be selected in the implementation slice, and the choice depends on the
founder-reserved winner count. This specification states the bound it has rather
than claiming one it does not.

An implementation must maintain the economy commitment incrementally. At the
stated bound a full tree recomputation per block is not viable, and the
specification fixes the commitment, not the method by which it is maintained.

`max_performance_recipients` is a resource bound, not the founder's performance
winner count. Its M3 devnet value is the protocol ceiling of 64 so that the
devnet exercises the general case and no configured number resembles an answer.
When the winner count is decided, it sets this parameter; a count above 64
requires a new transaction version because the allocation array is bounded by a
`u8`.

Each transition reads and writes only the seat, cycle, channel, custody, and
sequence entries it names. No transition iterates over all seats, all cycles, or
all channels.

## Determinism

Validation order, result numbers, receipt bytes, successful writes, failure
atomicity, and the epoch derivation are consensus rules. Implementations must
not consult a wall clock, locale, filesystem order, host integer width, adapter
metadata, floating-point arithmetic, or any mutable external value. Block
timestamps, including a consensus adapter's median time, are not consensus
inputs to any rule in this document.

## Compatibility

### Against accepted M1 bytes

- The 200-octet version-one transfer is unchanged and remains valid on a
  version-two chain, with its version-one signing label, transaction-ID label,
  and result codes 0 through 8 intact.
- The version-one genesis encoding is unchanged. A version-two chain uses
  genesis schema 2, which produces a different chain identifier. It is a new
  chain, not a migration of the M1 devnet, and no version-one state root is
  reinterpreted.
- The chain-identifier derivation rule and its label are unchanged.
- The 48-octet account entry, the accounts tree, and its three version-one
  labels are reused verbatim.
- The version-one state-root construction remains the definition for a
  version-one chain. Version two uses a distinct label and a distinct preimage.
- The version-one 47-octet receipt remains the receipt for a version-one chain.
- The M1 devnet's nine-decimal denomination is not reinterpreted. A version-two
  chain uses the eight-decimal Founder denomination and the
  5,574,394,010,000,000,000-atomic supply limit accepted in ADR 0017. The two
  chains share no state.

Nothing in this document changes an M1 account, fee pool, height, transaction
root, receipt, state root, SQLite database, ABCI response, or CometBFT
validator.

### Against frozen M2 schemas

The accepted M2 specifications, vectors, and digests are frozen and unchanged.
Where the consensus encoding is narrower than the model, the narrowing is
recorded here rather than by editing the M2 contract. Every outcome the model
reaches in cycle order is reachable in consensus with identical amounts,
beneficiaries, and conservation.

| M2 model | Version-two consensus | Reason |
| --- | --- | --- |
| `evaluated_permission_keys` set, any cycle order | per-seat, per-kind evaluated watermark, cycle order required | bounded state: 4 octets per seat replaces up to 1,462 keys |
| `pending_permissions` map | exercised watermark plus reallocation and skip records | the four fixed legs are constants; only exceptions cost a record |
| `accepted_direct_decision_ids` set of free identifiers | strict per-channel `u64` sequence | an unbounded replay set is a state-growth attack |
| `typed_custody[direct_beneficiary:*]` | ordinary account balance | direct channels pay users, and a zero-supply genesis needs one path to a spendable balance |
| exercise authorized by a simulator capability | permissionless, fee-bearing | exercise has no discretion; withholding would strand a reallocated leg |
| research inputs supplied as plain JSON values | signed, chain-bound, expiring attestations from configured keys | a consensus input must be authorized and replay-safe |

A future extension of the independent Python model must implement the consensus
rules, and the cross-language vectors must be derived from this document rather
than from the M2 result digests.

### Versioning

The version-two genesis layout, transaction encodings, attestation preimage,
economy record layouts, domain labels, state-root preimage, receipt layout, and
result-code numbers are immutable for version two. A changed transition, field,
bound, or semantic rule requires a new schema version with explicit activation
and migration vectors. A protocol upgrade may add a new kind, record type,
custody kind, policy identifier, or result code but must never reinterpret an
assigned one.

There is no in-place migration of a state root. Splitting the activity attester,
adding a claim transition, adding commercial and fee routing, or replacing a
stand-in authority with an accepted policy each requires its own specification
and ADR.

## Required vectors

`test-vectors/founder-economy-consensus-v1.txt` becomes normative when the
implementation slice produces it. It must fix:

- version-two canonical genesis bytes, byte length, and chain ID, and the
  rejection of a nonzero total supply, initial fee pool, or account count, a
  wrong supply limit, an out-of-range `epoch_blocks` or
  `max_performance_recipients`, and duplicate authority keys;
- `epoch_index` at the boundary, a seat's first and last eligible cycle, a
  cycle evaluated one block too early, and the `WINDOW_OVERFLOW` guard;
- canonical unsigned and signed bytes, transaction ID, and receipt for each of
  kinds 2 through 6, including the minimum and maximum allocation counts;
- an attestation preimage, a valid attestation, an unauthorized policy ID, an
  unauthorized key, an expired attestation, and an attestation replayed against
  a different payload, kind, or chain;
- every numeric result code, each produced by a transaction that reaches it;
- an unchanged version-one transfer executing on a version-two chain with a
  version-two receipt;
- economy leaf bytes for all six record types, the empty, single-record, and
  multi-record economy roots, and the version-two state root;
- a complete 731-cycle window for one seat, with the exact per-seat products
  from the accepted manifest, at least one inactive cycle with a multi-recipient
  reallocation, and at least one declined referral cycle;
- conservation after every accepted transition, cap exhaustion on a direct
  channel, sequence replay, and evaluation and exercise replay; and
- proof that a failed transition writes nothing, by state-root equality before
  and after.

Independent C++20 and Python harnesses must both reproduce every positive vector
and reject every negative case before an implementation is accepted.

## What acceptance establishes

Acceptance of this document fixes an exact, deterministic, replay-safe encoding
for the Founder economy and a cycle rule that depends on nothing but block
height. It does not implement any of it, and no code in this repository executes
these bytes today.

It settles no founder-reserved policy. The activity metric and its grace
allowance, performance ranking, winner count, and tie rule; inactive-seat
referral treatment; direct-channel eligibility; and the AI funding framework all
remain open, and this specification carries them as signed stand-in
attestations precisely so that their absence stays visible rather than being
filled by a default.

Passing the vectors this document requires will establish exact accounting under
an exact encoding. It will not establish that the encoding is safe against an
adversarial network, that the stand-in authorities are acceptable, or that any
economic, biometric, bridge, or AI claim holds. Independent protocol,
cryptographic, and economic review remains required before any activation claim.
