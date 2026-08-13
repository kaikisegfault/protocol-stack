# ADR 0032: The economy consensus transition, its encoding, and the M1 compatibility boundary

- Status: Accepted
- Date: 2026-08-13

## Context

Everything M3.1 through M3.7a produced is a specification or an independent
Python model that activates nothing. `founder-economy-manifest-v2` fixes the
contract, `founder-economy-simulator-v3` executes it, `cycle-boundary-v1` fixes
the window grid, and `uptime-measurement-v1` produces the record — and all four
say, in their own words, that they assign no canonical transaction bytes, no
receipt encoding, and no state-root schema, and that the numeric consensus
receipts are requirement 5.

This ADR settles that surface. It covers requirement 5 — canonical state keys,
transaction encodings, and numeric consensus receipt codes for seat activation,
permission evaluation, permission exercise, referral issuance, and capped direct
issuance — and requirement 6, the exact compatibility boundary against accepted
M1 transaction bytes, state, and roots. The two are one decision because the
boundary is a statement about the encoding and cannot be written before it.

The constraints are not open. `ledger-transition-v1` states that M1 has no
issuance transaction and that "any later issuance requires a new accepted
transition version and native authorization rule". `protocol-primitives-v1`
states that version-one bytes are immutable, that an upgrade may add identifiers
but never reinterpret one, and that "there is no in-place migration of a state
root". The whole economy is issuance, so the question was never whether to
version, but what shape the version takes and how narrow the boundary can be
made.

## Decision

### The version-one transfer is factored, not replaced

Every version-two transaction is a shared 80-byte header, a kind-specific body,
a shared 16-byte trailer, and a 64-byte signature. The header is exactly the
accepted transfer's first 80 bytes and the trailer exactly its last 16, so kind
1's 40-byte body reproduces the accepted 136-byte unsigned and 200-byte signed
transfer byte-for-byte.

This was discovered rather than designed: every field a new kind needs in common
— the chain it binds, who signed it, its replay key, what it will pay, and when
it expires — is already in the version-one transfer, in one place, in an order
that splits cleanly around the transfer-specific middle. The alternative was a
second envelope for economy transactions, which would have given the same fields
two layouts and made the compatibility claim a comparison of two schemas rather
than an identity.

Three consequences follow and are the reason the factoring is worth stating as a
decision rather than an implementation detail.

The **schema version stays `1`**, because the 80 bytes it versions do not
change. Adding a kind identifier is precisely what `protocol-primitives-v1`
permits.

The **signing and transaction-ID labels are not re-versioned**. The kind byte and
the chain ID are both inside every signature preimage, so a signature cannot
cross a kind or a chain. A version-two label would add no separation the
preimage does not carry and would destroy the kind-1 byte identity for nothing.

The **version-one result codes 0 through 8 apply to all six kinds** with their
exact meanings. They are envelope conditions rather than transfer conditions —
fee limit, expiry, sender existence, nonce, and balance are properties of the
shared header and trailer — so the new codes extend contiguously from 9 rather
than opening a second range per kind.

### Eight rejection conditions are removed by reading state instead of input

The evaluation transaction names a seat and a cycle index and nothing else. The
window is derived from the seat's recorded activation height, and the record for
that window is state the uptime pipeline finalised.

That makes ten of the economy model's twenty-four result codes unrepresentable,
and the reason is uniform: their input does not exist. A supplied uptime record
is an opinion, and `MISSING_UPTIME_RECORD`, `INVALID_UPTIME_RECORD`,
`INCONSISTENT_UPTIME_RECORD`, `SEAT_NOT_IN_SCOPE`, and
`INCOMPLETE_UPTIME_RECORD` exist to bound what an opinion may claim. The model's
`bound_uptime_records` map exists so that a window's uptime is one fact for a run
rather than a per-event opinion; a chain has one finalised record per window and
one fact by construction. The three window codes go the same way because the
window is derived. `HEIGHT_RANGE` and `HEIGHT_NOT_MONOTONIC` go because the
activation height is the executing block height, which ordered block execution
already fixes as the sole successor of the previous height.

Accepting a submitted record was rejected outright. It would have preserved a
one-to-one code mapping and made the encoding a transcription of the model,
while handing a submitter the measurements that decide who is paid.

One condition replaces them. `WINDOW_NOT_FINAL` refuses an evaluation before the
first height of window `w + 2`, which is a condition the model cannot express
because it has no current height.

**The removal is recorded as a total three-way partition of the model's codes —
twelve carried, two guards, ten unrepresentable — with a reason for each.** A
later encoding that reintroduces a supplied record must move a code out of that
table rather than quietly widen an input. Losing a check silently is the failure
this partition exists to prevent, and it is the same discipline
`founder-economy-simulator-v3` applied to its own reachable and guard codes.

