# Economy transition v2

Status: Accepted M3 consensus transition contract; not yet implemented

This document is normative for the canonical transaction bytes, state keys,
state-root construction, receipt bytes, and numeric result codes of the Founder
Economy as a **consensus transition**, and for its exact compatibility boundary
against the accepted M1 artifacts.

It extends [`protocol-primitives-v1.md`](protocol-primitives-v1.md) and
[`ledger-transition-v1.md`](ledger-transition-v1.md); definitions there govern
unless this document imposes a narrower rule. It realizes the accounting
contract of [`founder-economy-manifest-v2.md`](founder-economy-manifest-v2.md)
and the transitions of
[`founder-economy-simulator-v3.md`](founder-economy-simulator-v3.md), and reads
the window grid of [`cycle-boundary-v1.md`](cycle-boundary-v1.md) and the
measurement pipeline of
[`uptime-measurement-v1.md`](uptime-measurement-v1.md).

It satisfies requirements 5 and 6 of [`first-goal.md`](../project/first-goal.md).
The change is classified as encoding, state-transition shape, and compatibility.
[ADR 0032](../decisions/0032-economy-consensus-transition-and-compatibility.md)
records the alternatives and the decision.

**Everything before this specification was a Python model that activates
nothing.** This is the first artifact in the milestone that states what
independent nodes must reproduce byte-for-byte. It changes no M1 byte, no
accepted vector, and no accepted digest, because it defines a *second* chain
rather than a migration of the first.

## Scope

Version two defines:

- the canonical signed transaction envelope shared by every kind, and the five
  new transaction kinds;
- the canonical economy state key space and its value encodings;
- version-two genesis, chain identity, and the state-root construction;
- the version-two receipt and the complete numeric result-code space;
- the ordered rejection conditions of each new kind, and the total mapping from
  `founder-economy-simulator-v3`'s model codes onto them;
- the reallocation commitment, which is the bounded settlement mechanism
  `founder-economy-manifest-v2` names as remaining M3 work; and
- the exact compatibility boundary against M1 transaction bytes, state, and
  roots.

