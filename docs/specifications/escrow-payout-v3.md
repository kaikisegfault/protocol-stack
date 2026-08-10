# Escrow payout v3

Status: Accepted M3 research model contract; not a consensus transition

This document defines the deterministic escrow payout contract that binds
[`founder-economy-simulator-v3`](founder-economy-simulator-v3.md) instead of
version two.

The change is classified as compatibility, not economics.
[ADR 0030](../decisions/0030-dependent-model-rebinding-to-economy-v3.md) records
the alternatives and decision. It changes no M1 bytes, C++ state, configured
devnet supply, and no accepted schema, vector, or digest of any previously
accepted manifest, simulator, seat, routing, escrow, boundary, uptime, or
scenario-suite artifact.

## Relationship to versions one and two

[`escrow-payout-v1.md`](escrow-payout-v1.md) and
[`escrow-payout-v2.md`](escrow-payout-v2.md) are not edited, retracted, or
reinterpreted. Their vector files remain normative and passing.

Version one's versioning section fixes its schema strings, field sets, escrow
set, caps, research-input shapes, state shape, journal buckets, digest labels,
error codes, and rejection order as immutable, and requires a new schema and ADR
for a change to any of them. The economy state a bind accepts is one of those
research-input shapes, so rebinding is a new version rather than an edit. That is
the same rule that produced version two.

**Exactly six strings change, and nothing else does.**

| | v2 | v3 |
| --- | --- | --- |
| Result schema | `protocol-stack/escrow-payout-result/v2` | `…/v3` |
| Events label | `protocol-stack:escrow-payout:events-v2` | `…events-v3` |
| State label | `protocol-stack:escrow-payout:state-v2` | `…state-v3` |
| Trace label | `protocol-stack:escrow-payout:trace-v2` | `…trace-v3` |
| Result label | `protocol-stack:escrow-payout:result-v2` | `…result-v3` |
| Bound economy state label | `protocol-stack:founder-economy:state-v2` | `protocol-stack:founder-economy:state-v3` |

Every transition, field set, rejection condition, rejection order, journal
bucket, invariant, resource bound, and error code named in version one applies
here unchanged and is incorporated by reference rather than restated. A future
reader who needs the payout rules reads version one.

The three versions therefore share one implementation.
`simulation/escrow_payout/` selects a version through a `Binding` record rather
than existing three times.

### Why a third `Binding` and not a package

ADR 0026 chose a shared implementation for version two because the two versions'
transitions were identical, and it named the condition under which that choice
inverts: a version that revises a payout rule. Version three does not meet that
condition and version three of the *economy* model does not change it either.
What economy version three revised is the economy model's own transitions — an
activation height, a window check, a completeness check — none of which this
model performs. The escrow payout rules are exactly what they were.

That is the distinction ADR 0029 turned on in the other direction: the economy
model earned a sibling package because *its* transitions changed shape. Applying
the same test here gives the opposite and correct answer.

## The escrow set and its caps are unchanged

The three escrow identifiers and their caps are identical under all three
accepted economy contracts:

| Escrow | Cap, display units | Cap, atomic units |
| --- | --- | --- |
| `venture_escrow` | 12,500,100,000 | 1,250,010,000,000,000,000 |
| `community_grants_escrow` | 2,500,020,000 | 250,002,000,000,000,000 |
| `developer_incentives_escrow` | 1,250,010,000 | 125,001,000,000,000,000 |

This is a fact about the revisions rather than an assumption. ADR 0023 raised the
maximum supply through the `founder_referral` channel alone, and economy version
three does not re-version the manifest at all — it loads the same accepted
`founder-economy-manifest-v2` artifact. The model exposes `caps_agree()` over
every registered binding and the vectors record the agreement as a derived value,
so a future revision that moved one of the three would fail rather than be
absorbed silently.

## The compatibility boundary

A founder-economy state digest is computed as `D(L) || JCS(value)` over that
version's own domain label. `bind_opening_custody` recomputes the digest of the
supplied state under the bound version's label before reading a single amount.

Therefore a state recorded under any one of the three economy labels can never
satisfy a bind under either of the other two. All six directions are rejected
with `INVALID_RESEARCH_INPUT`, which is version one's existing code for a state
whose supplied digest is not the recomputed one. No new error code is
introduced, because no new failure mode exists.

