# Economy transition v6

Status: Accepted M3 consensus transition contract; not yet implemented in C++

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
The change is classified as primitive, encoding, authority, state-transition
shape, and compatibility.
[ADR 0044](../decisions/0044-economy-transition-v6-the-identity-account.md)
records the alternatives and the decision.

**Version six exists because the founder direction of 2026-08-15 makes a
verified identity the root of every account.** Five ADRs carry that direction:
[ADR 0039](../decisions/0039-hub-verification-is-mandatory-for-everyone.md) makes
verification mandatory,
[ADR 0040](../decisions/0040-holder-addresses-and-revocable-signers.md) replaces
addresses-as-identity with keyless escrows and revocable signers,
[ADR 0041](../decisions/0041-the-seat-is-tied-to-the-identity-not-an-address.md)
ties a Founder Seat to the identity so that it has no address at all,
[ADR 0042](../decisions/0042-the-hub-entry-airdrop-and-the-verified-user-rate.md)
funds a brand-new person's first action, and
[ADR 0043](../decisions/0043-founder-answers-on-reach-asymmetry-forfeiture-and-signers.md)
settles the four decisions the founder-decision gate stopped this slice to ask.

[`economy-transition-v5`](economy-transition-v5.md) and every version before it
are not edited, retracted, or reinterpreted. Their vectors and digests are the
record of what was verified, and the repository's rule is that a changed
transition is a new version rather than an edit.

## What version six changes

| | v5 | v6 |
| --- | --- | --- |
| What an account is | a public-key hash | a keyless escrow beneath an identity |
| Who may hold an account | anyone with a key | only a registered identity |
| Signing authority | the account's own key | a revocable signer assigned to that escrow |
| Registration | links an existing account | creates the identity, its first escrow, its first signer, and pays the entry airdrop |
| A transfer to a new recipient | creates the recipient account | is refused |
| Biometric protection | a per-seat mint flag | a per-escrow posture over every financial operation |
| Changing that protection | asymmetric for a seat | asymmetric for everyone |
| A Founder Seat | a manager address set, add-only, bounded at 16 | an owning identity and no address at all |
| A mint's destination | the address that signed | an escrow the transaction names and the chain checks |
| Verified-user incentives | reserved, refused as kind 6 | an entry airdrop and a daily permission |

Everything else carries over unchanged: the shared 80-byte header and 16-byte
trailer, the kind-1 body and its byte identity, the admission order and its three
codes, the frozen result numbers `0` through `25`, the RFC 9162 tree shape, the
genesis field table, the receipt layout, the accumulation cap and its window
measurement, the cycle-assignment record, the bounded mint walk, the carry
identity, and every founder-directed figure in the accepted manifest.

## Scope

Version six defines:

- the account architecture — identities, keyless escrows, and revocable
  signers — and the derivations that name an escrow and a signer;
- the canonical signed transaction envelope, its **two authorization schemes**,
  and the fourteen transaction kinds;
- the per-escrow security posture, the predicate that decides whether an
  operation requires a biometric confirmation, and the predicate that decides
  whether a posture change relaxes or tightens;
- the HUB signature family: six domain-separated messages, five of them signed
  by a person's own recorded key;
- the entry airdrop and the daily verified-user permission, with their
  thirty-window cap and its forfeiture;
- the automatic per-cycle assignment, the accumulation cap, and the bounded
  accumulate-then-mint settlement, all unchanged from version three;
- the canonical economy state key space and its value encodings;
- version-six genesis, chain identity, and the state-root construction;
- the version-six receipt and the complete numeric result-code space;
- the ordered rejection conditions of each kind, and the total mapping from
  `founder-economy-simulator-v3`'s model codes onto them; and
- the exact compatibility boundary against M1 transaction bytes, state, and
  roots, and against versions two through five.

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
`founder-economy-manifest-v2` contract, whose digest is bound into version-six
genesis.

**The window grid.** `window_of_height`, `first_cycle_window`,
`last_cycle_window`, and `window_for_cycle` are `cycle-boundary-v1`, and the
24-slot subdivision of a window is `uptime-measurement-v1`'s.

**The measurement.** The finalised per-window record, its finalisation rule, and
its in-scope seat set are `uptime-measurement-v1`.

**The transitions.** The activity verdict, the winner rule, the tie rule, the
remainder rule, the carry and its conservation identity, and the ordered
rejection conditions are `founder-economy-simulator-v3`.

**The settlement.** The accumulation cap, the cycle-assignment record, the
bounded mint walk, and the referral accrual are `economy-transition-v3`,
incorporated by reference and re-encoded only where a key changes.

## The account architecture

**Three objects, and each answers exactly one question.**

| Object | Answers | Keyed by | Holds |
| --- | --- | --- | --- |
| identity | who a person is | their HUB identity hash | their HUB public key and their counts |
| escrow | where value sits | a derived escrow identifier | its owning identity and its security posture |
| signer | who may act on an escrow | the accepted version-one derivation over a public key | the one escrow it is assigned to |

**An escrow is a version-one account.** Its balance and nonce live in the
version-one account map, keyed by the escrow identifier, so a version-six state
is a version-one state plus one ordered economy map and every version-one
invariant holds unchanged. What the economy map adds for an escrow is its owner
and its posture.

### The escrow identifier

An escrow has no key, so its identifier cannot be a public-key hash:

```text
escrow_id =
  H(D("protocol-stack:v6:escrow") || hub_identity_hash || u32(escrow_index))
```

`escrow_index` is drawn from the identity's `next_escrow_index`, which increases
by one at every creation and **never decreases**. A deleted escrow's identifier
is therefore never reissued, so a transaction naming a deleted escrow can never
be executed against a different escrow that happens to occupy its index later.

**The identifier is derived rather than chosen**, so two nodes reach the same
value without agreeing on anything beyond the identity and the index, and a
person can compute their own escrow identifiers offline before the chain has
written them.

### The signer identifier

```text
signer_id = H(D("protocol-stack:v1:account") || 0x01 || ed25519_public_key)
```

**This is the accepted version-one account derivation, unchanged**, with its
role narrowed from naming an account to naming a signer — which is what a
public-key hash is. Four contract versions preserved this derivation for
accounts; version six preserves the derivation and moves what it names.

**A signer key is assigned to exactly one escrow**, which is the founder answer
of 2026-08-15. A signer entry maps `signer_id` to one `escrow_id`, so the chain
resolves the acting escrow from the signing key alone and the version-one
80-byte header needs no escrow field. A key already assigned to any escrow
cannot be assigned to a second.

## The transaction envelope

Every version-six transaction, including the version-one native transfer, is:

```text
signed_transaction = header(80) || body(kind-specific) || trailer(16) || signature(64)
```

The header is exactly the first 80 bytes of the accepted version-one transfer
and the trailer exactly its last 16, both unchanged:

| Offset | Size | Field | Required value or range |
| ---: | ---: | --- | --- |
| 0 | 4 | magic | ASCII `PSTX` |
| 4 | 2 | schema version | `1` |
| 6 | 1 | transaction kind | an assigned kind |
| 7 | 32 | chain ID | configured chain |
| 39 | 1 | signature scheme | `1` or `2` |
| 40 | 32 | authority public key | canonical Ed25519 key |
| 72 | 8 | nonce | `u64` |

| Offset from body end | Size | Field |
| ---: | ---: | --- |
| 0 | 8 | fee limit `u64` |
| 8 | 8 | valid-until height `u64` |

```text
signing_message = D("protocol-stack:v1:tx-sign") || unsigned_transaction
transaction_id  = H(D("protocol-stack:v1:tx-id") || signed_transaction)
```

The schema version stays `1` because these 80 bytes do not change, and the two
signing labels stay unversioned for the reason version two gives: the kind byte
and the chain ID are inside every preimage, and re-versioning would destroy the
kind-1 byte identity for separation the preimage already carries.

### Two authorization schemes

Version one fixes the signature-scheme byte at `1` and reads the field at offset
40 as the sender's public key. Version six reads that field as an **authority
public key** and lets the scheme byte say whose:

| Scheme | Authority | Acting escrow | Verified against |
| ---: | --- | --- | --- |
| 1 | a signer key | the escrow that signer is assigned to | the header key |
| 2 | an identity's HUB key | an escrow the body names | the header key |

**Both schemes verify the envelope signature against the header key**, so
admission still checks a signature without reading state, exactly as version one
does. What differs is only how the acting escrow is found afterwards, which is an
execution step in both cases.

