# Current state

Last updated: 2026-08-16

## Phase

M3 — Founder Economy devnet, in progress. Slice M3.1 delivered the revised
economic contract, M3.2 made it executable, and M3.3 rebound every dependent
model to it, all on 2026-08-08. M3.4 defined the cycle boundary in chain heights
and M3.5 defined the uptime measurement pipeline, both on 2026-08-09. M3.6a
enforced both inside the economy model and M3.6b rebound the escrow payout
model to it, both on 2026-08-10. M3.6c rebound the scenario suite on 2026-08-11
and closed the dependent rebinding. M3.7a reclaimed the hosted matrix margin on
2026-08-12 and changed no protocol behavior. M3.8a defined the consensus
transaction and state surface on 2026-08-13, M3.8b revised it to
`economy-transition-v3` on 2026-08-14, M3.8c settled it as
`economy-transition-v4` on 2026-08-15, M3.9a put that contract's codec into the
C++20 kernel the same day, M3.9b accepted `economy-transition-v5` after
implementing version four exposed a transition with no conforming
implementation, and M3.9c gave version five its model, vectors, and verifier.

**The owner directed a pivot at the close of M3.9c on 2026-08-15, and it changes
the next action.** HUB verification becomes mandatory for anyone who registers
and for interacting with any part of the ecosystem, an address becomes an
operational tool rather than an identity root, and biometric confirmation
becomes the default on every financial transaction and every mint.
[ADR 0039](../decisions/0039-hub-verification-is-mandatory-for-everyone.md)
records it and the constitution now fixes it. **Three further ADRs the same day
completed the architecture and closed every founder question it raised**:
ADR 0040 replaced addresses-as-identity with keyless asset escrows and revocable
signers, ADR 0041 tied the Founder Seat to the identity rather than to any
address, and ADR 0042 funded a brand-new account's first action from the
verified-user channel. The C++ codec slice is withdrawn; the next slice is the
contract that encodes the direction. **Its founder-decision gate stopped it on
2026-08-15 with four reserved decisions**, two of which the constitution had
listed as unresolved since the pivot; the owner answered all four the same day
and [ADR 0043](../decisions/0043-founder-answers-on-reach-asymmetry-forfeiture-and-signers.md)
records them. **M3.10a then delivered `economy-transition-v6` the same day** —
the specification, ADR 0044, a sibling model, 462 vectors, a verifier, and 91
tests — so requirement 10's target is settled again and the C++ kernel has a
contract the direction does not supersede. **M3.10b then made that contract
execute on 2026-08-16** — a ledger state, the fourteen transitions in their
rejection orders, ordered block execution with the cycle-assignment prologue, a
recorded six-scenario trace, 512 vectors, a verifier, and 51 tests. It is the
first time anything in the repository *runs* a version-six transition rather
than encoding one, and it settled four execution rules the accepted contract
left to be derived. ADR 0045 records them.

Requirements 3, 4, 5, 6, 7, and 12 of `first-goal.md` are satisfied;
requirements 8 and 9 moved from specified to enforced; and requirement 14 is met
against the v3 contract at the standard the M2 suite set.
M2 completed on 2026-08-05 with all sixteen requirements of
`goals/m2-founder-economy-proof.md` passing.

**The remaining M3 work is the C++ half.** Requirements 10, 11, and 13 — the
C++20 kernel implementation, cross-language vectors, and four-node adversarial
scenarios — have not started. Everything delivered so far is specification and
independent Python evidence that activates nothing. **What M3.10b changed is what
that evidence covers**, not whether it activates anything: it is the first
evidence about transitions rather than about bytes, and it is what the C++ side
now has to reproduce.

**The two blocking founder questions M3.8a raised were answered the same day.**
Its gate found that all three authorization predicates the consensus encoding
names were founder-reserved. The owner settled seat purchase, activation, daily
permission assignment, minting, and referral on 2026-08-13, and the answers
changed the transaction set rather than only filling in predicates, so the
specification was rebuilt before being merged. Only direct-channel eligibility
remains reserved, and kind 6 is specified and refused because of it.

**On 2026-08-14 the owner supplied further direction that supersedes
`economy-transition-v2` in four places.** ADR 0033 records it: minted value
lands on the seat's own spendable address, any recorded manager address may act
for a seat, biometric verification on minting is an option the founder switches
on, accumulated unminted permissions are capped with the excess reallocating to
the day's best performers, the unreferred pool pays the single best performer
with exact ties sharing, and a referrer must be HUB verified. HUB — Human
Uniqueness Biometric verification — also becomes an ecosystem-wide identity
layer serving every participant class, with its own direct-mint incentive.

**M3.8b delivered `economy-transition-v3` on 2026-08-14** and merged at
`688efd0`. `economy-transition-v2` stays in place, passing, and unedited apart
from one storage figure that contradicted its own derivation and its own
vectors.

**Requirement 10's target moved again the same day, and the C++ kernel waits for
`economy-transition-v4`.** The owner answered M3.8b's four questions; three
confirmed what version three encodes and the fourth is new direction. HUB
verification survives the loss of any address and is the ecosystem's recovery
layer, and **HUB signing is what adds a Founder Seat address**. Version three
requires an existing manager's signature, so a founder holding no keys has no
path at all. Closing that changes an authorization rule, which is a new version
rather than an edit. ADR 0035 records the direction, and the kernel waits on the
same precedent M3.8a set: the encoding revision comes before the implementation,
because a kernel written against a contract already known to be superseded is
work that has to be done twice.

**Both questions were answered on 2026-08-14 and M3.8c delivered version four.**
Buying a seat requires HUB verification first and the seat is tied to that
identity; a HUB identity's address set lives in consensus state. Requirement 10
is now unblocked against a settled target, and nothing further is expected to
move it.

### How M3.10b was delivered

Issue #153 and PR #173 delivered the version-six execution model and its recorded
transition trace. It added `ledger.py`, `execution.py`, `transitions.py`,
`value_transitions.py`, `block.py`, and `trace.py` to
`simulation/economy_transition_v6/`, 512 normative vectors in
`test-vectors/economy-transition-v6-execution.txt`, a verifier in
`tools/economy-transition-v6-execution-vectors/`, ADR 0045, and 51 tests across
two modules.

**It comes before the C++ kernel because a codec never asks where a transaction
gets its arguments.** M3.9a implemented a version-four codec and M3.9b found that
two implementations agreed perfectly about a message neither could construct.
This is the first step that runs a transition, and it found four things a
byte-level cross-language check could not have.

**Three of them are places where the accepted contract admits two readings, and
one is a place where it is silent.** Every one is consensus-visible: two
conforming implementations that chose differently would return different result
codes, or pay a founder differently, for the same bytes against the same state.
None is founder-reserved — each is a rejection order or a code assignment, which
the constitution names as mechanism — and each is recorded with its alternative
in ADR 0045 rather than settled silently in code.

**Where a cycle assignment lands inside a block is worth more than the other
three together, and it is a decision about money.** `ledger-transition-v1` does
not say whether a record due at a window boundary is written before or after that
block's transactions. Version six's own sentence decides it — "the last assigned
window at any height `h` is `window_of_height(h) - 2`" is a statement about every
transaction executing at `h` — and the trace runs both readings against identical
inputs. Written first, a founder's mint at the boundary collects 114,860,000,000
atomic. Written after, the same mint **succeeds, collects zero, and advances its
mark to that window anyway**, so the cycle is forfeited permanently rather than
deferred. A referral mint in the same block is only deferred, because kind 5
advances its own mark on success alone. Both figures are recorded as vectors.

**`DEBIT_OVERFLOW` had to move to envelope check 8, and the reason is that the
literal order makes the specification contradict itself.** Check 8 is "escrow
balance is below what it must debit", and for a transfer that is
`amount + fixed_fee` — the exact sum kind 1's own condition 5 tests. Evaluating
the overflow test afterwards leaves check 8 undefined on a sum that does not fit
`u64`, and it would make code 7 unreachable in version six, while the
specification lists exactly three unreachable frozen codes and does not list it.
**One real divergence from version one survives and is recorded rather than
smoothed over**: `INSUFFICIENT_BALANCE` now precedes `ZERO_AMOUNT` for kind 1, so
a zero-amount transfer from an escrow that cannot pay the fee answers differently
under the two versions.

**The zero-confirmation-field rule is stated in a place that cannot evaluate it
and names a code that does not exist.** Whether an operation requires a
confirmation is a predicate over the escrow's stored posture, and the
specification says twice that admission reads no state; and the admission and
result code spaces are disjoint namespaces sharing numbers, so result `1` is
`ZERO_AMOUNT` and there is no result code named `MALFORMED_TRANSACTION` to put in
a receipt. It is refused at execution with `UNAUTHORIZED`. **This is the one
specification correction owed to a later version**, and it is the only one.

**`NOTHING_TO_MINT` is the empty walk range rather than an equality**, because a
seat activated in window `w` holds mark `w` while the last assigned window is
`w - 2`. Under the literal wording that mint would succeed, collect nothing, and
set the mark to `w - 2` — a mark that decreases, which destroys the exactness
argument the whole accumulation cap rests on. The trace exercises it directly:
Alice mints immediately after activating and is refused.

**One real defect was found by the tests rather than by the vectors, and it is
the same confusion the second derived rule turns on.** `admit` looked its three
codes up in the *result* code table, so `MALFORMED_TRANSACTION`, `WRONG_CHAIN`,
and `INVALID_SIGNATURE` all raised `KeyError`. The vectors passed anyway, because
the trace had no admission failure in it — so a second finding is that a trace
without a refused input never exercises admission at all. Two admission failures
are now in the fixture and their codes are recorded.

**The accepted version-one transfer is executed, not just encoded.** The exact
200 octets are admitted on a chain stamped with the accepted vectors' chain ID —
which is the only way those bytes reach execution rather than `WRONG_CHAIN` — and
refused with `RECIPIENT_NOT_REGISTERED`. The same transaction with only its 32
recipient octets replaced is accepted. **The byte identity is preserved and the
execution identity is not**, in one trace. The accepted recipient can never be a
registered escrow on any conforming chain, because an escrow identifier is a
digest of an identity and an index and reaching a chosen value is a SHA-256
preimage.

**Version six is the first contract under which a nonzero fixed fee is reachable
from genesis**, and the whole trace runs on the accepted version-one devnet fee
of 1,000 to demonstrate it. Version two derived that a conforming chain must
permit a zero fee, because a zero allocation and a nonzero fee leave nobody able
to pay for the first transaction. Registration is fee-exempt and pays the entry
airdrop, so the first transaction funds itself.

**A registration is exempt from the fee-limit floor as well as from the fee, and
that is forced rather than chosen.** Its fee-limit field is required to be zero,
so a `FEE_LIMIT_TOO_LOW` check would refuse every registration on any chain with
a nonzero fee — closing the ecosystem to new members, which is the opposite of
what exemption exists to guarantee. Expiry still applies.

**The millionth-and-first user is recorded as a consequence rather than argued
about.** They register successfully, receive no airdrop, and hold a zero-balance
escrow, so every transaction they can sign — including the kind-18 mint for a
permission they do not have — answers `INSUFFICIENT_BALANCE` until somebody
already inside the ecosystem sends them value. Only then does the refusal become
`NOT_ENROLLED`. That follows from two accepted decisions, ADR 0042's bounded
airdrop and the universal fee, and nothing in this slice changes it. **The owner
settled it the same day by leaving it as it stands**: the entry airdrop is a
launch incentive with a bound rather than the permanent funding path, and by a
million verified identities the native asset is purchasable outside the
ecosystem, so a newcomer funds their own escrow from outside or an existing
member sends them value.

**Every value two sources can reach is derived twice and recorded only when both
agree**, and `expected.py` imports nothing from `simulation/`. Three inherited
constructions are checked against a third source before anything rests on them:
the ordered transaction tree and the accepted signed transfer against
`test-vectors/protocol-primitives-v1.txt`, and the 146-byte block header and the
block ID against `test-vectors/ledger-transition-v1.txt`. **The block header and
the transaction tree are inherited unchanged, including the header's schema
version of `1`** — version six re-versions genesis, the receipt, and the state
root and says nothing about either, and it states that
`protocol-primitives-v1`'s definitions govern where it imposes no narrower rule.

**Six mutation probes establish that the verifier fails closed**: a re-versioned
block header (104 failures), the cycle assignment moved after the transactions
(33), an unrequested confirmation no longer refused (10), the literal
`NOTHING_TO_MINT` equality (36), a changed escrow domain label (116), and a
fixture that loses its last consecutive block pair (20). The second probe had to
be rewritten once: mutating the flag's *default* changed nothing, because the
fixture passes it explicitly, so the probe was measuring the argument rather than
the behaviour.

**The sixth probe exists because this slice's own file held a vacuous claim.**
Every block in the boundary scenario was separated by a height jump, so the
per-scenario "every consecutive block opens on its predecessor's root" was an
`all()` over an empty set — true forever, establishing nothing. That is exactly
the hazard `docs/engineering/verification.md`'s third rule names, found in the
file written by the person who applied the rule. The scenario gained a real
successor block at the very next height, which also demonstrates that the window
the boundary block assigned is not assigned a second time, and the checker now
**fails** rather than emitting a boolean over an empty set.

**Two states are stamped rather than executed, and both are recorded as stamps.**
The enrollment counter is set one short of the population before any block runs,
so the boundary is then crossed by a real registration; and a height jump between
segments stands in for a run of empty blocks, refusing to skip any window
boundary that would have written an assignment.

**Failed-transition atomicity is checked rather than asserted.** The block
executor commits the state root before every transaction and requires it
unchanged after any non-success result, and the count of refusals that check
covered is recorded per scenario. **Block-level atomicity is the separate rule
and it is implemented rather than described**: an invariant failure, a height
error, or a resource-bound violation restores the pre-block state before the
failure propagates, which is what `ledger-transition-v1` requires and what a
model that only raised would have left as prose.

**Nothing accepted was edited.** All five predecessor vector files verify at their
recorded counts — 238, 579, 441, 550, and 462 — and
`test-vectors/economy-transition-v6.txt` is byte-for-byte unchanged. The
specification gained an evidence pointer and no rule.

### How M3.10a was delivered

Issue #169 and PR #170 delivered `economy-transition-v6` and ADR 0044, merged by
rebase across commits `6fb57f6` through `15b5e90`. It added the specification,
the ADR, a sibling model in `simulation/economy_transition_v6/`, 462 normative
vectors, a verifier in `tools/economy-transition-v6-vectors/`, and four test
modules with 91 tests. The full hosted matrix passed on the exact candidate —
`gcc-debug` 8m33s, `clang-debug` 8m57s, `clang-sanitizers` 9m02s,
`gcc-sanitizers` 9m27s — and again post-merge on `main` in 9m48s.

**A verified identity is the root, an escrow is where value sits, and a signer is
who may act on one escrow.** Three objects, each answering exactly one question,
with the version-one account map holding an escrow's balance and nonce — so a
version-six state is still a version-one state plus an economy map and every
version-one invariant holds.

**The kind-1 bytes survive a fifth version and their execution does not**, and
the two facts have to be stated together or the compatibility section is wrong.
The accepted 136-byte unsigned and 200-byte signed transfer and its transaction
ID are reproduced exactly, and the same bytes are refused with
`RECIPIENT_NOT_REGISTERED` when the recipient is not a registered escrow. That
withdraws `ledger-transition-v1`'s recipient-creating transfer, which was the
last way an account could exist with no identity behind it, and makes **every
account is an escrow** a structural invariant rather than a policy.

**The signature-scheme byte carries the second authorization mode, and that is
what lets recovery pay a fee with no key.** Version one fixes the byte at `1` and
reads offset 40 as the sender's public key; version six reads it as an authority
public key and lets the scheme say whose — a signer key, or an identity's HUB
key. Both verify the envelope signature against the header key, so **admission
still reads no state**. An earlier draft put the identity hash in the header and
looked its key up in state; it works and would let an unsigned transaction reach
execution, so the key went in the header and the identity hash in the body.

**Recovery is not a transaction.** It is the ordinary `signer_add`, authorized by
the identity rather than by a key, against an escrow that already holds value.
The version-five dilemma — who may link an address to an identity — has no
subject here, because an escrow is created beneath an identity and never relinked.

**Registration is fee-exempt, against ADR 0042's stated preference, and the
reason is the millionth user.** The ADR prefers crediting the airdrop before the
fee because 1.71 units exceeds any plausible fee; that holds only while an
airdrop exists. The airdrop is bounded at 1,000,000 identities, so user
1,000,001 would create a zero-balance escrow and fail with
`INSUFFICIENT_BALANCE` — the ecosystem would close to new members at exactly the
point ADR 0042 says the problem stops recurring. Exemption works forever and its
anti-abuse bound is already non-monetary: only the verifier can sign a
registration.

**ADR 0040's two-signer question is answered by version one's own rule.** The
nonce belongs to the escrow rather than to the signer, so two signers race for
one sequence and the loser gets `NONCE_MISMATCH`. No new machinery.

**The escrow identifier is derived rather than allocated**, from the identity and
an index that never decreases. A wallet computes its own identifiers offline, and
a deleted escrow's identifier is never reissued — which is why the identity
record carries `next_escrow_index` and `escrow_count` separately. **The accepted
version-one account derivation survives with its subject moved** from an account
to a signer, which is what a public-key hash is, so the M1 primitive is extended
rather than replaced.

**The posture's direction is derived from the two stored postures**, because a
chain cannot read intent: turning confirmation off, raising the minimum, or
setting an exempt slot bit that was clear. Any one makes the change a relaxation
and requires the HUB signature, so a mixed change that weakens anything counts as
a weakening. Time windows are the accepted grid's 24 one-hour slots — heights,
never a clock.

**Two claims are checked against a third source.** The kind-1 identity and the
signer derivation both against `test-vectors/protocol-primitives-v1.txt`, and the
second matters most: a restatement checked only against its own formula agrees
with itself while both are wrong. **The probe was run with the account domain
octet changed in the model and in the independent derivation, and it still
fails.**

**Four mutation probes establish fail-closed behaviour**, and one of them is the
generator refusing to emit at all: a changed escrow label, a relaxation predicate
that lost its slot-mask disjunct, a removed accumulation cap, and the account
octet. **The boolean rule fired during generation and cost three renamings** —
three posture cases whose answer is "no confirmation" now record the negation
positively rather than recording `false` under a name asserting the opposite.

**The verified-user cap is applied at the mint rather than at assignment, and the
mechanism differs while the rule does not.** A seat's cap is applied when the
chain writes the assignment record, where a capped seat's permission moves to
that day's best performers; no per-window record for a million identities is
affordable at 25 kB a window. So a collection covers the most recent thirty
windows and the mark advances past everything older, which is what makes the
forfeiture permanent rather than deferred. **Channel 8 therefore satisfies an
inequality rather than an equality**: it has no accrual step and so no
`outstanding` term, and a chain whose users forfeit ends below the maximum supply
rather than holding the difference somewhere. ADR 0043 and the constitution were
corrected from "stays outstanding" to "never issued" on the same commit, because
the mechanism does not support the stronger wording.

**Five transaction kinds and two entry kinds are retired rather than reused.**
Each lost its subject, and reusing a number a reader associates with an accepted
contract is the cheapest way to create an auditing mistake. **Three frozen result
codes become unreachable** — `SENDER_NOT_FOUND`, `MANAGER_LIMIT`, and
`ADDRESS_LIMIT` — each because its subject is gone rather than its meaning.

**The seat family fell by an order of magnitude**, from version four's 71,600,000
bytes of seats and managers at capacity to 8,700,000 bytes of seats. **A new
unbounded term appears**: escrow and signer entries accumulate with adoption,
bounded only by the fee, at about 1.3 GB for ten million participants holding one
escrow each. That is recorded rather than solved.

**Nothing accepted was edited.** All five predecessor vector files verify at their
recorded counts — 238, 579, 441, 550 — and the version-one primitives.

### How M3.9c was delivered

Issue #157 and PR #158 delivered version five's evidence and ADR 0038. It added
`simulation/economy_transition_v5/`, 550 normative vectors, a verifier in
`tools/economy-transition-v5-vectors/`, and four test modules with 64 tests.
Version five's status line now says its model and vectors are recorded and its
C++ implementation is not.

**Almost nothing is duplicated, and that is the decision the slice turned on.**
Version five changes one field's meaning, eight labels, and four version fields.
The model imports version four's envelope, key space, registry, settlement,
genesis table, and receipt layout; the independent derivation loads version
four's accepted `expected.py` by path and overrides only what moved. Copying
twelve kind identifiers, twelve entry kinds, and twenty-six result codes to
change eight strings would be a second implementation of an accepted contract
with nothing keeping the two equal — the defect ADR 0026 and ADR 0029 exist to
avoid, and the condition ADR 0029 names for a sibling, a revised transition, is
not met by a relabelling.

**The claim that needed a new kind of evidence is the negative one.** "Everything
else in version four carries over unchanged" cannot be demonstrated by
deriving anything, because a width that moved is simply derived and recorded at
its new value and passes. So the whole vector file is read a second time
against `test-vectors/economy-transition-v4.txt`: every key that file records is
classified as carried, renamed, or revised, the classification must be total, a
carried key must hold version four's exact value, and a revised key must not.
**409 carried, 30 revised, 2 renamed**, and the file records that no envelope,
admission, code-space, state-key, storage, or settlement vector is among the
revised. It fails closed in both directions, and both were demonstrated by
mutation: an undeclared change lands in the carried set and disagrees, and a key
wrongly declared revised lands in the revised set and agrees.

**Kind 11 is now implementable, and the model makes that structural rather than
asserted.** `address_add_message_for` takes one decoded transaction and derives
every field from it — the identity from the body, the account from the sender —
so there is no argument through which a caller can supply an identity the
transaction does not carry. `apply_add_address` has no account parameter at all,
which is what makes squatting unrepresentable rather than merely refused.

**The squatting comparison runs both readings against one registry.** Under
version four's, an attacker links a stranger's account to their own identity and
that person's registration is `REPLAY` forever; under version five's, the same
attacker's transaction links only the attacker's own account and the victim
registers successfully. The superseded reading is kept in the model for exactly
this, labelled as not part of the contract.