It does not define the C++20 kernel implementation, which is requirement 10; the
cross-language vectors that implementation must reproduce, which are requirement
11; the four-node adversarial scenarios, which are requirement 13; the
distribution of transaction fees and commercial revenue to active seats, which
`revenue-routing-v1` models and no kind here performs; the withdrawal of typed
custody into a spendable account; the deterministic active-set protocol; or the
challenge content. Three authorization predicates are named and deliberately
left undefined; they are listed in
[Authorization](#authorization) and in
[What this specification does not establish](#what-this-specification-does-not-establish).

## Bindings

This specification holds no second copy of any founder-directed value.

**The manifest layer.** The channel table, the ten caps, the base-permission
legs, the denomination, the seat capacity, the issuance-cycle count, and the
referral amount are the accepted `founder-economy-manifest-v2` contract. Its
digest is bound into version-two genesis, so a chain whose manifest differs is a
different chain rather than the same chain with a different table.

**The window grid.** `window_of_height`, `first_cycle_window`,
`last_cycle_window`, and `window_for_cycle` are `cycle-boundary-v1`.

**The measurement.** The finalised per-window record, its finalisation rule, and
its in-scope seat set are `uptime-measurement-v1`.

**The transitions.** The activity verdict, the winner rule, the tie rule, the
remainder rule, the carry and its conservation identity, the journal buckets,
and the ordered rejection conditions are `founder-economy-simulator-v3`. This
document encodes them; it does not restate them, and where it narrows one it
says so and derives the narrowing.

## The transaction envelope

Every version-two transaction, including the version-one native transfer, is:

```text
signed_transaction = header(80) || body(kind-specific) || trailer(16) || signature(64)
```

The header is exactly the first 80 bytes of the accepted version-one transfer,
unchanged:

| Offset | Size | Field | Required value or range |
| ---: | ---: | --- | --- |
| 0 | 4 | magic | ASCII `PSTX` |
| 4 | 2 | schema version | `1` |
| 6 | 1 | transaction kind | `1` through `6` |
| 7 | 32 | chain ID | configured chain |
| 39 | 1 | signature scheme | `1` |
| 40 | 32 | sender public key | canonical Ed25519 key |
| 72 | 8 | nonce | `u64` |

The trailer is exactly the last 16 bytes of the accepted version-one transfer,
unchanged:

| Offset from body end | Size | Field |
| ---: | ---: | --- |
| 0 | 8 | fee limit `u64` |
| 8 | 8 | valid-until height `u64` |

**The schema version stays `1` because these 80 bytes do not change.**
`protocol-primitives-v1` permits an upgrade to "add new algorithm,
address-payload, transaction, or state-schema identifiers" and forbids
reinterpreting an existing one. A new kind identifier is the addition it
permits; bumping the envelope version would change bytes that are identical, and
would state a difference that does not exist.

### The version-one transfer is the kind-1 instance

Kind 1's body is the accepted transfer's middle 40 bytes:

| Offset | Size | Field |
| ---: | ---: | --- |
| 80 | 32 | recipient account ID |
| 112 | 8 | amount `u64` |

so `80 + 40 + 16 = 136` unsigned and `136 + 64 = 200` signed, which is the
accepted version-one transfer exactly. **The decomposition is a factoring of
version one, not a replacement of it.** The vectors prove this rather than
asserting it: the version-two encoder is handed the accepted
`protocol-primitives-v1` transfer inputs and must reproduce that specification's
recorded unsigned bytes, signed bytes, and transaction ID byte-for-byte.

Every field a version-two transaction needs in common — the chain it binds, who
signed it, its replay key, what it will pay, and when it expires — is already in
version one's transfer in exactly one place. Discovering that the transfer
factors cleanly into a shared header, a kind-specific body, and a shared trailer
is what makes version two an extension rather than a second protocol.

### Signing and identity are unchanged

```text
signing_message = D("protocol-stack:v1:tx-sign") || unsigned_transaction
transaction_id  = H(D("protocol-stack:v1:tx-id") || signed_transaction)
```

Both labels are the accepted version-one labels and are **not** re-versioned.
The transaction kind is at offset 6 and the chain ID at offset 7, so both are
inside every signature preimage: a signature over one kind cannot be presented
as another, and a signature for one chain cannot be presented on another.
Versioning the label would add no separation that the preimage does not already
carry, and would destroy the byte-identity of the kind-1 instance for nothing.

Two kinds share a body length — kinds 3, 4 with an empty winner list, and 5 are
all six-byte bodies plus the list header where present. They are distinguished
by the signed kind byte alone, which is sufficient and is checked by a vector
that presents each body under each of the other kinds' identifiers and requires
the signature to fail.

## Transaction kinds

| Kind | Name | Body size | Unsigned | Signed |
| ---: | --- | ---: | ---: | ---: |
| 1 | `native_transfer` | 40 | 136 | 200 |
| 2 | `activate_seat` | 9 | 105 | 169 |
| 3 | `evaluate_base_permission` | 6 | 102 | 166 |
| 4 | `exercise_permission` | 10 + 4W | 106 + 4W | 170 + 4W |
| 5 | `accrue_referral` | 6 | 102 | 166 |
| 6 | `direct_issue` | 105 | 201 | 265 |

`W` is the winner count carried by an exercise and is zero for every met cycle.
Kind 4 is the only variable-length kind.

### Kind 2 — `activate_seat`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 4 | seat ID `u32` | `0` through `99,999` |
| 84 | 1 | has referrer `bool` | `0x00` or `0x01` |
| 85 | 4 | referrer seat ID `u32` | `0` through `99,999`, or exactly `0` when absent |

A `has_referrer` of `0x00` requires a referrer field of exactly zero. Any other
value is a second encoding of "no referrer", which
`protocol-primitives-v1` forbids as a non-minimal representation, and is
`MALFORMED_TRANSACTION`.

**There is no `activation_height` field, and its absence is the point.** The
model takes an activation height as an input and must therefore enforce
`HEIGHT_RANGE` and `HEIGHT_NOT_MONOTONIC` at the writer. On a chain the
activation height *is* the executing block height, which `ledger-transition-v1`
already fixes as the sole successor of the previous height and invalidates the
block on overflow. Both conditions are consequently satisfied by construction
and unrepresentable as transaction results. This is exactly what
`founder-economy-simulator-v3` predicted: "a real activation executes inside the
block that includes it, so an activation height cannot decrease across the
sequence a chain records."

### Kind 3 — `evaluate_base_permission`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 4 | seat ID `u32` | `0` through `99,999` |
| 84 | 2 | cycle index `u16` | `0` through `730` |

**There is no uptime record and no cycle window field.** The window is
`window_for_cycle(seat.activation_height, cycle_index)`, derived from state, and
the record for that window is state the uptime pipeline finalised. A submitter
therefore selects a cycle and nothing else.

That removes eight of the model's rejection conditions as inputs that do not
exist, and it removes them for one reason: a supplied record is an opinion, and
the model's `MISSING_UPTIME_RECORD`, `INVALID_UPTIME_RECORD`,
`INCONSISTENT_UPTIME_RECORD`, `SEAT_NOT_IN_SCOPE`, and
`INCOMPLETE_UPTIME_RECORD` conditions exist to bound what a supplied opinion may
claim. The model's whole `bound_uptime_records` map exists so that a window's
uptime is one fact for a run rather than a per-event opinion; a chain reads one
finalised record per window and has one fact by construction. The three window
codes go the same way, because the window is derived rather than presented.

One condition replaces them. A cycle may be evaluated only when its window is
final under `uptime-measurement-v1` — at or after the first height of window
`w + 2` — which is `WINDOW_NOT_FINAL`. This is a condition the model cannot have,
because the model has no current height.

### Kind 4 — `exercise_permission`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 4 | seat ID `u32` | `0` through `99,999` |
| 84 | 2 | cycle index `u16` | `0` through `730` |
| 86 | 4 | winner count `u32` | `0`, or the recorded count |
| 90 | 4W | winner seat IDs `u32` | strictly increasing, each `0` through `99,999` |

The list is empty for a met cycle and is the complete winner set for a failed
one. It is checked against the commitment recorded at the window's finalisation;
see [The reallocation commitment](#the-reallocation-commitment).

### Kind 5 — `accrue_referral`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 4 | referred seat ID `u32` | `0` through `99,999` |
| 84 | 2 | cycle index `u16` | `0` through `730` |

The accrual is unconditional and direct-mint. It reads the referred seat's
recorded referrer and credits the referrer when one exists and the unreferred
performance pool when one does not, which is the founder-directed rule that
consumes the channel exactly. It does not read a record, a window, or a verdict,
so it has no boundary condition and no finality condition.

### Kind 6 — `direct_issue`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 1 | channel ID `u8` | `5`, `6`, `8`, or `9` |
| 81 | 32 | decision ID | 32 octets |
| 113 | 32 | beneficiary account ID | 32 octets |
| 145 | 8 | amount `u64` | nonzero |
| 153 | 32 | authorization | 32 octets |

The channel ID is the accepted manifest's array index, so the wire value is read
from the accepted contract rather than numbered again here. Index `7`,
`founder_referral`, is **not** admissible: it is consumed exactly by kind 5, and
admitting it here would mint referral units outside the per-seat-cycle
accounting, which is the containment `founder-economy-simulator-v3` already
applies. Indices `0` through `4` are base-permission channels and are not
direct-mint. Any other value is `INVALID_CHANNEL`.

**The `authorization` field is a commitment to an eligibility decision whose
verification predicate is not defined by this specification, and kind 6 is
specified but not activated.** A conforming version-two chain rejects every kind
6 with `UNAUTHORIZED` until that predicate is accepted. The eligibility and
anti-abuse mechanics for `liquidity_mining`, `impermanent_loss_protection`,
`hub_verified_user_incentives`, and `initial_mystery_box_incentives` are
founder-reserved and are listed under "Explicitly unresolved founder details" in
the Founder Constitution. `founder-economy-manifest-v2` may keep
`direct_channel_eligibility_result` as a research placeholder because a research
model may carry an unverified input; a consensus transition may not, because it
must decide what it actually verifies. Refusing the kind is the conservative
default and is reversible by an accepted predicate; inventing one would set what
a participant must do in order to be paid.

## Admission

Admission operates on raw transaction bytes before ledger state is read, and its
version-one steps are unchanged in order and in meaning:

1. decode exactly one signed version-two transaction with no trailing bytes;
2. require the configured chain ID;
3. derive the sender account ID from the encoded public key;
4. strictly verify the Ed25519 signature over the signing message.

Step 1 classifies a wrong magic, schema version, transaction kind,
signature-scheme identifier, a length that is not the exact length its kind
requires, a non-minimal absent-referrer encoding, a winner list that is not
strictly increasing, or a winner count above `FOUNDER_SEAT_CAPACITY` as
`MALFORMED_TRANSACTION`. The admission codes are version one's, unchanged:

| Code | Name |
| ---: | --- |
| 1 | `MALFORMED_TRANSACTION` |
| 2 | `WRONG_CHAIN` |
| 3 | `INVALID_SIGNATURE` |

**A bounded numeric field outside its range is not an admission failure.** A
seat ID of `100,000` decodes to a well-formed `u32` and is refused at execution
with `CYCLE_RANGE`. Admission is defined to perform no state read and to produce
no receipt, so classifying a range violation there would remove its receipt and
its place in the ordered transaction root, and a submitter's invalid seat ID
would leave no canonical trace. Shape belongs to admission and value belongs to
execution; the winner list is checked for shape at admission because strict
increase and its count bound are properties of the bytes alone.

Admission failures perform no state read or write, produce no application
receipt, and do not enter the application transaction root, exactly as in
version one.

## Authorization

Every kind is signed by an account, and every kind charges that account the
fixed fee. The Founder Constitution decides that fees apply here: "Every
protocol transaction fee is charged separately ... whether the transaction is a
purchase, transfer, issuance exercise, or another accepted state transition."

Three predicates decide *which* sender each kind accepts, and this specification
names all three and defines none of them:

| Predicate | Kinds | What is already decided | What is reserved |
| --- | --- | --- | --- |
| `activation_authority` | 2 | a sensitive Founder action requires an accepted signature **and** a fresh action-bound biometric approval | which key, and what proves purchase and enrollment |
| `seat_authority` | 3, 4, 5 | the same clause governs a Founder action against a recorded seat | which recorded manager addresses satisfy it |
| `direct_issue_authority` | 6 | nothing | the whole eligibility and anti-abuse rule for four channels |

A sender the applicable predicate refuses is `UNAUTHORIZED`. Encoding the
sender, reserving the code, and refusing kind 6 outright is what this
specification supplies. **Which senders a predicate accepts sets what an end
user must do and own in order to participate and be paid, so it is
founder-reserved and is not decided here.** It is the nearest blocking
dependency of requirement 10 and is recorded as such rather than filled with a
research fixture.

`founder-economy-simulator-v3` already records the same boundary from the other
side: "Nothing here proves that a seat paid for a position, enrolled, passed
biometric verification, or is a distinct human, and nothing here decides which
transition supplies the height."

## Canonical economy state

The version-two ledger state is version one's state — chain ID, supply limit,
total supply, fixed fee, height, fee pool, and the ordered account map — plus one
ordered map from canonical byte keys to canonical byte values.

A key is `u8(entry_kind)` followed by fixed-width big-endian fields, so
unsigned lexicographic key order is total and unambiguous and no key is a prefix
of another with a different meaning.

| Kind | Entry | Key | Key bytes | Value | Value bytes |
| ---: | --- | --- | ---: | --- | ---: |
| 1 | seat | `u8(1) \|\| seat_id:u32` | 5 | `activation_height:u64 \|\| has_referrer:u8 \|\| referrer_seat_id:u32` | 13 |
| 2 | channel | `u8(2) \|\| channel_id:u8` | 2 | `issued_atomic:u64 \|\| outstanding_atomic:u64` | 16 |
| 3 | pending permission | `u8(3) \|\| seat_id:u32 \|\| cycle_index:u16` | 7 | `met_cycle:u8` | 1 |
| 4 | referral accrual | `u8(4) \|\| seat_id:u32 \|\| cycle_index:u16` | 7 | *(empty)* | 0 |
| 5 | direct decision | `u8(5) \|\| decision_id:bytes<32>` | 33 | *(empty)* | 0 |
| 6 | typed custody | `u8(6) \|\| beneficiary_kind:u8 \|\| beneficiary_id:bytes<32>` | 34 | `amount_atomic:u64` | 8 |
| 7 | performance carry | `u8(7)` | 1 | `carry_atomic:u64` | 8 |
| 8 | window result | `u8(8) \|\| cycle_window:u64` | 9 | `winner_root:bytes<32> \|\| winner_count:u32 \|\| unevaluated_count:u32 \|\| met_bitmap:bytes` | 44 + ⌈n/8⌉ |

An entry kind outside `1` through `8` cannot occur, because no transition writes
one and the state is not an untrusted input.

**A pending permission holds one byte.** The model stores the resolved legs,
including one leg per performance winner, which is what makes its abstract
resource ceiling 73,100,000 entries of unbounded width. Here the legs of a met
cycle are the manifest's five fixed legs and need no storage, and the legs of a
failed cycle are the manifest's four unchanged legs plus an equal split over the
window's winner set, which is recorded once per window rather than once per
failed seat. The verdict is the only thing that must survive from evaluation to
exercise.

**An evaluated permission key is not a separate entry.** The model keeps
`evaluated_permission_keys` as a set alongside `pending_permissions` because a
permission is removed when exercised and replay must still be refused. Here the
verdict entry is retained after exercise with `met_cycle` replaced by an
exercised marker, so one entry answers both questions and the set disappears.
The `met_cycle` byte is `0x00` for a failed unexercised cycle, `0x01` for a met
unexercised cycle, and `0x02` once exercised.

**`last_activation_height` is not state.** The model needs it to enforce
monotonicity; a chain's heights are monotone by construction.

### The economy Merkle tree and the version-two state root

Entries are sorted by unsigned lexicographic key and must not contain
duplicates. A leaf preimage uses the accepted `bytes` primitive — a `u32` length
followed by that many octets — for both key and value, so the boundary between
them is explicit rather than inferred from the entry kind:

```text
economy_entry = bytes(key) || bytes(value)

economy_tree({})            = H(D("protocol-stack:v2:economy-empty"))
economy_tree({entry})       = H(D("protocol-stack:v2:economy-leaf") || entry)
economy_tree(left || right) = H(D("protocol-stack:v2:economy-node") || l || r)
```

The tree shape is `protocol-primitives-v1`'s RFC 9162 construction, unchanged: no
leaf is duplicated and no padding leaf is inserted.

```text
state_root =
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
    economy_entry_count:u64 ||
    economy_tree_root
  )
```

The accounts tree is `protocol-primitives-v1`'s, entry-for-entry unchanged. The
label and the version field both differ from version one, so **a version-two
state root is never equal to a version-one state root, including over an
identical account set and an empty economy.** That is required rather than
incidental: `protocol-primitives-v1` states that "there is no in-place migration
of a state root", and a construction that collided on the empty case would be a
version-one root reinterpreted as a version-two root.

## Version-two genesis

| Field | Encoding | Required value |
| --- | --- | --- |
| magic | `bytes<4>` | ASCII `PSGN` |
| schema version | `u16` | `2` |
| network ID | `u32` | configured |
| supply limit | `u64` | configured, nonzero |
| total supply | `u64` | configured, at most the limit |
| fixed transfer fee | `u64` | configured |
| initial fee pool | `u64` | configured |
| economy manifest digest | `bytes<32>` | the accepted manifest digest |
| account count | `u32` | `0` through `21,843` |
| accounts | repeated 48-byte state entries | exactly `account count` entries |

```text
chain_id = H(D("protocol-stack:v2:chain-id") || canonical_genesis_v2_bytes)
```

Genesis writes the ten channel entries with both amounts zero and the
performance-carry entry with zero, and nothing else. It never writes a seat, a
permission, a custody entry, or a window result.

**Three of version one's genesis requirements are relaxed, and each is forced by
founder direction rather than chosen.** The Founder Constitution states that
"there is no founder-directed genesis allocation: native units enter circulation
only through Founder Node issuance permissions and capped direct-mint channels",
so a Founder Economy chain must be able to open with `total supply` zero and
`account count` zero, which version one forbids. The fixed fee is relaxed to
permit zero for the consequence that follows: with a zero allocation and a
nonzero fee, no account can pay for the first transaction, so no transaction can
execute and the chain cannot reach a state in which any fee is payable.

**That bootstrap is a real gap and is recorded rather than closed here.** A
production chain must reach a first payable balance by some path, and every path
this specification can see is external — seat purchases are made in BTC, ETH, or
an approved stablecoin through the restricted bridge, and the bridge is a later
milestone. A zero fee makes a devnet runnable and states the dependency; it does
not decide the production fee policy, which sets what a user must pay and is not
settled here.

The genesis prefix through `account count` is 78 bytes, so the 1,048,576-byte
canonical object bound admits at most 21,843 entries:

```text
78 + 48 * 21,843 = 1,048,542   accepted
78 + 48 * 21,844 = 1,048,590   rejected
```

A decoder must reject a declared count above 21,843 before allocating account
storage. Version one's bound is 21,844 against a 46-byte prefix; the difference
is exactly the 32-byte manifest digest, and both figures are derived rather than
recorded.

## Execution

An admitted transaction executes against the current tentative block state.
Every kind first applies the shared envelope checks in version one's order and
with version one's codes and meanings, then its own conditions.

| Result | Name | Condition |
| ---: | --- | --- |
| 2 | `FEE_LIMIT_TOO_LOW` | fee limit is below the fixed fee |
| 3 | `EXPIRED` | valid-until height is below the executing block height |
| 4 | `SENDER_NOT_FOUND` | sender account does not exist |
| 5 | `NONCE_EXHAUSTED` | stored sender nonce is `u64` maximum |
| 6 | `NONCE_MISMATCH` | transaction nonce is not stored nonce plus one |
| 8 | `INSUFFICIENT_BALANCE` | sender balance is below what it must debit |

Codes `1` and `7` are transfer-shaped and reachable only where a body carries an
amount: `ZERO_AMOUNT` for kinds 1 and 6, and `DEBIT_OVERFLOW` for kind 1 alone,
because every other kind debits only the fixed fee.

**These six are not transfer conditions that the economy happens to inherit.**
They are envelope conditions, and they are shared precisely because the header
and trailer are shared. That is the second consequence of the factoring, and it
is why the version-one result numbers keep their exact meanings across all six
kinds rather than being re-numbered per kind.

Every non-success result performs no state write and charges no fee. It still
produces a receipt and enters the ordered transaction root, exactly as in
version one.

### Kind 2 — activate seat

Rejection conditions, in this order:

1. a sender `activation_authority` refuses is `UNAUTHORIZED`;
2. a `seat_id` outside `0..99,999` is `CYCLE_RANGE`;
3. a `referrer_seat_id` outside `0..99,999`, or equal to `seat_id`, is
   `INVALID_REFERRER`;
4. an already-activated `seat_id` is `REPLAY`;
5. a `referrer_seat_id` that is not itself activated is `SEAT_NOT_ACTIVATED`.

Conditions 2 through 5 are `founder-economy-simulator-v3`'s conditions 1, 3, 4,
and 5 in its order. Its conditions 2 and 6 are unrepresentable. Authorization
precedes every value check so that a refused sender learns nothing about which
seats exist.

On success the transition writes one seat entry whose `activation_height` is the
executing block height, issues nothing, reserves nothing, and credits nothing.

### Kind 3 — evaluate base permission

Rejection conditions, in this order:

1. a sender `seat_authority` refuses is `UNAUTHORIZED`;
2. a `seat_id` or `cycle_index` outside range is `CYCLE_RANGE`;
3. an unactivated seat is `SEAT_NOT_ACTIVATED`;
4. an already-evaluated key is `REPLAY`;
5. a derived window that is not yet final is `WINDOW_NOT_FINAL`;
6. a leg that does not fit its channel is `CHANNEL_CAP`.

On success the transition reads the window's finalised met bit for the seat,
writes the pending-permission entry, and increases each affected channel's
`outstanding_atomic`. It creates no units: outstanding capacity is a liability,
not issued supply.

### Kind 4 — exercise permission

Rejection conditions, in this order:

1. a sender `seat_authority` refuses is `UNAUTHORIZED`;
2. a `seat_id` or `cycle_index` outside range is `CYCLE_RANGE`;
3. no pending permission, or one already exercised, is `PERMISSION_NOT_FOUND`;
4. a winner list that is not exactly the committed set is `INVALID_WINNER_SET`;
5. a leg that does not fit its channel is `CHANNEL_CAP`.

On success the transition moves each leg from `outstanding_atomic` to
`issued_atomic`, credits typed custody, updates the performance carry, marks the
permission exercised, decrements the window's `unevaluated_count`, and increases
`total_supply` by the permission total. It is atomic: every beneficiary is
credited or none is.

### Kind 5 — accrue referral

Rejection conditions, in this order:

1. a sender `seat_authority` refuses is `UNAUTHORIZED`;
2. a `seat_id` or `cycle_index` outside range is `CYCLE_RANGE`;
3. an unactivated referred seat is `SEAT_NOT_ACTIVATED`;
4. an already-accrued key is `REPLAY`;
5. a leg that does not fit the channel is `CHANNEL_CAP`.

### Kind 6 — direct issue

Rejection conditions, in this order:

1. every sender is `UNAUTHORIZED` while the predicate is undecided;
2. a `channel_id` outside `{5, 6, 8, 9}` is `INVALID_CHANNEL`;
3. a zero `amount` is `ZERO_AMOUNT`;
4. an already-accepted `decision_id` is `REPLAY`;
5. an absent authorization is `MISSING_RESEARCH_INPUT`, one not bound to this
   exact action is `INVALID_RESEARCH_INPUT`, and a negative decision is
   `NOT_ELIGIBLE`;
6. an amount that does not fit the channel is `CHANNEL_CAP`.

Conditions 2 through 6 are specified so that the encoding is complete and the
code space is fixed. **They are unreachable in a conforming implementation**
until `direct_issue_authority` is decided, because condition 1 refuses every
sender first. The vectors record that unreachability as a derived property, so a
later implementation that activates the kind without the founder decision fails
a check rather than passing silently.

## The reallocation commitment

A failed cycle's 342-unit Founder portion goes to the highest cumulative uptime
in that same window, shared equally among exact ties, restricted to seats that
met the cycle, with the integer remainder carried forward. The winner set is
therefore a property of the **window** and not of the failed seat: every seat
that fails in window `w` reallocates to the same set.

At the first height of window `w + 2`, when `uptime-measurement-v1` finalises
`w`, ordered block execution writes the window-result entry for `w`:

- `met_bitmap`, one bit per in-scope seat in ascending seat order;
- `winner_root`, the ordered Merkle root over the sorted winner seat IDs using
  the accepted tree shape and the labels
  `protocol-stack:v2:winner-empty`, `-leaf`, and `-node`;
- `winner_count`; and
- `unevaluated_count`, the number of seats whose 731-window span contains `w`
  and which have not yet exercised their cycle for `w`.

**The bitmap and the counter are over two different seat sets, and the
difference is load-bearing.** The bitmap covers every **in-scope** seat, which
has no upper bound: a seat past its own issuance span is still measured and may
still be a reallocation winner, so the winner set must be derived over all of
them. The counter covers only seats whose **span contains** `w`, because only
those have a cycle for `w` to exercise. Initialising the counter from the
in-scope set would leave it permanently above zero and the entry would never be
prunable.

Both sets are fixed at finalisation rather than moving afterwards. A seat is in
scope for `w` when it was activated strictly before `w`'s first height, and `w`
is finalised two windows later, so every such seat is already recorded.

An exercise of a failed cycle carries the winner list and the transition
recomputes `winner_root` over it, refusing any list that does not reproduce the
recorded root and count with `INVALID_WINNER_SET`.

The entry is deleted when `unevaluated_count` reaches zero. Its retention is
therefore bounded by the founder-directed schedule rather than by a policy: a
window is retained only while some seat may still exercise a cycle that maps to
it.

### Why the winner set is committed at finalisation and carried by the exercise

Three placements were considered and two fail on bounds that the accepted
artifacts already fix.

**Resolving the legs at evaluation, as the model does, is a population-scale
write.** The model stores one leg per winner inside the pending permission,
which at a fully tied window is 100,000 legs for a single evaluation.
`founder-economy-manifest-v2` states that an implementation "may not iterate
over all 100,000 seats inside an unrelated transition", and writing 100,000
state entries for one transaction is worse than iterating over them.

**Computing the winner set lazily, at the first failed evaluation in a window,
does not survive the retention bound.** `uptime-measurement-v1` retains two
windows of bitmaps, and a seat may exercise a cycle arbitrarily later, so the
evidence the computation needs would already be gone. Committing at finalisation
is what allows that specification's `RETAINED_WINDOWS = 2` storage bound to hold
unchanged; a lazy design would have silently required unbounded retention in a
neighbouring specification.

**Carrying the set in the exercise costs transaction size and no state.** At
full capacity and a fully tied window the list is 400,000 bytes and the signed
transaction is 400,170 bytes, inside the 1,048,576-byte canonical object bound
with room to spare. That is the dominant resource cost of this encoding and it
is stated rather than discovered later: the constitution expects ties at a
perfect cycle to be "the ordinary case", so the large list is the common case
and not an adversarial one.

A compact complement encoding — naming the seats that did *not* win — would be
much smaller in exactly that common case and is deliberately not offered,
because two encodings of one set is the non-minimal representation
`protocol-primitives-v1` forbids. The commitment is an ordered Merkle root
rather than a flat hash so that a later version can add a per-winner claim path
with a logarithmic membership proof **without changing the committed value**.
Whether a winner is credited by the failed seat's exercise or claims its own
share is a change to what a participant must do in order to be paid, so it is
not made here.

## Receipt

Each admitted transaction produces exactly one 56-byte receipt:

| Offset | Size | Field |
| ---: | ---: | --- |
| 0 | 4 | ASCII `PSRC` |
| 4 | 2 | receipt version `2` |
| 6 | 32 | transaction ID |
| 38 | 1 | transaction kind |
| 39 | 1 | result code |
| 40 | 8 | fee charged; the fixed fee on success, otherwise zero |
| 48 | 8 | issued atomic units; zero for every non-issuing kind and every failure |

Unknown result codes, a kind outside `1` through `6`, a nonzero failed fee, and
a nonzero `issued_atomic` on a failure are invalid. Receipt order is the
admitted transaction order. Receipts remain deterministic outputs and are still
not part of the state-root preimage.

Two fields are new. The **transaction kind** is present because result codes are
now produced by six transitions and a reader must be able to interpret a code
without re-fetching the transaction. The **issued atomic units** field is
present because the whole milestone is about a fixed maximum supply: a receipt
that commits to the units a transaction created makes the conservation claim
auditable per transaction rather than only per block.

Version one's 47-byte receipt is not extended in place. Its layout is fixed by
`ledger-transition-v1` and a reader that trusts the length would silently
misparse a longer one, so version two takes a new receipt version, which is the
mechanism that specification names.

## Result codes

One flat numeric space, so a code means one thing regardless of the kind that
produced it.

| Code | Name | Origin |
| ---: | --- | --- |
| 0 | `SUCCESS` | version one, frozen |
| 1 | `ZERO_AMOUNT` | version one, frozen |
| 2 | `FEE_LIMIT_TOO_LOW` | version one, frozen |
| 3 | `EXPIRED` | version one, frozen |
| 4 | `SENDER_NOT_FOUND` | version one, frozen |
| 5 | `NONCE_EXHAUSTED` | version one, frozen |
| 6 | `NONCE_MISMATCH` | version one, frozen |
| 7 | `DEBIT_OVERFLOW` | version one, frozen |
| 8 | `INSUFFICIENT_BALANCE` | version one, frozen |
| 9 | `UNAUTHORIZED` | new |
| 10 | `CYCLE_RANGE` | economy model |
| 11 | `INVALID_REFERRER` | economy model |
| 12 | `REPLAY` | economy model |
| 13 | `SEAT_NOT_ACTIVATED` | economy model |
| 14 | `WINDOW_NOT_FINAL` | new |
| 15 | `PERMISSION_NOT_FOUND` | economy model |
| 16 | `INVALID_WINNER_SET` | new |
| 17 | `INVALID_CHANNEL` | economy model |
| 18 | `MISSING_RESEARCH_INPUT` | economy model |
| 19 | `INVALID_RESEARCH_INPUT` | economy model |
| 20 | `NOT_ELIGIBLE` | economy model |
| 21 | `CHANNEL_CAP` | economy model |

Codes `0` through `8` keep their exact version-one meanings, so a version-one
reader that understands a code reads the same fact from a version-two receipt.
This is the third consequence of the shared envelope and is the reason the space
extends contiguously from `9` rather than starting a second range.

### The model mapping is total

Every one of `founder-economy-simulator-v3`'s twenty-four result codes has
exactly one disposition here, and the vectors require the three sets to
partition it.

| Disposition | Count | Codes |
| --- | ---: | --- |
| carried | 12 | `OK`, `CYCLE_RANGE`, `INVALID_REFERRER`, `REPLAY`, `SEAT_NOT_ACTIVATED`, `PERMISSION_NOT_FOUND`, `INVALID_CHANNEL`, `ZERO_AMOUNT`, `MISSING_RESEARCH_INPUT`, `INVALID_RESEARCH_INPUT`, `NOT_ELIGIBLE`, `CHANNEL_CAP` |
| guard | 2 | `ARITHMETIC_OVERFLOW`, `INVARIANT` |
| unrepresentable | 10 | `MISSING_UPTIME_RECORD`, `INVALID_UPTIME_RECORD`, `INCONSISTENT_UPTIME_RECORD`, `HEIGHT_RANGE`, `HEIGHT_NOT_MONOTONIC`, `WINDOW_BEFORE_ISSUANCE`, `WINDOW_AFTER_ISSUANCE`, `WINDOW_NOT_FOR_CYCLE`, `SEAT_NOT_IN_SCOPE`, `INCOMPLETE_UPTIME_RECORD` |

**The two guards do not become receipt codes.** `ledger-transition-v1` already
decides their treatment: a checked-arithmetic violation "is an internal
invariant failure that invalidates the proposed block, not a transaction
result". The model's two guard codes map onto that rule exactly, so version two
adds nothing and refuses to give a defect a receipt.

**The ten unrepresentable codes are the measure of what the encoding removed.**
Each is unreachable because its input does not exist in a transaction: eight
because the uptime record and the cycle window are read from state rather than
supplied, and two because the activation height is the block height. Recording
them as a set with a stated reason each is what keeps the removal auditable — a
later encoding that reintroduces a supplied record would have to move a code out
of this table rather than quietly widen an input.

## Invariants

Version one's state invariants hold, with one revised and one extended.

1. `total_supply <= supply_limit`.
2. checked addition of every account balance, the fee pool, **and every typed
   custody amount** equals `total_supply`.
3. account IDs are unique and strictly ordered in commitments, and economy keys
   are unique and strictly ordered in the economy tree.
4. every value fits its canonical integer width.
5. height never decreases.
6. the fixed fee never changes; **`total_supply` changes only by issuance and
   never decreases.**

Invariant 2's third term is empty on a version-one state, so version one's
invariant is the special case rather than a different rule. Invariant 6 is the
one version-one rule this version revises, and `ledger-transition-v1` names
exactly that revision as requiring a new transition version: "any later issuance
requires a new accepted transition version and native authorization rule."

The manifest's invariants hold at every accepted state:

```text
for each channel: issued_atomic + outstanding_atomic <= cap_atomic
total_supply = genesis_total_supply + checked_sum(channel.issued_atomic)
total_supply + checked_sum(channel.outstanding_atomic) <= supply_limit
checked_sum(typed_custody) = checked_sum(channel.issued_atomic)
```

and the version-three carry identity is unchanged:

```text
issued(founder_operator) + outstanding(founder_operator) + performance_carry
  = count(evaluated_permission_keys) * 34,200,000,000
```

There is no burn, no negative issuance, and no transition that decreases
`total_supply`, so the fixed maximum is a bound that only ever tightens.

## Resource limits and storage bounds

Version one's limits are unchanged: at most 65,535 raw inputs and 65,535
admitted transactions per block, and a 1,048,576-byte canonical object bound.

| Entry | Bound at 100,000 seats | Derivation |
| --- | ---: | --- |
| seats | 1,800,000 bytes | `100,000 * (5 + 13)` |
| channels | 180 bytes | `10 * (2 + 16)` |
| pending permissions | 584,800,000 bytes | `73,100,000 * (7 + 1)` |
| referral accruals | 511,700,000 bytes | `73,100,000 * (7 + 0)` |
| typed custody | 4,200,000 bytes | `100,000 * (34 + 8)` per beneficiary kind |
| performance carry | 9 bytes | one entry |
| window result | 12,553 bytes per retained window | `9 + 44 + 12,500` |

The pending-permission and referral figures are the founder-directed 73,100,000
seat-cycle population at its absolute ceiling, reached only if every seat
completes every cycle and no permission is ever exercised. They answer the
per-seat-balance part of requirement 12, and the typed-custody figure answers
the recipient-balance part; the per-cycle uptime-record part was answered by
`uptime-measurement-v1`.

**One bound is not a constant and is recorded rather than smoothed over.** The
number of retained window results is the number of windows that lie inside some
activated seat's 731-window span and still hold an unexercised cycle. If every
seat activates in one window that is 731 entries and about 9.2 MB; if
activations span `W` windows it is `W + 731` entries, and the constitution
places no bound on how long the sale may take. The growth is one 12,553-byte
entry per window, which is about 4.6 MB per year at the pinned three-second
commit interval, and it is bounded in practice by the same schedule rather than
by a rule. Requirement 15's independent review should see this figure.

The exercise transaction is the dominant transient cost at 400,170 bytes for a
fully tied window, as
[Why the winner set is committed at finalisation](#why-the-winner-set-is-committed-at-finalisation-and-carried-by-the-exercise)
derives.

## Determinism

Validation order, result numbers, receipt bytes, successful writes, and failure
atomicity are consensus rules. An implementation must not consult a wall clock,
locale, filesystem order, host integer width, database-native ordering, or
adapter-specific metadata, and must not use floating point on any monetary or
consensus path. Every monetary operation is checked `u64` arithmetic whose
violation invalidates the block.

No AI inference, external price, biometric result, or telemetry value is a
direct input to any transition defined here. The Ecosystem AI's only reach into
this surface is the bounded dispute of `uptime-measurement-v1`, which resolves
before a window is final and can only subtract.

## Compatibility boundary

This is requirement 6 stated exactly.

**Transaction bytes.** A version-one signed transfer is a version-two kind-1
transaction, byte-for-byte, with the same signing message, the same transaction
ID, and the same execution result numbers. A version-one node presented with
kinds 2 through 6 rejects them at admission step 1 as `MALFORMED_TRANSACTION`,
which is version one's existing rule for an unknown kind and is not changed. No
version-one byte sequence acquires a new meaning.

**State.** A version-two state is a version-one state plus one ordered economy
map. Every version-one invariant holds, with conservation extended by the typed
custody term, which is empty on a version-one state. The one revised rule is
that `total_supply` may increase by issuance, which `ledger-transition-v1`
already names as requiring a new transition version.

**Roots.** The version-two state root has a distinct domain label and a distinct
version field, so no version-one root is reinterpreted and no version-two root
collides with one. The accounts subtree construction is unchanged, so a
version-two root contains the version-one accounts root as a value.

**Genesis and chain identity.** Version-two genesis has a different schema
version, an additional manifest digest field, and a different chain-ID domain
label, so a version-two chain has a different chain ID from any version-one
chain. **A Founder Economy chain is therefore a new chain, not a migration of
the M1 devnet.** `protocol-primitives-v1` states that "a different genesis
creates a different chain ID; it is not a migration of this chain", and this
specification takes that path deliberately rather than defining an upgrade
block.

**Denomination.** The version-one devnet records nine decimal places and the
economy contract eight. This is not a conflict and requires no migration:
`ledger-transition-v1` states that "the symbol and decimal precision are display
metadata; atomic values alone enter canonical state", and both sides are
unsigned `u64` atomic. The two are different configurations of one canonical
integer type on two different chains. `founder-economy-manifest-v2` separately
fixes eight places as forced rather than chosen, because nine would require
56,993,950,100,000,000,000 atomic units and overflow `u64`.

**Supply limit.** Version one's 1,000,000,000,000,000,000 is a configured
genesis field marked "configured, nonzero", not a protocol constant, so the
founder maximum of 5,699,395,010,000,000,000 is a different configuration of the
same field rather than a violation of a version-one rule.

**What is not claimed.** No accepted M1 vector, digest, receipt, root, or
recorded devnet result changes, and none is recomputed under this specification.
The M1 chain continues to mean exactly what it meant, and this document defines
no transition that reads or writes it.

## Versioning and compatibility of this document

The envelope layout, the six kind identifiers and their bodies, the admission
order, the state key space and value encodings, the tree and root constructions,
the genesis layout, the receipt layout, the numeric result codes, and the
rejection orders are immutable for version two. A changed field, code, order, or
semantic rule requires a new transition version and an ADR; it must not
reinterpret a version-two identifier.

Version one and version two coexist. The v1 artifacts are the accepted M1
evidence and remain in place, passing, and unedited.

The three named authorization predicates are the only points at which this
version is deliberately incomplete. Accepting one of them adds a rule and
activates an already-specified path; it does not change any byte defined here.
That separation is intentional: it is what allows the encoding to be fixed and
verified now, while the reserved decisions stay reserved.

## What this specification does not establish

- **Which senders may act.** All three authorization predicates are named and
  undefined. Until `activation_authority` and `seat_authority` are decided, no
  seat can be activated and no permission can be evaluated, exercised, or
  accrued on a conforming chain, so the economy is encodable and not yet
  operable. This is the nearest blocking dependency of requirement 10.
- **Direct-channel eligibility.** Kind 6 is specified and refused. The founder
  decision is unchanged and still reserved.
- **That any of this executes.** No C++ implementation exists. This document is
  a contract, and requirement 10 is where it becomes behavior; requirement 11 is
  where a C++ and a Python implementation are required to agree on fixed bytes.
- **The measurement.** Everything `uptime-measurement-v1` does not establish is
  inherited unchanged: an answered challenge proves liveness of a responder
  rather than possession of a resource, duty reports are consumed rather than
  derived, and the beacon's bias is unreviewed. Encoding a record's consequences
  does not make the record sound.
- **The bootstrap.** A chain with no genesis allocation and a nonzero fee cannot
  execute its first transaction. A zero fee makes a devnet runnable and defers
  the production fee and funding path to the bridge milestone.
- **Distribution.** No kind here distributes transaction fees or commercial
  revenue to active seats, and no kind moves typed custody into a spendable
  account. `revenue-routing-v1` models the former and nothing models the latter.
- **The unreferred pool's payout.** Accrual is encoded; the month definition and
  the distribution remain unspecified.
- **Seat provenance.** A seat purchased in the Founder Seat sale model is still
  not proved to be an activated seat, and the per-principal bound is still not a
  per-human bound.

## Required vectors and evidence

`test-vectors/economy-transition-v2.txt` is normative. It fixes:

- the envelope decomposition, every kind's body layout, and every unsigned and
  signed length, including the winner-list bound at zero and at 100,000;
- **the kind-1 identity**, by requiring the version-two encoder to reproduce the
  accepted `protocol-primitives-v1` unsigned bytes, signed bytes, and
  transaction ID exactly;
- the cross-kind signature separation, by presenting each body under another
  kind's identifier and requiring rejection;
- every admission and execution rejection, each produced by a live run over a
  minimally mutated input with a positive control on the unmutated one;
- the complete result-code table, and the three-way partition of the economy
  model's twenty-four codes with each disposition's reason;
- every state key and value encoding, the empty, single, and multi-entry economy
  roots, and the version-two state root over an empty economy;
- **the non-collision of a version-one and a version-two root** over an
  identical account set and an empty economy, preceded by the requirement that
  the version-one construction the comparison uses reproduces the accepted
  `protocol-primitives-v1` account, state, and transaction roots exactly — a
  merely plausible restatement would make the non-collision trivially true;
- version-two genesis bytes, the chain ID, and the 21,843-entry bound at its
  accepting and rejecting values;
- the receipt layout, its invalid combinations, and its round trip; and
- the winner commitment, its recomputation from a supplied list, and its refusal
  of a list that is complete but reordered, short by one, long by one, or
  correct for a different window.

The verifier independently derives rather than restates every recorded value.
Its independence is `tools/economy-transition-vectors/expected.py`, which imports
nothing from `simulation/` and restates the version-one layouts, the Founder
Constitution's tables, and the accepted manifest's channel order by hand, so a
value both sources agree on has been reached from the accepted documents and
from the model independently. It fails when a recorded key is never derived,
when a derived key is absent from the file, and when any recorded value is
tampered with.

Acceptance requires full GitHub-hosted verification on the exact commit. Passing
these checks establishes an exact, auditable encoding and compatibility
boundary. It does not establish that the transitions execute, that the economy
is safe, that the authorization predicates are fillable, or that the resource
bounds are adequate under adversarial load; those are requirements 10, 13, and
15.
