# Escrow payout v2

Status: Accepted M3 research model contract; not a consensus transition

This document defines the deterministic escrow payout contract that binds
[`founder-economy-simulator-v2`](founder-economy-simulator-v2.md) instead of
version one, as required by requirement 3 of
[`first-goal.md`](../project/first-goal.md).

The change is classified as compatibility, not economics.
[ADR 0026](../decisions/0026-dependent-model-rebinding-to-economy-v2.md) records
the alternatives and decision. It changes no M1 bytes, C++ state, configured
devnet supply, and no accepted schema, vector, or digest of
`founder-economy-manifest-v1`, `founder-economy-simulator-v1`,
`founder-economy-manifest-v2`, `founder-economy-simulator-v2`,
`founder-seat-schedule-v1`, `revenue-routing-v1`, or `escrow-payout-v1`.

## Relationship to version one

[`escrow-payout-v1.md`](escrow-payout-v1.md) is not edited, retracted, or
reinterpreted. It states the contract the accepted M2 evidence proves, and
`test-vectors/escrow-payout-v1.txt` remains normative and passing.

Version one's own versioning section fixes its schema strings, field sets,
escrow set, caps, research-input shapes, state shape, journal buckets, digest
labels, error codes, and rejection order as immutable, and requires a new schema
and ADR for a change to any of them. The economy state a bind accepts is one of
those research-input shapes, so rebinding is a new version rather than an edit.

**Exactly six strings change, and nothing else does.**

| | v1 | v2 |
| --- | --- | --- |
| Result schema | `protocol-stack/escrow-payout-result/v1` | `protocol-stack/escrow-payout-result/v2` |
| Events label | `protocol-stack:escrow-payout:events-v1` | `…events-v2` |
| State label | `protocol-stack:escrow-payout:state-v1` | `…state-v2` |
| Trace label | `protocol-stack:escrow-payout:trace-v1` | `…trace-v2` |
| Result label | `protocol-stack:escrow-payout:result-v1` | `…result-v2` |
| Bound economy state label | `protocol-stack:founder-economy:state-v1` | `protocol-stack:founder-economy:state-v2` |

Every transition, field set, rejection condition, rejection order, journal
bucket, invariant, resource bound, and error code named in version one applies
here unchanged and is incorporated by reference rather than restated. A future
reader who needs the payout rules reads version one.

Because the two versions share their transitions, they share one implementation.
`simulation/escrow_payout/` selects a version through a `Binding` record rather
than existing twice, and ADR 0026 records why a second package was rejected.

## The escrow set and its caps are unchanged

The three escrow identifiers and their caps are identical under both accepted
economy contracts:

| Escrow | Cap, display units | Cap, atomic units |
| --- | --- | --- |
| `venture_escrow` | 12,500,100,000 | 1,250,010,000,000,000,000 |
| `community_grants_escrow` | 2,500,020,000 | 250,002,000,000,000,000 |
| `developer_incentives_escrow` | 1,250,010,000 | 125,001,000,000,000,000 |

This is a fact about the revision rather than an assumption of this document.
[ADR 0023](../decisions/0023-founder-decisions-activity-referrals-and-supply.md)
raised the maximum supply from 55,743,940,100 to 56,993,950,100 display units
through the `founder_referral` channel alone, and no escrow channel moved. The
model exposes `caps_agree()` and the vectors record the agreement as a derived
value, so a future revision that did move one of the three would fail rather
than be absorbed silently.

The denomination is likewise unrevised: eight decimal places and 100,000,000
atomic units per display unit, enforced independently by both manifest loaders.

## The compatibility boundary

A founder-economy state digest is computed as `D(L) || JCS(value)` over that
version's own domain label. `bind_opening_custody` recomputes the digest of the
supplied state under the bound version's label before reading a single amount.

Therefore:

- a state recorded under `protocol-stack:founder-economy:state-v1` can never
  satisfy a version-two bind, and
- a state recorded under `protocol-stack:founder-economy:state-v2` can never
  satisfy a version-one bind.

Both directions are rejected with `INVALID_RESEARCH_INPUT`, which is version
one's existing code for a state whose supplied digest is not the recomputed one.
No new error code is introduced, because no new failure mode exists: a
cross-version state is exactly a state whose digest does not match.

The rejection is caused by the label and not by the state's shape. Relabelling
the identical v1 state value under the v2 label makes the same bind succeed,
which the tests assert so that the boundary is not confused with a schema check.