**Version five is the first transition contract whose evidence needs the
accepted version-one account derivation**, `H(D("protocol-stack:v1:account") ||
0x01 || public_key)`, because it is the first in which a signed message is built
from the sender rather than from an argument. Version four's fixture could
declare account identifiers as constants precisely because nothing derived them.
**The missing derivation and the defect are the same fact seen from two sides**,
and that is worth carrying into M3.9e: a message assembled from arguments can
name something the transaction does not carry, and one assembled from the
transaction cannot.

**One table is new and is not a relabelling.** `MESSAGE_IDENTITY_SOURCE` records
where a chain obtains the identity each of the eight HUB messages binds — the
body, the sender's address entry, the named account's address entry, or the seat
entry — and records that version four's address add had none. ADR 0037's second
review claim was that no comparable gap remains in the other eleven kinds,
checked by reading; this is that reading written where the next reader can check
it in one place. It is still asserted by the specification rather than executed.

**The genesis fixture holds every field fixed on purpose.** The encoded object
differs from version four's in the schema-version field alone — one octet — and
the chain identifier derived from it differs entirely, which makes "the same
fields under a different label are a different chain" a demonstration rather
than a sentence.

**Three verification rules came out of probing the slice's own evidence, and
they are now repository rules in `docs/engineering/verification.md`.** All three
close the same hole from different sides: **a defect present before a vector
file is first written is recorded at its wrong value and then faithfully
reproduced, so nothing ever fails.**

1. **A boolean vector may only be true.** Its name is the claim, so recording
   `false` records the negation — which is exactly
   `state.no_entry_is_keyed_by_seat_cycle=false`, the defect M3.8b found in an
   accepted file and could only leave in place. A derived `False` is now a
   failure in the checker rather than a value, and it fails twice: once for
   being false and once for leaving its recorded key underived. Neither this
   file nor version four's records a single `false`, so the rule cost nothing.
2. **A name must assert no more than its value establishes.** Three keys in the
   first draft did not: `recovery.the_sender_pays_the_fee` recorded a fee
   *limit*, and two others recorded a hex field or a length under a name that
   claimed a property.
3. **A claim must be checked against something other than itself.** Two checks
   in the first draft were vacuous — one compared a fixture to itself and one
   checked a list against an inline copy of the same list — and both would have
   recorded `true` forever. The account derivation is now checked against
   `test-vectors/protocol-primitives-v1.txt` rather than only against its own
   second restatement, so a formula the model and the derivation got wrong the
   same way still fails.

Each was demonstrated by mutation rather than asserted, and with the account
domain octet changed in *both* sources the generator now refuses to emit a file
at all.

**Nothing accepted was edited.** `simulation/economy_transition/`,
`simulation/economy_transition_v3/`, `simulation/economy_transition_v4/`, their
verifiers, and the version-four C++ codec are untouched, and all four earlier
vector files verify at their recorded counts: 238, 579, 441, and now 550.

### How M3.9b was delivered

Issue #154 and PR #155 delivered `economy-transition-v5` and ADR 0037. It added
the specification and the ADR and nothing else; the model, the vectors, the
verifier, and the C++ update are the next slice and are recorded as absent.

**The slice exists because implementing version four stopped at kind 11.**
`hub_add_address` carries an account and a signature and nothing else, while its
ordered rejection conditions open with "an unregistered `hub_identity_hash` is
`NOT_HUB_VERIFIED`" and its message binds one. The transaction never carries that
identity, and the chain cannot derive it: version four makes the sender
deliberately unconstrained and says why — "a person who holds none of their
linked addresses can still act" — so there is no linked sender to resolve, and
trying every registered key is neither canonical nor bounded.

**No conforming implementation of kind 11 exists**, and the consequence is not a
missing convenience: a founder who has lost every address has no way back, which
is the one guarantee the founder direction of 2026-08-14 was answered into the
contract to provide.

**A byte-level cross-language check could not have caught it, and that is the
general lesson.** M3.9a implements bytes, not transitions. The vectors fix
`message.hex.address_add`, which is built from an identity supplied as an
argument, and nothing in a codec ever asks where a transaction gets that
argument. Two implementations agreed with each other perfectly about a message
neither could construct. The repository's own order — specification, model,
vectors, C++ — is what surfaces this class of defect, and it surfaced this one at
the first step that runs anything.

**The correction reads the 32-byte field as the identity and takes the linked
account from the sender.** The body stays 96 octets and the message keeps its
shape. The obvious repair — an identity field beside the account, widening the
body to 128 — works and leaves squatting open: with the account named in the body
and any sender permitted, anyone may link another person's address to their own
identity, after which that person can never register it and cannot call removal,
because removal is authorized by the identity the address is linked to. Requiring
the sender to be the address added makes squatting unrepresentable.

**It is a new version rather than a repair in place.** Version four's own
versioning section forbids reinterpreting a version-four identifier, and this
reinterprets one. That rule was written one slice earlier; overriding it the day
after, by its author, to save a version is a worse precedent than the version
costs. No recorded byte changes as a consequence — version four's vectors, model,
and C++ codec remain in place, passing, and unedited.

**Version five was accepted without its evidence, which was a departure and was
stated as one.** Every earlier transition contract arrived with its model and its
vectors in one slice. This one did not, because it exists to correct the
contract the repository then called newest, and recording that correction was
more urgent than recording it with its evidence. M3.9c closed that gap the same
day.

### How M3.9a was delivered

Issue #150 and PR #151 delivered the version-four codec in the C++20 kernel. It
added `include/protocol/v4/economy.hpp`, six sources under `src/v4/`, and
`tests/kernel/economy_v4_test.cpp`, registered as `economy-transition-v4-cpp`
beside `protocol-primitives-cpp`.

**This is the first C++ in the milestone, and it is the first time requirement
11 has anything to check.** Everything before it was specification and
independent Python evidence; the codec is the same byte surface written a second
time in the language consensus will run, and the test compares it against
`test-vectors/economy-transition-v4.txt` rather than deriving a second set of
expected values.

**It is a codec alone.** Every entry point is a pure function of its arguments,
it performs no state transition and reads no ledger, and decode failures are
`std::nullopt` rather than exceptions — matching the version-one kernel, where
admission judges shape and nothing else. The transitions are M3.9b and need
block execution and a state store this does not.

**Two things are checked against the accepted M1 file rather than against the
version-four vectors.** The kind-1 identity, because if the C++ encoder does not
emit the accepted transfer bytes the compatibility boundary is broken at its
narrowest point. And the accounts tree, which is what keeps this file's
restatement of the RFC 9162 construction equal to the version-one kernel's
file-private one — that check is the reason a copy is acceptable at all, since
the two produce the same recorded root or one of them fails.

**All four hazards the M3.8c handoff predicted were covered, and two were
demonstrated to be caught.** The bitmaps are packed most significant bit first
and indexed by seat identifier; the cycle-assignment value carries no bitmap
length prefixes, so a decoder must refuse a length that disagrees with its
recorded bit count; dispatch is on the kind byte, and a same-length relabelling
must decode as the kind its byte names and change the signing message; and the
HUB identity record packs 32 + 8 + 4 + 4 into 48 octets with no padding.
Mutating the bitmap packing to least-significant-first and narrowing the address
count to sixteen bits each failed the test, at exactly the check named for them.

**One build defect was found by reading rather than by a failing build.**
`economy_v4_codec_tests` was declared and registered but absent from
`PROTOCOL_STACK_TARGETS`, which is the list carrying `-Wall -Wextra -Wpedantic
-Werror`, the sanitizer flags, `_GLIBCXX_ASSERTIONS`, and the libsodium link.
It would not have linked — but the failure mode that matters is the other one: a
target outside that list builds and passes while held to weaker rules than
everything around it.

**The codec passed on its first run, and the local check that established that
is worth recording.** Building libsodium locally is the heavy operation
`CLAUDE.md` refuses, so the harness supplies the two entry points the kernel
uses and backs SHA-256 with the system OpenSSL — an existing audited
implementation rather than a second one, in a scratch file that is never
committed and never part of the build. That turned a ten-minute hosted iteration
into a one-second one, and it is why three passes were enough.

### How M3.8c was delivered

Issue #148 and PR #149 delivered `economy-transition-v4` and ADR 0036. It added
the specification, the ADR, a sibling model in
`simulation/economy_transition_v4/`, 441 normative vectors, a verifier in
`tools/economy-transition-v4-vectors/`, and 87 tests across four modules.

**HUB verification became the root of identity, and the architecture follows
from one decision.** A registration records the person's own public key, so
every later proof of that person — purchase, activation, a protected mint,
removing protection, adding a seat address, adding or removing an ordinary
address — is a signature by that key. **The ecosystem verifier signs exactly one
thing: a registration.** That is the one judgement no chain can make, and once
made nothing else needs the verifier.

**That restores a containment property version three had to concede.** Version
two could say the verifier gated entry and never payment; version three could
not, because a seat with protection switched on made verifier availability a
precondition for its own income. Version four restores it and widens it: an
unavailable verifier stops new people joining and stops no participant already
inside from doing anything at all.

**The constitution's per-human seat bound reached the chain for the first time.**
Version three records that the 1,000-seat limit "is not enforced by any
transition here, because enforcing it requires knowing that two biometric hashes
belong to one human, which is exactly what the chain cannot see." With one
identity per person in state it can, and `SEAT_LIMIT` is that rule enforced. The
vectors exercise it at 999, 1,000, and 1,001.

**Self-referral became checkable.** Version three compares two account
identifiers, so a buyer could refer themselves from a second address. Version
four compares two HUB identities, and one person has exactly one. The fixture
holds both addresses of one person and records that version three would have
accepted the referral.

**Referral earnings moved from an address to a person**, which is forced rather
than chosen: the whole point of the recovery direction is that losing an address
loses nothing, and a balance keyed by an address would be the one place it still
did over a 731-cycle benefit.

**Three kinds accept any sender, deliberately.** Adding a seat address, adding
an ordinary address, and removing one are exactly the transactions a person must
be able to make holding none of their own addresses, so the signature is the
authority and the sender only pays the fee.

**The settlement was imported rather than copied, and that is checked against
version three's own recorded file.** The accumulation cap, the cycle-assignment
record, and the bounded mint walk are unchanged, so a copy would be a second
implementation of one accepted contract with nothing keeping the two equal. The
vectors require the record version four writes for the same population to equal
`test-vectors/economy-transition-v3.txt` byte-for-byte, and the referral
accrual's re-keying from an account to an identity needed no new code, because
version three's referrer key is opaque bytes — which is itself evidence the
settlement did not move.

**The largest transaction shrank.** Purchase no longer carries a 32-byte
biometric identity hash, because the seat's identity is the purchaser's HUB
identity and the chain reads it from the registry rather than being told it. The
64-byte signature stays and changes hands, from the verifier's to the
purchaser's own. The protocol's largest transaction fell from 325 bytes to 293.

**Each of the three predecessor root constructions is required to reproduce its
own accepted vectors** before the four-way non-collision rests on it, because a
lookalike would make "the roots differ" trivially true. All four roots differ
over an identical account set and an empty economy.

### How M3.8b was delivered

Issue #144 and PR #145 delivered `economy-transition-v3` and ADR 0034. It added
the specification, the ADR, a sibling codec-and-settlement model in
`simulation/economy_transition_v3/`, 579 normative vectors, a verifier in
`tools/economy-transition-v3-vectors/`, and 125 tests across four modules.

**Four things changed and two followed from them.** Any recorded manager address
may act for a seat; a biometric approval on minting is a per-seat option with an
asymmetric switch; unminted permissions are capped at thirty windows with the
excess reallocating to the cycle's best performers; and a referrer must hold a
HUB registration. The two consequences of ADR 0033's first decision are that
minted value lands in an ordinary spendable account rather than typed custody,
and that the account credited is the signer's.

**Two answers were derived rather than chosen, and both decide who is paid.**
The mint must credit the signing manager, because the constitution makes adding
a verified manager the remedy for a lost address, and a mint that credited the
recorded purchaser would leave that remedy able to recover nothing. And a capped
seat must be excluded from the winner set, because it can accrue nothing, so
including it would divide a reallocated permission by a count containing a
recipient that cannot receive and send that fraction nowhere — making ADR 0033's
own sentence false for it and stranding the value as permanently unmintable.
ADR 0034 records both derivations rather than burying them in an encoding.

**The cap is measured in windows, and only that form bounds anything.** ADR 0033
states that the cap turns the growth of a mint's work into a constant. A counter
of accrued cycles does not: thirty accruals can be spread over any number of
windows, so a mint would still walk every window since the mark to find them.
Measuring in windows makes the walk `(mark, min(last, mark + 30)]`, and the bound
is exact rather than conservative — the mark changes only at a mint and a mint
sets it to the last assigned window, so every window in `(mark, last]` was
assigned while the mark held its current value and the assignment applied the
same predicate against that same mark.

**A mint that collects nothing still advances the mark, and that is forced.** A
seat that failed every cycle for two months would otherwise be permanently past
the cap with nothing to collect, so `NOTHING_TO_MINT` would refuse the one action
that could free it. The code is reserved for a mark already at the last assigned
window.

**The optional biometric is a second kind rather than an optional field, and
kinds 3 and 7 therefore share a body length.** That is the case version two
predicted when it required a decoder to dispatch on the kind byte rather than on
the length, so the collision is evidence the rule was right rather than a defect
it created. A single kind with a presence flag would have made every unprotected
mint 229 bytes instead of 164 and needed a rule for a signature the seat did not
require.

**HUB verification enters consensus as one registry entry and one transaction,
and no more.** ADR 0033 widens HUB into an ecosystem-wide identity layer, and
that layer is an M4 milestone specified nowhere. What consensus needs is a
registry a purchase can consult. **One-human-one-account is deliberately not
enforced**, because enforcing it decides what happens to a verified human who
loses their key, which is founder-reserved; the chain records what the verifier
attested, exactly as it does for the seat biometric hash.

**Five defects in version two were found by deriving version three, and three
are fixed by the new contract.** Its bitmaps are indexed by in-scope rank, so
reading one seat's bit requires deriving the whole in-scope set inside a
transition version two describes as `O(1)`; version three indexes by seat ID.
Its record carries no count of reallocated permissions, without which a winner's
entitlement is not computable from the record, and the count cannot be recovered
from the bitmaps. Its assignment adds the carried remainder beside outstanding
rather than out of it, so the carry identity it states as an equality does not
follow from its own steps.

The other two are evidence defects rather than contract ones. A storage figure —
the carry family recorded at 180 bytes beside the derivation `10 * (2 + 8)`,
which gives 100, and which `test-vectors/economy-transition-v2.txt` also records
as 100 — **is repaired in place**, because a figure contradicting its own
derivation is prose rather than a rule. And
`state.no_entry_is_keyed_by_seat_cycle=false` in the accepted vector file
**states the opposite of what its own name asserts**: the property is true and
the expression behind it is wrong, so the file records `false` for a design
property the specification claims. That one is left alone, because a vector file
is the artifact the hosted matrix verified rather than prose. Version three
replaces the check with one that cannot pass while being false: it restates each
key as its named fields, derives every key width from that table, and then asks
directly whether any key names both a seat and a cycle.

**Storage moves in two directions and the one unbounded term does not move.**
Typed custody collapses from 4,200,000 bytes at capacity to 168, because minted
value lands in accounts founders already hold in order to pay a fee; the manager
set adds a bounded 59,200,000-byte worst case at 16 managers per seat that no
plausible deployment reaches. Cycle assignment records still accumulate at
25,033 bytes per cycle — the same width as version two's while carrying one more
field, because the two bitmap length prefixes are gone. **The cap does not prune
them**: it bounds how many records a mint reads, not how old they are, and a seat
whose mark is a thousand windows behind still walks records a thousand windows
old.

**The fixture is a discriminator rather than a restatement.** Seat 11 holds the
cycle's maximum uptime and is over the cap, so under the rejected reading the
winner set would be that seat alone — and the accepted economy model, which
applies no cap, returns exactly that. Seat 23 is past its own 731 cycles and wins
without accruing; seat 15 sits exactly on the 18-hour threshold and accrues
without winning. A second cycle is a total outage, so the winner set is empty and
the whole permission carries, which is the founder-directed rule for that case
and the one path a busy cycle never reaches.

**The verifier's independence is now two-sided.** `expected.py` still builds the
version-one transfer as one flat 136-byte field table while the model builds it
from three parts, and it now also reimplements the cap predicate, the winner
rule, the split, and the mint walk from the specification's prose. A settlement
defect that produced a self-consistent record would have to produce the same
record twice. The version-two root restatement is checked against
`test-vectors/economy-transition-v2.txt` before any non-collision claim rests on
it, and all three state roots are required to differ over an identical account
set and an empty economy.

### How M3.8a was delivered

Issue #139 and PR #140 delivered `economy-transition-v2` and ADR 0032, merged by
rebase across commits `f8d6374` through `5f66c49`. It added
the specification, the ADR, the codec model in `simulation/economy_transition/`,
238 normative vectors, a verifier in `tools/economy-transition-vectors/`, and 91
tests. It satisfies requirements 5 and 6 of `first-goal.md`, and completes
requirement 12 as a consequence of fixing the state keys.

**The slice was specified twice, and the second version is the delivery.** The
first draft named three authorization predicates and defined none, and it
therefore had to guess at the shape of the transitions those predicates govern.
The owner settled them on 2026-08-13 and the answers changed the transaction set
rather than only filling in blanks. The draft was rebuilt in place rather than
merged, because merging would have accepted a contract as immutable while
already knowing three of its records were wrong.

**What the founder decided.** A seat is purchased in one atomic transaction that
registers its biometric hash and the purchaser's address, gated by an off-chain
verifier signature. Activation is separate, one-time, permanent, and triggered
by the purchaser. While a node is up the chain writes mint permissions daily by
itself. Minting takes everything — one button, no quantity — and is the only way
native units reach a founder. Referral is a separate pool on a separate button,
accruing daily regardless of any node's activity and paid to a user account
rather than to a seat. Minting needs only the wallet signature.

**The version-one transfer factors, and that survived the rewrite unchanged.**
Every version-two transaction is a shared 80-byte header, a kind-specific body,
a shared 16-byte trailer, and a signature. The header is exactly the accepted
transfer's first 80 bytes and the trailer exactly its last 16, so kind 1's
40-byte body is what remains and the accepted 136-byte unsigned and 200-byte
signed transfer are reproduced byte-for-byte, transaction ID included. The
schema version stays `1`, both signing labels stay unversioned because the kind
byte and chain ID are already inside every preimage, and version one's result
codes 0 through 8 apply to all six kinds because they are envelope conditions
rather than transfer conditions.

That claim is checked against a third source rather than against itself. The
verifier's `expected.py` builds the transfer as one flat 136-byte field table,
exactly as `protocol-primitives-v1` writes it, while the model builds it from
the three parts; both must then equal the bytes
`test-vectors/protocol-primitives-v1.txt` already records.

**No transaction records a cycle.** The chain writes each cycle's outcome itself
at a block boundary, so the draft's submitted evaluation transaction is gone and
five model rejection conditions go with it: a record nobody supplies cannot be
missing, invalid, incomplete, inconsistent, or out of scope. The two-cycle
settlement lag this needs is forced by the AI dispute window rather than chosen,
and is recorded as forced.

**A mint takes everything, and that is what bounds the state.** One
`minted_through_window` high-water mark per seat replaces what the draft stored
as one verdict entry per seat-cycle — 73,100,000 entries and about 585 MB, plus
512 MB of referral accrual keys. The mark is both the bookkeeping and the replay
protection. A design in which a founder could mint a chosen amount could not
have this property, so the founder rule is also the reason the state is bounded.

**The winner commitment is replaced by a winner bitmap.** The draft committed to
the winner set and required an exercise to carry it, reaching 400,170 bytes for
one fully tied cycle — which under a take-everything mint would have been that
many times the number of saved failed cycles. Each cycle's record now holds a met
bitmap, a winner bitmap, the per-winner share, and the counts, so the set is
readable from state and **the largest transaction in version two is 325 bytes**.
No kind is variable-length and no two kinds share a length.

**Every leg of a failed cycle's permission is divided, not only the operator
leg.** The whole permission moves to that cycle's winners, so the escrows and the
System Creator are paid at the winner's mint rather than at a mint the failed
seat may never make. Each of the five legs is divided by the winner count and
each can leave a remainder, so the carry is per channel.

**Eleven of the economy model's twenty-four result codes become unrepresentable,
in four groups with a reason each**: five because the uptime record is state the
chain writes, three because no transaction names a window, two because the
activation height is the executing block height, and one because a
take-everything mint has no per-cycle key to miss. Eleven are carried and two are
guards `ledger-transition-v1` already routes to block invalidation. The vectors
require the three sets to partition the model's own declared set.

**A Founder Economy chain is a new chain, not a migration.** Version-two genesis
takes schema version 2, binds both the accepted manifest digest and the ecosystem
verifier key as fields, and uses a distinct chain-ID label; the state root takes a
distinct label and version field. A version-one and a version-two root over an
identical account set and an empty economy are required to differ.

**The verifier key gates entry and never payment.** Kinds 2 and 3 carry an
Ed25519 signature by that key over a message binding the chain, the seat, the
purchaser, and an expiry, so an approval cannot be replayed onto another seat or
attempt. Kinds 4 and 5 carry no second factor, so an unavailable verifier stops
new seats and stops no income — the containment direction the constitution
insists on. A stolen wallet key can mint, and only to the seat's own recorded
account.

**Three genesis requirements relax, each forced, and the third exposed a gap.**
The constitution's no-genesis-allocation rule means a conforming chain opens with
zero supply and zero accounts, which version one forbids. The fixed fee then has
to permit zero as the consequence: with a zero allocation and a nonzero fee, no
account can pay for the first transaction, so the chain can never reach a state
in which any fee is payable.

