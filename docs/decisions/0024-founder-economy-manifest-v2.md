# ADR 0024: A second Founder Economy manifest rather than an edited first one

- Status: Accepted
- Date: 2026-08-08

## Context

[ADR 0023](0023-founder-decisions-activity-referrals-and-supply.md) recorded the
2026-08-07 founder decisions: the maximum supply became 56,993,950,100 display
units, the Founder referral doubled to 34.2 units per cycle, became
unconditional, and moved to the direct-mint group, and unreferred seats fund a
monthly performance pool so the channel is consumed exactly.

That ADR is founder direction. It activates nothing. The accepted
`founder-economy-manifest-v1`, its five verifiers, its four models, and its 133
recorded vectors all implement the superseded figures, and they are the whole of
the M2 evidence.

The first M3 slice therefore had to answer a structural question before any
economic one: what happens to v1.

## Decision

### Version two is a new contract; version one is retained unedited

`founder-economy-manifest-v2` is a separate specification, JSON object, domain
label, canonical byte string, and digest. The v1 specification, manifest,
vectors, verifier, model, and digest are unchanged and still pass.

The alternative was to edit v1 in place: change four numbers and one issuance
kind, regenerate the digest, and carry one contract forward. It was rejected for
three reasons.

The M2 evidence is evidence *about a contract*. A digest is the name of exactly
one byte string, and a specification's claim is that specific values were
verified. Editing v1 would leave the repository asserting that 133 vectors,
107,812 events, and five verifiers proved a contract they never ran against.
That is not a documentation defect; it is a false evidence claim.

The two contracts differ in shape, not only in parameters. v1 has a
`referral_permission` issuance kind, a `referral_permission` top-level object,
and a permission `kind` discriminator over `base` and `referral`. v2 has none of
them. An in-place edit would have been a schema change wearing a parameter
change's clothes.

The retained v1 is also the only artifact that can prove what actually changed.
The v2 vectors derive the supply revision *against* the v1 caps and record that
the maximum rose by 1,250,010,000 display units, that the referral channel rose
by exactly that amount, and that the other nine channels changed by zero. That
check needs both tables to exist.

The cost is two contracts in the tree until the v1 models are retired. That cost
is bounded and visible; a false evidence claim is neither.

### The two versions are separated at the digest, not by convention

The domain label is `protocol-stack:founder-economy:manifest-v2`. Because the
accepted `D(L)` construction commits to the label, no digest computed under one
version can be presented as the other, and the separation does not depend on
anyone reading the schema string first. Each loader rejects the other's
manifest, and a test asserts both directions.

### The channel order follows the constitution's two tables

v1 interleaved the referral channel between the escrow channels and the System
Creator royalty. v2 lists the five Founder Node distribution channels in the
constitution's order, then the five direct-mint channels in the constitution's
order.

Array order is part of the canonical bytes, so this was a real choice rather
than a formatting preference. The alternative — keeping v1's positions and
leaving a direct-mint channel sitting inside the Founder Node run — would have
made the manifest harder to audit against the document it implements, for no
compatibility benefit, since the digest changes either way.

The reordering has an arithmetic consequence worth stating: the
`base_permission` kinds are now exactly the Founder Node subtotal, so
`57,430,000,000 * 73,100,000 = 4,198,133,000,000,000,000` holds as an identity.
The derivation stage checks it, and a manifest that mislabels a direct-mint
channel as `base_permission` is rejected by that check rather than passing
unnoticed.

### The referral is described by destination, not by permission

`referral_benefit` carries the channel, the per-cycle amount, an `unconditional`
boolean, and both beneficiary kinds — `recorded_referrer` and
`unreferred_performance_pool`.

Naming both destinations in the canonical bytes is what makes the exactness
claim machine-checkable. `100,000 x 731 x 34.2 = 2,500,020,000` is only true
because every seat-cycle reaches exactly one of them; a manifest that named one
destination would state a cap it could not consume. A vector records the
remainder as zero, and a negative vector replaces the unreferred destination
with the referred one and requires rejection.

The alternative shape — a `destinations` array with selector strings — was
rejected as more structure than two fixed cases need.

### The activity threshold stays out of the manifest

