# ADR 0030: Rebinding the escrow payout model to founder-economy-simulator-v3

- Status: Accepted
- Date: 2026-08-10

## Context

[ADR 0029](0029-founder-economy-simulator-v3-enforced-boundary.md) accepted
`founder-economy-simulator-v3`, which enforces the cycle boundary and record
completeness. Two accepted models still bind version two: the escrow payout model
and the scenario suite.

They are coupled in one direction. The suite's escrow drain binds the escrow
model, so rebinding the suite depends on the escrow model already having a
version-three binding. That is the same ordering ADR 0026 recorded for version
two, and this ADR covers only the escrow half.

## Decision

### A third `Binding`, not a package

ADR 0026 chose one shared implementation over a duplicate package because the two
escrow versions' transitions were identical, and it named the condition under
which that choice inverts: "that would become the wrong one if a version three
revised a payout rule; at that point option 1 becomes correct for the diverging
transition."

Version three does not revise a payout rule. What economy version three revised
is the *economy* model's transitions — a new activation-height input, a window
check, a completeness check — and this model performs none of them. It reads one
recorded economy state by digest and never evaluates a permission, a window, or a
record.

The same test that gave the economy model a sibling package in ADR 0029 therefore
gives this model a third `Binding` entry, and the two answers are consistent
rather than in tension: a version owns what its own behavior changes.

### Containment is checked against every predecessor

Version two's verifier replayed the version-one fixture's bind events through the
version-two walk and required all of them to be rejected. The obvious extension
would have been to replay only version two's fixture through version three.

That was rejected. The three economy state labels are distinct strings rather
than a chain, so containment against version two implies nothing about
containment against version one. A defect that made the version-three bind accept
a version-one state — a fallback label, a truncated comparison, a digest computed
over the wrong preimage — would pass a check that only offered it version-two
states. The verifier therefore replays both earlier fixtures, and the vectors
record an offered and a rejected count per predecessor.

The check is written over an ordered predecessor table rather than as two
hard-coded cases, so a fourth version inherits it by adding one entry.

### The scenario is held fixed again

`research-events-v3.json` is the version-two scenario with only its four embedded
economy states rebound. Authoring a fresh scenario against the version-three
economy was rejected for the reason ADR 0026 gives: it would change the evidence
and the binding at once, and a differing trace could then mean either a rebinding
defect or an intended scenario difference.

The equivalence is asserted rather than assumed. All three runs produce identical
result codes for all 39 events in identical order, and any two final states differ
in exactly one member, `bound_state_digest`.

### The cap agreement is derived across every binding, not pairwise

`caps_agree()` now compares every registered binding against version one rather
than comparing two. The recorded vector's value does not change — the caps do
agree — but the claim behind it is stronger, and a fourth binding is covered
without editing the check.

`escrow-payout-v2.txt` is byte-for-byte unchanged as a result, which the diff
shows directly. That is the intended property: strengthening a check must not
silently rewrite accepted evidence.

### The coinciding opening custody is recorded, not assumed

The bind yields 34,200,000,000 / 6,840,000,000 / 3,420,000,000 atomic units,
identical to both earlier versions, because the escrow legs of a base permission
are unrevised and all three fixtures accept two base permissions.

The state those amounts come from is not the same state. The version-three
research scenario records activation heights, enforces the window check, and
requires complete records, so its final state has a different shape and a
different digest. The vectors record the coincidence and its cause separately, so
a future revision that changed a leg would surface as a mismatch rather than be
read as continuity.

## Consequences

- `simulation/escrow_payout/` implements three accepted contracts. Versions one
  and two keep their fixtures, vector files, digests, and tests byte-for-byte
  unchanged and passing.
- `tools/escrow-payout-vectors/verify.py` accepts `--version v3`, still
  defaulting to `v1`. Each version loads only its own economy model, so none can
  silently satisfy another's binding.
- `test-vectors/escrow-payout-v3.txt` records 174 values: version one's 169 under
  v3 labels and digests, plus five derived compatibility values.
- The scenario suite still binds version two of both models. Rebinding it is the
  following slice, and it is the substantive half: its population generator must
  supply activation heights and derive every `cycle_window` from them, which is
  what turns its tick convention into a checked rule.
- No C++, consensus, devnet, bridge, wallet, AI, biometric, or resource behavior
  changes. The model activates nothing and issues no native unit.

## Compatibility and independent review

All three versions coexist. Every version-three domain label ends in `-v3`, and
all eighteen strings across the three bindings are distinct, so no digest computed
under one version can be replayed as another and every provenance pair is
disjoint in both directions.

This slice proves that the escrow accounting is unchanged under a third economy
binding, and that the enforced schedule version three introduced does not disturb
the custody it hands to the escrows. It proves nothing new about escrow policy:
not that a recipient is legitimate, that an AI evaluation is well made, that an
approval threshold is safe, or that recipient balances are bounded at 100,000
seats. Those limits are stated in `escrow-payout-v1.md` and are unchanged. No
independent security review has occurred.