**Kind 6 is specified and refused.** A conforming chain rejects every direct
issue with `UNAUTHORIZED` until the eligibility predicate is accepted, and the
vectors record the unreachability of its five inner conditions.

**One documentation gap was found and repaired.** ADR 0031 had never been indexed
in `docs/README.md`; M3.6c added the ADR and not its entry.

### How M3.7a was delivered

Issue #135 and PR #136 delivered the margin reclaim at merged commit `79d1c0f`,
in two commits. It changed no vector, model, source, specification, or ADR: the
whole diff is test scaffolding, build registration, `tools/verify.sh`, and
`docs/engineering/verification.md`.

**The test phase fell from 707.57s to 255.08s on the PR head and 286.64s
post-merge.** `ctest` was running perfectly serially, which the previous slice's
own measurement had already recorded without naming the cause: 105 tests, sum
707.5s, `Total Test time (real) = 707.57 sec`. Two equal figures are a run with
no concurrency in it.
`tools/verify.sh` now passes `--parallel` at `nproc`, and
`PROTOCOL_STACK_TEST_JOBS=1` restores the serial path for an ordering-sensitive
failure. The two CometBFT integrations run after CTest and stay serial, because
they bind real ports and supervise process groups.

**The slowest job margin went from 3m36s to about 10m.** Every preset roughly
halved. Taking the post-merge run as the conservative figure, `gcc-debug` went
14m30s to 8m28s, `clang-debug` 15m20s to 8m44s, `gcc-sanitizers` 16m24s to
9m17s, and `clang-sanitizers` 15m41s to 9m58s. The slowest is now
`clang-sanitizers` rather than `gcc-sanitizers`, leaving 10m02s against the
20-minute per-job timeout.

**The scheduling is within 3-5% of its floor, which is what the `COST` entries
buy.** Under 4-way contention the 106 entries sum to 992.0s on the PR head and
1096.7s post-merge, so the floor is `max(longest entry, sum / 4)` — 248s against
an actual 255.08s, and 274.2s against an actual 286.64s. Without a cost `ctest`
starts entries in registration order and the slowest are registered last, which
would have ended the run with one long test and three idle workers. The recorded
figures are a scheduling hint rather than a bound: a stale one costs packing
efficiency and never correctness, and a fresh checkout has no
`CTestCostData.txt` to use instead.

**The two runs differ by about 12%, which is runner variance rather than
anything the change controls.** The same 106 entries summed to 992.0s and
1096.7s on identical code, and `economic-envelope-study` alone moved from 143.8s
to 157.4s. Read the margin as roughly ten minutes, not as a precise figure.

**`scenario-v2` was rebuilding one population run three times.** It cost 107.9s
against `scenario-v3`'s 46.0s for strictly more work, because three separate
`setUpClass` bodies each built the complete 731-cycle run while
`scenario_v3_common` builds it once and deep-copies; the seeded property runs
were rebuilt six more times, once per test method. That is the defect PR #123
fixed for the uptime fixtures, in a module that predates the convention. The two
runs carrying a determinism claim still compute fresh: the prefix replays are
simulated per prefix and compared against the shared run, and
`test_the_same_seed_reproduces_the_same_digest` replays each seed against the
cached result rather than comparing a cached run to itself. Locally the module
fell from 70.3s to 32.0s and gained two tests guarding the risk the cache
introduces.

**The registration guard was registered in neither execution path, and that was
found by asking whether the new check would actually run.** The workflow runs
`unittest discover -s tests/tools` only when the scope classifies `lightweight`,
and `tests/tools/test_registration_test.py` had no `add_test`. A change that
adds a test or a verifier classifies `full`, so the one check that catches an
unregistered entry was skipped by exactly the pull requests able to introduce
one. The M3.6c handoff's claim that it "fires on every pull request including a
documentation-only one" was true only of documentation-only ones.

**That is the M3.6c defect one level up, and it is the same mistake a third
time: evidence counted from the command that happened to run rather than the
command the gate runs on the path that matters.** The guard is registered now,
and a new test requires every `tests/tools` module to be registered so the next
one cannot repeat it.

**The block parser was under-reaching in the same direction.** Anchored to a
closing paren in column zero, it silently swallowed all six nested fuzz entries
into the preceding match rather than failing. A test now requires the parse to
reach every `add_test(` in the file, because a pattern matching nothing would
pass the uniqueness check vacuously.

**The study entries were measured and correctly left alone.**
`economic-envelope-study` and `admission-cost-study` each call `run_study()`
three times — once in `setUpClass`, once in-process to prove reproducibility, and
once through the CLI as a subprocess to prove byte-identity. One envelope run is
16.0s against a 62.2s local entry and one admission run is 8.7s against 31.9s,
so all three are accounted for and every one is load-bearing. Unlike
`scenario_v2_test.py`, where three identical runs were rebuilt with nothing
asserting they agreed, there is nothing to reclaim here without deleting a
check.

### How M3.6c was delivered

Issue #131 and PR #132 delivered `economy-scenario-suite-v3` at merged commit
`c44c320`, in four commits. It added the specification, ADR 0031, a schedule, a
probe and a population module, a property generator, `expected_v3.py`, 158
normative vectors, and 51 tests — and repaired two evidence-gating defects left
by the two preceding slices.

**The activation heights are forced, not chosen.** Keeping the tick a shared
window is the property scenario 1 exists to demonstrate, and `cycle-boundary-v1`
then determines everything else: seat `k` activates inside window `k * STAGGER`,
opens at `k * STAGGER + 1`, and holds cycle `t - k * STAGGER` in window `t + 1`
for every seat and every one of its 731 cycles. The heights are non-decreasing in
seat order, so emitting the activations in that order satisfies the monotonicity
condition version three enforces at the writer. A test recomputes the whole
mapping from the grid rather than from the generator's arithmetic, so a generator
that agreed with itself and disagreed with the accepted grid fails.

**One early window has no eligible recipient, and the path was kept rather than
designed away.** A seat now enters a record when its own schedule opens, so seat
0 fails its cycle 0 while it is the only seat in scope: it cannot reward itself,
the derived winner set is empty, and the founder-directed rule carries the whole
342-unit portion forward. Version two's scenario never reached that path, and it
is the only place the suite reaches the empty-winner rule at population scale.
Moving the failure phase to avoid it, or activating every seat at one shared
height, were both rejected — the first deletes founder-directed coverage and the
second recreates the per-seat-window defect ADR 0027 records.

**The totals cannot reveal it, which is why it is a vector.** The carried portion
is delivered at tick 73 to the same seat that would otherwise have received it at
tick 0, so the three population seats' custody is byte-identical to version
two's. A closed form assuming every failed cycle pays a seat in its own window
reproduces every monetary total in the scenario. It is caught only because
`economy.unrewarded_windows` is derived from the trace on one side and from a
walk of the founder rule on the other, and the fail-closed evidence confirms that
mutation is rejected on that single vector and nothing else.

**A peer seat, because the window check now precedes the binding check.** A
contradictory record can only be presented inside a window the evaluating seat
genuinely holds, and a window is only bound by an accepted evaluation, which the
probe seat cannot supply for its own cycle without that being a replay. A second
seat sharing the probe seat's activation height is therefore required, and it
makes the probe sharper rather than merely possible: the refused event is a seat
claiming a higher uptime for itself than the window's bound record carries. A
third seat opening one window later supplies `SEAT_NOT_IN_SCOPE`. All three are
excluded from every population record by their heights rather than by event
order, so the totals stay statements about the three population seats.

**Scenarios 2 and 3 were re-proved, not inherited.** One test asserts the Founder
Seat sale and revenue routing packages contain no economy import, channel
identifier, or supply figure; another requires every `seats.` and `routing.`
vector to be byte-identical across all three accepted suite vector files.

**Two evidence-gating defects were found and fixed.** `CMakeLists.txt` registers
each test and verifier with an explicit `add_test`, and five test files and two
verifiers delivered by issues #125 and #128 had no entry, so the complete hosted
matrix those slices recorded as evidence never ran any of them. Registering them
exposed a second defect underneath: `ctest` invokes a test as `python3 <path>`,
and the four `founder_economy_v3` modules were written for `unittest discover` —
a package-relative import and no repository root on `sys.path` — so as scripts
they failed at import. Their recorded evidence came from a command the gate would
never issue. Both are now guarded by `tests/tools/test_registration_test.py`,
which runs under the focused metadata path and therefore fires on every pull
request including a documentation-only one.

**The two defects are the same mistake twice: evidence counted from the command
that happened to be run rather than from the command the gate runs.** A static
guard is the remedy because it is the *absence* of an invocation that must be
detected, and no run can detect its own absence.

### How M3.6b was delivered

Issue #128 and PR #129 delivered `escrow-payout-v3` at merged commit `93e782a`.
It added the specification, ADR 0030, a third `Binding`, the rebound fixture,
`--version v3` in the verifier, 174 normative vectors, and 14 tests.

**A third `Binding` rather than a package, and that is the same test ADR 0029
applied in the other direction.** ADR 0026 named the condition under which a
shared implementation becomes wrong: a version that revises a payout rule.
Version three does not meet it. What economy version three revised is the
*economy* model's transitions — an activation height, a window check, a
completeness check — and this model performs none of them; it reads one recorded
economy state by digest. A version owns what its own behavior changes, which is
why the economy model earned a sibling package and this one did not.

**Containment is checked against every predecessor, not only the immediate one.**
Extending version two's check to "replay v2 through v3" would have looked
complete and is not: the three economy state labels are distinct strings rather
than a chain, so refusing a v2 state implies nothing about refusing a v1 state,
and a defect with a fallback label, a truncated comparison, or a digest over the
wrong preimage would pass a check that only ever offered it v2 states. The
verifier replays both earlier fixtures through the v3 walk and records an offered
and a rejected count per predecessor, written over an ordered predecessor table
so a fourth version inherits it by adding one entry.

**The equivalence is asserted rather than assumed.** The scenario is held fixed
with only its four embedded economy states rebound, so a differing trace can only
mean a rebinding defect. All three runs produce identical result codes for all 39
events in identical order, and any two final states differ in exactly one member,
`bound_state_digest`.

**The opening custody coincides and its source does not.** The bind yields
34,200,000,000 / 6,840,000,000 / 3,420,000,000 atomic units under all three
versions, because the escrow legs are unrevised and all three fixtures accept two
base permissions. The state those amounts come from is not the same state: the v3
research scenario records activation heights, enforces the window check, and
requires complete records, so its final state has a different shape and digest.
Both facts are recorded separately, so the coincidence is evidence rather than
being read as continuity.

**`caps_agree()` now compares every registered binding instead of two.** The
recorded value does not change, so `escrow-payout-v2.txt` is byte-for-byte
unchanged, which the diff shows directly. Strengthening a check must not silently
rewrite accepted evidence.

### How M3.6a was delivered

Issue #125 and PR #126 delivered `founder-economy-simulator-v3` at merged commit
`271a173`. It added the specification, ADR 0029, the model in
`simulation/founder_economy_v3/`, a 62-event research fixture, 373 normative
vectors, a verifier in `tools/founder-economy-v3-vectors/`, and 63 tests.

**Three things change and nothing else does.** The seat record carries an
`activation_height`, `evaluate_base_permission` applies `cycle-boundary-v1`'s
window predicate, and a record must cover exactly its window's in-scope seat set.
The referral, the exercise, the direct-issuance transition, the carry and its
conservation identity, the journal buckets, the channel table, the base legs, the
activity threshold, and the winner, tie, and remainder rules are identical and
are incorporated by reference rather than restated.

**The manifest is not re-versioned.** No channel, cap, leg, denomination,
subtotal, beneficiary kind, seat capacity, per-person bound, or issuance-cycle
count moves, so version three loads the same 2,267-byte artifact with the same
digest. A third loader for a byte-identical accepted manifest would be a third
implementation of one contract with nothing keeping the three equal, so the
package binds the accepted v2 manifest layer instead of copying it.
`uptime-measurement-v1` likewise needs no version: the record's shape is
unchanged, which is what the M3.5 slice order was for.

**A sibling package rather than a `Binding`.** ADR 0026 chose one shared
implementation for `escrow-payout-v2` because the two versions differed in six
strings, and it named the condition under which that choice inverts: a version
that revises a transition. This slice meets it — a new transition input, a
changed state shape, six new rejection conditions — so a `Binding` would have to
select behavior rather than strings, which is a branch inside every affected
transition and exactly the drift the escrow decision avoided by having none.

**No cycle-boundary state is bound by digest, and that is the load-bearing
asymmetry.** `escrow-payout-v1` binds a foreign economy state because it reads
what another model wrote. Here the economy model is the **writer**:
`cycle-boundary-v1` says outright that it takes an activation height as given.
Binding a second activation table would create a schedule that could disagree
with the seat table this model already holds, and in a consensus implementation
the two are one chain state, so the disagreement would be unrepresentable there
and reachable only in the model. Agreement is required by construction and
proved externally: 45 cross-model probes require the accepted boundary model,
version three, and the founder restatement to give the same verdict, including
all three window rejection codes.

**Monotonicity moved to the writer.** `cycle-boundary-v1` states why an
activation height may not decrease and cannot enforce it against a seat table it
does not hold. Leaving it out would have left the containment stated in one
accepted artifact and applied in none.

**The in-scope set has no upper bound.** Bounding it at `last_cycle_window` is
the tempting narrowing and was rejected: the constitution ends a seat's issuance
period while keeping the seat permanent and its node running, and the
reallocation rule asks for the highest uptime in the window rather than the
highest among seats still issuing. Adding the bound would also make the producing
and consuming ends derive different sets from one schedule, which is the single
property that makes them agree.

**Completeness is two codes because the defects have opposite effects.** An
omission shrinks the population a reallocation ranks over and can send a failed
cycle's Founder portion to a seat that was not the best; an addition admits a
seat with no evidence for the window and could make it the winner.
`SEAT_NOT_IN_SCOPE` reuses the name `uptime-measurement-v1` already gives the
same concept, so both ends describe one condition with one word.

**The intrinsic checks precede the run-history check.** The boundary and
completeness checks are properties of the record, the seat, and the schedule
alone; `INCONSISTENT_UPTIME_RECORD` is a property of what an earlier event bound.
The other order would make one defect report as two different codes depending on
unrelated history. A rejected event binds nothing, so a defective record cannot
occupy a window and make a later correct one inconsistent with it.

**A height is a string and a window is a number, derived rather than chosen.**
`MAX_WINDOW` is 640,511,947,003,803, more than fourteen times below the largest
integer a conforming JSON stack represents exactly, so every window reachable
from a representable height is an exact JSON number while a `u64` height is not.
That is what keeps `cycle_window` a number inside the `cycle_uptime_record` and
therefore keeps the record byte-identical to the one `uptime-measurement-v1`
emits.

**Result-code coverage is partitioned rather than claimed whole.** Twenty-two
codes are event-reachable and all twenty-two are produced by execution; two are
guards. `ARITHMETIC_OVERFLOW` and `INVARIANT` are unreachable from any event
array at any representable scale, because every accumulated quantity is bounded
far below `u64` by a channel cap, so they are proved present by direct exercise
rather than deleted or claimed covered. M3.5 deleted its unreachable code because
no path produced it at all; these two are different, and the partition is what
makes both statements true at once.

**One limit was found by self-review and is recorded rather than asserted away.**
Completeness is measured against the seat table as it stands, and the model has
no current height for an evaluation, so it cannot require that every in-scope
seat has already activated. A chain closes that by ordering, because a record is
emitted only after its window is final. `HEIGHT_NOT_MONOTONIC` bounds the residue
to an event ordering a chain does not produce — once an activation lands at or
above a window's first height, no later one can join that window's in-scope set —
and both the vectors and a test derive that narrowing.

**Nothing accepted was edited.** `simulation/founder_economy/`,
`simulation/founder_economy_v2/`, `simulation/cycle_boundary/`, and
`simulation/uptime_measurement/` are untouched, and a test re-runs the v2
research scenario and requires its recorded state and result digests. No v1 or v2
artifact, C++, consensus, or devnet behavior changed.

On 2026-08-09 the owner also made the founder-decision gate an explicit step of
`proceed`. Issue #117 and PR #118 merged at `0b8c7c2`. The gate now runs after a
slice is selected and before its work begins, enumerates that slice's decisions
before judging them, classifies each with a citation, and reports a result even
when nothing is reserved, so a silent session is evidence that the check ran
rather than that it was skipped. Questions go in one batched selectable-option
call at the end of a response. `CLAUDE.md` gained one clause the reserved set was
missing: what an end user must do, own, run, or receive in order to participate
or be paid.

On 2026-08-07 the owner supplied the four outstanding founder decisions and
revised the economy. ADR 0023 records them: the maximum supply is now
56,993,950,100 display units, the Founder referral doubled to 34.2 units per
cycle and moved to the direct-mint channels as an unconditional benefit,
unreferred seats fund a monthly performance pool, a cycle is met at 18 hours of
fully operational uptime with a 6-hour fragmentable grace allowance, and a
failed cycle's 342 units go to the highest uptime that cycle.

**The accepted M2 models are therefore superseded as founder direction.** They
implement `founder-economy-manifest-v1` and remain exactly as verified; the
constitution now specifies a v2 that only the new economy model implements. The
seat, routing, escrow, and scenario-suite models still bind v1. Nothing about
what runs today changed, because none of it activates anything.

### How M3.5 was delivered

Issue #119 and PR #120 delivered `uptime-measurement-v1` at merged commit
`646cfb5`. It added the specification, ADR 0028, the model in
`simulation/uptime_measurement/`, 114 normative vectors, a verifier in
`tools/uptime-measurement-vectors/`, and 90 tests. It satisfies requirement 7 of
`first-goal.md` and the per-cycle uptime-record part of requirement 12.

**Credit is per slot, and a slot is one hour.** A window is 24 slots of 1,200
blocks, so the constitution's own 24-hour, 18-hour, and 6-hour figures are whole
slots and the rule is applied in the units it was written in. Crediting partial
slots was rejected: it needs evidence at a granularity the chain cannot supply
for a node holding no validator duty in the period, so it would interpolate
between two probes and credit blocks no evidence covers, and the constitution
states there is no partial-credit mode. The coarseness is paid for by the
founder-directed allowance, which is six whole slots.

**The record's shape did not change, which is what the slice order was for.**
`uptime_seconds = credited_slots * 3,600` lands exactly on the units
`founder-economy-simulator-v2` already validates, and whole hours are a strict
subset of the `0..86,400` range it checks. Had the economy model been rebound to
the cycle boundary first and the measurement then denominated in blocks, the
record's shape would have changed twice and two economy contract versions would
have been spent where one does. A cross-model test runs the accepted economy
model on a record this pipeline emits, reaching none of its three uptime-record
failures.

**A seat is credited for the duties it was assigned, not for signing.** The
constitution requires validator capability of every eligible node while stating
that this does not require all 100,000 machines to vote on every block and that
the protocol must select and rotate a bounded live signing set. Crediting only
seats that signed would fail every unselected seat in every slot and reallocate
essentially the whole population's Founder portion to that small set, which is
not a strict reading of the constitution but a contradiction of the sentence
bounding the signing set. An empty assignment is satisfied vacuously.

**Challenge selection is derived per height from a beacon nobody can predict.**
The beacon is the canonical state root at `height - 1`, so a seat learns of its
audit at most one block — three seconds — before it must answer and cannot
schedule uptime around it. `CHALLENGE_PERIOD_BLOCKS` equals `SLOT_BLOCKS`, so a
seat expects exactly one probe per credited unit: the sampling rate is one probe
per slot, which fixes the load at about 83 responses per block at full capacity
and adds nothing to an ordinary transaction. Selection excludes the final 20
heights of a slot, so a challenge and its 60-second deadline always lie inside
one slot, which is what makes the per-slot state disposable at the boundary.

**The dispute may only subtract, and only up to the grace allowance.** There is
no transition by which a dispute adds credit, so a captured Ecosystem AI key can
reduce a result and never manufacture one: it cannot mint, cannot direct value,
and cannot make a failed node appear to have met a cycle. The cap is 6 slots per
seat per window, and `24 - 6 = 18` is exactly the threshold, so **a seat credited
for every slot still meets its cycle after a maximal dispute.** The AI can
consume an operator's entire allowance and cannot by itself fail a fully
operational node. That is the constitution's own containment argument applied in
the second direction: it refuses to make the AI's signature a precondition for
payment because a company able to freeze income would own the reward path, and an
unbounded void power restores exactly that ownership through a different door.
The model asserts the theorem after every dispute rather than trusting the cap
arithmetic, and refuses a cap that would break it.

**Silence finalises after one window.** A window's dispute period is the whole of
the following window, and the result is final at the start of the window after
that regardless of AI availability. Reusing the existing grid makes finalisation
a window comparison rather than a second period, and delays a seat's exercise of
a cycle by at most two windows.

**Completeness is derived, not validated.** A record's seat set is every seat
activated strictly before the window's first height, derived from the bound
cycle-boundary activation table, so an omission is unrepresentable rather than
detected. This closes the gap `founder-economy-simulator-v2` and ADR 0027 both
record. The tests demonstrate it rather than describe it: the economy model
accepts a truncated record, and this pipeline has no way to emit one.

**Nothing is bound to this yet.** `simulation/founder_economy_v2/` and
`simulation/cycle_boundary/` are untouched. No v1 or v2 artifact, C++, consensus,
or devnet behavior changed.

### How M3.4 was delivered

Issue #114 and PR #115 delivered `cycle-boundary-v1` at merged commit `7dd6a84`.
It added the specification, ADR 0027, the model in `simulation/cycle_boundary/`,
101 normative vectors, a verifier in `tools/cycle-boundary-vectors/`, and 57
tests. It satisfies requirement 4 of `first-goal.md`.

A cycle is 28,800 block heights on one global grid. Window `w` is the inclusive
height span `[w * 28,800, w * 28,800 + 28,799]`, and a seat's 731 cycles are the
731 consecutive windows beginning with the first window that starts after its
activation height.