**Scheme 2 exists because identity administration must work with no key at all.**
A person recovering holds their face and nothing else, so the transaction that
assigns them a new signer cannot be signed by a signer. Scheme 2 is the
mechanism, and it is confined to the six administrative kinds; every value-moving
kind is scheme 1.

**A kind fixes its scheme.** A scheme byte a kind does not permit is
`MALFORMED_TRANSACTION`, so no transaction is ambiguous about which rule
authorizes it.

### The nonce belongs to the escrow

An escrow has one nonce sequence, shared by every signer assigned to it. Two
signers acting concurrently on one escrow race for that sequence and one of them
receives `NONCE_MISMATCH`, which is version one's rule applied unchanged to the
escrow rather than to a key. **Nothing new is required to order two signers**,
which is the answer to the question ADR 0040 recorded as engineering's to settle.

Kind 10 is the exception and is forced: a registration has no escrow yet, so its
nonce field must be `0` and its replay protection is the identity check rather
than a sequence.

## Transaction kinds

| Kind | Name | Scheme | Body | Unsigned | Signed |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `native_transfer` | 1 | 40 | 136 | 200 |
| 2 | `purchase_seat` | 1 | 101 | 197 | 261 |
| 3 | `activate_seat` | 1 | 68 | 164 | 228 |
| 4 | `mint_node` | 1 | 100 | 196 | 260 |
| 5 | `mint_referral` | 1 | 96 | 192 | 256 |
| 6 | `direct_issue` | 1 | 105 | 201 | 265 |
| 10 | `hub_register` | 2 | 128 | 224 | 288 |
| 13 | `escrow_create` | 2 | 64 | 160 | 224 |
| 14 | `escrow_delete` | 2 | 96 | 192 | 256 |
| 15 | `signer_add` | 2 | 96 | 192 | 256 |
| 16 | `signer_revoke` | 2 | 96 | 192 | 256 |
| 17 | `set_security_posture` | 1 | 77 | 173 | 237 |
| 18 | `mint_verified_user` | 1 | 96 | 192 | 256 |
| 19 | `native_transfer_verified` | 1 | 104 | 200 | 264 |

**Kinds 7, 8, 9, 11, and 12 are retired and permanently unassigned in version
six.** They named `mint_node_verified`, `set_mint_biometric`, `add_manager`,
`hub_add_address`, and `hub_remove_address`, and each lost its subject: the
protected mint folds into kind 4's confirmation field, the per-seat flag becomes
the per-escrow posture, a seat has no manager set, and an address is created
beneath an identity rather than linked to one. A retired kind byte is
`MALFORMED_TRANSACTION` at admission.

**They are retired rather than reused.** Assigning a new meaning to a number a
reader associates with an accepted contract is the cheapest possible way to
create an auditing mistake, and the five holes cost nothing but a gap in a table.
The six numbers that keep their subject — 1, 2, 3, 4, 5, and 6 — keep their
identifiers for exactly the same reason.

**Every kind is fixed-length, and two groups share a length.** Kinds 5, 14, 15,
16, and 18 are all 96-octet bodies, and no other pair collides. A decoder
dispatches on the kind byte, which is the rule version two stated for this case
and which version three first exercised.

**The largest transaction in version six is 288 bytes**, down from version four's
293. Nothing a transaction carries scales with the seat population or with a
person's escrow or signer count.

### Kind 1 — `native_transfer`

| Offset | Size | Field |
| ---: | ---: | --- |
| 80 | 32 | recipient escrow ID |
| 112 | 8 | amount `u64` |

**This is the accepted version-one transfer, byte-for-byte.** `80 + 40 + 16 =
136` unsigned and `200` signed, with the same signing message and the same
transaction ID. The vectors require the version-six encoder to reproduce
`protocol-primitives-v1`'s recorded bytes exactly.

**Five contract revisions have now left those bytes untouched, and version six is
the first to change what they do.** The recipient must be a registered escrow,
and a transfer naming anything else is `RECIPIENT_NOT_REGISTERED`. That is the
founder answer of 2026-08-15 — verification is the entry point, so there is no
account for a payment to reach — and it withdraws `ledger-transition-v1`'s rule
that "a transfer to an absent recipient creates it with nonce zero", which is the
last way an account could come into existence with no identity behind it.

### Kind 19 — `native_transfer_verified`

| Offset | Size | Field |
| ---: | ---: | --- |
| 80 | 32 | recipient escrow ID |
| 112 | 8 | amount `u64` |
| 120 | 64 | HUB signature over the transfer-confirm message |

Identical to kind 1 with a biometric confirmation attached. Kind 1 is refused
with `BIOMETRIC_REQUIRED` when the sending escrow's posture requires confirmation
for that amount at that height; kind 19 is accepted whether or not it does.

**A transfer is two kinds rather than one kind with an optional field, and the
reason is specific to kind 1.** Every other confirmable operation carries a
64-octet signature field that must be 64 zero octets when confirmation is not
required, which is version four's kind-8 pattern. A transfer cannot, because
widening kind 1's body by 64 octets would end a byte identity carried since M1
for the sake of uniformity. Kind 1's bytes are a compatibility commitment;
nothing else's are.

### Kind 2 — `purchase_seat`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 4 | seat ID `u32` | `0` through `99,999` |
| 84 | 1 | has referrer `bool` | `0x00` or `0x01` |
| 85 | 32 | referrer escrow ID | 32 octets, or 32 zero octets when absent |
| 117 | 64 | HUB signature | Ed25519 over the purchase message |

A `has_referrer` of `0x00` requires 32 zero octets in the referrer field; any
other value is the non-minimal representation `protocol-primitives-v1` forbids
and is `MALFORMED_TRANSACTION`.

**The purchaser is the identity that signed, and no account is named.** Version
four carried a 32-byte purchaser account because a seat recorded which address
bought it; ADR 0041 removed the concept, so the field went with it. The seat
belongs to a person and to nothing else.

**The referrer is named by escrow and recorded as an identity.** A referral link
yields an escrow identifier, which is the shareable thing; the chain resolves it
to its owning identity and records the identity, so referral earnings follow the
person and a referrer who changes escrows keeps everything accrued.

### Kind 3 — `activate_seat`

| Offset | Size | Field |
| ---: | ---: | --- |
| 80 | 4 | seat ID `u32` |
| 84 | 64 | HUB signature over the activation message |

Signed by the seat's owning identity. Activation is one-time and permanent.

### Kinds 4, 5, and 18 — the three mints

| Kind | Offset | Size | Field |
| ---: | ---: | ---: | --- |
| 4 | 80 | 4 | seat ID `u32` |
| 4 | 84 | 32 | destination escrow ID |
| 4 | 116 | 64 | HUB signature over the mint message, or 64 zero octets |
| 5 | 80 | 32 | destination escrow ID |
| 5 | 112 | 64 | HUB signature over the mint message, or 64 zero octets |
| 18 | 80 | 32 | destination escrow ID |
| 18 | 112 | 64 | HUB signature over the mint message, or 64 zero octets |

**One button, everything, no quantity**, unchanged and founder-directed.

**A mint names its destination and the chain checks it belongs to the minting
identity.** ADR 0041 records that derivation, and it follows from a person
holding many escrows and none being privileged: the rule it replaces sent minted
value to the address that signed, and a signer now holds no funds. A destination
that is not an escrow of the minting identity is `ESCROW_NOT_OWNED`.

**The confirmation field is the destination escrow's posture applied to the
amount the mint would credit.** The total is computed before any write, the
posture predicate is evaluated against it, and a mint that needs a confirmation
and carries 64 zero octets is `BIOMETRIC_REQUIRED` with nothing written. A mint
that does not need one must carry 64 zero octets, and any other value is
`MALFORMED_TRANSACTION`.

### Kind 6 — `direct_issue`

| Offset | Size | Field |
| ---: | ---: | --- |
| 80 | 1 | channel ID `u8` |
| 81 | 32 | decision ID |
| 113 | 32 | beneficiary escrow ID |
| 145 | 8 | amount `u64` |
| 153 | 32 | authorization |

Unchanged from versions two through five, including its refusal, with one
narrowing: **its channel set loses the verified-user channel.** A conforming
chain rejects every kind 6 with `UNAUTHORIZED` until `direct_issue_authority` is
accepted, and the channels it names are now `{5, 6, 9}` — liquidity mining,
impermanent-loss protection, and mystery-box incentives. Channel 8 leaves the set
because ADR 0042 decided its eligibility and its rate, and kinds 10 and 18 issue
it.

