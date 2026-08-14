# Economy transition v4

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
The change is classified as authority, encoding, state-transition shape, and
compatibility.
[ADR 0036](../decisions/0036-economy-transition-v4-hub-as-the-identity-root.md)
records the alternatives and the decision.

**Version four exists because the founder direction of 2026-08-14 makes HUB
verification the root of identity.**
[ADR 0035](../decisions/0035-founder-answers-on-payout-the-cap-and-hub-recovery.md)
records that direction and the answers that complete it.
[`economy-transition-v3`](economy-transition-v3.md) is not edited: it is the
accepted record of what was verified on 2026-08-14, its 579 vectors and their
digests are that evidence, and the repository's rule is that a changed
transition is a new version rather than an edit.

## What version four changes

| | v3 | v4 |
| --- | --- | --- |
| Seat identity | a biometric hash recorded at purchase | the purchaser's HUB identity |
| Buying a seat | any account, gated by a verifier enrollment signature | a HUB-verified person, signing with their own HUB key |
| Who adds a seat address | a recorded manager, plus a verifier approval | the seat's HUB identity, signing |
| A person's addresses | not represented | a set in consensus state, HUB-signed add and remove |
| Referral balance | keyed by account | keyed by HUB identity |
| Seats per human | unenforceable | enforced at 1,000 |
| What the verifier signs | purchase, activation, protected mint, protection removal, manager addition | HUB registration, and nothing else |

Everything else carries over unchanged: the envelope factoring and the kind-1
byte identity, the shared header and trailer, the admission order and its three
codes, the frozen result numbers `0` through `23`, the Merkle construction, the
genesis field table, the receipt layout, the accumulation cap and its
arithmetic, the cycle-assignment record, the bounded mint walk, the carry
identity, and every founder-directed figure in the accepted manifest.

**The accumulation cap is confirmed rather than changed.** The owner settled on
2026-08-14 that a seat is full when thirty days have passed since it last
collected, which is what version three measures. No byte of that machinery
moves.

## Scope

Version four defines:

- the canonical signed transaction envelope shared by every kind, and the eleven
  new transaction kinds;
- the HUB registry — identities, their public keys, and their address sets — and
  the transactions that write it;
- the HUB signature family: eight domain-separated messages, seven of them
  signed by a person's own recorded key;
- the automatic per-cycle assignment, the accumulation cap, and the bounded
  accumulate-then-mint settlement, all unchanged from version three;
- the canonical economy state key space and its value encodings;
- version-four genesis, chain identity, and the state-root construction;
- the version-four receipt and the complete numeric result-code space;
- the ordered rejection conditions of each kind, and the total mapping from
  `founder-economy-simulator-v3`'s model codes onto them; and
- the exact compatibility boundary against M1 transaction bytes, state, and
  roots, and against versions two and three.

It does not define the C++20 kernel implementation, which is requirement 10; the
cross-language vectors that implementation must reproduce, which are requirement
11; the four-node adversarial scenarios, which are requirement 13; the external
payment that must precede a seat purchase, which is bridge work; the
distribution of fees and commercial revenue, which `revenue-routing-v1` models;
the unreferred pool's payout; the deterministic active-set protocol; the
challenge content; or the HUB capture pipeline, its threat model, and the
construction of a person's HUB key, all of which are the identity milestone's
and which the constitution states are engineering work below this surface.