The two guards, `ARITHMETIC_OVERFLOW` and `INVARIANT`, get no receipt code.
`ledger-transition-v1` already decides that a checked-arithmetic violation "is an
internal invariant failure that invalidates the proposed block, not a
transaction result", so version two adds nothing and refuses to give a defect a
receipt.

### The winner set is committed at finalisation and carried by the exercise

A failed cycle's Founder portion goes to the highest uptime in that same window,
so the winner set is a property of the window and every seat failing in that
window reallocates to the same set. At finalisation, ordered block execution
writes one window-result entry holding the met bitmap, an ordered Merkle root
over the sorted winner seat IDs, the winner count, and the number of in-scope
seats yet to exercise. An exercise of a failed cycle carries the winner list and
the transition recomputes the root, refusing any list that does not reproduce it.

Two alternatives fail on bounds the accepted artifacts already fix.

**Resolving the legs at evaluation, as the model does, is a population-scale
write.** The model stores one leg per winner inside the pending permission, which
at a fully tied window is 100,000 legs for one evaluation.
`founder-economy-manifest-v2` forbids iterating over all 100,000 seats inside an
unrelated transition, and writing 100,000 entries is worse than iterating.

**Computing the set lazily, at the first failed evaluation in a window, does not
survive the retention bound.** `uptime-measurement-v1` retains two windows of
bitmaps and a seat may exercise arbitrarily later, so the evidence would already
be gone. Committing at finalisation is what lets that specification's
`RETAINED_WINDOWS = 2` bound stand unchanged; the lazy design would have
silently required unbounded retention in a neighbouring specification, which is
exactly the kind of cross-model consequence that is invisible when each
specification is read alone.

The cost is transaction size and no state: 400,170 bytes for a fully tied
window, inside the 1,048,576-byte object bound. That is the dominant resource
cost of the encoding and is stated rather than discovered later, because the
constitution expects ties at a perfect cycle to be "the ordinary case", so the
large list is the common case rather than an adversarial one.

A compact complement encoding would be far smaller in exactly that case and is
deliberately refused: two encodings of one set is the non-minimal representation
`protocol-primitives-v1` forbids. The commitment is an ordered Merkle root rather
than a flat hash so that a later version can add a per-winner claim path with a
logarithmic membership proof without changing the committed value. Whether a
winner is credited by the failed seat's exercise or claims its own share changes
what a participant must do in order to be paid, so it is not decided here.

### A pending permission holds one byte, and the evaluated-key set disappears

The model keeps resolved legs per permission and a separate
`evaluated_permission_keys` set, because a permission is deleted at exercise and
replay must still be refused. Here the legs of a met cycle are the manifest's
five fixed legs, the legs of a failed cycle are four fixed legs plus an equal
split over a set recorded once per window, and the entry is retained after
exercise with its verdict byte replaced by an exercised marker. One entry answers
both the verdict question and the replay question, and the set is not needed.

### A new chain, not a migration

Version-two genesis takes schema version `2`, adds the accepted manifest digest
as a field, and uses a distinct chain-ID domain label, so a Founder Economy chain
has a different chain ID from any M1 chain. The state root takes a distinct label
and version field, so no version-one root is reinterpreted and no version-two
root collides with one over an identical account set and an empty economy.

An upgrade block committing a last old root and a first new root was the
alternative. It was rejected because it buys nothing here: there is no M1 state
worth carrying — the devnet's four bootstrap accounts hold a configured devnet
supply under a different denomination and a supply limit the constitution
replaces — and it would have required migration vectors, rollback behavior, and
a replay rule across the boundary for a state nobody needs to keep.
`protocol-primitives-v1` names the new-genesis path explicitly: "a different
genesis creates a different chain ID; it is not a migration of this chain."

Binding the manifest digest into genesis is what makes the founder-directed
contract part of chain identity. A chain whose channel caps differ is a different
chain rather than the same chain with a different table.

### Three genesis relaxations, each forced

Version two permits `total supply` zero, `account count` zero, and a zero fixed
fee. The first two are forced by the constitution: "there is no founder-directed
genesis allocation: native units enter circulation only through Founder Node
issuance permissions and capped direct-mint channels." Version one requires both
to be nonzero, so a conforming Founder Economy chain cannot open under version
one's genesis rules.

