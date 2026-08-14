# Economy transition v3

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
The change is classified as encoding, state-transition shape, authority, and
compatibility.
[ADR 0034](../decisions/0034-economy-transition-v3-managers-cap-and-hub.md)
records the alternatives and the decision.

**Version three exists because the founder direction of 2026-08-14 supersedes
[`economy-transition-v2.md`](economy-transition-v2.md) in four places.**
[ADR 0033](../decisions/0033-founder-decisions-minting-hub-and-referral-entry.md)
records that direction. Version two is not edited: it is the accepted record of
what was verified on 2026-08-13, its 238 vectors and their digests are that
evidence, and the repository's rule — applied for `founder-economy-manifest-v2`,
`escrow-payout-v2` and `v3`, and `founder-economy-simulator-v3` — is that a
changed transition is a new version rather than an edit.

## What version three changes

| | v2 | v3 |
| --- | --- | --- |
| Who may act for a seat | the recorded purchaser only | any recorded manager address |
| Biometric on minting | never | optional, per seat |
| Permission accumulation | unbounded | capped at 30 cycles, excess reallocated |
| Referrer | any 32-byte account | must be HUB verified |

Two further changes follow from the same ADR's first decision rather than from
its table, and both are consequences rather than additions:

- **A mint credits an ordinary spendable account.** ADR 0033 states that there
  is "no separate withdrawal step and no second balance type", so the Founder
  operator leg and the referral both credit the ledger's own account map.
  Version two credited typed custody, and version two's own closing section
  recorded that no transition moved typed custody into a spendable account.
