# ADR 0021: Escrow payout capabilities and custody conservation

- Status: Accepted for M2 simulation; not a consensus activation
- Date: 2026-08-04

## Context

`m2-founder-economy-proof.md` requirement 11 asks for separate venture, community-grant, and
developer escrows whose balances cannot be spent through the issuance
capability and whose accepted payouts cannot exceed available custody.

The Founder Constitution funds those three escrows from Founder Node issuance,
states that unused escrow value remains available indefinitely and is not
burned, expired, or swept, and gives the Ecosystem AI authority to evaluate
proposals, define milestone and tranche plans, release bounded funds, pause
work, and terminate future funding. It bounds that authority twice: the AI can
spend only native units already held by the exact delegated escrow and must
reduce, counteroffer, queue, or reject a request it cannot fund; and one logical
AI authority must never hold one unrestricted key, so each role needs a
separate, amount-bounded, replay-safe capability. It leaves the AI funding
framework, approval thresholds, and milestone policy explicitly unresolved.

Charter invariants 11 and 12 restate the same boundary: AI actions enter through
signed, replay-safe, capability-scoped envelopes bounded by exact escrow,
amount, policy, and expiry rules, and one authority never receives an
unconstrained mint, treasury, bridge, content, and upgrade key.

Six questions had to be settled before implementation:

1. whether payouts extend the accepted economy simulator or form a new model;
2. where escrow custody comes from, if not from an issuance transition;
3. what a spending capability is bounded by;
4. whether a capability's envelope may exceed the escrow's current custody;
5. what happens when authority and funds are both insufficient; and
6. how much of the unresolved AI framework must be invented to make a payout
   testable.

## Decision

### A separate model, not an economy-simulator extension

Implement `simulation/escrow_payout/` with its own schema, state, digests, and
vectors. `founder-economy-manifest-v1`, `founder-economy-simulator-v1`,
`founder-seat-schedule-v1`, and `revenue-routing-v1` are unchanged.

The economy simulator credits escrow custody through `credit_custody` and has
no spend transition. Its invariant is `typed custody == issued supply`, which
holds only because custody there can never fall. Adding a payout would falsify
that invariant and break the schema ADR 0018 froze, in order to co-locate two
accounting systems whose only shared quantity is a starting balance.

This repeats the shape chosen for `revenue-routing-v1` and for the same reason:
a model that moves already-issued value shares no cap, no permission, and no
supply term with the model that issued it.

### Opening custody is bound to a recorded economy state by digest

`bind_opening_custody` accepts a complete recorded
`founder-economy-simulator-v1` canonical state value together with its recorded
digest, recomputes that model's `state-v1` digest over the supplied value, and
reads the three `{escrow_id}:global` custody keys only after the digests agree.
Each derived amount is additionally required to be at or below that escrow's
manifest cap.

The alternative was to accept three opening amounts as plain parameters. That
would have left the opening custody as three numbers with no stated origin.
Recomputing the digest ties them to a complete economy state, at the cost of
carrying that state into the fixture, which is a research file where verbosity
is free.

The recomputation proves consistency, not provenance: a self-consistent invented
state would also pass, because its digest can be computed as easily as a real
one. Provenance is established one level up, where the normative vectors record
the digest and the verifier derives it by running the economy simulator on its
accepted fixture. Inside the model, the defence against an invented state is the
manifest cap, which rejects an opening amount above the escrow's constitutional
bound however consistent the supplied state is. Stating this split matters: a
digest check that is described as proving more than it does is worse than no
check, because it invites the reader to stop looking.

The economy label is read and never written. This model produces no economy
state and changes no economy digest.

### A capability is bounded by a per-payout maximum, a cumulative envelope, an escrow, and an expiry

Two amount bounds are kept rather than one because they fail differently. The
per-payout maximum bounds a single mistaken or malicious release; the envelope
bounds the total authority delegated, so repeated correct-looking releases still
stop at a stated sum. A capability whose per-payout bound exceeded its envelope
would make the first bound unreachable, so that shape is rejected outright.

The escrow binding is what makes containment structural: a payout naming any
other escrow is `ESCROW_MISMATCH`, and each escrow keeps its own custody, its
own paid-out total, and its own recipient balances, so no expression in the
model reads two escrows' custody together.

Expiry and revocation bound authority in time without touching value. Custody
is never burned, expired, or swept — the constitution is explicit that unused
escrow value stays available indefinitely — so expiry is deliberately a property
of the capability record and never of a custody amount.

### An envelope may exceed current custody; the custody check belongs to the payout

A grant does not reserve funds and is not rejected for being larger than the
escrow's balance. The constitution requires the AI to reduce, counteroffer,
queue, or reject a request it cannot fund, so an under-funded delegation must be
expressible and must fail when spending is attempted.

The rule is that the envelope bounds authority and custody bounds value, and
both are checked at payout. Rejecting large grants instead would have moved a
funding decision into the delegation step and made a queued proposal
unrepresentable.

### Authority is checked before funds

The payout conditions are evaluated in one fixed order, and every authority
condition — replay, unknown capability, escrow mismatch, revocation, expiry,
zero amount, approval — precedes both bound checks, which precede the custody
check.

A request that is both unauthorized and unfunded therefore reports the
authority failure. Besides giving one deterministic code per event, this means a
holder of a capability bound to the wrong escrow learns nothing about that
escrow's balance, so the rejection order is not an oracle.

`ENVELOPE_EXCEEDED` and `INSUFFICIENT_CUSTODY` stay distinct codes because
exhausting delegated authority and exhausting the escrow are different
operational events that a later AI framework must handle differently.