One authorization predicate is named and deliberately left undefined; it is
described in [What is still reserved](#what-is-still-reserved).

## Bindings

This specification holds no second copy of any founder-directed value.

**The manifest layer.** The channel table, the ten caps, the base-permission
legs, the denomination, the seat capacity, the per-person seat bound, the
issuance-cycle count, and the referral amount are the accepted
`founder-economy-manifest-v2` contract, whose digest is bound into version-four
genesis.

**The window grid.** `window_of_height`, `first_cycle_window`,
`last_cycle_window`, and `window_for_cycle` are `cycle-boundary-v1`.

**The measurement.** The finalised per-window record, its finalisation rule, and
its in-scope seat set are `uptime-measurement-v1`.

**The transitions.** The activity verdict, the winner rule, the tie rule, the
remainder rule, the carry and its conservation identity, and the ordered
rejection conditions are `founder-economy-simulator-v3`.

**The settlement.** The accumulation cap, the cycle-assignment record, the
bounded mint walk, and the referral accrual are `economy-transition-v3`,
incorporated by reference and re-encoded only where a key changes from an
account to a HUB identity.

## The transaction envelope

Every version-four transaction, including the version-one native transfer, is:

```text
signed_transaction = header(80) || body(kind-specific) || trailer(16) || signature(64)
```

The header is exactly the first 80 bytes of the accepted version-one transfer
and the trailer exactly its last 16, both unchanged:

| Offset | Size | Field | Required value or range |
| ---: | ---: | --- | --- |
| 0 | 4 | magic | ASCII `PSTX` |
| 4 | 2 | schema version | `1` |
| 6 | 1 | transaction kind | `1` through `12` |
| 7 | 32 | chain ID | configured chain |
| 39 | 1 | signature scheme | `1` |
| 40 | 32 | sender public key | canonical Ed25519 key |
| 72 | 8 | nonce | `u64` |

| Offset from body end | Size | Field |
| ---: | ---: | --- |
| 0 | 8 | fee limit `u64` |
| 8 | 8 | valid-until height `u64` |

The schema version stays `1` because these 80 bytes do not change, and the two
signing labels stay unversioned for the reason version two gives: the kind byte
and the chain ID are inside every preimage, and re-versioning would destroy the
kind-1 byte identity for separation the preimage already carries.

```text
signing_message = D("protocol-stack:v1:tx-sign") || unsigned_transaction
transaction_id  = H(D("protocol-stack:v1:tx-id") || signed_transaction)
```

### The version-one transfer is still the kind-1 instance

Kind 1's body is the accepted transfer's middle 40 bytes — a 32-byte recipient
and a `u64` amount — so `80 + 40 + 16 = 136` unsigned and `200` signed, which is
the accepted version-one transfer exactly. The vectors require the version-four
encoder to reproduce `protocol-primitives-v1`'s recorded unsigned bytes, signed
bytes, and transaction ID byte-for-byte.

**Three contract revisions have now left it untouched**, which is what an
extension is supposed to be able to do.

## Transaction kinds

| Kind | Name | Body size | Unsigned | Signed |
| ---: | --- | ---: | ---: | ---: |
| 1 | `native_transfer` | 40 | 136 | 200 |
| 2 | `purchase_seat` | 133 | 229 | 293 |
| 3 | `activate_seat` | 68 | 164 | 228 |
| 4 | `mint_node` | 4 | 100 | 164 |
| 5 | `mint_referral` | 0 | 96 | 160 |
| 6 | `direct_issue` | 105 | 201 | 265 |
| 7 | `mint_node_verified` | 68 | 164 | 228 |
| 8 | `set_mint_biometric` | 69 | 165 | 229 |
| 9 | `add_manager` | 100 | 196 | 260 |
| 10 | `hub_register` | 128 | 224 | 288 |
| 11 | `hub_add_address` | 96 | 192 | 256 |
| 12 | `hub_remove_address` | 96 | 192 | 256 |

**Every kind is fixed-length, and two pairs share a length.** Kinds 3 and 7 both
name a seat and carry one signature; kinds 11 and 12 both name an account and
carry one. A decoder dispatches on the kind byte, which is the rule version two
stated for exactly this case and which version three first exercised.

**The largest transaction in version four is 293 bytes**, down from version
three's 325. Purchase no longer carries a 64-byte enrollment signature, because
HUB registration already did that work. Nothing a transaction carries scales
with the seat population.

### Kind 10 — `hub_register`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 32 | HUB identity hash | 32 octets |
| 112 | 32 | HUB public key | canonical Ed25519 key |
| 176 | 64 | verifier signature | Ed25519 over the registration message |

The sender is the account being linked to the new identity, and it becomes that
identity's first address. On success the transition writes the identity entry —
its public key, the executing height, an address count of one, and a seat count
of zero — and the address entry for the sender.

**This is the only transaction the ecosystem verifier signs, and that is the
whole architecture.** The verifier is what asserts that a live, distinct human
stands behind an identity, which is a judgement no chain can make. Every later
proof of the same person is made by that person's own recorded key. An
unavailable verifier therefore stops new people entering the ecosystem and stops
nothing else: no purchase, no activation, no mint, no address change, and no
seat management depends on it.

**A HUB identity is registered once and is never re-registered.** An identity
hash already present is `REPLAY`, and an account already belonging to an
identity is `REPLAY`. Losing an address is not a reason to register again — that
is what kind 11 is for, and it is the reason the founder direction calls HUB a
recovery layer.

### Kinds 11 and 12 — `hub_add_address` and `hub_remove_address`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 32 | account ID | 32 octets |
| 112 | 64 | HUB signature | Ed25519 over the address message |

Kind 11 links an account to the signing identity; kind 12 unlinks one. The
sender is any account, because the signature is what authorizes the change and
the sender only pays the fee — which is precisely what makes recovery work: a
person who holds none of their linked addresses can still act.

**Removal unlinks an identity claim and moves no value.** The account keeps its
balance, its nonce, and its ability to transact; what it loses is the statement
that a particular verified human stands behind it. Making removal move assets
would make a HUB signature able to take funds from any address it names, which
is a far larger authority than the direction grants, so it is not built here and
is recorded in
[What this specification does not establish](#what-this-specification-does-not-establish).

**Removing an address does not remove it from a Founder Seat.** Seat manager
addresses are permanent and add-only by founder direction, and they are a
separate recorded set. An address unlinked from its HUB identity therefore keeps
whatever seat authority it already held, which is stated here because it is
surprising and directed rather than incidental.

At most `16` addresses may be linked to one identity, and an identity may hold
zero: a person who has removed every address can still add one, because kind 11
is authorized by the HUB key rather than by an address.

### Kind 2 — `purchase_seat`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 4 | seat ID `u32` | `0` through `99,999` |
| 84 | 32 | purchaser account ID | 32 octets |
| 116 | 1 | has referrer `bool` | `0x00` or `0x01` |
| 117 | 32 | referrer account ID | 32 octets, or 32 zero octets when absent |
| 149 | 64 | HUB signature | Ed25519 over the purchase message |

A `has_referrer` of `0x00` requires 32 zero octets in the referrer field; any
other value is the non-minimal representation `protocol-primitives-v1` forbids
and is `MALFORMED_TRANSACTION`.

**The purchaser must already be HUB verified, and the seat records their
identity rather than a second biometric hash.** That is the founder answer of
2026-08-14 and it is what makes one person one identity across the ecosystem.
The seat is owned by a person, not by an address, so losing every address does
not lose the seat.

**The sender need not be the purchaser, and the HUB signature is why.** A third
party may submit and pay for a purchase, and the purchaser's own key must have
signed the exact seat and account, so nobody can register a seat against another
person's identity. Version three achieved the same separation with a verifier
enrollment signature; version four achieves it with the purchaser's own.

**The referrer is named by account and recorded as an identity.** A buyer
chooses a referrer from a search or arrives through a referral link, both of
which yield an address; the chain resolves that address to its HUB identity and
records the identity. Referral earnings therefore follow the person, and a
referrer who later changes addresses keeps everything accrued.

### Kind 3 — `activate_seat`, kind 7 — `mint_node_verified`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 4 | seat ID `u32` | `0` through `99,999` |
| 84 | 64 | HUB signature | Ed25519 over the activation or mint message |

Both are signed by the seat's HUB identity. Activation is one-time and
permanent; kind 7 is the protected form of the mint and is accepted whether or
not the seat has switched protection on.

### Kind 4 — `mint_node`, kind 5 — `mint_referral`

Kind 4's body is a 4-byte seat ID and kind 5's is empty. Neither carries a
second factor. Kind 4 is refused with `BIOMETRIC_REQUIRED` when the seat has
switched protection on.

**One button, everything, no quantity**, unchanged and founder-directed. Kind 5
mints to the sender's own account the whole outstanding balance of **the HUB
identity that account belongs to**, which is the one change: a referral balance
is a person's, and any of their addresses may collect it.

### Kind 8 — `set_mint_biometric`, kind 9 — `add_manager`

| Kind | Offset | Size | Field |
| ---: | ---: | ---: | --- |
| 8 | 80 | 4 | seat ID `u32` |
| 8 | 84 | 1 | enable `bool` |
| 8 | 85 | 64 | HUB signature, or 64 zero octets |
| 9 | 80 | 4 | seat ID `u32` |
| 9 | 84 | 32 | manager account ID |
| 9 | 116 | 64 | HUB signature over the manager message |

**Kind 8's switch is asymmetric and the asymmetry is the protection.** Turning
protection **on** requires only a recorded manager's address signature, so its
signature field must be 64 zero octets and any other value is
`MALFORMED_TRANSACTION`. Turning it **off** requires a HUB signature by the
seat's identity. A stolen address key can neither mint against a protected seat
nor remove the protection first.

**Kind 9 no longer requires an existing manager, and that is the whole point.**
Version three requires a recorded manager's signature *and* a verifier approval,
so a founder holding no keys has no path at all. Version four requires the
seat's HUB identity to sign, and lets any sender submit it. A founder who has
lost every address can add a new one by proving they are the person the seat
belongs to.

**Seat addresses stay permanent and add-only.** There is no removal transition
for a seat manager, by founder direction and by the constitution's rule that a
recorded manager address remains in the ledger forever. The consequence — a
compromised address keeps mint authority — is recorded under
[What this specification does not establish](#what-this-specification-does-not-establish).

### Kind 6 — `direct_issue`

Unchanged from versions two and three, including its refusal. Its body is a
channel ID, a decision ID, a beneficiary account, a `u64` amount, and a 32-byte
authorization. A conforming chain rejects every kind 6 with `UNAUTHORIZED` until
`direct_issue_authority` is accepted.

### There is no transaction that records a day

The chain writes each cycle's outcome itself, at a block boundary, exactly as in
version three. See [Cycle assignment](#cycle-assignment-and-settlement).

## Admission

Admission operates on raw transaction bytes before ledger state is read, and its
version-one steps are unchanged in order and in meaning:

1. decode exactly one signed version-four transaction with no trailing bytes;
2. require the configured chain ID;
3. derive the sender account ID from the encoded public key;
4. strictly verify the Ed25519 signature over the signing message.

Step 1 classifies a wrong magic, schema version, transaction kind, or
signature-scheme identifier, a length that is not the exact length its kind
requires, a `has_referrer` or `enable` byte that is not `0x00` or `0x01`, a
non-minimal absent-referrer encoding, or a non-zero signature field on an
enabling `set_mint_biometric` as `MALFORMED_TRANSACTION`.

| Code | Name |
| ---: | --- |
| 1 | `MALFORMED_TRANSACTION` |
| 2 | `WRONG_CHAIN` |
| 3 | `INVALID_SIGNATURE` |

**No HUB or verifier signature is checked at admission**, because every one of
them verifies against a key held in ledger state — the ecosystem verifier key
for kind 10, and a person's recorded HUB public key for every other. Admission
is defined to read no state, so they are execution conditions returning
`UNAUTHORIZED`, and they produce a receipt.

**A bounded numeric field outside its range is not an admission failure.** A
seat ID of `100,000` decodes and is refused at execution with `CYCLE_RANGE`.

## Authorization

Every kind is signed by an account and every kind charges that account the fixed
fee, which the Founder Constitution decides applies to every accepted state
transition.

| Kind | Sender | Proof of the person |
| ---: | --- | --- |
| 1 | any account | none |
| 2 | any account | the purchaser's HUB key, over the purchase message |
| 3 | a recorded manager of the seat | the seat's HUB key, over the activation message |
| 4 | a recorded manager of the seat | none; refused when the seat is protected |
| 5 | an address of the paid identity | none |
| 6 | refused | the predicate is reserved |
| 7 | a recorded manager of the seat | the seat's HUB key, over the mint message |
| 8 | a recorded manager of the seat | the seat's HUB key to disable; none to enable |
| 9 | any account | the seat's HUB key, over the manager message |
| 10 | the account being linked | the ecosystem verifier key, over the registration message |
| 11 | any account | the identity's HUB key, over the add message |
| 12 | any account | the identity's HUB key, over the remove message |

A sender the applicable rule refuses is `UNAUTHORIZED`.

**Three kinds accept any sender, and each is a recovery path.** Kinds 9, 11, and
12 are the transactions a person must be able to make when they hold none of
their own addresses, so requiring a particular sender would defeat them. The
signature is the authority and the sender only pays.

### The HUB signature family

Eight domain-separated messages. Seven verify against the acting identity's
recorded `hub_public_key`; only the first verifies against the genesis-configured
ecosystem verifier key.

```text
registration_message =
  D("protocol-stack:v4:hub-registration") ||
  chain_id || hub_identity_hash || hub_public_key ||
  sender_account_id || u64(valid_until_height)

address_add_message =
  D("protocol-stack:v4:hub-address-add") ||
  chain_id || hub_identity_hash || account_id || u64(valid_until_height)

address_remove_message =
  D("protocol-stack:v4:hub-address-remove") ||
  chain_id || hub_identity_hash || account_id || u64(valid_until_height)

purchase_message =
  D("protocol-stack:v4:seat-purchase") ||
  chain_id || hub_identity_hash || u32(seat_id) ||
  purchaser_account_id || u64(valid_until_height)

activation_message =
  D("protocol-stack:v4:seat-activation") ||
  chain_id || hub_identity_hash || u32(seat_id) || u64(valid_until_height)

mint_message =
  D("protocol-stack:v4:seat-mint") ||
  chain_id || hub_identity_hash || u32(seat_id) || u64(valid_until_height)

mint_biometric_disable_message =
  D("protocol-stack:v4:mint-biometric-disable") ||
  chain_id || hub_identity_hash || u32(seat_id) || u64(valid_until_height)

manager_message =
  D("protocol-stack:v4:seat-manager") ||
  chain_id || hub_identity_hash || u32(seat_id) ||
  manager_account_id || u64(valid_until_height)
```

**Every message binds the identity**, so a signature made by one person's key
cannot be presented as another's even where the remaining fields coincide.
Three messages carry identical field shapes and are separated only by their
labels, which is what domain separation is for: an approval to activate a seat
must not be presentable as an approval to mint from it or to remove its
protection.

`valid_until_height` in each message is the transaction's own trailer value, so
the proof and the transaction expire together.

**The verifier gates entry to the ecosystem and nothing else.** Version two said
this of entry to the economy; version three weakened it, because a seat that
switched protection on made verifier availability a precondition for its own
income. Version four restores it in full: the verifier signs a registration and
never anything else, so an unavailable verifier stops new people joining and
stops no participant already inside from doing anything at all.

### What is still reserved

`direct_issue_authority` — the eligibility and anti-abuse mechanics for the
`liquidity_mining`, `impermanent_loss_protection`,
`hub_verified_user_incentives`, and `initial_mystery_box_incentives` channels,
and the rate of the one whose eligibility ADR 0033 settled. Kind 6 is specified
and refused rather than given an invented predicate.

## Canonical economy state

Version one's state — chain ID, supply limit, total supply, fixed fee, height,
fee pool, and the ordered account map — plus one ordered map from canonical byte
keys to canonical byte values. A key is `u8(entry_kind)` followed by fixed-width
big-endian fields.

| Kind | Entry | Key | Key bytes | Value | Value bytes |
| ---: | --- | --- | ---: | --- | ---: |
| 1 | seat | `u8(1) \|\| seat_id:u32` | 5 | see below | 119 |
| 2 | channel | `u8(2) \|\| channel_id:u8` | 2 | `issued:u64 \|\| outstanding:u64` | 16 |
| 3 | cycle assignment | `u8(3) \|\| cycle_window:u64` | 9 | see below | 24 + 2⌈b/8⌉ |
| 4 | referral balance | `u8(4) \|\| hub_identity_hash:bytes<32>` | 33 | `accrued:u64 \|\| minted:u64 \|\| collected_through_window:u64` | 24 |
| 5 | direct decision | `u8(5) \|\| decision_id:bytes<32>` | 33 | *(empty)* | 0 |
| 6 | typed custody | `u8(6) \|\| beneficiary_kind:u8 \|\| beneficiary_id:bytes<32>` | 34 | `amount:u64` | 8 |
| 7 | carry | `u8(7) \|\| channel_id:u8` | 2 | `carry:u64` | 8 |
| 8 | verifier key | `u8(8)` | 1 | `ed25519_public_key:bytes<32>` | 32 |
| 9 | seat manager | `u8(9) \|\| seat_id:u32 \|\| account_id:bytes<32>` | 37 | *(empty)* | 0 |
| 10 | HUB identity | `u8(10) \|\| hub_identity_hash:bytes<32>` | 33 | see below | 48 |
| 11 | HUB address | `u8(11) \|\| account_id:bytes<32>` | 33 | `hub_identity_hash:bytes<32>` | 32 |
| 12 | unreferred pool | `u8(12)` | 1 | `accrued:u64 \|\| minted:u64` | 16 |

An entry kind outside `1` through `12` cannot occur, because no transition
writes one and the state is not an untrusted input.

### The HUB identity record

```text
hub_public_key       : bytes<32>
registered_at_height : u64
address_count        : u32
seat_count           : u32
```

48 bytes. The public key is what every later proof of this person verifies
against. The two counts are state for the same reason version three's
`manager_count` is: a bound enforced by iterating a key prefix inside a
transition is an implicit cost two implementations disagree about.

**`seat_count` is what makes the constitution's per-human bound enforceable.**
Version three records that the 1,000-seat limit "is not enforced by any
transition here, because enforcing it requires knowing that two biometric hashes
belong to one human, which is exactly what the chain cannot see". With one
identity per person in state, it can, and version four enforces it with
`SEAT_LIMIT`.

### The HUB address entry

Key by account, value the identity. The forward direction is what every
transition needs — is this account verified, and whose is it — and it is one
lookup. Enumerating a person's addresses is a read-side index rather than a
transition need, and no transition performs it.

**Membership is exactly this entry.** An account with no entry is not HUB
verified; an account with one belongs to exactly the identity it names. Two
identities cannot claim one account, because kind 11 refuses an account that
already has an entry.

### The seat record

```text
hub_identity_hash        : bytes<32>
purchaser_account_id     : bytes<32>
has_referrer             : u8
referrer_hub_identity    : bytes<32>
is_activated             : u8
activation_height        : u64
minted_through_window    : u64
mint_requires_biometric  : u8
manager_count            : u32
```

119 bytes, the same width as version three's. Two fields change meaning rather
than size: the seat's own identity is a HUB identity rather than a
purchase-time biometric hash, and the referrer is a HUB identity rather than an
account.

**The seat belongs to a person.** `purchaser_account_id` is retained as the
historical record of which address bought it and is not an authority: authority
is the manager set, and ownership is the HUB identity.

**Self-referral is now checkable across a person's addresses.** Version three
compares two account identifiers, so a buyer could refer themselves from a
second address. Version four compares two HUB identities, and one person has
exactly one.

### The cycle assignment record, the manager set, and everything else

Unchanged from version three, field for field:

```text
share_per_winner_atomic : u64
reallocated_count       : u32
winner_count            : u32
in_scope_count          : u32
bitmap_bits             : u32
accrued_bitmap          : ⌈bitmap_bits / 8⌉ octets, one bit per seat ID
winner_bitmap           : ⌈bitmap_bits / 8⌉ octets, one bit per seat ID
```

The manager set is a family of presence-only entries keyed by seat and account,
bounded at 16. The typed-custody beneficiary space is version three's five
codes, four of them singletons taking a zero beneficiary ID.

### The economy Merkle tree and the version-four state root

```text
economy_entry = bytes(key) || bytes(value)

economy_tree({})            = H(D("protocol-stack:v4:economy-empty"))
economy_tree({entry})       = H(D("protocol-stack:v4:economy-leaf") || entry)
economy_tree(left || right) = H(D("protocol-stack:v4:economy-node") || l || r)

state_root =
  H(
    D("protocol-stack:v4:state-root") ||
    u16(4) || chain_id || height:u64 || supply_limit:u64 ||
    total_supply:u64 || fee_pool_balance:u64 || account_count:u64 ||
    accounts_tree_root || economy_entry_count:u64 || economy_tree_root
  )
```

The tree shape is `protocol-primitives-v1`'s RFC 9162 construction and the
accounts tree is unchanged entry-for-entry. The label and version field differ
from all three predecessors, so **a version-four state root is never equal to a
version-one, version-two, or version-three root**, including over an identical
account set and an empty economy. Each non-collision is required separately,
because distinct labels are strings rather than a chain.

## Version-four genesis

| Field | Encoding | Required value |
| --- | --- | --- |
| magic | `bytes<4>` | ASCII `PSGN` |
| schema version | `u16` | `4` |
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
chain_id = H(D("protocol-stack:v4:chain-id") || canonical_genesis_v4_bytes)
```

The field table is version three's with a different schema version, so the
prefix is still 110 bytes and the 1,048,576-byte object bound still admits at
most 21,843 entries:

```text
110 + 48 * 21,843 = 1,048,574   accepted
110 + 48 * 21,844 = 1,048,622   rejected
```

Genesis writes the ten channel entries with both amounts zero, the ten carry
entries with zero, the ecosystem verifier key, and the unreferred pool entry
with both amounts zero. It writes no seat, no manager, no HUB identity, no HUB
address, no referral balance, no custody entry, and no cycle assignment.

The three relaxations version two derived are unchanged and each is forced by
the constitution's no-genesis-allocation rule: zero total supply, zero accounts,
and a fee permitted to be zero. **The bootstrap gap is unchanged and is recorded
rather than closed** — every path to a first payable balance is external and
belongs to the bridge milestone.

## Execution

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

Codes `1` and `7` are reachable only where a body carries an amount:
`ZERO_AMOUNT` for kinds 1 and 6, and `DEBIT_OVERFLOW` for kind 1 alone. Every
non-success result performs no state write and charges no fee, still produces a
receipt, and still enters the ordered transaction root.

### Kind 10 — HUB register

1. an already-registered `hub_identity_hash` is `REPLAY`;
2. a sender account already linked to an identity is `REPLAY`;
3. a verifier signature that does not verify over the registration message is
   `UNAUTHORIZED`.

On success it writes the identity record with the supplied public key, the
executing height, an address count of one, and a seat count of zero, and writes
the sender's address entry.

### Kind 11 — HUB add address

1. an unregistered `hub_identity_hash` is `NOT_HUB_VERIFIED`;
2. an `account_id` already linked to any identity is `REPLAY`;
3. an identity already holding 16 addresses is `ADDRESS_LIMIT`;
4. a HUB signature that does not verify over the add message is `UNAUTHORIZED`.

On success it writes the address entry and increments `address_count`.

**The identity is named in the body's message rather than derived from the
sender**, because a person recovering from total address loss has no linked
sender to derive it from.

### Kind 12 — HUB remove address

1. an `account_id` with no address entry is `NOT_HUB_VERIFIED`;
2. a HUB signature that does not verify over the remove message, against the
   public key of the identity that entry names, is `UNAUTHORIZED`.

On success it deletes the address entry and decrements `address_count`. It moves
no value and touches no seat.

### Kind 2 — purchase seat

1. a `seat_id` outside `0..99,999` is `CYCLE_RANGE`;
2. an already-purchased `seat_id` is `REPLAY`;
3. a `purchaser_account_id` with no HUB address entry is `NOT_HUB_VERIFIED`;
4. a named referrer with no HUB address entry is `NOT_HUB_VERIFIED`;
5. a referrer whose HUB identity equals the purchaser's is `INVALID_REFERRER`;
6. a purchaser identity already holding 1,000 seats is `SEAT_LIMIT`;
7. a HUB signature that does not verify over the purchase message, against the
   purchaser identity's public key, is `UNAUTHORIZED`.

On success it writes the seat record with the purchaser's HUB identity, the
referrer's HUB identity or absence, `is_activated` false, `activation_height`
zero, `minted_through_window` zero, `mint_requires_biometric` false, and
`manager_count` one; writes the purchaser's manager entry; and increments the
purchaser identity's `seat_count`. It issues nothing.

**Authorization is checked last and the request's own defects first**, for the
reason version two gives: a submitter fixing a bug should not be told that every
mistake is an authorization failure.

### Kind 3 — activate seat

1. a `seat_id` outside `0..99,999` is `CYCLE_RANGE`;
2. an unpurchased `seat_id` is `SEAT_NOT_PURCHASED`;
3. a sender that is not a recorded manager is `UNAUTHORIZED`;
4. an already-activated seat is `REPLAY`;
5. a HUB signature that does not verify over the activation message, against the
   seat identity's public key, is `UNAUTHORIZED`.

On success it sets `is_activated`, writes `activation_height` as the executing
block height, and sets `minted_through_window` to
`window_of_height(activation_height)`, which is the window before the seat's
first cycle window and which is what makes the accumulation cap well-defined.

### Kinds 4 and 7 — mint node

1. a `seat_id` outside `0..99,999` is `CYCLE_RANGE`;
2. an unpurchased `seat_id` is `SEAT_NOT_PURCHASED`;
3. an unactivated seat is `SEAT_NOT_ACTIVATED`;
4. a sender that is not a recorded manager is `UNAUTHORIZED`;
5. for kind 4, a seat whose `mint_requires_biometric` is set is
   `BIOMETRIC_REQUIRED`; for kind 7, a HUB signature that does not verify over
   the mint message is `UNAUTHORIZED`;
6. `minted_through_window` already equal to the last assigned window, or no
   window assigned yet, is `NOTHING_TO_MINT`;
7. a leg that does not fit its channel is `CHANNEL_CAP`.

On success the transition walks

```text
( minted_through_window , min(last_assigned_window, minted_through_window + 30) ]
```

and for each window holding an assignment record settles the seat's own base
permission when its accrued bit is set, and `reallocated_count` equal shares
when its winner bit is set. The Founder operator leg credits **the sender's
account balance**; the four institutional legs credit typed custody. It then
sets `minted_through_window` to the last assigned window, moves each leg from
`outstanding` to `issued`, and increases `total_supply`. It is atomic.

All of this is version three's, unchanged, including that the walk is bounded by
the cap exactly rather than conservatively and that a mint collecting nothing
still advances a stale mark.

### Kind 5 — mint referral

1. a sender with no HUB address entry is `NOT_HUB_VERIFIED`;
2. no referral balance for that identity, or a balance whose `accrued` equals
   its `minted` **and** whose `collected_through_window` already equals the last
   assigned window, is `NOTHING_TO_MINT`;
3. a leg that does not fit the channel is `CHANNEL_CAP`.

On success it mints the whole outstanding difference to the sender's account
balance, sets `minted` equal to `accrued`, sets `collected_through_window` to
the last assigned window, and increases `total_supply`.

**Any of a person's addresses may collect their referral earnings**, because the
balance belongs to the identity. A referrer who loses an address loses nothing.

### Kind 8 — set mint biometric

1. a `seat_id` outside `0..99,999` is `CYCLE_RANGE`;
2. an unpurchased `seat_id` is `SEAT_NOT_PURCHASED`;
3. a sender that is not a recorded manager is `UNAUTHORIZED`;
4. a seat whose `mint_requires_biometric` already equals `enable` is `REPLAY`;
5. when `enable` is false, a HUB signature that does not verify over the disable
   message is `UNAUTHORIZED`.

### Kind 9 — add manager

1. a `seat_id` outside `0..99,999` is `CYCLE_RANGE`;
2. an unpurchased `seat_id` is `SEAT_NOT_PURCHASED`;
3. a `manager_account_id` already recorded for the seat is `REPLAY`;
4. a seat already holding 16 managers is `MANAGER_LIMIT`;
5. a HUB signature that does not verify over the manager message, against the
   seat identity's public key, is `UNAUTHORIZED`.

On success it writes the manager entry and increments `manager_count`. **There
is no sender condition**, which is what makes it a recovery path.

### Kind 6 — direct issue

1. every sender is `UNAUTHORIZED` while the predicate is undecided;
2. a `channel_id` outside `{5, 6, 8, 9}` is `INVALID_CHANNEL`;
3. a zero `amount` is `ZERO_AMOUNT`;
4. an already-accepted `decision_id` is `REPLAY`;
5. an absent authorization is `MISSING_RESEARCH_INPUT`, one not bound to this
   exact action is `INVALID_RESEARCH_INPUT`, and a negative decision is
   `NOT_ELIGIBLE`;
6. an amount that does not fit the channel is `CHANNEL_CAP`.

Conditions 2 through 6 are unreachable in a conforming implementation because
condition 1 refuses every sender first, and the vectors record that
unreachability as a derived property.

## Cycle assignment and settlement

Unchanged from version three in every respect. At the first height of window
`w + 2`, when `uptime-measurement-v1` finalises window `w`, ordered block
execution writes window `w`'s cycle-assignment record:

1. derive the in-scope seat set and `bitmap_bits`;
2. read each in-scope seat's uptime and derive whether it met the cycle;
3. derive the winner set — the highest uptime among seats that met the cycle and
   are under the accumulation cap;
4. set the accrued bit of each in-span seat that met the cycle and is under the
   cap, and count every other in-span seat's permission as reallocated;
5. add one base permission's `outstanding` per in-span seat, per leg;
6. divide each leg by the winner count, then move `reallocated_count` times each
   remainder **out of** `outstanding` and into that channel's carry;
7. accrue the referral leg for each in-span seat — to the seat's recorded
   referrer identity when it has one and that identity is under the cap, and to
   the unreferred pool otherwise.

**A cycle a seat cannot collect because it is at the cap is a cycle it failed**,
which is the founder's own statement of steps 3 and 4 and which makes both
consequences follow from rules already written: the day's permission goes to the
best performers, and the full seat is not one of them because a failed seat
never rewards another failed seat.

The two-cycle lag is forced by the dispute window rather than chosen, and the
last assigned window at any height `h` is `window_of_height(h) - 2`.

## Receipt

Each admitted transaction produces exactly one 56-byte receipt:

| Offset | Size | Field |
| ---: | ---: | --- |
| 0 | 4 | ASCII `PSRC` |
| 4 | 2 | receipt version `4` |
| 6 | 32 | transaction ID |
| 38 | 1 | transaction kind |
| 39 | 1 | result code |
| 40 | 8 | fee charged; the fixed fee on success, otherwise zero |
| 48 | 8 | issued atomic units; zero for every non-issuing kind and every failure |

Unknown result codes, a kind outside `1` through `12`, a nonzero failed fee, and
a nonzero `issued_atomic` on a failure are invalid. The layout is version two's
and the version field is not, because the admissible kind and result-code ranges
widen again.

The non-issuing kinds are 1, 2, 3, 8, 9, 10, 11, and 12. Issuance happens only
at the two node mints, the referral mint, and direct issue.

## Result codes

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
| 9 | `UNAUTHORIZED` | version two |
| 10 | `CYCLE_RANGE` | economy model |
| 11 | `INVALID_REFERRER` | economy model |
| 12 | `REPLAY` | economy model |
| 13 | `SEAT_NOT_ACTIVATED` | economy model |
| 14 | `SEAT_NOT_PURCHASED` | version two |
| 15 | `NOTHING_TO_MINT` | version two |
| 16 | `INVALID_CHANNEL` | economy model |
| 17 | `MISSING_RESEARCH_INPUT` | economy model |
| 18 | `INVALID_RESEARCH_INPUT` | economy model |
| 19 | `NOT_ELIGIBLE` | economy model |
| 20 | `CHANNEL_CAP` | economy model |
| 21 | `NOT_HUB_VERIFIED` | version three |
| 22 | `BIOMETRIC_REQUIRED` | version three |
| 23 | `MANAGER_LIMIT` | version three |
| 24 | `SEAT_LIMIT` | new |
| 25 | `ADDRESS_LIMIT` | new |

Codes `0` through `23` keep their exact version-three meanings and `0` through
`8` their exact version-one meanings, so the space extends contiguously.

**`SEAT_LIMIT` is the constitution's own rule finally reaching the chain.** One
human may control no more than 1,000 seats, which no earlier version could
enforce.

### The model mapping is total and unchanged

`founder-economy-simulator-v3`'s twenty-four codes partition exactly as they do
under versions two and three — 11 carried, 2 guards, 11 unrepresentable — because
the model is unchanged. Eight codes here have no model counterpart: the three
version two added, the three version three added, and the two new ones.

## Invariants

Version one's state invariants hold, with conservation extended by the typed
custody term and `total_supply` permitted to increase by issuance, which
`ledger-transition-v1` names as requiring a new transition version.

The manifest's invariants hold at every accepted state, and the carry identity
holds per channel:

```text
for each Founder Node channel c, with leg(c) its per-cycle amount:
  issued(c) + outstanding(c) + carry(c) = assigned_cycle_permissions * leg(c)
```

with the carried remainder moved out of `outstanding` rather than added beside
it, which is what makes the equality hold. The referral channel satisfies the
same identity without a carry:

```text
issued(founder_referral) + outstanding(founder_referral)
  = assigned_cycle_permissions * 3,420,000,000
outstanding(founder_referral)
  = sum over identities of (accrued - minted) + (pool.accrued - pool.minted)
```

Version four adds two structural invariants:

1. **every HUB address entry names a registered identity**, and an identity's
   `address_count` equals the number of address entries naming it; and
2. **every seat names a registered identity**, and an identity's `seat_count`
   equals the number of seats naming it, and never exceeds 1,000.

Both are equalities rather than bounds, because a bound would admit a defect
that lost a count.

## Resource limits and storage bounds

Version one's limits are unchanged: at most 65,535 raw inputs and 65,535
admitted transactions per block, and a 1,048,576-byte canonical object bound.
The largest transaction is 293 bytes and the longest mint walk is 30 assignment
records.

| Entry | Bound at 100,000 seats | Derivation |
| --- | ---: | --- |
| seats | 12,400,000 bytes | `100,000 * (5 + 119)` |
| seat managers | 59,200,000 bytes | `100,000 * 16 * (37 + 0)` |
| HUB identities | 8,100 bytes per 100 people | `100 * (33 + 48)` |
| HUB addresses | 1,040 bytes per 16-address person | `16 * (33 + 32)` |
| channels | 180 bytes | `10 * (2 + 16)` |
| carries | 100 bytes | `10 * (2 + 8)` |
| typed custody | 168 bytes | `4 * (34 + 8)` |
| referral balance | 57 bytes per referring identity | `33 + 24` |
| verifier key | 33 bytes | one entry |
| unreferred pool | 17 bytes | one entry |
| cycle assignment | 25,033 bytes per cycle | `9 + 24 + 2 * 12,500` |

**The HUB registry is bounded per participant rather than at seat capacity**,
because it serves every participant class rather than the 100,000 seats. At the
constitutional minimum of 100 principals holding all seats it is 8,100 bytes;
its real size is a function of ecosystem adoption, which no figure here bounds.

**The one unbounded term is unchanged.** Cycle assignment records accumulate at
one per cycle and are never deleted, about 9.1 MB per year at full capacity. The
cap bounds how many records a mint reads, not how old they are, so no pruning
rule follows from it. The three mitigations version two enumerated and refused
stand as it left them.

## Determinism

Validation order, result numbers, receipt bytes, successful writes, and failure
atomicity are consensus rules. An implementation must not consult a wall clock,
locale, filesystem order, host integer width, database-native ordering, or
adapter-specific metadata, and must not use floating point on any monetary or
consensus path. Every monetary operation is checked `u64` arithmetic whose
violation invalidates the block.

No AI inference, external price, biometric result, or telemetry value is a
direct input to any transition defined here. A HUB signature is an Ed25519
signature over fixed bytes, verified against a key already in state; nothing
about the capture that produced it reaches consensus.

## Compatibility boundary

**Transaction bytes.** A version-one signed transfer is a version-four kind-1
transaction, byte-for-byte, with the same signing message, transaction ID, and
execution result numbers. A version-one node presented with kinds 2 through 12
rejects them at admission step 1 as `MALFORMED_TRANSACTION`; a version-two node
rejects kinds 7 through 12 and a version-three node kinds 11 and 12 the same
way. No earlier byte sequence acquires a new meaning.

**State.** A version-four state is a version-one state plus one ordered economy
map, and every version-one invariant holds.

**Roots.** The version-four state root has a distinct domain label and version
field from all three predecessors, so no earlier root is reinterpreted and no
version-four root collides with one.

**Genesis and chain identity.** Version-four genesis has a distinct schema
version and chain-ID label, so **a version-four chain is a new chain rather than
a migration of a version-three one**. There is no upgrade block and no state
translation; the four contracts are alternative chains and only one will ever
carry value.

**Denomination and supply limit.** Unchanged, and settled by
`ledger-transition-v1` and `founder-economy-manifest-v2` respectively.

**What is not claimed.** No accepted M1, version-two, or version-three vector,
digest, receipt, root, or recorded devnet result changes, and none is recomputed
under this specification.

## Versioning and compatibility of this document

The envelope layout, the twelve kind identifiers and their bodies, the admission
order, the state key space and value encodings, the beneficiary-kind space, the
HUB signature family, the tree and root constructions, the genesis layout, the
receipt layout, the numeric result codes, the accumulation cap, and the
rejection orders are immutable for version four. A changed field, code, order,
or semantic rule requires a new transition version and an ADR.

Versions one through four coexist as documents; every earlier artifact remains
in place, passing, and unedited.

## What this specification does not establish

- **Direct-channel eligibility.** `direct_issue_authority` remains named and
  undefined, and kind 6 is refused because of it.
- **That a HUB identity is a distinct human.** The chain verifies a signature by
  a key the ecosystem verifier attested to. Whether that verifier is sound,
  whether a live human stood in front of it, and whether the capture is
  unlinkable are outside consensus by design, and the constitution's threat-model
  and independent-review requirements for biometric capture are untouched by
  anything here. **Every guarantee version four adds — one person one identity,
  the per-human seat bound, self-referral refusal — rests on that attestation
  and is exactly as strong as it.**
- **What a coerced HUB signature can do.** It can add an address to a seat, and
  seat addresses are permanent. Version three required a second, independent
  factor for that — a key the founder already held — and version four removes it
  deliberately so that a founder holding no keys is not locked out. Whether that
  trade is acceptable is recorded for independent review in ADR 0036.
- **Asset movement on address removal.** Unlinking an address moves no value.
  Making a HUB signature able to move funds from an address it names is a far
  larger authority than the direction grants and is not built here.
- **Verifier key rotation.** The ecosystem verifier key is written at genesis
  and no transition changes it. Its reach is now narrower than in any earlier
  version — it signs registrations alone — so a compromised key admits false
  people and cannot touch anyone already inside.
- **The payment.** Nothing here proves that BTC, ETH, or an approved stablecoin
  was received for a seat.
- **That any of this executes.** No C++ implementation exists.
- **The measurement.** Everything `uptime-measurement-v1` does not establish is
  inherited unchanged.
- **The bootstrap.** A chain with no genesis allocation and a nonzero fee cannot
  execute its first transaction.
- **Distribution.** No kind here distributes transaction fees or commercial
  revenue to active seats.
- **The unreferred pool's payout.** The month, the ranking snapshot, and the
  payout transition remain unspecified.

## Required vectors and evidence

`test-vectors/economy-transition-v4.txt` is normative. It fixes the envelope
decomposition and every kind's layout and lengths, including the two length
collisions; **the kind-1 identity** against the accepted
`protocol-primitives-v1` bytes; the cross-kind separation; every admission
rejection over a minimally mutated input with a positive control; the eight HUB
message constructions and their pairwise distinctness on identical fields; the
complete result-code table and the three-way partition of the economy model's
codes; every state key and value encoding; the empty, genesis, and populated
economy roots and the version-four state root; **the four-way non-collision** of
version-one through version-four roots over an identical account set and an
empty economy, each predecessor's construction first required to reproduce its
own accepted vectors; version-four genesis bytes, its chain ID, that it differs
from a version-three genesis with identical fields, and the 21,843-entry bound
at its accepting and rejecting values; the receipt layout and its new version;
the accumulation cap, the walk range, and the cycle assignment, all required to
reproduce version three's recorded values where the fixture coincides; **the
HUB registry**: registration, add, remove, the two counts, the address bound,
and that an identity may hold zero addresses and still add one; **the per-human
seat bound** at 999, 1,000, and 1,001 seats; and **self-referral across two
addresses of one identity**, which version three cannot refuse and version four
does.

The conservation vectors are the load-bearing ones, and the two structural
invariants are checked alongside them: an identity's `address_count` equals the
number of address entries naming it, and its `seat_count` the number of seats.

The verifier independently derives rather than restates every recorded value.
Its independence is `tools/economy-transition-v4-vectors/expected.py`, which
imports nothing from `simulation/` and restates the version-one layouts, the
Founder Constitution's tables, and the accepted manifest's channel order by
hand.

Acceptance requires full GitHub-hosted verification on the exact commit. Passing
these checks establishes an exact, auditable encoding and compatibility
boundary. It does not establish that the transitions execute, that the economy
is safe, that a purchase was paid for, that a HUB identity is a distinct human,
or that the resource bounds are adequate under adversarial load.
