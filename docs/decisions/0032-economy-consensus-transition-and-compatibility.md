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

**A first draft of this decision was written before the founder answered.** It
named three authorization predicates and defined none, and it therefore had to
guess at the shape of the transitions those predicates would govern. It guessed
wrong in three places, and this ADR records both the guesses and why the answers
replaced them, because the difference is the clearest evidence available of what
the founder-decision gate is for.

## The founder decision of 2026-08-13

The owner settled the reserved questions:

- a seat is **purchased** in one atomic transaction that registers its biometric
  hash and the purchaser's address, and cannot be purchased without an off-chain
  biometric verification signature;
- **activation** is a separate, one-time, permanent event the purchaser triggers
  themselves, also biometric-gated, and it is what starts the 731 cycles;
- while a node is up, the chain **writes mint permissions daily by itself**,
  based on whether the cycle's requirement was met; no one submits anything;
- **minting takes everything** — one button, every accumulated permission, no
  quantity choice — and there is no other way native units reach a founder;
- **referral is a separate pool** on a separate button, accruing daily through
  the direct-mint channel regardless of any node's activity, and paid to a user
  account rather than to a seat; and
- minting needs only the wallet signature; the biometric gate is for entry.

The owner delegated the mechanism, naming, and structure explicitly.

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

Three consequences follow. The **schema version stays `1`**, because the 80
bytes it versions do not change. The **signing and transaction-ID labels are not
re-versioned**, because the kind byte and the chain ID are both inside every
signature preimage. The **version-one result codes 0 through 8 apply to all six
kinds** with their exact meanings, because fee limit, expiry, sender existence,
nonce, and balance are properties of the shared header and trailer rather than
of a transfer.

This part of the first draft survived the founder decision unchanged, and it is
the half of the slice that was never at risk: it is a statement about accepted
bytes, derivable without knowing anything about who may act.

### No transaction records a cycle

The chain writes each cycle's outcome itself, at a block boundary, for every
in-scope seat at once. Nothing is claimed, reported, or evaluated by a
submitter.

The first draft had a submitted `evaluate_base_permission` transaction and it
was wrong. The founder rule removes an authorization question rather than
answering it: a transition nobody submits has no sender to authorize, no fee to
charge, and no dependence on an operator remembering to act. It also removes
five of the model's rejection conditions outright, because a record nobody
supplies cannot be missing, invalid, incomplete, inconsistent, or out of scope.

**The two-cycle lag is forced.** A cycle's uptime is not final until its
Ecosystem AI dispute window expires, which `uptime-measurement-v1` fixes at the
whole of the following window, so the earliest height at which a cycle's outcome
is known is the first height of the window after that. Assigning earlier would
assign against a result a dispute could still change; the alternatives are to
remove the dispute window, which the constitution requires, or to assign
provisionally and revise, which would make a mint's value depend on when it
happened. The lag costs at most two cycles of delay on value that is never lost.

### One record per cycle, with two bitmaps

Each cycle's assignment record holds the per-winner share, the winner count, the
in-scope count, a met bitmap, and a winner bitmap — 25,033 bytes at the
100,000-seat capacity. A seat reads two bits per cycle when it mints.

This replaces the first draft's winner commitment, and the founder rule is what
forced the replacement. Under "mint takes everything", a founder with fifty
saved failed cycles would settle fifty windows in one transaction. The draft's
design had the exercise **carry** the winner list, which is 400,170 bytes for one
fully tied window and would have been fifty times that. Making the set readable
from state instead means the largest transaction in version two is 325 bytes and
no transaction carries anything that scales with the population.

Two alternatives were considered and rejected for reasons the accepted artifacts
already fix. **Crediting each winner at assignment** is 100,000 state writes for
one failed seat, and `founder-economy-manifest-v2` forbids iterating over all
100,000 seats inside a transition, let alone writing to them. **Computing the
winner set lazily**, at the first mint that needs it, does not survive
`uptime-measurement-v1`'s two-window retention bound, because the evidence would
already be pruned; committing at finalisation is what lets that specification's
storage bound stand unchanged.

### The per-seat-cycle population leaves the state entirely

A seat carries one `minted_through_window` high-water mark. There is no
pending-permission entry, no per-cycle replay key, and no set of exercised keys.

**This is the largest single consequence of the founder decision on this
encoding.** The first draft stored one verdict byte per seat-cycle — 73,100,000
entries, about 585 MB, plus 512 MB of referral accrual keys — because a mint that
names a cycle needs somewhere to record that this cycle was taken. A mint that
cannot take a chosen amount needs only to record how far it has taken, and the
mark is both the bookkeeping and the replay protection. The same rule collapses
referral accrual to one accrued-versus-minted pair per referrer.

A design in which a founder could mint a chosen quantity could not have this
property, which is worth recording: the founder rule was given as a product
decision and it is also the reason the state is bounded.

### The biometric signature gates entry and never payment

Kinds 2 and 3 carry an Ed25519 signature by a genesis-configured ecosystem
verifier key over a domain-separated message binding the chain, the seat, the
purchaser, and an expiry. Kinds 4 and 5 carry no second factor.

The message binding is what makes the approval "fresh, action-bound" in the
constitution's sense, expressed as bytes: a verifier signature cannot be replayed
onto another seat, purchaser, chain, or attempt. No image, template, or linkage
datum enters consensus — only a hash and a signature over it — which is what the
constitution requires when it says raw biometric data must not become ordinary
public blockchain data.