### Kind 10 — `hub_register`

| Offset | Size | Field | Range |
| ---: | ---: | --- | --- |
| 80 | 32 | HUB identity hash | 32 octets |
| 112 | 32 | first signer public key | canonical Ed25519 key |
| 144 | 64 | verifier signature | Ed25519 over the registration message |

Scheme 2, with the header authority being the identity's own new HUB public key.
It is **the one scheme-2 kind whose key is not read from state**, because the
identity does not exist yet; the verifier's signature is what binds the identity
hash to that key, and it is why nobody can register a key against another
person's identity hash.

**Registration is fee-exempt**, and its fee-limit field must be `0`. This is one
transaction rather than four, and it does all of the following atomically:

1. writes the identity record, with the header's HUB public key, the executing
   height, `next_escrow_index` one, `escrow_count` one, and `seat_count` zero;
2. derives escrow index `0`, writes its economy entry with the default posture,
   and creates its version-one account entry with nonce zero;
3. writes the signer entry binding the first signer key to that escrow; and
4. when fewer than 1,000,000 identities are enrolled, enrolls this one and
   credits the entry airdrop of `171,000,000` atomic to escrow `0`.

**This is the only transaction the ecosystem verifier signs, and that is the
whole architecture.** The verifier asserts that a live, distinct human stands
behind an identity, which is a judgement no chain can make. Every later proof of
the same person is made by that person's own recorded key. An unavailable
verifier stops new people entering the ecosystem and stops nothing else.

**A HUB identity is registered once and is never re-registered.** An identity
hash already present is `REPLAY`. Recovery is not a re-registration and pays
nothing: a person who has lost every signer proves their identity and adds a new
signer with kind 15.

**Fee exemption is deliberate and is not the smaller of two equal options.**
ADR 0042 preferred crediting the airdrop before assessing a fee, on the ground
that 1.71 units exceeds any plausible fixed fee. That holds only while an airdrop
exists: the airdrop is bounded at 1,000,000 identities, so user 1,000,001 would
create a zero-balance escrow and fail with `INSUFFICIENT_BALANCE` under that
rule. Exemption works for every user forever, and its anti-abuse bound is
non-monetary and already present, because only the ecosystem verifier can sign a
registration.

### Kind 13 — `escrow_create`

| Offset | Size | Field |
| ---: | ---: | --- |
| 80 | 32 | HUB identity hash |
| 112 | 32 | fee escrow ID |

Scheme 2. The identity is the admin over its escrows, so creating one is proved
by the identity's HUB key rather than by any signer. The new escrow takes the
identity's `next_escrow_index`, the default posture, a zero balance, and a zero
nonce, and it has **no signer until kind 15 assigns one**.

### Kind 14 — `escrow_delete`

| Offset | Size | Field |
| ---: | ---: | --- |
| 80 | 32 | HUB identity hash |
| 112 | 32 | target escrow ID |
| 144 | 32 | fee escrow ID |

Scheme 2. **A deleted escrow must hold a zero balance**, because any other rule
either destroys value or invents a sweep destination, and neither is this
contract's to choose. The fee escrow is named separately for the same reason: an
escrow with a zero balance cannot pay for its own deletion.

Deletion removes the escrow entry, its version-one account entry, and every
signer entry assigned to it, and decrements `escrow_count`. It does not decrement
`next_escrow_index`.

### Kinds 15 and 16 — `signer_add` and `signer_revoke`

| Kind | Offset | Size | Field |
| ---: | ---: | ---: | --- |
| 15 | 80 | 32 | HUB identity hash |
| 15 | 112 | 32 | escrow ID |
| 15 | 144 | 32 | new signer public key |
| 16 | 80 | 32 | HUB identity hash |
| 16 | 112 | 32 | escrow ID |
| 16 | 144 | 32 | signer ID |

Scheme 2, and the named escrow pays the fee.

**Kind 15 is the recovery path, and it is the ordinary transaction rather than a
special one.** A person who has lost every signer proves their identity with
their HUB key, names an escrow that already holds value, and assigns a fresh
signer to it. There is no helper, no third party, and no external funding step,
because regaining an identity regains escrows that already hold value — which is
exactly what ADR 0040 said dissolves the version-five dilemma.

**A signer key already assigned to any escrow is `REPLAY`**, which is what makes
one key belong to exactly one escrow. At most `16` signers may be assigned to one
escrow, and an escrow may hold zero: a person may revoke every signer on an
escrow and still add one, because kind 15 is authorized by the HUB key.

**Revocation is immediate and total.** A revoked signer authorizes nothing from
the block that revokes it, which is what makes the identity an admin rather than
a co-signer.

### Kind 17 — `set_security_posture`

| Offset | Size | Field |
| ---: | ---: | --- |
| 80 | 1 | requires confirmation `bool` |
| 81 | 8 | minimum amount `u64` |
| 89 | 4 | exempt slot mask `u32` |
| 93 | 64 | HUB signature over the posture-relax message, or 64 zero octets |

**Scheme 1, and the escrow is the signer's own.** A signer is assigned to exactly
one escrow, so the posture this changes needs no field: it is the posture of the
escrow the signing key acts on. An identity that holds no signer on an escrow
cannot tighten its posture directly, and the path is to assign a signer with kind
15 first.

The high 8 bits of the exempt slot mask must be zero, because a window has 24
slots; any other value is `MALFORMED_TRANSACTION`.

**The asymmetry is the protection, and version six generalises it.** Version
three made it a Founder Seat rule; the founder answer of 2026-08-15 makes it
everyone's. Relaxing a posture requires a HUB signature; tightening requires only
the signer signature and must carry 64 zero octets.

## The security posture

Every escrow stores a posture. A newly created escrow takes the default the
constitution directs — **confirmation on for every financial operation**:

```text
requires_confirmation = 1
min_amount_atomic     = 0
exempt_slot_mask      = 0
```

### When an operation requires a confirmation

For an operation on escrow `E` moving `amount` atomic units at executing height
`h`:

```text
requires(E, amount, h) =
  E.requires_confirmation = 1
  and amount >= E.min_amount_atomic
  and bit(slot_of(h)) not set in E.exempt_slot_mask

slot_of(h) = (h mod CYCLE_BLOCKS) div SLOT_BLOCKS
```

`CYCLE_BLOCKS` and `SLOT_BLOCKS` are the accepted window grid's, so a slot is one
hour and a window has 24 of them. **A "time window" is expressed in block heights
and never in wall-clock time**, because a transition may not read a clock; the
mask names hours of the daily grid the chain already computes.

A `min_amount_atomic` of zero means every amount requires confirmation, because
every amount is at least zero. A person who wants no confirmation below one unit
sets the minimum to `100,000,000`.

### Which operations it governs

The transfers, kinds 1 and 19, against the **sending** escrow's posture and the
transferred amount. The three mints, kinds 4, 5, and 18, against the
**destination** escrow's posture and the total the mint would credit.

It does not govern the administrative kinds, because scheme 2 already requires
the identity's HUB signature on every one of them, so a confirmation is
structurally present rather than optional. It does not govern kinds 2 and 3,
which carry a HUB signature unconditionally. It does not govern kind 17's
tightening direction, which is the asymmetry itself.

### Whether a change relaxes or tightens

A chain cannot read intent, so the direction of a posture change is derived from
the two stored postures alone. A change from `P` to `P'` **relaxes** when any of:

```text
P.requires_confirmation = 1 and P'.requires_confirmation = 0
P'.min_amount_atomic > P.min_amount_atomic
(P'.exempt_slot_mask and not P.exempt_slot_mask) != 0
```

Otherwise it tightens. A change to a posture equal in all three fields is
`REPLAY`.

**The three disjuncts are the three ways to shrink the set of operations that
require a confirmation**, and each is checked independently, so a change that
tightens one field and relaxes another counts as a relaxation and needs the HUB
signature. That direction of rounding is deliberate: the failure that matters is
a stolen key weakening a protection, and a mixed change that weakens anything is
a weakening.

## Admission

Admission operates on raw transaction bytes before ledger state is read, and its
version-one steps are unchanged in order and in meaning:

1. decode exactly one signed version-six transaction with no trailing bytes;
2. require the configured chain ID;
3. derive the authority identifier from the encoded public key;
4. strictly verify the Ed25519 signature over the signing message.