**The grid is shared, and that is the load-bearing decision.** Performance
reallocation sends a failed cycle's 342-unit Founder portion to the highest
uptime "in that same cycle", so a cycle must name a period several seats can be
compared over. With per-seat windows anchored at each seat's own activation, two
seats share a window only when their activation heights are congruent modulo
28,800, so essentially every reallocation would rank a population of one — the
failed seat, which cannot win. The winner set would be empty and the whole
portion would carry forward indefinitely, which is not a conservative reading of
the founder rule but the rule not running. The vectors record this as a derived
property rather than a claim: seats activated at genesis and at the last height
of the same window hold identical spans, and one block later shifts the span by
exactly one window.

**28,800 was chosen for exactness, not convenience.** The pinned M1
`timeout_commit = "3s"` divides all three founder-directed durations without
remainder, so 18 hours is exactly 21,600 blocks and the fragmentable 6-hour
allowance exactly 7,200. A grid leaving a remainder would put a founder-directed
threshold between two blocks, appliable only by rounding it toward the operator
or against them, which is a change to a founder-directed value that the standing
delegation does not authorize. The model computes each quotient and requires a
zero remainder rather than trusting the arithmetic to have worked out.

**A seat begins at the next full window.** Counting the activating window would
give a seat activated one block before a boundary a first cycle of one block, in
which the 18-hour threshold is unreachable; it would fail a cycle it was never
able to meet and have that cycle's Founder portion reallocated to other seats
purely because of where in a window its activation was included. The cost is at
most one window of delay, and the constitution fixes how many cycles a seat
receives rather than the height at which the first opens.

**The drift between a window and a day is stated rather than smoothed over.**
28,800 blocks is 24 hours only at exactly 3 seconds a block, so a slow chain
stretches a window in real time and a node up throughout it would accumulate more
wall-clock uptime than `founder-economy-simulator-v2` accepts in a record. The
grid is not what changes: a window's nominal duration is 86,400 seconds and a
measurement is a statement about a window rather than about a clock, so
`uptime_seconds = uptime_blocks * 3` for `0 <= uptime_blocks <= 28,800`, exact
because the divisions are exact. Widening the economy model's containment bound
to admit wall-clock seconds was rejected: it would let a slow chain inflate every
node's measured uptime against a fixed threshold.

Activation heights may not decrease, because a real activation executes inside
the block that includes it, so a replayed or reordered activation cannot install
a schedule in the past and claim windows the seat did not hold. Equal heights are
accepted, since one block may activate several seats.

**Nothing is bound to this yet.** Applying the check inside
`evaluate_base_permission` adds a rejection condition and requires the seat
record to carry an activation height, which under the rule ADR 0024 and ADR 0026
established is a new economy contract version rather than an edit.
`simulation/founder_economy_v2/` is untouched and its recorded gap stays
recorded. No v1 or v2 artifact, C++, consensus, or devnet behavior changed.

### How M3.3 was delivered

Issue #108 and PR #109 delivered `escrow-payout-v2` at merged commit `a8ea180`,
and issue #110 and PR #111 delivered `economy-scenario-suite-v2` at merged commit
`04cdd23`. Together they satisfy requirement 3 of `first-goal.md`: all four
dependent models are re-verified against version two, every recorded digest is
regenerated, and both verifiers still fail closed in both directions.

The slice was split because the suite binds the escrow model, so rebinding the
suite depends on the escrow model already having a v2 binding.

**Rebinding is a new version, not an edit, and the repository decided that rather
than the session.** `escrow-payout-v1.md` fixes its research-input shapes and
digest labels as immutable and requires a new schema and ADR to change them, and
`economy-scenario-suite-v1.md` already recorded that its scenario parameters were
superseded and that a version two suite would derive them. ADR 0026 records both
halves.

Escrow payout differs in exactly six strings: the five domain labels it writes
and the one founder-economy state label it reads. Every transition, rejection
condition, rejection order, journal bucket, and invariant is identical, so the
two versions share one implementation selected by a `Binding` record. A duplicate
package was rejected — `founder_economy_v2` earned one because its transition set
changed shape, while two copies of a thousand lines of identical payout logic
would have nothing to notice drift.

The escrow v2 fixture is the v1 scenario with only its four embedded economy
states rebound. Holding the scenario fixed is what makes the rebinding auditable:
the two runs produce identical result codes for all 39 events in identical order,
and their final states differ in exactly one member, `bound_state_digest`. That
equivalence is asserted, because a rebinding defect that altered a payout rule
would still produce a self-consistent vector file.

The opening custody is unchanged at 34,200,000,000 / 6,840,000,000 /
3,420,000,000 atomic units. The escrow legs are unrevised and both fixtures accept
two base permissions, so the amounts coincide while the state they come from does
not. Both facts are recorded rather than one being assumed.

**The suite's scenario 1 changed shape.** Version one supplied the activity
verdict and the performance recipient because the constitution had not decided
them; both are now decided, so the generator supplies measurements and the model
derives the answers. The tick is the shared `cycle_window`: three seats staggered
61 ticks apart hold different cycle indices at the same tick, and reallocation to
"the highest uptime in that same cycle" is only meaningful against a shared
window. Reusing `cycle_index` would have put exactly one seat in every window, so
no reallocation would ever have had a candidate.

The intended winner is given the only maximal uptime and the model derives the
winner set. Every other seat sits exactly on the 64,800-second threshold, so the
founder-directed boundary is exercised in every reallocating window rather than
only in a unit test. At most one seat may fail per window, which the generator
asserts rather than assumes: two would make the winner set depend on evaluation
order. A fourth seat is activated and never evaluates, because all three
population seats consume their whole 731-cycle windows and the three uptime
probes need an unevaluated key to reach `MISSING_UPTIME_RECORD`,
`INVALID_UPTIME_RECORD`, and `INCONSISTENT_UPTIME_RECORD` in order.

Scenarios 2 and 3 are proved version-independent rather than asserted to be: the
19 seat and 26 routing vectors are byte-identical in both vector files.

No v1 artifact, C++, consensus, or devnet behavior changed.
`simulation/founder_economy/` is untouched, and `escrow-payout-v1.txt`, its
fixture, and `economy-scenario-suite-v1.txt` are byte-for-byte unchanged and
still pass.

### How M3.2 was delivered

Issue #103 and PR #104 delivered `founder-economy-simulator-v2` at merged commit
`a0521d0`. It added the specification, ADR 0025, the executable model in
`simulation/founder_economy_v2/`, a research scenario fixture, 189 normative
vectors, and a second verifier entry point in `tools/founder-economy-v2-vectors/`.

The transition set changed shape, not only parameters. The referral left the
permission system entirely: `accrue_referral` is unconditional, direct-mint, and
keyed by `(referred_seat_id, cycle_index)`, with no activity and no eligibility
input. An unreferred seat credits `unreferred_performance_pool:global` rather
than being rejected, which is what consumes the channel exactly at capacity, so
`SEAT_NOT_REFERRED` is gone. The permission `kind` discriminator went with the
referral, and `INVALID_PERFORMANCE_ALLOCATION` went with the supplied allocation
list it validated.

`evaluate_base_permission` now derives the activity verdict and the winner set
from a cycle uptime record instead of reading two supplied fixtures.

**The record carries measurements only.** It cannot express a verdict, an
eligibility flag, a winner, a ranking, or an amount, and tests assert that a
record carrying an `active` flag or a `winners` list fails to parse. This is the
distinction the slice existed to preserve: a research placeholder stands in for
an undecided founder policy, while the record stands in for a rule ADR 0023 and
the Founder Constitution already decide but whose measurement pipeline is
unbuilt. `MISSING_UPTIME_RECORD`, `INVALID_UPTIME_RECORD`, and
`INCONSISTENT_UPTIME_RECORD` are deliberately distinct from the research codes so
a trace can tell a missing measurement from a missing founder decision.

A `cycle_window` is separate from a seat's `cycle_index`. A seat's 731 cycles
begin at its own first activation, so two seats' cycle 7 are different windows
and reallocation to "the highest uptime in that same cycle" is only meaningful
against a shared one. The model cannot verify that a supplied window is the
correct window for a seat's cycle — that is the deferred cycle-boundary rule — so
the separate field keeps the gap visible in every event rather than hiding it in
a coincidence of names.

The carry needed care. Carried value is unreserved channel capacity, not a fourth
ledger dimension, so folding it into the journal's channel balance would
double-count it and no accepted journal would balance. It is pinned by its own
identity instead, per event in the engine and cumulatively in the state
invariants:

```text
issued(founder_operator) + outstanding(founder_operator) + performance_carry
  = count(evaluated_permission_keys) * 34,200,000,000
 <= cap(founder_operator)
```

asserted as an equality rather than a bound, because a bound would admit a defect
that lost carried value.

`founder_referral` is rejected by `direct_issue`. That is containment rather than
tidiness: admitting it would let a supplied eligibility fixture mint referral
units outside the per-seat-cycle accounting and place a founder-decided channel
under an undecided placeholder.

No v1 artifact, C++, consensus, or devnet behavior changed.

### How M3.1 was delivered

Issue #99 and PR #100 accepted `founder-economy-manifest-v2` at merged commit
`0c05b52`. It added the specification, ADR 0024, the manifest JSON and its
digest, 154 normative vectors, a strict loader in `simulation/founder_economy_v2/`,
and a verifier in `tools/founder-economy-v2-vectors/`.

The contract fixes the 56,993,950,100 display maximum as
5,699,395,010,000,000,000 atomic under the unchanged eight-decimal
denomination, and the referral at 34,200,000,000 atomic per cycle as an
unconditional direct-mint channel capped at 250,002,000,000,000,000. The other
nine channel caps, the seat capacity, the per-person bound, the 731-cycle
schedule, and every base-permission leg are unchanged.

Version one was not edited. Its digest names the exact byte string the M2
evidence was verified against, and the two contracts differ in shape rather
than only in parameters: v2 has no `referral_permission` issuance kind, no
`referral_permission` object, and no permission `kind` discriminator. Each
loader rejects the other's manifest, the domain labels differ, and tests assert
both directions. ADR 0024 records that reasoning and four other structural
decisions.

No simulator, C++, consensus, devnet, or previously accepted v1 artifact
changed. v2 has no executable model and activates nothing.

### How M2 was delivered

Issue #71 and PR #72 adopted the first exact contract at merged commit
`14486cb`: an eight-decimal `u64` denomination, all ten fixed issuance-channel caps, the
731-cycle supply derivation, permission liabilities, research-only eligibility
placeholders, ADR 0017, and normative vectors.

Issue #77 then made that contract executable and is merged at `9aeac23`. It
added `founder-economy-simulator-v1`, ADR 0018, the independent
`simulation/founder_economy/` model, a second normative vector file, and a
verifier that derives every recorded value from the loaded manifest and live
runs.

Issue #79 delivered the Founder Seat sale model satisfying `goals/m2-founder-economy-proof.md`
requirement 8 and is merged at `c03262f`.

Issue #82 delivered commercial revenue and transaction-fee routing satisfying
`goals/m2-founder-economy-proof.md` requirements 9 and 10 and is merged at `5029c00`. It added
`revenue-routing-v1`, ADR 0020, the independent `simulation/revenue_routing/`
model, a third normative vector file, and a verifier whose `walk.py` is a
second implementation the recorded file and the model must both agree with.

Issue #85 delivered escrow payout capabilities satisfying `goals/m2-founder-economy-proof.md`
requirement 11. It added `escrow-payout-v1`, ADR 0021, the independent
`simulation/escrow_payout/` model, a fourth normative vector file, and a
verifier that both replays the scenario against an independent walk and proves
the fixture's opening custody is bound to a live `founder-economy-simulator-v1`
run.

Issue #88 delivered the multi-year and adversarial scenario suite satisfying
`goals/m2-founder-economy-proof.md` requirement 13. It added `economy-scenario-suite-v1`, ADR 0022,
the deterministic generators in `simulation/scenarios/`, a fifth normative
vector file, and a verifier whose independence is closed-form derivation from
Founder Constitution literals rather than a fifth walk. It added no model,
transition, event kind, or canonical label.

Issue #91 delivered `founder-economy-report-v1.md`, satisfying `goals/m2-founder-economy-proof.md`
requirement 14, and this handoff satisfies requirement 16. No C++, consensus,
devnet, or previously accepted simulator behavior changed in any of these
slices.

## What works now

- The completed M1 C++20 ledger processes canonical signed native transfers,
  exact nonces, and fixed fees while rejecting malformed, replayed,
  unauthorized, overflowing, and insufficient-balance transactions.
- SQLite persistence, atomic commit, restart, deterministic state roots, a
  stateless Go ABCI adapter, and pinned CometBFT operate as a reproducible
  four-validator local devnet.
- Independent Python differential testing covers at least 10,000 seeded
  sequences; GCC, Clang, sanitizer, bounded fuzz, single-node, and
  four-validator hosted verification passed on the last merged executable
  state.
- Accepted M2 research models cover native custody, escrow, claims,
  participation, bounded authority, economic stress, concentration,
  identity-split incentives, and minimum entitlements. Their schemas and
  results remain research evidence, not production Founder economics.
- The accepted `founder-economy-manifest-v2` contract represents the
  56,993,950,100-unit maximum as 5,699,395,010,000,000,000 eight-decimal atomic
  units, fixes a canonical ten-channel manifest at 2,267 JCS bytes with digest
  `84cca09865b6c62bf09d3f6bc3821a2527c7a4835652cffdc0ebefa34b314ce5`, and puts
  the referral in the direct-mint group at 250,002,000,000,000,000 atomic. Its
  strict loader enforces the eight ordered failure codes and rederives every
  product and subtotal.
- The `founder-economy-simulator-v2` model executes that contract. It runs seat
  activation, base permission evaluation, unconditional referral accrual, atomic
  exercise, and capped direct issuance with deterministic trace, state, and
  result digests. A cycle is met at 64,800 seconds of cumulative fully
  operational uptime, checked in both of the constitution's stated forms; the
  failed-cycle winner set is the highest uptime among seats that met the same
  window, split equally with the remainder carried; an empty winner set carries
  the whole portion. A window's record is bound by digest on first reference, so
  the window's uptime is one fact for a run rather than a per-event opinion. It
  is research software and activates nothing.
- A complete 731-cycle single-seat run reproduces the v2 per-seat schedule
  exactly, including 25,000,200,000,000 Founder-operator, 12,500,100,000,000
  venture-escrow, and 2,500,020,000,000 unreferred-pool atomic units.
- The accepted Founder Economy manifest exactly represents the
  55,743,940,100-unit maximum as 5,574,394,010,000,000,000 eight-decimal atomic
  units, fixes a canonical ten-channel manifest and digest, and proves every
  per-cycle, per-seat, and complete-population supply product without
  activating it. That maximum is the superseded v1 figure; the constitution now
  directs 56,993,950,100.
- The independent Founder Economy simulator executes that contract. It loads
  the manifest under the ordered failure codes, tracks per-channel issued and
  outstanding amounts with checked `u64` arithmetic, and runs seat activation,
  base and referral permission evaluation, atomic exercise, and capped
  direct-channel issuance with deterministic trace, state, and result digests.
  It is research software and activates nothing. Its referral transition is
  superseded: a referral is now unconditional and direct-mint.
- The Founder Seat sale model derives the complete constitutional price
  schedule and runs the full 100,000-seat sale end to end to exactly USD
  4,231,855,000, enforcing the 100,000-seat capacity and the 1,000-seat
  per-principal bound at their boundaries. It models the sale only; a purchased
  seat is not yet an activated seat.
- The revenue routing model splits a native commercial payment 45/45/10, halves
  the creator share for the 22.5/22.5 product-creator case, routes the floored
  shares' remainder to the Founder pool under a bound proved by exhaustive scan
  of all 200 residues, routes 100% of a transaction fee to a separate Founder
  fee pool, and distributes both pools per accounting cycle over a bound
  active-seat snapshot while carrying each residue forward. It creates no
  native units and routes value a constitutional channel already issued.
- The escrow payout model holds the three founder-directed escrows separately,
  takes opening custody from a recorded `founder-economy-simulator-v1` state by
  recomputing that model's digest, and releases value only through a capability
  bound to exactly one escrow and bounded by a per-payout maximum, a cumulative
  envelope, an expiry, and revocation. Each escrow conserves independently, and
  a second capability-side account of the same value must agree. It creates no
  native units: custody is fixed at the bind and non-increasing afterwards.
- The scenario suite runs those four models at multi-year scale. Three seats
  staggered 61 ticks apart each complete all 731 cycles with disjoint inactive
  cycles and performance reallocation; exactly 100 principals at the 1,000-seat
  bound absorb the whole 100,000-seat capacity; 122 routing cycles change their
  active population every cycle, 25 of them empty; and every escrow is drained
  and every envelope exhausted against custody the population run itself issued.
  Restart equivalence holds under prefix replay and split resume, and seeded
  property tests assert each model's conservation equations against its
  published results rather than its recorded totals.
- The escrow payout model implements two accepted contracts. `escrow-payout-v2`
  binds `founder-economy-simulator-v2` and differs from version one in exactly
  six strings; a state recorded under either economy version is rejected by the
  other's bind with `INVALID_RESEARCH_INPUT`, derived in the vectors rather than
  asserted. Both versions' transitions are identical, which the two runs' equal
  trace codes prove.
- The scenario suite runs under either binding. `economy-scenario-suite-v2`
  reruns all four scenarios against the revised economy: a complete 731-cycle
  staggered population run with derived activity and derived performance
  winners, the 100,000-seat concentrated sale, 122 routing cycles, and an escrow
  drain bound to the v2 population run's own state digest. The referral channel
  is consumed exactly by its two destinations — 5,000,040,000,000 atomic units of
  referrer custody plus a 2,500,020,000,000 unreferred pool equal its whole
  issuance — and the performance carry ends at zero.
- The cycle boundary model holds a seat activation table and answers whether a
  supplied window is the window for a supplied cycle index. A cycle is 28,800
  block heights on one global grid shared by every seat, a seat's 731 cycles are
  the 731 consecutive windows beginning after its activation height, activation
  heights may not decrease, and a wrong window yields three distinct codes for
  before the span, after it, and inside it but attached to another cycle. It
  derives no measurement and no economy model is bound to it yet.
- The uptime measurement model turns evidence into a finalised record. It
  subdivides a window into 24 one-hour slots, credits a slot only when every
  assigned duty in it was performed and every challenge issued in it was answered
  correctly and on time, selects challenges from a beacon no participant can
  compute before the block commits, applies bounded Ecosystem AI disputes that
  can only subtract, finalises by expiry without any signature, and emits the
  `cycle_uptime_record` shape `founder-economy-simulator-v2` accepts unchanged. It
  observes no real machine: the challenge protocol is defined and the challenge
  content is not.
- The escrow payout model implements three accepted contracts. `escrow-payout-v3`
  binds `founder-economy-simulator-v3` and differs from version two in exactly six
  strings; a state recorded under any one economy version is rejected by both
  other binds, derived in the vectors against each predecessor separately rather
  than asserted. All eighteen strings across the three bindings are distinct.
- The `founder-economy-simulator-v3` model enforces what the two preceding slices
  only defined. A seat records the activation height its 731-window schedule is
  derived from; a base permission is rejected when its `cycle_window` is not the
  window the accepted grid assigns to its `cycle_index`, with the three codes
  `cycle-boundary-v1` distinguishes; and an uptime record is rejected when its
  seat set is not exactly the window's in-scope set, in either direction. It
  reuses the accepted v2 manifest and the accepted window grid rather than
  holding a copy of either, and refuses to run at all if they have drifted. It is
  research software and activates nothing.
- The scenario suite runs under all three bindings. `economy-scenario-suite-v3`
  reruns every scenario against the enforced schedule: each seat carries the
  activation height its 731 windows are derived from, every record covers exactly
  its window's in-scope set, and one early window reaches the founder-directed
  empty-winner rule with a complete population rather than in a unit test. The
  performance carry survives that window and still ends at zero. Scenarios 2 and
  3 record byte-identical values under all three versions.
- Every simulation test, every executable vector verifier, every recorded vector
  file, and every `tests/tools` module is reachable from a registered `ctest`
  entry, and every simulation test runs the way `ctest` invokes it.
  `tests/tools/test_registration_test.py` enforces all of that, and it is now
  registered itself, so it runs on both verification paths rather than only the
  lightweight one. Until 2026-08-12 it ran only when the scope classified
  `lightweight`, which excluded every pull request able to add an unregistered
  entry.
- The hosted test phase runs concurrently at `nproc` jobs, and no two registered
  entries are handed the same path under the build directory, which is checked
  statically rather than left to an intermittent race.
  `PROTOCOL_STACK_TEST_JOBS=1` restores serial execution.
- `economy-transition-v2` is the accepted consensus surface the economy must be
  implemented against. It fixes a shared transaction envelope whose kind-1
  instance reproduces the accepted M1 transfer byte-for-byte; five new kinds —
  purchase, activate, mint node, mint referral, and direct issue; the biometric
  verifier signature that gates entry and never payment; the per-cycle assignment
  the chain writes at a block boundary; the economy state key space; version-two
  genesis and chain identity; the state-root extension; a 56-byte receipt; and a
  flat 21-code result space whose first nine are version one's frozen meanings.
  It is a contract for an implementation that does not exist: no C++ executes it.
  Kind 6 is specified and refused, because direct-channel eligibility is the one
  authorization predicate still founder-reserved.
- The codec model in `simulation/economy_transition/` encodes and decodes every
  kind, derives every state key, computes the economy tree and both state roots,
  encodes the receipt, derives a cycle's winner set, and splits every leg of a
  failed cycle's permission. It implements no cryptographic primitive: a
  signature is carried as recorded bytes and never computed. Its verifier derives
  the version-one transfer twice from two different shapes and checks both
  against the accepted `protocol-primitives-v1` vectors.