Putting the gate on entry alone is the containment direction the constitution
insists on. If the verifier is unavailable, no new seat can be bought or
activated and **every existing seat keeps earning and minting**. Requiring a
biometric approval per mint was offered and refused: it would make an off-chain
service a precondition for income, which is exactly the ownership the
constitution's dispute-window design exists to prevent. A stolen wallet key can
mint, and it can only mint to the seat's own recorded account, so it redirects
nothing.

The verifier key is genesis state rather than a constant, so it sits inside the
chain ID: a chain trusting a different verifier is a different chain. No
transition rotates it, because rotation decides who controls admission and that
rule does not exist yet.

### A new chain, not a migration

Version-two genesis takes schema version `2`, adds the accepted manifest digest
and the verifier key as fields, and uses a distinct chain-ID domain label. The
state root takes a distinct label and version field, so no version-one root is
reinterpreted and no version-two root collides with one over an identical
account set and an empty economy.

An upgrade block committing a last old root and a first new root was the
alternative. It was rejected because it buys nothing: there is no M1 state worth
carrying — the devnet's four bootstrap accounts hold a configured devnet supply
under a different denomination and a supply limit the constitution replaces — and
it would have required migration vectors, rollback behavior, and a replay rule
across the boundary for a state nobody needs to keep.

### Three genesis relaxations, each forced

Version two permits `total supply` zero, `account count` zero, and a zero fixed
fee. The first two are forced by the constitution: native units enter circulation
only through issuance channels, so a conforming chain must be able to open with
nothing allocated, which version one forbids.

The third follows from the first two and is the finding this decision did not
expect. **With a zero allocation and a nonzero fee, no account can pay for the
first transaction, so no transaction can execute and the chain can never reach a
state in which any fee is payable.** Every path out is external, and the bridge
is a later milestone. A zero fee makes a devnet runnable and states the
dependency honestly; it does not decide the production fee policy.

### Kind 6 is specified and refused

`direct_issue_authority` is the one predicate still reserved. A conforming chain
rejects every kind 6 with `UNAUTHORIZED`.

`founder-economy-manifest-v2` may keep `direct_channel_eligibility_result` as a
research placeholder because a research model may carry an unverified input. A
consensus transition may not, because it must decide what it actually verifies,
and this is the point the M3.7a handoff predicted the placeholder would try to
cross into consensus. Refusing the kind is conservative and reversible; inventing
a predicate is not. The vectors record the unreachability of the kind's five
inner conditions, so an implementation that activates it without the founder
decision fails a check rather than passing silently.

## Consequences

Requirements 5 and 6 are satisfied as specification. The per-seat-balance and
recipient-balance parts of requirement 12 are answered as a consequence of fixing
the state keys, which completes requirement 12.

Eleven of the economy model's twenty-four result codes become unreachable, and
the mapping is recorded as a total three-way partition — eleven carried, two
guards, eleven unrepresentable — with a reason for each. That is a narrowing of
the input surface rather than a loss of checking: the model keeps its codes and
stays correct about the contract it states, and nothing accepted is edited.

The encoding is now bounded in every direction that scales with the population.
The largest transaction is 325 bytes, no transition writes per-seat state at a
cycle boundary, and the per-seat-cycle population is absent from the state.

One bound is not a constant and it is the weakest result in the slice. Cycle
assignment records accumulate at one per cycle and are never deleted, because a
seat may mint at any time and must be able to walk every cycle it has not
collected: 25,033 bytes per cycle at capacity, about 9.1 MB per year at the
pinned commit interval. Expiring an uncollected cycle would bound it exactly and
would decide a seat's entitlement by inaction, which the constitution does not
do; pruning past every seat's mint does not help, because one seat that never
mints holds everything after its own last mint. A run-length encoding of the
ordinary all-ones day would shrink the common case by a large factor and is the
option worth revisiting, but it must be the record's *single* canonical form
rather than a second one, because two encodings of one record is the non-minimal
representation `protocol-primitives-v1` forbids.

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
identical account set and an empty economy to differ — after first requiring the
version-one construction used in that comparison to reproduce the accepted
account, state, and transaction roots, so the non-collision is not trivially
true.

Four claims are design intent rather than proof and belong to requirement 15's
independent review.

**That the encoding is complete for the transitions it names.** It is checked
against `founder-economy-simulator-v3` by a total code mapping, which shows that
no model condition was dropped without a reason. It is not checked against an
implementation, because none exists; requirement 11 is where a C++ and a Python
implementation must agree on fixed bytes, and a defect the mapping cannot see
would surface there.

**That the cycle-assignment growth is acceptable.** It is derived at full
capacity under the founder-directed schedule, and its worst case is set by
operator behavior rather than by a rule.

**That the verifier key is a safe single point of admission.** It gates entry and
not payment, which bounds the damage, and it cannot be rotated, which bounds the
remedy. Both facts are recorded; neither is reviewed.

**That refusing kind 6 is sufficient containment.** It prevents issuance on four
channels whose eligibility is undecided. It does not prevent the specification
from being read as an endorsement of the encoded shape, and the eligibility
decision may well change the fields.

ADR 0027 and ADR 0028's five open review items are inherited unchanged. Encoding
a record's consequences does not make the record sound.