The third follows from the first two and is the finding this decision did not
expect. **With a zero allocation and a nonzero fee, no account can pay for the
first transaction, so no transaction can execute and the chain can never reach a
state in which any fee is payable.** Every path out is external — seat purchases
are made in BTC, ETH, or an approved stablecoin through the restricted bridge,
which is a later milestone. A zero fee makes a devnet runnable and states the
dependency honestly; it does not decide the production fee policy, which sets
what a user must pay.

### Three authorization predicates are named and none is defined

Every kind is signed by an account and charges it the fixed fee, which the
constitution decides applies to "an issuance exercise, or another accepted state
transition". Which sender each kind accepts is `activation_authority` for kind 2,
`seat_authority` for kinds 3, 4, and 5, and `direct_issue_authority` for kind 6.
A refused sender is `UNAUTHORIZED`.

**All three are founder-reserved and none is filled.** Which senders a predicate
accepts sets what an end user must do and own in order to participate and be
paid. The constitution decides that a sensitive Founder action requires an
accepted signature and a fresh action-bound biometric approval, and
`founder-economy-simulator-v3` records that what authorizes an activation — the
payment, enrollment, and biometric preconditions — is M4. Neither says which key
signs which transaction.

Kind 6 goes further and is **specified but not activated**: a conforming chain
refuses every kind 6 with `UNAUTHORIZED`. `founder-economy-manifest-v2` may keep
`direct_channel_eligibility_result` as a research placeholder because a research
model may carry an unverified input. A consensus transition may not, because it
must decide what it actually verifies, and this is the point the M3.7a handoff
predicted the placeholder would try to cross into consensus. Refusing the kind is
conservative and reversible; inventing a predicate is not.

The vectors record the unreachability of kind 6's five inner conditions as a
derived property, so an implementation that activates the kind without the
founder decision fails a check rather than passing silently.

## Consequences

Requirements 5 and 6 are satisfied as specification. The per-seat-balance and
recipient-balance parts of requirement 12 are answered as a consequence of fixing
the state keys, which completes requirement 12.

The economy is now **encodable and not operable**. Until `activation_authority`
and `seat_authority` are decided, no seat can be activated and no permission can
be evaluated, exercised, or accrued on a conforming chain. This is the first
genuinely blocking founder question of M3, and it arrives one slice earlier than
the M3.7a handoff predicted: that handoff expected direct-channel eligibility to
block requirement 10, and it does, but seat authorization blocks it more broadly
and was not previously classified as reserved.

Ten of the economy model's result codes become unreachable, which is a narrowing
of the input surface rather than a loss of checking. The model keeps them and
stays correct about the contract it states; nothing accepted is edited.

One storage bound is not a constant. The number of retained window results is the
number of windows inside some activated seat's span that still hold an
unexercised cycle: 731 entries and about 9.2 MB if every seat activates in one
window, and `W + 731` if activations span `W` windows, which the constitution
does not bound. Growth is about 4.6 MB per year at the pinned commit interval.
Requirement 15's independent review should see this figure.

The exercise transaction reaches 400,170 bytes for a fully tied window. It fits
the canonical object bound, and whether it fits a block under adversarial load is
a question for requirement 13.

No accepted artifact changes. `simulation/founder_economy*/`,
`simulation/cycle_boundary/`, `simulation/uptime_measurement/`,
`simulation/escrow_payout/`, and `simulation/scenarios/` are untouched, every
recorded vector file is byte-for-byte unchanged, and no M1 account, fee pool,
height, transaction root, receipt, state root, SQLite database, ABCI response, or
CometBFT validator is affected.

## Compatibility and independent review

The compatibility boundary is stated exactly in the specification and is proved
rather than asserted: the vectors require the version-two encoder to reproduce
the accepted `protocol-primitives-v1` transfer bytes and transaction ID
byte-for-byte, and require a version-one and a version-two state root over an
identical account set and an empty economy to differ.

Three claims are design intent rather than proof and belong to requirement 15's
independent review.

**That the encoding is complete for the transitions it names.** It is checked
against `founder-economy-simulator-v3` by a total code mapping, which shows that
no model condition was dropped without a reason. It is not checked against an
implementation, because none exists; requirement 11 is where a C++ and a Python
implementation must agree on fixed bytes, and a defect the mapping cannot see
would surface there.

**That the resource bounds are adequate.** The window-result growth and the
400,170-byte exercise are derived at full capacity under the founder-directed
schedule, not under an adversary choosing the worst arrival pattern.

**That refusing kind 6 is sufficient containment.** It prevents issuance on four
channels whose eligibility is undecided. It does not prevent the specification
from being read as an endorsement of the encoded shape, and the eligibility
decision may well change the fields.

ADR 0027 and ADR 0028's five open review items are inherited unchanged. Encoding
a record's consequences does not make the record sound.