- `economy-transition-v3` is the accepted consensus surface the C++ kernel must
  be implemented against, and it supersedes version two as the implementation
  target. It adds four transaction kinds — a biometrically approved mint, the
  per-seat protection switch, manager addition, and HUB verification — three
  state entry kinds, three result codes, and six domain-separated verifier
  messages. Any recorded manager may act for a seat and receives what it mints; a
  seat may require a fresh biometric approval to mint, and removing that
  requirement itself needs one; unminted permissions are capped at thirty windows
  and the excess reallocates to the cycle's best performers by the same path a
  failed cycle takes; and a named referrer must hold a HUB registration. The
  kind-1 byte identity, the shared envelope, the admission order, the genesis
  field table, the receipt layout, and result codes 0 through 20 are unchanged.
  Kind 6 is still specified and refused.
- `economy-transition-v6` is the accepted consensus surface the C++ kernel must
  be implemented against. A verified identity is the root of every account, a
  keyless escrow is where value sits, and a revocable signer assigned to exactly
  one escrow is who may act on it; an escrow's balance and nonce stay in the
  version-one account map, so a version-six state is a version-one state plus an
  economy map. Registration is fee-exempt and creates the identity, escrow zero,
  the first signer, and the entry airdrop in one atomic execution. A Founder Seat
  has no address and a mint names a destination escrow the chain checks. A
  transfer refuses an unregistered recipient, which withdraws
  `ledger-transition-v1`'s recipient-creating transfer and makes **every account
  is an escrow** a structural invariant. The signature-scheme byte carries a
  second authorization mode so that identity administration works with no key at
  all, and admission still verifies a signature without reading state. It has a
  model, 462 vectors, a verifier, and 91 tests; **what it does not yet have is
  the C++ implementation**, which still targets version four.
- **`economy-transition-v6` also executes, in Python.** The same package now
  holds a version-six ledger state, escrow resolution under both authorization
  schemes, the shared envelope checks, the fourteen transitions in their
  specified rejection orders, and ordered block execution that writes a cycle
  assignment at a window boundary, charges the fixed fee, advances the escrow's
  nonce, produces one 56-byte receipt per admitted transaction, and commits a
  state root, a transaction root, a 146-byte header, and a block ID. A recorded
  six-scenario trace walks registration and its entry airdrop, a forfeiting
  verified-user collection thirty windows later, the millionth-and-first user,
  recovery with no signer at all, the accepted version-one transfer admitted and
  refused for its recipient, both directions of a posture change, and a mint that
  collects the cycle the block it is in just assigned.
  `test-vectors/economy-transition-v6-execution.txt` fixes 512 vectors over it
  and five mutation probes establish that the verifier fails closed. It is still
  Python that activates nothing; what changed is that the evidence is now about
  transitions rather than about bytes.
- `economy-transition-v5` is accepted, fully evidenced, and superseded as
  direction hours after it was evidenced. It is version four with one field's
  meaning corrected — kind 11's 32-byte field is the HUB identity hash and the
  account being linked is the sender — because version four's kind 11 names an
  identity it does not carry and therefore cannot be implemented. Its model, 550
  vectors, and verifier remain in place and passing. No C++ was ever written
  against it, which is the precedent working rather than failing.
- `economy-transition-v4` is accepted, fully evidenced, and superseded in one
  place. HUB verification is the root of identity: a
  registration records the person's own public key and the ecosystem verifier
  signs registrations and nothing else; a person holds a set of up to 16
  addresses and manages it themselves; a seat is owned by a person rather than
  an address, so losing every address does not lose the seat; HUB signing is
  what adds a seat address, and seat addresses stay permanent and add-only;
  referral earnings are keyed by identity; self-referral is compared between
  people; and the constitution's 1,000-seat-per-human bound is enforced. The
  kind-1 byte identity, the shared envelope, the admission order, the genesis
  field table, the receipt layout, result codes 0 through 23, and the whole
  settlement carry over. Kind 6 is still specified and refused.
- **The C++20 kernel implements the version-four codec**, and it is the first
  consensus-language artifact in the milestone. `protocol::v4` encodes and
  decodes all twelve transaction kinds, builds all eight HUB messages, derives
  every state key and value, computes the economy tree and the version-four
  state root, encodes genesis and derives the chain identifier, and encodes and
  decodes the receipt. It reproduces `test-vectors/economy-transition-v4.txt`
  and, for the kind-1 identity and the accounts tree, the accepted M1 file. It
  runs no transition and reads no ledger.
- The model in `simulation/economy_transition_v4/` encodes and decodes all
  twelve kinds, builds all eight HUB messages, derives every state key, computes
  the economy tree and all four versions' state roots, encodes the receipt, and
  runs the HUB registry with its two counts. It imports version three's
  settlement rather than copying it, and the vectors require the record it
  writes to equal version three's recorded bytes exactly.
- The codec-and-settlement model in `simulation/economy_transition_v3/` encodes
  and decodes all ten kinds, builds all six verifier messages, derives every
  state key, computes the economy tree and all three versions' state roots,
  encodes the receipt, derives a cycle's assignment under the cap, and walks a
  bounded mint. It implements no cryptographic primitive. Its verifier derives
  every value twice — structurally for the compatibility claim and behaviourally
  for the settlement — and fails closed on a tampered value, a missing key, and
  an invented key alike.
- The one-word `proceed`, `conclude`, and `status` workflows reconstruct,
  deliver, and report repository state. `proceed` runs an explicit
  founder-decision gate before starting a slice and reports its result whether or
  not anything is reserved.

## Adopted founder direction

- One native asset with an intended fixed maximum of 56,993,950,100 display
  units and no burn, secondary internal currency, or public asset creation. The
  maximum was raised from 55,743,940,100 on 2026-08-07, before any issuance, to
  fund the doubled referral channel; it becomes immutable at genesis.
- Exactly 100,000 permanent biometric Founder Seats, all-in-one Founder Nodes,
  731-cycle issuance, fixed allocation channels, 45/45/10 commercial routing,
  and 100% Founder transaction-fee routing.
- A cycle is met at 18 hours or more of cumulative fully operational uptime,
  where fully operational means every node component healthy at once. The
  6-hour grace allowance is cumulative and fragmentable.
- A failed cycle's whole 574.3-unit permission goes to the highest cumulative
  uptime in that same cycle, shared equally among exact ties, restricted to
  seats that met the cycle, with the integer remainder carried forward per
  channel. It settles at the winner's mint rather than at a mint the failed seat
  may never make, which is the 2026-08-13 revision of the constitution's original
  "when the failed seat next exercises a permission".
- The Founder referral benefit is 34.2 units per cycle, unconditional, and a
  direct-mint channel capped at 2,500,020,000. A seat bought without a recorded
  referrer routes its allocation to a monthly unreferred performance pool, so
  the channel is consumed exactly. A referrer must be HUB verified.
- A seat is controlled by a recorded set of at most 16 manager addresses rather
  than by one purchase address, a mint credits the address that signed it, and
  minted value is spendable immediately with no withdrawal step. A founder may
  require a fresh biometric approval on every mint; switching that on needs only
  an address signature and switching it off needs a biometric approval. A seat's
  addresses are permanent and add-only, and **HUB signing is what adds one**, so
  a founder who has lost every key still has a path back.
- Unminted permissions accumulate for at most thirty cycles after the last
  collection. Past that, **a cycle a seat cannot collect is a cycle it failed**:
  the day's generation goes to the best performers, and the full seat is not one
  of them, because a failed seat never rewards another failed seat. What the seat
  has already earned is untouched, and one collection restores both the room and
  the eligibility. The same bound applies to a referrer's accrual, whose
  forfeited value routes to the unreferred pool. It is a collect-or-lose rule
  rather than a penalty: an unminted permission's units do not exist and are not
  circulating.
- **HUB verification is the ecosystem's recovery layer as well as its identity
  layer.** It survives the loss of any address, so a registered person can always
  sign back in, and a verified person may add and remove their own addresses
  through it. Founder Seat addresses are the stated exception: add-only, never
  removed.
- Buying a Founder Seat requires HUB verification first, and the seat is tied to
  that identity. One human may hold at most 1,000 seats, which the chain now
  enforces because it can finally tell that two addresses are one person.
- Uptime reaches consensus without trusting self-reports: validator duties are
  derived on-chain, resource provision is proved by challenge-response, and the
  Ecosystem AI holds a bounded dispute window rather than a signature that
  could freeze payment.
- One company-hosted logical Ecosystem AI outside consensus and outside
  Founder Nodes, with separately bounded biometric, moderation, project,
  treasury, and developer-program capabilities.
- AI-approved controlled full-stack applications, one project creator plus at
  most one product creator, immutable accepted history, and Founder-only
  resource infrastructure.
- BTC, ETH, and approved stablecoins restricted to Founder Seat purchase,
  liquidity, native swaps, and withdrawal; they never become general internal
  balances.

These are target requirements, not runnable Founder behavior. Issue #71 added a
specification, JSON manifest, and fixed vectors; issues #77, #79, #82, and #85
each added a specification, ADR, Python model, vectors, and verifier for part of
them; issue #88 added a specification, ADR, deterministic generators, vectors,
and verifier that exercise all four at multi-year scale. Issue #99 restated the
contract under the revised direction and issue #103 made that restatement
executable. None changed current transaction bytes, C++ state, devnet supply,
previously accepted simulator schemas, bridge, wallet, AI, biometric, or resource
behavior.

## Repository state

- Repository: `kaikisegfault/protocol-stack`.
- Issue #153 and PR #173 are the M3.10b delivery, merged by rebase across
  commits `19107df` through `cc2e8fc` on `main`. It adds the version-six
  execution model, 512 vectors, a verifier, ADR 0045, and two test modules, and
  edits no accepted artifact. PR run 31952597793 on the final head `66fcab8`
  passed the complete hosted matrix — scope classification `full`, GCC and Clang
  debug, both sanitizers, and the aggregate required check — and post-merge run
  31953123699 on `cc2e8fc` passed the same matrix.
- **The margin is about ten and a half minutes, and the slice moved it very
  little.** Per-job durations on the candidate against the 20-minute per-job
  timeout: `gcc-debug` 5m48s, `clang-sanitizers` 7m21s, `clang-debug` 8m45s,
  `gcc-sanitizers` 9m21s. Post-merge on `main`: `clang-debug` 8m15s, `gcc-debug`
  8m17s, `clang-sanitizers` 8m50s, `gcc-sanitizers` 9m20s. The slice adds no
  translation unit and two fast Python entries that `ctest --parallel` absorbs,
  so the spread sits inside the roughly 12% run-to-run variance M3.7a measured
  on identical code. **M3.10c is the one to watch**: it is C++, and build time is
  the larger half of each job.
- Issue #153's scope has been rebound twice. It was opened as M3.9b against
  version four, renumbered M3.9e and rebound to version five when version four's
  kind-11 defect pushed three slices in front of it, and finally rebound to
  version six after the pivot of 2026-08-15. It closed as M3.10b, and its
  recorded requirement that the trace walk the recovery path is satisfied by the
  `recovery` scenario.
- Issue #169 and PR #170 are the M3.10a delivery, merged by rebase across
  commits `6fb57f6` through `15b5e90` on `main`, with PR #171 closing out the
  handoff at `07afe4c`. The complete hosted matrix passed on the exact candidate
  — `gcc-debug` 8m33s, `clang-debug` 8m57s, `clang-sanitizers` 9m02s,
  `gcc-sanitizers` 9m27s — and again post-merge in 9m48s.
- Issue #154 and PR #155 are the M3.9b delivery, merged by rebase at commit
  `fa1907f` on `main`. It is documentation only — a specification and an ADR —
  so it took the focused metadata path rather than the matrix: scope
  classification passed, the preset matrix was skipped as designed, and the
  aggregate required check passed. Post-merge run 31872875912 on `fa1907f`
  passed the same path.
- Issue #157 and PR #158 are the M3.9c delivery, merged by rebase across commits
  `0f93026` through `c1e9ee4` on `main`. It adds the version-five model, 550
  vectors, a verifier, four test modules, and ADR 0038, and edits no accepted
  artifact. PR run 31880586047 on the final head `13c8229` passed the complete
  hosted matrix — scope classification `full`, GCC and Clang debug, both
  sanitizers, and the aggregate required check.
- **The margin is unchanged at about eleven minutes**, which is the expected
  result and is recorded so the next slice has a baseline. Per-job durations
  against the 20-minute per-job timeout: `gcc-sanitizers` 6m15s, `clang-debug`
  8m06s, `gcc-debug` 8m16s, `clang-sanitizers` 8m51s. The slice adds no
  translation unit, and `ctest --parallel` absorbs four fast Python entries, so
  the figures sit inside the roughly 12% run-to-run variance M3.7a measured on
  identical code. **M3.9d is the one to watch**: it is C++, and build time is
  the larger half of each job.
- **Version five's evidence gap is closed and its implementation gap is now
  moot.** The C++ codec in `src/v4/` implements version four and stays there;
  M3.9d was withdrawn the same day, because the direction of 2026-08-15
  supersedes version five as the kernel's target.
- Issue #150 and PR #151 are the M3.9a delivery, merged by rebase. The slice is
  commits `f457ca2` through `ab1e036` on `main`. PR Actions run 31849896862 on
  the final head `2c8d0fa` passed the complete hosted matrix — scope
  classification `full`, GCC and Clang debug, both sanitizers, and the aggregate
  required check.
- **The margin is about eleven minutes, and the first C++ of the milestone moved
  it very little.** Per-job durations on that run against the 20-minute per-job
  timeout: `gcc-debug` 5m39s, `clang-debug` 8m13s, `gcc-sanitizers` 9m06s,
  `clang-sanitizers` 9m08s. The slice added six translation units and one test
  executable, and the slowest job is within the roughly 12% run-to-run variance
  M3.7a measured on identical code. That is the figure to watch as M3.9b adds
  the transitions, because build time is the larger half of each job and
  `ctest --parallel` does not touch it.
- Issue #148 and PR #149 were the M3.8c delivery, merged by rebase across
  commits `225c7b0` through `7d6a69f`. PR run 31846053158 on head `3b8b944` and
  post-merge run 31846841502 on `7d6a69f` both passed the complete matrix.
- Issue #144 and PR #145 were the M3.8b delivery, merged by rebase across
  commits `b04575d` through `688efd0`. PR run 31823949771 on head `a98ac85` and
  post-merge run 31825463939 on `688efd0` both passed the complete matrix.
- Issue #139 and PR #140 were the M3.8a delivery, merged by rebase across
  commits `f8d6374` through `5f66c49`. PR run 31744378969 on head `6ced9f7` and
  post-merge run 31745207592 on `5f66c49` both passed the complete matrix.
- **The C++ codec reproduces the recorded vectors on every hosted preset.** The
  `economy-transition-v4-cpp` entry runs under GCC and Clang, debug and
  sanitized, and compares against `test-vectors/economy-transition-v4.txt` and —
  for the kind-1 identity and the accounts tree — against
  `test-vectors/protocol-primitives-v1.txt`.
- The kind-1 identity is exact. The version-two encoder reproduces
  `test-vectors/protocol-primitives-v1.txt`'s recorded `unsigned_tx`,
  `signed_tx`, and `tx_id`
  (`df2372fa965e33a7e6b871ac07acc2e2a0cb29c32939808cc6d9e1893d6d0997`)
  byte-for-byte, and the header and trailer are proved to be slices of the
  accepted bytes rather than a re-encoding of them.
- The version-one state root the non-collision claim is measured against is the
  real one, not a lookalike. Self-review found that comparing a version-two root
  against a merely plausible restatement would make "the roots differ" trivially
  true and prove nothing, so the restatement is first required to reproduce the
  accepted `state.empty_tree_root`, `state.accounts_tree_root`, `state.root`,
  `tx.empty_root`, and `tx.root` exactly. All five reproduce.
- Signed transaction lengths are 200, 325, 228, 164, 160, and 265 bytes for kinds
  1 through 6. Every kind is fixed-length, no two share a length, and **the
  largest transaction in version two is 325 bytes**, because nothing a
  transaction carries scales with the seat population.
- Version-two genesis is 110 bytes of prefix — version one's 46 plus the manifest
  digest and the ecosystem verifier key — so the object bound admits 21,843
  account entries against version one's 21,844. Version two adds 64 bytes and
  loses exactly one entry, clearing the bound by two bytes. Every figure is
  derived.
- Storage bounds at the founder-directed capacity, which complete requirement
  12: 11,900,000 bytes of seats, 180 bytes of channels, 100 bytes of carries, 49
  bytes per referrer, 4,200,000 bytes of typed custody, and 25,033 bytes per
  cycle assignment. **The per-seat-cycle population is absent from the state
  entirely** — the take-everything mint rule collapses 73,100,000 would-be
  entries into 800,000 bytes of high-water marks.
- The cycle-assignment growth is the one bound that is not a constant and is the
  weakest result in the slice: 25,033 bytes per cycle at capacity, about
  9,137,045 bytes per year at the pinned three-second commit interval, never
  deleted because a seat may mint at any time. Three mitigations are named and
  refused: expiring an uncollected cycle would decide a seat's entitlement by
  inaction, pruning past every seat's mint does not help because one seat that
  never mints holds everything after its own last mint, and a run-length form of
  the ordinary all-ones day must be the record's single canonical encoding rather
  than a second one. It belongs in requirement 15's independent review as a limit
  rather than as a figure.
- The verifier records 238 vectors and fails closed three ways, each confirmed
  by execution against the unmutated run as a positive control: a tampered
  value, a derived key the file omits, and a recorded key no derivation reaches.
- The four test modules run 91 tests. The economy model's twenty-four declared
  result codes partition exactly 11 carried, 2 guards, and 11 unrepresentable,
  checked against `simulation/founder_economy_v3`'s own declared set rather than
  a copy of it.
- No accepted artifact changed. `simulation/founder_economy*/`,
  `simulation/cycle_boundary/`, `simulation/uptime_measurement/`,
  `simulation/escrow_payout/`, and `simulation/scenarios/` are untouched, and
  every previously recorded `test-vectors/` file is byte-for-byte unchanged.
- Issue #135 and PR #136 are the M3.7a delivery, merged by rebase at `79d1c0f`.
  PR Actions run 31608054054 and post-merge run 31609094115 on `79d1c0f` both
  passed the complete hosted matrix — scope classification `full`, GCC and Clang
  debug, both sanitizers, and the aggregate required check. No run on that branch
  was superseded.
- **The margin measurement, which is the point of the slice.** Per-job durations
  against the workflow's 20-minute per-job timeout. The baseline is post-merge
  run 31495429227 on `c44c320`:

  | preset | before | PR 31608054054 | post-merge 31609094115 |
  | --- | --- | --- | --- |
  | `gcc-debug` | 14m30s | 7m40s | 8m28s |
  | `clang-debug` | 15m20s | 8m50s | 8m44s |
  | `gcc-sanitizers` | 16m24s | 8m32s | 9m17s |
  | `clang-sanitizers` | 15m41s | 9m23s | 9m58s |

  The slowest job is now `clang-sanitizers` at 9m58s post-merge, so the margin is
  about 10m rather than 3m36s.
- The `gcc-sanitizers` job records `100% tests passed out of 106` with
  `Total Test time (real) = 255.08 sec` on the PR head and `286.64 sec`
  post-merge, against 105 tests and 707.57s before. The 106 entries sum to 992.0s
  and 1096.7s under 4-way contention, so both wall times are within 3-5% of their
  `max(longest entry, sum / 4)` floor of 248s and 274.2s. `scenario-v2` and
  `scenario-v3` are now 76.0s and 72.3s, having been 107.9s and 46.0s.
- **The two runs differ by about 12% on identical code**, so the margin is
  roughly ten minutes rather than a precise figure. Treat a single hosted timing
  as an estimate and re-measure after the next slice.
- M3.7a local evidence: `scenario_v2_test.py` falls from 70.3s to 32.0s and
  gains two tests, 31 to 33. The 81 Python entries invoked the way `ctest`
  invokes them take 475.0s serially and 209.1s at `-j4` with zero failures, which
  is what established that no entry contends for a port, a fixed path, or a
  shared temp directory. Peak RSS of the heaviest entry is 139 MB, so four
  concurrent jobs are not a memory constraint.
- All three scenario-suite verifiers pass unchanged at 133 v1, 138 v2, and 158
  v3, and every `test-vectors/` file is byte-for-byte unchanged, which the diff
  shows directly. No vector, model, source, specification, or ADR changed.
- The registration guard fails closed four ways, each confirmed by execution
  against the unmutated run as a positive control: a duplicated build-directory
  path, a duplicated entry name, an unparsable registration, and an unregistered
  `tests/tools` module. The third is the informative one — it is what makes the
  uniqueness check non-vacuous, and the parser it guards was in fact missing all
  six fuzz entries when written.
- Issue #131 and PR #132 are the M3.6c delivery, merged by rebase at `c44c320`.
  PR final-head Actions run 31493856438 on `0be7b05` and post-merge run
  31495429227 on `c44c320` both passed the complete hosted matrix — scope
  classification `full`, GCC and Clang debug, both sanitizers, and the aggregate
  required check. No run on that branch was superseded.
- **The CI margin moved, and this is the measurement M3.6b asked for.** The
  slowest job, `gcc-sanitizers`, took 16m24s post-merge and 16m55s on the PR head,
  against the workflow's 20-minute per-job timeout. The margin is therefore about
  3m36s, down from 5m12s at M3.6a. Roughly a minute and a half of that is the
  newly gated evidence — 63 economy and 14 escrow tests plus two verifiers that
  had never run at all — and the rest is the second complete 731-cycle population
  run. 16m55s is the exact figure that triggered issue #122 and PR #123, which
  reclaimed the margin by caching a rebuilt fixture.
- M3.6c local evidence: the suite verifier derives 158 v3 vectors and 51 new
  tests pass — 40 scenario and 11 property. All three suite verifiers pass at 133
  v1, 138 v2, and 158 v3, and `economy-scenario-suite-v1.txt` and `-v2.txt` are
  byte-for-byte unchanged. The 63 v3 economy tests, the 14 escrow v3 tests, the
  373-vector economy v3 verifier, and the 174-vector escrow v3 verifier now run
  in the matrix for the first time and all pass.
