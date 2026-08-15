# ADR 0044: Economy transition v6 — the identity is the account

- Status: Accepted
- Date: 2026-08-15

## Context

Five ADRs of 2026-08-15 replaced the account model every earlier transition
contract assumed. [ADR 0039](0039-hub-verification-is-mandatory-for-everyone.md)
made HUB verification mandatory,
[ADR 0040](0040-holder-addresses-and-revocable-signers.md) replaced
addresses-as-identity with keyless escrows and revocable signers,
[ADR 0041](0041-the-seat-is-tied-to-the-identity-not-an-address.md) tied a
Founder Seat to the identity so that it has no address at all,
[ADR 0042](0042-the-hub-entry-airdrop-and-the-verified-user-rate.md) funded a
brand-new person's first action, and
[ADR 0043](0043-founder-answers-on-reach-asymmetry-forfeiture-and-signers.md)
settled the four decisions the founder-decision gate stopped this slice to ask.

[`economy-transition-v6.md`](../specifications/economy-transition-v6.md) is the
contract that encodes all of it. This record covers the decisions the direction
did not make, the alternatives considered, and the consequences that are easy to
miss.

## The decision

**A verified identity is the root, an escrow is where value sits, and a signer is
who may act on one escrow.** Three objects, each answering exactly one question,
with the version-one account map holding an escrow's balance and nonce so that a
version-six state remains a version-one state plus an economy map.

## What was decided and why

### The escrow identifier is derived, not allocated

```text
escrow_id = H(D("protocol-stack:v6:escrow") || hub_identity_hash || u32(index))
```

ADR 0040 named this as the one place the direction reaches the M1 compatibility
boundary and asked for it to be specified deliberately rather than discovered.

**A derivation beats an allocation.** A counter-allocated identifier would need
the chain to publish a value the person cannot predict, so a wallet could not
compute its own escrow identifiers before the chain wrote them, and two nodes
would have to agree on an allocation order rather than on a hash.

**The index never decreases, and that is the load-bearing part.** A deleted
escrow's identifier is never reissued, so a transaction naming a deleted escrow
can never execute against a different escrow that later occupies its index. The
identity record therefore carries `next_escrow_index` and `escrow_count`
separately; collapsing them into one field makes one of the two properties false.

### The accepted version-one derivation survives by changing what it names

`H(D("protocol-stack:v1:account") || 0x01 || public_key)` stops naming accounts
and starts naming **signers**, which is what a public-key hash is. Four contract
versions preserved this derivation for accounts; version six preserves the
derivation and moves its subject.

**That is why the pivot is cheaper at the primitive layer than ADR 0040
expected.** The direction reads as replacing an accepted primitive; what it
actually does is narrow one and add a second beside it.

### The signature-scheme byte carries the second authorization mode

Version one fixes the scheme byte at `1` and reads offset 40 as the sender's
public key. Version six reads it as an **authority** public key and lets the
scheme say whose: a signer key, or an identity's HUB key.

**This is what lets recovery pay a fee with no key.** A person recovering holds
their face and nothing else, so the transaction that assigns a new signer cannot
be signed by a signer. Scheme 2 is that transaction's home.

**Three alternatives were rejected.**

- *Widening the header with an escrow field.* It ends the kind-1 byte identity
  for every kind at once, to solve a problem five kinds have.
- *Naming the escrow in each body.* Same cost for kind 1, which cannot carry a
  field and stay byte-identical.
- *Verifying scheme-2 envelope signatures against state.* An earlier draft put
  the identity hash in the header and looked its key up in the identity record.
  It works and it moves signature verification from admission into execution,
  which would let an unsigned transaction reach execution and consume block
  resources. Putting the **key** in the header and the identity hash in the body
  keeps admission stateless, which is the property version one has and which
  nothing in the direction asked to spend.

### One nonce per escrow answers the two-signer question with no new machinery

ADR 0040 recorded that two signers on one escrow race for version one's single
nonce sequence and called it engineering's to settle before the encoding. The
answer is that the sequence belongs to the escrow rather than to the signer, so
version one's rule applies unchanged and the loser of a race receives
`NONCE_MISMATCH`. Ordering is the wallet's problem and determinism is the chain's,
which is where both already were.

### Registration is fee-exempt, against ADR 0042's stated preference

ADR 0042 offered two ways to make registration self-funding — credit the entry
airdrop before assessing the fee, or exempt registration — and preferred the
first as "the smaller change", reasoning that 1.71 units far exceeds any
plausible fixed fee.

**That reasoning holds only while an airdrop exists.** The airdrop is bounded at
1,000,000 identities. User 1,000,001 creates a zero-balance escrow, and under
credit-before-fee their registration fails with `INSUFFICIENT_BALANCE` — the
ecosystem would close to new members at exactly the point ADR 0042 says the
problem stops recurring.

Exemption works for every user forever. Its anti-abuse bound is non-monetary and
already present: only the ecosystem verifier can sign a registration, so the fee
was never what limited registrations. ADR 0042 states that either option
satisfies the direction, which makes this mechanism rather than a founder
decision; it is recorded prominently because the ADR recommends the other one.

### A transfer is two kinds and a mint is one kind with an optional field

Both patterns exist in the accepted contracts. Version three split the protected
mint into kinds 3 and 7 rather than adding a presence flag; version four's kind 8
carried a signature field required to be 64 zero octets when unused.