## What the binding does and does not establish

Unchanged from version one, and restated because it is the claim most easily
overread: the model only recomputes the supplied state's digest, so a
self-consistent invented state also passes it. Consistency is not provenance.

Provenance is supplied by the verifier, not the model. `verify.py --version v2`
runs `founder-economy-simulator-v2` on its own accepted fixture and requires the
escrow fixture to bind that exact run's digest. A fixture carrying an invented
but self-consistent v2 state satisfies the model and fails the verifier.

Inside the model the manifest cap remains the defence, and the
`CUSTODY_ABOVE_CAP` vector still exercises it against a self-consistent v2 state
one atomic unit above the venture escrow cap.

## The research scenario

`simulation/escrow_payout/fixtures/research-events-v2.json` is the version-one
scenario with only its four embedded founder-economy states rebound. The
capability grants, payouts, revocations, cycle advances, approval fixtures, and
every adversarial probe are carried over unchanged.

That is deliberate. Holding the scenario fixed makes the rebinding auditable:
the two runs must produce identical result codes for all 39 events in identical
order, and their final states must differ in exactly one member,
`bound_state_digest`. A rebinding that altered a payout rule would still produce
a self-consistent vector file, so the equivalence is asserted rather than
assumed.

The four rebound events are:

| Event | Supplied v2 state | Expected result |
| --- | --- | --- |
| `bind-tampered-digest` | the real state, one hex digit altered in the digest | `INVALID_RESEARCH_INPUT` |
| `bind-above-cap` | self-consistent, venture custody at cap + 1 | `CUSTODY_ABOVE_CAP` |
| `bind-economy-state` | the live v2 run's final state | `OK` |
| `bind-replay` | the same state again | `ALREADY_BOUND` |

`bind-missing-input` carries no state and is unchanged.

The opening custody the accepted bind yields is 34,200,000,000 /
6,840,000,000 / 3,420,000,000 atomic units, which equals version one's. The
escrow legs of a base permission are unrevised and both fixtures accept two base
permissions, so the amounts coincide while the state they come from does not.
The vectors record both facts, so the coincidence is evidence rather than a
silent assumption that nothing changed.

## Versioning and compatibility

Everything version one fixes as immutable is immutable here, with the six
strings above substituted. A changed bound, a new escrow, a changed rejection
order, or a third economy binding requires a new schema and ADR.

Running this model has no effect on an M1 account, height, transaction root,
receipt, state root, SQLite database, ABCI response, or CometBFT validator, nor
on any accepted state, vector, or digest of the other five models.

`economy-scenario-suite-v1` remains bound to version one of both the economy and
this model. Rebinding the suite is the next slice; until then its recorded
digests are evidence about the v1 contracts, which
[`economy-scenario-suite-v1.md`](economy-scenario-suite-v1.md) already records.

Error codes here are simulator result codes. M3 must separately define consensus
receipts, numeric codes, and commitments before a C++ transition exists.

## Required vectors and evidence

[`escrow-payout-v2.txt`](../../test-vectors/escrow-payout-v2.txt) is normative.
It records everything `escrow-payout-v1.txt` records, under the v2 labels and
digests, plus three derived compatibility values:

- `binding.v1_states_offered_to_v2` — the count of v1 fixture bind events
  carrying an economy state, replayed under the v2 label;
- `binding.v1_states_rejected_by_v2` — how many of those were rejected, which
  must equal the first; and
- `binding.escrow_caps_agree_with_v1` — whether both accepted economy contracts
  give the same three escrow caps.

The executed verifier must independently derive, not restate, every recorded
value, and must fail when a recorded key is never derived, when a derived key is
not recorded, and when any recorded value is tampered with. All three, plus
running the v2 verifier against the v1 vector file, are confirmed by execution.

Test coverage must additionally include both cross-version bind rejections, the
relabelling control that shows the label caused the rejection, the equality of
the two versions' trace codes and event order, the single differing state
member, the distinctness of all six strings, and the escrow-cap agreement.

## What this model does not establish

Every limitation in version one's corresponding section holds unchanged. In
particular, this slice adds no evidence about whether a payout recipient is
legitimate, whether an AI evaluation is well made, whether an approval threshold
is safe, or whether the per-seat and recipient balance sets are bounded at
100,000 seats. It changes which economy contract the escrows draw from; it does
not change what an escrow payout proves.