### Custody accounting and capability accounting are reconciled independently

Each escrow satisfies `opening = available + paid_out`, and `paid_out` must
equal both the sum of that escrow's recipient balances and the sum of `spent`
across the capabilities bound to it.

The third equation is a second, separately maintained account of the same value.
A payout that moved value without charging an envelope, or charged an envelope
without moving value, is an invariant failure rather than a silent divergence.

### The AI evaluation stays a supplied research input

`execute_payout` consumes an `approval_result` bound by `payout_id` to the exact
release it authorizes, carrying only `approved` or `rejected` and an opaque
evaluation reference. A withheld approval is its own result code so the trace
records that a rejection was supplied rather than derived.

The evaluation criteria, milestone and tranche plan, approval thresholds,
negotiation, pause, and termination rules are explicitly unresolved founder and
AI-framework decisions. Inventing any of them to make a test pass would convert
a research fixture into policy, so the approval is the weakest input that still
allows custody conservation and capability containment to be proved. It decides
only whether a release proceeds, never an amount, a bound, or which escrow is
charged.

## Alternatives not selected

- **Add a payout transition to `founder-economy-simulator-v1`:** breaks the
  frozen schema and falsifies its `typed custody == issued supply` invariant to
  merge two accounting systems that share only a starting balance.
- **Take opening custody as three plain amounts:** simpler fixtures, but the
  claim that no unit enters except through a constitutional channel would rest
  on the fixture author rather than on a checked digest.
- **Re-run the economy simulator inside this model to obtain custody:** couples
  the two models' event schemas, makes this model's result depend on the other's
  fixture, and would rerun an accepted simulation to learn three numbers a
  digest already fixes.
- **One capability per escrow, created implicitly at bind:** removes the grant
  transition, but then delegated authority has no stated total, no expiry, and
  no revocation, which is precisely the unconstrained standing key charter
  invariant 12 forbids.
- **A single capability spanning all three escrows with a shared envelope:**
  would let a compromised venture workflow reach the developer escrow, and would
  replace three independent conservation equations with one that cannot
  distinguish them.
- **Only a cumulative envelope, with no per-payout bound:** a single erroneous
  release could drain the entire delegation, and the constitution's requirement
  for amount-bounded capabilities reads more naturally as bounding the action,
  not only the programme.
- **Only a per-payout bound, with no envelope:** bounds one mistake but permits
  unlimited repetition, so the delegated total would be unstated.
- **Reject a grant whose envelope exceeds current custody:** moves a funding
  decision into the delegation step and makes a queued or staged proposal
  unrepresentable, contradicting the constitutional instruction to queue rather
  than refuse outright.
- **Reserve or lock custody at grant time:** would let idle delegations strand
  value that the constitution says stays available, and would require an
  unlocking rule with its own expiry semantics.
- **Check custody before authority:** turns the rejection order into a balance
  oracle for a caller holding a capability that cannot spend the escrow.
- **A single `PAYOUT_REJECTED` code:** loses the operational distinction between
  exhausted authority and exhausted funds, which a later AI framework must treat
  differently.
- **Expire or sweep unused custody after some period:** directly contradicts the
  constitutional rule that unused escrow value is not burned, expired, or swept,
  and would need a substitute beneficiary no founder decision supplies.
- **Model the AI evaluation, thresholds, or tranche schedule now:** every one of
  those is an explicitly deferred founder or AI-framework decision.
- **Allow a payout to name no capability, authorized by a signature alone:** is
  the unconstrained key the charter forbids, and would make containment
  untestable.

## Consequences

- Requirement 11 becomes an executed derivation: separate escrows, payouts that
  cannot exceed available custody, and a spending path with no issuance
  capability anywhere in it.
- Custody is fixed at bind and non-increasing thereafter, because
  `bind_opening_custody` is the only writer of a custody amount and rejects once
  bound. "Cannot be spent through the issuance capability" is therefore a
  property of the model's shape, not an assertion in a test.
- Three conservation equations sharing no term make cross-escrow containment
  structural, and a second capability-side account of the same value makes a
  divergence between authority and custody an invariant failure.
- No native units are created, so the 55,743,940,100-unit maximum, every channel
  cap, and the accepted economy, seat, and routing vectors are untouched.
- Opening custody is tied to a `founder-economy-simulator-v1` state by digest —
  the first join among the M2 models, and a one-way read that changes nothing in
  the other. The model checks that the supplied state matches the digest it
  claims; the verifier is what establishes that the digest is an accepted
  economy run. Neither step alone is the whole claim, and the split is
  deliberate rather than incidental.
- The fixture carries a complete economy state value, so a future change to the
  economy model's canonical state shape would invalidate this model's binding
  fixture and vectors. That is intended: the binding is meant to break loudly
  rather than silently accept stale custody.
- An approval remains a fixture. Nothing here shows that a proposal was
  evaluated well, that a threshold is safe, that a milestone plan is
  appropriate, or that a recipient is legitimate.
- A capability is modelled as a record, not as a signed envelope. The signature
  scheme, replay domain, and encoding that would carry one on a real chain are
  not defined here.

## Compatibility and independent review

This ADR accepts a research model contract. It activates no consensus
transition, creates no native units, and its error codes are simulator result
codes rather than consensus receipts.

M3 must separately define the signed capability envelope and its replay domain,
the cycle boundary in heights or epochs, the AI decision receipt and audit
trail, the storage bound on recipient balances, the path by which a credited
recipient balance becomes a spendable account, and the consensus receipts and
numeric codes. Exact custody arithmetic is not treasury safety, and independent
economic, protocol, and AI-authority review remains required before any
production escrow releases value.
