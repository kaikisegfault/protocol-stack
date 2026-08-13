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
- the biometric verification signature that gates seat purchase and activation;
- the automatic per-cycle assignment the chain performs at a block boundary, and
  the accumulate-then-mint settlement it feeds;
- the canonical economy state key space and its value encodings;
- version-two genesis, chain identity, and the state-root construction;
- the version-two receipt and the complete numeric result-code space;
- the ordered rejection conditions of each new kind, and the total mapping from
  `founder-economy-simulator-v3`'s model codes onto them; and
- the exact compatibility boundary against M1 transaction bytes, state, and
  roots.

It does not define the C++20 kernel implementation, which is requirement 10; the
cross-language vectors that implementation must reproduce, which are requirement
11; the four-node adversarial scenarios, which are requirement 13; the external
payment that must precede a seat purchase, which is bridge work; the
distribution of transaction fees and commercial revenue to active seats, which
`revenue-routing-v1` models and no kind here performs; the withdrawal of typed
custody into a spendable account; the deterministic active-set protocol; or the
challenge content. One authorization predicate is named and deliberately left
undefined; it is described in [Authorization](#authorization) and in
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

The kind byte is what separates two kinds, not their length. Version two happens
to give every kind a distinct body length, so no two encodings collide by
accident, but a decoder must dispatch on the kind byte because a later version
may add a kind whose length coincides. A vector presents each body under another
kind's identifier and requires the signing message to change, which is what
makes a signature unusable across kinds.

## Transaction kinds

| Kind | Name | Body size | Unsigned | Signed |
| ---: | --- | ---: | ---: | ---: |
| 1 | `native_transfer` | 40 | 136 | 200 |
| 2 | `purchase_seat` | 165 | 261 | 325 |
| 3 | `activate_seat` | 68 | 164 | 228 |
| 4 | `mint_node` | 4 | 100 | 164 |
| 5 | `mint_referral` | 0 | 96 | 160 |
| 6 | `direct_issue` | 105 | 201 | 265 |

**Every kind is fixed-length and no two share a length.** Version two has no
variable-length body at all, which is a consequence of the settlement design in
[Cycle assignment](#cycle-assignment-and-settlement): nothing a transaction
carries scales with the seat population, so the largest transaction in the
protocol is 325 bytes. The distinct lengths are a derived property rather than a
design goal, and a decoder must still dispatch on the kind byte rather than on
the length, because a future kind may coincide.

### Kind 2 — `purchase_seat`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 4 | seat ID `u32` | `0` through `99,999` |
| 84 | 32 | biometric identity hash | 32 octets |
| 116 | 32 | purchaser account ID | 32 octets |
| 148 | 1 | has referrer `bool` | `0x00` or `0x01` |
| 149 | 32 | referrer account ID | 32 octets, or 32 zero octets when absent |
| 181 | 64 | biometric verification signature | Ed25519 over the enrollment message |

A `has_referrer` of `0x00` requires 32 zero octets in the referrer field. Any
other value is a second encoding of "no referrer", which
`protocol-primitives-v1` forbids as a non-minimal representation, and is
`MALFORMED_TRANSACTION`.

**The seat record and the biometric binding are written in one transition.** The
purchase cannot be separated from the identity registration: there is no
transaction that records a seat without a biometric hash, and none that attaches
one afterwards, so a seat with no biometric identity is unrepresentable rather
than merely disallowed.

**The referrer is an account, not a seat.** The Founder Constitution leaves open
"whether a referrer must itself hold a Founder Seat"; the founder decision of
2026-08-13 settles it — a referrer is a user participating in the incentive
programme, and holding a seat is neither required nor relevant. The referral
channel is therefore keyed by an account identifier throughout, and a seat
identifier never appears on the referral path.

**What is deliberately absent is the payment.** No field here proves that BTC,
ETH, or an approved stablecoin was received, because that proof is a bridge
commitment and the bridge is a later milestone. The transition records what the
chain owns — the seat, the identity hash, the purchaser, and the referrer — and
the external settlement that must precede it is named in
[What this specification does not establish](#what-this-specification-does-not-establish).

### Kind 3 — `activate_seat`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 4 | seat ID `u32` | `0` through `99,999` |
| 84 | 64 | biometric verification signature | Ed25519 over the activation message |

Activation is **one-time and permanent**. It carries no referrer, because the
referrer was recorded at purchase, and no activation height, because the height
is the executing block's. It starts the seat's 731 cycles and is the only
transition that does.

**A seat may stay purchased and un-activated indefinitely.** Nothing expires a
purchased seat and nothing activates one on the founder's behalf, so the seat
record carries an activation height only once activation has happened.

### Kind 4 — `mint_node`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 4 | seat ID `u32` | `0` through `99,999` |

**One button, everything, no quantity.** The transaction names a seat and
nothing else. It mints every permission the seat has accumulated and not yet
minted — its own met cycles and every reallocation share it won — and there is
no field by which a founder could mint part of it. That is founder-directed and
is the reason the body is four bytes: a quantity field would be a way to express
a choice the rule does not offer.

### Kind 5 — `mint_referral`

The body is empty. The transaction mints every referral permission accumulated
to the **sender's own account**, so it names no seat and no beneficiary: the
signer is the beneficiary, and there is nothing else to say.

**Referral is a separate pool with a separate button, and that is
founder-directed.** A Founder Seat and a referrer are different roles even when
one person holds both; the referral accrues through a direct-mint channel on the
referred seat's schedule and does not depend on any node's activity. Folding it
into `mint_node` would tie a user's referral earnings to a seat they may not
hold.

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
`founder_referral`, is **not** admissible: it is consumed exactly by the daily
referral assignment and kind 5, and admitting it here would mint referral units
outside that accounting. Indices `0` through `4` are Founder Node distribution
channels and are not direct-mint. Any other value is `INVALID_CHANNEL`.

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

### There is no transaction that records a day

Version two has no transaction by which anyone reports, claims, or evaluates a
cycle. **The chain writes each cycle's outcome itself**, at a block boundary,
for every activated seat at once. See
[Cycle assignment](#cycle-assignment-and-settlement).

That is founder-directed and it removes an entire authorization question rather
than answering one: a transition nobody submits has no sender to authorize, no
fee to pay, and no liveness dependency on an operator remembering to press
something. An earlier draft of this specification had a submitted
`evaluate_base_permission` transaction, and it was wrong.

## Admission

Admission operates on raw transaction bytes before ledger state is read, and its
version-one steps are unchanged in order and in meaning:

1. decode exactly one signed version-two transaction with no trailing bytes;
2. require the configured chain ID;
3. derive the sender account ID from the encoded public key;
4. strictly verify the Ed25519 signature over the signing message.

Step 1 classifies a wrong magic, schema version, transaction kind, or
signature-scheme identifier, a length that is not the exact length its kind
requires, a `has_referrer` byte that is not `0x00` or `0x01`, or a non-minimal
absent-referrer encoding as `MALFORMED_TRANSACTION`. The admission codes are
version one's, unchanged:

| Code | Name |
| ---: | --- |
| 1 | `MALFORMED_TRANSACTION` |
| 2 | `WRONG_CHAIN` |
| 3 | `INVALID_SIGNATURE` |

Because every kind is fixed-length, step 1 needs no length arithmetic beyond a
table lookup on the kind byte, and there is no count field anywhere in version
two that a decoder must bound before allocating.

**A bounded numeric field outside its range is not an admission failure.** A
seat ID of `100,000` decodes to a well-formed `u32` and is refused at execution
with `CYCLE_RANGE`. Admission is defined to perform no state read and to produce
no receipt, so classifying a range violation there would remove its receipt and
its place in the ordered transaction root, and a submitter's invalid seat ID
would leave no canonical trace. Shape belongs to admission and value belongs to
execution.

**The biometric verification signature is not checked at admission.** It
verifies against the ecosystem verifier key, which is ledger state, and
admission is defined to read none. It is therefore an execution condition
returning `UNAUTHORIZED`, and it produces a receipt — which is what a founder
whose enrollment signature expired needs in order to see why.

Admission failures perform no state read or write, produce no application
receipt, and do not enter the application transaction root, exactly as in
version one.

## Authorization

Every kind is signed by an account, and every kind charges that account the
fixed fee. The Founder Constitution decides that fees apply here: "Every
protocol transaction fee is charged separately ... whether the transaction is a
purchase, transfer, issuance exercise, or another accepted state transition."

The founder decision of 2026-08-13 settles two of the three predicates this
surface needs. The third is unchanged and still reserved.

| Kind | Signer | Second factor |
| ---: | --- | --- |
| 1 | any account | none |
| 2 | any account | biometric verification signature, required |
| 3 | the seat's recorded purchaser account | biometric verification signature, required |
| 4 | the seat's recorded purchaser account | none |
| 5 | the account being paid | none |
| 6 | refused | the predicate is reserved |

A sender the applicable rule refuses is `UNAUTHORIZED`.

### The biometric verification signature

Kinds 2 and 3 carry a 64-byte Ed25519 signature by the **ecosystem verifier
key**, a genesis-configured public key, over a domain-separated message binding
the exact action:

```text
enrollment_message =
  D("protocol-stack:v2:seat-enrollment") ||
  chain_id || u32(seat_id) || biometric_identity_hash ||
  purchaser_account_id || u64(valid_until_height)

activation_message =
  D("protocol-stack:v2:seat-activation") ||
  chain_id || u32(seat_id) || purchaser_account_id || u64(valid_until_height)
```

The verification is performed by the chain against the recorded verifier key
using the same strict Ed25519 rules `protocol-primitives-v1` fixes for
transaction signatures. **No biometric image, template, or private linkage datum
enters consensus** — the chain sees a hash and a signature over it, which is
what the constitution requires when it says raw images and private linkage data
"do not become ordinary public blockchain data".

Each message binds the chain, the seat, the purchaser, and an expiry, so a
verifier signature is **action-bound**: it cannot be replayed onto another seat,
another purchaser, another chain, or a later attempt after expiry. That is the
"fresh, action-bound biometric approval" the constitution requires, expressed as
bytes.

`valid_until_height` in each message is the transaction's own trailer value, so
the verifier signature and the transaction expire together and neither outlives
the other.

**This makes the ecosystem verifier a gate on entry and never on payment.** It
signs purchases and activations; it signs no mint. If the verifier is
unavailable, no new seat can be bought or activated and **every existing seat
continues to earn and to mint unaffected**. That is the containment direction
the constitution insists on when it refuses to make an off-chain signature a
precondition for income, and it is why kinds 4 and 5 carry no second factor: a
stolen wallet key can mint, but it can only mint to the seat's own recorded
account, so it redirects nothing.

### What is still reserved

`direct_issue_authority` is unchanged and remains founder-reserved: the
eligibility and anti-abuse mechanics for the four undecided direct-mint
channels. Kind 6 is therefore specified and refused rather than given an
invented predicate.

`founder-economy-simulator-v3` records the boundary this specification now
crosses: "Nothing here proves that a seat paid for a position, enrolled, passed
biometric verification, or is a distinct human, and nothing here decides which
transition supplies the height." Kinds 2 and 3 supply the height and the
enrollment binding. What remains outside is the *payment* — the external
settlement that must precede a purchase — which is bridge work.

## Canonical economy state

The version-two ledger state is version one's state — chain ID, supply limit,
total supply, fixed fee, height, fee pool, and the ordered account map — plus one
ordered map from canonical byte keys to canonical byte values.

A key is `u8(entry_kind)` followed by fixed-width big-endian fields, so
unsigned lexicographic key order is total and unambiguous and no key is a prefix
of another with a different meaning.

| Kind | Entry | Key | Key bytes | Value | Value bytes |
| ---: | --- | --- | ---: | --- | ---: |
| 1 | seat | `u8(1) \|\| seat_id:u32` | 5 | see below | 106 |
| 2 | channel | `u8(2) \|\| channel_id:u8` | 2 | `issued_atomic:u64 \|\| outstanding_atomic:u64` | 16 |
| 3 | cycle assignment | `u8(3) \|\| cycle_window:u64` | 9 | see below | 24 + 2⌈n/8⌉ |
| 4 | referral balance | `u8(4) \|\| account_id:bytes<32>` | 33 | `accrued_atomic:u64 \|\| minted_atomic:u64` | 16 |
| 5 | direct decision | `u8(5) \|\| decision_id:bytes<32>` | 33 | *(empty)* | 0 |
| 6 | typed custody | `u8(6) \|\| beneficiary_kind:u8 \|\| beneficiary_id:bytes<32>` | 34 | `amount_atomic:u64` | 8 |
| 7 | carry | `u8(7) \|\| channel_id:u8` | 2 | `carry_atomic:u64` | 8 |
| 8 | verifier key | `u8(8)` | 1 | `ed25519_public_key:bytes<32>` | 32 |

An entry kind outside `1` through `8` cannot occur, because no transition writes
one and the state is not an untrusted input.

### The seat record

```text
biometric_identity_hash : bytes<32>
purchaser_account_id    : bytes<32>
has_referrer            : u8
referrer_account_id     : bytes<32>
is_activated            : u8
activation_height       : u64
minted_through_window   : u64
```

106 bytes. Three of its fields are the shape of the founder decision of
2026-08-13 and were absent from the first draft of this specification.

**Identity is present from the first byte of the seat's existence.** The hash and
the purchaser are written by the same transition that creates the record, so a
seat with no biometric binding is unrepresentable rather than disallowed.

**Activation is a flag, not an inferred sentinel.** `is_activated` is `0x00` or
`0x01`; `activation_height` must be zero while it is `0x00`. A purchased seat
that has never been activated is an ordinary, permanent state — nothing expires
it — so "not yet activated" needs its own representation rather than borrowing
height zero, which is a real height.

**`minted_through_window` is the whole of the mint bookkeeping.** Because a mint
takes everything and cannot take part of it, one high-water mark answers what a
seat has already collected. There is no per-cycle permission record, no
per-cycle replay key, and no set of exercised keys: the mark is the replay
protection, and a second mint at the same height simply finds nothing to take.

That is a direct consequence of the founder rule. A mint that could take a chosen
quantity would need to record which cycles were taken, and the natural encoding
of that is one entry per seat-cycle — 73,100,000 entries at capacity. The rule
that there is no quantity choice is what collapses it to eight bytes per seat.

**The referrer is an account and the seat table is not on the referral path.**
`referrer_account_id` is a 32-byte account, because a referrer is a user
participating in the incentive programme rather than a seat holder.

### The cycle assignment record

```text
share_per_winner_atomic : u64
winner_count            : u32
in_scope_count          : u32
met_bitmap              : one bit per in-scope seat, ascending seat order
winner_bitmap           : one bit per in-scope seat, ascending seat order
```

One record per cycle, written once, by the chain. At the 100,000-seat capacity
each bitmap is 12,500 bytes and the record is 25,024 bytes.

**This one record replaces every per-seat write the assignment would otherwise
need.** A cycle in which one seat fails owes a share to every seat that tied at
the best uptime, which on an ordinary day is nearly the whole population.
Crediting them individually is 100,000 state writes for one failed seat, and a
founder who has saved up many failed cycles would settle millions of them in a
single mint. Recording who won, and how much each won, lets a seat compute its
own entitlement when it mints.

**A seat reads its own bits, so a mint is bounded by the seat's own history.**
`mint_node` walks the windows after `minted_through_window`, and for each one
reads two bits: whether this seat met that cycle, and whether it won a share of
someone else's. Both are `O(1)` lookups into a record the chain already holds.

The bitmaps cover the **in-scope** set, which has no upper bound: a seat past its
own 731 cycles still runs a node, is still measured, and may still win. The met
bit and the winner bit are therefore defined for every in-scope seat, while only
seats whose span contains the window have a base permission of their own to
collect.

### What is no longer state

**There is no pending-permission entry.** The first draft stored one verdict byte
per seat-cycle, up to 73,100,000 entries. The verdict now lives as one bit inside
its cycle's record, so the same fact costs one bit instead of eight bytes and is
stored once per cycle rather than once per seat-cycle.

**There is no winner commitment and no winner list in any transaction.** The
first draft committed to the winner set and required an exercise to carry it,
reaching 400,170 bytes for a fully tied cycle. The winner bitmap makes the set
readable from state, so the largest transaction in version two is 325 bytes.

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
| ecosystem verifier key | `bytes<32>` | canonical Ed25519 public key |
| account count | `u32` | `0` through `21,843` |
| accounts | repeated 48-byte state entries | exactly `account count` entries |

```text
chain_id = H(D("protocol-stack:v2:chain-id") || canonical_genesis_v2_bytes)
```

Genesis writes the ten channel entries with both amounts zero, the ten carry
entries with zero, and the ecosystem verifier key. It writes nothing else: never
a seat, a referral balance, a custody entry, or a cycle assignment.

**The verifier key is genesis state, not a configured constant.** It is what
kinds 2 and 3 check their biometric signatures against, so a chain that does not
carry one can admit no seat at all. Placing it in genesis puts it inside the
chain ID, which means a chain with a different verifier key is a different chain
rather than the same chain trusting a different verifier. No transition in
version two rotates it; rotation needs an authorization rule that does not exist
yet and is named in
[What this specification does not establish](#what-this-specification-does-not-establish).

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

The genesis prefix through `account count` is 110 bytes — version one's 46 plus
the manifest digest and the verifier key — so the 1,048,576-byte canonical object
bound admits at most 21,843 entries:

```text
110 + 48 * 21,843 = 1,048,574   accepted
110 + 48 * 21,844 = 1,048,622   rejected
```

A decoder must reject a declared count above 21,843 before allocating account
storage. Version one's bound is 21,844 against its 46-byte prefix, so version two
loses exactly one entry despite adding 64 bytes: the accepting case clears the
bound by two bytes. Every figure here is derived rather than recorded, which is
what makes the two-byte margin a checked fact rather than a lucky one.

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

### Kind 2 — purchase seat

Rejection conditions, in this order:

1. a `seat_id` outside `0..99,999` is `CYCLE_RANGE`;
2. an already-purchased `seat_id` is `REPLAY`;
3. a `referrer_account_id` equal to the `purchaser_account_id` is
   `INVALID_REFERRER`;
4. a biometric verification signature that does not verify against the recorded
   verifier key over the enrollment message is `UNAUTHORIZED`.

On success the transition writes the seat record with `is_activated` false,
`activation_height` zero, and `minted_through_window` zero. It issues nothing,
reserves nothing, and credits nothing.

**The signature is checked last among these, and that is deliberate.** The three
conditions before it are properties of the transaction and the seat table, so a
defect in the request is reported as a defect in the request. Checking the
verifier signature first would report every malformed purchase as an
authorization failure and would make the two indistinguishable to a submitter
fixing a bug.

**Self-referral is refused, and it is the only referral condition here.** Nothing
requires a referrer to exist, to hold a seat, or to have been referred
themselves. The constitution's open question — whether a referrer must itself
hold a Founder Seat — was settled in the negative on 2026-08-13, so there is no
condition to encode.

### Kind 3 — activate seat

Rejection conditions, in this order:

1. a `seat_id` outside `0..99,999` is `CYCLE_RANGE`;
2. an unpurchased `seat_id` is `SEAT_NOT_PURCHASED`;
3. a sender other than the seat's recorded `purchaser_account_id` is
   `UNAUTHORIZED`;
4. an already-activated seat is `REPLAY`;
5. a biometric verification signature that does not verify against the recorded
   verifier key over the activation message is `UNAUTHORIZED`.

On success the transition sets `is_activated` and writes `activation_height` as
the executing block height. It issues nothing.

**Activation is permanent and has no inverse.** No transition clears
`is_activated`, moves `activation_height`, or re-activates a seat, so the 731
cycles a seat receives are fixed by one irreversible event. `REPLAY` is what
makes that true rather than a convention.

**`HEIGHT_RANGE` and `HEIGHT_NOT_MONOTONIC` are unrepresentable.** The model
takes an activation height as an input and must bound it and enforce that it
never decreases. Here the height is the executing block's, which
`ledger-transition-v1` already fixes as the sole successor of the previous height
and invalidates the block on overflow.

### Kind 4 — mint node

Rejection conditions, in this order:

1. a `seat_id` outside `0..99,999` is `CYCLE_RANGE`;
2. an unpurchased `seat_id` is `SEAT_NOT_PURCHASED`;
3. an unactivated seat is `SEAT_NOT_ACTIVATED`;
4. a sender other than the seat's recorded `purchaser_account_id` is
   `UNAUTHORIZED`;
5. nothing accumulated since `minted_through_window` is `NOTHING_TO_MINT`;
6. a leg that does not fit its channel is `CHANNEL_CAP`.

On success the transition walks every assigned cycle after
`minted_through_window` up to the last assigned one, and for each:

- if the window lies in the seat's own 731-cycle span and the seat's met bit is
  set, it settles that cycle's full base permission — the four escrow and
  System Creator legs to their own beneficiaries and 34,200,000,000 atomic units
  to the seat's custody;
- if the seat's winner bit is set, it settles its equal share of every failed
  seat's permission for that cycle, with each of the five legs divided by the
  winner count, so the escrows and the System Creator receive their portions at
  this mint rather than at a mint the failed seat may never make.

It then sets `minted_through_window` to the last assigned window, credits typed
custody, moves each leg from `outstanding_atomic` to `issued_atomic`, and
increases `total_supply` by the total minted. It is atomic: every beneficiary is
credited or none is.

**A failed seat's own cycle contributes nothing to its own mint.** The whole
permission moved to that cycle's winners when the cycle was assigned, which is
what makes the escrows independent of whether the failed founder ever mints. The
constitution's rule that a failed cycle's Founder portion "cannot be recovered
later" by the original seat is preserved exactly, and its statement that
reallocation settles "when the failed seat next exercises a permission" is
superseded by the founder decision of 2026-08-13, which settles at the winner's
mint instead. The reason the owner gave for the change is the reason to record:
a failed seat that never mints must not be able to withhold the escrows' and the
winners' value indefinitely.

**`NOTHING_TO_MINT` is a result, not a no-op.** A mint that found nothing writes
no state and charges no fee, so a repeated mint is refused rather than silently
accepted, and the receipt says which it was.

### Kind 5 — mint referral

Rejection conditions, in this order:

1. no referral balance for the sender, or an accrued total equal to the minted
   total, is `NOTHING_TO_MINT`;
2. a leg that does not fit the channel is `CHANNEL_CAP`.

On success the transition mints the whole outstanding difference to the sender's
custody, sets `minted_atomic` equal to `accrued_atomic`, and increases
`total_supply`.

**There is no seat and no authorization check.** The signer is the beneficiary,
so there is nobody else the transition could pay and nothing to authorize.

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

## Cycle assignment and settlement

**No transaction records a cycle.** At the first height of window `w + 2`, when
`uptime-measurement-v1` finalises window `w`, ordered block execution writes
window `w`'s cycle-assignment record and nothing else does.

The transition, in order:

1. derive the in-scope seat set for `w` from the seat table;
2. set each seat's met bit from the finalised measurement;
3. derive the winner set — the seats at the highest uptime among those that met
   the cycle — and set their bits;
4. compute the per-winner share of one failed seat's permission by dividing each
   of the five legs by the winner count, adding each leg's remainder to that
   channel's carry;
5. add one base permission's `outstanding_atomic` per in-scope seat whose span
   contains `w`, so the channel liability is recorded when the permission is
   assigned rather than when it is minted.

**Assignment is one automatic event per cycle, in cycle order, and it is
founder-directed.** The chain evaluates the cycle and assigns the permissions
itself; nothing is claimed, requested, or reported. That removes an entire
authorization question rather than answering one, and it means a founder who
never touches the dashboard still accrues everything they are owed.

### The two-cycle lag is forced, not chosen

The assignment for cycle `w` cannot execute at the end of `w`. A cycle's uptime
is not final until its Ecosystem AI dispute window has expired, which
`uptime-measurement-v1` fixes at the whole of window `w + 1`, so the earliest
height at which `w`'s outcome is known is the first height of `w + 2`.

Assigning earlier would mean assigning against a result a dispute could still
change, and the only ways to avoid the lag are to remove the dispute window,
which the constitution requires, or to assign provisionally and revise, which
would make a mint's value depend on when it happened. The lag is therefore a
consequence of a founder-directed rule rather than a design choice, and it costs
a seat at most two cycles of delay on value that is never lost.

### Nothing is left unassigned

Every in-scope seat whose span contains the cycle produces exactly one base
permission, so the total assigned per cycle is the number of such seats times
57,430,000,000 atomic units, and the Founder Node distribution channels are
consumed exactly when all 100,000 seats complete all 731 cycles:

```text
57,430,000,000 * 100,000 * 731 = 4,198,133,000,000,000,000
```

which is the accepted manifest's Founder Node subtotal. **A failed cycle removes
nothing from the total** — it moves the whole permission to that cycle's winners
— and the integer remainder of each equal split is carried forward per channel
rather than dropped, so no atomic unit is unassigned at any point.

If no seat met the cycle, the winner set is empty and the whole permission is
carried forward, which is the founder-directed rule for that case.

**An unminted permission is not an unassigned one.** A seat that never mints
leaves its value recorded and unspent forever, which the constitution intends:
until a permission is minted its units do not exist and are not circulating.

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
| 14 | `SEAT_NOT_PURCHASED` | new |
| 15 | `NOTHING_TO_MINT` | new |
| 16 | `INVALID_CHANNEL` | economy model |
| 17 | `MISSING_RESEARCH_INPUT` | economy model |
| 18 | `INVALID_RESEARCH_INPUT` | economy model |
| 19 | `NOT_ELIGIBLE` | economy model |
| 20 | `CHANNEL_CAP` | economy model |

Codes `0` through `8` keep their exact version-one meanings, so a version-one
reader that understands a code reads the same fact from a version-two receipt.
This is the third consequence of the shared envelope and is the reason the space
extends contiguously from `9` rather than starting a second range.

The three new codes are each a condition the research model cannot have.
`UNAUTHORIZED` is a sender the transition refuses, which a model with no signer
never sees. `SEAT_NOT_PURCHASED` distinguishes a seat that does not exist from
one that exists and has not been activated, a distinction the model has no
purchase transition to make. `NOTHING_TO_MINT` is what a take-everything mint
returns when everything is already taken, replacing the per-cycle key lookup the
model performs.

### The model mapping is total

Every one of `founder-economy-simulator-v3`'s twenty-four result codes has
exactly one disposition here, and the vectors require the three sets to
partition it.

| Disposition | Count | Codes |
| --- | ---: | --- |
| carried | 11 | `OK`, `CYCLE_RANGE`, `INVALID_REFERRER`, `REPLAY`, `SEAT_NOT_ACTIVATED`, `INVALID_CHANNEL`, `ZERO_AMOUNT`, `MISSING_RESEARCH_INPUT`, `INVALID_RESEARCH_INPUT`, `NOT_ELIGIBLE`, `CHANNEL_CAP` |
| guard | 2 | `ARITHMETIC_OVERFLOW`, `INVARIANT` |
| unrepresentable | 11 | `MISSING_UPTIME_RECORD`, `INVALID_UPTIME_RECORD`, `INCONSISTENT_UPTIME_RECORD`, `PERMISSION_NOT_FOUND`, `HEIGHT_RANGE`, `HEIGHT_NOT_MONOTONIC`, `WINDOW_BEFORE_ISSUANCE`, `WINDOW_AFTER_ISSUANCE`, `WINDOW_NOT_FOR_CYCLE`, `SEAT_NOT_IN_SCOPE`, `INCOMPLETE_UPTIME_RECORD` |

**The two guards do not become receipt codes.** `ledger-transition-v1` already
decides their treatment: a checked-arithmetic violation "is an internal
invariant failure that invalidates the proposed block, not a transaction
result". The model's two guard codes map onto that rule exactly, so version two
adds nothing and refuses to give a defect a receipt.

**The eleven unrepresentable codes are the measure of what the encoding
removed.** Each is unreachable because its input does not exist in a
transaction:

- five because the uptime record is state the chain writes rather than an input
  anyone supplies — `MISSING_UPTIME_RECORD`, `INVALID_UPTIME_RECORD`,
  `INCONSISTENT_UPTIME_RECORD`, `SEAT_NOT_IN_SCOPE`, and
  `INCOMPLETE_UPTIME_RECORD`;
- three because the cycle window is derived from the seat's own schedule rather
  than presented — the three `WINDOW_` codes;
- two because the activation height is the executing block height —
  `HEIGHT_RANGE` and `HEIGHT_NOT_MONOTONIC`;
- and one because a mint takes everything, so there is no per-cycle key to miss
  — `PERMISSION_NOT_FOUND`.

Recording them as a set with a reason each is what keeps the removal auditable.
A later encoding that reintroduces a supplied record, a submitted window, or a
partial mint would have to move a code out of this table rather than quietly
widen an input.

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

and the carry identity holds per channel, restated for an assignment that is
per cycle rather than per evaluated key:

```text
for each Founder Node channel c, with leg(c) its per-cycle amount:
  issued(c) + outstanding(c) + carry(c)
    = assigned_cycle_permissions * leg(c)
```

where `assigned_cycle_permissions` is the number of base permissions the chain
has assigned across every cycle so far — one per in-scope seat whose span
contains that cycle. The model states the same identity over
`count(evaluated_permission_keys)`, which is the same quantity counted at the
event that produced it rather than at the cycle that assigned it.

It is an equality rather than a bound, because a bound would admit a defect that
lost carried value. Extending it from the one Founder-operator channel the model
tracks to all five is forced by the settlement rule: a failed cycle's whole
permission moves to the winners, so every leg is divided by the winner count and
every leg can leave a remainder, not only the operator leg.

There is no burn, no negative issuance, and no transition that decreases
`total_supply`, so the fixed maximum is a bound that only ever tightens.

## Resource limits and storage bounds

Version one's limits are unchanged: at most 65,535 raw inputs and 65,535
admitted transactions per block, and a 1,048,576-byte canonical object bound.

**The largest transaction in version two is 325 bytes.** Nothing a transaction
carries scales with the seat population, so no transaction-size bound is close
to binding and a block's economy content is bounded by its transaction count
alone.

| Entry | Bound at 100,000 seats | Derivation |
| --- | ---: | --- |
| seats | 11,100,000 bytes | `100,000 * (5 + 106)` |
| channels | 180 bytes | `10 * (2 + 16)` |
| referral balances | 49 bytes per referrer | `33 + 16` |
| typed custody | 4,200,000 bytes | `100,000 * (34 + 8)` per beneficiary kind |
| carries | 180 bytes | `10 * (2 + 8)` |
| verifier key | 33 bytes | one entry |
| cycle assignment | 25,033 bytes per cycle | `9 + 24 + 2 * 12,500` |

The seat and custody figures answer the per-seat-balance and recipient-balance
parts of requirement 12; the per-cycle uptime-record part was answered by
`uptime-measurement-v1`.

**The per-seat-cycle population has left the state entirely.** The first draft of
this specification stored one entry per seat-cycle — 73,100,000 entries and
about 585 MB of pending permissions plus 512 MB of referral accruals. The founder
rule that a mint takes everything with no quantity choice collapses both to a
single high-water mark per seat and a single accrued-versus-minted pair per
referrer. **That is the largest single consequence of the founder decision on
this encoding**, and it was not available to a design in which a founder could
mint a chosen amount.

**One bound is not a constant, and it is the weakest result here.** Cycle
assignment records accumulate at one per cycle and are never deleted, because a
seat may mint at any time and must be able to walk every cycle it has not yet
collected. At full capacity that is 25,033 bytes per cycle, about 9.1 MB per year
at the pinned three-second commit interval, and 6.7 GB over a century.

Three mitigations exist and each is refused, so the growth is stated rather than
solved:

- expiring an uncollected cycle would bound it exactly and would decide a seat's
  entitlement by inaction, which the constitution does not do;
- pruning a cycle once every in-scope seat has minted past it would work, but a
  seat that never mints holds every record after its own last mint forever, so
  the worst case is unchanged;
- compressing a cycle whose met and winner bitmaps are both all-ones — the
  ordinary perfect day — would shrink the common case by a large factor and is a
  genuine optimization, but it introduces a second encoding of one record, which
  is the non-minimal representation `protocol-primitives-v1` forbids.

**This is the one place in the specification where the encoding is bounded by
expected behavior rather than by a rule**, and requirement 15's independent
review should see it as such. The third option is the one worth revisiting, and
doing it properly means giving the record a single canonical encoding with a
run-length form rather than two alternative forms.

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

- **Direct-channel eligibility.** One authorization predicate remains named and
  undefined, and kind 6 is refused because of it. The founder decision is
  unchanged and still reserved. Every other predicate was settled on 2026-08-13,
  so purchase, activation, and both mints are fully specified.
- **The payment.** Nothing here proves that BTC, ETH, or an approved stablecoin
  was received for a seat. `purchase_seat` records the seat, the identity hash,
  the purchaser, and the referrer; the external settlement that must precede it
  is a bridge commitment and the bridge is a later milestone. Until then a
  conforming chain records purchases that its own rules cannot show were paid
  for.
- **Verifier key rotation.** The ecosystem verifier key is written at genesis
  and no transition changes it, so a compromised or retired verifier key can only
  be replaced by a new chain. Rotation needs an authorization rule — who may
  rotate, under what approval, and what happens to signatures already issued —
  and that rule decides who controls admission to the economy, so it is not
  invented here. Until it exists, the key is effectively permanent.
- **That the biometric hash means anything.** The chain verifies a signature by
  a configured key over a hash. Whether that key belongs to a sound verifier,
  whether the hash was derived from a live human, whether one human holds at
  most 1,000 seats, and whether the enrollment is unlinkable are all outside
  consensus by design, and the constitution's own threat-model and independent
  review requirements for biometric capture are untouched by anything here.
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
- **The unreferred pool's payout.** A seat purchased without a referrer
  contributes its per-cycle referral allocation to the unreferred performance
  pool. The accrual is encoded; the month definition and the pool's distribution
  remain unspecified, so that value accumulates against a payout rule that does
  not exist yet.
- **Seat concentration.** The per-principal 1,000-seat bound the constitution
  fixes is not enforced by any transition here, because enforcing it requires
  knowing that two biometric hashes belong to one human, which is exactly what
  the chain cannot see.

## Required vectors and evidence

`test-vectors/economy-transition-v2.txt` is normative. It fixes:

- the envelope decomposition, every kind's body layout, and every unsigned and
  signed length, including that no two kinds share one;
- **the kind-1 identity**, by requiring the version-two encoder to reproduce the
  accepted `protocol-primitives-v1` unsigned bytes, signed bytes, and
  transaction ID exactly;
- the cross-kind separation, by presenting each body under another kind's
  identifier and requiring the signing message to change;
- every admission and execution rejection, each produced by a live run over a
  minimally mutated input with a positive control on the unmutated one;
- the two biometric message constructions, and that a verifier signature bound
  to one seat, purchaser, chain, or expiry is refused on any other;
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
- the receipt layout, its invalid combinations, and its round trip;
- the cycle assignment: the met and winner bitmaps over a population that
  exercises a failed seat, a tie at the maximum, a seat that met below the
  maximum, and a seat outside its own span but still in scope; the per-winner
  share and every leg's carried remainder; and the empty-winner case in which
  the whole permission carries forward; and
- the mint walk: that a seat collects exactly its own met cycles and its own
  winner shares, that `minted_through_window` advances to the last assigned
  cycle, that an immediate second mint returns `NOTHING_TO_MINT`, and that the
  five legs of an acquired permission reach the escrows and the System Creator
  at the winner's mint rather than the failed seat's.

The conservation vectors are the load-bearing ones. Across a complete assignment
and mint sequence, every channel's `issued + outstanding + carry` must equal the
number of assigned permissions times that channel's per-cycle leg, exactly, and
the sum of typed custody must equal issued supply. A settlement defect that
moved value between beneficiaries would satisfy a per-transaction check and fail
this one.

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
is safe, that a purchase was paid for, that a biometric hash means anything, or
that the resource bounds are adequate under adversarial load; those are
requirements 10, 13, and 15 and the bridge and identity milestones.