Step 1 classifies a wrong magic, schema version, or signature-scheme identifier,
a retired or unassigned transaction kind, a scheme a kind does not permit, a
length that is not the exact length its kind requires, a `has_referrer` or
`requires_confirmation` byte that is not `0x00` or `0x01`, a non-minimal
absent-referrer encoding, a nonzero high byte in an exempt slot mask, a nonzero
confirmation field on an operation that requires none, a nonzero fee limit on a
registration, or a nonzero nonce on a registration as `MALFORMED_TRANSACTION`.

| Code | Name |
| ---: | --- |
| 1 | `MALFORMED_TRANSACTION` |
| 2 | `WRONG_CHAIN` |
| 3 | `INVALID_SIGNATURE` |

**Step 4 is unchanged by the second scheme, and that is why the scheme byte
selects a key rather than a verification rule.** Under both schemes the envelope
signature verifies against the 32-byte header field, so admission reads no state
in either case. What the scheme decides is how the acting escrow is resolved
afterwards, which was always an execution step.

**No HUB or verifier signature carried in a body is checked at admission**,
because each verifies against a key held in ledger state. They are execution
conditions returning `UNAUTHORIZED`, and they produce a receipt.

**A bounded numeric field outside its range is not an admission failure.** A seat
ID of `100,000` decodes and is refused at execution with `CYCLE_RANGE`.

## Authorization

Every kind is signed by a key and every kind except registration charges the
acting escrow the fixed fee, which the Founder Constitution decides applies to
every accepted state transition.

| Kind | Scheme | Fee escrow | Proof of the person |
| ---: | ---: | --- | --- |
| 1 | 1 | the signer's escrow | none; refused when the posture requires one |
| 2 | 1 | the signer's escrow | the purchaser's HUB key, over the purchase message |
| 3 | 1 | the signer's escrow | the seat's HUB key, over the activation message |
| 4 | 1 | the signer's escrow | the destination's HUB key when the posture requires one |
| 5 | 1 | the signer's escrow | the destination's HUB key when the posture requires one |
| 6 | 1 | the signer's escrow | refused; the predicate is reserved |
| 10 | 2 | none; fee-exempt | the ecosystem verifier key, over the registration message |
| 13 | 2 | the named fee escrow | the envelope signature by the identity's HUB key |
| 14 | 2 | the named fee escrow | the envelope signature by the identity's HUB key |
| 15 | 2 | the named escrow | the envelope signature by the identity's HUB key |
| 16 | 2 | the named escrow | the envelope signature by the identity's HUB key |
| 17 | 1 | the signer's escrow | the escrow's HUB key to relax; none to tighten |
| 18 | 1 | the signer's escrow | the destination's HUB key when the posture requires one |
| 19 | 1 | the signer's escrow | the sender's HUB key, over the transfer-confirm message |

A key the applicable rule refuses is `UNAUTHORIZED`.

**Six kinds require no signer at all, and each is a recovery path.** Kinds 10 and
13 through 16 are exactly the transactions a person must be able to make holding
no key: register, create an escrow, delete one, assign a signer, revoke a signer.
The HUB signature is the authority and a named escrow pays.

### The HUB signature family

Six domain-separated messages. Five verify against the acting identity's recorded
`hub_public_key`; only the first verifies against the genesis-configured
ecosystem verifier key.

```text
registration_message =
  D("protocol-stack:v6:hub-registration") ||
  chain_id || hub_identity_hash || hub_public_key ||
  first_signer_public_key || u64(valid_until_height)

purchase_message =
  D("protocol-stack:v6:seat-purchase") ||
  chain_id || hub_identity_hash || u32(seat_id) || u64(valid_until_height)

activation_message =
  D("protocol-stack:v6:seat-activation") ||
  chain_id || hub_identity_hash || u32(seat_id) || u64(valid_until_height)

mint_message =
  D("protocol-stack:v6:mint-confirm") ||
  chain_id || hub_identity_hash || u8(transaction_kind) || u32(seat_id) ||
  destination_escrow_id || u64(valid_until_height)

posture_relax_message =
  D("protocol-stack:v6:posture-relax") ||
  chain_id || hub_identity_hash || escrow_id ||
  u8(requires_confirmation) || u64(min_amount_atomic) ||
  u32(exempt_slot_mask) || u64(valid_until_height)

transfer_confirm_message =
  D("protocol-stack:v6:transfer-confirm") ||
  chain_id || hub_identity_hash || escrow_id ||
  recipient_escrow_id || u64(amount) || u64(valid_until_height)
```

**Every message binds the identity**, so a signature made by one person's key
cannot be presented as another's even where the remaining fields coincide.

**The mint message binds the kind and the destination**, which is what stops a
confirmation obtained for one mint being replayed onto a different one. Kinds 5
and 18 carry no seat, so their `seat_id` term is `u32(0)`; the kind byte is what
separates them, and the vectors require the three constructions to differ on
identical remaining fields.

**A posture-relax signature binds the exact posture it approves**, so an approval
to raise a minimum to one unit cannot be presented as an approval to turn
confirmation off.

`valid_until_height` in each message is the transaction's own trailer value, so
the proof and the transaction expire together.

### What is still reserved

`direct_issue_authority` — the eligibility and anti-abuse mechanics for the
`liquidity_mining`, `impermanent_loss_protection`, and
`initial_mystery_box_incentives` channels. Kind 6 is specified and refused rather
than given an invented predicate. **The `hub_verified_user_incentives` channel
has left this set**, because ADR 0042 decided both its eligibility and its rate.

## Canonical economy state

Version one's state — chain ID, supply limit, total supply, fixed fee, height,
fee pool, and the ordered account map — plus one ordered map from canonical byte
keys to canonical byte values. A key is `u8(entry_kind)` followed by fixed-width
big-endian fields.

| Kind | Entry | Key | Key bytes | Value | Value bytes |
| ---: | --- | --- | ---: | --- | ---: |
| 1 | seat | `u8(1) \|\| seat_id:u32` | 5 | see below | 82 |
| 2 | channel | `u8(2) \|\| channel_id:u8` | 2 | `issued:u64 \|\| outstanding:u64` | 16 |
| 3 | cycle assignment | `u8(3) \|\| cycle_window:u64` | 9 | see below | 24 + 2⌈b/8⌉ |
| 4 | referral balance | `u8(4) \|\| hub_identity_hash:bytes<32>` | 33 | `accrued:u64 \|\| minted:u64 \|\| collected_through_window:u64` | 24 |
| 5 | direct decision | `u8(5) \|\| decision_id:bytes<32>` | 33 | *(empty)* | 0 |
| 6 | typed custody | `u8(6) \|\| beneficiary_kind:u8 \|\| beneficiary_id:bytes<32>` | 34 | `amount:u64` | 8 |
| 7 | carry | `u8(7) \|\| channel_id:u8` | 2 | `carry:u64` | 8 |
| 8 | verifier key | `u8(8)` | 1 | `ed25519_public_key:bytes<32>` | 32 |
| 10 | HUB identity | `u8(10) \|\| hub_identity_hash:bytes<32>` | 33 | see below | 52 |
| 12 | unreferred pool | `u8(12)` | 1 | `accrued:u64 \|\| minted:u64` | 16 |
| 13 | escrow | `u8(13) \|\| escrow_id:bytes<32>` | 33 | see below | 49 |
| 14 | signer | `u8(14) \|\| signer_id:bytes<32>` | 33 | `escrow_id:bytes<32>` | 32 |
| 15 | verified-user enrollment | `u8(15) \|\| hub_identity_hash:bytes<32>` | 33 | see below | 24 |
| 16 | verified-user counter | `u8(16)` | 1 | `enrolled_count:u64` | 8 |

**Entry kinds 9 and 11 are retired and permanently unassigned**, exactly as their
transaction kinds are. They held the seat manager set and the HUB address set,
and both concepts are gone. An entry kind outside the assigned set cannot occur,
because no transition writes one and the state is not an untrusted input.

### The HUB identity record

```text
hub_public_key       : bytes<32>
registered_at_height : u64
next_escrow_index    : u32
escrow_count         : u32
seat_count           : u32
```

52 bytes. The public key is what every later proof of this person verifies
against. The three counts are state for the reason version three's
`manager_count` is: a bound or an index derived by iterating a key prefix inside
a transition is an implicit cost two implementations disagree about.

**`next_escrow_index` and `escrow_count` are separate on purpose.** The index
never decreases so an identifier is never reissued; the count falls on deletion
so the live figure is exact. Collapsing them into one field would make one of the
two properties false.

### The escrow record