**Version six uses the field form everywhere except the transfer, and the reason
is specific rather than aesthetic.** Widening kind 1's body by 64 octets would
end a byte identity carried since M1. Kind 1's bytes are a compatibility
commitment; nothing else's are. Splitting all three mints instead would have cost
three more kind identifiers to buy uniformity with a rule that exists for one
kind's sake.

### The posture is per escrow, and its direction is derived from stored values

A chain cannot read intent, so "relaxes" is defined over the two stored postures:
turning confirmation off, raising the minimum amount, or setting an exempt slot
bit that was clear. Any one of them makes the change a relaxation and requires
the HUB signature.

**A mixed change counts as a relaxation.** Rounding in that direction is
deliberate: the failure that matters is a stolen signer key weakening a
protection, and a change that weakens anything is a weakening.

**Time windows are block heights.** `slot_of(h)` reuses the accepted window
grid's 24 one-hour slots, so two nodes agree on whether a confirmation was
required without agreeing on what time it is. A wall clock is forbidden on a
consensus path and was never a candidate.

### The verified-user cap is applied at the mint rather than at assignment

A seat's thirty-window cap is applied when the chain writes the cycle-assignment
record, where a capped seat's permission moves to that day's best performers. No
per-window record exists for up to 1,000,000 identities and none is affordable at
25 kB a window, so the verified-user cap is applied at the mint: a collection
covers the most recent thirty windows and the mark advances past everything
older.

**The rule is the same and the mechanism differs, which the specification states
rather than glossing.** The founder answer is that uncollected value is never
issued, and advancing the mark past the forfeited windows is what makes the
forfeiture permanent rather than deferred.

**Channel 8 therefore satisfies an inequality rather than an equality.** It has
no accrual step, so it has no `outstanding` term: value is issued when collected
and is otherwise never represented anywhere, and a chain whose users forfeit ends
below the maximum supply rather than holding the difference somewhere. Every
other channel's conservation identity is unchanged.

### Five kinds and two entry kinds are retired rather than reused

Kinds 7, 8, 9, 11, and 12 and entry kinds 9 and 11 each lost their subject. Their
numbers are left permanently unassigned and refused at admission.

**Reusing a number a reader associates with an accepted contract is the cheapest
possible way to create an auditing mistake**, and five holes in a table cost
nothing. The six kind numbers that keep their subject keep their identifiers for
the same reason.

## Consequences

**The kind-1 byte identity survives a fifth version and its execution identity
does not.** The accepted 136-byte unsigned and 200-byte signed transfer are
reproduced exactly, and the same bytes are refused with
`RECIPIENT_NOT_REGISTERED` when the recipient is not a registered escrow. No
earlier version had to state a divergence between bytes and behavior, because no
earlier version changed what kind 1 does. The specification states it in those
terms and the vectors carry both halves.

**`ledger-transition-v1`'s recipient-creating transfer is withdrawn.** It was the
last way an account could come into existence with no identity behind it, and
"every account is an escrow" is the structural invariant that makes the founder
direction a property of state rather than a policy the ecosystem observes.

**Three frozen result codes become unreachable** — `SENDER_NOT_FOUND`,
`MANAGER_LIMIT`, and `ADDRESS_LIMIT` — each because its subject is gone rather
than its meaning. They keep their numbers, because renumbering a frozen code
space is the compatibility break the space exists to prevent.

**The seat family fell by an order of magnitude**, from version four's 71,600,000
bytes of seats and managers at capacity to 8,700,000 bytes of seats. A seat is
now an identity reference and nothing else.

**A new unbounded storage term appears.** Escrow and signer entries accumulate
with adoption, bounded only by the fee that creates them; ten million
participants holding one escrow each is about 1.3 GB. That is a consequence of
opening the account model to every participant rather than to 100,000 seats, and
it is recorded rather than solved.

**Recovery is not a transaction.** It is the ordinary `signer_add`, authorized by
the identity rather than by a key. The version-five dilemma — who may link an
address to an identity — has no subject here, because an escrow is created
beneath an identity that already exists and is never relinked.

## Compatibility and independent review

No accepted artifact changes. Versions one through five, their models, vectors,
verifiers, and the version-four C++ codec remain in place, passing, and unedited.

Five claims need independent review before value depends on them, and the first
three are inherited and sharpened rather than new.

**That the ecosystem verifier's attestation is sound.** Every guarantee here
rests on it and is exactly as strong as it, and an entry airdrop makes a false
registration worth attempting in a way it was not when verification only gated a
seat purchase. A million entry payments are a million reasons to try.

**That one biometric layer can carry both uniqueness and recovery.** Uniqueness
wants a binding that cannot move; recovery requires one that can.

**That no HUB key rotation is survivable.** A person who loses the secret behind
their recorded key loses every proof this contract depends on — and, new with the
posture asymmetry, also loses the ability to loosen a posture they set, because
relaxing requires that key. A strict posture plus a lost key is a permanently
locked escrow with a nonzero balance, and the chain offers no remedy. **This is
the strongest argument yet that HUB key rotation needs a founder answer**, and it
is recorded here rather than asked, because it blocks nothing in this contract.

**That admission's statelessness is worth what it cost.** Scheme 2 puts a public
key in the header and an identity hash in the body specifically so admission
still verifies a signature without reading state. The price is 32 octets of
redundancy on five kinds; the alternative lets unsigned transactions reach
execution.

**That a five-way body-length collision is safe.** Kinds 5, 14, 15, 16, and 18
all carry 96-octet bodies. The rule that a decoder dispatches on the kind byte
has been in the contract since version two and was first exercised by version
three, but five is the widest collision any version has had, and a decoder that
dispatched on length would now be wrong five ways rather than two.