ADR 0023 fixed a cycle as met at 18 hours or more of cumulative fully
operational uptime with a fragmentable 6-hour allowance. Those constants are not
in the v2 manifest.

The manifest is the monetary and liability contract: what may be issued, to
which channel, against which cap. The activity rule decides *whether* a cycle is
met, not *how much* it is worth, and it is stated in hours, which cannot become
a consensus value until the cycle boundary is defined in heights or epochs.
Putting hours into a canonical digest now would commit a wall-clock quantity to
the contract's identity and force a version three when the boundary is chosen.

The threshold is instead named in the specification prose as an input to the
revised simulator, where it will be fixed alongside the uptime record and the
cycle boundary.

### Three research placeholders are removed, and only one remains

v1 declared four research placeholders. v2 declares
`direct_channel_eligibility_result` alone, covering the four direct-mint
channels whose eligibility the owner has not decided. `founder_referral` is
excluded: its eligibility is the recorded referrer relationship the ledger
already holds.

The array length is part of the canonical bytes, so this is an auditable
statement rather than a comment. A negative vector puts each retired placeholder
back and requires rejection.

Removing a placeholder does not supply the computation that replaces it. The
uptime record, challenge construction, dispute window, and winner rule remain
unspecified, and the specification says so rather than letting an empty
placeholder list imply that activity is now solved.

### The verifier's independence is the constitution, not a second model

The v1 economy verifier derives its values from the loaded manifest and a live
model run. That catches a manifest that disagrees with the model, but not a
manifest and contract table edited together.

The v2 verifier adds a closed-form `expected.py` that imports nothing from
`simulation/` and restates the Founder Constitution's two allocation tables by
hand, in tenths of a display unit, with no floating point. The constitution
states the economy twice — as per-eligible-cycle amounts and as maximum channel
totals — and derives neither from the other. Requiring the two to agree, and
requiring the manifest to agree with both, is a check against the founder
document rather than against a second reading of the specification.

This was confirmed rather than assumed: a forged manifest and contract table
that raise the referral to 34.3 units per cycle and propagate the change
consistently through the referral cap, the direct-mint subtotal, and the maximum
supply pass every loader stage, and are still rejected by four `expected.py`
comparisons.

### Every rejection is executed, not named

The v1 manifest verifier confirms that each recorded failure code is one the
simulator models, and leaves the rejections themselves to the error tests. The
v2 verifier runs the loader over a minimally mutated manifest for each recorded
code, and adds five pairs that carry two defects at once to prove which stage
reports first. A positive control asserts that the same entry point accepts the
unmutated manifest.

## Consequences

- The repository now carries two Founder Economy contracts. v1 is the accepted
  M2 evidence; v2 is the accepted founder direction. Until the revised simulator
  lands, only v1 is executable, and v2 activates nothing.
- The revised simulator is the next slice. It reads v2, drops
  `evaluate_referral_permission` and the permission `kind` discriminator, takes
  a derived activity input and a derived winner set in
  `evaluate_base_permission`, and adds the unreferred performance pool as a
  beneficiary. Every dependent model, vector, and digest — seat, routing,
  escrow, and the scenario suite — regenerates after that.
- `INVALID_PERFORMANCE_ALLOCATION` does not carry forward. It validated a
  supplied allocation list; the winner set is now computed, so its failure modes
  belong to the uptime and winner rules that are still unspecified.
- No C++, consensus, devnet, M1 byte, state root, or accepted v1 artifact is
  modified by this slice.

## Compatibility and independent review

This ADR and the v2 specification fix an economic contract and its canonical
identity. They do not make it a consensus value. No transaction encoding,
receipt code, state key, activation height, or cycle boundary exists yet, and
the v2 loader is research software.

The following remain unreviewed and are not claimed by this decision: that the
uptime scheme resists an adversarial founder with physical machine access, that
the performance winner rule is fair or ungameable, that the unreferred pool's
monthly definition is safe against a seat-timing attack, that the accrued
referral balances at 100,000 seats have a workable storage bound, and that the
revised maximum is economically sound. Each requires the specification work ADR
0023 names, and the security-sensitive ones require independent review that has
not occurred.
