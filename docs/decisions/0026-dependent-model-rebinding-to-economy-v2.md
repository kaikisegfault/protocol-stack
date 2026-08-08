# ADR 0026: Rebinding the dependent models to founder-economy-simulator-v2

- Status: Accepted
- Date: 2026-08-08

## Context

[ADR 0024](0024-founder-economy-manifest-v2.md) accepted
`founder-economy-manifest-v2` and [ADR 0025](0025-founder-economy-simulator-v2-transitions.md)
made it executable. Four accepted M2 models were built against version one, and
requirement 3 of [`first-goal.md`](../project/first-goal.md) requires them
re-verified against version two with every recorded digest regenerated and every
verifier still failing closed.

Two of the four are coupled and two are not. That was re-proved by inspection
rather than inherited from the handoff:

- `simulation/escrow_payout/` imports the v1 economy contract, pins
  `protocol-stack:founder-economy:state-v1`, and derives its three escrow caps
  from the v1 channel table.
- `simulation/scenarios/` imports the v1 economy engine, manifest loader, and
  contract, and `tools/scenario-suite-vectors/expected.py` hard-codes the
  superseded maximum supply and referral leg.
- `simulation/founder_seats/` imports only `simulation/common/canonical.py` and
  carries no supply or channel figure.
- `simulation/revenue_routing/` likewise imports only
  `simulation/common/canonical.py` and carries no supply figure.

This ADR records the decisions for the escrow payout model. The scenario suite
is the following slice and will extend this record rather than restate it.

## Decision

### Rebinding is a new version, not an edit

`escrow-payout-v1.md` fixes its schema strings, field sets, escrow set, caps,
research-input shapes, state shape, journal buckets, digest labels, error codes,
and rejection order as immutable for version one, and requires a new schema and
ADR for a change to any of them. The economy state a bind accepts is one of
those research-input shapes.

`escrow-payout-v2` is therefore accepted as a separate contract, and
`escrow-payout-v1.txt` is retained unedited and passing. The alternative —
editing version one in place and regenerating its digests — was rejected because
it would make one label name two different contracts across the repository's own
history, which is precisely what ADR 0024 established version labels to prevent.

### One implementation, selected by a `Binding`

The two versions differ in exactly six strings. Every transition, rejection
condition, rejection order, journal bucket, and invariant is identical.

The alternatives considered were:

1. **A sibling `simulation/escrow_payout_v2/` package**, mirroring how
   `founder_economy_v2` sits beside `founder_economy`.
2. **A `Binding` record selecting the six strings, with one shared
   implementation** — the selected option.
3. **Edit version one in place**, rejected above.

Option 1 was rejected on drift. `founder_economy_v2` earned a separate package
because its transition set genuinely changed shape: a removed permission kind,
two removed research placeholders, a new derived winner set. Duplicating roughly
a thousand lines of identical payout, capability, expiry, and conservation logic
to vary six strings would create two copies of rules that must stay identical,
with no mechanism to notice when they stop being identical. The repository's
engineering rules prefer cohesive modules and warn against fragmenting coherent
logic.

Option 2 keeps one copy of the rules and makes the difference between versions
enumerable in a single table. The one version-specific transition,
`bind_opening_custody`, receives the binding explicitly; the other four are
shared without a parameter, so a future version needing a second version-specific
handler would have to say so in `handlers_for`, where it is visible.

The consequence accepted with option 2 is that the two versions cannot diverge
in behavior without a code change that affects both. That is the intended
property here and would become the wrong one if a version three revised a payout
rule; at that point option 1 becomes correct for the diverging transition.

### The scenario is held fixed so the rebinding is auditable

`research-events-v2.json` is the v1 scenario with only its four embedded
founder-economy states rebound. Every capability, payout, approval fixture, and
adversarial probe is carried over unchanged.

The alternative was to author a fresh v2 scenario exercising the new economy's
seat population. It was rejected because it would have changed the evidence and
the binding at once: a differing trace could then mean either a rebinding defect
or an intended scenario difference, and no test could tell them apart.

Holding the scenario fixed makes the equivalence assertable, and it is asserted
rather than assumed: the two runs must produce identical result codes for all 39
events in identical order, and their final states must differ in exactly one
member, `bound_state_digest`. A rebinding that altered a payout rule would still
produce a self-consistent vector file, so this is the check that catches it.

### The shared cap table is licensed by a derived check

Both accepted economy contracts give identical caps for the three escrows,
because ADR 0023 raised the maximum supply through the `founder_referral`
channel alone. One cap table therefore serves both bindings.

That agreement is recorded as a derived vector and asserted in tests rather than
left as a comment, so a future revision that moved an escrow cap would fail
instead of being absorbed. `bind_opening_custody` reads the cap from the binding
rather than from the module default, because it is the one transition whose
meaning is version specific.

### Cross-version binds reuse `INVALID_RESEARCH_INPUT`

No new error code is introduced. A cross-version state is exactly a state whose
supplied digest is not the recomputed one, which version one already rejects
with `INVALID_RESEARCH_INPUT`.

A distinct code such as `WRONG_ECONOMY_VERSION` was considered and rejected: the
model cannot distinguish a foreign-version state from a corrupted one without
attempting a second digest under every known label, which would make the set of
accepted provenances grow with every future version.

## Consequences

- `simulation/escrow_payout/` implements two accepted contracts. Version one's
  fixture, vector file, digests, and 57 tests are byte-for-byte unchanged and
  continue to pass, which the diff shows directly.
- `tools/escrow-payout-vectors/verify.py` gains `--version`, defaulting to `v1`.
  Each version loads only its own economy model, so neither can silently satisfy
  the other's binding.
- `test-vectors/escrow-payout-v2.txt` records 172 values: version one's 169
  under v2 labels and digests, plus three derived compatibility values.
- `simulation/scenarios/` still binds version one of both the economy and the
  escrow model, and now names that binding explicitly as `c.V1` rather than
  relying on a module default. Its recorded digests remain evidence about the v1
  contracts until the next slice rebinds it.
- The Founder Seat sale and revenue routing models are unchanged, because
  neither imports the economy model nor carries a supply or channel figure.
- No C++, consensus, devnet, bridge, wallet, AI, biometric, or resource behavior
  changes. The model activates nothing and issues no native unit.

## Compatibility and independent review

Version two coexists with version one. All five of the escrow model's own domain
labels end in `-v2`, so no digest computed under one version can be replayed as
the other, and the bound economy label makes the two provenances disjoint in
both directions.

This slice proves that the escrow accounting is unchanged under a different
economy binding. It proves nothing new about escrow policy: not that a recipient
is legitimate, that an AI evaluation is well made, that an approval threshold is
safe, or that recipient balances are bounded at 100,000 seats. Those limits are
stated in `escrow-payout-v1.md` and are unchanged. No independent security
review has occurred.