- The v3 suite verifier fails closed six ways, each confirmed by execution at
  exit 1 with the unmutated run as a positive control: a tampered recorded value,
  a recorded key no derivation reaches, a derived key the file does not carry, the
  v3 verifier run against the v2 vector file, a closed form assuming every failed
  cycle pays a seat in its own window, and a generator listing every seat in every
  window as version two did.
- **The fifth is the informative one.** It reproduces every monetary total in the
  scenario and is still rejected, on the single vector `economy.unrewarded_windows`
  and nothing else. That is the whole reason the count is recorded: the amounts
  cannot distinguish a portion delivered late from one never carried.
- `random_economy_v3` installs an accepted schedule first and aims each later
  event at one condition, because a purely random window and seat set would now be
  refused almost always. Every hostile activation is refused by construction, and
  a test requires that no run ever records a seat the generator did not install,
  so the schedule it aims against is never disturbed. The eight seeds reach 18
  result codes, a strict superset of the 11 `random_economy_v2` reaches.
- Issue #128 and PR #129 are the M3.6b delivery, merged by rebase at `93e782a`.
  PR Actions run 31395311829 and post-merge run 31396835571 on `93e782a` both
  passed the complete hosted matrix — scope classification `full`, GCC and
  Clang debug, both sanitizers, and the aggregate required check.
- M3.6b local evidence: the escrow verifier derives 174 v3 vectors and 14 new
  tests pass, alongside the 76 retained escrow tests. All three escrow versions
  verify — 169 v1, 172 v2, 174 v3 — and both scenario-suite verifiers pass
  unchanged at 133 v1 and 138 v2, which is the focused check that the changed
  `caps_agree()` and `custody_key()` disturbed nothing that binds through them.
- The v3 escrow verifier fails closed four ways, each confirmed by execution: a
  tampered recorded value, a recorded key no derivation reaches, a derived key the
  file does not carry, and the v3 verifier run against the v2 vector file.
- `test-vectors/escrow-payout-v1.txt`, `escrow-payout-v2.txt`, and both earlier
  fixtures are byte-for-byte unchanged.
- Issue #125 and PR #126 are the M3.6a delivery, merged by rebase at `271a173`.
  PR final-head Actions run 31391379966 on `b06557b` passed the complete hosted
  matrix — scope classification `full`, GCC and Clang debug, both sanitizers,
  and the aggregate required check. Post-merge run 31392793631 on `271a173`
  passed the same complete matrix. Run 31391091746 was superseded by the
  self-review push to the same branch and was cancelled.
- **The CI margin held.** That run took 15m03s with its slowest job,
  `gcc-sanitizers`, taking 14m48s against the workflow's 20-minute per-job
  timeout, which is the same margin PR #123 reclaimed at 14m52s. A new economy
  version, 373 vectors, and 63 tests cost no measurable hosted time, because
  the matrix is dominated by the C++ builds rather than by the Python models.
  M3.6c adds a second complete 731-cycle population run and should re-measure
  rather than assume this holds.
- M3.6a local evidence: the v3 verifier derives 373 vectors and 63 new tests pass
  — 22 schedule, 16 model, 13 error, and 12 scenario. The complete local
  simulation suite is 816 tests in 6m3s. All ten retained verifiers pass
  unchanged: economy v1 derives 139 manifest and 65 simulator values, manifest v2
  154, simulator v2 189, seat 96, routing 200, escrow v1 169 and v2 172, the
  suite 133 v1 and 138 v2, the cycle boundary 101, and the uptime pipeline 114.
  The M2 and M3.1 through M3.5 evidence is intact.
- The v3 verifier fails closed seven ways, each confirmed by execution at exit 1
  with the unmutated run as a positive control: a tampered recorded value, a
  recorded key no derivation reaches, a derived key the file does not carry, a
  boundary check that always accepts, a disabled completeness check, an in-scope
  set given an upper bound at `last_cycle_window`, and a model holding a second
  opinion about a founder figure.
- The sixth is the informative one. Bounding the in-scope set at a seat's last
  issuance window is the plausible narrowing — a seat that no longer issues looks
  like a seat that no longer needs measuring — and it leaves the model internally
  self-consistent. It is caught because `expected.py` derives the set from
  `uptime-measurement-v1`'s rule independently, so the producing and consuming
  ends stop agreeing.
- The seventh is the containment working rather than a check firing. A drifted
  binding makes the run refuse to start, so there is no result to compare, and
  the verifier reports that as its failure.
- `walk.py` is a second implementation of the transitions rather than a wrapper.
  It keeps its own channel, custody, permission, and carry state, reads the
  scenario as plain JSON so it shares no parser with the model, and stands in for
  the record digest with an injective rendering rather than recomputing the
  model's label. A recorded trace is therefore agreement between two
  implementations.
- `expected.py` restates nothing already hand-restated. It reads the economy
  tables from the v2 verifier's closed form and the grid from the cycle-boundary
  verifier's, and requires those two independent restatements to agree with each
  other before any vector is checked, so a divergence between them surfaces as an
  evidence defect rather than a confusing model mismatch.
- Issue #117 and PR #118 are the founder-decision gate change, merged by rebase
  at `0b8c7c2`. PR run 31317461354 and post-merge run 31317481539 both passed the
  focused metadata path; the hosted matrix was correctly skipped for a
  documentation and skill-instruction change.
- Issue #119 and PR #120 are the M3.5 delivery, merged by rebase at `646cfb5`.
  PR final-head Actions run 31319226328 on `5c91dc3` passed the complete hosted
  matrix — scope classification `full`, GCC and Clang debug, both sanitizers, and
  the aggregate required check. Runs 31318883966 and 31319061179 were superseded
  by later pushes to the same branch and were cancelled.
- **That run took 16m55s against the workflow's 20-minute per-job timeout, and
  issue #122 and PR #123 reclaimed the margin at `a38598f`.** The M3.5 fixtures
  rebuilt the scenario in `setUp` rather than once, running a complete
  28,800-block window for a single assertion. Each run shape is now executed once
  and deep-copied per use in `tests/simulation/uptime_measurement_common.py`,
  matching the convention the economy, escrow, and authority suites already use.
  The model test fell from 58.2s to 13.4s and the cross-model test from 8.2s to
  4.5s, about 49 seconds per preset.
- The measurement that matters is the hosted one. PR run 31321119542 completed in
  15m14s with its slowest job, `clang-sanitizers`, taking 14m52s, so the per-job
  margin is about five minutes rather than three. No assertion, boundary,
  rejection condition, or result code moved, and the suite gained one test rather
  than losing any.
- Two tests deliberately do not use the shared fixture. `test_two_runs_agree` and
  `test_a_prefix_reproduces_the_state_it_held` exist to prove a run is
  deterministic, and a cached run would make both tautologies. The one added test
  guards the risk the change introduces: two callers get distinct objects from the
  same state, and mutating one leaves the other whole.
- M3.5 local evidence: the uptime verifier derives 114 vectors and 91 tests pass
  — 22 slot-grid, 60 model, and 9 cross-model. All ten retained verifiers pass
  unchanged: economy v1 derives 139 manifest and 65 simulator values, manifest v2
  154, simulator v2 189, seat 96, routing 200, escrow v1 169 and v2 172, the suite
  133 v1 and 138 v2, and the cycle boundary 101. The M2 and M3.1 through M3.4
  evidence is intact.
- The uptime verifier fails closed five ways, each confirmed by execution at exit
  1 with the unmutated run as a positive control: a tampered recorded value, a
  recorded key no derivation reaches, a derived key the file does not carry, a
  slot count that disagrees with the founder derivation, and a dispute cap one
  above the grace allowance. The last is the informative one. Raising the cap to
  seven leaves the model internally self-consistent and is still refused, because
  a maximal dispute would then leave a perfect seat 17 slots against an 18-slot
  threshold, and the model asserts that theorem rather than trusting its own
  arithmetic.
- `expected.py` reimplements challenge selection from the specification rather
  than importing it, so a recorded selection is agreement between two
  implementations of the rule. It walks the whole scenario independently and
  derives the credited slots the model must also produce.
- The sampling claim is recorded as a measurement rather than as a probability. A
  seat that answers no challenge at all is still credited for the slots it
  happened not to be sampled in, and that is 9 of 24 in the scenario, 9 slots
  below the threshold, so sampling alone fails a fully absent node.
- One defect was found by self-review before merge and fixed at `646cfb5`. The
  result-code table declared `ARITHMETIC_OVERFLOW` and no path could return it:
  every accumulated quantity is bounded far below `u64` by an earlier condition,
  so an overflow there is a defect rather than a rejectable input and the checked
  arithmetic raises. The code was removed rather than given a fabricated path, and
  result-code coverage is now a recorded vector — the declared count, the count
  produced by execution, and their equality — so a later change cannot quietly
  lose a code or add one no path reaches.
- Issue #114 and PR #115 are the M3.4 delivery, merged by rebase at `7dd6a84`.
  PR final-head Actions run 31308600720 on `7d812bd` and post-merge run
  31309236144 on `7dd6a84` both passed the complete hosted matrix — scope
  classification `full`, GCC and Clang debug, both sanitizers, and the aggregate
  required check. Runs 31308454760 and 31308516536 were superseded by later
  pushes to the same branch and were cancelled. The post-merge run was allowed to
  reach a terminal result before the handoff branch was merged, which is the
  procedure the M3.3b cancellation established.
- M3.4 local evidence: the cycle-boundary verifier derives 101 vectors and 57 new
  tests pass — 24 grid and 33 model. All nine retained verifiers pass unchanged:
  economy v1 derives 139 manifest and 65 simulator values, manifest v2 154,
  simulator v2 189, seat 96, routing 200, escrow v1 169 and v2 172, and the suite
  133 v1 and 138 v2. The M2 and M3.1 through M3.3 evidence is intact.
- The cycle-boundary verifier fails closed four ways, each confirmed by execution
  at exit 1 with the unmutated run as a positive control: a tampered recorded
  value, a recorded key no derivation reaches, a derived key the file does not
  carry, and a model constant that disagrees with the founder derivation. The
  last is the informative one. Forcing the model's commit interval to four
  seconds leaves it internally self-consistent — every division stays exact, both
  identities still hold, and the model's own `assert_exact_derivation` passes —
  and the run is still rejected, because `expected.py` reaches three seconds from
  the pinned M1 configuration without importing anything from `simulation/`.
- One containment vector was corrected during self-review before merge. It
  compared two separately built models, which proves the model is deterministic
  rather than that a rejected activation writes nothing, so it would have passed
  a defect that wrote a height before raising. It now measures one instance
  before and after the rejection attempts; forcing a replayed activation to
  record its height was confirmed to fail the corrected derivation and to pass
  the old one. The recorded value never changed, only the derivation's ability to
  fail. The model test already measured this correctly on a single instance.
- Issue #108 and PR #109 are the M3.3a delivery, merged by rebase at `a8ea180`.
  PR final-head Actions run 31268938270 on `0076d4f` and post-merge run
  31269458528 on `a8ea180` both passed the complete hosted matrix — scope
  classification `full`, GCC and Clang debug, both sanitizers, and the aggregate
  required check. Run 31268730543 was superseded by a later push and was
  cancelled.
- Issue #110 and PR #111 are the M3.3b delivery, merged by rebase at `04cdd23`.
  PR final-head Actions run 31270415727 on `5ba7b14` passed the complete hosted
  matrix; no run on that branch was superseded. Post-merge run 31271049373 on
  `04cdd23` was cancelled mid-flight and re-run to a complete pass — scope
  classification `full`, GCC and Clang debug, both sanitizers, and the aggregate
  required check.
- **`verify.yml` sets `cancel-in-progress: true` on a concurrency group keyed by
  `github.ref`, so pushing the handoff commit to `main` cancels the post-merge
  matrix of the slice just merged.** That is what cancelled run 31271049373; no
  operator cancelled it, and nothing was wrong with the commit. Merge a slice,
  let its post-merge run reach a terminal result, and only then push the handoff.
  A cancelled post-merge run is not evidence of a pass, and re-running it is the
  repair.
- PR #112 recorded this handoff and merged by rebase at `848ba36`, with
  post-merge run 31271183838 passing the focused metadata path; the hosted matrix
  was correctly skipped for a documentation-only change.
- M3.3 local evidence: eight verifiers pass. The suite derives 133 v1 and 138 v2
  vectors; escrow payout derives 169 v1 and 172 v2; the economy derives 139
  manifest and 65 simulator v1 values, 154 manifest v2 and 189 simulator v2; the
  seat verifier derives 96 and the routing verifier 200, both unchanged. 50 new
  tests pass — 19 escrow v2 and 31 scenario v2 — alongside the 57 existing escrow
  and 48 existing scenario tests, all unchanged.
- Both v2 verifiers fail closed four ways, each confirmed by execution at exit 1
  with the unmutated run as a positive control: a tampered recorded value, a
  recorded key no derivation reaches, a derived key the file does not carry, and
  the v2 verifier run against the v1 vector file. The last is the informative
  one for the suite: it fails first on the superseded maximum supply.
- Issue #103 and PR #104 are the M3.2 delivery, merged by rebase at `a0521d0`.
  PR final-head Actions run 31266418185 on `4392d15` and post-merge run
  31266927181 on `a0521d0` both passed the complete hosted matrix — scope
  classification `full`, GCC and Clang debug, both sanitizers, and the aggregate
  required check.
- PR #105 recorded this handoff and merged by rebase at `3d23416`, with
  post-merge run 31267484643 passing the focused metadata path; the hosted matrix
  was correctly skipped for a documentation-only change.
- M3.2 local evidence: the simulator verifier derives 189 vectors and the
  manifest verifier still derives 154; 96 new tests pass — 38 model, 39
  transition-error, and 19 scenario — alongside the 61 existing v2 manifest and
  loader tests. All five retained v1 verifiers pass unchanged, so the M2 evidence
  is intact.
- The simulator verifier fails closed five ways, each confirmed by execution: a
  tampered recorded value, a recorded key no derivation reaches, a derived key
  the file does not carry, a Founder Constitution literal that no longer spans a
  cycle, and a model constant that disagrees with the constitution. The last is
  the informative one: shrinking the model's threshold to 64,500 seconds does not
  merely change a number, it makes the constitution's two stated forms of the
  cycle rule disagree and turns an accepted evaluation into a rejection.
- The research scenario reaches all fourteen modelled result codes, and the
  verifier records that as a derived claim so a later scenario cannot quietly
  lose coverage. Every prefix of a mixed scenario reproduces the state the full
  run held at that point.
- Two guards are unreachable at real scale and are proved present rather than
  reached. A zero equal-split share requires the Founder portion shrunk below the
  winner count, because the smallest possible share at the full 100,000-seat
  capacity is 342,000 atomic units. Arithmetic overflow requires a carry near the
  `u64` maximum, because every channel cap leaves more than double its own size
  in headroom.
- Issue #99 and PR #100 are the M3.1 delivery, merged by rebase at `0c05b52`.
  PR final-head Actions run 31262789135 on `e9de7a7` and post-merge run
  31263319868 both passed the complete hosted matrix — scope classification
  `full`, GCC and Clang debug, both sanitizers, and the aggregate required
  check. Runs 31262577723 and 31262627548 were superseded by later pushes to the
  same branch and were cancelled.
- PR #101 recorded this handoff and merged by rebase at `852e289`, with
  post-merge run 31263846117 passing the focused metadata path; the hosted
  matrix was correctly skipped for a documentation-only change.
- Issues #71, #77, #79, #82, #85, #88, and #91 are the M2 deliveries; PRs #72,
  #78, #80, #83, #86, #89, and #92 are merged.
- After PR #72, commits `de9903e` and `4947c46` replaced the Codex agent layout
  with Claude Code and simplified the authorship rules.
- Issue #77 and PR #78 merged at `9aeac23`. PR final-head Actions run
  30849218092 and post-merge run 30850030514 both passed the complete hosted
  matrix — scope classification, GCC and Clang debug, both sanitizers, and the
  aggregate required check.
- Issue #79 and PR #80 merged at `c03262f`. PR final-head Actions run
  30852439693 and post-merge run 30853305170 both passed the complete hosted
  matrix — scope classification, GCC and Clang debug, both sanitizers, and the
  aggregate required check.
- Issue #82 and PR #83 merged by rebase at `5029c00`. PR final-head Actions run
  30896652965 and post-merge run 30897473243 both passed the complete hosted
  matrix. Squash merge is disabled on this repository; use `--rebase`.
- Issue #85 and PR #86 merged by rebase at `512dc0c`. PR final-head Actions run
  30900989541 and post-merge run 30901790621 both passed the complete hosted
  matrix — scope classification, GCC and Clang debug, both sanitizers, and the
  aggregate required check.
- Issue #88 and PR #89 merged by rebase at `20f7fcf`. PR final-head Actions run
  31012045337 and post-merge run 31013129150 both passed the complete hosted
  matrix — scope classification, GCC and Clang debug, both sanitizers, and the
  aggregate required check. Runs 31011546356 and 31011900980 were superseded by
  later pushes to the same branch and were cancelled.
- Issue #91 and PR #92 merged by rebase at `7b4cd6a`, with post-merge run
  31015245429 passing the focused metadata path; the hosted matrix was correctly
  skipped for a documentation-only change. The preceding handoff merged at
  `bc4272a` with post-merge run 31014389973.
- No delivery branch, open PR, additional worktree, or generated build
  directory remains from any delivery.
- M3.1 local evidence: the v2 verifier derives 154 vectors; 23 manifest and 38
  error tests pass; all five v1 verifiers pass unchanged, so the retained M2
  evidence is intact.
- The v2 verifier fails closed five ways, each confirmed: a tampered recorded
  value, a recorded key never derived, a derived key the file does not carry, a
  manifest that disagrees with the Founder Constitution, and an edit to the
  retained v1 contract table down to one atomic unit.
- The fourth of those is the load-bearing one. `expected.py` imports nothing
  from `simulation/` and restates the constitution's two allocation tables by
  hand in tenths of a display unit. The constitution states the economy twice —
  as per-eligible-cycle amounts and as maximum channel totals — and derives
  neither from the other, so requiring them to agree checks the manifest against
  the founder document rather than against a second reading of the
  specification. A forged manifest and contract table raising the referral to
  34.3 units per cycle, propagated consistently through the referral cap, the
  direct-mint subtotal, and the maximum supply, passes every loader stage and is
  still rejected by four `expected.py` comparisons.
- Every recorded v2 rejection is produced by a live loader run over a minimally
  mutated manifest rather than named, and five pairs carrying two defects at
  once prove which stage reports first. A positive control asserts the same
  entry point accepts the unmutated manifest.
- The vectors prove the supply revision is accounted to the referral channel
  alone: the maximum rose by 1,250,010,000 display units, the referral channel
  rose by exactly that, and the summed change across the other nine channels is
  zero. That sum is taken in atomic units against the retained v1 contract
  table, because summing in display units divided a one-atomic-unit divergence
  to zero and hid what the check exists to find.
- Local evidence: 67 Founder Economy tests, 49 Founder Seat tests, 57 revenue
  routing tests, and 57 escrow payout tests pass; the economy verifier derives
  139 manifest and 65 simulator values, the seat verifier derives 96 values
  while confirming an independent walk of the constitutional rule agrees with
  the model on all 1,000 blocks, the routing verifier derives 200 values while
  confirming an independent replay agrees with the model and with 2,400
  contract share computations, and the escrow verifier derives 169 values while
  confirming an independent walk agrees with the model on all 39 events and
  that three caps match the Founder Constitution; repository metadata and link
  validation, `git diff --check`, and the focused verifier unit tests pass.
- The scenario suite adds 48 tests — 14 multi-year, 15 market, 19 property — and
  133 vectors derived across 107,812 events in four scenarios. Every monetary
  total agrees with a closed-form derivation in
  `tools/scenario-suite-vectors/expected.py`, which imports nothing from
  `simulation/`; changing one constitutional literal there was confirmed to fail
  five vectors, including the maximum-supply accounting.
- All five verifiers fail closed when a recorded vector key is never derived.
  The economy, routing, and escrow verifiers were each confirmed to fail on a
  tampered recorded value. The suite verifier was confirmed to fail three ways:
  a tampered value, a recorded key never derived, and a derived key the file
  does not carry.
- The escrow drain scenario binds the population run's own state digest, so the
  escrows are proved drained of exactly what three seats issued into them across
  their complete 731-cycle windows. The empty-cycle count is recorded three
  times: from the generator's population rule, from the verifier's independent
  restatement of it, and from the trace as closes that credited no seat. The
  third agrees with the other two only because every pool in that scenario
  exceeds its active seat count, which the specification states rather than
  assumes.
- The routing remainder bound is proved, not asserted: the remainder depends
  only on `amount mod 200`, so scanning all 200 residues in both creator cases
  is complete. It is at most 2 atomic units with one creator and 3 with two.
- Routing share arithmetic uses the amount's quotient and remainder. The direct
  `45 * amount / 100` form leaves `u64` above roughly 7.4% of maximum supply,
  so it would have rejected a representable payment as an overflow.
- Escrow custody is fixed at the bind and never rises afterwards, because
  `bind_opening_custody` is the only writer of a custody amount and rejects once
  bound. The vectors record `containment.custody_increases_after_bind=0` and
  `containment.multi_escrow_payouts=0`, both derived by the independent walk.
- The escrow binding proves consistency, not provenance: the model only
  recomputes the supplied economy state's digest, so a self-consistent invented
  state would also pass it. The verifier closes that gap by running the economy
  simulator on its accepted fixture and requiring the escrow fixture to bind
  that exact run. Inside the model, the manifest cap is the defence, and a
  `CUSTODY_ABOVE_CAP` vector exercises it. The specification and ADR 0021 both
  state this split rather than overclaiming the digest check.
- `ARITHMETIC_OVERFLOW` is unreachable through escrow events because the caps
  are far below `u64`. The checked arithmetic is still exercised directly by
  the tests so the guard is proved present rather than assumed.
- The verifier reproduces 2,297 canonical JCS bytes and manifest digest
  `2a8923d40615589cc9c9ef90598c0cec56b72a7efa103cf8c05aceb5b54dc698` from the
  checked-in manifest, and fails closed when a recorded vector key is never
  derived or when any recorded value is tampered with.