- **The account credited is the signer's.** The constitution makes adding a
  manager the remedy for a lost address; a mint that credited the recorded
  purchaser would leave that remedy unable to recover anything, so the acting
  manager is the recipient. This is derived in
  [Authorization](#authorization) rather than assumed.

Four things are repaired rather than changed, because specifying version three
required deriving them and version two's text did not survive the derivation:

- the cycle-assignment bitmaps are **indexed by seat ID** rather than by
  in-scope rank, so reading one seat's bit no longer requires deriving the whole
  in-scope set;
- the assignment record carries the **number of reallocated permissions**,
  without which a winner's entitlement is not computable from the record alone;
- the carried remainder is **subtracted from the channel's outstanding amount**,
  which is what makes version two's own stated carry identity hold; and
- the beneficiary-kind space of the typed-custody key is **enumerated**, which
  version two used and never fixed.

ADR 0034 records two further version-two defects that this contract cannot
repair because they are evidence rather than rules: a storage figure that
contradicts its own derivation, corrected in place in version two's prose, and a
recorded vector whose value states the opposite of what its own name asserts,
left alone because a vector file is the artifact the hosted matrix verified.

The envelope factoring, the kind-1 byte identity, the shared header and trailer,
the frozen version-one result numbers, the admission order, the Merkle
construction, the genesis field table, and the compatibility argument are
unchanged and carry over.

## Scope

Version three defines:

- the canonical signed transaction envelope shared by every kind, and the nine
  new transaction kinds;
- the biometric verification signatures that gate seat purchase, activation,
  protected minting, protection removal, manager addition, and HUB verification;
- the automatic per-cycle assignment the chain performs at a block boundary, the
  bounded accumulate-then-mint settlement it feeds, and the accumulation cap;
- the canonical economy state key space and its value encodings;
- version-three genesis, chain identity, and the state-root construction;
- the version-three receipt and the complete numeric result-code space;
- the ordered rejection conditions of each kind, and the total mapping from
  `founder-economy-simulator-v3`'s model codes onto them; and
- the exact compatibility boundary against M1 transaction bytes, state, and
  roots, and against version two.

It does not define the C++20 kernel implementation, which is requirement 10; the
cross-language vectors that implementation must reproduce, which are requirement
11; the four-node adversarial scenarios, which are requirement 13; the external
payment that must precede a seat purchase, which is bridge work; the
distribution of transaction fees and commercial revenue to active seats, which
`revenue-routing-v1` models and no kind here performs; the unreferred pool's
payout; the deterministic active-set protocol; the challenge content; or the
HUB identity service itself. One authorization predicate is named and
deliberately left undefined; it is described in
[What is still reserved](#what-is-still-reserved).

## Bindings

This specification holds no second copy of any founder-directed value.

**The manifest layer.** The channel table, the ten caps, the base-permission
legs, the denomination, the seat capacity, the issuance-cycle count, and the
referral amount are the accepted `founder-economy-manifest-v2` contract. Its
digest is bound into version-three genesis, so a chain whose manifest differs is
a different chain rather than the same chain with a different table.

**The window grid.** `window_of_height`, `first_cycle_window`,
`last_cycle_window`, and `window_for_cycle` are `cycle-boundary-v1`.

**The measurement.** The finalised per-window record, its finalisation rule, and
its in-scope seat set are `uptime-measurement-v1`.

**The transitions.** The activity verdict, the winner rule, the tie rule, the
remainder rule, the carry and its conservation identity, the journal buckets,
and the ordered rejection conditions are `founder-economy-simulator-v3`. This
document encodes them; it does not restate them, and where it narrows one it
says so and derives the narrowing.

**The founder direction.** The manager rule, the optional biometric on minting
and its asymmetry, the accumulation cap and its reallocation path, the referral
cap and its destination, and the HUB requirement for a referrer are ADR 0033 and
the Founder Constitution.

## The transaction envelope

Every version-three transaction, including the version-one native transfer, is:

```text
signed_transaction = header(80) || body(kind-specific) || trailer(16) || signature(64)
```

The header is exactly the first 80 bytes of the accepted version-one transfer,
unchanged:

| Offset | Size | Field | Required value or range |
| ---: | ---: | --- | --- |
| 0 | 4 | magic | ASCII `PSTX` |
| 4 | 2 | schema version | `1` |
| 6 | 1 | transaction kind | `1` through `10` |
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
reinterpreting an existing one. Four new kind identifiers are the addition it
permits.

### The version-one transfer is still the kind-1 instance

Kind 1's body is the accepted transfer's middle 40 bytes:

| Offset | Size | Field |
| ---: | ---: | --- |
| 80 | 32 | recipient account ID |
| 112 | 8 | amount `u64` |

so `80 + 40 + 16 = 136` unsigned and `136 + 64 = 200` signed, which is the
accepted version-one transfer exactly. The vectors prove this rather than
asserting it: the version-three encoder is handed the accepted
`protocol-primitives-v1` transfer inputs and must reproduce that specification's
recorded unsigned bytes, signed bytes, and transaction ID byte-for-byte.

**That the identity survives a second contract revision is the point of
checking it again.** Version two established that the transfer factors; version
three adds four kinds, five state entries, and a new settlement rule without
touching the factoring, which is what an extension is supposed to be able to do.

### Signing and identity are unchanged

```text
signing_message = D("protocol-stack:v1:tx-sign") || unsigned_transaction
transaction_id  = H(D("protocol-stack:v1:tx-id") || signed_transaction)
```

Both labels are the accepted version-one labels and are **not** re-versioned,
for the reason version two gives: the transaction kind is at offset 6 and the
chain ID at offset 7, so both are inside every signature preimage, and
re-versioning would destroy the kind-1 byte identity for separation the preimage
already carries.

## Transaction kinds

| Kind | Name | Body size | Unsigned | Signed |
| ---: | --- | ---: | ---: | ---: |
| 1 | `native_transfer` | 40 | 136 | 200 |
| 2 | `purchase_seat` | 165 | 261 | 325 |
| 3 | `activate_seat` | 68 | 164 | 228 |
| 4 | `mint_node` | 4 | 100 | 164 |
| 5 | `mint_referral` | 0 | 96 | 160 |
| 6 | `direct_issue` | 105 | 201 | 265 |
| 7 | `mint_node_verified` | 68 | 164 | 228 |
| 8 | `set_mint_biometric` | 69 | 165 | 229 |
| 9 | `add_manager` | 100 | 196 | 260 |
| 10 | `hub_verify` | 96 | 192 | 256 |

**Every kind is fixed-length, and two kinds now share a length.** Kinds 3 and 7
are both 68-byte bodies, because both name a seat and carry one verifier
signature. Version two recorded that "a decoder must dispatch on the kind byte
because a later version may add a kind whose length coincides", and version
three is that later version. The coincidence is therefore evidence that the rule
was right rather than a defect: a decoder that dispatched on length would
mis-execute a protected mint as an activation, and the vectors require the
signing message to change when a body is presented under another kind's
identifier.

Nothing a transaction carries scales with the seat population, so **the largest
transaction in version three is still 325 bytes**.

### Kind 2 — `purchase_seat`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 4 | seat ID `u32` | `0` through `99,999` |
| 84 | 32 | biometric identity hash | 32 octets |
| 116 | 32 | purchaser account ID | 32 octets |
| 148 | 1 | has referrer `bool` | `0x00` or `0x01` |
| 149 | 32 | referrer account ID | 32 octets, or 32 zero octets when absent |
| 181 | 64 | biometric verification signature | Ed25519 over the enrollment message |

The body is byte-for-byte version two's. What changes is an execution condition:
a named referrer must hold a HUB registration.

A `has_referrer` of `0x00` requires 32 zero octets in the referrer field. Any
other value is a second encoding of "no referrer", which
`protocol-primitives-v1` forbids as a non-minimal representation, and is
`MALFORMED_TRANSACTION`.

**The purchaser becomes the seat's first manager**, in the same transition that
writes the seat record. A seat with no manager is therefore unrepresentable,
exactly as a seat with no biometric identity hash is.

**What is deliberately absent is the payment.** No field here proves that BTC,
ETH, or an approved stablecoin was received, because that proof is a bridge
commitment and the bridge is a later milestone.

### Kind 3 — `activate_seat`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 4 | seat ID `u32` | `0` through `99,999` |
| 84 | 64 | biometric verification signature | Ed25519 over the activation message |

Activation is **one-time and permanent**. It carries no referrer, because the
referrer was recorded at purchase, and no activation height, because the height
is the executing block's. It starts the seat's 731 cycles and is the only
transition that does.

It also sets the seat's accumulation mark. See
[The accumulation cap](#the-accumulation-cap).

### Kind 4 — `mint_node`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 4 | seat ID `u32` | `0` through `99,999` |

**One button, everything, no quantity.** The transaction names a seat and
nothing else. It mints every permission the seat has accumulated and not yet
minted — its own met cycles and every reallocation share it won — and there is
no field by which a founder could mint part of it. That is founder-directed and
is the reason the body is four bytes.

A seat that has switched protection on refuses this kind with
`BIOMETRIC_REQUIRED` and must use kind 7.

### Kind 7 — `mint_node_verified`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 4 | seat ID `u32` | `0` through `99,999` |
| 84 | 64 | biometric verification signature | Ed25519 over the mint message |

The same settlement as kind 4, carrying a fresh action-bound biometric approval.
It is accepted **whether or not the seat has switched protection on**: the
signature is a strictly stronger proof, it is verified in either case, and
refusing it against an unprotected seat would spend a result code on a
transaction that proves more than it had to.

**Two kinds rather than an optional field, and the reason is length.** A single
mint kind carrying a presence flag and a 64-byte field would make every
unprotected mint 229 bytes instead of 164, and would need an execution rule for
a signature the seat did not ask for. Two fixed-length kinds cost one kind
identifier and no ambiguity.

### Kind 8 — `set_mint_biometric`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 4 | seat ID `u32` | `0` through `99,999` |
| 84 | 1 | enable `bool` | `0x00` or `0x01` |
| 85 | 64 | biometric verification signature | Ed25519 over the disable message, or 64 zero octets |

**The switch is asymmetric, and that asymmetry is the whole protection.**
Turning protection **on** requires only the manager's address signature, so the
signature field must be 64 zero octets and any other value is a non-minimal
representation and therefore `MALFORMED_TRANSACTION`. Turning it **off**
requires a verifier signature over the disable message.

A stolen wallet key can therefore neither mint against a protected seat nor
remove the protection first, which is exactly the attack the option exists to
defeat. A symmetric switch would have protected against nothing.

The asymmetry is checkable at admission in one direction only, and that is
correct: "the signature field must be zero when enabling" is a property of the
bytes, while "the signature must verify when disabling" reads the verifier key
from state.

### Kind 9 — `add_manager`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 4 | seat ID `u32` | `0` through `99,999` |
| 84 | 32 | manager account ID | 32 octets |
| 116 | 64 | biometric verification signature | Ed25519 over the manager message |

The Founder Constitution decides both factors: "Another registered manager may
initiate an addition, but the new authority becomes usable only after deep
biometric verification matches the permanent Founder identity." One transaction
carrying an existing manager's signature and a fresh verifier approval is that
sentence expressed as bytes; the new authority does not exist until both are
present, so there is no intermediate state in which a manager is pending.

**There is no removal transition.** The constitution states that "a recorded
manager address remains in the historical ledger forever" and that "loss of an
address is handled by adding a new verified manager, not by rewriting ownership
history", and the owner confirmed on 2026-08-14 that a Founder Seat's addresses
are permanent and add-only. A removal rule would decide what happens to a
compromised address, which nothing decides, so it is not invented here; the
consequence is recorded in
[What this specification does not establish](#what-this-specification-does-not-establish).

**Version three's requirement that the sender already be a manager is
superseded.** The owner decided on 2026-08-14 that HUB signing is what adds a
Founder Seat address, so that a founder who has lost every address still has a
path back. That is an authorization change and therefore a version four; ADR
0035 records it and the two questions that must be settled before it can be
written.

### Kind 10 — `hub_verify`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 32 | HUB uniqueness hash | 32 octets |
| 112 | 64 | biometric verification signature | Ed25519 over the HUB message |

The sender is the account being verified, so the body names no beneficiary. On
success the chain records that this account holds a HUB registration, the
uniqueness commitment the verifier attested, and the height at which it did.

**This is the smallest surface that makes the referrer rule enforceable, and no
more.** ADR 0033 widens HUB verification into an ecosystem-wide identity layer
with its own direct-mint incentive, and that layer is an M4 milestone specified
nowhere. What consensus needs in version three is a registry it can consult when
a purchase names a referrer, and that is all this kind writes.

**The chain does not enforce that one uniqueness hash reaches one account.**
Doing so would decide what happens to a verified human who loses the key to
their registered account, which sets what a user must own in order to keep
participating and is founder-reserved. The limit is recorded in
[What this specification does not establish](#what-this-specification-does-not-establish)
and stands exactly where version two's "that the biometric hash means anything"
already stands.

### Kind 6 — `direct_issue`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 1 | channel ID `u8` | `5`, `6`, `8`, or `9` |
| 81 | 32 | decision ID | 32 octets |
| 113 | 32 | beneficiary account ID | 32 octets |
| 145 | 8 | amount `u64` | nonzero |
| 153 | 32 | authorization | 32 octets |

Unchanged from version two, including its refusal. The channel ID is the
accepted manifest's array index. Index `7`, `founder_referral`, is **not**
admissible: it is consumed exactly by the daily referral assignment and kind 5.
Indices `0` through `4` are Founder Node distribution channels and are not
direct-mint. Any other value is `INVALID_CHANNEL`.

**Kind 6 is still specified and refused.** A conforming version-three chain
rejects every kind 6 with `UNAUTHORIZED` until `direct_issue_authority` is
accepted. ADR 0033 decided the *eligibility* of one of the four channels —
`hub_verified_user_incentives` pays HUB-verified humans — and left its *rate*
open, so the predicate as a whole is still undecided and refusing the kind is
still the conservative default.

### There is no transaction that records a day

Version three has no transaction by which anyone reports, claims, or evaluates a
cycle. **The chain writes each cycle's outcome itself**, at a block boundary,
for every activated seat at once. See
[Cycle assignment](#cycle-assignment-and-settlement).

## Admission

Admission operates on raw transaction bytes before ledger state is read, and its
version-one steps are unchanged in order and in meaning:

1. decode exactly one signed version-three transaction with no trailing bytes;
2. require the configured chain ID;
3. derive the sender account ID from the encoded public key;
4. strictly verify the Ed25519 signature over the signing message.

Step 1 classifies a wrong magic, schema version, transaction kind, or
signature-scheme identifier, a length that is not the exact length its kind
requires, a `has_referrer` or `enable` byte that is not `0x00` or `0x01`, a
non-minimal absent-referrer encoding, or a non-zero signature field on an
enabling `set_mint_biometric` as `MALFORMED_TRANSACTION`. The admission codes
are version one's, unchanged:

| Code | Name |
| ---: | --- |
| 1 | `MALFORMED_TRANSACTION` |
| 2 | `WRONG_CHAIN` |
| 3 | `INVALID_SIGNATURE` |

Because every kind is fixed-length, step 1 needs no length arithmetic beyond a
table lookup on the kind byte, and there is no count field anywhere in version
three that a decoder must bound before allocating.

**A bounded numeric field outside its range is not an admission failure.** A
seat ID of `100,000` decodes to a well-formed `u32` and is refused at execution
with `CYCLE_RANGE`. Shape belongs to admission and value belongs to execution.

**No biometric verification signature is checked at admission.** Every one of
them verifies against the ecosystem verifier key, which is ledger state, and
admission is defined to read none. They are therefore execution conditions
returning `UNAUTHORIZED`, and they produce a receipt.

Admission failures perform no state read or write, produce no application
receipt, and do not enter the application transaction root, exactly as in
version one.

## Authorization

Every kind is signed by an account, and every kind charges that account the
fixed fee. The Founder Constitution decides that fees apply here: "Every
protocol transaction fee is charged separately ... whether the transaction is a
purchase, transfer, issuance exercise, or another accepted state transition."

| Kind | Signer | Second factor |
| ---: | --- | --- |
| 1 | any account | none |
| 2 | any account | verifier signature over the enrollment message |
| 3 | a recorded manager of the seat | verifier signature over the activation message |
| 4 | a recorded manager of the seat | none; refused when the seat is protected |
| 5 | the account being paid | none |
| 6 | refused | the predicate is reserved |
| 7 | a recorded manager of the seat | verifier signature over the mint message |
| 8 | a recorded manager of the seat | verifier signature to disable; none to enable |
| 9 | a recorded manager of the seat | verifier signature over the manager message |
| 10 | the account being verified | verifier signature over the HUB message |

A sender the applicable rule refuses is `UNAUTHORIZED`.

### Any recorded manager, and what that costs

Version two admitted only the recorded purchaser. ADR 0033 replaces that with
the recorded manager set, and the Founder Constitution already says why: an
address can be lost, and the remedy is to add a new verified manager rather than
to rewrite ownership history.

**The mint therefore credits the signing manager's account, not the
purchaser's.** This is derived rather than chosen. If minted value went to the
recorded purchaser, a founder who lost that key could add a manager, mint, and
still be unable to reach a single unit, so the remedy the constitution names
would recover nothing. The recipient must be an address the founder can sign
with, and the only such address the transaction identifies is its sender.

**That trades away a containment property version two had, deliberately and with
a replacement.** Version two could say that "a stolen wallet key can mint, but
it can only mint to the seat's own recorded account, so it redirects nothing".
Version three cannot: a stolen manager key mints to itself. The replacement is
the optional biometric on minting, which ADR 0033 introduces for exactly this
attack, and the asymmetry of its switch is what makes it hold — a thief can
neither mint against a protected seat nor remove the protection first.

A founder who leaves protection off is in the position the constitution's own
wallet-signature rule describes: an ordinary signature is sufficient for an
ordinary action, and the sensitive actions — adding a manager, removing
protection — require a fresh biometric approval in every case.

### The biometric verification signatures

Six actions carry a 64-byte Ed25519 signature by the **ecosystem verifier key**,
a genesis-configured public key, over a domain-separated message binding the
exact action:

```text
enrollment_message =
  D("protocol-stack:v3:seat-enrollment") ||
  chain_id || u32(seat_id) || biometric_identity_hash ||
  purchaser_account_id || u64(valid_until_height)

activation_message =
  D("protocol-stack:v3:seat-activation") ||
  chain_id || u32(seat_id) || sender_account_id || u64(valid_until_height)

mint_message =
  D("protocol-stack:v3:seat-mint") ||
  chain_id || u32(seat_id) || sender_account_id || u64(valid_until_height)

mint_biometric_disable_message =
  D("protocol-stack:v3:mint-biometric-disable") ||
  chain_id || u32(seat_id) || sender_account_id || u64(valid_until_height)

manager_message =
  D("protocol-stack:v3:seat-manager") ||
  chain_id || u32(seat_id) || sender_account_id ||
  manager_account_id || u64(valid_until_height)

hub_message =
  D("protocol-stack:v3:hub-verification") ||
  chain_id || sender_account_id || hub_uniqueness_hash ||
  u64(valid_until_height)
```

Three of these messages carry identical field shapes and are separated only by
their labels, which is precisely what domain separation is for: a verifier
approval for an activation cannot be presented as an approval for a mint or for
removing protection.

**The message family is re-versioned to `v3` while the transaction labels are
not, and the asymmetry is deliberate.** No accepted byte string depends on the
verifier messages, so versioning them costs nothing and lets a verifier
implementation tell which contract a request belongs to without inspecting a
chain ID. The transaction signing and identity labels are the opposite case:
re-versioning them would destroy the kind-1 byte identity, which is the whole
compatibility argument.

The verification is performed by the chain against the recorded verifier key
using the same strict Ed25519 rules `protocol-primitives-v1` fixes for
transaction signatures. **No biometric image, template, or private linkage datum
enters consensus** — the chain sees a hash and a signature over it.

Each message binds the chain, the acting account, the exact subject, and an
expiry, so a verifier signature is **action-bound**: it cannot be replayed onto
another seat, another actor, another chain, or a later attempt after expiry.
`valid_until_height` in each message is the transaction's own trailer value, so
the verifier signature and the transaction expire together.

**The verifier now gates one payment path, and only by the operator's own
choice.** In version two the verifier signed purchases and activations and no
mint, so an unavailable verifier stopped new seats and stopped no income.
Version three keeps that for every seat that leaves protection off, and a seat
that switches it on has chosen to make verifier availability a precondition for
its own income. Whether an operator can make that choice for themselves without
recreating the failure mode institutionally is recorded for independent review
in ADR 0034 rather than settled here.

### What is still reserved

`direct_issue_authority` is unchanged and remains founder-reserved: the
eligibility and anti-abuse mechanics for the four undecided direct-mint
channels, and now also the rate of the one whose eligibility ADR 0033 settled.
Kind 6 is therefore specified and refused rather than given an invented
predicate.

## Canonical economy state

The version-three ledger state is version one's state — chain ID, supply limit,
total supply, fixed fee, height, fee pool, and the ordered account map — plus one
ordered map from canonical byte keys to canonical byte values.

A key is `u8(entry_kind)` followed by fixed-width big-endian fields, so
unsigned lexicographic key order is total and unambiguous and no key is a prefix
of another with a different meaning.

| Kind | Entry | Key | Key bytes | Value | Value bytes |
| ---: | --- | --- | ---: | --- | ---: |
| 1 | seat | `u8(1) \|\| seat_id:u32` | 5 | see below | 119 |
| 2 | channel | `u8(2) \|\| channel_id:u8` | 2 | `issued_atomic:u64 \|\| outstanding_atomic:u64` | 16 |
| 3 | cycle assignment | `u8(3) \|\| cycle_window:u64` | 9 | see below | 24 + 2⌈b/8⌉ |
| 4 | referral balance | `u8(4) \|\| account_id:bytes<32>` | 33 | see below | 24 |
| 5 | direct decision | `u8(5) \|\| decision_id:bytes<32>` | 33 | *(empty)* | 0 |
| 6 | typed custody | `u8(6) \|\| beneficiary_kind:u8 \|\| beneficiary_id:bytes<32>` | 34 | `amount_atomic:u64` | 8 |
| 7 | carry | `u8(7) \|\| channel_id:u8` | 2 | `carry_atomic:u64` | 8 |
| 8 | verifier key | `u8(8)` | 1 | `ed25519_public_key:bytes<32>` | 32 |
| 9 | seat manager | `u8(9) \|\| seat_id:u32 \|\| manager_account_id:bytes<32>` | 37 | *(empty)* | 0 |
| 10 | HUB registration | `u8(10) \|\| account_id:bytes<32>` | 33 | `hub_uniqueness_hash:bytes<32> \|\| verified_at_height:u64` | 40 |
| 11 | unreferred pool | `u8(11)` | 1 | `accrued_atomic:u64 \|\| minted_atomic:u64` | 16 |

An entry kind outside `1` through `11` cannot occur, because no transition
writes one and the state is not an untrusted input.

### The seat record

```text
biometric_identity_hash : bytes<32>
purchaser_account_id    : bytes<32>
has_referrer            : u8
referrer_account_id     : bytes<32>
is_activated            : u8
activation_height       : u64
minted_through_window   : u64
mint_requires_biometric : u8
manager_count           : u32
```

119 bytes; version two's 114 plus a protection flag and a manager count.

**Identity is present from the first byte of the seat's existence.** The hash,
the purchaser, and the purchaser's manager entry are written by the same
transition that creates the record, so a seat with no biometric binding and a
seat with no manager are both unrepresentable rather than disallowed.

**Activation is a flag, not an inferred sentinel.** `is_activated` is `0x00` or
`0x01`; `activation_height` must be zero while it is `0x00`. A purchased seat
that has never been activated is an ordinary, permanent state.

**`minted_through_window` is both the mint bookkeeping and the accumulation
clock.** Because a mint takes everything and cannot take part of it, one
high-water mark answers what a seat has already collected; because the
accumulation cap is measured in windows since that mark, the same field answers
whether the seat is still accruing. There is no per-cycle permission record, no
per-cycle replay key, and no separate unminted-cycle counter: a second field
holding `w - minted_through_window` would be a second representation of a fact
this one already carries.

**`manager_count` is state because the bound must be enforceable without a
scan.** The manager set is a family of presence-only entries under kind 9, and
counting them would require iterating a key range inside a transition.

### The manager set

A manager entry is presence-only: its key names the seat and the account, and
its value is empty. Membership is one lookup, addition is one write, and the
ordering of the set never enters a transition, so there is nothing for two
implementations to disagree about.

At most `16` managers may be recorded for one seat. **That bound is a resource
limit rather than a policy about founders.** Each addition already costs a fee
and a fresh biometric approval, so the bound is not what makes abuse expensive;
it is what makes the per-seat state a constant, which requirement 12 asks for.
Sixteen is far above any plausible device set and is recorded as an engineering
default in ADR 0034.

### The referral balance

```text
accrued_atomic            : u64
minted_atomic             : u64
collected_through_window  : u64
```

24 bytes; version two's 16 plus the referrer's own accumulation mark. The entry
is created lazily, at a referrer's first accrual, with
`collected_through_window` set to the window before that accrual, so a referrer
is never capped before anything has been credited to them.

### The cycle assignment record

```text
share_per_winner_atomic : u64
reallocated_count       : u32
winner_count            : u32
in_scope_count          : u32
bitmap_bits             : u32
accrued_bitmap          : ⌈bitmap_bits / 8⌉ octets, one bit per seat ID
winner_bitmap           : ⌈bitmap_bits / 8⌉ octets, one bit per seat ID
```

One record per cycle, written once, by the chain. `bitmap_bits` is the highest
in-scope seat ID plus one, so at the 100,000-seat capacity each bitmap is 12,500
bytes and the record is 25,024 bytes — the same size as version two's while
carrying one more field.

**The bitmaps are indexed by seat ID, and that is a repair.** Version two
indexed them by rank within the in-scope set, which means reading one seat's bit
required first deriving the whole in-scope set for that window — an `O(n)`
operation inside a transition version two described as `O(1)`. A seat-ID index
makes the lookup a shift and a mask. It costs nothing at capacity, where every
seat ID is in scope, and costs only leading zero bits on a chain whose highest
purchased seat ID exceeds its in-scope population.

**`accrued_bitmap` records what the settlement needs, which is not what version
two recorded.** A seat's bit is set when the window lies inside its own
731-cycle span, it met the cycle, **and** it was under the accumulation cap. A
mint therefore reads one bit rather than recomputing three conditions against
historical state. Version two stored a met bitmap and left the span and — as of
ADR 0033 — the cap to be re-derived at mint time.

**`reallocated_count` is what makes a winner's entitlement computable.** A
winner receives an equal share of *every* reallocated permission for that cycle,
so without the count the record cannot answer how much a winner won, and the
count cannot be recovered from the bitmaps: a seat with no accrued bit may be
outside its span, may have failed, or may have been capped, and only the second
and third reallocate.

**`in_scope_count` enters no transition.** It is the population the winner set
was ranked over, kept so that a record states its own basis.

**What the record no longer holds is the met bitmap.** Whether a seat met a
cycle is `uptime-measurement-v1`'s finalised record, which is where that
question belongs; duplicating it here would add 12,500 bytes per cycle to the
one storage term that already grows without bound, to answer a question no
transition asks.

### What is not state

**There is no pending-permission entry.** The verdict lives as one bit inside
its cycle's record, so the same fact costs one bit instead of eight bytes and is
stored once per cycle rather than once per seat-cycle.

**There is no winner commitment and no winner list in any transaction.** The
winner bitmap makes the set readable from state, so the largest transaction in
version three is 325 bytes.

**There is no per-seat unminted-cycle counter, and no `last_assigned_window`
entry.** The first is `w - minted_through_window`; the second is
`window_of_height(h) - 2` at the executing height, because
`uptime-measurement-v1` finalises window `w` at the first height of `w + 2`.

**`last_activation_height` is not state.** A chain's heights are monotone by
construction.

### Beneficiary kinds

The typed-custody key's `beneficiary_kind` byte is fixed here, which version two
used and never enumerated:

| Code | Beneficiary | Beneficiary ID |
| ---: | --- | --- |
| 1 | `venture_escrow` | 32 zero octets |
| 2 | `community_grants_escrow` | 32 zero octets |
| 3 | `developer_incentives_escrow` | 32 zero octets |
| 4 | `system_creator_company` | 32 zero octets |
| 5 | `direct_beneficiary` | the account named by kind 6 |

The four institutional beneficiaries are singletons and take a zero
beneficiary ID, so their keys are fixed strings rather than a family.

**A Founder Seat is not a beneficiary kind, and a referrer is not one either.**
Both are paid into ordinary account balances under ADR 0033's rule that minted
value lands on a spendable address, so the per-seat custody population version
two carried has left the state entirely.

### The economy Merkle tree and the version-three state root

Entries are sorted by unsigned lexicographic key and must not contain
duplicates. A leaf preimage uses the accepted `bytes` primitive — a `u32` length
followed by that many octets — for both key and value, so the boundary between
them is explicit rather than inferred from the entry kind:

```text
economy_entry = bytes(key) || bytes(value)

economy_tree({})            = H(D("protocol-stack:v3:economy-empty"))
economy_tree({entry})       = H(D("protocol-stack:v3:economy-leaf") || entry)
economy_tree(left || right) = H(D("protocol-stack:v3:economy-node") || l || r)
```

The tree shape is `protocol-primitives-v1`'s RFC 9162 construction, unchanged: no
leaf is duplicated and no padding leaf is inserted.

```text
state_root =
  H(
    D("protocol-stack:v3:state-root") ||
    u16(3) ||
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
label and the version field both differ from version one **and from version
two**, so a version-three state root is never equal to either, including over an
identical account set and an empty economy. Version two proved that against
version one; version three must prove it against both predecessors, because
distinct labels are strings rather than a chain and refusing a version-one
collision implies nothing about a version-two one.

## Version-three genesis

| Field | Encoding | Required value |
| --- | --- | --- |
| magic | `bytes<4>` | ASCII `PSGN` |
| schema version | `u16` | `3` |
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
chain_id = H(D("protocol-stack:v3:chain-id") || canonical_genesis_v3_bytes)
```

The field table is version two's with a different schema version, so the prefix
is still 110 bytes and the 1,048,576-byte canonical object bound still admits at
most 21,843 entries:

```text
110 + 48 * 21,843 = 1,048,574   accepted
110 + 48 * 21,844 = 1,048,622   rejected
```

Genesis writes the ten channel entries with both amounts zero, the ten carry
entries with zero, the ecosystem verifier key, and the unreferred pool entry
with both amounts zero. It writes nothing else: never a seat, a manager, a HUB
registration, a referral balance, a custody entry, or a cycle assignment.
Writing the fixed tables explicitly is what keeps an absent entry unambiguous.

**Three of version one's genesis requirements are relaxed, and each is forced by
founder direction rather than chosen.** The Founder Constitution states that
"there is no founder-directed genesis allocation", so a Founder Economy chain
must be able to open with `total supply` zero and `account count` zero, which
version one forbids. The fixed fee is relaxed to permit zero for the consequence
that follows: with a zero allocation and a nonzero fee, no account can pay for
the first transaction.

**That bootstrap is a real gap and is recorded rather than closed here**, exactly
as version two records it. Every path to a first payable balance is external and
belongs to the bridge milestone.

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

**These six are envelope conditions, not transfer conditions the economy
inherits**, and they are shared precisely because the header and trailer are
shared. That is why the version-one result numbers keep their exact meanings
across all ten kinds rather than being re-numbered per kind.

Every non-success result performs no state write and charges no fee. It still
produces a receipt and enters the ordered transaction root.

### Kind 2 — purchase seat

Rejection conditions, in this order:

1. a `seat_id` outside `0..99,999` is `CYCLE_RANGE`;
2. an already-purchased `seat_id` is `REPLAY`;
3. a `referrer_account_id` equal to the `purchaser_account_id` is
   `INVALID_REFERRER`;
4. a named referrer with no HUB registration is `NOT_HUB_VERIFIED`;
5. a biometric verification signature that does not verify against the recorded
   verifier key over the enrollment message is `UNAUTHORIZED`.

On success the transition writes the seat record with `is_activated` false,
`activation_height` zero, `minted_through_window` zero,
`mint_requires_biometric` false, and `manager_count` one, and writes the
purchaser's manager entry. It issues nothing, reserves nothing, and credits
nothing.

**The HUB check precedes the signature check and follows the self-referral
check**, for the reason version two gives about ordering: conditions that are
properties of the request and of chain tables are reported as defects in the
request, and authorization comes last, so a submitter fixing a bug is not told
that every mistake is an authorization failure.

**The HUB requirement is the founder's answer to a mistyped referrer.** ADR 0033
records that validating an address format would not have solved it, because a
well-formed address nobody controls still strands 731 cycles of benefit. A
HUB-verified account exists and belongs to a distinct human, so the condition
the chain checks is the one that matters.

### Kind 3 — activate seat

Rejection conditions, in this order:

1. a `seat_id` outside `0..99,999` is `CYCLE_RANGE`;
2. an unpurchased `seat_id` is `SEAT_NOT_PURCHASED`;
3. a sender that is not a recorded manager of the seat is `UNAUTHORIZED`;
4. an already-activated seat is `REPLAY`;
5. a biometric verification signature that does not verify over the activation
   message is `UNAUTHORIZED`.

On success the transition sets `is_activated`, writes `activation_height` as the
executing block height, and sets `minted_through_window` to
`window_of_height(activation_height)`, which is the window before the seat's
first cycle window.

**Setting the mark at activation is what makes the accumulation cap
well-defined.** A mark left at zero would place a seat activated at window 4,000
more than the cap's distance from its own first cycle, so its first permission
would be reallocated the moment it was earned.

**Activation is permanent and has no inverse.** No transition clears
`is_activated`, moves `activation_height`, or re-activates a seat.

**`HEIGHT_RANGE` and `HEIGHT_NOT_MONOTONIC` are unrepresentable.** Here the
height is the executing block's, which `ledger-transition-v1` already fixes as
the sole successor of the previous height.

### Kinds 4 and 7 — mint node

Rejection conditions for kind 4, in this order:

1. a `seat_id` outside `0..99,999` is `CYCLE_RANGE`;
2. an unpurchased `seat_id` is `SEAT_NOT_PURCHASED`;
3. an unactivated seat is `SEAT_NOT_ACTIVATED`;
4. a sender that is not a recorded manager is `UNAUTHORIZED`;
5. a seat whose `mint_requires_biometric` is set is `BIOMETRIC_REQUIRED`;
6. `minted_through_window` already equal to the last assigned window, or no
   window assigned yet, is `NOTHING_TO_MINT`;
7. a leg that does not fit its channel is `CHANNEL_CAP`.

Kind 7 replaces condition 5 with a biometric verification signature that does
not verify over the mint message, which is `UNAUTHORIZED`, and is otherwise
identical.

On success the transition walks every window in

```text
( minted_through_window , min(last_assigned_window, minted_through_window + 30) ]
```

and for each window that has an assignment record:

- if the seat's **accrued** bit is set, it settles that cycle's full base
  permission — the four institutional legs to their typed custody and
  34,200,000,000 atomic units to the **sender's account balance**;
- if the seat's **winner** bit is set, it settles `reallocated_count` equal
  shares of a reallocated permission, with each of the five legs divided by
  `winner_count`, so the escrows and the System Creator receive their portions
  at this mint rather than at a mint the reallocating seat may never make.

It then sets `minted_through_window` to the last assigned window, moves each leg
from `outstanding_atomic` to `issued_atomic`, and increases `total_supply` by
the total minted. It is atomic: every beneficiary is credited or none is.

**The walk is bounded by the cap and by nothing else.** No window beyond
`minted_through_window + 30` can carry a bit for this seat, because the
assignment that wrote it applied the same bound with the same mark; the mark
changes only at a mint, and a mint sets it to the last assigned window, so every
window in `(mark, last]` was assigned while the mark held its current value.
The bound is therefore exact rather than conservative, and the largest possible
mint walks 30 records regardless of how long a founder waited.

**A mint that finds nothing still advances the mark, and that is required rather
than convenient.** A seat that failed every cycle for two months has accrued
nothing, and if its mark could not move it would be permanently past the cap and
could never accrue again. `NOTHING_TO_MINT` is therefore reserved for the case
where the mark is already at the last assigned window — a genuinely empty
action — and a mint that collects zero units while moving a stale mark succeeds,
charges the fee, and issues nothing.

**A reallocated cycle contributes nothing to the reallocating seat's own mint.**
The whole permission moved to that cycle's winners when the cycle was assigned,
which is what makes the escrows independent of whether that founder ever mints.

### Kind 5 — mint referral

Rejection conditions, in this order:

1. no referral balance entry for the sender, or an entry whose
   `accrued_atomic` equals its `minted_atomic` **and** whose
   `collected_through_window` already equals the last assigned window, is
   `NOTHING_TO_MINT`;
2. a leg that does not fit the channel is `CHANNEL_CAP`.

On success the transition mints the whole outstanding difference to the
**sender's account balance**, sets `minted_atomic` equal to `accrued_atomic`,
sets `collected_through_window` to the last assigned window, and increases
`total_supply`.

**There is no seat and no authorization check.** The signer is the beneficiary,
so there is nobody else the transition could pay and nothing to authorize. The
per-seat biometric option does not reach here, because it is a property of a
seat and a referrer need not hold one.

**A referral mint that collects nothing still advances the mark**, for the same
reason a node mint does: without it a referrer whose referred seats have all
completed their 731 cycles could never accrue for a seat referred later.

### Kind 8 — set mint biometric

Rejection conditions, in this order:

1. a `seat_id` outside `0..99,999` is `CYCLE_RANGE`;
2. an unpurchased `seat_id` is `SEAT_NOT_PURCHASED`;
3. a sender that is not a recorded manager is `UNAUTHORIZED`;
4. a seat whose `mint_requires_biometric` already equals `enable` is `REPLAY`;
5. when `enable` is false, a biometric verification signature that does not
   verify over the disable message is `UNAUTHORIZED`.

On success the transition sets `mint_requires_biometric` to `enable`. It issues
nothing and requires no activation, so a seat may be protected before it is ever
activated.

### Kind 9 — add manager

Rejection conditions, in this order:

1. a `seat_id` outside `0..99,999` is `CYCLE_RANGE`;
2. an unpurchased `seat_id` is `SEAT_NOT_PURCHASED`;
3. a sender that is not a recorded manager is `UNAUTHORIZED`;
4. a `manager_account_id` already recorded for the seat is `REPLAY`;
5. a seat already holding 16 managers is `MANAGER_LIMIT`;
6. a biometric verification signature that does not verify over the manager
   message is `UNAUTHORIZED`.

On success the transition writes the manager entry and increments
`manager_count`.

### Kind 10 — HUB verify

Rejection conditions, in this order:

1. an already-registered sender is `REPLAY`;
2. a biometric verification signature that does not verify over the HUB message
   is `UNAUTHORIZED`.

On success the transition writes the HUB registration entry with the attested
uniqueness hash and the executing block height. It issues nothing: the
`hub_verified_user_incentives` channel pays through kind 6, whose predicate is
reserved and whose rate ADR 0033 leaves open.

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
sender first. The vectors record that unreachability as a derived property.

## The accumulation cap

ADR 0033 directs that a seat may accumulate at most a bounded number of unminted
cycles, names roughly thirty days, and delegates the exact figure. Version three
fixes it at **30 cycles**, which is 30 windows on the accepted grid and
therefore thirty 24-hour-target days.

```text
MINT_ACCUMULATION_CAP = 30
```

A seat accrues in window `w` only when

```text
w <= minted_through_window + MINT_ACCUMULATION_CAP
```

and a referrer accrues in window `w` only when

```text
w <= collected_through_window + MINT_ACCUMULATION_CAP
```

**The cap is measured in windows since the last collection rather than in
accrued cycles, and that is what bounds the mint.** A counter of accrued cycles
expresses the same intent and bounds nothing: thirty accruals can be spread over
any number of windows, so a mint would still have to walk every window since the
last one to find them. Measuring in windows makes the walk range a constant,
which is the cost ADR 0033 says the cap is there to close.

The two forms agree wherever a seat is running: a seat that meets every cycle
accrues once per window, so thirty windows and thirty accrued cycles are the
same thirty cycles. They differ only for a seat that has been failing, and there
the window form is the one that keeps the rule's promise — a founder who has not
pressed the button in a month is not accruing, whatever the reason.

**Reaching the cap is always recoverable by one button press.** A mint advances
the mark to the last assigned window whether or not it collected anything, so a
capped seat is never locked out; what it cannot do is recover the cycles that
were reallocated while it was over the cap.

**What the cap does not touch is what the seat has already earned.** A seat at
the limit is full rather than emptied: its accumulated unminted value is intact
and waiting, and what it loses is the new days it had no room for. ADR 0035
records the owner's statement of this.

**This is not a monetary penalty and does not contradict the constitution's
no-slashing rule.** An unminted permission's units do not exist and are not
circulating; the constitution says so directly and already accepts that a failed
cycle's portion moves to other seats and cannot be recovered later. Nothing
already owned is burned, seized, or reduced. ADR 0034 records the one respect in
which the two cases differ, for independent review.

## Cycle assignment and settlement

**No transaction records a cycle.** At the first height of window `w + 2`, when
`uptime-measurement-v1` finalises window `w`, ordered block execution writes
window `w`'s cycle-assignment record and nothing else does.

The transition, in order:

1. derive the in-scope seat set for `w` from the seat table, and set
   `bitmap_bits` to the highest in-scope seat ID plus one, or zero when the set
   is empty;
2. read each in-scope seat's uptime from the finalised measurement and derive
   whether it met the cycle;
3. derive the **winner set** — the seats at the highest uptime among those that
   met the cycle **and are under the accumulation cap for `w`** — and set their
   bits;
4. for each in-scope seat whose 731-cycle span contains `w`: set its accrued bit
   when it met the cycle and is under the cap, and otherwise count its
   permission as reallocated;

   Steps 3 and 4 are one rule stated twice, and the founder states it in one
   sentence: **a cycle a seat cannot collect because it is at the cap is treated
   exactly as a cycle it failed.** Both consequences then follow from rules that
   already exist — the day's permission goes to the best performers because that
   is what happens to a failed cycle, and the capped seat is not one of them
   because a winner must itself have met the cycle. The two formulations select
   the same seats, and ADR 0035 records the confirmation;
5. add one base permission's `outstanding_atomic` per in-scope seat whose span
   contains `w`, per leg;
6. compute the per-winner share of one reallocated permission by dividing each
   leg by `winner_count`, then move `reallocated_count` times each leg's
   remainder **out of** `outstanding_atomic` and into that channel's carry;
   when `winner_count` is zero the whole reallocated amount moves to the carry;
7. accrue the referral leg for each in-scope seat whose span contains `w`: to
   the seat's referrer when the seat has one and that referrer is under the cap,
   and to the unreferred pool otherwise; `founder_referral.outstanding_atomic`
   increases by one referral leg in every case.

**A capped seat is excluded from the winner set, and the founder confirmed it.**
ADR 0033 states that a capped seat's permissions "go to that cycle's best
performers instead". A capped seat can accrue nothing, so including it in the
division would send its share nowhere and make that sentence false for the
fraction concerned. Excluding it is the reading under which every reallocated
unit reaches a seat that can collect it. ADR 0035 records the owner's own
statement of the same rule, which is shorter: a capped day is a failed day, and
everything else follows from the failed-cycle rules already written.

**Assignment is one automatic event per cycle, in cycle order, and it is
founder-directed.** Nothing is claimed, requested, or reported, so a founder who
never touches the dashboard still accrues everything they are owed, up to the
cap.

**A window with an empty in-scope set writes no record.** A mint that reaches
such a window in its walk finds nothing and treats it as neither an accrual nor
a win, so an absent record and a record with both bits clear are the same fact.

### The two-cycle lag is forced, not chosen

The assignment for cycle `w` cannot execute at the end of `w`. A cycle's uptime
is not final until its Ecosystem AI dispute window has expired, which
`uptime-measurement-v1` fixes at the whole of window `w + 1`, so the earliest
height at which `w`'s outcome is known is the first height of `w + 2`. That also
fixes the last assigned window at any height `h` as `window_of_height(h) - 2`,
with no window assigned while `window_of_height(h)` is below `2`.

### Nothing is left unassigned

Every in-scope seat whose span contains the cycle produces exactly one base
permission, so the total assigned per cycle is the number of such seats times
57,430,000,000 atomic units, and the Founder Node distribution channels are
consumed exactly when all 100,000 seats complete all 731 cycles:

```text
57,430,000,000 * 100,000 * 731 = 4,198,133,000,000,000,000
```

which is the accepted manifest's Founder Node subtotal. **A failed or capped
cycle removes nothing from the total** — it moves the whole permission to that
cycle's winners — and the integer remainder of each equal split is carried
forward per channel rather than dropped.

If no seat is eligible to win, the winner set is empty and the whole reallocated
amount is carried forward, which is the founder-directed rule for that case.

**An unminted permission is not an unassigned one.** A seat that never mints
leaves its value recorded and unspent forever, which the constitution intends:
until a permission is minted its units do not exist and are not circulating.

## Receipt

Each admitted transaction produces exactly one 56-byte receipt:

| Offset | Size | Field |
| ---: | ---: | --- |
| 0 | 4 | ASCII `PSRC` |
| 4 | 2 | receipt version `3` |
| 6 | 32 | transaction ID |
| 38 | 1 | transaction kind |
| 39 | 1 | result code |
| 40 | 8 | fee charged; the fixed fee on success, otherwise zero |
| 48 | 8 | issued atomic units; zero for every non-issuing kind and every failure |

Unknown result codes, a kind outside `1` through `10`, a nonzero failed fee, and
a nonzero `issued_atomic` on a failure are invalid. Receipt order is the
admitted transaction order. Receipts remain deterministic outputs and are still
not part of the state-root preimage.

**The layout is version two's and the version field is not.** No field moves and
no width changes, but the admissible kind and result-code ranges both widen, so
a version-two reader presented with a version-three receipt must be able to tell
that it is looking at a contract it does not know. Leaving the version at `2`
would make such a reader classify a kind-7 receipt as invalid rather than as
unknown, which is the misreading a version field exists to prevent.

The non-issuing kinds are 1, 2, 3, 8, 9, and 10. Issuance happens only at the two
node mints, the referral mint, and direct issue.

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
| 21 | `NOT_HUB_VERIFIED` | new |
| 22 | `BIOMETRIC_REQUIRED` | new |
| 23 | `MANAGER_LIMIT` | new |

Codes `0` through `20` keep their exact version-two meanings, and `0` through
`8` their exact version-one meanings, so the space extends contiguously rather
than being re-numbered. **A version-three chain is a different chain from a
version-two chain, so nothing forces this**; it is kept because a reader,
a wallet, and an operator's runbook should not have to relearn a code that names
the same condition.

The three new codes are each a condition version two could not have.
`NOT_HUB_VERIFIED` requires a registry version two had no entry kind for.
`BIOMETRIC_REQUIRED` requires a per-seat option version two did not offer.
`MANAGER_LIMIT` requires a manager set version two did not hold.

### The model mapping is total and unchanged

Every one of `founder-economy-simulator-v3`'s twenty-four result codes has
exactly one disposition here, and the vectors require the three sets to
partition it. The model is unchanged between transition versions two and three,
so the partition is unchanged.

| Disposition | Count | Codes |
| --- | ---: | --- |
| carried | 11 | `OK`, `CYCLE_RANGE`, `INVALID_REFERRER`, `REPLAY`, `SEAT_NOT_ACTIVATED`, `INVALID_CHANNEL`, `ZERO_AMOUNT`, `MISSING_RESEARCH_INPUT`, `INVALID_RESEARCH_INPUT`, `NOT_ELIGIBLE`, `CHANNEL_CAP` |
| guard | 2 | `ARITHMETIC_OVERFLOW`, `INVARIANT` |
| unrepresentable | 11 | `MISSING_UPTIME_RECORD`, `INVALID_UPTIME_RECORD`, `INCONSISTENT_UPTIME_RECORD`, `PERMISSION_NOT_FOUND`, `HEIGHT_RANGE`, `HEIGHT_NOT_MONOTONIC`, `WINDOW_BEFORE_ISSUANCE`, `WINDOW_AFTER_ISSUANCE`, `WINDOW_NOT_FOR_CYCLE`, `SEAT_NOT_IN_SCOPE`, `INCOMPLETE_UPTIME_RECORD` |

**The two guards do not become receipt codes.** `ledger-transition-v1` already
decides their treatment: a checked-arithmetic violation "is an internal
invariant failure that invalidates the proposed block, not a transaction
result".

**Six codes here have no model counterpart**, three from version two and three
new, and every one of them names a condition a model with no signer, no purchase
transition, no manager set, no registry, and no take-everything mint cannot
reach.

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

Invariant 2's third term is empty on a version-one state. Invariant 6 is the one
version-one rule this version revises, and `ledger-transition-v1` names exactly
that revision as requiring a new transition version.

The manifest's invariants hold at every accepted state:

```text
for each channel: issued_atomic + outstanding_atomic <= cap_atomic
total_supply = genesis_total_supply + checked_sum(channel.issued_atomic)
total_supply + checked_sum(channel.outstanding_atomic) <= supply_limit
```

and the carry identity holds per channel:

```text
for each Founder Node channel c, with leg(c) its per-cycle amount:
  issued(c) + outstanding(c) + carry(c)
    = assigned_cycle_permissions * leg(c)
```

where `assigned_cycle_permissions` is the number of base permissions the chain
has assigned across every cycle so far — one per in-scope seat whose span
contains that cycle, whether it accrued to that seat or was reallocated.

**It is an equality, and step 6 of the assignment is what makes it one.** The
carried remainder is moved out of the channel's outstanding amount rather than
added beside it; adding it beside would count the same value twice and no
accepted journal would balance. Version two stated this identity and did not
state the subtraction, which version three repairs.

The referral channel satisfies the same identity without a carry, because
nothing about a referral is divided:

```text
issued(founder_referral) + outstanding(founder_referral)
  = assigned_cycle_permissions * 3,420,000,000
outstanding(founder_referral)
  = sum over referrers of (accrued - minted) + (pool.accrued - pool.minted)
```

There is no burn, no negative issuance, and no transition that decreases
`total_supply`, so the fixed maximum is a bound that only ever tightens.

## Resource limits and storage bounds

Version one's limits are unchanged: at most 65,535 raw inputs and 65,535
admitted transactions per block, and a 1,048,576-byte canonical object bound.

**The largest transaction in version three is 325 bytes**, and **the longest
mint walk is 30 assignment records**, which is the bound version two could not
state.

| Entry | Bound at 100,000 seats | Derivation |
| --- | ---: | --- |
| seats | 12,400,000 bytes | `100,000 * (5 + 119)` |
| seat managers | 59,200,000 bytes | `100,000 * 16 * (37 + 0)` |
| channels | 180 bytes | `10 * (2 + 16)` |
| carries | 100 bytes | `10 * (2 + 8)` |
| typed custody | 168 bytes | `4 * (34 + 8)` |
| referral balance | 57 bytes per referrer | `33 + 24` |
| HUB registration | 73 bytes per verified account | `33 + 40` |
| verifier key | 33 bytes | one entry |
| unreferred pool | 17 bytes | one entry |
| cycle assignment | 25,033 bytes per cycle | `9 + 24 + 2 * 12,500` |

**Typed custody has collapsed from 4,200,000 bytes to 168.** Version two held one
custody entry per Founder Seat because minted value landed in typed custody;
under ADR 0033 it lands in an ordinary account balance, so only the four
institutional singletons remain, and the accounts that replace them are accounts
those founders already hold in order to pay a fee.

**The manager set is the one new population, and it is bounded by construction.**
Its worst case assumes every seat records the maximum 16 managers, which no
plausible deployment reaches; the point of the bound is that the figure is a
constant at all.

**One bound is not a constant, and it is the same weakest result version two
recorded.** Cycle assignment records accumulate at one per cycle and are never
deleted, because a seat may mint at any time. At full capacity that is 25,033
bytes per cycle, about 9.1 MB per year at the pinned three-second commit
interval.

**The cap does not close it, and stating that plainly is the point.** The cap
bounds how *many* records a mint reads; it does not bound how *old* they are. A
seat whose mark is a thousand windows behind still walks
`(mark, mark + 30]`, so those thirty records — a thousand windows old — must
still be retained. The retention requirement is therefore unchanged from version
two, and only the per-transaction work is now a constant.

No pruning rule follows from the cap, and none is invented. Deleting a record
would need every seat to have passed it, and a seat that never mints never does.
The three mitigations version two enumerated and refused stand exactly as it
left them; the run-length encoding of an all-ones cycle is still the one worth
revisiting, and still needs a single canonical form rather than two.

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

The accumulation cap reads `minted_through_window` and `collected_through_window`
as they stand in the executing block's tentative state, so a seat's eligibility
for a cycle is a function of committed state and the executing height alone.

## Compatibility boundary

This is requirement 6 stated exactly, extended to two predecessors.

**Transaction bytes.** A version-one signed transfer is a version-three kind-1
transaction, byte-for-byte, with the same signing message, the same transaction
ID, and the same execution result numbers. A version-one node presented with
kinds 2 through 10 rejects them at admission step 1 as `MALFORMED_TRANSACTION`,
which is version one's existing rule for an unknown kind. A version-two node
rejects kinds 7 through 10 the same way. No version-one or version-two byte
sequence acquires a new meaning.

**State.** A version-three state is a version-one state plus one ordered economy
map. Every version-one invariant holds, with conservation extended by the typed
custody term, which is empty on a version-one state.

**Roots.** The version-three state root has a distinct domain label and a
distinct version field from both predecessors, so no earlier root is
reinterpreted and no version-three root collides with one. The accounts subtree
construction is unchanged, so a version-three root contains the version-one
accounts root as a value.

**Genesis and chain identity.** Version-three genesis has a different schema
version and a different chain-ID domain label from both predecessors, so a
version-three chain has a different chain ID from any version-one or
version-two chain. **A version-three Founder Economy chain is a new chain, not a
migration of a version-two one.** There is no upgrade block and no state
translation: the two contracts are alternative chains, and only one of them will
ever carry value.

**Denomination and supply limit.** Unchanged from version two. The version-one
devnet records nine decimal places and the economy contract eight, which
`ledger-transition-v1` settles as display metadata over one canonical integer
type, and version one's supply limit is a configured genesis field rather than a
protocol constant.

**What is not claimed.** No accepted M1 or version-two vector, digest, receipt,
root, or recorded devnet result changes, and none is recomputed under this
specification.

## Versioning and compatibility of this document

The envelope layout, the ten kind identifiers and their bodies, the admission
order, the state key space and value encodings, the beneficiary-kind space, the
tree and root constructions, the genesis layout, the receipt layout, the numeric
result codes, the accumulation cap, and the rejection orders are immutable for
version three. A changed field, code, order, or semantic rule requires a new
transition version and an ADR; it must not reinterpret a version-three
identifier.

Versions one, two, and three coexist as documents. The v1 artifacts are the
accepted M1 evidence and the v2 artifacts are the accepted 2026-08-13 evidence;
both remain in place, passing, and unedited.

One authorization predicate is the only point at which this version is
deliberately incomplete. Accepting it adds a rule and activates an
already-specified path; it does not change any byte defined here.

## What this specification does not establish

- **Direct-channel eligibility.** `direct_issue_authority` remains named and
  undefined, and kind 6 is refused because of it. ADR 0033 decided the
  eligibility of `hub_verified_user_incentives` and left its rate open, so the
  predicate as a whole is still reserved.
- **The HUB identity layer.** Kind 10 records an attestation; it does not build
  the service that produces one. The construction of a per-person signature, the
  capture pipeline, unlinkability, retention, and the threat model are the
  identity milestone's, and ADR 0033 widened that milestone to every participant
  class.
- **That one human holds one HUB registration.** The chain does not check that a
  uniqueness hash reaches at most one account, because enforcing it decides what
  happens to a verified human who loses their key, which is founder-reserved.
  Until it is decided, HUB verification is exactly as strong as the off-chain
  verifier, which is where the seat biometric hash already stands.
- **Manager compromise.** There is no removal transition, because the
  constitution names manager addition as the remedy for a *lost* address and
  decides nothing about a *stolen* one. The owner confirmed permanence on
  2026-08-14: a Founder Seat's addresses are add-only and can never be removed.
  A compromised manager address therefore retains mint authority permanently.
  The founder's defence is to switch protection on, which needs only their own
  address signature and which the thief cannot undo, and it works — but only for
  value not yet minted, and only once the founder notices.
- **Recovery when every manager key is lost.** Version three has no path: kind 9
  requires an existing manager's signature, so a founder holding none cannot add
  one. The owner closed this on 2026-08-14 — HUB signing is what adds a Founder
  Seat address — and closing it changes an authorization rule, which
  [ADR 0035](../decisions/0035-founder-answers-on-payout-the-cap-and-hub-recovery.md)
  records as requiring `economy-transition-v4`.
- **The payment.** Nothing here proves that BTC, ETH, or an approved stablecoin
  was received for a seat. The external settlement is a bridge commitment.
- **Verifier key rotation.** The ecosystem verifier key is written at genesis and
  no transition changes it, so a compromised or retired key can only be replaced
  by a new chain. Rotation decides who controls admission to the economy, so it
  is not invented here. Version three widens the consequence: the key now also
  gates protected mints and manager additions, so its unavailability stops more
  than it did in version two.
- **That any of this executes.** No C++ implementation exists. This document is
  a contract, and requirement 10 is where it becomes behavior; requirement 11 is
  where a C++ and a Python implementation are required to agree on fixed bytes.
- **The measurement.** Everything `uptime-measurement-v1` does not establish is
  inherited unchanged.
- **The bootstrap.** A chain with no genesis allocation and a nonzero fee cannot
  execute its first transaction.
- **Distribution.** No kind here distributes transaction fees or commercial
  revenue to active seats.
- **The unreferred pool's payout.** Version three specifies where the pool's
  value comes from — unreferred seats and forfeited referral accruals — and adds
  a state entry to hold it. It does not specify the month, the ranking snapshot,
  or the payout transition, so that value accumulates against a rule that does
  not exist yet. ADR 0033 decided the rule's *shape* — the single best performer,
  with exact ties sharing — and the month definition remains specification work.
- **Seat concentration.** The per-principal 1,000-seat bound is not enforced by
  any transition here, because enforcing it requires knowing that two biometric
  hashes belong to one human.

## Required vectors and evidence

`test-vectors/economy-transition-v3.txt` is normative. It fixes:

- the envelope decomposition, every kind's body layout, and every unsigned and
  signed length, including that kinds 3 and 7 share one and that the decoder
  therefore dispatches on the kind byte;
- **the kind-1 identity**, by requiring the version-three encoder to reproduce
  the accepted `protocol-primitives-v1` unsigned bytes, signed bytes, and
  transaction ID exactly;
- the cross-kind separation, by presenting each body under another kind's
  identifier and requiring the signing message to change;
- every admission rejection, each produced by a live run over a minimally
  mutated input with a positive control on the unmutated one, including the
  non-minimal absent referrer and the non-zero signature on an enabling
  `set_mint_biometric`;
- the six biometric message constructions, that they are pairwise distinct on
  identical fields, and that a verifier signature bound to one seat, actor,
  chain, or expiry is refused on any other;
- the complete result-code table, its contiguity, the preserved version-one and
  version-two meanings, and the three-way partition of the economy model's
  twenty-four codes;
- every state key and value encoding, the beneficiary-kind space, the empty,
  genesis, and populated economy roots, and the version-three state root;
- **the three-way non-collision** of version-one, version-two, and
  version-three roots over an identical account set and an empty economy,
  preceded by the requirement that the version-one construction the comparison
  uses reproduces the accepted `protocol-primitives-v1` account, state, and
  transaction roots exactly;
- version-three genesis bytes, the chain ID, that the chain ID differs from a
  version-two genesis with identical fields, and the 21,843-entry bound at its
  accepting and rejecting values;
- the receipt layout, its new version, its invalid combinations, and its round
  trip;
- **the accumulation cap**: the accrual predicate at the boundary window and one
  past it, the exact walk range for a fresh seat, a current seat, and a seat
  that has not minted for a year, and that no window outside that range can
  carry a bit for the seat;
- the cycle assignment: the accrued and winner bitmaps over a population that
  exercises a failed seat, a capped seat that met the cycle, a tie at the
  maximum, a seat that met below the maximum, and a seat outside its own span
  but still in scope; the per-winner share, `reallocated_count`, and every leg's
  carried remainder; and the empty-winner case;
- **that a capped seat is excluded from the winner set**, by a fixture in which
  the highest uptime in the cycle belongs to a capped seat and the winner set is
  the next-highest;
- the mint walk: that a seat collects exactly its own accrued cycles and its own
  winner shares, that `minted_through_window` advances to the last assigned
  window, that a mint collecting nothing still advances a stale mark, that an
  immediate second mint returns `NOTHING_TO_MINT`, and that the five legs of a
  reallocated permission reach the escrows and the System Creator at the
  winner's mint; and
- the referral accrual: that an unreferred seat and a capped referrer both route
  to the unreferred pool, and that the referral channel's identity holds across
  both destinations.

The conservation vectors are the load-bearing ones. Across a complete assignment
and mint sequence, every channel's `issued + outstanding + carry` must equal the
number of assigned permissions times that channel's per-cycle leg, exactly. A
settlement defect that moved value between beneficiaries would satisfy a
per-transaction check and fail this one.

The verifier independently derives rather than restates every recorded value.
Its independence is `tools/economy-transition-v3-vectors/expected.py`, which
imports nothing from `simulation/` and restates the version-one layouts, the
Founder Constitution's tables, and the accepted manifest's channel order by
hand, so a value both sources agree on has been reached from the accepted
documents and from the model independently. It fails when a recorded key is
never derived, when a derived key is absent from the file, and when any recorded
value is tampered with.

Acceptance requires full GitHub-hosted verification on the exact commit. Passing
these checks establishes an exact, auditable encoding and compatibility
boundary. It does not establish that the transitions execute, that the economy
is safe, that a purchase was paid for, that a biometric hash means anything, or
that the resource bounds are adequate under adversarial load.