```text
owner_hub_identity    : bytes<32>
requires_confirmation : u8
min_amount_atomic     : u64
exempt_slot_mask      : u32
signer_count          : u32
```

49 bytes. **The balance and the nonce are not here**: they are the version-one
account entry keyed by the same 32 octets, which is what makes a version-six
state a version-one state plus an economy map.

### The signer record

Key by signer identifier, value the one escrow it is assigned to. The forward
direction is what every scheme-1 transaction needs — which escrow does this key
act on — and it is one lookup. **Membership is exactly this entry**: a key with
no entry authorizes nothing, and a key with one authorizes exactly the escrow it
names.

### The verified-user enrollment record

```text
enrolled_at_height    : u64
minted_through_window : u64
issued_atomic         : u64
```

24 bytes, written only for an identity that registered while fewer than
1,000,000 were enrolled.

### The seat record

```text
hub_identity_hash        : bytes<32>
has_referrer             : u8
referrer_hub_identity    : bytes<32>
is_activated             : u8
activation_height        : u64
minted_through_window    : u64
```

82 bytes, down from version four's 119. The purchaser account, the biometric
flag, and the manager count are gone with the concepts they served, and nothing
replaced them: a seat is owned by an identity and read through it.

### The cycle assignment record and everything else

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

The typed-custody beneficiary space is version three's five codes, four of them
singletons taking a zero beneficiary ID.

### The economy Merkle tree and the version-six state root

```text
economy_entry = bytes(key) || bytes(value)

economy_tree({})            = H(D("protocol-stack:v6:economy-empty"))
economy_tree({entry})       = H(D("protocol-stack:v6:economy-leaf") || entry)
economy_tree(left || right) = H(D("protocol-stack:v6:economy-node") || l || r)

state_root =
  H(
    D("protocol-stack:v6:state-root") ||
    u16(6) || chain_id || height:u64 || supply_limit:u64 ||
    total_supply:u64 || fee_pool_balance:u64 || account_count:u64 ||
    accounts_tree_root || economy_entry_count:u64 || economy_tree_root
  )
```

The tree shape is `protocol-primitives-v1`'s RFC 9162 construction and the
accounts tree is unchanged entry-for-entry. The label and version field differ
from all five predecessors, so **a version-six state root is never equal to a
version-one through version-five root**, including over an identical account set
and an empty economy. Each non-collision is required separately, because distinct
labels are strings rather than a chain.

## Version-six genesis

| Field | Encoding | Required value |
| --- | --- | --- |
| magic | `bytes<4>` | ASCII `PSGN` |
| schema version | `u16` | `6` |
| network ID | `u32` | configured |
| supply limit | `u64` | configured, nonzero |
| total supply | `u64` | `0` |
| fixed transfer fee | `u64` | configured |
| initial fee pool | `u64` | configured |
| economy manifest digest | `bytes<32>` | the accepted manifest digest |
| ecosystem verifier key | `bytes<32>` | canonical Ed25519 public key |
| account count | `u32` | `0` |
| accounts | repeated 48-byte state entries | none |

```text
chain_id = H(D("protocol-stack:v6:chain-id") || canonical_genesis_v6_bytes)
```

The field table is version four's with a different schema version, so the prefix
is still 110 bytes and the 1,048,576-byte object bound still admits at most
21,843 entries:

```text
110 + 48 * 21,843 = 1,048,574   within the bound
110 + 48 * 21,844 = 1,048,622   beyond it
```

**Version six is the first version to require zero genesis accounts rather than
merely to expect it.** Versions two through five permitted `0` through `21,843`
while recording that the constitution's no-genesis-allocation rule forces zero. A
genesis account would now be an account with no escrow entry and no identity
behind it, which violates a structural invariant, so the field is retained at
zero for layout compatibility and the 21,843 bound is inherited and unreachable.
Both facts are recorded in the vectors rather than left to be inferred.

Genesis writes the ten channel entries with both amounts zero, the ten carry
entries with zero, the ecosystem verifier key, the unreferred pool entry with
both amounts zero, and the verified-user counter at zero. It writes no seat, no
identity, no escrow, no signer, no enrollment, no referral balance, no custody
entry, and no cycle assignment.

The three relaxations version two derived are unchanged and each is forced by the
no-genesis-allocation rule: zero total supply, zero accounts, and a fee permitted
to be zero.

**The bootstrap gap is closed for a participant and open for the chain.** A
brand-new person no longer needs an external balance, because registration is
fee-exempt and pays the entry airdrop. The chain still opens with zero supply and
no way to reach a first balance other than a registration, which is now the
intended path rather than a gap.

## Execution

Every kind first applies the shared envelope checks in version one's order and
with version one's codes and meanings, then its own conditions.

| Result | Name | Condition |
| ---: | --- | --- |
| 2 | `FEE_LIMIT_TOO_LOW` | fee limit is below the fixed fee |
| 3 | `EXPIRED` | valid-until height is below the executing block height |
| 5 | `NONCE_EXHAUSTED` | stored escrow nonce is `u64` maximum |
| 6 | `NONCE_MISMATCH` | transaction nonce is not stored nonce plus one |
| 8 | `INSUFFICIENT_BALANCE` | escrow balance is below what it must debit |

Before those, the acting escrow must be resolved:

- under scheme 1, a header key with no signer entry is `SIGNER_NOT_FOUND`;
- under scheme 2, a body identity hash that is unregistered is
  `NOT_HUB_VERIFIED`, a header key that is not that identity's recorded
  `hub_public_key` is `UNAUTHORIZED`, a named fee escrow that does not exist is
  `ESCROW_NOT_FOUND`, and one owned by another identity is `ESCROW_NOT_OWNED`.

**`SENDER_NOT_FOUND` is frozen and unreachable in version six.** A signer entry
names an escrow, an escrow entry implies a version-one account entry, and the two
are written and deleted together, so an escrow that resolves always exists. The
code keeps its number and its version-one meaning and no version-six path
produces it, which the vectors record as a derived property rather than a claim.

Every non-success result performs no state write and charges no fee, still
produces a receipt, and still enters the ordered transaction root.

### Kind 10 — HUB register

1. an already-registered `hub_identity_hash` is `REPLAY`;
2. a first signer key already assigned to any escrow is `REPLAY`;
3. a verifier signature that does not verify over the registration message,
   against the genesis-configured verifier key, is `UNAUTHORIZED`;
4. an entry airdrop that does not fit channel 8 is `CHANNEL_CAP`.