- The 731-cycle single-seat scenario reproduces the recorded per-seat schedule
  exactly, including 25,000,200,000,000 Founder-operator and
  1,250,010,000,000 referral atomic units.
- Scope classification correctly selects `full` because Python source, CMake,
  and vector paths are not lightweight metadata.
- No dependency, workflow, C++ source, generated build directory, or additional
  worktree is part of any M2 result.

## Remaining gap

No executable Founder Seat, revenue distribution, production escrow, biometric
verifier, packaged Founder Node, AI service, controlled application runtime,
resource cloud, bridge, liquidity system, wallet, public testnet, or mainnet is
implemented. The Founder issuance schedule, permission transitions, revenue
routing, and escrow payouts now exist only as independent Python models, not as
C++ consensus behavior.

**One of those absences now carries a dependency rather than only a roadmap
position.** The founder answer of 2026-08-16 makes external purchasability the
permanent funding path for a new participant once the entry airdrop's
1,000,000-identity bound is reached. Until a bridge or an external venue exists,
the airdrop is the *only* path by which a person who holds nothing can make their
first transaction, so **external purchasability has to exist before the millionth
identity registers**. No transition can enforce that ordering; it is a sequencing
constraint on the bridge and liquidity milestones, and it is recorded here so a
later session does not rediscover it from an `INSUFFICIENT_BALANCE` vector.

All sixteen requirements of `goals/m2-founder-economy-proof.md` passed against
`founder-economy-manifest-v1`. What that does and does not establish is stated
in `founder-economy-report-v1.md` rather than summarized here.

Two qualifiers mattered for M3, and both are now closed as specifications. The
models represented a cycle as a deterministic integer index with no wall clock
reachable from a transition, but that index was not bound to a chain-defined
quantity; M3.4 defines the binding. And the direction the M2 models implement was
superseded on 2026-08-07, so their accepted schemas, vectors, and digests are
evidence about a contract the constitution no longer directs; M3.1 through M3.3
restated it.

Closing them as specifications is not the same as closing them in the models.
`cycle-boundary-v1` defines the mapping and the check, and nothing applies it
yet, so `founder-economy-simulator-v2` still cannot tell whether a supplied
window is the correct one for a seat's cycle. The gap moved from undefined to
unenforced.

M3.1 restated that contract, M3.2 made it executable, and M3.3 rebound every
dependent to it, which closes the second qualifier. `escrow-payout-v2` and
`economy-scenario-suite-v2` bind version two; the seat and revenue-routing models
needed no change, which was re-proved rather than assumed — neither imports either
economy package, and neither carries a supply figure, channel cap, channel
identifier, referral amount, or issuance-cycle count. The retained v1 contracts,
models, vectors, and digests remain in place and passing as the M2 evidence.

M3.2 supplies the activity and reallocation computation that three removed
placeholders used to stand in for, and M3.5 supplies the measurement that
computation reads. The challenge construction, sampling rate, dispute window
length, dispute resolution, and record completeness are now specified, and the
cycle boundary was specified by M3.4. The month definition for the unreferred
pool and that pool's payout, tie, and remainder rules remain unspecified; accrual
into the pool is modelled and paying it out is not.

**What M3.5 does not establish is one undecided value, not an oversight.** The
challenge *protocol* is specified and the challenge *content* is not, so an
answered challenge proves that something able to produce it was reachable within
sixty seconds. That is liveness of a responder rather than possession of a
resource, and every anti-gaming property the specification claims inherits that
limit. The concrete resource commitment — what a Founder Node must prove it holds
— sets what an operator must own in order to be paid, so it is founder-reserved
and belongs to the Founder Node and resource-network milestone rather than being
invented here.

Three further claims are design intent rather than proof and go to the
independent review of requirement 15. The pipeline consumes duty reports and does
not derive them, so a chain that fails to report an assigned duty credits a seat
that did not perform it. A proposer with influence over the state root at
`h - 1` has some influence over who is challenged at `h`, which is the same
adversary ADR 0027 refers to review for the block production rate. And whether a
sampling margin that catches a lost slot about 63% of the time is adequate
against a founder with physical machine access is the question ADR 0023 already
records as unreviewed.

M3.3 exercised that input at multi-year scale without narrowing the gap. The
scenario suite supplies a `cycle_window` by generator convention — the tick — and
supplies every `uptime_seconds` value it then derives verdicts from. A suite that
conserves value under supplied measurements is evidence about the derivation, not
about the measurements. Its winner is also deliberately unique in every window,
so the tie and remainder paths of the reallocation rule are covered by
`founder-economy-simulator-v2`'s own vectors rather than by the suite.

M3.4 made that tick convention checkable without yet checking it, and M3.6c
turned it into a checked rule. The generator now supplies an activation height
per seat and derives every window from the accepted grid, and a window it got
wrong would be rejected rather than ranked. **The supplied `uptime_seconds`
values are unchanged in status.** Completeness is enforced, so a record can no
longer omit an in-scope seat, but every measurement in the suite is still a
fixture and nothing here shows one reflects a real machine.

M3.6b narrows nothing about that. The escrow model reads one recorded economy
state by digest and evaluates no window, so rebinding it proves that escrow
accounting survives an enforced schedule and proves nothing about the suite's
supplied windows.

M3.4 established nothing about measurement and M3.5 does. The grid states how
many blocks a window holds; the pipeline states how a seat earns them. Requirement
12 is now answered in two parts — 800,000 bytes for the activation schedule and
800,000 bytes for per-cycle uptime records at full seat capacity — leaving
per-seat balances and escrow recipient balances open.

**Specified became enforced on 2026-08-10, and only for the newest contract.**
`founder-economy-simulator-v3` applies `cycle-boundary-v1`'s window check and
rejects a record whose seat set is not its window's in-scope set, in either
direction, so the two gaps M3.4 and M3.5 each closed at one end are now closed at
both. `founder-economy-simulator-v2` is unchanged and still records them, which
is correct: it states what the M3.2 and M3.3 evidence proves, and that evidence
was taken against a model that did not check.

What enforcement does not do is make a schedule right. Version three proves that
a supplied window is the window the accepted grid assigns and that a record covers
the population the accepted schedule says was running. It proves nothing about
whether that population was operational, whether the duty reports behind a
measurement are complete, or whether the beacon that selected a challenge was
unbiasable.

One residue is recorded rather than closed. Completeness is measured against the
seat table as it stands, and the model has no current height for an evaluation,
so it cannot require that every in-scope seat has already activated. A chain
closes that by ordering, since a record is emitted only after its window is
final; the activation-height monotonicity rule bounds the residue to an event
ordering a chain does not produce.

**M3.8a moved the whole milestone from modelled to specified-for-consensus, and
that is a different kind of claim.** Everything before it was a Python model
that activates nothing; `economy-transition-v2` states what independent nodes
must reproduce byte-for-byte. What it does not do is execute: no C++ implements
it, no node has run it, and the cross-language agreement of requirement 11 is
exactly the check that would catch an encoding defect the code mapping cannot
see. The encoding is checked against the accepted M1 vectors and against the
economy model's declared code set; it is not checked against an implementation,
because there is none.

**And it is specified into a state that cannot be operated.** All three
authorization predicates are named and undefined, so on a conforming chain no
seat can be activated and no permission can be evaluated, exercised, or accrued.
That is a deliberate refusal rather than an oversight: which senders a predicate
accepts sets what an end user must do and own in order to participate and be
paid, which is founder-reserved. Two consequences are worth separating. The
economy's *accounting* is now proved at four levels — contract, model, enforced
schedule, and canonical bytes — and its *access* has never been specified at
any level.

**M3.8b closed that access gap for every path except one, and it is still not
execution.** `economy-transition-v3` defines who may act for a seat, what a mint
credits, when a seat stops accruing, and what a referrer must hold, so a
conforming version-three chain can be operated end to end apart from kind 6.
What version three does not do is execute: no C++ implements it, no node has run
it, and the cross-language agreement of requirement 11 is still exactly the check
that would catch an encoding defect the code mapping cannot see.

**Three limits version three adds are recorded rather than closed.** A
compromised manager address keeps mint authority permanently, because the
constitution names manager addition as the remedy for a *lost* address and
decides nothing about a *stolen* one; the founder's only defence is to switch
protection on, and only for value not yet minted. The chain does not check that a
HUB uniqueness hash reaches at most one account, so HUB verification is exactly
as strong as the off-chain verifier — where the seat biometric hash already
stands. And the ecosystem verifier key now gates protected mints and manager
additions as well as entry, so its unavailability stops more than it did in
version two, though only for seats whose operators chose that.

The bootstrap is a second gap of the same kind, found while deriving genesis. A
chain with no genesis allocation and a nonzero fee cannot execute its first
transaction, and every path to a first payable balance is external, so the fee
policy and the funding path are bridge-milestone work rather than settled here.

Restart equivalence is state equivalence under replay. It is not persistence,
crash-consistency, or a snapshot format, and no model has any of those.

The four models are only partly joined. The escrow model is the only one that
binds another: it takes opening custody from a recorded founder-economy state by
digest, a one-way read that changes nothing in the economy model, and the
scenario suite exercises that binding against a complete 731-cycle population run
rather than a small fixture. Versions two and three of both preserve exactly
this, and no more. The
others remain unjoined. A seat purchased in the sale model is not an activated
seat in the economy model, and a seat identifier in a routing snapshot is not
proved to be either. M3.4 narrowed that and M3.6a narrows it further: a seat's
schedule given an activation height is defined, and the economy model now records
that height, so what remains unsettled is only what authorizes an activation —
the payment, enrollment, and biometric preconditions. Enrollment, biometric
identity, managers, and same-cycle liveness proof for a performance recipient
are not modelled, and the last of those cannot be without the unresolved
performance policy. The per-principal seat bound is not yet a per-human bound.

Routing and escrow payouts prove accounting, not policy. Nothing shows that the
activity metric is fair, that a snapshot reflects a real machine, that a creator
or product is legitimately approved, that the transaction-fee amount rule is
sound, that any AI evaluation is well made, that an approval threshold is safe,
or that a payout recipient is legitimate. The per-seat balance carry has no
storage bound at 100,000 seats, escrow recipient balances have no storage bound
either, and no claim or push mechanism moves a credited balance into a spendable
account. An escrow capability is modelled as a record; the signed envelope,
replay domain, and encoding that would carry one on a real chain are undefined.

## Exact next action

Milestone slice **M3.10c: the C++20 kernel codec and transitions for
`economy-transition-v6`**, which is requirement 10. Use the `change-protocol`
skill.

**Replace `src/v4/` rather than adding `src/v6/` beside it**, and record the
decision either way. The Python side keeps version four because its 441 vectors
are the record of what the hosted matrix verified; the C++ side has a weaker case
for a copy, since it is one implementation of a byte surface and keeping two
would double the build with nothing but labels between them. **The codec is the
only place in the repository where a superseded contract would still be
compiled.**

**Four things in the C++ move and are easy to miss.** The six HUB message
labels, which are string literals rather than a table. The scheme byte, which is
a `switch` the version-one kernel does not have — it reads offset 39 as a
constant. The signer derivation, `H(D("protocol-stack:v1:account") || 0x01 ||
pk)`, which `src/v1/admission.cpp` already implements file-privately and which
should be reused rather than written twice, checked against the identifier
`test-vectors/protocol-primitives-v1.txt` records. And the state-root version
field, which is a number rather than a label and so will not appear in a search
for `v4`.

**M3.10b's four derived rules are what the C++ must reproduce, and they are
exactly the class a byte-level cross-language check cannot catch.** ADR 0045
records each with its alternative: `DEBIT_OVERFLOW` at envelope check 8, an
unrequested confirmation field refused at execution with `UNAUTHORIZED` rather
than at admission with a code the result space does not contain,
`NOTHING_TO_MINT` as the empty walk range, and the cycle assignment written
before a boundary block's transactions. **Whether M3.10c is a codec alone or a
codec plus transitions decides which of them it can demonstrate.** M3.9a's
version-four codec was a codec alone and every entry point was a pure function of
its arguments; a codec cannot reach any of the four, so a codec-only slice leaves
requirement 11's cross-language vectors covering bytes and nothing else — which
is the shape of the M3.9b defect one layer up. Prefer the codec **plus** the
envelope-check order and the four rules, and record what was left out.

**The local C++ harness is the reusable result of M3.9a.** Building libsodium
locally is the heavy operation `CLAUDE.md` refuses, so a scratch harness supplies
the two entry points the kernel uses and backs SHA-256 with the system OpenSSL —
an existing audited implementation rather than a second one, in a file that is
never committed and never part of the build. With it the whole codec test
compiles and runs in about a second under both compilers with the project's exact
flags and under address and undefined-behaviour sanitizers.

**One local hazard cost time in M3.10a and again in M3.10b.** Stale
`__pycache__` made a reverted mutation appear to still fail and a real failure
appear to pass. A hosted runner starts clean, so it is a local-only trap; clear
it before believing a probe result.

**A mutation probe must mutate the behaviour rather than an argument's default.**
M3.10b's assignment-ordering probe passed on its first attempt because the
fixture passes the flag explicitly, so changing the default changed nothing. The
probe was measuring the argument. Re-run any probe that passes.

### What M3.10b superseded in this section

The rest of what stood here is delivered. The execution model was written, the
five things it had to exercise were exercised, and the order it was written in —
model before kernel — found four things a codec could not have.

**Both things M3.10a was told to re-check were re-checked.** Requirement 12's
storage bounds moved to per-identity escrow and signer entries and are recorded
as a per-person figure, and the settlement was imported rather than copied, with
the two assignment records required to equal the bytes
`test-vectors/economy-transition-v3.txt` fixes.

**The recorded next action changed at the end of the M3.9c session, and the
reason is founder direction rather than a defect.** M3.9c closed by asking about
the recovery path version five encodes. The owner rejected the premise of the
question and directed a pivot, recorded in
[ADR 0039](../decisions/0039-hub-verification-is-mandatory-for-everyone.md) and
in the constitution: **HUB verification is mandatory for anyone who registers
and for interacting with any part of the ecosystem**, an address is an
operational tool rather than an identity root, recovery is direct between the
owner and their recorded biometric data with no third party at any step, and
biometric confirmation is on by default for every financial transaction and
every mint with each person free to set a minimum amount, set time windows, or
turn it off entirely.

**M3.9d — the C++ codec updated to version five — is therefore withdrawn as the
next action.** It is not wrong work; it is work that would have to be done twice,
which is the precedent M3.8a set and M3.9b repeated: a kernel written against a
contract already known to be superseded is wasted. The kernel codec stays at
version four until a contract exists that the direction does not supersede.

**The account model was answered the same day and is recorded in
[ADR 0040](../decisions/0040-holder-addresses-and-revocable-signers.md).** A
verified identity holds as many fund-holding addresses as the person wants;
those hold no keys and never change; signers are separate, revocable, and
assigned per holding address; and the identity is the admin that may add,
remove, revoke, or modify them. Regaining an identity on a new device regains
the holding addresses directly.

**That answered the fee question for recovery and dissolved the version-five
dilemma.** Maria never arrives at an empty address, so nothing needs funding and
no helper is involved; and an address created beneath an identity is never
relinked, so there is nothing to link and nothing to squat.

**That conflict was resolved the same day, in
[ADR 0041](../decisions/0041-the-seat-is-tied-to-the-identity-not-an-address.md),
by naming what the add-only rule was for.** It was never about addresses; it was
about non-sellability. A seat is now tied permanently to the owner's HUB
verified data, **so a Founder Seat has no address at all** and there is nothing
left for an add-only rule to govern. Seat addresses, the 16-manager limit, and
the mint-to-the-signing-address rule are superseded together with the concept
they governed. One uniform model covers every participant.

**Every founder-reserved question the pivot itself raised was closed the same
day**, the last in
[ADR 0042](../decisions/0042-the-hub-entry-airdrop-and-the-verified-user-rate.md).
A brand-new person's first action is funded by the protocol from an allocation
they are already entitled to: on completing HUB verification for the first time
the chain issues their first day's `hub_verified_user_incentives` portion as an
entry airdrop, and every later day continues as an ordinary mint permission
under the thirty-window cap.

**That was not the same as nothing blocking the next slice, and the handoff said
it was.** Writing the contract reached two decisions the constitution had already
listed as unresolved and two the ADRs left open, none of which the pivot's own
three questions covered. All four were answered on 2026-08-15 and are recorded in
ADR 0043.

**The rate is derived, not chosen, and that is the strongest thing about it.**
The owner supplied the population and the period — the first 1,000,000 verified
users, daily, for two years — and those with the founder-directed cap divide
exactly: 125,001,000,000,000,000 / 1,000,000 / 731 = 171,000,000 atomic, or 1.71
native units per user per day, with no remainder. 730 cycles leaves 420,000,000,
so the period is 731, the same as a seat's issuance period. Three supplied
figures reproducing the accepted cap to the atomic unit is what makes this the
intended reading rather than a plausible one.

**What version six inherits, and why the pivot is cheaper than it looks.** The
dilemma version five had to solve — who may link an address to an identity —
exists only because an address can exist, transact, and hold value with no
identity behind it. When registration is HUB-first for everyone, an address is
created under an identity that already exists, so kind 11 in its version-five
form has nothing left to solve. The envelope, the key space, the settlement, the
receipt, and the tree constructions are unaffected by any of this, and version
five's model and vectors are what make a successor's carryover check possible.

**Check that any new target is in `PROTOCOL_STACK_TARGETS`.** That list carries
`-Wall -Wextra -Wpedantic -Werror`, the sanitizer flags, `_GLIBCXX_ASSERTIONS`,
and the libsodium link. M3.9a declared a target, added its `add_test`, and left
it off that list; the registration guard does not catch it, because it checks
that a test is *run* rather than how it is *built*.

**Keep every accepted artifact in place and passing.**
`simulation/founder_economy/`, `simulation/founder_economy_v2/`,
`simulation/founder_economy_v3/`, `simulation/cycle_boundary/`,
`simulation/uptime_measurement/`, `simulation/economy_transition/`,
`simulation/economy_transition_v3/`, `simulation/economy_transition_v4/`, and
`simulation/economy_transition_v5/` stay untouched.
**`simulation/economy_transition_v4/` is now load-bearing three ways**: version
five imports it, version five's carryover check reads
`test-vectors/economy-transition-v4.txt` directly, and version six imports its
constants and its independent derivation — so editing it would move three
versions' evidence rather than one. **`simulation/economy_transition_v3/` is
load-bearing twice**, because versions four and six both import its settlement
and both require its two recorded assignment records.
`simulation/escrow_payout/` is shared by three bindings and
should gain no fourth without a new contract version, and
`simulation/scenarios/` holds three population generators that must stay
independent for the same reason.

**Every new test and verifier must be registered in `CMakeLists.txt` and must run
as `python3 <path>`.** `tests/tools/test_registration_test.py` enforces both.

**`main` is branch-protected.** Even a documentation-only commit needs its own
branch and pull request.

## Blockers

**None for M3.10c.** M3.10b ran the founder-decision gate and **passed** it.
Every decision the slice had to settle was already decided or delegated:
where the execution model lives, which vector file records it, the order of the
shared envelope checks, where the debit-overflow test sits inside them, which
result code an unrequested confirmation field earns, what `NOTHING_TO_MINT`
means for a fresh mark, where a cycle assignment lands inside a block, whether
the block header and transaction tree are re-versioned, what fee the trace runs
on, and how a signature is modelled without implementing one. **Four of those had
to be derived rather than looked up**, because the accepted contract admits two
readings of three of them and is silent on the fourth; every one is a rejection
order or a code assignment, which `founder-constitution.md` lines 883-886 name
as mechanism, and each is recorded with its alternative in ADR 0045 rather than
settled silently. None sets or changes supply, allocation, beneficiaries, Founder
ownership, creator hierarchy, commercial routing, AI institutional authority,
bridge scope, content permanence, or what a participant must do, own, run, or
receive.

**The one founder-reserved question M3.10b raised was answered the same day, and
the answer is that the accepted rule stands.** The millionth-and-first verified
person registers successfully, receives no entry airdrop, and holds a
zero-balance escrow — so until they are funded, every transaction they can sign
answers `INSUFFICIENT_BALANCE`, including the mint for a verified-user permission
they do not have. **That is a consequence of two accepted decisions rather than a
new rule**: ADR 0042 bounds the airdrop at 1,000,000 identities and the
constitution applies a fixed fee to every accepted state transition.

**The owner's answer on 2026-08-16 was to change nothing, and the reasoning
supplies what the question was missing.** By the time a million people hold HUB
verification the project has scaled past the point where the native asset exists
only inside the ecosystem: bridges and external venues make it purchasable, so a
new participant funds their own escrow from outside, or an existing member sends
them value. The entry airdrop is a launch incentive with a bound, not the
permanent funding path, and **the permanent funding path is external liquidity**.
No specification, model, vector, or ADR rule changes; `economy-transition-v6` and
ADR 0042 already encode the answer.

**It creates one checkable roadmap dependency, and that is the part worth
carrying.** External purchasability must exist before the millionth identity
registers, because the airdrop is the only funding path a newcomer has until it
does. That is a sequencing constraint on the bridge and liquidity milestones
rather than a protocol change, and no transition here can enforce it.

**The founder-decision gate stopped `economy-transition-v6` on 2026-08-15 with
four reserved decisions**, the owner answered all four the same day, and the
contract that encodes them was delivered the same day. ADR 0043 records the
answers, ADR 0044 records the contract, the constitution states both, and the
unresolved list is two entries shorter.

**Requirement 10's target is settled again**, at `economy-transition-v6`, and it
is the first version-six-era contract the direction does not supersede. Nothing
founder-reserved stands in front of the C++ kernel, and the execution model that
was to precede it is delivered.