**Containment is checked against every predecessor, not only the immediate one.**
The three labels are distinct strings rather than a chain, so containment against
version two would not imply containment against version one. The vectors replay
every state-carrying bind event of both earlier fixtures through the version-three
walk and record that all of them are rejected.

The rejection is caused by the label and not by the state's shape. Relabelling an
identical state value under the version-three label makes the same bind succeed,
which the tests assert so the boundary is not confused with a schema check.

## The research scenario

`simulation/escrow_payout/fixtures/research-events-v3.json` is the version-two
scenario with only its four embedded founder-economy states rebound. The
capability grants, payouts, revocations, cycle advances, approval fixtures, and
every adversarial probe are carried over unchanged.

Holding the scenario fixed is what makes the rebinding auditable, and the
equivalence is asserted rather than assumed: **all three runs produce identical
result codes for all 39 events in identical order, and any two of their final
states differ in exactly one member, `bound_state_digest`.** A rebinding that
altered a payout rule would still produce a self-consistent vector file, so this
is the check that catches it.

The four rebound events are:

| Event | Supplied v3 state | Expected result |
| --- | --- | --- |
| `bind-tampered-digest` | the real state, one hex digit altered in the digest | `INVALID_RESEARCH_INPUT` |
| `bind-above-cap` | self-consistent, venture custody at cap + 1 | `CUSTODY_ABOVE_CAP` |
| `bind-economy-state` | the live v3 run's final state | `OK` |
| `bind-replay` | the same state again | `ALREADY_BOUND` |

`bind-missing-input` carries no state and is unchanged.

The opening custody the accepted bind yields is 34,200,000,000 /
6,840,000,000 / 3,420,000,000 atomic units, which equals both earlier versions'.
The escrow legs of a base permission are unrevised and all three fixtures accept
two base permissions, so the amounts coincide while the state they come from does
not. The vectors record both facts, so the coincidence is evidence rather than a
silent assumption that nothing changed.

**The economy state behind it is not the same state.** The version-three research
scenario records activation heights, enforces the window check, and requires
complete records, so its final state has a different shape and a different digest
from version two's. That the three escrow custody amounts survive that unchanged
is the substance of this slice.

## Versioning and compatibility

Everything version one fixes as immutable is immutable here, with the six strings
above substituted. A changed bound, a new escrow, a changed rejection order, or a
fourth economy binding requires a new schema and ADR.

Running this model has no effect on an M1 account, height, transaction root,
receipt, state root, SQLite database, ABCI response, or CometBFT validator, nor
on any accepted state, vector, or digest of the other models.

`economy-scenario-suite-v2` remains bound to version two of both the economy and
this model. Rebinding the suite is the next slice; until then its recorded
digests are evidence about the v2 contracts.

Error codes here are simulator result codes. M3 must separately define consensus
receipts, numeric codes, and commitments before a C++ transition exists.

## Required vectors and evidence

`test-vectors/escrow-payout-v3.txt` is normative. It records everything
`escrow-payout-v1.txt` records, under the v3 labels and digests, plus five
derived compatibility values:

- `binding.v1_states_offered_to_v3` and `binding.v1_states_rejected_by_v3`;
- `binding.v2_states_offered_to_v3` and `binding.v2_states_rejected_by_v3`, each
  rejected count required to equal its offered count; and
- `binding.escrow_caps_agree_with_v1`, now derived across every registered
  binding rather than across two.

The executed verifier must independently derive, not restate, every recorded
value, and must fail when a recorded key is never derived, when a derived key is
not recorded, and when any recorded value is tampered with.

Test coverage must additionally include every cross-version bind rejection in
both directions, the relabelling control that shows the label caused the
rejection, the equality of the three versions' trace codes and event order, the
single differing state member between each pair, the distinctness of all
eighteen strings, and the escrow-cap agreement across all three bindings.

## What this model does not establish

Every limitation in version one's corresponding section holds unchanged. In
particular, this slice adds no evidence about whether a payout recipient is
legitimate, whether an AI evaluation is well made, whether an approval threshold
is safe, or whether the per-seat and recipient balance sets are bounded at
100,000 seats. It changes which economy contract the escrows draw from; it does
not change what an escrow payout proves.