On success it performs the four writes listed under
[Kind 10](#kind-10--hub_register), atomically. Condition 4 is a guard: the
enrollment count bounds issuance below the cap by construction, so it is proved
present by direct exercise rather than reachable from an ordinary sequence.

### Kind 13 — escrow create

1. an unregistered `hub_identity_hash` is `NOT_HUB_VERIFIED`;
2. a header key that is not that identity's recorded key is `UNAUTHORIZED`;
3. a fee escrow that does not exist is `ESCROW_NOT_FOUND`;
4. a fee escrow owned by another identity is `ESCROW_NOT_OWNED`.

On success it writes the escrow entry at `next_escrow_index` with the default
posture and a zero `signer_count`, creates its version-one account entry with
nonce zero and balance zero, increments both `next_escrow_index` and
`escrow_count`.

### Kind 14 — escrow delete

1. an unregistered `hub_identity_hash` is `NOT_HUB_VERIFIED`;
2. a header key that is not that identity's recorded key is `UNAUTHORIZED`;
3. a target or fee escrow that does not exist is `ESCROW_NOT_FOUND`;
4. a target or fee escrow owned by another identity is `ESCROW_NOT_OWNED`;
5. a target equal to the fee escrow is `ESCROW_NOT_EMPTY`, because the fee is
   debited from it;
6. a target whose balance is nonzero is `ESCROW_NOT_EMPTY`.

On success it deletes the target's escrow entry, its account entry, and every
signer entry naming it, and decrements `escrow_count`.

### Kinds 15 and 16 — signer add and revoke

For kind 15:

1. an unregistered `hub_identity_hash` is `NOT_HUB_VERIFIED`;
2. a header key that is not that identity's recorded key is `UNAUTHORIZED`;
3. a named escrow that does not exist is `ESCROW_NOT_FOUND`;
4. a named escrow owned by another identity is `ESCROW_NOT_OWNED`;
5. a signer key already assigned to any escrow is `REPLAY`;
6. an escrow already holding 16 signers is `SIGNER_LIMIT`.

For kind 16, conditions 1 through 4 are identical, then:

5. a `signer_id` with no signer entry is `SIGNER_NOT_FOUND`;
6. a signer entry naming a different escrow is `UNAUTHORIZED`.

On success kind 15 writes the signer entry and increments `signer_count`; kind 16
deletes it and decrements `signer_count`. Neither moves value.

### Kinds 1 and 19 — native transfer

1. a zero `amount` is `ZERO_AMOUNT`;
2. a `recipient` with no escrow entry is `RECIPIENT_NOT_REGISTERED`;
3. for kind 1, a sending escrow whose posture requires a confirmation for this
   amount at this height is `BIOMETRIC_REQUIRED`;
4. for kind 19, a HUB signature that does not verify over the transfer-confirm
   message, against the sending escrow's owning identity's public key, is
   `UNAUTHORIZED`;
5. a debit that overflows is `DEBIT_OVERFLOW`.

On success it debits the sender, credits the recipient, charges the fixed fee,
and increments the sender's nonce. **It never creates an account.**

### Kind 2 — purchase seat

1. a `seat_id` outside `0..99,999` is `CYCLE_RANGE`;
2. an already-purchased `seat_id` is `REPLAY`;
3. a named referrer escrow that does not exist is `RECIPIENT_NOT_REGISTERED`;
4. a referrer whose HUB identity equals the purchaser's is `INVALID_REFERRER`;
5. a purchaser identity already holding 1,000 seats is `SEAT_LIMIT`;
6. a HUB signature that does not verify over the purchase message, against the
   purchasing identity's public key, is `UNAUTHORIZED`.

The purchasing identity is the owner of the signer's escrow. On success it writes
the seat record with that identity, the referrer's identity or absence,
`is_activated` false, `activation_height` zero, and `minted_through_window` zero,
then increments the identity's `seat_count`. It issues nothing.

**Authorization is checked last and the request's own defects first**, for the
reason version two gives: a submitter fixing a bug should not be told that every
mistake is an authorization failure.

**Self-referral is refused across every escrow a person holds**, because the
comparison is between two identities and one person has exactly one.

### Kind 3 — activate seat

1. a `seat_id` outside `0..99,999` is `CYCLE_RANGE`;
2. an unpurchased `seat_id` is `SEAT_NOT_PURCHASED`;
3. a seat whose identity is not the signer's escrow's owner is `UNAUTHORIZED`;
4. an already-activated seat is `REPLAY`;
5. a HUB signature that does not verify over the activation message is
   `UNAUTHORIZED`.

On success it sets `is_activated`, writes `activation_height` as the executing
block height, and sets `minted_through_window` to
`window_of_height(activation_height)`, which is the window before the seat's
first cycle window and which is what makes the accumulation cap well-defined.

### Kind 4 — mint node

1. a `seat_id` outside `0..99,999` is `CYCLE_RANGE`;
2. an unpurchased `seat_id` is `SEAT_NOT_PURCHASED`;
3. an unactivated seat is `SEAT_NOT_ACTIVATED`;
4. a seat whose identity is not the signer's escrow's owner is `UNAUTHORIZED`;
5. a destination escrow that does not exist is `ESCROW_NOT_FOUND`;
6. a destination escrow owned by another identity is `ESCROW_NOT_OWNED`;
7. `minted_through_window` already equal to the last assigned window, or no
   window assigned yet, is `NOTHING_TO_MINT`;
8. a total the destination's posture requires a confirmation for, presented with
   64 zero octets, is `BIOMETRIC_REQUIRED`; a confirmation that does not verify
   over the mint message is `UNAUTHORIZED`;
9. a leg that does not fit its channel is `CHANNEL_CAP`.

On success the transition walks

```text
( minted_through_window , min(last_assigned_window, minted_through_window + 30) ]
```

and for each window holding an assignment record settles the seat's own base
permission when its accrued bit is set, and `reallocated_count` equal shares when
its winner bit is set. The Founder operator leg credits **the named destination
escrow's balance**; the four institutional legs credit typed custody. It then sets
`minted_through_window` to the last assigned window, moves each leg from
`outstanding` to `issued`, and increases `total_supply`. It is atomic.

All of this is version three's, unchanged, including that the walk is bounded by
the cap exactly rather than conservatively and that a mint collecting nothing
still advances a stale mark.

### Kind 5 — mint referral

1. a destination escrow that does not exist is `ESCROW_NOT_FOUND`;
2. a destination escrow owned by another identity is `ESCROW_NOT_OWNED`;
3. no referral balance for the acting identity, or a balance whose `accrued`
   equals its `minted` **and** whose `collected_through_window` already equals
   the last assigned window, is `NOTHING_TO_MINT`;
4. the confirmation conditions of kind 4's step 8;
5. a leg that does not fit the channel is `CHANNEL_CAP`.

On success it mints the whole outstanding difference to the destination escrow,
sets `minted` equal to `accrued`, sets `collected_through_window` to the last
assigned window, and increases `total_supply`.

**Any escrow of the person may receive their referral earnings**, because the
balance belongs to the identity.

### Kind 18 — mint verified user

1. a destination escrow that does not exist is `ESCROW_NOT_FOUND`;
2. a destination escrow owned by another identity is `ESCROW_NOT_OWNED`;
3. an acting identity with no enrollment entry is `NOT_ENROLLED`;
4. a collectable count of zero is `NOTHING_TO_MINT`;
5. the confirmation conditions of kind 4's step 8;
6. an amount that does not fit channel 8 is `CHANNEL_CAP`.

See [The verified-user channel](#the-verified-user-channel) for the amount.

### Kind 17 — set security posture

1. a posture equal to the escrow's current posture in all three fields is
   `REPLAY`;
2. when the change relaxes, a HUB signature that does not verify over the
   posture-relax message, against the escrow's owning identity's public key, is
   `UNAUTHORIZED`.

On success it overwrites the three posture fields.

### Kind 6 — direct issue

1. every acting key is `UNAUTHORIZED` while the predicate is undecided;
2. a `channel_id` outside `{5, 6, 9}` is `INVALID_CHANNEL`;
3. a zero `amount` is `ZERO_AMOUNT`;
4. an already-accepted `decision_id` is `REPLAY`;
5. an absent authorization is `MISSING_RESEARCH_INPUT`, one not bound to this
   exact action is `INVALID_RESEARCH_INPUT`, and a negative decision is
   `NOT_ELIGIBLE`;
6. a beneficiary escrow that does not exist is `RECIPIENT_NOT_REGISTERED`;
7. an amount that does not fit the channel is `CHANNEL_CAP`.

Conditions 2 through 7 are unreachable in a conforming implementation because
condition 1 refuses every acting key first, and the vectors record that
unreachability as a derived property.

## The verified-user channel

Channel 8 pays the first 1,000,000 verified identities `171,000,000` atomic per
day for 731 days. The three figures are founder-directed and the fourth follows
exactly:

```text
1,000,000 * 731 * 171,000,000 = 125,001,000,000,000,000 atomic
```

which is the accepted manifest's cap for that channel to the atomic unit.

**Day one is the entry airdrop** written by kind 10, and it is what makes a new
account able to transact. **Days two through 731 are ordinary mint permissions**
collected with kind 18.

Enrollment writes `enrolled_at_height`, sets `minted_through_window` to
`window_of_height(enrolled_at_height)`, and sets `issued_atomic` to
`171,000,000`. The identity's last collectable window is

```text
enrollment_last_window = window_of_height(enrolled_at_height) + 730
```

At a kind-18 mint executing at height `h`:

```text
last_completed_window = window_of_height(h) - 1
collectable_end       = min(last_completed_window, enrollment_last_window)
window_start          = max(minted_through_window, collectable_end - 30)
count                 = collectable_end - window_start     when positive, else 0
amount                = count * 171,000,000
```

and on success `minted_through_window` becomes `collectable_end`, `issued_atomic`
increases by `amount`, channel 8's `issued` increases by `amount`, and
`total_supply` increases by `amount`.

**The cap forfeits, and `window_start` is where it does.** A person who has not
collected for forty days collects the most recent thirty windows and the older
ten are never issued. The mark then advances to `collectable_end` rather than to
the walk's end, which is what makes the forfeiture permanent rather than deferred.
That is the founder answer of 2026-08-15: the verified-user channel has no second
destination, so uncollected value is not reallocated, and total supply ends below
the maximum by exactly what was not collected.

**This is the same thirty-window rule as a seat's, applied at a different
moment.** A seat's cap is applied at assignment, where the day's permission moves
to that day's best performers, and it can be because a per-window record exists.
No per-window record exists for 1,000,000 identities and none is affordable, so
the cap is applied at the mint instead. The two mechanisms differ and the rule
does not.

**The walk is arithmetic rather than iteration**, because every window in the
period pays the same amount unconditionally. A verified-user mint is `O(1)`
whatever the gap.

**No transition depends on the cycle-assignment record**, so the verified-user
channel is independent of uptime measurement, of the two-cycle dispute lag, and
of whether any seat exists at all.

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

The two-cycle lag is forced by the dispute window rather than chosen, and the
last assigned window at any height `h` is `window_of_height(h) - 2`.

## Receipt

Each admitted transaction produces exactly one 56-byte receipt:

| Offset | Size | Field |
| ---: | ---: | --- |
| 0 | 4 | ASCII `PSRC` |
| 4 | 2 | receipt version `6` |
| 6 | 32 | transaction ID |
| 38 | 1 | transaction kind |
| 39 | 1 | result code |
| 40 | 8 | fee charged; the fixed fee on success, otherwise zero |
| 48 | 8 | issued atomic units; zero for every non-issuing kind and every failure |

Unknown result codes, an unassigned or retired kind, a nonzero failed fee, and a
nonzero `issued_atomic` on a failure are invalid. **A successful kind 10 charges
a zero fee**, which is the one success in any version with no fee, and the
receipt records it as zero rather than as the fixed fee.

The issuing kinds are 4, 5, 6, 18, and **10**, which is new: a registration
issues the entry airdrop. The non-issuing kinds are 1, 2, 3, 13, 14, 15, 16, 17,
and 19.

## Result codes

| Code | Name | Origin |
| ---: | --- | --- |
| 0 | `SUCCESS` | version one, frozen |
| 1 | `ZERO_AMOUNT` | version one, frozen |
| 2 | `FEE_LIMIT_TOO_LOW` | version one, frozen |
| 3 | `EXPIRED` | version one, frozen |
| 4 | `SENDER_NOT_FOUND` | version one, frozen; unreachable here |
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
| 23 | `MANAGER_LIMIT` | version three; unreachable here |
| 24 | `SEAT_LIMIT` | version four |
| 25 | `ADDRESS_LIMIT` | version four; unreachable here |
| 26 | `SIGNER_NOT_FOUND` | new |
| 27 | `RECIPIENT_NOT_REGISTERED` | new |
| 28 | `ESCROW_NOT_FOUND` | new |
| 29 | `ESCROW_NOT_OWNED` | new |
| 30 | `ESCROW_NOT_EMPTY` | new |
| 31 | `SIGNER_LIMIT` | new |
| 32 | `NOT_ENROLLED` | new |

Codes `0` through `25` keep their exact version-four meanings and `0` through `8`
their exact version-one meanings, so the space extends contiguously.

**Three codes are frozen and unreachable in version six**, and each lost its
subject rather than its meaning: `SENDER_NOT_FOUND` because an escrow that
resolves always exists, `MANAGER_LIMIT` because a seat has no managers, and
`ADDRESS_LIMIT` because an identity's addresses are escrows it creates rather
than accounts it links. They keep their numbers because renumbering a frozen code
space is exactly the compatibility break the space exists to prevent, and the
vectors record their unreachability as derived rather than asserted.

### The model mapping is total and unchanged

`founder-economy-simulator-v3`'s twenty-four codes partition exactly as they do
under versions two through five — 11 carried, 2 guards, 11 unrepresentable —
because the model is unchanged. Fifteen codes here have no model counterpart: the
three version two added, the three version three added, the two version four
added, and the seven new ones.

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
it. The referral channel satisfies the same identity without a carry:

```text
issued(founder_referral) + outstanding(founder_referral)
  = assigned_cycle_permissions * 3,420,000,000
outstanding(founder_referral)
  = sum over identities of (accrued - minted) + (pool.accrued - pool.minted)
```

**Channel 8 satisfies an inequality rather than an equality**, and that is the
shape forfeiture forces:

```text
outstanding(hub_verified_user_incentives) = 0
issued(hub_verified_user_incentives)
  = sum over enrolled identities of issued_atomic
  <= 125,001,000,000,000,000
```

The channel has no accrual step, so it has no outstanding term: value is issued
when it is collected and is otherwise never represented anywhere. The equality
holds only for a population that collected everything within the cap, and the
inequality is what says that a chain whose users forfeit ends below the maximum
supply rather than holding the difference somewhere.

Version six adds four structural invariants:

1. **every account is an escrow.** The version-one account map and the escrow
   entry set have exactly the same key set, so no account exists with no identity
   behind it.
2. **every escrow names a registered identity**, and an identity's `escrow_count`
   equals the number of escrow entries naming it, and its `next_escrow_index` is
   at least that count.
3. **every signer entry names an existing escrow**, and an escrow's
   `signer_count` equals the number of signer entries naming it and never exceeds
   16.
4. **every seat names a registered identity**, and an identity's `seat_count`
   equals the number of seats naming it, and never exceeds 1,000.

All four are equalities or exact bounds rather than loose ones, because a bound
would admit a defect that lost a count. **The first is the one this version
exists for**: it is the founder direction "there is no unverified participation"
written as a property of state.

## Resource limits and storage bounds

Version one's limits are unchanged: at most 65,535 raw inputs and 65,535 admitted
transactions per block, and a 1,048,576-byte canonical object bound. The largest
transaction is 288 bytes and the longest mint walk is 30 assignment records.

| Entry | Bound | Derivation |
| --- | ---: | --- |
| seats | 8,700,000 bytes at capacity | `100,000 * (5 + 82)` |
| HUB identity | 85 bytes per person | `33 + 52` |
| escrow, economy side | 82 bytes per escrow | `33 + 49` |
| escrow, account side | 48 bytes per escrow | one version-one entry |
| signers | 1,040 bytes per full escrow | `16 * (33 + 32)` |
| verified-user enrollment | 57,000,000 bytes at 1,000,000 | `1,000,000 * (33 + 24)` |
| verified-user counter | 9 bytes | one entry |
| channels | 180 bytes | `10 * (2 + 16)` |
| carries | 100 bytes | `10 * (2 + 8)` |
| typed custody | 168 bytes | `4 * (34 + 8)` |
| referral balance | 57 bytes per referring identity | `33 + 24` |
| verifier key | 33 bytes | one entry |
| unreferred pool | 17 bytes | one entry |
| cycle assignment | 25,033 bytes per cycle | `9 + 24 + 2 * 12,500` |

**The seat family fell by an order of magnitude.** Version four's seats and
managers together bounded at 71,600,000 bytes; version six's seats bound at
8,700,000 and there are no managers, because a seat is an identity reference and
nothing else.

**A person's own footprint is `85 + 130 * escrows + 65 * signers` bytes**, which
is the per-person figure ADR 0041 said requirement 12 now needs. Escrows per
identity are **not bounded by rule**, because the founder direction is that a
person may hold as many as they want; they are bounded economically, since each
costs a fixed fee to create. Signers per escrow are bounded at 16, which is a
resource limit rather than a statement about participants.

**Two unbounded terms remain and they are different in kind.** Cycle assignment
records accumulate at one per cycle and are never deleted, about 9.1 MB per year
at full capacity; the cap bounds how many records a mint reads, not how old they
are, so no pruning rule follows from it. Escrow and signer entries accumulate
with adoption and are bounded only by the fee; a chain with ten million
participants holding one escrow each carries about 1.3 GB of them. Both are
recorded rather than solved, and the second is new with this version.

## Determinism

Validation order, result numbers, receipt bytes, successful writes, and failure
atomicity are consensus rules. An implementation must not consult a wall clock,
locale, filesystem order, host integer width, database-native ordering, or
adapter-specific metadata, and must not use floating point on any monetary or
consensus path. Every monetary operation is checked `u64` arithmetic whose
violation invalidates the block.

**The posture's time windows are heights, not clocks.** `slot_of(h)` is derived
from the executing block height and the accepted window grid, so two nodes agree
on whether a confirmation was required without agreeing on what time it is.

No AI inference, external price, biometric result, or telemetry value is a direct
input to any transition defined here. A HUB signature is an Ed25519 signature over
fixed bytes, verified against a key already in state; nothing about the capture
that produced it reaches consensus.

## Compatibility boundary

**Transaction bytes.** A version-one signed transfer is a version-six kind-1
transaction, byte-for-byte, with the same signing message and the same
transaction ID. A version-one node presented with any other version-six kind
rejects it at admission step 1 as `MALFORMED_TRANSACTION`.

**Execution is where the boundary moves, and it moves for the first time.** The
same bytes do not always produce the same result: a version-one transfer to an
account that does not yet exist **succeeds under version one and is refused under
version six** with `RECIPIENT_NOT_REGISTERED`, because version one creates the
recipient and version six requires it to be a registered escrow. A transfer
between two existing accounts produces the same result under both. **The byte
identity is preserved and the execution identity is not**, and no earlier version
had to say that, because no earlier version changed what kind 1 does.

**State.** A version-six state is a version-one state plus one ordered economy
map, and every version-one invariant holds. The account map gains a structural
constraint — every key is an escrow — that version one does not impose.

**Roots.** The version-six state root has a distinct domain label and version
field from all five predecessors, so no earlier root is reinterpreted and no
version-six root collides with one.

**Genesis and chain identity.** Version-six genesis has a distinct schema version
and chain-ID label, so **a version-six chain is a new chain rather than a
migration of a version-five one**. There is no upgrade block and no state
translation; the six contracts are alternative chains and only one will ever
carry value.

**Denomination and supply limit.** Unchanged, and settled by
`ledger-transition-v1` and `founder-economy-manifest-v2` respectively.

**What is not claimed.** No accepted M1, version-two, version-three,
version-four, or version-five vector, digest, receipt, root, or recorded devnet
result changes, and none is recomputed under this specification.

## Versioning and compatibility of this document

The envelope layout, the two schemes, the fourteen assigned kind identifiers and
their bodies, the five retired kind identifiers, the admission order, the escrow
and signer derivations, the state key space and value encodings, the retired
entry kinds, the beneficiary-kind space, the HUB signature family, the posture
predicates, the tree and root constructions, the genesis layout, the receipt
layout, the numeric result codes, the accumulation cap, the verified-user rate
and period, and the rejection orders are immutable for version six. A changed
field, code, order, or semantic rule requires a new transition version and an
ADR; it must not reinterpret a version-six identifier.

Versions one through six coexist as documents; every earlier artifact remains in
place, passing, and unedited.

## What this specification does not establish

- **Direct-channel eligibility.** `direct_issue_authority` remains named and
  undefined for three channels, and kind 6 is refused because of it.
- **That a HUB identity is a distinct human.** The chain verifies a signature by
  a key the ecosystem verifier attested to. **Every guarantee here — one person
  one identity, the per-human seat bound, self-referral refusal, one entry
  airdrop per person — rests on that attestation and is exactly as strong as
  it**, and an entry payment makes a false registration worth attempting in a way
  it was not when verification only gated a seat purchase.
- **That a mandatory-verification ecosystem is reachable.** The verifier is on
  the critical path of every participant's first interaction, and there is now no
  path by which value reaches a person outside the ecosystem.
- **What a coerced HUB signature can do.** It can relax a posture, assign a
  signer, delete an empty escrow, and confirm a transfer. Revocation is the
  remedy and it is a race.
- **HUB key rotation.** No transition changes an identity's recorded public key.
  A person who loses the secret behind it loses every proof this contract
  depends on, and with the posture asymmetry they also lose the ability to
  loosen a posture they set. The chain offers no remedy.
- **Verifier key rotation.** The ecosystem verifier key is written at genesis and
  no transition changes it.
- **The payment.** Nothing here proves that BTC, ETH, or an approved stablecoin
  was received for a seat.
- **That any of this executes.** No C++ implementation exists.
- **The measurement.** Everything `uptime-measurement-v1` does not establish is
  inherited unchanged.
- **Distribution.** No kind here distributes transaction fees or commercial
  revenue to active seats.
- **The unreferred pool's payout.** The month, the ranking snapshot, and the
  payout transition remain unspecified.
- **Legacy succession**, which is the one path by which a seat's identity
  changes and which no transition here implements.

## Required vectors and evidence

`test-vectors/economy-transition-v6.txt` is normative. It fixes the envelope
decomposition and every kind's layout and lengths, including the five-way length
collision; **the kind-1 identity** against the accepted `protocol-primitives-v1`
bytes; the two authorization schemes and that a scheme a kind does not permit is
refused; the cross-kind separation; every admission rejection over a minimally
mutated input with a positive control; the six HUB message constructions and
their pairwise distinctness on identical fields; the complete result-code table,
the three-way partition of the economy model's codes, and the three frozen codes
proved unreachable; every state key and value encoding, including the two retired
entry kinds; the empty, genesis, and populated economy roots and the version-six
state root; **the six-way non-collision** of version-one through version-six
roots over an identical account set and an empty economy, each predecessor's
construction first required to reproduce its own accepted vectors; version-six
genesis bytes, its chain ID, that it differs from a version-five genesis with
identical fields, and that its account count is required to be zero; the receipt
layout, its new version, and the zero-fee success; and the accumulation cap, the
walk range, and the cycle assignment, all required to reproduce version three's
recorded values where the fixture coincides.

It fixes five things that are new with this version:

- **the escrow derivation**, including that two indexes of one identity and one
  index of two identities all differ, and that a deleted index is never reissued;
- **the signer derivation against `test-vectors/protocol-primitives-v1.txt`**,
  because it is the accepted version-one account derivation and a restatement
  that drifted would otherwise agree with itself;
- **the posture predicates**, both of them, over a table that exercises each
  disjunct of the relaxation rule alone and in combination, and the slot mask at
  its boundary;
- **the transfer boundary**, which is the pair of vectors the founder answer
  produced: the accepted version-one transfer bytes reproduced exactly, and the
  same bytes refused with `RECIPIENT_NOT_REGISTERED` against an unregistered
  recipient; and
- **the verified-user arithmetic**: the rate derivation reproducing the accepted
  channel cap to the atomic unit, the remainder a 730-cycle period would leave,
  the entry airdrop, a full 731-window collection, and a forfeiting mint at the
  cap, one window past it, ten windows past it, and long past the period.

The conservation vectors are the load-bearing ones, and the four structural
invariants are checked alongside them, the first by requiring the account map's
key set and the escrow entry set to be equal.

The verifier independently derives rather than restates every recorded value. Its
independence is `tools/economy-transition-v6-vectors/expected.py`, which imports
nothing from `simulation/` and restates the version-one layouts, the Founder
Constitution's tables, and the accepted manifest's channel order by hand.

`docs/engineering/verification.md`'s three vector-file rules apply: a boolean
vector may only be true, a name must assert no more than its value establishes,
and a claim must be checked against something other than itself.

**All of it is recorded.** `simulation/economy_transition_v6/` is the model,
`test-vectors/economy-transition-v6.txt` holds 462 normative vectors, and
`tools/economy-transition-v6-vectors/verify.py` derives every one of them twice.

**A second, separate file records what a chain conforming to this document
*does*.** `test-vectors/economy-transition-v6-execution.txt` holds 512 normative
vectors over a recorded transition trace: registration as one atomic execution,
the recovery path end to end, the accepted version-one transfer admitted and
refused for its recipient, both directions of a posture change, and a block that
writes a cycle assignment and commits a root. It is a separate file because this
one is the artifact the hosted matrix verified on 2026-08-15 and an accepted
vector file is not edited. Building the execution model reached three places
where this document admits two readings and one place where it is silent;
[ADR 0045](../decisions/0045-the-version-six-execution-model-and-three-derived-rules.md)
records each reading, the alternative, and why the alternative was rejected. **No
rule in this document changes as a consequence**, and one — the requirement that
an unrequested confirmation field be zero, placed at admission and named
`MALFORMED_TRANSACTION` — is stated in a place that cannot evaluate it and names
a code the result space does not contain, which a later version should correct
outright rather than leave derived.
Four mutation probes establish that it fails closed: a changed escrow label, a
relaxation predicate that lost one disjunct, a removed accumulation cap, and a
changed account domain octet are each rejected — the last **with the octet
changed in both the model and the independent derivation**, because it is
checked against `test-vectors/protocol-primitives-v1.txt` rather than against a
second restatement of its own formula.

Acceptance requires full GitHub-hosted verification on the exact commit. Passing
these checks establishes an exact, auditable encoding and compatibility boundary.
It does not establish that the transitions execute, that the economy is safe,
that a purchase was paid for, that a HUB identity is a distinct human, or that
the resource bounds are adequate under adversarial load.