**One specification correction is owed to a later contract version, and only
one.** `economy-transition-v6`'s requirement that an unrequested confirmation
field be 64 zero octets is placed at admission, which cannot read the stored
posture its predicate needs, and names `MALFORMED_TRANSACTION`, which is an
admission code and has no counterpart in the result-code space a receipt records.
M3.10b refuses it at execution with `UNAUTHORIZED` and ADR 0045 records why.
**No rule in the accepted specification was edited**, and the correction is a
note for version seven rather than a defect that stops anything.

**How the gate came to stop the slice is worth keeping, because the failure mode
recurs.** The handoff had said "Blockers: None". The pivot's own three questions
did all close on 2026-08-15 — the recovery fee by ADR 0040, the seat-permanence
conflict by ADR 0041, entry funding and the verified-user rate by ADR 0042 — and
the handoff generalised from those three closures to the milestone. Two items the
constitution had listed as unresolved since the pivot were filed as "answerable
alongside" and "blocking nothing on their own", which was true while the
entry-funding question was the nearest dependency and false the moment it closed.
**Nothing in the repository changed; the next slice moved toward them.** That is
what "record a reserved decision and raise it once it becomes the nearest
dependency" is for, and enumerating the slice rather than assessing it whole is
what surfaced it — the same failure mode M3.8a's gate caught, in the same place.

**Two of the four answers went further than filling in a blank**, which is the
third time the standing invitation has produced that. Refusing an unregistered
recipient withdraws a transfer behavior every version since M1 has carried, and
generalising the seat's protection asymmetry to every participant deletes a
per-seat flag rather than adding a policy layer beside it.

### What remains open in the constitution and is genuinely not this milestone's

Eligibility and anti-abuse for the liquidity-mining, impermanent-loss, and
mystery-box channels; legacy inactivity bounds; stablecoin allowlist governance;
the AI frameworks; and verifier key rotation. Kind 6 stays specified and refused
because of the first, which costs one transaction kind rather than a milestone.

Superseded, and kept for the record: **how a person who holds nothing pays for
their first transaction.** The mandatory-verification direction of 2026-08-15 says
registration and recovery involve no helper and no third party, and every
transaction costs a fee paid by a sender. The three candidate answers —
fee-exempt identity transactions, a fee drawn from value the identity already
holds on chain, or registration performed by the company-hosted HUB service —
each change what a participant must do and own, so none may be invented. ADR 0040
answered it for recovery and ADR 0042 for entry, and it no longer blocks
anything.

**The two questions this entry filed beside it as blocking nothing are
blockers 1 and 2 above**, and the reclassification is the correction rather than
new information. They were recorded as "answerable alongside" the entry-funding
question while it was the nearest dependency; once it closed, the next slice
became the contract, and the contract reaches both. Neither moved — the slice
moved toward them.

Requirement 10's target is no longer settled. It was `economy-transition-v5` for
one day; the direction of 2026-08-15 supersedes it, and the C++ kernel waits for
the contract that encodes the direction. **That is a change of target, not lost
work**: the envelope, the key space, the settlement, the receipt, and the tree
constructions are unaffected, and version five's model and vectors are what make
a successor's carryover check possible.

**The evidence debt M3.9b took on is repaid.** `economy-transition-v5` has a
model, 550 vectors, and a verifier as of M3.9c. It is a fully evidenced contract
that was superseded as direction hours after it was evidenced — which is the
same thing that happened to versions two, three, and four, and is the reason the
repository evidences a contract before implementing it in C++ rather than after.

**One accepted contract cannot be implemented and stays in the tree.**
`economy-transition-v4`'s kind 11 has no conforming implementation; version five
corrects it and version four is retained unedited because its 441 vectors are
the record of what the hosted matrix verified on 2026-08-15. Its specification
and the documentation index both say so, so a reader cannot pick it up as the
newest contract by accident.

M3.10a ran the founder-decision gate and **did not pass it**, which is the second
time the gate has stopped a slice rather than clearing it; M3.8a was the first,
and that slice's specification had to be rebuilt because the answers changed the
transaction set rather than filling in blanks. **The answers arrived the same day
and the slice was then delivered in full**, so the stop cost a question rather
than a session.

Thirty-six decisions were enumerated before any was judged. Thirty-two are
delegated. Mandatory registration, the address as an operational tool, direct
recovery, and biometric-by-default are ADR 0039 and the constitution. The
identity as admin, escrows that hold no keys, revocable per-escrow signers, and
unlimited escrows per person are ADR 0040 and the constitution's uniform-model
paragraph. A seat with no address, the removal of kind 9 and the manager set, and
a mint naming a destination escrow the chain checks belongs to the minting
identity are ADR 0041, the last recorded there as a derivation. The entry
airdrop, its 171,000,000-atomic rate, its one-per-identity bound, the
1,000,000-identity enrollment, the 731-cycle period, and who submits a
registration are ADR 0042. The escrow identifier derivation and the two-signer
ordering rule are named as engineering by ADR 0040 in those words. The version
labels, kind identifiers, body layouts, entry kinds, result codes, storage
shapes, receipt version, genesis fields, and root constructions are mechanism,
encoding, and storage under `founder-constitution.md` lines 883-886.

Six were deductions from decided principles, which the gate treats as delegated
and expected: that registration must create the identity, its first escrow, and
its first signer in one atomic execution or the airdrop has nowhere to land; that
registration is better made fee-exempt than credit-before-fee, because the
airdrop is bounded at a million identities and the fee is not; that the accepted
version-one account derivation becomes the *signer* identifier; that the nonce
belongs to the escrow rather than the signer; that escrow deletion requires a zero
balance; and that a policy's time windows are block heights, because a transition
may not read a wall clock. All six are recorded under
[What the M3.10a gate's enumeration found](#what-the-m310a-gates-enumeration-found).

**The four reserved ones were asked in one batched call and all four were
answered the same day**, and ADR 0043 records them. Two — the reach of mandatory
verification into a transfer, and what "off entirely" means for a seat's
protection asymmetry — had been in the constitution's unresolved list since the
pivot was recorded, and enumerating is what showed they are inside the contract
rather than beside it. Assessed whole, "specify the account architecture the four
ADRs settled" reads as pure engineering, and both reserved decisions are inside
it. That is the same failure mode M3.8a's gate caught, in the same place.

**The gate's own record is the point.** It stopped a slice for the second time in
the milestone, the answers changed the contract rather than filling blanks in it,
and the specification was not started before they arrived — which is what the
gate exists to produce.

M3.9c ran the founder-decision gate and passed it. Every decision the slice had
to settle was already decided or delegated: the corrected field meaning, the
sender as the linked account, the rejection order, and the eight labels by the
accepted `economy-transition-v5` and ADR 0037; the package layout by ADR 0026
and ADR 0029; and the evidence method, the fixture, the vector names, and the
test registration as engineering under `founder-constitution.md` lines 772-775.
Nothing in it set or changed supply, allocation, beneficiaries, ownership,
creator hierarchy, commercial routing, AI authority, bridge scope, content
permanence, or what an end user must do, own, run, or receive.

**One consequence of the accepted contract is worth the owner's eye even though
it blocks nothing, and the gate flagged it rather than passing over it.**
Requiring the sender to be the address being added means a person recovering
from total address loss must first fund a fresh account themselves, and no third
party can perform the addition on their behalf. ADR 0037 records that trade and
lists it for review; it is stated here because it is the kind of thing the
standing invitation of 2026-08-13 covers — a rule about what an end user must do
to be paid — and because the moment to revisit it was before the C++ codec was
rewritten against it, not after.

**Asking it was the right call, and the answer went further than the question.**
The owner rejected all three offered flows and directed the pivot ADRs 0039
through 0042 record. The consequence flagged here no longer exists: a recovering
person regains escrows that already hold value, and a brand-new one is funded by
the entry airdrop. That is the second time the standing invitation of 2026-08-13
produced a materially better design than inference would have — the first was
M3.8a, which the invitation itself cites.

M3.9b ran the founder-decision gate and passed it. Every decision the slice had
to settle was mechanism: which of two repairs to make, whether to version or
repair in place, and the version-five labels. Nothing in it set or changed
supply, allocation, beneficiaries, ownership, creator hierarchy, commercial
routing, AI authority, bridge scope, content permanence, or what an end user must
do, own, run, or receive. The correction restores a capability the founder
direction already granted rather than granting a new one.

**Six answers arrived on 2026-08-14 and all six are now encoded.** A mint credits
the address that signed it; sixteen manager addresses per seat; a cycle a seat
cannot collect because it is full **is** a cycle it failed, so the day's
generation goes to the best performers and the full seat is not one of them;
buying a seat requires HUB verification first, with the seat tied to that
identity; a HUB identity's address set lives in consensus state, HUB-signed on
both add and remove; and the accumulation limit stays measured as time since the
last collection.

**One founder-reserved decision remains and it blocks nothing.**
`direct_issue_authority` — the eligibility and anti-abuse mechanics for the
`liquidity_mining`, `impermanent_loss_protection`,
`hub_verified_user_incentives`, and `initial_mystery_box_incentives` channels,
and the rate of the one whose eligibility ADR 0033 settled. Kind 6 is specified
and refused rather than given an invented predicate, which costs one transaction
kind rather than a milestone.

**Four claims in version four need independent review before value depends on
them**, and ADR 0036 records each with its reasoning. The sharpest is that adding
a seat address now needs one factor where version three needed two: version three
requires a key the founder already holds *and* a fresh approval, and version four
requires only the HUB signature so that a founder holding no keys is not locked
out — so a coerced or spoofed HUB signature can add an address to a seat, and
seat addresses are permanent. The others are that one identity layer is asked to
carry both uniqueness, which wants a binding that cannot move, and recovery,
which requires one that can; that **no transition rotates a HUB public key**, so
a person who loses the secret behind it loses every proof version four depends
on and the chain offers no remedy; and that the verifier's narrower reach cuts
both ways, since it can no longer help anyone either.

**One residual gap is worth naming for the identity milestone.** Every guarantee
version four adds — one person one identity, the per-human seat bound,
self-referral refusal — rests on the ecosystem verifier's attestation that a
registration is a distinct live human, and is exactly as strong as it. The chain
verifies signatures by a key it was told to trust; it establishes nothing about
the capture behind it.

The three questions the founder decisions of 2026-08-14 themselves raised are
settled and recorded in ADR 0033, and all three are now encoded in
`economy-transition-v3`:

1. **A capped cycle moves its whole permission**, escrow and System Creator legs
   included, exactly as a failed cycle does. One rule rather than two, and the
   escrows never lose value because an operator was slow to collect.
2. **Disabling biometric-on-mint requires a biometric approval**, while enabling
   it requires only the address signature. The asymmetry is the protection: a
   stolen key can neither mint against a protected seat nor remove the protection
   first.
3. **The cap applies to referral earnings too.** The forfeited value stays inside
   the `founder_referral` channel and routes to the unreferred performance pool,
   which is already that channel's second destination and already pays the
   month's best performer. This was chosen against the recommendation offered;
   the consequence is that a referrer forfeits value for inactivity that was
   never asked of them, and what it buys is one collect-or-lose rule across the
   whole economy with no account holding value indefinitely.

One founder-reserved decision is narrowed rather than closed:
**`direct_issue_authority`**. The `hub_verified_user_incentives` channel's
eligibility is now decided — being HUB verified — but its *rate* is not, and the
`liquidity_mining`, `impermanent_loss_protection`, and
`initial_mystery_box_incentives` channels are unchanged. Kind 6 stays specified
and refused.

Two further decisions are recorded rather than blocking. **The concrete resource
commitment** — what a Founder Node must prove it holds — becomes the nearest
dependency at the Founder Node and resource-network milestone. **Verifier key
rotation** is recorded from M3.8a: the ecosystem verifier key is written at
genesis and no transition changes it, so a compromised or retired key can only be
replaced by a new chain. Rotation decides who controls admission to the economy,
so it is not invented.

**The bootstrap gap is a bridge dependency, not a founder question.** A chain
with no genesis allocation and a nonzero fee cannot execute its first
transaction, and every path to a first payable balance is external.

**HUB verification is now a cross-milestone dependency and is specified
nowhere.** ADR 0033 widens M4 from a founder-seat biometric verifier to an
ecosystem identity service serving every participant class, with a direct-mint
incentive attached. The constitution's existing threat-model, unlinkability,
retention, and independent-review requirements apply to the widened scope.

M3.8c ran the founder-decision gate and passed it. Every decision the slice had
to settle was already decided or delegated: that a changed authorization is a
new version by ADR 0024, ADR 0026, and version three's own versioning section;
HUB-first purchase, the on-chain address set, and the cap's measurement by the
owner's answers of 2026-08-14; HUB signing for seat addresses and their
permanence by ADR 0035; the construction of a person's HUB signature by the
constitution's own statement that "the cryptographic construction is engineering
work"; the per-human seat bound by the constitution, which fixes 1,000 and which
version four is the first contract able to enforce; and the version labels, kind
identifiers, body layouts, entry kinds, message shapes, result codes, and the
16-address bound as mechanism, encoding, and storage under
`founder-constitution.md` lines 712-715. Two deductions were recorded rather
than invented: that removal unlinks without moving value, which is the smaller
claim, and that removing an address from an identity does not remove it from a
seat, which follows from seat addresses being permanent. `direct_issue_authority`
stayed reserved and kind 6 stayed refused. Nothing in the slice set or changed
supply, allocation, beneficiaries, ownership, creator hierarchy, commercial
routing, AI authority, bridge scope, or content permanence.

M3.8b ran the founder-decision gate and passed it. Twenty-five decisions were
enumerated before any was judged. Twenty are delegated: that a changed transition
is a new version by ADR 0024, ADR 0026, and `economy-transition-v2`'s own
versioning section; the manager rule, the optional biometric and its asymmetry,
the cap and its reallocation path, the referral cap and its destination, and the
HUB requirement by ADR 0033 and the constitution; that a manager may not be
removed by the constitution's own "remains in the historical ledger forever";
that HUB eligibility is "any participant who registers" and that its
cryptographic construction is engineering work, both stated in the constitution;
and the version number, labels, kind identifiers, body layouts, entry kinds,
beneficiary numbering, result codes, cap figure, manager bound, and storage
shapes as mechanism, encoding, and storage under `founder-constitution.md`
lines 712-715.

Three are deductions from decided principles, which the gate treats as delegated
and expected: that a mint credits its signer, that a capped seat is not a winner,
and that `mint_referral` gains no biometric option because the option is a
property of a seat and a referrer need not hold one. The first two are raised
above for confirmation because they decide who is paid.

Two remain founder-reserved and neither blocks: `direct_issue_authority`, which
keeps kind 6 refused, and **whether the chain enforces one HUB registration per
human**. The second is new, and version three deliberately does not enforce it:
doing so would decide what happens to a verified human who loses the key to
their registered account, which sets what a user must own in order to keep
participating. Not enforcing it is the smaller claim and leaves HUB exactly as
strong as the off-chain verifier, where the seat biometric hash already stands.

M3.8a ran the founder-decision gate and **it did not pass silently — it is what
found the two blocking questions above.** Eighteen decisions were enumerated
before any was judged. Fifteen are delegated: the transition version, the kind
identifiers and their bodies, the byte layouts, the signing labels, the state
keys, the state-root extension, the receipt layout, the numeric receipt codes,
the activation rule, the per-block resource limits, where the uptime record
enters consensus, and the fee treatment are mechanism, encoding, and storage
under `founder-constitution.md` lines 669-672, and `first-goal.md` requirement 5
names the first group as the deliverable while requirement 15 requires an ADR
stating the transition shape, encoding, and compatibility boundary. The
compatibility boundary is delegated by requirement 6 and by
`ledger-transition-v1`'s own rule that a later issuance rule requires a new
transition version. The denomination boundary is delegated by
`founder-economy-manifest-v2`'s versioning section, which names the new-genesis
or migration choice as engineering work with required evidence. The supply limit
is founder-directed and already fixed at 5,699,395,010,000,000,000 atomic.

The remaining three are the authorization predicates, and enumerating before
judging is what surfaced them: assessed as a whole, "specify the transaction
encoding" reads as pure engineering, and the reserved decision is inside it.
Only `direct_issue_authority` was previously on the list. Nothing in the slice
sets or changes supply, allocation, beneficiaries, ownership, creator hierarchy,
commercial routing, AI authority, bridge scope, or content permanence.

M3.7a ran the founder-decision gate and passed it. Five decisions were
enumerated — whether `ctest` runs entries concurrently and at what job count,
how that count is derived and whether a serial path is kept, the scheduling
order, which runs a shared fixture may cache, and which guards run on which
verification path — and every one is autonomous engineering work under
`founder-constitution.md` lines 669-672, which place testing and operational
choices outside the reserved set alongside mechanism, encoding, storage,
consensus scheduling, networking, and packaging. Nothing in the slice set or
changed supply, allocation, beneficiaries, ownership, creator hierarchy,
commercial routing, AI authority, bridge scope, content permanence, or what an
end user must do, own, run, or receive; it changed no vector, model, source,
specification, or ADR at all.

Two were already recorded: eligibility and anti-abuse mechanics for the
liquidity-mining, impermanent-loss, HUB-verified-user, and mystery-box
direct-mint channels, and the AI funding framework with its evaluation criteria,
milestone and tranche policy, and approval thresholds. Both are still supplied to
the models as bound research inputs, and `founder-economy-manifest-v2` keeps
`direct_channel_eligibility_result` as its single research placeholder for
exactly that reason.

**M3.5 identified a third: the concrete resource commitment.** What a Founder
Node must prove it holds — the storage, compute, and delivery capacity a
challenge is answered against — sets what an operator must own in order to be
paid, which is founder-reserved under the clause added to `CLAUDE.md` on
2026-08-09. It is not in the constitution's list of explicitly unresolved details
and is recorded here and in ADR 0028 rather than added to that document.

It becomes the nearest dependency at the Founder Node and resource-network
milestone, not at M3.6, which consumes a record and never issues a challenge.
M3.6a confirmed that by execution rather than by assumption: version three reads
a record's measurements and has no transition that issues, answers, or disputes a
challenge.
Until it is decided, `uptime-measurement-v1` proves liveness of a responder
rather than possession of a resource, and says so. Ask the owner when a challenge
must actually be constructed, and do not invent a minimum specification to make
one testable — use an abstract answer predicate, as the model already does.

The other two closed on 2026-08-07. Activity, grace, performance ranking, tie
handling, inactive-seat referral treatment, and referral-channel eligibility are
now decided in the Founder Constitution and ADR 0023, and must be implemented as
stated rather than re-litigated or re-supplied as fixtures.

Ask the owner at the point where a specific transition would otherwise have to
invent one of the three that remain, using the founder-decision gate in the
`proceed-project` skill.

M3.6c ran that gate and passed it. Eight decisions were enumerated and every one
was already decided elsewhere: that rebinding is a new suite version by
`economy-scenario-suite-v1.md`'s versioning section and ADR 0024 and ADR 0026;
the activation heights by `cycle-boundary-v1` once the shared window is held
fixed, which is arithmetic rather than a choice; the in-scope rule by
`uptime-measurement-v1`; the record's three uptime values and the 64,800-second
threshold by `economy-scenario-suite-v2.md` and ADR 0023; the empty-winner
carry-forward rule by ADR 0023; the escrow binding by ADR 0030; and the version
independence of scenarios 2 and 3 by ADR 0026. The probe seats' heights and the
peer seat are fixture engineering that changes no cap, channel, or entitlement.
Nothing in the slice sets or changes supply, allocation, beneficiaries,
ownership, creator hierarchy, commercial routing, AI authority, bridge scope,
content permanence, or what an end user must do, own, run, or receive.

M3.6b ran that gate and passed it. Every decision it settled was already decided:
that rebinding is a new version by ADR 0024 and ADR 0026, which six strings change
by version two's own table, and that a `Binding` rather than a package is correct
by ADR 0026's stated condition. The escrow caps agreeing across three contracts is
a derived fact about ADR 0023's revision, not a choice.

M3.6a ran that gate and passed it. Every decision the slice had to settle is
already decided elsewhere: the window mapping and its three rejection codes by
`cycle-boundary-v1` and ADR 0027, the in-scope rule by `uptime-measurement-v1`
and ADR 0028, the requirement that the seat record carry an activation height by
`cycle-boundary-v1`'s own closing section, and that a changed transition is a new
version by ADR 0024 and ADR 0026. Nothing in the slice sets or changes supply,
allocation, beneficiaries, ownership, creator hierarchy, commercial routing, AI
authority, bridge scope, content permanence, or what an end user must do, own,
run, or receive: an activation height is *recorded*, not earned, and what
authorizes an activation stays M4 and was not touched.

M3.5 ran that gate and passed it. It touches the Ecosystem AI without reaching
the reserved AI question: ADR 0023 and the Founder Constitution already decide
that the AI reviews and may dispute, that its signature is deliberately not a
precondition for payment, and that silence finalises a result, and the
constitution states outright that the challenge construction, sampling rate,
dispute window length, and dispute resolution are specification work rather than
founder decisions. The AI *funding* framework is the reserved one and M3.5 did
not touch it. The dispute cap was derived from the founder-directed grace
allowance rather than chosen, which is why it needed no decision.

ADR 0027 and ADR 0028 together record five claims that are design intent rather
than proof and need independent review before the pipeline carries value. From
ADR 0027: that the grid is safe against an adversary able to influence block
production rate, since a slow chain stretches every window in real time while the
nominal accounting stays fixed; and the interaction between the schedule and the
measurement pipeline. From ADR 0028: that an answered challenge reflects a real
machine, which is bounded by the undecided resource commitment; that the sampling
margin is adequate against a founder with physical machine access; and that
beacon bias is tolerable, since a proposer with influence over the state root at
`h - 1` has some influence over who is challenged at `h`. The last should be
reviewed together with ADR 0027's block-production-rate adversary, because they
are the same adversary. None blocks M3.7a, and all belong in the independent
review requirement of `first-goal.md` requirement 15. None of M3.6a, M3.6b, or
M3.6c narrows any of them: enforcing a schedule against a measurement does not
make the measurement sound, rebinding an escrow model to that schedule does not
either, and running a longer scenario against it does not either. ADR 0029, ADR
0030, and ADR 0031 record the limits rather than leaving them to be inferred.
